import React, { useState, useEffect, useRef } from 'react';
import {
  Search,
  MapPin,
  Play,
  Square,
  Loader2,
  Filter,
  ShieldCheck,
  Globe,
  Compass,
  Layers,
  ChevronRight,
  Target,
} from 'lucide-react';
import { ScrapeRequest, JobStatus, LocationSuggestion } from '../types';
import { api } from '../services/api';

interface SearchPanelProps {
  onStartScrape: (req: ScrapeRequest) => void;
  onStopScrape: () => void;
  activeJob: JobStatus | null;
  isScraping: boolean;
}

const QUICK_PROFESSIONS = [
  'Electrician',
  'Plumber',
  'Roofing Contractor',
  'HVAC & Air Conditioning',
  'Car Mechanic & Garage',
  'Bakery & Cafe',
  'Dental Clinic',
  'Real Estate Agency',
];

const RADIUS_OPTIONS = [
  { value: 5, label: '5 km (Neighborhood)' },
  { value: 10, label: '10 km (Local Area)' },
  { value: 25, label: '25 km (City-wide)' },
  { value: 50, label: '50 km (Metro Region)' },
  { value: 100, label: '100 km (Wide Region)' },
];

export const SearchPanel: React.FC<SearchPanelProps> = ({
  onStartScrape,
  onStopScrape,
  activeJob,
  isScraping,
}) => {
  const [query, setQuery] = useState('Electrician');
  const [locationInput, setLocationInput] = useState('Ontario, Canada');
  const [selectedCoords, setSelectedCoords] = useState<{ lat?: number; lon?: number }>({});
  const [radiusKm, setRadiusKm] = useState<number>(10);
  const [maxLeads, setMaxLeads] = useState<number>(25);
  const [noWebsiteOnly, setNoWebsiteOnly] = useState<boolean>(false);
  const [mobileOnly, setMobileOnly] = useState<boolean>(false);
  const [minRating, setMinRating] = useState<number>(0.0);

  // Suggestions state
  const [suggestions, setSuggestions] = useState<LocationSuggestion[]>([]);
  const [subAreas, setSubAreas] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState<boolean>(false);
  const [isSearchingLocation, setIsSearchingLocation] = useState<boolean>(false);

  const locationDebounceTimer = useRef<number | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Live Location Search as user types
  useEffect(() => {
    if (locationDebounceTimer.current) clearTimeout(locationDebounceTimer.current);

    if (locationInput.trim().length >= 2) {
      setIsSearchingLocation(true);
      locationDebounceTimer.current = window.setTimeout(async () => {
        try {
          const results = await api.searchLocations(locationInput);
          setSuggestions(results);
          setShowSuggestions(true);

          // Check for sub-areas if a major region/state was entered
          const areas = await api.getSubAreas(locationInput);
          setSubAreas(areas);
        } catch (e) {
          console.error('Location search error:', e);
        } finally {
          setIsSearchingLocation(false);
        }
      }, 300);
    } else {
      setSuggestions([]);
      setSubAreas([]);
      setIsSearchingLocation(false);
    }

    return () => {
      if (locationDebounceTimer.current) clearTimeout(locationDebounceTimer.current);
    };
  }, [locationInput]);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectLocation = async (s: LocationSuggestion) => {
    setLocationInput(s.display_name || s.name);
    setSelectedCoords({ lat: s.lat, lon: s.lon });
    setShowSuggestions(false);

    // Fetch specific sub-areas for this region (e.g. Toronto, Ottawa in Ontario)
    const areas = await api.getSubAreas(s.name || s.display_name);
    setSubAreas(areas);
  };

  const handleSelectSubArea = async (subArea: string) => {
    setLocationInput(subArea);
    setSubAreas([]);
    try {
      const geo = await api.searchLocations(subArea);
      if (geo && geo.length > 0) {
        setSelectedCoords({ lat: geo[0].lat, lon: geo[0].lon });
      }
    } catch {
      // Coordinates will be auto-resolved by backend
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || !locationInput.trim()) return;

    let lat = selectedCoords.lat;
    let lon = selectedCoords.lon;

    if (!lat || !lon) {
      try {
        const geo = await api.searchLocations(locationInput.trim());
        if (geo && geo.length > 0) {
          lat = geo[0].lat;
          lon = geo[0].lon;
          setSelectedCoords({ lat, lon });
        }
      } catch {
        // Coordinates will be auto-resolved by backend
      }
    }

    onStartScrape({
      query: query.trim(),
      location: locationInput.trim(),
      max_leads: maxLeads,
      radius_km: radiusKm,
      lat: lat,
      lon: lon,
      no_website_only: noWebsiteOnly,
      mobile_only: mobileOnly,
      min_rating: minRating,
    });
  };

  return (
    <div className="bg-dark-800 border border-dark-700 rounded-2xl p-5 mb-6 shadow-xl relative overflow-visible">
      {/* Background ambient glow */}
      <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Main Inputs: Profession, Location, Radius, Submit */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
          {/* 1. Profession / Category */}
          <div className="md:col-span-4 relative">
            <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center gap-1.5">
              <Search className="w-3.5 h-3.5 text-emerald-400" /> Profession / Category
            </label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Electrician, Plumber, Cafe, Auto Repair"
              required
              disabled={isScraping}
              className="w-full px-3.5 py-2.5 rounded-xl bg-dark-900 border border-dark-600 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 text-sm text-white placeholder-slate-500 transition-all outline-none"
            />
          </div>

          {/* 2. Global Location with Live Autocomplete */}
          <div className="md:col-span-5 relative" ref={dropdownRef}>
            <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-rose-400" /> Target Area / City (Anywhere on Earth)
              </span>
              {isSearchingLocation && (
                <span className="text-[10px] text-slate-400 flex items-center gap-1">
                  <Loader2 className="w-3 h-3 animate-spin text-emerald-400" /> Searching globe...
                </span>
              )}
            </label>

            <div className="relative">
              <input
                type="text"
                value={locationInput}
                onChange={(e) => {
                  setLocationInput(e.target.value);
                  setSelectedCoords({});
                }}
                onFocus={() => {
                  if (suggestions.length > 0) setShowSuggestions(true);
                }}
                placeholder="Type any state or city (e.g. Ontario, Tokyo, London, Sydney)"
                required
                disabled={isScraping}
                className="w-full px-3.5 py-2.5 rounded-xl bg-dark-900 border border-dark-600 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 text-sm text-white placeholder-slate-500 transition-all outline-none"
              />

              {/* Suggestions Dropdown */}
              {showSuggestions && suggestions.length > 0 && !isScraping && (
                <div className="absolute left-0 right-0 top-full mt-1.5 bg-dark-800 border border-dark-600 rounded-xl shadow-2xl z-50 max-h-60 overflow-y-auto divide-y divide-dark-700/60 animate-in fade-in duration-100">
                  <div className="px-3 py-1.5 bg-dark-900 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                    <span>Global Location Results</span>
                    <Globe className="w-3.5 h-3.5 text-emerald-400" />
                  </div>
                  {suggestions.map((s, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleSelectLocation(s)}
                      className="w-full px-3.5 py-2.5 text-left hover:bg-dark-700/80 flex items-start justify-between text-xs transition-colors group"
                    >
                      <div>
                        <p className="text-white font-medium group-hover:text-emerald-400 transition-colors">
                          {s.display_name}
                        </p>
                        <p className="text-[11px] text-slate-400">
                          {[s.city, s.state, s.country].filter(Boolean).join(', ')}
                        </p>
                      </div>
                      {s.country_code && (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-dark-900 border border-dark-600 text-slate-300">
                          {s.country_code}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 3. Search Radius Selector & Start Button */}
          <div className="md:col-span-3 flex items-end gap-2">
            <div className="w-32">
              <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center gap-1">
                <Target className="w-3 h-3 text-emerald-400" /> Radius
              </label>
              <select
                value={radiusKm}
                onChange={(e) => setRadiusKm(Number(e.target.value))}
                disabled={isScraping}
                className="w-full px-2.5 py-2.5 rounded-xl bg-dark-900 border border-dark-600 text-xs text-white outline-none focus:border-emerald-500 font-medium"
              >
                {RADIUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {isScraping ? (
              <button
                type="button"
                onClick={onStopScrape}
                className="flex-1 py-2.5 px-4 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-sm font-semibold flex items-center justify-center space-x-1.5 shadow-lg shadow-rose-600/30 transition-all"
              >
                <Square className="w-4 h-4 fill-current" />
                <span>Stop</span>
              </button>
            ) : (
              <button
                type="submit"
                className="flex-1 py-2.5 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white text-sm font-semibold flex items-center justify-center space-x-1.5 shadow-lg shadow-emerald-500/20 transition-all hover:shadow-emerald-500/30 active:scale-[0.98]"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>Find Leads</span>
              </button>
            )}
          </div>
        </div>

        {/* Dynamic Specific Sub-Area Drilldown (e.g. when typing "Ontario") */}
        {subAreas.length > 0 && !isScraping && (
          <div className="p-3 rounded-xl bg-dark-900/80 border border-emerald-500/30 animate-in fade-in duration-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                <Compass className="w-3.5 h-3.5" /> Specific Areas in {locationInput.split(',')[0]} (Click to target directly):
              </span>
              <span className="text-[10px] text-slate-400">Drill down to specific city</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {subAreas.map((area) => (
                <button
                  key={area}
                  type="button"
                  onClick={() => handleSelectSubArea(area)}
                  className="px-2.5 py-1 text-xs rounded-lg bg-dark-800 hover:bg-emerald-600 hover:text-white text-slate-200 border border-dark-600 hover:border-emerald-500 transition-all flex items-center gap-1 group"
                >
                  <span>{area}</span>
                  <ChevronRight className="w-3 h-3 text-slate-500 group-hover:text-white" />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Quick Profession Selector */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1 text-xs">
          <span className="text-slate-400 text-[11px] font-medium mr-1">Popular:</span>
          {QUICK_PROFESSIONS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setQuery(p)}
              disabled={isScraping}
              className="px-2.5 py-1 rounded-lg bg-dark-700/50 hover:bg-dark-700 text-slate-300 border border-dark-600/70 hover:border-emerald-500/50 transition-colors"
            >
              {p}
            </button>
          ))}
        </div>

        {/* Filters and Toggles Row */}
        <div className="pt-3 border-t border-dark-700/80 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-4">
            {/* Zero-Website Filter */}
            <label className="flex items-center space-x-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={noWebsiteOnly}
                onChange={(e) => setNoWebsiteOnly(e.target.checked)}
                disabled={isScraping}
                className="w-4 h-4 rounded border-dark-600 text-emerald-600 focus:ring-emerald-500 bg-dark-900"
              />
              <span className="text-slate-200 font-semibold flex items-center gap-1">
                Zero-Website Businesses Only
                <span className="px-1.5 py-0.2 text-[10px] bg-amber-500/20 text-amber-300 rounded font-bold border border-amber-500/30">
                  Hot Leads
                </span>
              </span>
            </label>

            {/* Mobile / Direct Phone Filter */}
            <label className="flex items-center space-x-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={mobileOnly}
                onChange={(e) => setMobileOnly(e.target.checked)}
                disabled={isScraping}
                className="w-4 h-4 rounded border-dark-600 text-emerald-600 focus:ring-emerald-500 bg-dark-900"
              />
              <span className="text-slate-200 font-medium flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                Mobile / WhatsApp Numbers Only
              </span>
            </label>

            {/* Max Leads Limit */}
            <div className="flex items-center space-x-1.5 text-slate-300">
              <span>Leads Limit:</span>
              <select
                value={maxLeads}
                onChange={(e) => setMaxLeads(Number(e.target.value))}
                disabled={isScraping}
                className="bg-dark-900 border border-dark-600 rounded-lg px-2 py-1 text-slate-200 outline-none"
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>

            {/* Min Rating */}
            <div className="flex items-center space-x-1.5 text-slate-300">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <span>Min Rating:</span>
              <select
                value={minRating}
                onChange={(e) => setMinRating(Number(e.target.value))}
                disabled={isScraping}
                className="bg-dark-900 border border-dark-600 rounded-lg px-2 py-1 text-slate-200 outline-none"
              >
                <option value={0.0}>Any</option>
                <option value={3.5}>3.5+ ⭐</option>
                <option value={4.0}>4.0+ ⭐</option>
                <option value={4.5}>4.5+ ⭐</option>
              </select>
            </div>
          </div>

          <div className="text-slate-400 text-[11px] flex items-center gap-1">
            <Globe className="w-3.5 h-3.5 text-emerald-400" />
            Global Reach: Search any country, state, city or radius
          </div>
        </div>
      </form>

      {/* Active Scraping Progress Card */}
      {isScraping && activeJob && (
        <div className="mt-4 pt-4 border-t border-emerald-500/30 bg-emerald-500/5 -mx-5 -mb-5 p-5">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2.5">
              <Loader2 className="w-5 h-5 text-emerald-400 animate-spin" />
              <div>
                <p className="text-sm font-bold text-white">
                  Extracting from Google Maps:{' '}
                  <span className="text-emerald-400">{activeJob.query}</span> in{' '}
                  <span className="text-slate-200">{activeJob.location}</span> ({radiusKm} km radius)
                </p>
                <p className="text-xs text-slate-400">
                  {activeJob.error_message || 'Connecting to live Google Maps search feed...'}
                </p>
              </div>
            </div>
            <div className="text-right">
              <span className="text-xs font-bold text-emerald-400">
                {activeJob.mobile_count} / {activeJob.target_count} Leads
              </span>
            </div>
          </div>

          <div className="w-full bg-dark-900 rounded-full h-2 overflow-hidden border border-dark-700">
            <div
              className="bg-gradient-to-r from-emerald-500 to-teal-400 h-2 rounded-full transition-all duration-300"
              style={{
                width: `${Math.min(
                  100,
                  Math.round((activeJob.mobile_count / (activeJob.target_count || 1)) * 100)
                )}%`,
              }}
            />
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2">
            <span>Listings Found: {activeJob.total_found}</span>
            <span>Zero-Website Qualified: {activeJob.no_website_count}</span>
            <span>Phone Numbers Extracted: {activeJob.mobile_count}</span>
          </div>
        </div>
      )}
    </div>
  );
};
