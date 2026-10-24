import sqlite3
from typing import List, Optional, Dict, Any
from datetime import datetime
from backend.config import DB_PATH
from backend.models import LeadItem, JobStatus


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Leads Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                place_id TEXT UNIQUE,
                title TEXT NOT NULL,
                category TEXT,
                address TEXT,
                city TEXT,
                phone_raw TEXT,
                phone_clean TEXT,
                is_mobile INTEGER DEFAULT 0,
                has_website INTEGER DEFAULT 0,
                website_url TEXT,
                rating REAL,
                reviews_count INTEGER,
                owner_name TEXT,
                whatsapp_link TEXT,
                status TEXT DEFAULT 'New',
                notes TEXT,
                job_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Jobs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                location TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                total_found INTEGER DEFAULT 0,
                no_website_count INTEGER DEFAULT 0,
                mobile_count INTEGER DEFAULT 0,
                target_count INTEGER DEFAULT 30,
                error_message TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        # Indexes for fast querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_place_id ON leads(place_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_phone_clean ON leads(phone_clean)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_has_website ON leads(has_website)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_is_mobile ON leads(is_mobile)")
        
        # Automatically purge initial mock test data if present
        cursor.execute("DELETE FROM leads WHERE place_id LIKE 'mock_%'")
        conn.commit()


def save_or_update_lead(lead: LeadItem) -> Optional[int]:
    """Inserts or updates a lead, deduplicating by place_id or phone_clean."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if lead already exists by place_id or phone_clean
        existing = None
        if lead.place_id:
            cursor.execute("SELECT id FROM leads WHERE place_id = ?", (lead.place_id,))
            existing = cursor.fetchone()
            
        if not existing and lead.phone_clean:
            cursor.execute("SELECT id FROM leads WHERE phone_clean = ?", (lead.phone_clean,))
            existing = cursor.fetchone()
            
        now_str = datetime.now().isoformat()
        
        if existing:
            lead_id = existing["id"]
            cursor.execute("""
                UPDATE leads SET
                    title = COALESCE(?, title),
                    category = COALESCE(?, category),
                    address = COALESCE(?, address),
                    city = COALESCE(?, city),
                    phone_raw = COALESCE(?, phone_raw),
                    phone_clean = COALESCE(?, phone_clean),
                    is_mobile = ?,
                    has_website = ?,
                    website_url = COALESCE(?, website_url),
                    rating = COALESCE(?, rating),
                    reviews_count = COALESCE(?, reviews_count),
                    owner_name = COALESCE(?, owner_name),
                    whatsapp_link = COALESCE(?, whatsapp_link),
                    job_id = COALESCE(?, job_id)
                WHERE id = ?
            """, (
                lead.title, lead.category, lead.address, lead.city,
                lead.phone_raw, lead.phone_clean, 1 if lead.is_mobile else 0,
                1 if lead.has_website else 0, lead.website_url,
                lead.rating, lead.reviews_count, lead.owner_name,
                lead.whatsapp_link, lead.job_id, lead_id
            ))
            conn.commit()
            return lead_id
        else:
            cursor.execute("""
                INSERT INTO leads (
                    place_id, title, category, address, city, phone_raw, phone_clean,
                    is_mobile, has_website, website_url, rating, reviews_count,
                    owner_name, whatsapp_link, status, notes, job_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lead.place_id, lead.title, lead.category, lead.address, lead.city,
                lead.phone_raw, lead.phone_clean, 1 if lead.is_mobile else 0,
                1 if lead.has_website else 0, lead.website_url, lead.rating,
                lead.reviews_count, lead.owner_name, lead.whatsapp_link,
                lead.status or "New", lead.notes, lead.job_id, now_str
            ))
            conn.commit()
            return cursor.lastrowid


def create_job(query: str, location: str, target_count: int) -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO jobs (query, location, status, target_count)
            VALUES (?, ?, 'running', ?)
        """, (query, location, target_count))
        conn.commit()
        return cursor.lastrowid


def update_job_progress(job_id: int, total_found: int, no_website: int, mobile: int, status: str = "running", error_msg: Optional[str] = None):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        completed_at = datetime.now().isoformat() if status in ("completed", "stopped", "error") else None
        cursor.execute("""
            UPDATE jobs SET
                total_found = ?,
                no_website_count = ?,
                mobile_count = ?,
                status = ?,
                error_message = ?,
                completed_at = COALESCE(?, completed_at)
            WHERE id = ?
        """, (total_found, no_website, mobile, status, error_msg, completed_at, job_id))
        conn.commit()


def get_job(job_id: int) -> Optional[JobStatus]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return JobStatus(
            id=row["id"],
            query=row["query"],
            location=row["location"],
            status=row["status"],
            total_found=row["total_found"],
            no_website_count=row["no_website_count"],
            mobile_count=row["mobile_count"],
            target_count=row["target_count"],
            error_message=row["error_message"],
            started_at=str(row["started_at"]),
            completed_at=str(row["completed_at"]) if row["completed_at"] else None
        )


def get_all_jobs() -> List[Dict[str, Any]]:
    """Returns all past and active search runs with their extracted leads count."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                j.*,
                COUNT(l.id) as actual_leads_count,
                SUM(CASE WHEN l.phone_clean IS NOT NULL AND l.phone_clean != '' THEN 1 ELSE 0 END) as actual_phones_count,
                SUM(CASE WHEN l.has_website = 0 THEN 1 ELSE 0 END) as actual_no_website_count
            FROM jobs j
            LEFT JOIN leads l ON j.id = l.job_id
            GROUP BY j.id
            ORDER BY j.id DESC
        """)
        rows = cursor.fetchall()
        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "query": r["query"],
                "location": r["location"],
                "status": r["status"],
                "target_count": r["target_count"],
                "leads_count": r["actual_leads_count"],
                "phones_count": r["actual_phones_count"] or 0,
                "no_website_count": r["actual_no_website_count"] or 0,
                "started_at": str(r["started_at"]),
                "completed_at": str(r["completed_at"]) if r["completed_at"] else None,
                "error_message": r["error_message"]
            })
        return results


def delete_job(job_id: int) -> bool:
    """Deletes a search run and its associated leads."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM leads WHERE job_id = ?", (job_id,))
        cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()
        return True



def query_leads(
    search: Optional[str] = None,
    no_website_only: bool = False,
    mobile_only: bool = False,
    status: Optional[str] = None,
    job_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> List[LeadItem]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        clauses = []
        params = []
        
        if job_id is not None:
            clauses.append("job_id = ?")
            params.append(job_id)

        if search:
            clauses.append("(title LIKE ? OR address LIKE ? OR phone_clean LIKE ? OR category LIKE ?)")
            term = f"%{search}%"
            params.extend([term, term, term, term])
            
        if no_website_only:
            clauses.append("has_website = 0")
            
        if mobile_only:
            clauses.append("is_mobile = 1")
            
        if status and status.lower() != "all":
            clauses.append("status = ?")
            params.append(status)
            
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM leads {where_sql} ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        results = []
        for r in rows:
            results.append(LeadItem(
                id=r["id"],
                place_id=r["place_id"],
                title=r["title"],
                category=r["category"],
                address=r["address"],
                city=r["city"],
                phone_raw=r["phone_raw"],
                phone_clean=r["phone_clean"],
                is_mobile=bool(r["is_mobile"]),
                has_website=bool(r["has_website"]),
                website_url=r["website_url"],
                rating=r["rating"],
                reviews_count=r["reviews_count"],
                owner_name=r["owner_name"],
                whatsapp_link=r["whatsapp_link"],
                status=r["status"] or "New",
                notes=r["notes"],
                job_id=r["job_id"],
                created_at=str(r["created_at"])
            ))
        return results


def get_stats() -> Dict[str, int]:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM leads")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM leads WHERE has_website = 0")
        no_web = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM leads WHERE is_mobile = 1")
        mob = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM leads WHERE status != 'New'")
        contacted = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM jobs")
        jobs_count = cursor.fetchone()[0]
        
        return {
            "total_leads": total,
            "no_website_leads": no_web,
            "mobile_leads": mob,
            "contacted_leads": contacted,
            "total_jobs": jobs_count
        }


def update_lead(lead_id: int, status: Optional[str] = None, notes: Optional[str] = None, owner_name: Optional[str] = None) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        updates = []
        params = []
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        if owner_name is not None:
            updates.append("owner_name = ?")
            params.append(owner_name)
            
        if not updates:
            return False
            
        params.append(lead_id)
        cursor.execute(f"UPDATE leads SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        return cursor.rowcount > 0


def delete_lead(lead_id: int) -> bool:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
        conn.commit()
        return cursor.rowcount > 0


def clear_all_leads() -> int:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM leads")
        deleted = cursor.rowcount
        cursor.execute("DELETE FROM jobs")
        conn.commit()
        return deleted

