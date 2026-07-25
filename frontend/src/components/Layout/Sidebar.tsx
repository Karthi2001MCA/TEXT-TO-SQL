/**
 * Sidebar Component — navigation with icons (no auth).
 */

import { useNavigate, useLocation } from 'react-router-dom';
import {
  MessageSquare, Upload, Database, History, BarChart3,
  Settings, Shield, Sparkles,
} from 'lucide-react';

const navItems = [
  { label: 'Query', path: '/query', icon: MessageSquare },
  { label: 'Upload Data', path: '/upload', icon: Upload },
  { label: 'Datasets', path: '/datasets', icon: Database },
  { label: 'History', path: '/history', icon: History },
  { label: 'Dashboard', path: '/dashboard', icon: BarChart3 },
];

const adminItems = [
  { label: 'Admin Panel', path: '/admin', icon: Shield },
  { label: 'Settings', path: '/settings', icon: Settings },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Sparkles size={20} color="white" />
        </div>
        <span className="sidebar-logo-text">AI Data Assistant</span>
      </div>

      <nav className="sidebar-nav">
        <div className="sidebar-section-title">Main</div>
        {navItems.map(item => (
          <div
            key={item.path}
            className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
            onClick={() => navigate(item.path)}
          >
            <item.icon size={18} />
            <span>{item.label}</span>
          </div>
        ))}

        <div className="sidebar-section-title">System</div>
        {adminItems.map(item => (
          <div
            key={item.path}
            className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
            onClick={() => navigate(item.path)}
          >
            <item.icon size={18} />
            <span>{item.label}</span>
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-user-avatar">AI</div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">AI Data Assistant</div>
            <div className="sidebar-user-role">Enterprise Edition</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
