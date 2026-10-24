from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ScrapeRequest(BaseModel):
    query: str = Field(..., description="Business category or service, e.g. 'Electrician', 'Plumber'")
    location: str = Field(..., description="Target area or city, e.g. 'Ontario, Canada' or 'Mississauga, Ontario'")
    max_leads: int = Field(default=30, ge=5, le=200, description="Target number of leads")
    radius_km: int = Field(default=10, ge=1, le=100, description="Search radius in kilometers")
    lat: Optional[float] = Field(default=None, description="Optional latitude for precise radius targeting")
    lon: Optional[float] = Field(default=None, description="Optional longitude for precise radius targeting")
    no_website_only: bool = Field(default=False, description="Filter for businesses without a website")
    mobile_only: bool = Field(default=False, description="Filter for mobile numbers if enabled")
    min_rating: Optional[float] = Field(default=0.0, description="Minimum Google rating (0.0 to 5.0)")
    template: Optional[str] = Field(default=None, description="Custom WhatsApp pitch message template")
    country_code: Optional[str] = Field(default=None, description="Country code (auto-detected if omitted)")


class LeadItem(BaseModel):
    id: Optional[int] = None
    place_id: Optional[str] = None
    title: str
    category: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    phone_raw: Optional[str] = None
    phone_clean: Optional[str] = None
    is_mobile: bool = False
    has_website: bool = False
    website_url: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    owner_name: Optional[str] = None
    whatsapp_link: Optional[str] = None
    status: str = "New"  # New, Contacted, Interested, Closed, Disqualified
    notes: Optional[str] = None
    job_id: Optional[int] = None
    created_at: Optional[str] = None


class LeadUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    owner_name: Optional[str] = None


class JobStatus(BaseModel):
    id: int
    query: str
    location: str
    status: str  # pending, running, completed, stopped, error
    total_found: int = 0
    no_website_count: int = 0
    mobile_count: int = 0
    target_count: int = 30
    error_message: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None


class StatsResponse(BaseModel):
    total_leads: int
    no_website_leads: int
    mobile_leads: int
    contacted_leads: int
    total_jobs: int
