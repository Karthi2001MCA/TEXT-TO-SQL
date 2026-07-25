/**
 * Settings Page — configure API keys and preferences.
 */

import { Key } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Configure your AI Data Assistant preferences</p>
      </div>

      <div className="card" style={{ maxWidth: 600 }}>
        <div className="card-title mb-4">
          <Key size={18} style={{ display: 'inline', marginRight: 8 }} />
          API Configuration
        </div>
        <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 24 }}>
          API keys are configured via environment variables on the backend.
          Contact your system administrator to update LLM provider keys.
        </p>

        <div style={{
          padding: 16,
          background: 'rgba(99, 102, 241, 0.08)',
          borderRadius: 'var(--radius-sm)',
          border: '1px solid rgba(99, 102, 241, 0.2)',
          fontSize: 13,
          color: 'var(--text-secondary)',
          lineHeight: 1.8,
        }}>
          <strong style={{ color: 'var(--accent-primary)' }}>Backend Configuration:</strong><br/>
          1. Copy <code style={{ color: 'var(--accent-tertiary)' }}>.env.example</code> to <code style={{ color: 'var(--accent-tertiary)' }}>.env</code><br/>
          2. Add your API keys (Gemini, Groq, DeepSeek)<br/>
          3. Restart the backend server<br/>
          4. Check Dashboard → LLM Providers for status
        </div>
      </div>
    </div>
  );
}
