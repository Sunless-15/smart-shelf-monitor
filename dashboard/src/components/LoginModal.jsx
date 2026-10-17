import React, { useState } from 'react';
import { Lock, ShieldCheck, AlertCircle, ArrowRight, Eye, EyeOff } from 'lucide-react';
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
      background: 'rgba(5, 8, 16, 0.82)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 99999,
      padding: '1rem',
      animation: 'fadeIn 0.25s ease-out'
    }}>
      <div style={{
        background: 'var(--surface-primary, #111827)',
        border: '1px solid var(--border-color, #374151)',
        borderRadius: '16px',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.75)',
        width: '100%',
        maxWidth: '420px',
        padding: '2rem',
        color: 'var(--text-primary, #f9fafb)',
        textAlign: 'center'
      }}>
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          background: 'rgba(59, 130, 246, 0.15)',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 1.25rem auto'
        }}>
          <Lock size={28} color="var(--accent-blue, #3b82f6)" />
        </div>

        <h2 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: '0.4rem' }}>
          Dashboard Access
        </h2>
        <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary, #9ca3af)', marginBottom: '1.5rem' }}>
          Enter administrator password to access live feeds, alerts, and settings.
        </p>

        {error && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            color: '#f87171',
            borderRadius: '8px',
            padding: '0.65rem 0.85rem',
            fontSize: '0.82rem',
            marginBottom: '1.25rem',
            textAlign: 'left'
          }}>
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ position: 'relative', marginBottom: '1.25rem' }}>
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password (default: admin123)"
              autoFocus
              style={{
                width: '100%',
                padding: '0.8rem 2.8rem 0.8rem 1rem',
                background: 'var(--surface-secondary, #1f2937)',
                border: '1px solid var(--border-color, #4b5563)',
                borderRadius: '10px',
                color: '#fff',
                fontSize: '0.95rem',
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              style={{
                position: 'absolute',
                right: '0.8rem',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'none',
                border: 'none',
                color: 'var(--text-muted, #9ca3af)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center'
              }}
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '0.85rem',
              background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
              border: 'none',
              borderRadius: '10px',
              color: '#fff',
              fontSize: '0.95rem',
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              transition: 'all 0.2s ease',
              opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? 'Authenticating...' : (
              <>
                Unlock Dashboard <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted, #6b7280)', marginTop: '1.25rem' }}>
          Default credential: <code style={{ color: 'var(--accent-blue, #60a5fa)' }}>admin123</code> (configured via DASHBOARD_PASSWORD)
        </p>
      </div>
    </div>
  );
}
