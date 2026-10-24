import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { StatsOverview } from './components/StatsOverview';
import { SearchPanel } from './components/SearchPanel';
import { LeadTable } from './components/LeadTable';
import { SearchHistory } from './components/SearchHistory';
import { LeadDetailModal } from './components/LeadDetailModal';
import { TemplateModal } from './components/TemplateModal';
import { ExportModal } from './components/ExportModal';
import { LoginScreen } from './components/LoginScreen';
import { api } from './services/api';
import { LeadItem, ScrapeRequest, JobStatus, StatsResponse, HistoryJob } from './types';
import { RotateCcw, Loader2 } from 'lucide-react';

export const App: React.FC = () => {
  // Authentication state
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [currentUser, setCurrentUser] = useState<string>('');
  const [checkingAuth, setCheckingAuth] = useState<boolean>(true);

  // Navigation: 'live' (current extraction) vs 'history' (past search archives)
  const [activeTab, setActiveTab] = useState<'live' | 'history'>('live');

  // Leads state
  const [leads, setLeads] = useState<LeadItem[]>([]);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loadingLeads, setLoadingLeads] = useState(true);
  const [loadingStats, setLoadingStats] = useState(true);

  // Search History state
  const [historyJobs, setHistoryJobs] = useState<HistoryJob[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Scoped Job Filter (to isolate current extraction from past extractions)
  const [currentJobId, setCurrentJobId] = useState<number | null>(null);
  const [viewingJob, setViewingJob] = useState<HistoryJob | null>(null);

  // Table search & status filter
  const [filterStatus, setFilterStatus] = useState('All');
  const [searchFilter, setSearchFilter] = useState('');

  // Active Scraping Job State
  const [isScraping, setIsScraping] = useState(false);
  const [activeJob, setActiveJob] = useState<JobStatus | null>(null);
  const pollIntervalRef = useRef<number | null>(null);

  // Modals
  const [selectedLead, setSelectedLead] = useState<LeadItem | null>(null);
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState(false);
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);
  const [currentTemplate, setCurrentTemplate] = useState('');

  // Verify Authentication on Load
  useEffect(() => {
    api.checkAuth().then((res) => {
      if (res.authenticated) {
        setIsAuthenticated(true);
        setCurrentUser(res.username || 'vishxl');
      } else {
        setIsAuthenticated(false);
      }
      setCheckingAuth(false);
    });
  }, []);

  // Load Initial Template
  useEffect(() => {
    if (isAuthenticated) {
      api.getDefaultTemplate().then((tpl) => {
        if (tpl) setCurrentTemplate(tpl);
      });
    }
  }, [isAuthenticated]);

  // Fetch Stats (silent option to prevent UI jitter)
  const loadStats = useCallback(async (silent = false) => {
    try {
      if (!silent) setLoadingStats(true);
      const data = await api.getStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    } finally {
      if (!silent) setLoadingStats(false);
    }
  }, []);

  // Fetch History Jobs
  const loadHistoryJobs = useCallback(async () => {
    try {
      setLoadingHistory(true);
      const jobs = await api.getJobs();
      setHistoryJobs(jobs);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  // Fetch Leads (silent = true prevents table unmounting / blinking!)
  const loadLeads = useCallback(
    async (silent = false, scopedJobId?: number | null) => {
      try {
        if (!silent) setLoadingLeads(true);
        const jobIdToQuery = scopedJobId !== undefined ? scopedJobId : currentJobId;

        const data = await api.getLeads({
          search: searchFilter || undefined,
          status: filterStatus !== 'All' ? filterStatus : undefined,
          job_id: jobIdToQuery !== null ? jobIdToQuery : undefined,
          limit: 500,
        });
        setLeads(data);
      } catch (err) {
        console.error('Failed to load leads:', err);
      } finally {
        if (!silent) setLoadingLeads(false);
      }
    },
    [searchFilter, filterStatus, currentJobId]
  );

  useEffect(() => {
    if (isAuthenticated) {
      loadLeads();
      loadStats();
      loadHistoryJobs();
    }
  }, [isAuthenticated, loadLeads, loadStats, loadHistoryJobs]);

  // Polling for Active Job — uses silent=true so there is ZERO blinking!
  const startPollingJob = useCallback(
    (jobId: number) => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      let consecutiveErrors = 0;

      pollIntervalRef.current = window.setInterval(async () => {
        try {
          const job = await api.getJobStatus(jobId);
          consecutiveErrors = 0;
          setActiveJob(job);

          // Silent background update: appends new leads without unmounting table or blinking
          loadLeads(true, jobId);
          loadStats(true);

          if (['completed', 'stopped', 'error'].includes(job.status)) {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setIsScraping(false);
            loadHistoryJobs();
          }
        } catch (err) {
          consecutiveErrors++;
          console.warn(`Job polling transient hiccup (${consecutiveErrors}/10):`, err);
          // Only stop if the server is permanently down after 10 consecutive failed attempts (15 seconds)
          if (consecutiveErrors >= 10) {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setIsScraping(false);
          }
        }
      }, 1500);
    },
    [loadLeads, loadStats, loadHistoryJobs]
  );

  // Start Scrape: resets table to only show leads from THIS new run!
  const handleStartScrape = async (req: ScrapeRequest) => {
    try {
      setIsScraping(true);
      setActiveTab('live');
      setViewingJob(null);
      setLeads([]); // Clear view for current extraction

      const res = await api.startScrape({
        ...req,
        template: currentTemplate || undefined,
      });

      setCurrentJobId(res.job_id);
      startPollingJob(res.job_id);
    } catch (err) {
      console.error('Failed to start scrape:', err);
      alert('Could not start scraping. Check backend logs.');
      setIsScraping(false);
    }
  };

  const handleStopScrape = async () => {
    if (!activeJob) return;
    try {
      await api.stopJob(activeJob.id);
      setIsScraping(false);
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      loadHistoryJobs();
    } catch (err) {
      console.error('Failed to stop scrape:', err);
    }
  };

  const handleUpdateStatus = async (leadId: number, newStatus: LeadItem['status']) => {
    setLeads((prev) =>
      prev.map((l) => (l.id === leadId ? { ...l, status: newStatus } : l))
    );
    try {
      await api.updateLead(leadId, { status: newStatus });
      loadStats(true);
    } catch (err) {
      console.error('Failed to update lead status:', err);
      loadLeads(true);
    }
  };

  const handleDeleteLead = async (leadId: number) => {
    if (!confirm('Are you sure you want to delete this lead?')) return;
    setLeads((prev) => prev.filter((l) => l.id !== leadId));
    try {
      await api.deleteLead(leadId);
      loadStats(true);
      loadHistoryJobs();
    } catch (err) {
      console.error('Failed to delete lead:', err);
      loadLeads(true);
    }
  };

  const handleClearAll = async () => {
    if (!confirm('Clear all leads from the database? This cannot be undone.')) return;
    setLeads([]);
    try {
      await api.clearAllLeads();
      loadStats();
      loadHistoryJobs();
      setCurrentJobId(null);
      setViewingJob(null);
    } catch (err) {
      console.error('Failed to clear leads:', err);
      loadLeads();
    }
  };

  const handleSaveLeadModal = async (
    leadId: number,
    update: { status?: LeadItem['status']; notes?: string; owner_name?: string }
  ) => {
    try {
      await api.updateLead(leadId, update);
      loadLeads(true);
      loadStats(true);
    } catch (err) {
      console.error('Failed to save lead updates:', err);
    }
  };

  // View leads from a specific historical search run
  const handleSelectHistoryJob = (job: HistoryJob) => {
    setViewingJob(job);
    setCurrentJobId(job.id);
    setActiveTab('live');
    loadLeads(false, job.id);
  };

  // Delete a past search history run
  const handleDeleteHistoryJob = async (jobId: number) => {
    if (!confirm('Delete this search run and all its leads?')) return;
    try {
      await api.deleteJob(jobId);
      if (currentJobId === jobId) {
        setCurrentJobId(null);
        setViewingJob(null);
        loadLeads(false, null);
      }
      loadHistoryJobs();
      loadStats();
    } catch (err) {
      console.error('Failed to delete history job:', err);
    }
  };

  // Reset filter to see all leads across all jobs
  const handleShowAllLeads = () => {
    setCurrentJobId(null);
    setViewingJob(null);
    loadLeads(false, null);
  };

  // Dynamic table title
  const currentTableTitle = viewingJob
    ? `Archive: ${viewingJob.query} in ${viewingJob.location}`
    : currentJobId
    ? `Current Extraction (Run #${currentJobId})`
    : 'All Extracted Leads';

  if (checkingAuth) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center space-y-3">
        <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
        <p className="text-xs text-slate-400 font-mono tracking-wider">INITIALIZING SECURE SESSION...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <LoginScreen
        onLoginSuccess={(uname) => {
          setIsAuthenticated(true);
          setCurrentUser(uname);
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-dark-900 text-slate-100 flex flex-col font-sans">
      {/* Navigation Bar with Tabs & User Badge */}
      <Navbar
        activeTab={activeTab}
        onChangeTab={(tab) => {
          setActiveTab(tab);
          if (tab === 'history') loadHistoryJobs();
        }}
        historyCount={historyJobs.length}
        onOpenTemplate={() => setIsTemplateModalOpen(true)}
        onOpenExport={() => setIsExportModalOpen(true)}
        currentUser={currentUser}
        onLogout={() => {
          api.logout();
          setIsAuthenticated(false);
          setLeads([]);
          setStats(null);
          setHistoryJobs([]);
        }}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Top Metric Cards */}
        <StatsOverview stats={stats} loading={loadingStats} />

        {/* Tab 1: Live Extraction / Finder */}
        {activeTab === 'live' && (
          <>
            {/* Scraper Search & Filter Panel */}
            <SearchPanel
              onStartScrape={handleStartScrape}
              onStopScrape={handleStopScrape}
              activeJob={activeJob}
              isScraping={isScraping}
            />

            {/* Scope reset banner if viewing a specific run */}
            {(currentJobId !== null || viewingJob !== null) && (
              <div className="mb-3 px-4 py-2 rounded-xl bg-dark-800 border border-dark-700 flex items-center justify-between text-xs">
                <span className="text-slate-300">
                  Showing leads for:{' '}
                  <strong className="text-emerald-400">
                    {viewingJob
                      ? `${viewingJob.query} in ${viewingJob.location}`
                      : `Current Extraction Run #${currentJobId}`}
                  </strong>
                </span>
                <button
                  type="button"
                  onClick={handleShowAllLeads}
                  className="px-2.5 py-1 rounded-lg bg-dark-700 hover:bg-dark-600 text-slate-200 border border-dark-600 transition-colors flex items-center gap-1 font-semibold"
                >
                  <RotateCcw className="w-3 h-3 text-slate-400" />
                  <span>Show All Past Leads</span>
                </button>
              </div>
            )}

            {/* Captured Leads Table */}
            <LeadTable
              leads={leads}
              loading={loadingLeads}
              currentJobTitle={currentTableTitle}
              onUpdateStatus={handleUpdateStatus}
              onDeleteLead={handleDeleteLead}
              onClearAll={handleClearAll}
              onSelectLead={(lead) => setSelectedLead(lead)}
              filterStatus={filterStatus}
              setFilterStatus={setFilterStatus}
              searchFilter={searchFilter}
              setSearchFilter={setSearchFilter}
            />
          </>
        )}

        {/* Tab 2: Search History & Archive Page */}
        {activeTab === 'history' && (
          <SearchHistory
            jobs={historyJobs}
            loading={loadingHistory}
            onSelectJob={handleSelectHistoryJob}
            onDeleteJob={handleDeleteHistoryJob}
            selectedJobId={currentJobId}
          />
        )}
      </main>

      {/* Modals */}
      <LeadDetailModal
        lead={selectedLead}
        onClose={() => setSelectedLead(null)}
        onSave={handleSaveLeadModal}
      />

      <TemplateModal
        isOpen={isTemplateModalOpen}
        onClose={() => setIsTemplateModalOpen(false)}
        currentTemplate={currentTemplate}
        onSaveTemplate={(tpl) => setCurrentTemplate(tpl)}
      />

      <ExportModal
        isOpen={isExportModalOpen}
        onClose={() => setIsExportModalOpen(false)}
        leads={leads}
      />

      {/* Footer */}
      <footer className="border-t border-dark-800 py-4 text-center text-xs text-slate-400">
        LeadFinder &bull; 100% Free Self-Hosted Google Maps B2B Lead Extractor
      </footer>
    </div>
  );
};

export default App;
