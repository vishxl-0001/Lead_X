# LeadFinder — B2B Google Maps & WhatsApp Lead Generator

A 100% free, self-hosted B2B Lead Extractor engineered to find local businesses **without a website**, extract their owners' direct mobile numbers, and generate instant 1-click WhatsApp outreach links.

---

## 🌟 Key Features

1. **Zero-Website Filter**: Focuses exclusively on businesses without an official website or web page (prime conversion targets for web development, SEO, digital catalog, and marketing services).
2. **Direct WhatsApp Mobile Verification**: Uses carrier classification to filter out landlines and keep only mobile numbers capable of receiving WhatsApp messages.
3. **Owner Mention Mining**: Identifies potential owner/proprietor names from business titles and customer reviews.
4. **1-Click WhatsApp Launcher**: Generates instant `wa.me/` links pre-filled with your customized cold outreach pitch.
5. **Multi-Format Export Suite**:
   - **CSV / Excel**: Complete spreadsheet for CRM import.
   - **Phone Contacts (.vcf / vCard)**: 1-click import into Android / iPhone so all leads sync directly into your phone's WhatsApp contact list.
   - **Direct Clipboard Copy**: Copy all clean mobile numbers with one click.
6. **Stealth & Pacing Engine**: Uses `playwright-stealth` and randomized human-like delays (1.5–3.5s) to prevent automated rate limiting.

---

## 🛠️ Tech Stack

- **Backend**: FastAPI, Uvicorn, Python 3.12, SQLite.
- **Scraper**: Playwright (Async Chromium), Playwright-Stealth, Phonenumbers.
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide React Icons.

---

## 🚀 Quick Start (Single Command)

To start both the FastAPI backend and React frontend dashboard:

```bash
chmod +x start.sh
./start.sh
```

- **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
- **API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📂 Project Structure

```
Lead_Finder/
├── backend/
│   ├── config.py         # Config paths, default pitch template
│   ├── database.py       # SQLite connection, CRUD & deduplication
│   ├── export_utils.py   # CSV & VCF (vCard contacts) generators
│   ├── main.py           # FastAPI routes & background job runner
│   ├── models.py         # Pydantic schemas
│   ├── phone_utils.py    # Mobile vs landline parser & wa.me builder
│   └── scraper.py        # Playwright stealth Google Maps crawler
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ExportModal.tsx      # CSV / VCF download modal
│   │   │   ├── LeadDetailModal.tsx  # CRM notes & lead details
│   │   │   ├── LeadTable.tsx        # Interactive leads table
│   │   │   ├── Navbar.tsx           # Top navigation bar
│   │   │   ├── SearchPanel.tsx      # Scraper controls & live progress
│   │   │   ├── StatsOverview.tsx    # Metric summary cards
│   │   │   └── TemplateModal.tsx    # Custom WhatsApp message editor
│   │   ├── services/api.ts          # Backend API client
│   │   ├── types.ts                 # TypeScript types
│   │   ├── App.tsx                  # Main app layout
│   │   └── main.tsx
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── requirements.txt
├── start.sh
└── README.md
```

---

## 💬 WhatsApp Pitch Template

You can customize the outreach template from the dashboard UI using dynamic tags:
- `{business_name}`
- `{area}`
- `{category}`
- `{owner_name}`

Default Template:
> *"Hi {business_name}, I came across your business in {area} on Google Maps. I noticed you don't have an official website or digital catalog yet. We help local businesses create fast, high-converting websites and get 2x more direct customer inquiries. Can I share a quick sample preview for your business?"*

---

## 🛡️ Anti-Ban & Safety Rules
- Runs anonymously without requiring any personal Google account login.
- Respects pacing with random 1.5–3.5s delays between card clicks.
- Built-in fallback: if Google ever presents a verification challenge, the browser can be run in headful mode (`headless=False`) to solve it manually in seconds.
