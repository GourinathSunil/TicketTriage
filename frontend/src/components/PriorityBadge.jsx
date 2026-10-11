import React from 'react';
import { AlertCircle, AlertTriangle, Clock, Info } from 'lucide-react';

export default function PriorityBadge({ priority, priorities = [] }) {
  const pConfig = priorities.find((p) => p.id === priority);
  const color = pConfig?.color || '#3B82F6';
  const name = pConfig?.name || priority;

  const getPriorityStyle = (pId) => {
    switch (pId) {
      case 'P1':
        return 'bg-red-500/15 text-red-400 border-red-500/30';
      case 'P2':
        return 'bg-orange-500/15 text-orange-400 border-orange-500/30';
      case 'P3':
        return 'bg-blue-500/15 text-blue-400 border-blue-500/30';
      case 'P4':
        return 'bg-gray-500/15 text-gray-400 border-gray-500/30';
      default:
        return 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30';
    }
  };

  const getIcon = (pId) => {
    switch (pId) {
      case 'P1':
        return <AlertCircle className="w-3.5 h-3.5 text-red-400" />;
      case 'P2':
        return <AlertTriangle className="w-3.5 h-3.5 text-orange-400" />;
      case 'P3':
        return <Clock className="w-3.5 h-3.5 text-blue-400" />;
      default:
        return <Info className="w-3.5 h-3.5 text-gray-400" />;
    }
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold border ${getPriorityStyle(
        priority
      )}`}
      title={name}
    >
      {getIcon(priority)}
      <span>{priority}</span>
    </span>
  );
}
