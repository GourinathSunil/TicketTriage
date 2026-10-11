import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, Check } from 'lucide-react';

export default function StatusBadge({ status, isCompleted = false, label = null }) {
  if (isCompleted) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
        <Check className="w-3.5 h-3.5" />
        <span>{label || 'Met'}</span>
      </span>
    );
  }

  switch (status) {
    case 'breached':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse">
          <XCircle className="w-3.5 h-3.5 text-rose-400" />
          <span>{label || 'Breached'}</span>
        </span>
      );
    case 'at_risk':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          <span>{label || 'At Risk'}</span>
        </span>
      );
    case 'on_track':
    default:
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>{label || 'On Track'}</span>
        </span>
      );
  }
}
