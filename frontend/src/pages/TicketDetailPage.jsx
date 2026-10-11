import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Clock,
  Building,
  CheckCircle2,
  AlertTriangle,
  UserCheck,
  Send,
  Plus,
  Save,
  MessageSquare,
  Shield,
  Tag,
  Check,
} from 'lucide-react';
import api from '../api';
import PriorityBadge from '../components/PriorityBadge';
import StatusBadge from '../components/StatusBadge';
import LabelBadge from '../components/LabelBadge';
import CountdownTimer from '../components/CountdownTimer';

export default function TicketDetailPage({ config }) {
  const { id } = useParams();
  const navigate = useNavigate();

  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Correction state
  const [currentLabels, setCurrentLabels] = useState([]);
  const [selectedAddLabel, setSelectedAddLabel] = useState('');
  const [agentNotes, setAgentNotes] = useState('');
  const [savingCorrections, setSavingCorrections] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const fetchTicket = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getTicket(id);
      setTicket(data);
      const effective = data.effective_labels || data.predicted_labels || [];
      setCurrentLabels(effective);
    } catch (err) {
      console.error(err);
      setError(err.message || 'Failed to load ticket details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTicket();
  }, [id]);

  const handleAddLabel = () => {
    if (selectedAddLabel && !currentLabels.includes(selectedAddLabel)) {
      setCurrentLabels([...currentLabels, selectedAddLabel]);
      setSelectedAddLabel('');
    }
  };

  const handleRemoveLabel = (lbl) => {
    setCurrentLabels(currentLabels.filter((l) => l !== lbl));
  };

  const handleSaveCorrections = async () => {
    setSavingCorrections(true);
    setSaveSuccess(false);
    try {
      const updated = await api.patchTicket(id, {
        corrected_labels: currentLabels,
        agent_notes: agentNotes || undefined,
      });
      setTicket(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      alert('Failed to update labels: ' + err.message);
    } finally {
      setSavingCorrections(false);
    }
  };

  const handleToggleResponded = async () => {
    try {
      const updated = await api.patchTicket(id, {
        is_responded: !ticket.is_responded,
      });
      setTicket(updated);
    } catch (err) {
      alert('Error updating responded state: ' + err.message);
    }
  };

  const handleToggleResolved = async () => {
    try {
      const updated = await api.patchTicket(id, {
        is_resolved: !ticket.is_resolved,
      });
      setTicket(updated);
    } catch (err) {
      alert('Error updating resolved state: ' + err.message);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center">
        <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-gray-400 text-sm">Loading ticket #{id}...</p>
      </div>
    );
  }

  if (error || !ticket) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center text-rose-400">
        <AlertTriangle className="w-10 h-10 mx-auto mb-3" />
        <p>{error || 'Ticket not found'}</p>
        <button
          onClick={() => navigate('/')}
          className="mt-4 px-4 py-2 rounded-lg bg-gray-800 text-xs text-gray-200"
        >
          Back to Queue
        </button>
      </div>
    );
  }

  // Available labels that can be added
  const availableToAdd = (config?.labels || []).filter(
    (l) => !currentLabels.includes(l.id)
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      
      {/* Top Breadcrumb & Controls */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Triage Queue</span>
        </button>

        <div className="flex items-center gap-2">
          {/* Quick Respond Button */}
          <button
            onClick={handleToggleResponded}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border flex items-center gap-1.5 transition-all ${
              ticket.is_responded
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                : 'bg-indigo-600/20 text-indigo-300 border-indigo-500/40 hover:bg-indigo-600/30'
            }`}
          >
            <Check className="w-3.5 h-3.5" />
            <span>{ticket.is_responded ? 'Response Recorded' : 'Mark Responded'}</span>
          </button>

          {/* Quick Resolve Button */}
          <button
            onClick={handleToggleResolved}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold border flex items-center gap-1.5 transition-all ${
              ticket.is_resolved
                ? 'bg-emerald-600 text-white border-emerald-500'
                : 'bg-emerald-950/40 text-emerald-400 border-emerald-800/60 hover:bg-emerald-900/60'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{ticket.is_resolved ? 'Ticket Resolved' : 'Resolve Ticket'}</span>
          </button>
        </div>
      </div>

      {/* Main Ticket Banner Header */}
      <div className="glass-panel p-6 rounded-2xl border border-gray-800 space-y-3 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-3">
            <span className="font-mono text-sm font-bold text-indigo-400">{ticket.id}</span>
            <PriorityBadge priority={ticket.priority} priorities={config?.priorities} />
            <StatusBadge status={ticket.sla_status} isCompleted={ticket.is_resolved} />
            {ticket.needs_human_review && (
              <span className="px-2 py-0.5 rounded text-xs font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30 flex items-center gap-1">
                <UserCheck className="w-3.5 h-3.5" />
                <span>Needs Human Review</span>
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 text-xs text-gray-400">
            <span>Created: {new Date(ticket.created_at).toLocaleString()}</span>
            <span className="capitalize px-2 py-0.5 rounded bg-gray-900 border border-gray-800 font-semibold text-gray-300">
              Tier: {ticket.customer_tier}
            </span>
          </div>
        </div>

        <h1 className="text-xl sm:text-2xl font-bold text-white">{ticket.subject}</h1>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* Left Column: Ticket Body & ML Probabilities */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* Ticket Description Card */}
          <div className="glass-panel p-6 rounded-2xl border border-gray-800 space-y-4">
            <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-indigo-400" />
              <span>Ticket Description</span>
            </h2>
            <div className="p-4 rounded-xl bg-gray-900/90 border border-gray-800/80 text-sm text-gray-200 whitespace-pre-wrap font-sans leading-relaxed">
              {ticket.body}
            </div>
          </div>

          {/* Label Probabilities Breakdown */}
          <div className="glass-panel p-6 rounded-2xl border border-gray-800 space-y-4">
            <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
              <Shield className="w-4 h-4 text-indigo-400" />
              <span>Full ML Confidence Distribution</span>
            </h2>
            <div className="space-y-2">
              {Object.entries(ticket.label_probabilities || {})
                .sort(([, a], [, b]) => b - a)
                .map(([lbl, prob]) => {
                  const isEffective = currentLabels.includes(lbl);
                  const pct = Math.round(prob * 100);
                  const lblCfg = (config?.labels || []).find((l) => l.id === lbl);
                  const hexColor = lblCfg?.color || '#6366F1';
                  return (
                    <div key={lbl} className="space-y-1">
                      <div className="flex justify-between items-center text-xs">
                        <div className="flex items-center gap-2">
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: hexColor }}
                          ></span>
                          <span className={isEffective ? 'font-semibold text-white' : 'text-gray-400'}>
                            {lblCfg?.name || lbl}
                          </span>
                          {isEffective && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300">
                              Active
                            </span>
                          )}
                        </div>
                        <span className="font-mono text-gray-400 text-xs">{pct}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-gray-900 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${pct}%`,
                            backgroundColor: isEffective ? hexColor : '#4B5563',
                          }}
                        ></div>
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>

        </div>

        {/* Right Column: SLA Details, Routing, and Agent Corrections */}
        <div className="lg:col-span-5 space-y-6">
          
          {/* SLA Tracking Details Card */}
          <div className="glass-panel p-6 rounded-2xl border border-gray-800 space-y-4">
            <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-400" />
              <span>SLA & Routing Engine</span>
            </h2>

            <div className="grid grid-cols-2 gap-3 text-center">
              <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                <span className="text-[10px] text-gray-400 block mb-1">First Response Due</span>
                <div className="text-sm font-bold text-indigo-300 mb-1">
                  <CountdownTimer
                    dueDate={ticket.first_response_due}
                    isCompleted={ticket.is_responded}
                    completedAt={ticket.responded_at}
                  />
                </div>
                <span className="text-[10px] text-gray-500 font-mono">
                  Target: {ticket.first_response_minutes} min
                </span>
              </div>

              <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                <span className="text-[10px] text-gray-400 block mb-1">Resolution Due</span>
                <div className="text-sm font-bold text-indigo-300 mb-1">
                  <CountdownTimer
                    dueDate={ticket.resolution_due}
                    isCompleted={ticket.is_resolved}
                    completedAt={ticket.resolved_at}
                  />
                </div>
                <span className="text-[10px] text-gray-500 font-mono">
                  Target: {ticket.resolution_minutes} min
                </span>
              </div>
            </div>

            {/* Team Ownership */}
            <div className="p-3 rounded-xl bg-gray-900/80 border border-gray-800 space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-400 font-medium">Lead Routing Owner:</span>
                <span className="font-semibold text-gray-200">{ticket.primary_team}</span>
              </div>
              <div className="text-xs">
                <span className="text-gray-400 font-medium block mb-1">Assigned Teams:</span>
                <div className="flex flex-wrap gap-1">
                  {ticket.assigned_teams?.map((tm) => (
                    <span
                      key={tm}
                      className="px-2 py-0.5 rounded text-[11px] bg-gray-800 text-gray-300 border border-gray-700"
                    >
                      {tm}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Reasons / Rules that fired */}
            <div>
              <span className="text-[11px] font-semibold text-gray-400 block mb-1.5">
                Rules & Modifiers Applied:
              </span>
              <ul className="space-y-1 bg-gray-900/60 p-3 rounded-xl border border-gray-800 text-xs text-gray-300 list-disc list-inside">
                {ticket.reasons?.map((r, idx) => (
                  <li key={idx} className="leading-snug">
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Agent Label Corrections & Feedback Card */}
          <div className="glass-panel p-6 rounded-2xl border border-gray-800 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                <Tag className="w-4 h-4 text-indigo-400" />
                <span>Agent Label Corrections</span>
              </h2>
              {ticket.corrected_labels && (
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Corrected by Agent
                </span>
              )}
            </div>

            <p className="text-xs text-gray-400">
              Add or remove labels to correct model predictions. Saving updates the SLA routing in real
              time and records feedback to the training dataset.
            </p>

            {/* Active Label Chips */}
            <div className="flex flex-wrap gap-1.5 p-3 rounded-xl bg-gray-900 border border-gray-800 min-h-[48px]">
              {currentLabels.length > 0 ? (
                currentLabels.map((lbl) => (
                  <LabelBadge
                    key={lbl}
                    labelId={lbl}
                    labels={config?.labels}
                    showRemove={true}
                    onRemove={handleRemoveLabel}
                  />
                ))
              ) : (
                <span className="text-xs text-gray-500 italic">No labels selected</span>
              )}
            </div>

            {/* Add Label Dropdown */}
            {availableToAdd.length > 0 && (
              <div className="flex gap-2">
                <select
                  value={selectedAddLabel}
                  onChange={(e) => setSelectedAddLabel(e.target.value)}
                  className="flex-1 bg-gray-900 border border-gray-700 rounded-lg py-1.5 px-2.5 text-xs text-gray-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Select label to add...</option>
                  {availableToAdd.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleAddLabel}
                  disabled={!selectedAddLabel}
                  className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-xs font-semibold text-gray-200 border border-gray-700 flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add</span>
                </button>
              </div>
            )}

            {/* Agent Notes */}
            <div>
              <label className="block text-[11px] font-semibold text-gray-400 mb-1">
                Feedback Notes (Optional)
              </label>
              <textarea
                rows={2}
                value={agentNotes}
                onChange={(e) => setAgentNotes(e.target.value)}
                placeholder="Why was this label changed? (stored for retraining)"
                className="w-full p-2 bg-gray-900 border border-gray-700 rounded-lg text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-indigo-500 font-sans"
              />
            </div>

            {/* Save Button */}
            <button
              onClick={handleSaveCorrections}
              disabled={savingCorrections}
              className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-semibold text-white shadow-md shadow-indigo-600/30 transition-all flex items-center justify-center gap-2"
            >
              <Save className="w-3.5 h-3.5" />
              <span>{savingCorrections ? 'Saving & Re-evaluating SLA...' : 'Save Corrections & Update SLA'}</span>
            </button>

            {saveSuccess && (
              <div className="p-2.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs text-center flex items-center justify-center gap-1.5 animate-fadeIn">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>SLA re-evaluated and corrections saved!</span>
              </div>
            )}

          </div>

        </div>

      </div>

    </div>
  );
}
