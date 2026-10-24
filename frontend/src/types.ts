export interface AuthUser {
  username: string;
  token: string;
  expires_in?: number;
}

export interface LeadItem {
  id?: number;
  place_id?: string;
  title: string;
  category?: string;
  address?: string;
  city?: string;
  phone_raw?: string;
  phone_clean?: string;
  is_mobile: boolean;
  has_website: boolean;
  website_url?: string;
  rating?: number;
  reviews_count?: number;
  owner_name?: string;
  whatsapp_link?: string;
  status: 'New' | 'Contacted' | 'Interested' | 'Closed' | 'Disqualified';
  notes?: string;
  job_id?: number;
  created_at?: string;
}

export interface ScrapeRequest {
  query: string;
  location: string;
  max_leads: number;
  radius_km?: number;
  lat?: number;
  lon?: number;
  no_website_only: boolean;
  mobile_only: boolean;
  min_rating?: number;
  template?: string;
  country_code?: string;
}

export interface LocationSuggestion {
  display_name: string;
  name: string;
  city?: string;
  state?: string;
  country?: string;
  country_code?: string;
  lat: number;
  lon: number;
  type?: string;
}

export interface JobStatus {
  id: number;
  query: string;
  location: string;
  status: 'pending' | 'running' | 'completed' | 'stopped' | 'error';
  total_found: number;
  no_website_count: number;
  mobile_count: number;
  target_count: number;
  error_message?: string;
  started_at: string;
  completed_at?: string;
}

export interface HistoryJob {
  id: number;
  query: string;
  location: string;
  status: string;
  target_count: number;
  leads_count: number;
  phones_count: number;
  no_website_count: number;
  started_at: string;
  completed_at?: string;
  error_message?: string;
}

export interface StatsResponse {
  total_leads: number;
  no_website_leads: number;
  mobile_leads: number;
  contacted_leads: number;
  total_jobs: number;
}
