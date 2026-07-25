/**
 * History Page — query history with details.
 */

import { useState, useEffect } from 'react';
import { queryAPI } from '../services/api';
import { QueryHistoryItem } from '../types';
import { CheckCircle2, XCircle, Clock } from 'lucide-react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';

export default function HistoryPage() {
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const res = await queryAPI.getHistory(100);
      setHistory(res.data);
    } catch {
      toast.error('Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
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
        <h1 className="page-title">Query History</h1>
        <p className="page-subtitle">View past queries and their results</p>
      </div>

      {history.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📜</div>
            <div className="empty-state-title">No History</div>
            <div className="empty-state-text">Your query history will appear here</div>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {history.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03 }}
              className="card"
              style={{ padding: '16px 20px' }}
            >
              <div className="flex items-center gap-4">
                {item.is_successful ? (
                  <CheckCircle2 size={20} color="var(--accent-success)" />
                ) : (
                  <XCircle size={20} color="var(--accent-danger)" />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{item.question}</div>
                  {item.sql && (
                    <div style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 12,
                      color: 'var(--accent-tertiary)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      maxWidth: '600px',
                    }}>
                      {item.sql}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-3" style={{ flexShrink: 0 }}>
                  {item.confidence && (
                    <span className={`confidence-badge ${item.confidence >= 70 ? 'high' : item.confidence >= 40 ? 'medium' : 'low'}`}>
                      {item.confidence.toFixed(0)}%
                    </span>
                  )}
                  {item.row_count !== null && (
                    <span className="badge badge-primary">{item.row_count} rows</span>
                  )}
                  <span style={{ fontSize: 12, color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Clock size={12} />
                    {formatDate(item.created_at)}
                  </span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
