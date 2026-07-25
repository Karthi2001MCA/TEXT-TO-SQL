/**
 * Dashboard Page — overview with stats, recent queries, and system info.
 * (No authentication)
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadAPI, queryAPI, adminAPI } from '../services/api';
import { Dataset, QueryHistoryItem, LLMProvider } from '../types';
import {
  Database, MessageSquare, CheckCircle2, Cpu, Clock,
} from 'lucide-react';
import { motion } from 'framer-motion';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const [datasetsRes, historyRes, providersRes] = await Promise.all([
        uploadAPI.listDatasets(),
        queryAPI.getHistory(10),
        queryAPI.getProviders(),
      ]);
      setDatasets(datasetsRes.data.datasets);
      setHistory(historyRes.data);
      setProviders(providersRes.data.providers);

      try {
        const statsRes = await adminAPI.getStats();
        setStats(statsRes.data);
      } catch {}
    } catch (err) {
      console.error('Dashboard load error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="loading-spinner lg" />
        <div className="loading-text">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">
          Welcome to the AI Data Assistant! Here's your overview.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="stat-grid">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="card stat-card"
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="stat-value">{datasets.length}</div>
              <div className="stat-label">Datasets</div>
            </div>
            <div className="stat-icon purple"><Database size={22} /></div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card stat-card"
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="stat-value">{stats?.total_queries ?? history.length}</div>
              <div className="stat-label">Total Queries</div>
            </div>
            <div className="stat-icon cyan"><MessageSquare size={22} /></div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="card stat-card"
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="stat-value">
                {stats?.success_rate ? `${stats.success_rate}%` : `${history.filter(h => h.is_successful).length}`}
              </div>
              <div className="stat-label">{stats?.success_rate ? 'Success Rate' : 'Successful Queries'}</div>
            </div>
            <div className="stat-icon green"><CheckCircle2 size={22} /></div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card stat-card"
        >
          <div className="flex items-center justify-between">
            <div>
              <div className="stat-value">
                {providers.filter(p => p.is_available).length}
              </div>
              <div className="stat-label">Active LLMs</div>
            </div>
            <div className="stat-icon pink"><Cpu size={22} /></div>
          </div>
        </motion.div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* LLM Providers */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="card"
        >
          <div className="card-header">
            <div className="card-title">
              <Cpu size={18} style={{ display: 'inline', marginRight: 8 }} />
              LLM Providers
            </div>
          </div>
          <div className="flex flex-col gap-3">
            {providers.map((p, i) => (
              <div key={i} className="flex items-center justify-between" style={{
                padding: '10px 14px',
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-color)',
              }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{p.model}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-tertiary)', textTransform: 'uppercase' }}>
                    {p.provider}
                  </div>
                </div>
                <span className={`badge ${p.is_available ? 'badge-success' : 'badge-danger'}`}>
                  {p.is_available ? 'Online' : 'Offline'}
                </span>
              </div>
            ))}
            {providers.length === 0 && (
              <div className="empty-state">
                <div className="empty-state-text">No LLM providers configured</div>
              </div>
            )}
          </div>
        </motion.div>

        {/* Recent Queries */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card"
        >
          <div className="card-header">
            <div className="card-title">
              <Clock size={18} style={{ display: 'inline', marginRight: 8 }} />
              Recent Queries
            </div>
            <button className="btn btn-ghost btn-sm" onClick={() => navigate('/history')}>
              View All
            </button>
          </div>
          <div className="flex flex-col gap-2">
            {history.slice(0, 6).map((item, i) => (
              <div key={i} className="flex items-center gap-3" style={{
                padding: '10px 14px',
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-color)',
              }}>
                <span className={`badge ${item.is_successful ? 'badge-success' : 'badge-danger'}`}>
                  {item.is_successful ? '✓' : '✗'}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    fontSize: 13, fontWeight: 500,
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {item.question}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                    {item.confidence ? `${item.confidence.toFixed(0)}% confidence` : 'N/A'}
                    {' • '}
                    {item.execution_time_ms ? `${item.execution_time_ms.toFixed(0)}ms` : ''}
                  </div>
                </div>
              </div>
            ))}
            {history.length === 0 && (
              <div className="empty-state">
                <div className="empty-state-text">No queries yet. Go ask some questions!</div>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
