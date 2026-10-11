import React, { useState, useEffect } from 'react';
import { Clock, AlertCircle } from 'lucide-react';

export default function CountdownTimer({ dueDate, isCompleted = false, completedAt = null }) {
  const [timeText, setTimeText] = useState('');
  const [isOverdue, setIsOverdue] = useState(false);

  useEffect(() => {
    if (!dueDate) return;

    const updateTimer = () => {
      const target = new Date(dueDate).getTime();
      const ref = isCompleted && completedAt ? new Date(completedAt).getTime() : Date.now();
      const diff = target - ref;

      if (diff <= 0) {
        setIsOverdue(true);
        const overdueMs = Math.abs(diff);
        const mins = Math.floor(overdueMs / 60000);
        const hrs = Math.floor(mins / 60);
        const remMins = mins % 60;
        if (hrs > 0) {
          setTimeText(`-${hrs}h ${remMins}m`);
        } else {
          setTimeText(`-${mins}m`);
        }
      } else {
        setIsOverdue(false);
        const mins = Math.floor(diff / 60000);
        const hrs = Math.floor(mins / 60);
        const remMins = mins % 60;
        if (hrs > 24) {
          const days = Math.floor(hrs / 24);
          setTimeText(`${days}d ${hrs % 24}h`);
        } else if (hrs > 0) {
          setTimeText(`${hrs}h ${remMins}m`);
        } else {
          setTimeText(`${mins}m`);
        }
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, [dueDate, isCompleted, completedAt]);

  if (isCompleted) {
    return (
      <span className="text-xs text-gray-400 font-mono flex items-center gap-1">
        <Clock className="w-3 h-3 text-emerald-400" />
        <span>Completed</span>
      </span>
    );
  }

  return (
    <span
      className={`text-xs font-mono font-medium flex items-center gap-1 ${
        isOverdue ? 'text-rose-400 font-semibold' : 'text-gray-300'
      }`}
    >
      <Clock className={`w-3.5 h-3.5 ${isOverdue ? 'text-rose-400' : 'text-gray-400'}`} />
      <span>{timeText || 'calculating...'}</span>
    </span>
  );
}
