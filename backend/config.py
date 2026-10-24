import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "leads.db"

DEFAULT_TEMPLATE = (
    "Hi {business_name}, I came across your business in {area} on Google Maps. "
    "I noticed you don't have an official website or digital catalog yet. "
    "We help local businesses create fast, high-converting websites and get 2x more direct customer inquiries. "
    "Can I share a quick sample preview for your business?"
)

DEFAULT_COUNTRY = "IN"  # Default to India (+91), supports any ISO country code
