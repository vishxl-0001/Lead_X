import React, { useState } from 'react';
import { ShieldCheck, Lock, User, Eye, EyeOff, Loader2, AlertCircle, Sparkles, Server, Check } from 'lucide-react';
import { api } from '../services/api';

interface LoginScreenProps {
  onLoginSuccess: (username: string) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Backend connection configuration
  const [serverUrl, setServerUrl] = useState(() => api.getBackendUrl());
  const [showServerConfig, setShowServerConfig] = useState(false);
  const [serverSaved, setServerSaved] = useState(false);

  const handleSaveServer = (e: React.FormEvent) => {
    e.preventDefault();
    api.setBackendUrl(serverUrl);
    setServerSaved(true);
    setError(null);
    setTimeout(() => setServerSaved(false), 2000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError('Please enter both username and password.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await api.login(username.trim(), password.trim());
      onLoginSuccess(data.username);
    } catch (err: any) {
      setError(err.message || 'Invalid credentials or server unavailable.');
      if (err.message?.includes('404') || err.message?.includes('Cannot reach') || err.message?.includes('connect')) {
        setShowServerConfig(true);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center px-4 relative overflow-hidden select-none">
      {/* Background Neon Glows */}
      <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/3 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Main Card */}
      <div className="w-full max-w-md bg-slate-900/90 border border-slate-800 rounded-2xl shadow-2xl p-8 backdrop-blur-xl relative z-10">
        {/* Brand Icon & Heading */}
        <div className="flex flex-col items-center text-center mb-8">
          <div className="relative mb-3">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-emerald-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <ShieldCheck className="w-9 h-9 text-slate-950 stroke-[2.5]" />
            </div>
            <div className="absolute -bottom-1 -right-1 bg-slate-950 p-1 rounded-full border border-slate-800">
              <Sparkles className="w-4 h-4 text-emerald-400" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            Lead_X <span className="text-emerald-400 font-mono text-sm px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">ADMIN</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Enterprise B2B Lead Generator & WhatsApp Outreach
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-start gap-2.5 animate-in fade-in">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold mb-0.5">Authentication Error</p>
              <p className="text-xs text-rose-300/90 leading-relaxed">{error}</p>
            </div>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
              Admin Username
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <User className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter admin username"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-950/80 border border-slate-700/80 rounded-xl text-white placeholder-slate-500 text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all font-mono"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2">
              Security Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter admin password"
                className="w-full pl-10 pr-11 py-2.5 bg-slate-950/80 border border-slate-700/80 rounded-xl text-white placeholder-slate-500 text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all font-mono"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-200 transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 hover:from-emerald-400 hover:to-cyan-400 text-slate-950 font-bold text-sm shadow-lg shadow-emerald-500/25 transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Connecting to Server...</span>
              </>
            ) : (
              <>
                <Lock className="w-4 h-4" />
                <span>Unlock Lead_X Console</span>
              </>
            )}
          </button>
        </form>

        {/* Backend Server Configuration Toggle */}
        <div className="mt-6 pt-4 border-t border-slate-800/80">
          <button
            type="button"
            onClick={() => setShowServerConfig(!showServerConfig)}
            className="w-full flex items-center justify-between text-xs text-slate-400 hover:text-slate-300 py-1"
          >
            <span className="flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-cyan-400" />
              <span>Backend API Server</span>
            </span>
            <span className="text-[11px] text-emerald-400 underline">
              {showServerConfig ? 'Hide' : 'Configure Server'}
            </span>
          </button>

          {showServerConfig && (
            <div className="mt-3 p-3 rounded-xl bg-slate-950/90 border border-slate-800 text-xs animate-in fade-in space-y-2">
              <label className="block text-[11px] text-slate-300">
                Render Backend URL:
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={serverUrl}
                  onChange={(e) => setServerUrl(e.target.value)}
                  placeholder="https://lead-x-backend.onrender.com"
                  className="flex-1 px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-white font-mono text-xs focus:outline-none focus:border-cyan-500"
                />
                <button
                  type="button"
                  onClick={handleSaveServer}
                  className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-medium rounded-lg text-xs flex items-center gap-1"
                >
                  {serverSaved ? <Check className="w-3.5 h-3.5" /> : 'Save'}
                </button>
              </div>
              <p className="text-[10px] text-slate-400 leading-normal">
                Paste your live Render web service URL here if not set in Vercel.
              </p>
            </div>
          )}
        </div>

        <div className="mt-4 text-center">
          <p className="text-xs text-slate-500 flex items-center justify-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            Protected by HMAC-SHA256 Token Authentication
          </p>
        </div>
      </div>
    </div>
  );
};
