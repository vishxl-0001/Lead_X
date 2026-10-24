import React from 'react';
import {
  History,
  Calendar,
  MapPin,
  Phone,
  Flame,
  Download,
  Trash2,
  ExternalLink,
  Search,
  CheckCircle2,
  Loader2,
  XCircle,
} from 'lucide-react';
import { HistoryJob } from '../types';
import { api } from '../services/api';

interface SearchHistoryProps {
  jobs: HistoryJob[];
  loading: boolean;
  onSelectJob: (job: HistoryJob) => void;
  onDeleteJob: (jobId: number) => void;
  selectedJobId?: number | null;
}

export const SearchHistory: React.FC<SearchHistoryProps> = ({
  jobs,
  loading,
  onSelectJob,
  onDeleteJob,
  selectedJobId,
}) => {
  const formatDateTime = (isoStr: string) => {
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoStr;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Completed
          </span>
        );
      case 'running':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center gap-1">
            <Loader2 className="w-3 h-3 animate-spin" /> In Progress
          </span>
        );
      case 'error':
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center gap-1">
            <XCircle className="w-3 h-3" /> Error
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-700/40 text-slate-300">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="bg-dark-800 border border-dark-700 rounded-2xl shadow-xl overflow-hidden mb-6">
      {/* Header */}
      <div className="p-4 sm:p-5 border-b border-dark-700 flex items-center justify-between bg-dark-800/90">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <History className="w-5 h-5 text-emerald-400" />
            Extraction Search History
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-dark-700 text-slate-300 border border-dark-600">
              {jobs.length} Runs
            </span>
          </h2>
          <p className="text-xs text-slate-400">
            Every past search run is saved here with its exact keyword, location, and leads archive.
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 sm:p-5">
        {loading ? (
          <div className="py-12 text-center text-slate-400">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-2 border-emerald-500 border-t-transparent" />
            <p className="mt-2 text-xs">Loading search history...</p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="py-12 text-center text-slate-400">
            <Search className="w-10 h-10 mx-auto text-dark-600 mb-2" />
            <p className="text-sm font-semibold text-slate-300">No search history yet</p>
            <p className="text-xs text-slate-500 mt-1">
              Your extraction runs will be archived here automatically.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {jobs.map((job) => {
              const isSelected = selectedJobId === job.id;
              const csvUrl = api.getExportCsvUrl({ job_id: job.id });

              return (
                <div
                  key={job.id}
                  className={`p-4 rounded-xl border transition-all flex flex-col justify-between ${
                    isSelected
                      ? 'bg-dark-900 border-emerald-500/60 ring-1 ring-emerald-500/30'
                      : 'bg-dark-900/60 border-dark-700 hover:border-dark-600 hover:bg-dark-900'
                  }`}
                >
                  <div>
                    {/* Header: Query & Status */}
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <h3 className="font-bold text-white text-sm line-clamp-1">
                        {job.query}
                      </h3>
                      {getStatusBadge(job.status)}
                    </div>

                    {/* Location & Time */}
                    <p className="text-xs text-slate-300 flex items-center gap-1 line-clamp-1 mb-2">
                      <MapPin className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
                      {job.location}
                    </p>

                    <div className="text-[11px] text-slate-500 flex items-center gap-1 mb-3">
                      <Calendar className="w-3 h-3 text-slate-500" />
                      {formatDateTime(job.started_at)}
                    </div>

                    {/* Metric Badges */}
                    <div className="flex flex-wrap items-center gap-2 text-xs mb-3">
                      <span className="px-2 py-0.5 rounded-lg bg-dark-800 text-slate-200 border border-dark-700 font-semibold flex items-center gap-1">
                        {job.leads_count} Leads
                      </span>
                      <span className="px-2 py-0.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold flex items-center gap-1">
                        <Phone className="w-3 h-3" />
                        {job.phones_count} Phones
                      </span>
                      {job.no_website_count > 0 && (
                        <span className="px-2 py-0.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 font-semibold flex items-center gap-1">
                          <Flame className="w-3 h-3" />
                          {job.no_website_count} No Web
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Footer actions */}
                  <div className="pt-3 border-t border-dark-800 flex items-center justify-between text-xs">
                    <button
                      type="button"
                      onClick={() => onSelectJob(job)}
                      className={`px-3 py-1.5 rounded-lg font-bold transition-colors flex items-center gap-1 ${
                        isSelected
                          ? 'bg-emerald-600 text-white'
                          : 'bg-dark-800 hover:bg-dark-700 text-slate-200 border border-dark-700'
                      }`}
                    >
                      <span>{isSelected ? 'Viewing' : 'View Leads'}</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </button>

                    <div className="flex items-center space-x-1">
                      {job.leads_count > 0 && (
                        <a
                          href={csvUrl}
                          download
                          title="Download CSV for this search run"
                          className="p-1.5 rounded-lg bg-dark-800 hover:bg-dark-700 text-slate-400 hover:text-emerald-400 border border-dark-700 transition-colors"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </a>
                      )}

                      <button
                        type="button"
                        onClick={() => onDeleteJob(job.id)}
                        title="Delete this search history"
                        className="p-1.5 rounded-lg bg-dark-800 hover:bg-rose-500/10 text-slate-400 hover:text-rose-400 border border-dark-700 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
