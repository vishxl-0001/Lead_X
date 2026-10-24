import React, { useState } from 'react';
import { X, Download, FileSpreadsheet, Contact, Copy, Check, Filter } from 'lucide-react';
import { api } from '../services/api';
import { LeadItem } from '../types';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  leads: LeadItem[];
}

export const ExportModal: React.FC<ExportModalProps> = ({ isOpen, onClose, leads }) => {
  if (!isOpen) return null;

  const [noWebsiteOnly, setNoWebsiteOnly] = useState(false);
  const [mobileOnly, setMobileOnly] = useState(true);
  const [copiedNumbers, setCopiedNumbers] = useState(false);

  const filteredLeads = leads.filter((l) => {
    if (noWebsiteOnly && l.has_website) return false;
    if (mobileOnly && !l.is_mobile) return false;
    return true;
  });

  const handleCopyNumbers = () => {
    const numbers = filteredLeads
      .map((l) => l.phone_clean || l.phone_raw)
      .filter(Boolean)
      .join('\n');
    navigator.clipboard.writeText(numbers);
    setCopiedNumbers(true);
    setTimeout(() => setCopiedNumbers(false), 2000);
  };

  const csvUrl = api.getExportCsvUrl({ no_website_only: noWebsiteOnly, mobile_only: mobileOnly });
  const vcfUrl = api.getExportVcfUrl({ no_website_only: noWebsiteOnly, mobile_only: mobileOnly });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-dark-800 border border-dark-700 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-dark-700 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Download className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Export Lead Data</h3>
              <p className="text-xs text-slate-400">Download formatted files ready for CRM or phone sync.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-dark-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 text-xs text-slate-300">
          {/* Filter options for export */}
          <div className="bg-dark-900 p-3.5 rounded-xl border border-dark-700 space-y-2">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Filter className="w-3.5 h-3.5 text-emerald-400" /> Export Filters:
            </span>
            <div className="flex flex-col gap-2">
              <label className="flex items-center space-x-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={noWebsiteOnly}
                  onChange={(e) => setNoWebsiteOnly(e.target.checked)}
                  className="w-4 h-4 rounded border-dark-600 text-emerald-600 focus:ring-emerald-500 bg-dark-900"
                />
                <span className="text-slate-200">Export only Zero-Website leads</span>
              </label>
              <label className="flex items-center space-x-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={mobileOnly}
                  onChange={(e) => setMobileOnly(e.target.checked)}
                  className="w-4 h-4 rounded border-dark-600 text-emerald-600 focus:ring-emerald-500 bg-dark-900"
                />
                <span className="text-slate-200">Export only Verified Mobile / WhatsApp numbers</span>
              </label>
            </div>
            <div className="pt-2 border-t border-dark-800 text-slate-400 text-[11px]">
              Selected: <strong className="text-emerald-400">{filteredLeads.length}</strong> leads out of {leads.length}
            </div>
          </div>

          {/* Export Buttons Options */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* CSV Export */}
            <a
              href={csvUrl}
              download
              className="p-4 rounded-xl border border-dark-700 bg-dark-900/60 hover:bg-dark-700/60 hover:border-emerald-500/50 transition-all flex flex-col justify-between group"
            >
              <div>
                <FileSpreadsheet className="w-7 h-7 text-emerald-400 mb-2 group-hover:scale-110 transition-transform" />
                <h4 className="font-bold text-sm text-white">Excel / CSV (.csv)</h4>
                <p className="text-[11px] text-slate-400 mt-1">
                  Full dataset with owner names, address, ratings, and WhatsApp links.
                </p>
              </div>
              <span className="mt-3 inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400">
                Download CSV &rarr;
              </span>
            </a>

            {/* VCF Export */}
            <a
              href={vcfUrl}
              download
              className="p-4 rounded-xl border border-dark-700 bg-dark-900/60 hover:bg-dark-700/60 hover:border-blue-500/50 transition-all flex flex-col justify-between group"
            >
              <div>
                <Contact className="w-7 h-7 text-blue-400 mb-2 group-hover:scale-110 transition-transform" />
                <h4 className="font-bold text-sm text-white">Phone Contacts (.vcf)</h4>
                <p className="text-[11px] text-slate-400 mt-1">
                  Import directly into iPhone / Android. WhatsApp syncs contacts instantly!
                </p>
              </div>
              <span className="mt-3 inline-flex items-center gap-1 text-[11px] font-bold text-blue-400">
                Download VCF &rarr;
              </span>
            </a>
          </div>

          {/* Clipboard Copy Action */}
          <div className="pt-2">
            <button
              onClick={handleCopyNumbers}
              className="w-full py-2.5 px-4 rounded-xl bg-dark-700 hover:bg-dark-600 text-slate-200 font-semibold flex items-center justify-center space-x-2 transition-colors border border-dark-600 text-xs"
            >
              {copiedNumbers ? (
                <>
                  <Check className="w-4 h-4 text-emerald-400" />
                  <span className="text-emerald-400 font-bold">Copied {filteredLeads.length} Numbers to Clipboard!</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  <span>Copy Clean Numbers List to Clipboard</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-dark-700 bg-dark-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-dark-700 hover:bg-dark-600 text-slate-300 font-medium text-xs transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
