import { LeadItem, ScrapeRequest, JobStatus, StatsResponse, LocationSuggestion, HistoryJob, AuthUser } from '../types';

const TOKEN_KEY = 'lead_x_auth_token';
const USERNAME_KEY = 'lead_x_auth_user';
const BACKEND_URL_KEY = 'lead_x_custom_backend_url';

export function getApiBase(): string {
  const custom = typeof window !== 'undefined' ? localStorage.getItem(BACKEND_URL_KEY) : null;
  const envUrl = ((import.meta as any).env?.VITE_API_URL || '').trim();
  let raw = (custom || envUrl).replace(/\/+$/, '');
  if (!raw && typeof window !== 'undefined') {
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    if (!isLocal) {
      raw = 'https://lead-x.onrender.com';
    }
  }
  return raw ? (raw.endsWith('/api') ? raw : `${raw}/api`) : '/api';
}

function getAuthHeaders(customHeaders: Record<string, string> = {}): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY);
  const headers: Record<string, string> = { ...customHeaders };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export const api = {
  getBackendUrl(): string {
    return localStorage.getItem(BACKEND_URL_KEY) || ((import.meta as any).env?.VITE_API_URL || '');
  },

  setBackendUrl(url: string): void {
    const trimmed = url.trim().replace(/\/+$/, '');
    if (trimmed) {
      localStorage.setItem(BACKEND_URL_KEY, trimmed);
    } else {
      localStorage.removeItem(BACKEND_URL_KEY);
    }
  },

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },

  getCurrentUser(): string | null {
    return localStorage.getItem(USERNAME_KEY);
  },

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USERNAME_KEY);
  },

  async login(username: string, password: string): Promise<AuthUser> {
    const apiBase = getApiBase();
    try {
      const res = await fetch(`${apiBase}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        if (res.status === 404) {
          throw new Error(
            'Backend returned 404 Not Found. Make sure your Render backend has finished building and the backend URL is connected.'
          );
        }
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Invalid username or password');
      }

      const data: AuthUser = await res.json();
      localStorage.setItem(TOKEN_KEY, data.token);
      localStorage.setItem(USERNAME_KEY, data.username);
      return data;
    } catch (fetchErr: any) {
      if (fetchErr.name === 'TypeError' || fetchErr.message?.includes('Failed to fetch')) {
        throw new Error(
          'Cannot reach backend server. Please verify your Render service is Live and enter the backend URL below.'
        );
      }
      throw fetchErr;
    }
  },

  async checkAuth(): Promise<{ authenticated: boolean; username: string }> {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return { authenticated: false, username: '' };
    try {
      const res = await fetch(`${getApiBase()}/auth/me`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) {
        this.logout();
        return { authenticated: false, username: '' };
      }
      const data = await res.json();
      return { authenticated: true, username: data.username || 'vishxl' };
    } catch {
      return { authenticated: false, username: '' };
    }
  },

  async getJobs(): Promise<HistoryJob[]> {
    try {
      const res = await fetch(`${getApiBase()}/jobs`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) return [];
      const data = await res.json();
      return data.jobs || [];
    } catch {
      return [];
    }
  },

  async deleteJob(jobId: number): Promise<void> {
    const res = await fetch(`${getApiBase()}/jobs/${jobId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete job');
  },

  async searchLocations(q: string): Promise<LocationSuggestion[]> {
    if (!q || q.trim().length < 2) return [];

    // 1. Primary: Try Backend location service
    try {
      const res = await fetch(`${getApiBase()}/locations/search?q=${encodeURIComponent(q)}`, {
        headers: getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.results && data.results.length > 0) {
          return data.results;
        }
      }
    } catch (e) {
      console.warn('Backend location lookup error, falling back to direct geocoding:', e);
    }

    // 2. Client-side Fallback: Query Open-Meteo global API directly from browser
    try {
      const cleanQ = q.trim();
      const directRes = await fetch(
        `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(cleanQ)}&count=8&language=en&format=json`
      );
      if (directRes.ok) {
        const data = await directRes.json();
        let items = data.results || [];

        // If no results and query has a comma (e.g. "Auckland, New Zealand"), try the first token
        if (items.length === 0 && cleanQ.includes(',')) {
          const firstToken = cleanQ.split(',')[0].trim();
          const tokenRes = await fetch(
            `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(firstToken)}&count=8&language=en&format=json`
          );
          if (tokenRes.ok) {
            const tokenData = await tokenRes.json();
            items = tokenData.results || [];
          }
        }

        if (items.length > 0) {
          return items.map((item: any) => {
            const parts = [item.name, item.admin1, item.country].filter(Boolean);
            const displayName = Array.from(new Set(parts)).join(', ');
            return {
              display_name: displayName,
              name: item.name,
              city: item.name,
              state: item.admin1 || '',
              country: item.country || '',
              country_code: (item.country_code || '').toUpperCase(),
              lat: item.latitude,
              lon: item.longitude,
              type: 'city',
            };
          });
        }
      }
    } catch (err) {
      console.error('Direct geocoding error:', err);
    }

    return [];
  },

  async getSubAreas(region: string): Promise<string[]> {
    if (!region) return [];
    try {
      const res = await fetch(`${getApiBase()}/locations/sub-areas?region=${encodeURIComponent(region)}`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) return [];
      const data = await res.json();
      return data.sub_areas || [];
    } catch {
      return [];
    }
  },

  async startScrape(payload: ScrapeRequest): Promise<{ status: string; job_id: number; message: string }> {
    const res = await fetch(`${getApiBase()}/scrape`, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to start scrape task');
    return res.json();
  },

  async getJobStatus(jobId: number): Promise<JobStatus> {
    const res = await fetch(`${getApiBase()}/jobs/${jobId}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get job status');
    return res.json();
  },

  async stopJob(jobId: number): Promise<void> {
    const res = await fetch(`${getApiBase()}/jobs/${jobId}/stop`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to stop job');
  },

  async getLeads(params?: {
    search?: string;
    no_website_only?: boolean;
    mobile_only?: boolean;
    status?: string;
    job_id?: number;
    limit?: number;
    offset?: number;
  }): Promise<LeadItem[]> {
    const query = new URLSearchParams();
    if (params?.search) query.set('search', params.search);
    if (params?.no_website_only !== undefined) query.set('no_website_only', String(params.no_website_only));
    if (params?.mobile_only !== undefined) query.set('mobile_only', String(params.mobile_only));
    if (params?.status && params.status !== 'All') query.set('status', params.status);
    if (params?.job_id !== undefined) query.set('job_id', String(params.job_id));
    if (params?.limit) query.set('limit', String(params.limit));
    if (params?.offset) query.set('offset', String(params.offset));

    const res = await fetch(`${getApiBase()}/leads?${query.toString()}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch leads');
    return res.json();
  },

  async updateLead(leadId: number, update: { status?: string; notes?: string; owner_name?: string }): Promise<void> {
    const res = await fetch(`${getApiBase()}/leads/${leadId}`, {
      method: 'PATCH',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(update),
    });
    if (!res.ok) throw new Error('Failed to update lead');
  },

  async deleteLead(leadId: number): Promise<void> {
    const res = await fetch(`${getApiBase()}/leads/${leadId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete lead');
  },

  async clearAllLeads(): Promise<void> {
    const res = await fetch(`${getApiBase()}/leads`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to clear leads');
  },

  async getStats(): Promise<StatsResponse> {
    const res = await fetch(`${getApiBase()}/stats`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch statistics');
    return res.json();
  },

  async getDefaultTemplate(): Promise<string> {
    const res = await fetch(`${getApiBase()}/template`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) return '';
    const data = await res.json();
    return data.template || '';
  },

  getExportCsvUrl(params?: { no_website_only?: boolean; mobile_only?: boolean; status?: string; search?: string; job_id?: number }): string {
    const query = new URLSearchParams();
    if (params?.search) query.set('search', params.search);
    if (params?.no_website_only) query.set('no_website_only', 'true');
    if (params?.mobile_only) query.set('mobile_only', 'true');
    if (params?.status && params.status !== 'All') query.set('status', params.status);
    if (params?.job_id !== undefined) query.set('job_id', String(params.job_id));
    const token = this.getToken();
    if (token) query.set('token', token);
    return `${getApiBase()}/export/csv?${query.toString()}`;
  },

  getExportVcfUrl(params?: { no_website_only?: boolean; mobile_only?: boolean; status?: string; search?: string; job_id?: number }): string {
    const query = new URLSearchParams();
    if (params?.search) query.set('search', params.search);
    if (params?.no_website_only) query.set('no_website_only', 'true');
    if (params?.mobile_only) query.set('mobile_only', 'true');
    if (params?.status && params.status !== 'All') query.set('status', params.status);
    if (params?.job_id !== undefined) query.set('job_id', String(params.job_id));
    const token = this.getToken();
    if (token) query.set('token', token);
    return `${getApiBase()}/export/vcf?${query.toString()}`;
  },
};
