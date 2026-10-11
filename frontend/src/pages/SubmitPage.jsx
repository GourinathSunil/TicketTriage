import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Send,
  Sparkles,
  ShieldAlert,
  Clock,
  Building,
  CheckCircle2,
  FileText,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import api from '../api';
import PriorityBadge from '../components/PriorityBadge';
import LabelBadge from '../components/LabelBadge';

export default function SubmitPage({ config }) {
  const navigate = useNavigate();

  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [customerTier, setCustomerTier] = useState('enterprise');
  const [loadingPredict, setLoadingPredict] = useState(false);
  const [loadingSubmit, setLoadingSubmit] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);
  const [error, setError] = useState(null);

  // Quick Preset Sample Tickets for instant testing
  const presets = [
    {
      title: 'P1 Outage + Double Charge',
      tier: 'enterprise',
      subject: 'Checkout API returns 500 since this morning and we were charged twice',
      body: 'Our production users are receiving 500 Internal Server Error when accessing /v1/checkout/charge. Monitoring alerts fired 20 minutes ago. In addition, credit card statement shows customers were billed duplicate charges.',
    },
    {
      title: 'P1 Urgent SSO Lockout',
      tier: 'pro',
      subject: 'URGENT: Executive locked out of production tenant immediately',
      body: 'Our VP and organization administrators are completely locked out of the dashboard after MFA reset. Session returns 401 Unauthorized across all users. Immediate assistance required.',
    },
    {
      title: 'P2 Performance Latency',
      tier: 'pro',
      subject: 'API response times degraded to >5000ms on /api/v1/projects',
      body: 'Latency has spiked from 150ms to over 5 seconds during peak business hours. Queries are frequently timing out on dashboard load.',
    },
    {
      title: 'P2 GDPR Data Deletion',
      tier: 'free',
      subject: 'Formal GDPR Article 17 Right to Erasure request for account UUID #89201',
      body: 'Pursuant to GDPR Article 17, please delete all personally identifiable data associated with our workspace within 30 days and provide confirmation.',
    },
    {
      title: 'P3 API Webhook Issue',
      tier: 'free',
      subject: 'Webhook delivery failing with 429 Too Many Requests',
      body: 'Our webhook listener has stopped receiving events since yesterday. Delivery logs indicate premature rate limiting below our quota.',
    },
    {
      title: 'P4 Feature Request',
      tier: 'free',
      subject: 'Support for custom webhook payload signing with HMAC-SHA256',
      body: 'Would love to see native support for secret HMAC signing on outgoing payloads for additional verification security.',
    },
  ];

  const handleApplyPreset = (p) => {
    setSubject(p.subject);
    setBody(p.body);
    setCustomerTier(p.tier);
    setPredictionResult(null);
    setError(null);
  };

  const handlePredict = async () => {
    if (!subject.trim() || !body.trim()) {
      setError('Please provide both subject and body to evaluate.');
      return;
    }
    setLoadingPredict(true);
    setError(null);
    try {
      const res = await api.predict({
        subject,
        body,
        customer_tier: customerTier,
      });
      setPredictionResult(res);
    } catch (err) {
      console.error(err);
      setError(err.message || 'Prediction failed');
    } finally {
      setLoadingPredict(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!subject.trim() || !body.trim()) {
      setError('Please provide both subject and body.');
      return;
    }
    setLoadingSubmit(true);
    setError(null);
    try {
      const newTicket = await api.createTicket({
        subject,
        body,
        customer_tier: customerTier,
      });
      navigate(`/tickets/${newTicket.id}`);
    } catch (err) {
      console.error(err);
      setError(err.message || 'Ticket creation failed');
    } finally {
      setLoadingSubmit(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
          <Sparkles className="w-6 h-6 text-indigo-400" />
          <span>Intelligent Ticket Triage & SLA Simulator</span>
        </h1>
        <p className="text-gray-400 text-sm mt-1 max-w-2xl">
          Enter a support ticket or choose a sample scenario to instantly predict all relevant labels,
          evaluate the SLA priority, determine owning teams, and calculate response deadlines.
        </p>
      </div>

      {/* Quick Scenario Presets */}
      <div>
        <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Quick Test Presets (1-Click Fill)
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {presets.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleApplyPreset(p)}
              className="p-2.5 rounded-xl text-left bg-gray-900/80 hover:bg-indigo-950/40 border border-gray-800 hover:border-indigo-500/40 transition-all text-xs group"
            >
              <div className="font-semibold text-gray-200 group-hover:text-indigo-300 line-clamp-1">
                {p.title}
              </div>
              <div className="text-[10px] text-gray-500 mt-1 uppercase font-mono">
                Tier: {p.tier}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* Left Column: Form */}
        <div className="lg:col-span-7 glass-panel p-6 rounded-2xl border border-gray-800 space-y-5 shadow-xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            
            {/* Subject */}
            <div>
              <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
                Ticket Subject *
              </label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="e.g. Checkout API returns 500 since this morning"
                required
                className="w-full px-3.5 py-2.5 bg-gray-900 border border-gray-700/80 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>

            {/* Customer Tier */}
            <div>
              <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
                Customer Subscription Tier
              </label>
              <div className="grid grid-cols-3 gap-2">
                {config?.customer_tiers?.map((tier) => (
                  <button
                    key={tier.id}
                    type="button"
                    onClick={() => setCustomerTier(tier.id)}
                    className={`py-2 px-3 rounded-xl text-xs font-semibold border transition-all text-center capitalize ${
                      customerTier === tier.id
                        ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500 shadow-sm'
                        : 'bg-gray-900 text-gray-400 border-gray-800 hover:border-gray-700'
                    }`}
                  >
                    <div>{tier.name}</div>
                    <div className="text-[10px] text-gray-500 font-normal">
                      x{tier.deadline_multiplier} deadline
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Body */}
            <div>
              <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
                Ticket Body / Description *
              </label>
              <textarea
                rows={7}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Paste the user issue description, error logs, or request details..."
                required
                className="w-full px-3.5 py-2.5 bg-gray-900 border border-gray-700/80 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors font-sans"
              />
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center gap-3 pt-2">
              <button
                type="button"
                onClick={handlePredict}
                disabled={loadingPredict || !subject || !body}
                className="flex-1 py-2.5 px-4 rounded-xl bg-gray-800 hover:bg-gray-700 disabled:opacity-50 text-xs font-semibold text-gray-200 border border-gray-700 transition-all flex items-center justify-center gap-2"
              >
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <span>{loadingPredict ? 'Analyzing...' : 'Test Predict & SLA'}</span>
              </button>

              <button
                type="submit"
                disabled={loadingSubmit || !subject || !body}
                className="flex-1 py-2.5 px-4 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 disabled:opacity-50 text-xs font-semibold text-white shadow-lg shadow-indigo-600/30 transition-all flex items-center justify-center gap-2"
              >
                <Send className="w-4 h-4" />
                <span>{loadingSubmit ? 'Submitting...' : 'Submit into Queue'}</span>
              </button>
            </div>

          </form>
        </div>

        {/* Right Column: Live ML + SLA Prediction Card */}
        <div className="lg:col-span-5 space-y-4">
          <div className="glass-panel p-6 rounded-2xl border border-gray-800 shadow-xl space-y-5">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <h2 className="text-sm font-bold text-gray-200 uppercase tracking-wider flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-indigo-400" />
                <span>Live Triage Output</span>
              </h2>
              {predictionResult?.sla?.needs_human_review && (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  Needs Review
                </span>
              )}
            </div>

            {!predictionResult ? (
              <div className="py-12 text-center text-gray-500 text-xs space-y-2">
                <Sparkles className="w-8 h-8 text-indigo-400/30 mx-auto" />
                <p>Click "Test Predict & SLA" to simulate classification and routing for this ticket.</p>
              </div>
            ) : (
              <div className="space-y-4 text-xs">
                
                {/* Priority & Ownership */}
                <div className="p-3.5 rounded-xl bg-gray-900 border border-gray-800 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-gray-400 uppercase font-semibold block mb-1">
                      Assigned Priority
                    </span>
                    <PriorityBadge
                      priority={predictionResult.sla.priority}
                      priorities={config?.priorities}
                    />
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-gray-400 uppercase font-semibold block mb-1">
                      Primary Owner
                    </span>
                    <span className="font-semibold text-gray-200">
                      {predictionResult.sla.primary_team}
                    </span>
                  </div>
                </div>

                {/* Deadlines */}
                <div className="grid grid-cols-2 gap-2 text-center">
                  <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                    <span className="text-[10px] text-gray-400 block mb-0.5">First Response</span>
                    <span className="text-sm font-bold text-indigo-300">
                      {predictionResult.sla.first_response_minutes} min
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-gray-900 border border-gray-800">
                    <span className="text-[10px] text-gray-400 block mb-0.5">Resolution</span>
                    <span className="text-sm font-bold text-indigo-300">
                      {predictionResult.sla.resolution_minutes >= 1440
                        ? `${(predictionResult.sla.resolution_minutes / 1440).toFixed(1)} days`
                        : `${(predictionResult.sla.resolution_minutes / 60).toFixed(1)} hrs`}
                    </span>
                  </div>
                </div>

                {/* Predicted Multi-Labels */}
                <div>
                  <span className="text-[10px] text-gray-400 uppercase font-semibold block mb-2">
                    Multi-Label Classifications ({predictionResult.predicted_labels.length})
                  </span>
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {predictionResult.predicted_labels.length > 0 ? (
                      predictionResult.predicted_labels.map((lbl) => (
                        <LabelBadge key={lbl} labelId={lbl} labels={config?.labels} />
                      ))
                    ) : (
                      <span className="text-gray-500 italic">No labels exceeded threshold</span>
                    )}
                  </div>

                  {/* Top Probabilities Progress Bars */}
                  <div className="space-y-1.5 pt-2 border-t border-gray-800/60">
                    <span className="text-[10px] text-gray-500 block mb-1">Label Probabilities:</span>
                    {Object.entries(predictionResult.label_probabilities)
                      .sort(([, a], [, b]) => b - a)
                      .slice(0, 5)
                      .map(([lbl, prob]) => {
                        const isPred = predictionResult.predicted_labels.includes(lbl);
                        const pct = Math.round(prob * 100);
                        return (
                          <div key={lbl} className="space-y-0.5">
                            <div className="flex justify-between text-[11px]">
                              <span className={isPred ? 'text-indigo-300 font-semibold' : 'text-gray-400'}>
                                {lbl}
                              </span>
                              <span className="font-mono text-gray-400">{pct}%</span>
                            </div>
                            <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  isPred ? 'bg-indigo-500' : 'bg-gray-600'
                                }`}
                                style={{ width: `${pct}%` }}
                              ></div>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>

                {/* Assigned Teams */}
                <div>
                  <span className="text-[10px] text-gray-400 uppercase font-semibold block mb-1.5">
                    Routed Teams
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {predictionResult.sla.teams.map((tm) => (
                      <span
                        key={tm}
                        className={`px-2 py-0.5 rounded text-[11px] font-medium border ${
                          tm === predictionResult.sla.primary_team
                            ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40 font-semibold'
                            : 'bg-gray-800 text-gray-300 border-gray-700'
                        }`}
                      >
                        {tm} {tm === predictionResult.sla.primary_team && '(Lead)'}
                      </span>
                    ))}
                  </div>
                </div>

                {/* SLA Rules Reasoning */}
                <div>
                  <span className="text-[10px] text-gray-400 uppercase font-semibold block mb-1.5">
                    SLA Rule Explanation
                  </span>
                  <ul className="space-y-1 bg-gray-900/60 p-2.5 rounded-lg border border-gray-800 text-[11px] text-gray-300 list-disc list-inside">
                    {predictionResult.sla.reasons.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>

              </div>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
