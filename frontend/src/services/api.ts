import { LeadItem, ScrapeRequest, JobStatus, StatsResponse, LocationSuggestion, HistoryJob, AuthUser } from '../types';

const RAW_URL = ((import.meta as any).env?.VITE_API_URL || '').trim().replace(/\/+$/, '');
const API_BASE = RAW_URL ? (RAW_URL.endsWith('/api') ? RAW_URL : `${RAW_URL}/api`) : '/api';

const TOKEN_KEY = 'lead_x_auth_token';
const USERNAME_KEY = 'lead_x_auth_user';

function getAuthHeaders(customHeaders: Record<string, string> = {}): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY);
  const headers: Record<string, string> = { ...customHeaders };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export const api = {
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
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Invalid username or password');
    }
    const data: AuthUser = await res.json();
    localStorage.setItem(TOKEN_KEY, data.token);
    localStorage.setItem(USERNAME_KEY, data.username);
    return data;
  },

  async checkAuth(): Promise<{ authenticated: boolean; username: string }> {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return { authenticated: false, username: '' };
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
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
      const res = await fetch(`${API_BASE}/jobs`, {
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
    const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete job');
  },

  async searchLocations(q: string): Promise<LocationSuggestion[]> {
    if (!q || q.trim().length < 2) return [];
    try {
      const res = await fetch(`${API_BASE}/locations/search?q=${encodeURIComponent(q)}`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) return [];
      const data = await res.json();
      return data.results || [];
    } catch {
      return [];
    }
  },

  async getSubAreas(region: string): Promise<string[]> {
    if (!region) return [];
    try {
      const res = await fetch(`${API_BASE}/locations/sub-areas?region=${encodeURIComponent(region)}`, {
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
    const res = await fetch(`${API_BASE}/scrape`, {
      method: 'POST',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to start scrape task');
    return res.json();
  },

  async getJobStatus(jobId: number): Promise<JobStatus> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get job status');
    return res.json();
  },

  async stopJob(jobId: number): Promise<void> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/stop`, {
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

    const res = await fetch(`${API_BASE}/leads?${query.toString()}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch leads');
    return res.json();
  },

  async updateLead(leadId: number, update: { status?: string; notes?: string; owner_name?: string }): Promise<void> {
    const res = await fetch(`${API_BASE}/leads/${leadId}`, {
      method: 'PATCH',
      headers: getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(update),
    });
    if (!res.ok) throw new Error('Failed to update lead');
  },

  async deleteLead(leadId: number): Promise<void> {
    const res = await fetch(`${API_BASE}/leads/${leadId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete lead');
  },

  async clearAllLeads(): Promise<void> {
    const res = await fetch(`${API_BASE}/leads`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to clear leads');
  },

  async getStats(): Promise<StatsResponse> {
    const res = await fetch(`${API_BASE}/stats`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch statistics');
    return res.json();
  },

  async getDefaultTemplate(): Promise<string> {
    const res = await fetch(`${API_BASE}/template`, {
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
    return `${API_BASE}/export/csv?${query.toString()}`;
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
    return `${API_BASE}/export/vcf?${query.toString()}`;
  },
};
