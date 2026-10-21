from pathlib import Path

ROOT = Path(r"D:\project\smart shelf\dashboard\src")

# 1. Update BottomNav.jsx
bottom_nav = ROOT / "components" / "BottomNav.jsx"
bn_content = """import React from 'react';
import { LayoutDashboard, Bell, BarChart3, UploadCloud, Sliders, Sparkles } from 'lucide-react';

export default function BottomNav({ currentTab, setCurrentTab, unreadAlertsCount = 0 }) {
  const tabs = [
    { id: 'dashboard', label: 'Shelves', icon: LayoutDashboard },
    { id: 'demo', label: 'Demo', icon: Sparkles },
    { id: 'alerts', label: 'Alerts', icon: Bell, badge: unreadAlertsCount },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'upload', label: 'Upload', icon: UploadCloud },
    { id: 'settings', label: 'Settings', icon: Sliders },
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
"""
bottom_nav.write_text(bn_content, encoding="utf-8")
print("Updated BottomNav.jsx")

# 2. Update Sidebar.jsx
sidebar_path = ROOT / "components" / "Sidebar.jsx"
sb_text = sidebar_path.read_text(encoding="utf-8")
if "setCurrentTab('demo')" not in sb_text:
    anchor = "{/* Upload Video Nav Item */}"
    demo_item = """{/* Try It / Demo Studio Nav Item */}
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

          """
    sb_text = sb_text.replace(anchor, demo_item + anchor)
    sidebar_path.write_text(sb_text, encoding="utf-8")
    print("Updated Sidebar.jsx with Demo item")

# 3. Update App.jsx
app_path = ROOT / "App.jsx"
app_text = app_path.read_text(encoding="utf-8")

if "DemoView" not in app_text:
    # Add import
    app_text = app_text.replace(
        "import ZonesSettingsView from './pages/ZonesSettingsView';",
        "import ZonesSettingsView from './pages/ZonesSettingsView';\nimport DemoView from './pages/DemoView';\nimport { getCameraStatus } from './services/api';"
    )
    # Add cameraStatus state
    app_text = app_text.replace(
        "const [lastSeenAlertId, setLastSeenAlertId] = useState(null);",
        "const [lastSeenAlertId, setLastSeenAlertId] = useState(null);\n  const [cameraStatus, setCameraStatus] = useState(null);"
    )
    # Poll camera status in checkStatus
    app_text = app_text.replace(
        "const [health, alertsData, srcData] = await Promise.all([",
        "const [health, alertsData, srcData, camData] = await Promise.all([\n          getCameraStatus().catch(() => null),"
    )
    # Handle camera status response
    app_text = app_text.replace(
        "setUnreadAlertsCount(unackAlerts.length);",
        "setUnreadAlertsCount(unackAlerts.length);\n        if (camData) setCameraStatus(camData);"
    )
    # Add demo to pageInfo
    app_text = app_text.replace(
        "case 'settings':",
        "case 'demo':\n        return { title: 'Vision Studio & Sandbox', subtitle: 'Test YOLO detections live on sample gallery images or custom shelf uploads' };\n      case 'settings':"
    )
    # Render camera mode badge in viewport
    badge_block = """{/* Camera Mode Honest Badge */}
        {cameraStatus && (
          <div style={{
            background: cameraStatus.is_simulated ? 'rgba(255, 149, 0, 0.12)' : 'rgba(52, 199, 89, 0.12)',
            border: `1px solid ${cameraStatus.is_simulated ? '#FF9500' : '#34C759'}60`,
            borderRadius: '16px',
            padding: '6px 14px',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.8rem',
            color: cameraStatus.is_simulated ? '#FF9500' : '#34C759',
            fontWeight: 700
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: cameraStatus.is_simulated ? '#FF9500' : '#34C759',
                boxShadow: `0 0 8px ${cameraStatus.is_simulated ? '#FF9500' : '#34C759'}`
              }} />
              <span>{cameraStatus.badge_text}</span>
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 500 }}>
              {cameraStatus.is_simulated ? 'Simulated feed (tagged simulated=true)' : 'Hardware Feed Active'}
            </span>
          </div>
        )}
        """
    app_text = app_text.replace(
        '<main className="main-viewport" style={{ marginTop: serverWakingUp ? \'2rem\' : 0 }}>',
        '<main className="main-viewport" style={{ marginTop: serverWakingUp ? \'2rem\' : 0 }}>\n        ' + badge_block
    )
    # Render DemoView tab
    app_text = app_text.replace(
        "{currentTab === 'settings' && <ZonesSettingsView />}",
        "{currentTab === 'demo' && <DemoView />}\n        {currentTab === 'settings' && <ZonesSettingsView />}"
    )
    app_path.write_text(app_text, encoding="utf-8")
    print("Updated App.jsx with DemoView and Camera Badge")
