import React from 'react';
import { Users, Flame, PhoneCall, CheckCircle2, TrendingUp } from 'lucide-react';
import { StatsResponse } from '../types';

interface StatsOverviewProps {
  stats: StatsResponse | null;
  loading: boolean;
}

export const StatsOverview: React.FC<StatsOverviewProps> = ({ stats, loading }) => {
  const total = stats?.total_leads || 0;
  const noWeb = stats?.no_website_leads || 0;
  const mobile = stats?.mobile_leads || 0;
  const contacted = stats?.contacted_leads || 0;

  const noWebPercent = total > 0 ? Math.round((noWeb / total) * 100) : 0;
  const mobilePercent = total > 0 ? Math.round((mobile / total) * 100) : 0;

  const cards = [
    {
      label: 'Total Leads Scraped',
      value: total,
      subtext: `${stats?.total_jobs || 0} searches executed`,
      icon: Users,
      color: 'from-blue-500/20 to-indigo-500/10 border-blue-500/30 text-blue-400',
      badge: 'All Places',
    },
    {
      label: 'Zero-Website Leads',
      value: noWeb,
      subtext: `${noWebPercent}% of total (Hot Pitch Targets)`,
      icon: Flame,
      color: 'from-amber-500/20 to-orange-500/10 border-amber-500/30 text-amber-400',
      badge: 'Prime Leads 🔥',
    },
    {
      label: 'WhatsApp Ready Mobiles',
      value: mobile,
      subtext: `${mobilePercent}% verified mobile carriers`,
      icon: PhoneCall,
      color: 'from-emerald-500/20 to-teal-500/10 border-emerald-500/30 text-emerald-400',
      badge: 'Direct WhatsApp',
    },
    {
      label: 'Contacted Leads',
      value: contacted,
      subtext: 'Outreach pipeline active',
      icon: CheckCircle2,
      color: 'from-purple-500/20 to-pink-500/10 border-purple-500/30 text-purple-400',
      badge: 'CRM Tracking',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className={`p-4 rounded-xl border bg-gradient-to-br ${card.color} bg-dark-800/80 backdrop-blur-sm relative overflow-hidden shadow-lg transition-transform hover:-translate-y-0.5`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                {card.label}
              </span>
              <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-dark-900/60 border border-slate-700/50 text-slate-300">
                {card.badge}
              </span>
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-black text-white tracking-tight">
                {loading ? '...' : card.value.toLocaleString()}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
              <TrendingUp className="w-3.5 h-3.5 text-slate-500" />
              {card.subtext}
            </p>
          </div>
        );
      })}
    </div>
  );
};
