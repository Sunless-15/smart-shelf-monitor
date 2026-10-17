import React, { useState, useEffect } from 'react';
import { getAlerts, acknowledgeAlert } from '../services/api';
import { 
  Bell, 
  CheckCheck, 
  CheckCircle, 
  AlertTriangle, 
  AlertCircle, 
  Info, 
  Filter, 
  RefreshCw,
  Clock 
} from 'lucide-react';

export default function AlertsView() {
  const [alerts, setAlerts] = useState([]);
  const [unackOnly, setUnackOnly] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [ackLoading, setAckLoading] = useState(null);

  const fetchAlertsData = async () => {
    try {
      const data = await getAlerts(unackOnly, 100);
      setAlerts(data.alerts || []);
      setError(null);
    } catch (err) {
      setError('Unable to fetch alerts from server.');
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh every 3 seconds as required
  useEffect(() => {
    fetchAlertsData();
    const interval = setInterval(fetchAlertsData, 3000);
    return () => clearInterval(interval);
  }, [unackOnly]);

  const handleAcknowledge = async (alertId) => {
    setAckLoading(alertId);
    try {
      await acknowledgeAlert(alertId);
      // Optimistic update
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, acknowledged: true } : a))
      );
    } catch (err) {
      console.error('Failed to acknowledge alert:', err);
    } finally {
      setAckLoading(null);
    }
  };

  const handleAcknowledgeAll = async () => {
    const unacknowledged = alerts.filter((a) => !a.acknowledged);
    for (const a of unacknowledged) {
      try {
        await acknowledgeAlert(a.id);
      } catch (err) {
        console.error(err);
      }
    }
    fetchAlertsData();
  };

  const formatTimestamp = (ts) => {
    if (!ts) return 'Just now';
    const d = new Date(ts * 1000);
    const now = new Date();
    const diffSec = Math.floor((now - d) / 1000);

    if (diffSec < 60) return `${diffSec}s ago`;
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const unackCount = alerts.filter((a) => !a.acknowledged).length;

  return (
    <div>
      {/* Top Controls */}
      <div className="glass-card" style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            width: '38px',
            height: '38px',
            borderRadius: 'var(--radius-md)',
            background: 'var(--status-low-bg)',
            color: 'var(--status-low)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Bell size={20} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700 }}>Alert Center</h2>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Auto-refreshes every 3s | {unackCount} unacknowledged
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          {/* Filter Toggle */}
          <button
            onClick={() => setUnackOnly(!unackOnly)}
            className={`btn ${unackOnly ? 'btn-primary' : 'btn-secondary'}`}
            style={{ minHeight: '36px', fontSize: '0.8rem' }}
          >
            <Filter size={14} />
            <span>{unackOnly ? 'Unacknowledged Only' : 'All Alerts'}</span>
          </button>

          {unackCount > 0 && (
            <button
              onClick={handleAcknowledgeAll}
              className="btn btn-secondary"
              style={{ minHeight: '36px', fontSize: '0.8rem', color: 'var(--status-ok)' }}
            >
              <CheckCheck size={16} />
              <span>Acknowledge All</span>
            </button>
          )}

          <button 
            onClick={fetchAlertsData} 
            className="btn btn-secondary" 
            style={{ minHeight: '36px', padding: '0.35rem 0.65rem' }}
            title="Refresh alerts"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Alerts List */}
      {alerts.length === 0 ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: '3.5rem', color: 'var(--text-muted)' }}>
          <CheckCircle size={44} color="var(--status-ok)" style={{ margin: '0 auto 0.75rem', opacity: 0.8 }} />
          <h3 style={{ fontSize: '1.2rem', color: 'var(--text-primary)', fontWeight: 700 }}>No Active Alerts</h3>
          <p style={{ fontSize: '0.88rem', marginTop: '0.25rem' }}>
            {unackOnly ? 'All stock anomalies have been acknowledged.' : 'No alerts have been recorded yet.'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          {alerts.map((alert) => {
            const isAck = alert.acknowledged;
            const severity = (alert.severity || 'info').toLowerCase();
            const alertType = alert.type || 'alert';

            let icon = <Info size={18} color="var(--status-misplaced)" />;
            let badgeClass = 'badge-misplaced';
            if (severity === 'critical' || alertType === 'empty_shelf') {
              icon = <AlertCircle size={18} color="var(--status-empty)" />;
              badgeClass = 'badge-empty';
            } else if (severity === 'warning' || alertType === 'low_stock') {
              icon = <AlertTriangle size={18} color="var(--status-low)" />;
              badgeClass = 'badge-low';
            }

            return (
              <div
                key={alert.id || alert._id}
                className="glass-card"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '1rem',
                  padding: '1rem 1.25rem',
                  opacity: isAck ? 0.65 : 1,
                  borderLeft: isAck ? '4px solid var(--border-subtle)' : `4px solid var(--${badgeClass.replace('badge-', 'status-')})`
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.85rem' }}>
                  <div style={{ marginTop: '2px' }}>{icon}</div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <span className={`badge ${badgeClass}`}>{alert.severity || 'ALERT'}</span>
                      <strong style={{ fontSize: '0.92rem', color: 'var(--text-primary)' }}>
                        {alert.zone_name || 'Shelf Zone'}
                      </strong>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <Clock size={12} />
                        {formatTimestamp(alert.timestamp)}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginTop: '0.35rem' }}>
                      {alert.message}
                    </p>
                  </div>
                </div>

                <div>
                  {!isAck ? (
                    <button
                      onClick={() => handleAcknowledge(alert.id || alert._id)}
                      disabled={ackLoading === (alert.id || alert._id)}
                      className="btn btn-secondary"
                      style={{
                        minHeight: '34px',
                        padding: '0.35rem 0.85rem',
                        fontSize: '0.8rem',
                        whiteSpace: 'nowrap'
                      }}
                    >
                      <CheckCircle size={14} color="var(--status-ok)" />
                      <span>{ackLoading === (alert.id || alert._id) ? 'Saving...' : 'Acknowledge'}</span>
                    </button>
                  ) : (
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      <CheckCheck size={14} color="var(--status-ok)" /> Acknowledged
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
