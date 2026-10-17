import React, { useState } from 'react';
import { Lock, AlertCircle, Eye, EyeOff, ShieldCheck } from 'lucide-react';
import { login } from '../services/api';

export default function LoginModal({ isOpen, onSuccess }) {
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!password.trim()) {
      setError('Please enter the dashboard password.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await login(password.trim());
      setPassword('');
      if (onSuccess) onSuccess();
    } catch (err) {
      if (err.response?.status === 401) {
        setError('Invalid password. Default is admin123 unless changed in .env.');
      } else if (err.response?.status === 429) {
        setError('Too many failed attempts. Please wait 1 minute.');
      } else {
        setError('Could not connect to backend server. Please verify backend is running.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(5, 5, 5, 0.88)',
      backdropFilter: 'blur(16px)',
      WebkitBackdropFilter: 'blur(16px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 99999,
      padding: '1.25rem',
      animation: 'fadeIn 0.25s ease-out'
    }}>
      <div className="bento-card bento-card-dark" style={{
        width: '100%',
        maxWidth: '400px',
        padding: '36px 30px',
        textAlign: 'center',
        border: '1px solid var(--border-subtle)'
      }}>
        {/* Brand Header */}
        <div style={{ marginBottom: '22px' }}>
          <div style={{
            fontSize: '1.6rem',
            fontWeight: 800,
            letterSpacing: '-0.04em',
            color: '#FFFFFF'
          }}>
            shelf<span style={{ color: 'var(--accent-lime)' }}>sense</span>
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Store Manager Terminal & AI Monitoring
          </div>
        </div>

        <div style={{
          width: '54px',
          height: '54px',
          borderRadius: '50%',
          background: 'rgba(228, 255, 26, 0.1)',
          border: '1px solid rgba(228, 255, 26, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 18px auto'
        }}>
          <Lock size={22} color="var(--accent-lime)" />
        </div>

        <h2 style={{ fontSize: '1.35rem', fontWeight: 800, letterSpacing: '-0.02em', marginBottom: '6px' }}>
          Access Dashboard
        </h2>
        <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '24px' }}>
          Enter administrator password to access live feeds, stock alerts, and zone camera settings.
        </p>

        {error && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(255, 77, 79, 0.15)',
            border: '1px solid rgba(255, 77, 79, 0.35)',
            color: '#FF4D4F',
            borderRadius: 'var(--radius-card-sm)',
            padding: '10px 14px',
            fontSize: '0.82rem',
            marginBottom: '18px',
            textAlign: 'left'
          }}>
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ position: 'relative', marginBottom: '20px' }}>
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password (default: admin123)"
              autoFocus
              style={{
                width: '100%',
                padding: '12px 42px 12px 18px',
                background: '#101010',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-pill)',
                color: '#FFFFFF',
                fontSize: '0.92rem',
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              style={{
                position: 'absolute',
                right: '14px',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
            </button>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-pill btn-pill-lime"
            style={{
              width: '100%',
              padding: '13px',
              fontSize: '0.95rem'
            }}
          >
            {loading ? 'Authenticating...' : 'Unlock Terminal'}
          </button>
        </form>

        <div style={{
          marginTop: '18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
          fontSize: '0.75rem',
          color: 'var(--text-muted)'
        }}>
          <ShieldCheck size={14} color="var(--accent-lime)" />
          <span>Protected with YOLOv8 Vision & Session JWT</span>
        </div>
      </div>
    </div>
  );
}
