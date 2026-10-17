import React from 'react';
import { 
  LayoutDashboard, 
  Bell, 
  BarChart3, 
  UploadCloud, 
  Sliders, 
  Tv, 
  Sun, 
  Moon, 
  Wifi, 
  WifiOff 
} from 'lucide-react';

export default function Sidebar({ 
  currentTab, 
  setCurrentTab, 
  unreadAlertsCount = 0, 
  isOnline = true, 
  isDemoMode = false, 
  onToggleDemoMode, 
  theme = 'dark', 
  onToggleTheme 
}) {
  const navItems = [
    { id: 'dashboard', label: 'Live Dashboard', icon: LayoutDashboard },
    { id: 'alerts', label: 'Alerts', icon: Bell, badge: unreadAlertsCount },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'upload', label: 'Upload Video', icon: UploadCloud },
    { id: 'settings', label: 'Zones & Sources', icon: Sliders },
  ];

  return (
    <aside className="desktop-sidebar">
      <div>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem', padding: '0 0.5rem' }}>
          <div style={{ 
            width: '38px', 
            height: '38px', 
            borderRadius: '10px', 
            background: 'linear-gradient(135deg, #3b82f6, #06b6d4)', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center', 
            color: '#fff', 
            fontWeight: 800,
            boxShadow: '0 0 12px rgba(59, 130, 246, 0.4)'
          }}>
            AI
          </div>
          <div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 800, lineHeight: 1.1 }}>SmartShelf</h2>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Retail Monitor AI</span>
          </div>
        </div>

        {/* Navigation */}
        <nav>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <div
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`nav-link ${isActive ? 'active' : ''}`}
                style={{ position: 'relative' }}
              >
                <Icon size={18} />
                <span>{item.label}</span>
                {item.badge > 0 && (
                  <span style={{
                    marginLeft: 'auto',
                    background: 'var(--status-empty)',
                    color: '#fff',
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    borderRadius: '999px',
                    padding: '0.1rem 0.45rem',
                  }}>
                    {item.badge}
                  </span>
                )}
              </div>
            );
          })}
        </nav>
      </div>

      {/* Footer Controls: Demo Mode & System Status */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
        {/* Demo Mode Toggle */}
        <div style={{ 
          background: 'rgba(255, 255, 255, 0.04)', 
          padding: '0.75rem', 
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Tv size={16} color={isDemoMode ? '#10b981' : 'var(--text-muted)'} />
            <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>Demo Mode</span>
          </div>
          <button 
            onClick={onToggleDemoMode}
            className={`btn ${isDemoMode ? 'btn-primary' : 'btn-secondary'}`}
            style={{ minHeight: '28px', padding: '0.2rem 0.6rem', fontSize: '0.75rem' }}
          >
            {isDemoMode ? 'ON' : 'OFF'}
          </button>
        </div>

        {/* Theme and Connection */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 0.5rem' }}>
          <button 
            onClick={onToggleTheme} 
            className="btn btn-secondary"
            style={{ minHeight: '34px', padding: '0.35rem 0.6rem', borderRadius: 'var(--radius-full)' }}
            title="Toggle theme"
          >
            {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: isOnline ? 'var(--status-ok)' : 'var(--status-empty)' }}>
            {isOnline ? <Wifi size={14} /> : <WifiOff size={14} />}
            <span>{isOnline ? 'Connected' : 'Offline'}</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
