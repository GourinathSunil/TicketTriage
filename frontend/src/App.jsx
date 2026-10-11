import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import QueuePage from './pages/QueuePage';
import SubmitPage from './pages/SubmitPage';
import TicketDetailPage from './pages/TicketDetailPage';
import AnalyticsPage from './pages/AnalyticsPage';
import api from './api';

export default function App() {
  const [config, setConfig] = useState(null);
  const [serverStatus, setServerStatus] = useState('connecting');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const loadConfigAndHealth = async () => {
    try {
      const [health, cfg] = await Promise.all([
        api.getHealth(),
        api.getConfig(),
      ]);
      setConfig(cfg);
      setServerStatus('online');
    } catch (err) {
      console.warn('Backend not responding yet:', err);
      setServerStatus('offline');
    }
  };

  useEffect(() => {
    loadConfigAndHealth();
    const interval = setInterval(loadConfigAndHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleManualRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
    loadConfigAndHealth();
  };

  return (
    <Router>
      <div className="min-h-screen bg-[#0B0F19] text-gray-100 flex flex-col font-sans selection:bg-indigo-500/30 selection:text-indigo-200">
        <Navbar
          config={config}
          serverStatus={serverStatus}
          onRefresh={handleManualRefresh}
        />

        <main className="flex-1 pb-16">
          <Routes>
            <Route
              path="/"
              element={<QueuePage key={refreshTrigger} config={config} />}
            />
            <Route
              path="/submit"
              element={<SubmitPage config={config} />}
            />
            <Route
              path="/tickets/:id"
              element={<TicketDetailPage config={config} />}
            />
            <Route
              path="/analytics"
              element={<AnalyticsPage config={config} />}
            />
          </Routes>
        </main>

        <footer className="border-t border-gray-800/80 bg-gray-950/60 py-6 text-xs text-gray-500 text-center">
          <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
            <div>
              <span className="font-semibold text-gray-400">TicketTriage</span> &bull; Domain Configurable ML Classifier &amp; SLA Routing Engine
            </div>
            {config && (
              <div className="flex items-center gap-2">
                <span>Active Domain:</span>
                <span className="px-2 py-0.5 rounded bg-gray-900 border border-gray-800 text-gray-300 font-mono">
                  {config.domain}
                </span>
              </div>
            )}
          </div>
        </footer>
      </div>
    </Router>
  );
}
