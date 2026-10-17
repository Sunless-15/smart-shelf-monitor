import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import BottomNav from './components/BottomNav';
import Header from './components/Header';
import LoginModal from './components/LoginModal';
import LiveDashboard from './pages/LiveDashboard';
import AlertsView from './pages/AlertsView';
import AnalyticsView from './pages/AnalyticsView';
import VideoUploadView from './pages/VideoUploadView';
import ZonesSettingsView from './pages/ZonesSettingsView';

import { 
  getAlerts, 
  getHealth, 
  getSource, 
  switchSource,
  getAuthToken,
  clearAuthToken
} from './services/api';
import { AlertCircle, AlertTriangle, X, CloudLightning } from 'lucide-react';

export default function App() {
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [unreadAlertsCount, setUnreadAlertsCount] = useState(0);
  const [isOnline, setIsOnline] = useState(true);
  const [isDemoMode, setIsDemoMode] = useState(true);
  const [theme, setTheme] = useState('dark');
  const [toastAlert, setToastAlert] = useState(null);
  const [lastSeenAlertId, setLastSeenAlertId] = useState(null);
  const [showLogin, setShowLogin] = useState(!getAuthToken());
  const [serverWakingUp, setServerWakingUp] = useState(false);

  // Apply theme to document element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Request browser notification permissions
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }, []);

  // Listen for 401 unauthorized events from API client
  useEffect(() => {
    const handleAuthRequired = () => {
      setShowLogin(true);
    };
    window.addEventListener('auth_required', handleAuthRequired);
    return () => window.removeEventListener('auth_required', handleAuthRequired);
  }, []);

  // Poll system health and unacknowledged alerts count
  useEffect(() => {
    let failureCount = 0;

    const checkStatus = async () => {
      try {
        const [health, alertsData, srcData] = await Promise.all([
          getHealth(),
          getAlerts(true, 5),
          getSource()
        ]);

        setIsOnline(true);
        setServerWakingUp(false);
        failureCount = 0;

        const unackAlerts = alertsData.alerts || [];
        setUnreadAlertsCount(unackAlerts.length);

        // Check if demo mode is active
        if (srcData && srcData.type === 'video' && srcData.value?.includes('sample_shelf')) {
          setIsDemoMode(true);
        } else {
          setIsDemoMode(false);
        }

        // Show toast notification for new alert
        if (unackAlerts.length > 0) {
          const newest = unackAlerts[0];
          const nid = newest.id || newest._id;
          if (nid && nid !== lastSeenAlertId) {
            setLastSeenAlertId(nid);
            setToastAlert(newest);

            // Native browser notification if granted
            if ('Notification' in window && Notification.permission === 'granted') {
              new Notification(`Alert: ${newest.zone_name}`, {
                body: newest.message,
                icon: '/vite.svg'
              });
            }
          }
        }
      } catch (err) {
        setIsOnline(false);
        failureCount += 1;
        // If consecutive connection failures occur, hint at cloud cold-start
        if (failureCount >= 2) {
          setServerWakingUp(true);
        }
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 3000);
    return () => clearInterval(interval);
  }, [lastSeenAlertId]);

  const handleToggleDemoMode = async () => {
    try {
      const targetMode = !isDemoMode;
      if (targetMode) {
        await switchSource('video', 'sample_data/sample_shelf.mp4');
      } else {
        await switchSource('webcam', 0);
      }
      setIsDemoMode(targetMode);
    } catch (err) {
      console.error('Failed to toggle demo mode:', err);
    }
  };

  const handleToggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const handleLogout = () => {
    clearAuthToken();
    setShowLogin(true);
  };

  const handleLoginSuccess = () => {
    setShowLogin(false);
    setIsOnline(true);
  };

  const getPageInfo = () => {
    switch (currentTab) {
      case 'dashboard':
        return { title: 'Live Shelf Dashboard', subtitle: 'Real-time retail shelf vision feed and inventory analytics' };
      case 'alerts':
        return { title: 'Stock & Misplaced Alerts', subtitle: 'Live inventory anomalies requiring store manager intervention' };
      case 'analytics':
        return { title: 'Predictive Analytics', subtitle: 'Historical depletion trends, shortage forecasts, and system telemetry' };
      case 'upload':
        return { title: 'Video Analysis Studio', subtitle: 'Upload recorded store videos for automated YOLO annotation and timeline logging' };
      case 'settings':
        return { title: 'Zones & Video Sources', subtitle: 'Configure shelf detection boundaries and switch camera/ESP32-CAM stream inputs' };
      default:
        return { title: 'Smart Shelf Monitor', subtitle: '' };
    }
  };

  const pageInfo = getPageInfo();

  return (
    <div className="app-layout">
      {/* Cloud Cold Start Waking Up Banner */}
      {serverWakingUp && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          background: 'linear-gradient(90deg, #1e3a8a, #3b82f6)',
          color: '#fff',
          padding: '0.5rem 1rem',
          textAlign: 'center',
          fontSize: '0.85rem',
          fontWeight: 500,
          zIndex: 100000,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.5rem',
          boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
        }}>
          <CloudLightning size={16} className="animate-spin" />
          <span>Connecting to cloud backend... Free-tier hosts (e.g. Render) take ~30-50s to wake up from idle. Auto-retrying...</span>
        </div>
      )}

      {/* Login Authentication Modal */}
      <LoginModal isOpen={showLogin} onSuccess={handleLoginSuccess} />

      {/* Desktop Navigation Sidebar */}
      <Sidebar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        unreadAlertsCount={unreadAlertsCount}
        isOnline={isOnline}
        isDemoMode={isDemoMode}
        onToggleDemoMode={handleToggleDemoMode}
        theme={theme}
        onToggleTheme={handleToggleTheme}
      />

      {/* Main App Content Viewport */}
      <main className="main-viewport" style={{ marginTop: serverWakingUp ? '2rem' : 0 }}>
        {currentTab !== 'dashboard' && (
          <Header
            title={pageInfo.title}
            subtitle={pageInfo.subtitle}
            isOnline={isOnline}
            isDemoMode={isDemoMode}
            onToggleDemoMode={handleToggleDemoMode}
            theme={theme}
            onToggleTheme={handleToggleTheme}
            onLogout={handleLogout}
          />
        )}

        {/* Tab Switching Body */}
        {currentTab === 'dashboard' && <LiveDashboard isOnline={isOnline} />}
        {currentTab === 'alerts' && <AlertsView />}
        {currentTab === 'analytics' && <AnalyticsView />}
        {currentTab === 'upload' && <VideoUploadView />}
        {currentTab === 'settings' && <ZonesSettingsView />}
      </main>

      {/* Mobile Touch Bottom Nav */}
      <BottomNav
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        unreadAlertsCount={unreadAlertsCount}
      />

      {/* Live Toast Alert Banner */}
      {toastAlert && (
        <div style={{
          position: 'fixed',
          top: '1.25rem',
          right: '1.25rem',
          background: 'rgba(17, 24, 39, 0.95)',
          backdropFilter: 'blur(12px)',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          boxShadow: '0 8px 30px rgba(0, 0, 0, 0.6)',
          borderRadius: 'var(--radius-md)',
          padding: '0.85rem 1.1rem',
          zIndex: 9999,
          maxWidth: '380px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '0.75rem',
          animation: 'slideIn 0.3s ease-out'
        }}>
          <AlertCircle size={20} color="var(--status-empty)" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong style={{ fontSize: '0.88rem', color: '#fff' }}>
                {toastAlert.zone_name} Alert
              </strong>
              <button
                onClick={() => setToastAlert(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '2px' }}
              >
                <X size={15} />
              </button>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
              {toastAlert.message}
            </p>
            <button
              onClick={() => {
                setCurrentTab('alerts');
                setToastAlert(null);
              }}
              style={{
                marginTop: '0.4rem',
                background: 'none',
                border: 'none',
                color: 'var(--accent-blue)',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                padding: 0
              }}
            >
              View in Alerts Center &rarr;
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
