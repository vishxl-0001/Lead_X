import asyncio
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Query, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from backend.config import DEFAULT_TEMPLATE
from backend.auth import authenticate_user, create_token, get_current_user
from backend.database import (
    init_db,
    save_or_update_lead,
    create_job,
    update_job_progress,
    get_job,
    query_leads,
    get_stats,
    update_lead,
    delete_lead,
    clear_all_leads,
    get_all_jobs,
    delete_job
)
from backend.models import (
    LoginRequest,
    AuthResponse,
    ScrapeRequest,
    LeadItem,
    LeadUpdate,
    JobStatus,
    StatsResponse
)
from backend.scraper import GoogleMapsScraper
from backend.export_utils import export_leads_to_csv, export_leads_to_vcf
from backend.country_detector import GLOBAL_COUNTRIES, detect_country_from_location
from backend.geocoding import search_locations_global, get_sub_areas_for_region

logger = logging.getLogger("lead_finder.api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Lead Finder API",
    description="B2B Google Maps Lead Finder without Website filter & WhatsApp Linker",
    version="1.0.0"
)

@app.get("/api/version")
def get_version():
    return {
        "version": "1.0.1",
        "commit": "ccb688a-tile-block",
        "status": "healthy"
    }

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active scraper instances by job_id
active_scrapers: Dict[int, GoogleMapsScraper] = {}


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Database initialized successfully.")


async def run_scraper_task(job_id: int, req: ScrapeRequest):
    """Background task executing the scraper and writing leads to the database."""
    def on_progress(scanned: int, no_web: int, mobile: int, msg: str):
        update_job_progress(job_id, scanned, no_web, mobile, "running", None)

    def on_lead(lead: LeadItem):
        lead.job_id = job_id
        save_or_update_lead(lead)

    scraper = GoogleMapsScraper(
        query=req.query,
        location=req.location,
        target_count=req.max_leads,
        radius_km=req.radius_km,
        lat=req.lat,
        lon=req.lon,
        no_website_only=req.no_website_only,
        mobile_only=req.mobile_only,
        min_rating=req.min_rating or 0.0,
        country_code=req.country_code,
        template=req.template or DEFAULT_TEMPLATE,
        job_id=job_id,
        progress_callback=on_progress,
        lead_callback=on_lead,
        headless=True
    )
    active_scrapers[job_id] = scraper

    try:
        leads = await scraper.run()
        update_job_progress(
            job_id=job_id,
            total_found=scraper.total_scanned,
            no_website=scraper.no_website_count,
            mobile=scraper.mobile_count,
            status="completed"
        )
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        update_job_progress(
            job_id=job_id,
            total_found=scraper.total_scanned,
            no_website=scraper.no_website_count,
            mobile=scraper.mobile_count,
            status="error",
            error_msg=str(e)
        )
    finally:
        active_scrapers.pop(job_id, None)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(req: LoginRequest):
    """Authenticates admin user and returns a signed 7-day bearer token."""
    if not authenticate_user(req.username, req.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )
    token = create_token(req.username)
    return AuthResponse(
        token=token,
        username=req.username,
        expires_in=7 * 86400
    )


@app.get("/api/auth/me")
def check_auth(current_user: str = Depends(get_current_user)):
    """Verifies that the current bearer token is active and valid."""
    return {"authenticated": True, "username": current_user}


@app.post("/api/scrape", response_model=Dict[str, Any])
async def start_scrape_job(
    req: ScrapeRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user)
):
    job_id = create_job(req.query, req.location, req.max_leads)
    background_tasks.add_task(run_scraper_task, job_id, req)
    return {
        "status": "started",
        "job_id": job_id,
        "message": f"Scraping started for '{req.query}' in '{req.location}'"
    }


@app.get("/api/jobs")
def list_jobs(current_user: str = Depends(get_current_user)):
    """Lists all search history jobs with aggregated leads count."""
    return {"jobs": get_all_jobs()}


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
def check_job_status(job_id: int, current_user: str = Depends(get_current_user)):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.delete("/api/jobs/{job_id}")
def remove_job(job_id: int, current_user: str = Depends(get_current_user)):
    """Deletes a past search run and its associated leads."""
    delete_job(job_id)
    return {"status": "deleted", "job_id": job_id}



@app.post("/api/jobs/{job_id}/stop")
def stop_job(job_id: int, current_user: str = Depends(get_current_user)):
    if job_id in active_scrapers:
        active_scrapers[job_id].stop()
        update_job_progress(job_id, 0, 0, 0, status="stopped", error_msg="Stopped by user")
        return {"status": "stopped", "message": f"Job {job_id} signaled to stop"}
    raise HTTPException(status_code=404, detail="Active job not found or already completed")


@app.get("/api/leads", response_model=List[LeadItem])
def list_leads(
    search: Optional[str] = None,
    no_website_only: bool = False,
    mobile_only: bool = False,
    status: Optional[str] = None,
    job_id: Optional[int] = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    current_user: str = Depends(get_current_user)
):
    return query_leads(
        search=search,
        no_website_only=no_website_only,
        mobile_only=mobile_only,
        status=status,
        job_id=job_id,
        limit=limit,
        offset=offset
    )


@app.patch("/api/leads/{lead_id}")
def edit_lead(lead_id: int, update: LeadUpdate, current_user: str = Depends(get_current_user)):
    success = update_lead(
        lead_id=lead_id,
        status=update.status,
        notes=update.notes,
        owner_name=update.owner_name
    )
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"status": "updated", "lead_id": lead_id}


@app.delete("/api/leads")
def clear_all(current_user: str = Depends(get_current_user)):
    count = clear_all_leads()
    return {"status": "cleared", "deleted_count": count}


@app.delete("/api/leads/{lead_id}")
def remove_lead(lead_id: int, current_user: str = Depends(get_current_user)):
    success = delete_lead(lead_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"status": "deleted", "lead_id": lead_id}


@app.get("/api/locations/search")
def search_locations(q: str = Query(..., min_length=2)):
    """Live global location lookup (cities, states, regions, countries worldwide)."""
    return {"results": search_locations_global(q)}


@app.get("/api/locations/sub-areas")
def get_sub_areas(region: str = Query(...)):
    """Returns top business sub-areas/cities within a selected state or region (e.g. Ontario)."""
    return {"sub_areas": get_sub_areas_for_region(region)}


@app.get("/api/countries")
def get_countries():
    return {
        "countries": [
            {"code": c["code"], "name": c["name"], "dial_code": c["dial_code"], "flag": c["flag"]}
            for c in GLOBAL_COUNTRIES.values()
        ]
    }



@app.get("/api/stats", response_model=StatsResponse)
def get_dashboard_stats(current_user: str = Depends(get_current_user)):
    stats = get_stats()
    return StatsResponse(**stats)


@app.get("/api/export/csv")
def download_csv(
    search: Optional[str] = None,
    no_website_only: bool = False,
    mobile_only: bool = False,
    status: Optional[str] = None,
    job_id: Optional[int] = None,
    current_user: str = Depends(get_current_user)
):
    leads = query_leads(
        search=search,
        no_website_only=no_website_only,
        mobile_only=mobile_only,
        status=status,
        job_id=job_id,
        limit=5000
    )
    csv_data = export_leads_to_csv(leads)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"}
    )


@app.get("/api/export/vcf")
def download_vcf(
    search: Optional[str] = None,
    no_website_only: bool = False,
    mobile_only: bool = False,
    status: Optional[str] = None,
    job_id: Optional[int] = None,
    current_user: str = Depends(get_current_user)
):
    leads = query_leads(
        search=search,
        no_website_only=no_website_only,
        mobile_only=mobile_only,
        status=status,
        job_id=job_id,
        limit=5000
    )
    vcf_data = export_leads_to_vcf(leads)
    return Response(
        content=vcf_data,
        media_type="text/vcard",
        headers={"Content-Disposition": "attachment; filename=leads_contacts.vcf"}
    )


@app.get("/api/template")
def get_default_template():
    return {"template": DEFAULT_TEMPLATE}
