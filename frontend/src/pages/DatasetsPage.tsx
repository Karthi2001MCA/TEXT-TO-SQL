/**
 * Datasets Page — manage uploaded datasets with preview.
 */

import { useState, useEffect } from 'react';
import { uploadAPI } from '../services/api';
import { Dataset } from '../types';
import { Trash2, Eye, FileSpreadsheet } from 'lucide-react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [preview, setPreview] = useState<{ data: any; dataset: Dataset } | null>(null);

  useEffect(() => {
    loadDatasets();
  }, []);

  const loadDatasets = async () => {
    try {
      const res = await uploadAPI.listDatasets();
      setDatasets(res.data.datasets);
    } catch (err) {
      toast.error('Failed to load datasets');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Delete dataset "${name}"? This will drop the SQL table.`)) return;
    try {
      await uploadAPI.deleteDataset(id);
      toast.success('Dataset deleted');
      loadDatasets();
    } catch (err) {
      toast.error('Failed to delete dataset');
    }
  };

  const handlePreview = async (dataset: Dataset) => {
    try {
      const res = await uploadAPI.previewDataset(dataset.id, 20);
      setPreview({ data: res.data, dataset });
    } catch (err) {
      toast.error('Failed to load preview');
    }
  };

  const formatSize = (bytes: number | null) => {
    if (!bytes) return '—';
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (loading) {
    return (
      <div className="loading-overlay">
        <div className="loading-spinner lg" />
        <div className="loading-text">Loading datasets...</div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Datasets</h1>
        <p className="page-subtitle">Manage your uploaded datasets and SQL tables</p>
      </div>

      {datasets.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📁</div>
            <div className="empty-state-title">No Datasets</div>
            <div className="empty-state-text">Upload an Excel file to get started</div>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 20 }}>
          {datasets.map((ds, i) => (
            <motion.div
              key={ds.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="card"
            >
              <div className="flex items-center gap-3 mb-4">
                <FileSpreadsheet size={24} color="var(--accent-success)" />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 15 }}>{ds.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-tertiary)', fontFamily: "'JetBrains Mono', monospace" }}>
                    {ds.table_name}
                  </div>
                </div>
              </div>

              <div className="flex gap-4 mb-4" style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                <span>{ds.row_count.toLocaleString()} rows</span>
                <span>{ds.column_count} cols</span>
                <span>{formatSize(ds.file_size_bytes)}</span>
              </div>

              <div className="flex gap-2">
                <button className="btn btn-secondary btn-sm" onClick={() => handlePreview(ds)}>
                  <Eye size={14} /> Preview
                </button>
                <button className="btn btn-ghost btn-sm" onClick={() => handleDelete(ds.id, ds.name)}
                  style={{ color: 'var(--accent-danger)' }}>
                  <Trash2 size={14} /> Delete
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Preview Modal */}
      {preview && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          padding: 32,
        }} onClick={() => setPreview(null)}>
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="card"
            style={{ maxWidth: 900, width: '100%', maxHeight: '80vh', overflow: 'auto' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="card-header">
              <div className="card-title">Preview: {preview.dataset.name}</div>
              <button className="btn btn-ghost btn-sm" onClick={() => setPreview(null)}>✕</button>
            </div>
            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    {preview.data.columns.map((col: string) => (
                      <th key={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.data.rows.map((row: any, i: number) => (
                    <tr key={i}>
                      {preview.data.columns.map((col: string) => (
                        <td key={col}>{row[col] ?? '—'}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ padding: '12px 0', fontSize: 13, color: 'var(--text-tertiary)' }}>
              Showing {preview.data.rows.length} of {preview.data.total_rows} rows
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
