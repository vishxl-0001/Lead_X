import React, { useState } from 'react';
import {
  MessageCircle,
  Copy,
  Check,
  Star,
  MapPin,
  Globe,
  Flame,
  User,
  Trash2,
  ExternalLink,
  Search,
  Filter,
} from 'lucide-react';
import { LeadItem } from '../types';

interface LeadTableProps {
  leads: LeadItem[];
  loading: boolean;
  currentJobTitle?: string | null;
  onUpdateStatus: (leadId: number, status: LeadItem['status']) => void;
  onDeleteLead: (leadId: number) => void;
  onClearAll?: () => void;
  onSelectLead: (lead: LeadItem) => void;
  filterStatus: string;
  setFilterStatus: (s: string) => void;
  searchFilter: string;
  setSearchFilter: (s: string) => void;
}

export const LeadTable: React.FC<LeadTableProps> = ({
  leads,
  loading,
  currentJobTitle,
  onUpdateStatus,
  onDeleteLead,
  onClearAll,
  onSelectLead,
  filterStatus,
  setFilterStatus,
  searchFilter,
  setSearchFilter,
}) => {
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const handleCopy = (phone: string, id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(phone);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const getStatusBadge = (status: LeadItem['status']) => {
    switch (status) {
      case 'New':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      case 'Contacted':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'Interested':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'Closed':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      case 'Disqualified':
        return 'bg-slate-700/40 text-slate-400 border-slate-600/30';
      default:
        return 'bg-dark-700 text-slate-300';
    }
  };

  return (
    <div className="bg-dark-800 border border-dark-700 rounded-2xl shadow-xl overflow-hidden">
      {/* Table Header Controls */}
      <div className="p-4 sm:p-5 border-b border-dark-700 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-dark-800/90">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <span>{currentJobTitle ? currentJobTitle : 'Captured Leads'}</span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-dark-700 text-slate-300 border border-dark-600">
              {leads.length} Records
            </span>
          </h2>
          <p className="text-xs text-slate-400">
            Click &apos;Chat&apos; to instantly launch WhatsApp with pre-filled pitch.
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          {/* Search bar inside table */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder="Search leads, phone, area..."
              className="pl-9 pr-3.5 py-1.5 text-xs rounded-xl bg-dark-900 border border-dark-600 focus:border-emerald-500 text-white placeholder-slate-500 outline-none w-48 sm:w-64"
            />
          </div>

          {/* Status filter */}
          <div className="flex items-center space-x-1">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-2.5 py-1.5 text-xs rounded-xl bg-dark-900 border border-dark-600 text-slate-200 outline-none focus:border-emerald-500"
            >
              <option value="All">All Statuses</option>
              <option value="New">New</option>
              <option value="Contacted">Contacted</option>
              <option value="Interested">Interested</option>
              <option value="Closed">Closed</option>
              <option value="Disqualified">Disqualified</option>
            </select>
          </div>

          {onClearAll && leads.length > 0 && (
            <button
              onClick={onClearAll}
              title="Clear all leads from database"
              className="px-2.5 py-1.5 text-xs rounded-xl bg-dark-700/60 hover:bg-rose-600/20 text-slate-400 hover:text-rose-300 border border-dark-600 hover:border-rose-500/30 transition-colors flex items-center gap-1"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>
          )}
        </div>
      </div>

      {/* Table / List */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-dark-700 bg-dark-900/60 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
              <th className="py-3 px-4">Business & Owner</th>
              <th className="py-3 px-4">Category</th>
              <th className="py-3 px-4">Direct WhatsApp Phone</th>
              <th className="py-3 px-4">Rating</th>
              <th className="py-3 px-4">Web Presence</th>
              <th className="py-3 px-4">CRM Status</th>
              <th className="py-3 px-4 text-right">Quick Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-700/60 text-slate-200">
            {loading && leads.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-slate-400">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-2 border-emerald-500 border-t-transparent" />
                  <p className="mt-2 text-xs">Loading leads...</p>
                </td>
              </tr>
            ) : leads.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-16 text-center text-slate-400">
                  <Search className="w-12 h-12 mx-auto text-dark-600 mb-2" />
                  <p className="text-sm font-semibold text-slate-300">No leads found</p>
                  <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                    Try searching for a category (e.g. Electrician, Bakery, Plumber) and location above to start scraping.
                  </p>
                </td>
              </tr>
            ) : (
              leads.map((lead) => {
                const phone = lead.phone_clean || lead.phone_raw;
                return (
                  <tr
                    key={lead.id}
                    onClick={() => onSelectLead(lead)}
                    className="hover:bg-dark-700/40 transition-colors cursor-pointer group"
                  >
                    {/* Business Title & Owner */}
                    <td className="py-3 px-4">
                      <div className="font-bold text-white text-sm group-hover:text-emerald-400 transition-colors">
                        {lead.title}
                      </div>
                      <div className="flex items-center space-x-2 mt-0.5 text-slate-400">
                        {lead.owner_name && (
                          <span className="flex items-center gap-1 text-[11px] text-amber-300 font-medium bg-amber-500/10 px-1.5 py-0.2 rounded border border-amber-500/20">
                            <User className="w-3 h-3" />
                            {lead.owner_name} (Owner)
                          </span>
                        )}
                        <span className="flex items-center gap-0.5 text-[11px] text-slate-400 truncate max-w-[200px]">
                          <MapPin className="w-3 h-3 text-slate-500 flex-shrink-0" />
                          {lead.address || lead.city}
                        </span>
                      </div>
                    </td>

                    {/* Category */}
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded-md bg-dark-900 border border-dark-600 text-slate-300 text-[11px] font-medium">
                        {lead.category || 'Local Business'}
                      </span>
                    </td>

                    {/* Phone & WhatsApp status */}
                    <td className="py-3 px-4">
                      {phone ? (
                        <div className="flex items-center space-x-2">
                          <span className="font-mono text-slate-200 font-semibold">{phone}</span>
                          <button
                            type="button"
                            onClick={(e) => handleCopy(phone, lead.id!, e)}
                            title="Copy number"
                            className="p-1 rounded hover:bg-dark-600 text-slate-400 hover:text-white transition-colors"
                          >
                            {copiedId === lead.id ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      ) : (
                        <span className="text-slate-500 italic">No phone</span>
                      )}
                    </td>

                    {/* Rating */}
                    <td className="py-3 px-4">
                      {lead.rating ? (
                        <div className="flex items-center space-x-1">
                          <span className="flex items-center text-amber-400 font-bold">
                            <Star className="w-3.5 h-3.5 fill-current mr-0.5" />
                            {lead.rating}
                          </span>
                          <span className="text-slate-500 text-[11px]">
                            ({lead.reviews_count || 0})
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-500">Unrated</span>
                      )}
                    </td>

                    {/* Web Presence Badge */}
                    <td className="py-3 px-4">
                      {!lead.has_website ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          <Flame className="w-3 h-3" /> No Website
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-700/40 text-slate-400">
                          <Globe className="w-3 h-3" /> Has Website
                        </span>
                      )}
                    </td>

                    {/* CRM Status Dropdown */}
                    <td className="py-3 px-4" onClick={(e) => e.stopPropagation()}>
                      <select
                        value={lead.status}
                        onChange={(e) => onUpdateStatus(lead.id!, e.target.value as LeadItem['status'])}
                        className={`text-[11px] font-semibold px-2 py-1 rounded-lg border outline-none bg-dark-900 cursor-pointer ${getStatusBadge(
                          lead.status
                        )}`}
                      >
                        <option value="New">New</option>
                        <option value="Contacted">Contacted</option>
                        <option value="Interested">Interested</option>
                        <option value="Closed">Closed</option>
                        <option value="Disqualified">Disqualified</option>
                      </select>
                    </td>

                    {/* Action buttons */}
                    <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center justify-end space-x-2">
                        {lead.whatsapp_link ? (
                          <a
                            href={lead.whatsapp_link}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={() => onUpdateStatus(lead.id!, 'Contacted')}
                            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md shadow-emerald-600/30 transition-all hover:scale-105"
                          >
                            <MessageCircle className="w-3.5 h-3.5 fill-current" />
                            <span>Chat</span>
                          </a>
                        ) : null}

                        <button
                          type="button"
                          onClick={() => onDeleteLead(lead.id!)}
                          title="Delete Lead"
                          className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
