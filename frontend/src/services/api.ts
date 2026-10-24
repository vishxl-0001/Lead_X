import { LeadItem, ScrapeRequest, JobStatus, StatsResponse, LocationSuggestion, HistoryJob } from '../types';

const RAW_URL = ((import.meta as any).env?.VITE_API_URL || '').trim().replace(/\/+$/, '');
const API_BASE = RAW_URL ? (RAW_URL.endsWith('/api') ? RAW_URL : `${RAW_URL}/api`) : '/api';

export const api = {
  async getJobs(): Promise<HistoryJob[]> {
    try {
      const res = await fetch(`${API_BASE}/jobs`);
      if (!res.ok) return [];
      const data = await res.json();
      return data.jobs || [];
    } catch {
      return [];
    }
  },

  async deleteJob(jobId: number): Promise<void> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete job');
  },

  async searchLocations(q: string): Promise<LocationSuggestion[]> {
    if (!q || q.trim().length < 2) return [];
    try {
      const res = await fetch(`${API_BASE}/locations/search?q=${encodeURIComponent(q)}`);
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
      const res = await fetch(`${API_BASE}/locations/sub-areas?region=${encodeURIComponent(region)}`);
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to start scrape task');
    return res.json();
  },

  async getJobStatus(jobId: number): Promise<JobStatus> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`);
    if (!res.ok) throw new Error('Failed to get job status');
    return res.json();
  },

  async stopJob(jobId: number): Promise<void> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/stop`, { method: 'POST' });
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

    const res = await fetch(`${API_BASE}/leads?${query.toString()}`);
    if (!res.ok) throw new Error('Failed to fetch leads');
    return res.json();
  },

  async updateLead(leadId: number, update: { status?: string; notes?: string; owner_name?: string }): Promise<void> {
    const res = await fetch(`${API_BASE}/leads/${leadId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(update),
    });
    if (!res.ok) throw new Error('Failed to update lead');
  },

  async deleteLead(leadId: number): Promise<void> {
    const res = await fetch(`${API_BASE}/leads/${leadId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete lead');
  },

  async clearAllLeads(): Promise<void> {
    const res = await fetch(`${API_BASE}/leads`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to clear leads');
  },

  async getStats(): Promise<StatsResponse> {
    const res = await fetch(`${API_BASE}/stats`);
    if (!res.ok) throw new Error('Failed to fetch statistics');
    return res.json();
  },

  async getDefaultTemplate(): Promise<string> {
    const res = await fetch(`${API_BASE}/template`);
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
    return `${API_BASE}/export/csv?${query.toString()}`;
  },

  getExportVcfUrl(params?: { no_website_only?: boolean; mobile_only?: boolean; status?: string; search?: string; job_id?: number }): string {
    const query = new URLSearchParams();
    if (params?.search) query.set('search', params.search);
    if (params?.no_website_only) query.set('no_website_only', 'true');
    if (params?.mobile_only) query.set('mobile_only', 'true');
    if (params?.status && params.status !== 'All') query.set('status', params.status);
    if (params?.job_id !== undefined) query.set('job_id', String(params.job_id));
    return `${API_BASE}/export/vcf?${query.toString()}`;
  },
};
