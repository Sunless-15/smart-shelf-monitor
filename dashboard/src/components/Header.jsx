import React from 'react';
import { Wifi, WifiOff, Tv, RefreshCw, Sun, Moon, LogOut } from 'lucide-react';

export default function Header({ 
  title, 
  subtitle, 
  isOnline = true, 
  isDemoMode = false, 
  onToggleDemoMode, 
  onRefresh, 
  theme, 
  onToggleTheme,
  onLogout
}) {
  return (
    <header style={{ 
      display: 'flex', 
      justifyContent: 'space-between', 
      alignItems: 'center', 
      marginBottom: '20px', 
      flexWrap: 'wrap', 
      gap: '12px' 
    }}>
      <div>
        <h1 style={{ 
          fontSize: '1.85rem', 
          fontWeight: 800, 
          letterSpacing: '-0.03em', 
          color: 'var(--text-primary)' 
        }}>
          {title}
        </h1>
        {subtitle && (
          <p style={{ 
            color: 'var(--text-secondary)', 
            fontSize: '0.88rem', 
            marginTop: '3px' 
          }}>
            {subtitle}
          </p>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {/* Live Status Pill */}
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '6px', 
          padding: '7px 14px', 
          borderRadius: 'var(--radius-pill)', 
          background: isOnline ? 'var(--accent-lime)' : 'rgba(255, 77, 79, 0.15)',
          color: isOnline ? '#000000' : '#FF4D4F',
          fontSize: '0.76rem',
          fontWeight: 800,
          letterSpacing: '0.04em'
        }}>
          {isOnline ? <Wifi size={13} strokeWidth={3} /> : <WifiOff size={13} />}
          <span>{isOnline ? 'LIVE' : 'OFFLINE'}</span>
        </div>

        {/* Demo Mode Pill */}
        <button
          onClick={onToggleDemoMode}
          className="btn-pill btn-pill-dark"
          style={{ padding: '7px 14px', fontSize: '0.78rem' }}
          title="Toggle demo playback"
        >
          <Tv size={14} color={isDemoMode ? 'var(--accent-lime)' : 'inherit'} />
          <span>Demo: {isDemoMode ? 'ON' : 'OFF'}</span>
        </button>

        {onRefresh && (
          <button 
            onClick={onRefresh} 
            className="btn-round-action btn-round-dark"
            style={{ width: '36px', height: '36px' }}
            title="Refresh View"
          >
            <RefreshCw size={14} />
          </button>
        )}

        <button 
          onClick={onToggleTheme} 
          className="btn-round-action btn-round-dark"
          style={{ width: '36px', height: '36px' }}
          title="Toggle Theme"
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        {onLogout && (
          <button 
            onClick={onLogout} 
            className="btn-round-action btn-round-dark"
            style={{ width: '36px', height: '36px' }}
            title="Lock Dashboard"
          >
            <LogOut size={14} />
          </button>
        )}
      </div>
    </header>
  );
}
