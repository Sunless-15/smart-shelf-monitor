import React from 'react';
import { LayoutDashboard, Bell, BarChart3, UploadCloud, Sliders } from 'lucide-react';

export default function BottomNav({ currentTab, setCurrentTab, unreadAlertsCount = 0 }) {
  const tabs = [
    { id: 'dashboard', label: 'Shelves', icon: LayoutDashboard },
    { id: 'alerts', label: 'Alerts', icon: Bell, badge: unreadAlertsCount },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'upload', label: 'Upload', icon: UploadCloud },
    { id: 'settings', label: 'Zones', icon: Sliders },
  ];

  return (
    <nav className="mobile-bottom-bar">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = currentTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => setCurrentTab(tab.id)}
            className={`mobile-nav-pill-item ${isActive ? 'active' : ''}`}
            style={{ position: 'relative' }}
          >
            <Icon size={18} />
            <span>{tab.label}</span>
            {tab.badge > 0 && (
              <span style={{
                position: 'absolute',
                top: '2px',
                right: '12px',
                background: '#FF4D4F',
                color: '#FFFFFF',
                borderRadius: '50%',
                width: '15px',
                height: '15px',
                fontSize: '0.65rem',
                fontWeight: 800,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </nav>
  );
}
