import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Filter,
  AlertOctagon,
  Clock,
  CheckCircle,
  AlertTriangle,
  UserCheck,
  ChevronRight,
  RefreshCw,
  Building2,
  SlidersHorizontal,
} from 'lucide-react';
import api from '../api';
import PriorityBadge from '../components/PriorityBadge';
import StatusBadge from '../components/StatusBadge';
import LabelBadge from '../components/LabelBadge';
import CountdownTimer from '../components/CountdownTimer';

export default function QueuePage({ config }) {
  const navigate = useNavigate();
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedLabel, setSelectedLabel] = useState('');
  const [selectedPriority, setSelectedPriority] = useState('');
  const [selectedTeam, setSelectedTeam] = useState('');
  const [selectedTier, setSelectedTier] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [needsReviewOnly, setNeedsReviewOnly] = useState(false);

  const fetchTickets = async () => {
    setLoading(true);
    setError(null);
    try {
      const filters = {
        search: search || undefined,
        label: selectedLabel || undefined,
        priority: selectedPriority || undefined,
        team: selectedTeam || undefined,
        tier: selectedTier || undefined,
        sla_status: selectedStatus || undefined,
        needs_human_review: needsReviewOnly ? true : undefined,
      };
      const res = await api.getTickets(filters);
      setTickets(res.tickets || []);
    } catch (err) {
      console.error('Failed to load tickets', err);
      setError(err.message || 'Failed to fetch tickets');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, [selectedLabel, selectedPriority, selectedTeam, selectedTier, selectedStatus, needsReviewOnly]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchTickets();
  };

  const handleQuickRespond = async (e, ticketId) => {
    e.stopPropagation();
    try {
      await api.patchTicket(ticketId, { is_responded: true });
      fetchTickets();
    } catch (err) {
      alert('Error updating ticket: ' + err.message);
    }
  };

  const handleQuickResolve = async (e, ticketId) => {
    e.stopPropagation();
    try {
      await api.patchTicket(ticketId, { is_resolved: true });
      fetchTickets();
    } catch (err) {
      alert('Error resolving ticket: ' + err.message);
    }
  };

  // Quick summary stats
  const totalCount = tickets.length;
  const breachedCount = tickets.filter((t) => t.sla_status === 'breached' && !t.is_resolved).length;
  const atRiskCount = tickets.filter((t) => t.sla_status === 'at_risk' && !t.is_resolved).length;
  const reviewCount = tickets.filter((t) => t.needs_human_review).length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      
      {/* Top Banner / Summary KPI Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-card p-4 rounded-xl border border-gray-800">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
            <span>Total Tickets</span>
            <Clock className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white">{totalCount}</div>
        </div>

        <div className="glass-card p-4 rounded-xl border border-rose-900/30 bg-rose-950/10">
          <div className="flex items-center justify-between text-xs text-rose-300 mb-1">
            <span>SLA Breached</span>
            <AlertOctagon className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-rose-400">{breachedCount}</div>
        </div>

        <div className="glass-card p-4 rounded-xl border border-amber-900/30 bg-amber-950/10">
          <div className="flex items-center justify-between text-xs text-amber-300 mb-1">
            <span>At Risk (&gt;70% SLA)</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400">{atRiskCount}</div>
        </div>

        <div className="glass-card p-4 rounded-xl border border-purple-900/30 bg-purple-950/10">
          <div className="flex items-center justify-between text-xs text-purple-300 mb-1">
            <span>Needs Review</span>
            <UserCheck className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-purple-400">{reviewCount}</div>
        </div>
      </div>

      {/* Filter and Controls Header */}
      <div className="glass-panel p-5 rounded-2xl border border-gray-800 space-y-4">
        
        {/* Search Bar & Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
          <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-96">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search tickets by subject or body..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-gray-900 border border-gray-700/70 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </form>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <button
              onClick={() => {
                setSearch('');
                setSelectedLabel('');
                setSelectedPriority('');
                setSelectedTeam('');
                setSelectedTier('');
                setSelectedStatus('');
                setNeedsReviewOnly(false);
              }}
              className="px-3 py-2 rounded-lg bg-gray-800/80 hover:bg-gray-700 text-xs font-medium text-gray-300 transition-colors flex items-center gap-1.5"
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Reset Filters</span>
            </button>
            <button
              onClick={fetchTickets}
              className="px-3 py-2 rounded-lg bg-indigo-600/80 hover:bg-indigo-600 text-xs font-semibold text-white transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Dynamic Filter Selectors */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 pt-2 border-t border-gray-800/60">
          
          {/* Priority */}
          <div>
            <label className="block text-[11px] font-medium text-gray-400 mb-1">Priority</label>
            <select
              value={selectedPriority}
              onChange={(e) => setSelectedPriority(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-md py-1.5 px-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Priorities</option>
              {config?.priorities?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.id} - {p.name.split('-')[1]?.trim() || p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Status */}
          <div>
            <label className="block text-[11px] font-medium text-gray-400 mb-1">SLA Status</label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-md py-1.5 px-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Statuses</option>
              <option value="on_track">On Track</option>
              <option value="at_risk">At Risk</option>
              <option value="breached">Breached</option>
            </select>
          </div>

          {/* Label */}
          <div>
            <label className="block text-[11px] font-medium text-gray-400 mb-1">Label</label>
            <select
              value={selectedLabel}
              onChange={(e) => setSelectedLabel(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-md py-1.5 px-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Labels</option>
              {config?.labels?.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>

          {/* Team */}
          <div>
            <label className="block text-[11px] font-medium text-gray-400 mb-1">Team</label>
            <select
              value={selectedTeam}
              onChange={(e) => setSelectedTeam(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-md py-1.5 px-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="">All Teams</option>
              {config?.teams?.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>

          {/* Tier */}
          <div>
            <label className="block text-[11px] font-medium text-gray-400 mb-1">Customer Tier</label>
            <select
              value={selectedTier}
              onChange={(e) => setSelectedTier(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-md py-1.5 px-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-500 capitalize"
            >
              <option value="">All Tiers</option>
              {config?.customer_tiers?.map((tier) => (
                <option key={tier.id} value={tier.id}>
                  {tier.name}
                </option>
              ))}
            </select>
          </div>

          {/* Needs Review Toggle */}
          <div className="flex flex-col justify-end">
            <button
              type="button"
              onClick={() => setNeedsReviewOnly(!needsReviewOnly)}
              className={`w-full py-1.5 px-2 rounded-md text-xs font-medium border flex items-center justify-center gap-1.5 transition-all ${
                needsReviewOnly
                  ? 'bg-purple-600/20 text-purple-300 border-purple-500/50 shadow-sm'
                  : 'bg-gray-900 text-gray-400 border-gray-700 hover:text-gray-200'
              }`}
            >
              <UserCheck className="w-3.5 h-3.5" />
              <span>Needs Review</span>
            </button>
          </div>

        </div>
      </div>

      {/* Main Triage Queue Table */}
      <div className="glass-panel rounded-2xl border border-gray-800 overflow-hidden shadow-2xl">
        {loading ? (
          <div className="py-24 text-center">
            <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-400 text-sm">Loading support ticket queue...</p>
          </div>
        ) : error ? (
          <div className="py-16 text-center text-rose-400">
            <AlertOctagon className="w-8 h-8 mx-auto mb-2" />
            <p>{error}</p>
          </div>
        ) : tickets.length === 0 ? (
          <div className="py-20 text-center">
            <CheckCircle className="w-12 h-12 text-emerald-500/60 mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-gray-200">No tickets found</h3>
            <p className="text-gray-400 text-sm mt-1 max-w-sm mx-auto">
              No tickets matched your filter criteria or the triage queue is completely cleared!
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-300">
              <thead className="bg-gray-900/90 text-gray-400 text-xs uppercase tracking-wider font-semibold border-b border-gray-800">
                <tr>
                  <th className="py-3.5 px-4">Ticket</th>
                  <th className="py-3.5 px-3">Priority</th>
                  <th className="py-3.5 px-3">Predicted Labels</th>
                  <th className="py-3.5 px-3">Owner / Team</th>
                  <th className="py-3.5 px-3">Customer Tier</th>
                  <th className="py-3.5 px-3">SLA Status</th>
                  <th className="py-3.5 px-3">First Resp Due</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {tickets.map((t) => {
                  const effectiveLabels = t.effective_labels || t.predicted_labels || [];
                  return (
                    <tr
                      key={t.id}
                      onClick={() => navigate(`/tickets/${t.id}`)}
                      className="hover:bg-indigo-950/20 cursor-pointer transition-colors group"
                    >
                      {/* Ticket ID & Subject */}
                      <td className="py-3.5 px-4 max-w-xs sm:max-w-md">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-indigo-400 font-semibold">{t.id}</span>
                          {t.needs_human_review && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                              Review
                            </span>
                          )}
                          {t.is_resolved && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                              Resolved
                            </span>
                          )}
                        </div>
                        <p className="font-medium text-gray-200 mt-1 line-clamp-1 group-hover:text-indigo-200 transition-colors">
                          {t.subject}
                        </p>
                      </td>

                      {/* Priority */}
                      <td className="py-3.5 px-3 whitespace-nowrap">
                        <PriorityBadge priority={t.priority} priorities={config?.priorities} />
                      </td>

                      {/* Multi-Labels */}
                      <td className="py-3.5 px-3">
                        <div className="flex flex-wrap gap-1.5 max-w-xs">
                          {effectiveLabels.length > 0 ? (
                            effectiveLabels.map((lbl) => (
                              <LabelBadge key={lbl} labelId={lbl} labels={config?.labels} />
                            ))
                          ) : (
                            <span className="text-xs text-gray-500 italic">No labels</span>
                          )}
                        </div>
                      </td>

                      {/* Team */}
                      <td className="py-3.5 px-3 whitespace-nowrap">
                        <div className="flex items-center gap-1.5 text-xs text-gray-300 font-medium">
                          <Building2 className="w-3.5 h-3.5 text-gray-400" />
                          <span>{t.primary_team || 'Unassigned'}</span>
                        </div>
                      </td>

                      {/* Customer Tier */}
                      <td className="py-3.5 px-3 whitespace-nowrap">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider ${
                            t.customer_tier === 'enterprise'
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              : t.customer_tier === 'pro'
                              ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                              : 'bg-gray-800 text-gray-400 border border-gray-700'
                          }`}
                        >
                          {t.customer_tier}
                        </span>
                      </td>

                      {/* SLA Status Badge */}
                      <td className="py-3.5 px-3 whitespace-nowrap">
                        <StatusBadge status={t.sla_status} isCompleted={t.is_resolved} />
                      </td>

                      {/* Live SLA Countdown */}
                      <td className="py-3.5 px-3 whitespace-nowrap">
                        <CountdownTimer
                          dueDate={t.first_response_due}
                          isCompleted={t.is_responded}
                          completedAt={t.responded_at}
                        />
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2">
                          {!t.is_responded && (
                            <button
                              onClick={(e) => handleQuickRespond(e, t.id)}
                              className="px-2.5 py-1 rounded bg-gray-800 hover:bg-gray-700 text-xs text-gray-300 transition-colors"
                              title="Mark Responded"
                            >
                              Respond
                            </button>
                          )}
                          {!t.is_resolved && (
                            <button
                              onClick={(e) => handleQuickResolve(e, t.id)}
                              className="px-2.5 py-1 rounded bg-emerald-900/40 hover:bg-emerald-800/60 text-xs text-emerald-300 border border-emerald-700/50 transition-colors"
                              title="Resolve"
                            >
                              Resolve
                            </button>
                          )}
                          <ChevronRight className="w-4 h-4 text-gray-500 group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all" />
                        </div>
                      </td>

                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
