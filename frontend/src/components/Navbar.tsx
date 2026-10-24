import React from 'react';
import { Target, History, MessageSquareCode, Download, Sparkles } from 'lucide-react';

interface NavbarProps {
  activeTab: 'live' | 'history';
  onChangeTab: (tab: 'live' | 'history') => void;
  historyCount: number;
  onOpenTemplate: () => void;
  onOpenExport: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onChangeTab,
  historyCount,
  onOpenTemplate,
  onOpenExport,
}) => {
  return (
    <header className="border-b border-dark-700 bg-dark-800/80 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20 text-white font-bold">
            <Target className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-lg text-white tracking-tight">LeadFinder</span>
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <Sparkles className="w-3 h-3" /> Global B2B
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">
              Direct Google Maps & WhatsApp Owner Extractor
            </p>
          </div>
        </div>

        {/* Center Navigation Tabs: Live Finder vs History */}
        <div className="flex items-center p-1 rounded-xl bg-dark-900 border border-dark-700">
          <button
            type="button"
            onClick={() => onChangeTab('live')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeTab === 'live'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
                : 'text-slate-400 hover:text-white hover:bg-dark-800'
            }`}
          >
            <Target className="w-3.5 h-3.5" />
            <span>Current Extraction</span>
          </button>

          <button
            type="button"
            onClick={() => onChangeTab('history')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              activeTab === 'history'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
                : 'text-slate-400 hover:text-white hover:bg-dark-800'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            <span>Search History</span>
            {historyCount > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-dark-800 text-emerald-300 font-bold border border-dark-700">
                {historyCount}
              </span>
            )}
          </button>
        </div>

        {/* Right Action buttons */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          <button
            onClick={onOpenTemplate}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-dark-600 bg-dark-700/60 hover:bg-dark-600 text-xs font-medium text-slate-300 transition-colors shadow-sm"
          >
            <MessageSquareCode className="w-4 h-4 text-emerald-400" />
            <span className="hidden sm:inline">Outreach Pitch</span>
          </button>

          <button
            onClick={onOpenExport}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-all shadow-md shadow-emerald-600/20"
          >
            <Download className="w-4 h-4" />
            <span>Export</span>
          </button>
        </div>
      </div>
    </header>
  );
};
