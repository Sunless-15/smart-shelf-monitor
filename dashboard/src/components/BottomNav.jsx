import React from 'react';
import { LayoutDashboard, Bell, BarChart3, UploadCloud, Sliders } from 'lucide-react';

export default function BottomNav({ currentTab, setCurrentTab, unreadAlertsCount = 0 }) {
  const items = [
    { id: 'dashboard', label: 'Feed', icon: LayoutDashboard },
    { id: 'alerts', label: 'Alerts', icon: Bell, badge: unreadAlertsCount },
    { id: 'analytics', label: 'Stats', icon: BarChart3 },
    { id: 'upload', label: 'Upload', icon: UploadCloud },
    { id: 'settings', label: 'Zones', icon: Sliders },
  ];

  return (
    <nav className="mobile-bottom-nav">
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = currentTab === item.id;
        return (
          <div
            key={item.id}
            onClick={() => setCurrentTab(item.id)}
            className={`bottom-nav-item ${isActive ? 'active' : ''}`}
          >
            <Icon size={20} />
            <span style={{ marginTop: '2px' }}>{item.label}</span>
            {item.badge > 0 && <span className="badge-counter">{item.badge}</span>}
          </div>
        );
      })}
    </nav>
  );
}
