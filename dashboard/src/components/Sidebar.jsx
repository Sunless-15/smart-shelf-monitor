import React, { useState } from 'react';
import { 
  LayoutDashboard, 
  Bell, 
  BarChart3, 
  UploadCloud, 
  Sliders, 
  Tv, 
  Sun, 
  Moon, 
  ChevronLeft,
  ChevronDown,
  ChevronRight,
  Plus,
  Layers,
  Sparkles
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
  const [overviewOpen, setOverviewOpen] = useState(true);

  return (
    <aside className="sidebar-floating">
      <div>
        {/* Brand Header with Round Lime Collapse Button */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between', 
          marginBottom: '26px',
          padding: '0 4px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ 
              fontSize: '1.35rem', 
              fontWeight: 800, 
              letterSpacing: '-0.04em',
              color: '#FFFFFF'
            }}>
              shelf<span style={{ color: 'var(--accent-lime)' }}>sense</span>
            </span>
          </div>

          <button 
            className="btn-round-action btn-round-lime"
            style={{ width: '28px', height: '28px', padding: 0 }}
            title="Collapse Sidebar"
          >
            <ChevronLeft size={16} strokeWidth={2.8} />
          </button>
        </div>

        {/* Navigation Section */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {/* Home Nav Item */}
          <div 
            onClick={() => setCurrentTab('dashboard')}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              padding: '10px 14px',
              borderRadius: 'var(--radius-pill)',
              color: currentTab === 'dashboard' && !overviewOpen ? 'var(--accent-lime)' : 'var(--text-secondary)',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              fontSize: '0.9rem',
              fontWeight: 600
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <LayoutDashboard size={18} />
              <span>Home</span>
            </div>
            <Plus size={15} style={{ opacity: 0.6 }} />
          </div>

          {/* Overview Group (Expandable with White Rounded Active Card) */}
          <div style={{ marginTop: '2px' }}>
            <div 
              onClick={() => setOverviewOpen(!overviewOpen)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                borderRadius: 'var(--radius-pill)',
                color: '#FFFFFF',
                cursor: 'pointer',
                fontSize: '0.9rem',
                fontWeight: 600
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Layers size={18} />
                <span>Overview</span>
              </div>
              <span style={{ fontSize: '1.1rem', fontWeight: 700, lineHeight: 0.5, opacity: 0.7 }}>
                {overviewOpen ? '—' : '+'}
              </span>
            </div>

            {/* Sub-items Container inside Overview */}
            {overviewOpen && (
              <div style={{
                background: '#202020',
                borderRadius: '18px',
                padding: '6px',
                marginTop: '6px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px'
              }}>
                {/* Active Sub-item in solid white card */}
                <div 
                  onClick={() => setCurrentTab('dashboard')}
                  style={{
                    background: currentTab === 'dashboard' ? '#FFFFFF' : 'transparent',
                    color: currentTab === 'dashboard' ? '#000000' : 'var(--text-secondary)',
                    borderRadius: '14px',
                    padding: '9px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    fontWeight: 700,
                    fontSize: '0.84rem',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <span style={{ paddingLeft: '4px' }}>Live Shelves</span>
                  <span style={{
                    background: currentTab === 'dashboard' ? '#000000' : '#2A2A2A',
                    color: currentTab === 'dashboard' ? '#FFFFFF' : 'var(--text-secondary)',
                    fontSize: '0.72rem',
                    padding: '2px 8px',
                    borderRadius: 'var(--radius-pill)',
                    fontWeight: 800
                  }}>
                    56
                  </span>
                </div>

                {/* Second Sub-item */}
                <div 
                  onClick={() => setCurrentTab('alerts')}
                  style={{
                    background: currentTab === 'alerts' ? '#FFFFFF' : 'transparent',
                    color: currentTab === 'alerts' ? '#000000' : 'var(--text-secondary)',
                    borderRadius: '14px',
                    padding: '9px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    fontWeight: 600,
                    fontSize: '0.84rem',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <span style={{ paddingLeft: '4px' }}>Critical Stock</span>
                  <span style={{
                    background: currentTab === 'alerts' ? '#000000' : '#2A2A2A',
                    color: currentTab === 'alerts' ? '#FFFFFF' : 'var(--text-secondary)',
                    fontSize: '0.72rem',
                    padding: '2px 8px',
                    borderRadius: 'var(--radius-pill)',
                    fontWeight: 800
                  }}>
                    {unreadAlertsCount > 0 ? unreadAlertsCount : '12'}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Alerts / Shipments Nav Item */}
          <div 
            onClick={() => setCurrentTab('alerts')}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              padding: '10px 14px',
              borderRadius: 'var(--radius-pill)',
              color: currentTab === 'alerts' ? 'var(--accent-lime)' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '0.9rem',
              fontWeight: 600
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Bell size={18} />
              <span>Alerts</span>
            </div>
            <Plus size={15} style={{ opacity: 0.6 }} />
          </div>

          {/* Analytics / Orders Nav Item */}
          <div 
            onClick={() => setCurrentTab('analytics')}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              padding: '10px 14px',
              borderRadius: 'var(--radius-pill)',
              color: currentTab === 'analytics' ? 'var(--accent-lime)' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '0.9rem',
              fontWeight: 600
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <BarChart3 size={18} />
              <span>Analytics</span>
            </div>
          </div>

          {/* Try It / Demo Studio Nav Item */}
          <div 
            onClick={() => setCurrentTab('demo')}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              padding: '10px 14px',
              borderRadius: 'var(--radius-pill)',
              color: currentTab === 'demo' ? 'var(--accent-lime)' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '0.9rem',
              fontWeight: 600
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Sparkles size={18} />
              <span>Try It / Demo</span>
            </div>
            <span style={{
              background: 'rgba(228, 255, 26, 0.15)',
              color: 'var(--accent-lime)',
              fontSize: '0.68rem',
              padding: '2px 6px',
              borderRadius: '10px',
              fontWeight: 700
            }}>
              NEW
            </span>
          </div>

          {/* Upload Video Nav Item */}
          <div 
            onClick={() => setCurrentTab('upload')}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              padding: '10px 14px',
              borderRadius: 'var(--radius-pill)',
              color: currentTab === 'upload' ? 'var(--accent-lime)' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '0.9rem',
              fontWeight: 600
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <UploadCloud size={18} />
              <span>Upload Video</span>
            </div>
          </div>

          {/* Zones & Settings Nav Item */}
          <div 
            onClick={() => setCurrentTab('settings')}
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              padding: '10px 14px',
              borderRadius: 'var(--radius-pill)',
              color: currentTab === 'settings' ? 'var(--accent-lime)' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '0.9rem',
              fontWeight: 600
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Sliders size={18} />
              <span>Zones & Vision</span>
            </div>
          </div>
        </nav>
      </div>

      {/* Footer: Demo Mode Toggle & Light/Dark Segmented Pill */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', paddingTop: '16px' }}>
        {/* Quick Demo Mode Pill Button */}
        <button
          onClick={onToggleDemoMode}
          className="btn-pill btn-pill-dark"
          style={{ width: '100%', fontSize: '0.8rem', padding: '8px 12px', justifyContent: 'space-between' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Tv size={15} color={isDemoMode ? 'var(--accent-lime)' : 'var(--text-muted)'} />
            <span>Demo Mode</span>
          </div>
          <span style={{ 
            color: isDemoMode ? 'var(--accent-lime)' : 'var(--text-muted)',
            fontWeight: 800,
            fontSize: '0.74rem'
          }}>
            {isDemoMode ? 'ON' : 'OFF'}
          </span>
        </button>

        {/* Light / Dark Segmented Pill Switch as shown in reference */}
        <div className="theme-pill-switch">
          <button 
            onClick={() => { if (theme !== 'light') onToggleTheme(); }}
            className={`theme-pill-option ${theme === 'light' ? 'active' : ''}`}
          >
            <Sun size={14} />
            <span>Light</span>
          </button>
          <button 
            onClick={() => { if (theme !== 'dark') onToggleTheme(); }}
            className={`theme-pill-option ${theme === 'dark' ? 'active' : ''}`}
          >
            <Moon size={14} />
            <span>Dark</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
