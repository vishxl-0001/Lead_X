import React, { useState } from 'react';
import { X, MessageCircle, MapPin, Star, User, Globe, Flame, Phone, Save, ExternalLink } from 'lucide-react';
import { LeadItem } from '../types';

interface LeadDetailModalProps {
  lead: LeadItem | null;
  onClose: () => void;
  onSave: (leadId: number, update: { status?: LeadItem['status']; notes?: string; owner_name?: string }) => void;
}

export const LeadDetailModal: React.FC<LeadDetailModalProps> = ({ lead, onClose, onSave }) => {
  if (!lead) return null;

  const [status, setStatus] = useState<LeadItem['status']>(lead.status);
  const [ownerName, setOwnerName] = useState(lead.owner_name || '');
  const [notes, setNotes] = useState(lead.notes || '');

  const handleSave = () => {
    if (!lead.id) return;
    onSave(lead.id, {
      status,
      owner_name: ownerName.trim() || undefined,
      notes: notes.trim() || undefined,
    });
    onClose();
  };

  const phone = lead.phone_clean || lead.phone_raw;
  const mapsSearchUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
    `${lead.title} ${lead.address || lead.city || ''}`
  )}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-dark-800 border border-dark-700 w-full max-w-xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-5 border-b border-dark-700 flex items-center justify-between bg-dark-800/90">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">
              {lead.category || 'Lead Details'}
            </span>
            <h3 className="text-lg font-bold text-white tracking-tight">{lead.title}</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-dark-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4 overflow-y-auto text-xs text-slate-300">
          {/* Quick Badges Bar */}
          <div className="flex flex-wrap items-center gap-2">
            {!lead.has_website ? (
              <span className="px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 font-bold flex items-center gap-1">
                <Flame className="w-3.5 h-3.5" /> No Website (Hot Pitch)
              </span>
            ) : (
              <span className="px-2.5 py-1 rounded-full bg-slate-700/40 text-slate-300 border border-slate-600/30 flex items-center gap-1">
                <Globe className="w-3.5 h-3.5" /> Has Website: {lead.website_url}
              </span>
            )}

            {lead.rating && (
              <span className="px-2.5 py-1 rounded-full bg-dark-900 border border-dark-600 text-amber-400 font-bold flex items-center gap-1">
                <Star className="w-3.5 h-3.5 fill-current" />
                {lead.rating} ({lead.reviews_count || 0} reviews)
              </span>
            )}

            <a
              href={mapsSearchUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="px-2.5 py-1 rounded-full bg-dark-900 border border-dark-600 hover:border-slate-500 text-slate-300 flex items-center gap-1 transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5 text-blue-400" /> View on Google Maps
            </a>
          </div>

          {/* Contact & Location Info */}
          <div className="bg-dark-900/80 p-3.5 rounded-xl border border-dark-700 space-y-2">
            <div className="flex items-center space-x-2">
              <Phone className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span className="font-mono font-bold text-sm text-white">{phone || 'No phone'}</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 font-semibold border border-emerald-500/20">
                {lead.is_mobile ? 'Verified Mobile' : 'Landline / Inferred'}
              </span>
            </div>

            <div className="flex items-start space-x-2 pt-1 border-t border-dark-800 text-slate-400">
              <MapPin className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
              <span>{lead.address || lead.city || 'No address details'}</span>
            </div>
          </div>

          {/* Form Fields: Owner Name & Status */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-slate-400 mb-1 font-semibold flex items-center gap-1">
                <User className="w-3.5 h-3.5 text-amber-400" /> Owner / Contact Name
              </label>
              <input
                type="text"
                value={ownerName}
                onChange={(e) => setOwnerName(e.target.value)}
                placeholder="e.g. Ramesh Gupta"
                className="w-full px-3 py-2 rounded-xl bg-dark-900 border border-dark-600 text-white outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-slate-400 mb-1 font-semibold">CRM Outreach Status</label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as LeadItem['status'])}
                className="w-full px-3 py-2 rounded-xl bg-dark-900 border border-dark-600 text-white outline-none focus:border-emerald-500"
              >
                <option value="New">New</option>
                <option value="Contacted">Contacted</option>
                <option value="Interested">Interested</option>
                <option value="Closed">Closed</option>
                <option value="Disqualified">Disqualified</option>
              </select>
            </div>
          </div>

          {/* Notes textarea */}
          <div>
            <label className="block text-slate-400 mb-1 font-semibold">Call & Meeting Notes</label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g. Quoted ₹15,000 for 5-page business website with WhatsApp catalog..."
              className="w-full px-3 py-2 rounded-xl bg-dark-900 border border-dark-600 text-white outline-none focus:border-emerald-500 resize-none"
            />
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-dark-700 bg-dark-800 flex items-center justify-between">
          <div>
            {lead.whatsapp_link && (
              <a
                href={lead.whatsapp_link}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => setStatus('Contacted')}
                className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md shadow-emerald-600/30 transition-transform active:scale-95"
              >
                <MessageCircle className="w-4 h-4 fill-current" />
                <span>Launch WhatsApp Chat</span>
              </a>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-3.5 py-2 rounded-xl bg-dark-700 hover:bg-dark-600 text-slate-300 font-medium text-xs transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs shadow-md shadow-blue-600/20 transition-colors"
            >
              <Save className="w-4 h-4" />
              <span>Save Changes</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
