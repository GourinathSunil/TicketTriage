import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Layers, ListChecks, PlusCircle, BarChart3, Activity, ShieldCheck, RefreshCw } from 'lucide-react';

export default function Navbar({ config, serverStatus, onRefresh }) {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Triage Queue', icon: ListChecks },
    { path: '/submit', label: 'Submit Ticket', icon: PlusCircle },
    { path: '/analytics', label: 'Analytics & Models', icon: BarChart3 },
  ];

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-gray-800/80 bg-gray-950/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo & Domain Pack Badge */}
          <div className="flex items-center gap-4">
            <Link to="/" className="flex items-center gap-3 group">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
                <Layers className="w-5 h-5 text-white" />
              </div>
              <div>
                <span className="text-lg font-bold bg-gradient-to-r from-white via-gray-100 to-gray-400 bg-clip-text text-transparent">
                  TicketTriage
                </span>
                <span className="hidden sm:inline-block ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  ML + SLA
                </span>
              </div>
            </Link>

            {/* Active Domain Pill */}
            {config && (
              <div className="hidden md:flex items-center gap-1.5 px-3 py-1 rounded-full bg-gray-900 border border-gray-800 text-xs text-gray-300">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className="text-gray-400">Domain:</span>
                <span className="font-semibold text-gray-200">{config.display_name}</span>
                <span className="text-gray-500 font-mono text-[10px]">({config.domain})</span>
              </div>
            )}
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center gap-1 sm:gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/30 shadow-sm'
                      : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-gray-400'}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Server Status & Refresh */}
          <div className="flex items-center gap-3">
            {onRefresh && (
              <button
                onClick={onRefresh}
                title="Refresh Queue"
                className="p-2 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-800/60 transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            )}

            <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-gray-900/80 border border-gray-800 text-xs">
              <span
                className={`w-2 h-2 rounded-full ${
                  serverStatus === 'online'
                    ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]'
                    : 'bg-rose-500'
                }`}
              ></span>
              <span className="text-gray-400 font-mono hidden sm:inline">
                {serverStatus === 'online' ? 'Backend Ready' : 'Connecting...'}
              </span>
            </div>
          </div>

        </div>
      </div>
    </header>
  );
}
