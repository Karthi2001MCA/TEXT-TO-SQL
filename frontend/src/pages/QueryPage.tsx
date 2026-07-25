/**
 * Query Page — the main natural language query interface.
 * Full experience: question input → SQL display → results table → chart → insights.
 */

import { useState } from 'react';
import { queryAPI } from '../services/api';
import { QueryResponse } from '../types';
import { Send, Copy, CheckCircle2, AlertTriangle, Sparkles, Table, Code2, BarChart3, Download } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';

export default function QueryPage() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'results' | 'sql' | 'models' | 'insights'>('results');

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!question.trim() || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await queryAPI.submitQuery(question.trim());
      setResult(res.data);
      setActiveTab('results');
      toast.success('Query executed successfully!');
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to execute query';
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const copySQL = () => {
    if (result?.sql) {
      navigator.clipboard.writeText(result.sql);
      toast.success('SQL copied to clipboard');
    }
  };

  const getConfidenceLevel = (score: number) => {
    if (score >= 70) return 'high';
    if (score >= 40) return 'medium';
    return 'low';
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Ask Your Data</h1>
        <p className="page-subtitle">
          Ask questions in plain English — AI will generate SQL, execute it, and show results
        </p>
      </div>

      {/* Query Input */}
      <form onSubmit={handleSubmit} className="query-container">
        <div className="query-input-wrapper">
          <input
            id="query-input"
            type="text"
            className="query-input"
            placeholder="e.g., Show me total sales by region for the last quarter..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            disabled={loading}
          />
          <button
            id="query-submit"
            type="submit"
            className="query-submit-btn"
            disabled={loading || !question.trim()}
          >
            {loading ? (
              <span className="loading-spinner" />
            ) : (
              <>
                <Send size={16} />
                Query
              </>
            )}
          </button>
        </div>
      </form>

      {/* Loading State */}
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="loading-overlay"
          >
            <div className="loading-spinner lg" />
            <div className="loading-text">
              Sending to multiple AI models in parallel...
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error State */}
      {error && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="card"
          style={{ borderColor: 'rgba(239, 68, 68, 0.3)' }}
        >
          <div className="flex items-center gap-3">
            <AlertTriangle size={20} color="var(--accent-danger)" />
            <div>
              <div style={{ fontWeight: 600, color: 'var(--accent-danger)' }}>Query Failed</div>
              <div style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4 }}>{error}</div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Results */}
      {result && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          {/* Confidence & Meta */}
          <div className="flex items-center gap-4 mb-6" style={{ flexWrap: 'wrap' }}>
            <span className={`confidence-badge ${getConfidenceLevel(result.confidence)}`}>
              <CheckCircle2 size={14} />
              {result.confidence.toFixed(1)}% Confidence
            </span>
            <span className="badge badge-primary">
              {result.results.row_count} rows
            </span>
            <span className="badge badge-primary">
              {result.execution_time_ms.toFixed(0)}ms
            </span>
            <span className="badge badge-success">
              {result.models.length} models queried
            </span>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mb-4">
            {[
              { key: 'results', label: 'Results', icon: Table },
              { key: 'sql', label: 'SQL', icon: Code2 },
              { key: 'models', label: 'Models', icon: BarChart3 },
              { key: 'insights', label: 'Insights', icon: Sparkles },
            ].map(tab => (
              <button
                key={tab.key}
                className={`btn ${activeTab === tab.key ? 'btn-primary' : 'btn-secondary'} btn-sm`}
                onClick={() => setActiveTab(tab.key as any)}
              >
                <tab.icon size={14} />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          {activeTab === 'results' && (
            <div className="card animate-fade-in">
              <div className="card-header">
                <div className="card-title">Query Results</div>
                <button className="btn btn-secondary btn-sm" onClick={copySQL}>
                  <Download size={14} />
                  Export
                </button>
              </div>
              {result.results.rows.length > 0 ? (
                <div className="data-table-wrapper">
                  <table className="data-table">
                    <thead>
                      <tr>
                        {result.results.columns.map(col => (
                          <th key={col}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.results.rows.slice(0, 100).map((row, i) => (
                        <tr key={i}>
                          {result.results.columns.map(col => (
                            <td key={col}>{row[col] ?? '—'}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty-state">
                  <div className="empty-state-icon">📊</div>
                  <div className="empty-state-title">No Data</div>
                  <div className="empty-state-text">The query returned no results</div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'sql' && (
            <div className="card animate-fade-in">
              <div className="sql-viewer">
                <div className="sql-header">
                  <span className="sql-header-title">Generated SQL</span>
                  <button className="btn btn-ghost btn-sm" onClick={copySQL}>
                    <Copy size={14} />
                    Copy
                  </button>
                </div>
                <pre className="sql-code">{result.sql}</pre>
              </div>
            </div>
          )}

          {activeTab === 'models' && (
            <div className="card animate-fade-in">
              <div className="card-title mb-4">Model Comparison</div>
              <div className="model-grid">
                {result.models.map((model, i) => (
                  <div
                    key={i}
                    className={`model-card ${i === 0 ? 'selected' : ''}`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="model-name">{model.model}</div>
                        <div className="model-provider">{model.provider}</div>
                      </div>
                      <span className={`badge ${model.is_valid ? 'badge-success' : 'badge-danger'}`}>
                        {model.is_valid ? 'Valid' : 'Invalid'}
                      </span>
                    </div>
                    <div className="model-score-bar">
                      <div
                        className="model-score-fill"
                        style={{ width: `${model.score}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between" style={{ fontSize: 12, color: 'var(--text-tertiary)' }}>
                      <span>Score: {model.score.toFixed(1)}</span>
                      <span>{model.latency_ms.toFixed(0)}ms</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'insights' && (
            <div className="insight-card animate-fade-in">
              <div className="insight-icon">
                <Sparkles size={20} color="white" />
              </div>
              <div className="card-title mb-4">AI Insights</div>
              {result.insights ? (
                <div className="insight-text">{result.insights}</div>
              ) : (
                <div className="empty-state">
                  <div className="empty-state-text">No insights generated for this query</div>
                </div>
              )}
            </div>
          )}
        </motion.div>
      )}

      {/* Empty State */}
      {!result && !loading && !error && (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">🤖</div>
            <div className="empty-state-title">Ready to Analyze</div>
            <div className="empty-state-text">
              Upload a dataset first, then ask questions in natural language.
              The AI will generate SQL, validate it across multiple models,
              and return the best result.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
