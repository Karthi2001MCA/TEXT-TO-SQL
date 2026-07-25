/**
 * Admin Page — system stats and audit logs (no authentication).
 */

import { useState, useEffect } from 'react';
import { adminAPI } from '../services/api';
import { SystemStats, AuditLog } from '../types';
import {
  Database, MessageSquare, TrendingUp,
  CheckCircle2, XCircle,
} from 'lucide-react';
import toast from 'react-hot-toast';

export default function AdminPage() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'logs'>('overview');

  useEffect(() => {
    loadAdmin();
  }, []);

  const loadAdmin = async () => {
    try {
      const [statsRes, logsRes] = await Promise.all([
        adminAPI.getStats(),
        adminAPI.getLogs(50),
      ]);
      setStats(statsRes.data);
      setLogs(logsRes.data.logs);
    } catch {
      toast.error('Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="loading-spinner lg" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Admin Panel</h1>
        <p className="page-subtitle">System monitoring and audit logs</p>
      </div>

      {stats && (
        <div className="stat-grid">
          <div className="card stat-card">
            <div className="flex items-center justify-between">
              <div><div className="stat-value">{stats.total_datasets}</div><div className="stat-label">Total Datasets</div></div>
              <div className="stat-icon cyan"><Database size={22} /></div>
            </div>
          </div>
          <div className="card stat-card">
            <div className="flex items-center justify-between">
              <div><div className="stat-value">{stats.total_queries}</div><div className="stat-label">Total Queries</div></div>
              <div className="stat-icon green"><MessageSquare size={22} /></div>
            </div>
          </div>
          <div className="card stat-card">
            <div className="flex items-center justify-between">
              <div><div className="stat-value">{stats.success_rate}%</div><div className="stat-label">Success Rate</div></div>
              <div className="stat-icon yellow"><TrendingUp size={22} /></div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        {(['overview', 'logs'] as const).map(tab => (
          <button
            key={tab}
            className={`btn ${activeTab === tab ? 'btn-primary' : 'btn-secondary'} btn-sm`}
            onClick={() => setActiveTab(tab)}
            style={{ textTransform: 'capitalize' }}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 'logs' && (
        <div className="card animate-fade-in">
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Question</th>
                  <th>Model</th>
                  <th>Confidence</th>
                  <th>Time (ms)</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log, i) => (
                  <tr key={i}>
                    <td>{log.is_successful ? <CheckCircle2 size={16} color="var(--accent-success)" /> : <XCircle size={16} color="var(--accent-danger)" />}</td>
                    <td style={{ maxWidth: 300 }}>{log.question}</td>
                    <td><span className="badge badge-primary">{log.model || '—'}</span></td>
                    <td>{log.confidence ? `${log.confidence.toFixed(0)}%` : '—'}</td>
                    <td>{log.execution_time_ms?.toFixed(0) || '—'}</td>
                    <td style={{ fontSize: 12 }}>{new Date(log.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'overview' && stats && (
        <div className="card animate-fade-in">
          <div className="card-title mb-4">System Health</div>
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between" style={{ padding: 14, background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
              <span>RAG Vector Index</span>
              <span className="badge badge-primary">{stats.rag_index.total_vectors} vectors</span>
            </div>
            <div className="flex items-center justify-between" style={{ padding: 14, background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
              <span>Embedding Model</span>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13 }}>{stats.rag_index.embedding_model}</span>
            </div>
            <div className="flex items-center justify-between" style={{ padding: 14, background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
              <span>Average Confidence</span>
              <span style={{ fontWeight: 700, color: 'var(--accent-primary)' }}>{stats.average_confidence}%</span>
            </div>
            <div className="flex items-center justify-between" style={{ padding: 14, background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)' }}>
              <span>Active LLM Providers</span>
              <span>{stats.llm_providers.filter((p: any) => p.is_available).length} / {stats.llm_providers.length}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
