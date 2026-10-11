import React, { useState, useEffect } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from 'recharts';
import {
  BarChart3,
  TrendingUp,
  Cpu,
  Clock,
  ShieldAlert,
  AlertCircle,
  Award,
  Layers,
} from 'lucide-react';
import api from '../api';

export default function AnalyticsPage({ config }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchMetrics = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getMetrics();
        setMetrics(data);
      } catch (err) {
        console.error(err);
        setError(err.message || 'Failed to load analytics metrics');
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
  }, []);

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center">
        <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-gray-400 text-sm">Loading performance metrics and benchmarks...</p>
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center text-rose-400">
        <AlertCircle className="w-10 h-10 mx-auto mb-3" />
        <p>{error || 'Metrics not available'}</p>
      </div>
    );
  }

  const { sla_metrics, model_metrics, model_comparison } = metrics;

  // Prepare Chart Data
  // 1. Per-label F1 from model evaluation
  const perLabelF1Data = [];
  if (model_metrics?.evaluation?.per_label) {
    Object.entries(model_metrics.evaluation.per_label).forEach(([lbl, vals]) => {
      const lblConfig = config?.labels?.find((l) => l.id === lbl);
      perLabelF1Data.push({
        label: lblConfig?.name || lbl,
        rawLabel: lbl,
        f1: vals.f1,
        precision: vals.precision,
        recall: vals.recall,
        support: vals.support,
        color: lblConfig?.color || '#6366F1',
      });
    });
    perLabelF1Data.sort((a, b) => b.f1 - a.f1);
  }

  // 2. Tickets by Priority
  const priorityData = Object.entries(sla_metrics?.by_priority || {}).map(([pId, count]) => {
    const pCfg = config?.priorities?.find((p) => p.id === pId);
    return {
      priority: pId,
      name: pCfg?.name || pId,
      count,
      color: pCfg?.color || '#3B82F6',
    };
  });

  // 3. Tickets by Team
  const teamData = Object.entries(sla_metrics?.by_team || {}).map(([tId, count]) => {
    const tCfg = config?.teams?.find((t) => t.id === tId);
    return {
      team: tCfg?.name || tId,
      count,
    };
  }).sort((a, b) => b.count - a.count);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Title */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
          <BarChart3 className="w-6 h-6 text-indigo-400" />
          <span>Analytics & Model Evaluation Benchmarks</span>
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          Real-time SLA operational performance and held-out test evaluation benchmarks for active domain{' '}
          <span className="font-semibold text-gray-200">"{config?.display_name}"</span>.
        </p>
      </div>

      {/* Operational SLA KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        
        <div className="glass-card p-5 rounded-2xl border border-gray-800">
          <span className="text-xs text-gray-400 block mb-1">Total Triage Tickets</span>
          <div className="text-3xl font-extrabold text-white">{sla_metrics?.total_tickets || 0}</div>
          <div className="text-[11px] text-gray-500 mt-2">
            {sla_metrics?.active_tickets || 0} active, {sla_metrics?.resolved_tickets || 0} resolved
          </div>
        </div>

        <div className="glass-card p-5 rounded-2xl border border-rose-900/30 bg-rose-950/10">
          <span className="text-xs text-rose-300 block mb-1">SLA Breach Rate</span>
          <div className="text-3xl font-extrabold text-rose-400">
            {sla_metrics?.breach_rate_pct || 0}%
          </div>
          <div className="text-[11px] text-rose-300/70 mt-2">
            {sla_metrics?.breached_count || 0} overdue / breached tickets
          </div>
        </div>

        <div className="glass-card p-5 rounded-2xl border border-amber-900/30 bg-amber-950/10">
          <span className="text-xs text-amber-300 block mb-1">At Risk (&gt;70% elapsed)</span>
          <div className="text-3xl font-extrabold text-amber-400">
            {sla_metrics?.at_risk_count || 0}
          </div>
          <div className="text-[11px] text-amber-300/70 mt-2">Approaching response deadline</div>
        </div>

        <div className="glass-card p-5 rounded-2xl border border-purple-900/30 bg-purple-950/10">
          <span className="text-xs text-purple-300 block mb-1">Confidence Gate Reviews</span>
          <div className="text-3xl font-extrabold text-purple-400">
            {sla_metrics?.needs_review_count || 0}
          </div>
          <div className="text-[11px] text-purple-300/70 mt-2">Borderline or unassigned tickets</div>
        </div>

      </div>

      {/* ML Model Benchmark Comparison Table */}
      <div className="glass-panel p-6 rounded-2xl border border-gray-800 space-y-4 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-800 pb-3">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Award className="w-5 h-5 text-indigo-400" />
              <span>Multi-Label Model Architecture Comparison (Held-out Test Set)</span>
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Identical train/val/test splits with validation-tuned per-label decision thresholds.
            </p>
          </div>
          {model_metrics?.best_model_name && (
            <div className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold flex items-center gap-1.5 self-start sm:self-auto">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>Production: {model_metrics.best_model_name}</span>
            </div>
          )}
        </div>

        {model_comparison && model_comparison.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-gray-300">
              <thead className="bg-gray-900 text-gray-400 uppercase tracking-wider font-semibold border-b border-gray-800">
                <tr>
                  <th className="py-3 px-3">Model Architecture</th>
                  <th className="py-3 px-2">Macro F1</th>
                  <th className="py-3 px-2">Micro F1</th>
                  <th className="py-3 px-2">Subset Acc</th>
                  <th className="py-3 px-2">Hamming Loss</th>
                  <th className="py-3 px-2">Rare Labels F1</th>
                  <th className="py-3 px-2">Common F1</th>
                  <th className="py-3 px-2">Train Time</th>
                  <th className="py-3 px-2">Latency p50</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60 font-mono">
                {model_comparison.map((row, idx) => {
                  const isBest =
                    row.Model === model_metrics?.best_model_name ||
                    row.Model?.includes(model_metrics?.best_model_name);
                  return (
                    <tr
                      key={idx}
                      className={isBest ? 'bg-indigo-950/30 font-semibold text-white' : 'hover:bg-gray-900/40'}
                    >
                      <td className="py-3 px-3 font-sans flex items-center gap-2">
                        {isBest && <Award className="w-4 h-4 text-emerald-400 shrink-0" />}
                        <span>{row.Model}</span>
                      </td>
                      <td className="py-3 px-2 text-indigo-300">{row['Macro F1']}</td>
                      <td className="py-3 px-2">{row['Micro F1']}</td>
                      <td className="py-3 px-2">{row['Subset Accuracy']}</td>
                      <td className="py-3 px-2 text-gray-400">{row['Hamming Loss']}</td>
                      <td className="py-3 px-2 text-purple-300">{row['Rare Labels F1']}</td>
                      <td className="py-3 px-2">{row['Common Labels F1']}</td>
                      <td className="py-3 px-2 text-gray-400">{row['Train Time (s)']}s</td>
                      <td className="py-3 px-2 text-emerald-400">{row['Latency p50 (ms)']}ms</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-gray-500 text-xs">
            Model comparison table generating in background.
          </div>
        )}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Per-Label F1 Performance */}
        {perLabelF1Data.length > 0 && (
          <div className="glass-panel p-6 rounded-2xl border border-gray-800 space-y-4 shadow-xl">
            <h3 className="text-sm font-bold text-gray-200 uppercase tracking-wider flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-indigo-400" />
              <span>Per-Label F1 Score (Held-Out Test Set)</span>
            </h3>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={perLabelF1Data} layout="vertical" margin={{ top: 5, right: 30, left: 40, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
                  <XAxis type="number" domain={[0, 1]} tick={{ fill: '#9ca3af', fontSize: 10 }} />
                  <YAxis type="category" dataKey="label" tick={{ fill: '#d1d5db', fontSize: 11 }} width={130} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '0.5rem' }}
                    itemStyle={{ color: '#e5e7eb', fontSize: '12px' }}
                    formatter={(val) => [`${(val * 100).toFixed(1)}%`, 'F1 Score']}
                  />
                  <Bar dataKey="f1" radius={[0, 4, 4, 0]}>
                    {perLabelF1Data.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Tickets by Priority */}
        <div className="glass-panel p-6 rounded-2xl border border-gray-800 space-y-4 shadow-xl">
          <h3 className="text-sm font-bold text-gray-200 uppercase tracking-wider flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-indigo-400" />
            <span>Ticket Volume by Priority</span>
          </h3>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={priorityData} margin={{ top: 20, right: 20, left: 0, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis dataKey="priority" tick={{ fill: '#d1d5db', fontSize: 12 }} />
                <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '0.5rem' }}
                  itemStyle={{ color: '#e5e7eb', fontSize: '12px' }}
                  formatter={(val) => [val, 'Tickets']}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {priorityData.map((entry, index) => (
                    <Cell key={`p-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Tickets by Team */}
        <div className="glass-panel p-6 rounded-2xl border border-gray-800 space-y-4 shadow-xl lg:col-span-2">
          <h3 className="text-sm font-bold text-gray-200 uppercase tracking-wider flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            <span>Tickets Routed by Owning Team</span>
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={teamData} margin={{ top: 10, right: 30, left: 20, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" vertical={false} />
                <XAxis dataKey="team" tick={{ fill: '#d1d5db', fontSize: 11 }} angle={-15} textAnchor="end" />
                <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '0.5rem' }}
                  itemStyle={{ color: '#e5e7eb', fontSize: '12px' }}
                />
                <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

    </div>
  );
}
