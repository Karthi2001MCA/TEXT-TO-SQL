/**
 * Upload Page — drag-and-drop Excel file upload with preview.
 */

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadAPI } from '../services/api';
import { Dataset } from '../types';
import { Upload, FileSpreadsheet, Check, X, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';

export default function UploadPage() {
  const [uploading, setUploading] = useState(false);
  const [uploadedDataset, setUploadedDataset] = useState<Dataset | null>(null);
  const [datasetName, setDatasetName] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setSelectedFile(acceptedFiles[0]);
      setDatasetName(acceptedFiles[0].name.replace(/\.[^.]+$/, ''));
      setUploadedDataset(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv'],
    },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024,
  });

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    try {
      const res = await uploadAPI.uploadExcel(selectedFile, datasetName);
      setUploadedDataset(res.data);
      toast.success(`Dataset "${res.data.name}" uploaded successfully!`);
      setSelectedFile(null);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const formatSize = (bytes: number | null) => {
    if (!bytes) return 'Unknown';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Upload Data</h1>
        <p className="page-subtitle">
          Upload Excel (.xlsx, .xls) or CSV files to create queryable SQL tables
        </p>
      </div>

      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={`upload-zone ${isDragActive ? 'active' : ''}`}
      >
        <input {...getInputProps()} id="file-upload-input" />
        <div className="upload-zone-icon">
          <Upload size={48} strokeWidth={1.5} color="var(--accent-primary)" />
        </div>
        <div className="upload-zone-title">
          {isDragActive ? 'Drop your file here' : 'Drag & drop your file here'}
        </div>
        <div className="upload-zone-subtitle">
          or click to browse • Supports .xlsx, .xls, .csv • Max 50MB
        </div>
      </div>

      {/* Selected File */}
      {selectedFile && !uploading && !uploadedDataset && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="card mt-4"
        >
          <div className="flex items-center gap-4 mb-4">
            <FileSpreadsheet size={24} color="var(--accent-success)" />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600 }}>{selectedFile.name}</div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                {formatSize(selectedFile.size)}
              </div>
            </div>
            <button className="btn btn-ghost btn-sm" onClick={() => setSelectedFile(null)}>
              <X size={16} />
            </button>
          </div>

          <div className="form-group">
            <label className="form-label">Dataset Name</label>
            <input
              id="dataset-name"
              type="text"
              className="form-input"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              placeholder="Give your dataset a name"
            />
          </div>

          <button
            id="upload-submit"
            className="btn btn-primary"
            onClick={handleUpload}
          >
            <Upload size={16} />
            Upload & Create Table
          </button>
        </motion.div>
      )}

      {/* Uploading */}
      {uploading && (
        <div className="card mt-4">
          <div className="loading-overlay">
            <Loader2 size={32} className="loading-spinner" color="var(--accent-primary)" />
            <div className="loading-text">Processing your file...</div>
          </div>
        </div>
      )}

      {/* Upload Success */}
      {uploadedDataset && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="card mt-4"
          style={{ borderColor: 'rgba(16, 185, 129, 0.3)' }}
        >
          <div className="flex items-center gap-3 mb-4">
            <Check size={24} color="var(--accent-success)" />
            <div className="card-title" style={{ color: 'var(--accent-success)' }}>
              Upload Successful!
            </div>
          </div>

          <div className="stat-grid">
            <div>
              <div className="stat-label">Table Name</div>
              <div style={{ fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", fontSize: 13 }}>
                {uploadedDataset.table_name}
              </div>
            </div>
            <div>
              <div className="stat-label">Rows</div>
              <div style={{ fontWeight: 700, fontSize: 20, color: 'var(--accent-primary)' }}>
                {uploadedDataset.row_count.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="stat-label">Columns</div>
              <div style={{ fontWeight: 700, fontSize: 20, color: 'var(--accent-tertiary)' }}>
                {uploadedDataset.column_count}
              </div>
            </div>
          </div>

          {uploadedDataset.columns_info && (
            <div className="data-table-wrapper mt-4">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Column</th>
                    <th>Type</th>
                    <th>Non-Null</th>
                    <th>Unique</th>
                    <th>Samples</th>
                  </tr>
                </thead>
                <tbody>
                  {uploadedDataset.columns_info.map((col: any, i: number) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 600 }}>{col.clean_name}</td>
                      <td><span className="badge badge-primary">{col.data_type}</span></td>
                      <td>{col.non_null_count}</td>
                      <td>{col.unique_count}</td>
                      <td style={{ maxWidth: 200 }}>{col.sample_values?.slice(0, 3).join(', ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </motion.div>
      )}
    </div>
  );
}
