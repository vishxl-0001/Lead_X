import io
import csv
from typing import List
from backend.models import LeadItem


def export_leads_to_csv(leads: List[LeadItem]) -> str:
    """Exports a list of LeadItem objects to CSV string."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    
    headers = [
        "ID",
        "Business Name",
        "Category",
        "Owner Name",
        "Phone Clean (WhatsApp)",
        "Is Mobile",
        "Has Website",
        "Rating",
        "Reviews Count",
        "Address",
        "City",
        "WhatsApp Link",
        "Lead Status",
        "Notes",
        "Created At"
    ]
    writer.writerow(headers)
    
    for lead in leads:
        writer.writerow([
            lead.id or "",
            lead.title or "",
            lead.category or "",
            lead.owner_name or "",
            lead.phone_clean or lead.phone_raw or "",
            "YES" if lead.is_mobile else "NO",
            "YES" if lead.has_website else "NO",
            lead.rating if lead.rating is not None else "",
            lead.reviews_count if lead.reviews_count is not None else "",
            lead.address or "",
            lead.city or "",
            lead.whatsapp_link or "",
            lead.status or "New",
            lead.notes or "",
            lead.created_at or ""
        ])
        
    return output.getvalue()


def export_leads_to_vcf(leads: List[LeadItem]) -> str:
    """
    Exports leads to vCard (VCF 3.0) format.
    Allows 1-click import into Android, iPhone, Google Contacts, and iCloud.
    Once imported into the phone, WhatsApp automatically links their contact cards!
    """
    vcf_lines = []
    
    for lead in leads:
        # Require a valid phone number for contact import
        phone = lead.phone_clean or lead.phone_raw
        if not phone:
            continue
            
        display_name = lead.title
        if lead.owner_name:
            display_name = f"{lead.owner_name} ({lead.title})"
            
        vcf_lines.append("BEGIN:VCARD")
        vcf_lines.append("VERSION:3.0")
        vcf_lines.append(f"FN:{display_name}")
        vcf_lines.append(f"ORG:{lead.title}")
        if lead.category:
            vcf_lines.append(f"TITLE:{lead.category}")
            
        # Cell / Mobile phone
        clean_tel = phone.replace(" ", "")
        vcf_lines.append(f"TEL;TYPE=CELL,VOICE,PREF:{clean_tel}")
        
        # Address
        if lead.address:
            clean_addr = lead.address.replace(";", " ").replace("\n", " ")
            vcf_lines.append(f"ADR;TYPE=WORK:;;{clean_addr};{lead.city or ''};;;")
            
        if lead.whatsapp_link:
            vcf_lines.append(f"URL:{lead.whatsapp_link}")
            
        # Notes
        note_parts = [
            f"Rating: {lead.rating or 'N/A'} ({lead.reviews_count or 0} reviews)",
            f"Website: {'None (Hot Lead)' if not lead.has_website else lead.website_url}",
            f"Status: {lead.status}"
        ]
        if lead.notes:
            note_parts.append(f"Notes: {lead.notes}")
        vcf_lines.append(f"NOTE:{' | '.join(note_parts)}")
        
        vcf_lines.append("END:VCARD\n")
        
    return "\n".join(vcf_lines)
