import React from 'react';
import { Wifi, WifiOff, Tv, RefreshCw, Sun, Moon } from 'lucide-react';

export default function Header({ 
  title, 
  subtitle, 
  isOnline = true, 
  isDemoMode = false, 
  onToggleDemoMode, 
  onRefresh, 
  theme, 
  onToggleTheme 
}) {
  return (
    <header className="page-header">
      <div>
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
        {/* Quick Demo toggle button */}
        <button
          onClick={onToggleDemoMode}
          className={`btn ${isDemoMode ? 'btn-primary' : 'btn-secondary'}`}
          style={{ minHeight: '36px', padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
          title="Toggle looping demo video"
        >
          <Tv size={15} />
          <span>Demo {isDemoMode ? 'ON' : 'OFF'}</span>
        </button>

        {onRefresh && (
          <button 
            onClick={onRefresh} 
            className="btn btn-secondary" 
            style={{ minHeight: '36px', padding: '0.35rem 0.65rem' }}
            title="Refresh data"
          >
            <RefreshCw size={15} />
          </button>
        )}

        <button 
          onClick={onToggleTheme} 
          className="btn btn-secondary"
          style={{ minHeight: '36px', padding: '0.35rem 0.65rem' }}
          title="Toggle dark/light mode"
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        <div 
          className={`badge ${isOnline ? 'badge-ok' : 'badge-empty'}`}
          style={{ padding: '0.4rem 0.75rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
        >
          {isOnline ? <Wifi size={13} /> : <WifiOff size={13} />}
          <span>{isOnline ? 'LIVE' : 'DISCONNECTED'}</span>
        </div>
      </div>
    </header>
  );
}
