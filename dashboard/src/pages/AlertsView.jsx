import React, { useState, useEffect } from 'react';
import { getAlerts, acknowledgeAlert } from '../services/api';
import { 
  Bell, 
  CheckCheck, 
  CheckCircle, 
  AlertTriangle, 
  AlertCircle, 
  Info, 
  Clock, 
  RefreshCw 
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

  useEffect(() => {
    fetchAlertsData();
    const interval = setInterval(fetchAlertsData, 3000);
    return () => clearInterval(interval);
  }, [unackOnly]);

  const handleAcknowledge = async (alertId) => {
    setAckLoading(alertId);
    try {
      await acknowledgeAlert(alertId);
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Bento Header Card */}
      <div className="bento-card bento-card-dark" style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        flexWrap: 'wrap', 
        gap: '14px',
        padding: '20px 24px' 
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            width: '44px',
            height: '44px',
            borderRadius: '50%',
            background: 'var(--accent-lime-muted)',
            color: 'var(--accent-lime)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Bell size={22} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#FFFFFF' }}>
              Alert Center
            </h2>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Auto-refreshes every 3s · {unackCount} active unacknowledged
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Filter Pills */}
          <div className="pill-tabs">
            <button
              onClick={() => setUnackOnly(true)}
              className={`pill-tab ${unackOnly ? 'active' : ''}`}
            >
              Unacknowledged ({unackCount})
            </button>
            <button
              onClick={() => setUnackOnly(false)}
              className={`pill-tab ${!unackOnly ? 'active' : ''}`}
            >
              All Alerts
            </button>
          </div>

          {unackCount > 0 && (
            <button
              onClick={handleAcknowledgeAll}
              className="btn-pill btn-pill-lime"
              style={{ padding: '8px 16px', fontSize: '0.8rem' }}
            >
              <CheckCheck size={15} />
              <span>Acknowledge All</span>
            </button>
          )}

          <button 
            onClick={fetchAlertsData} 
            className="btn-round-action btn-round-dark" 
            title="Refresh alerts"
          >
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      {/* Alerts List */}
      {alerts.length === 0 ? (
        <div className="bento-card bento-card-dark" style={{ textAlign: 'center', padding: '50px 20px', color: 'var(--text-muted)' }}>
          <CheckCircle size={48} color="var(--accent-lime)" style={{ margin: '0 auto 12px', opacity: 0.9 }} />
          <h3 style={{ fontSize: '1.2rem', color: '#FFFFFF', fontWeight: 800 }}>No Active Anomalies</h3>
          <p style={{ fontSize: '0.86rem', marginTop: '4px', color: 'var(--text-secondary)' }}>
            {unackOnly ? 'All store shelf stock alerts have been cleared.' : 'No alerts have been recorded yet.'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {alerts.map((alert) => {
            const isAck = alert.acknowledged;
            const severity = (alert.severity || 'info').toLowerCase();
            const alertType = alert.type || 'alert';

            let icon = <Info size={18} color="var(--status-misplaced)" />;
            let statusColor = 'var(--status-misplaced)';
            if (severity === 'critical' || alertType === 'empty_shelf') {
              icon = <AlertCircle size={18} color="var(--status-empty)" />;
              statusColor = 'var(--status-empty)';
            } else if (severity === 'warning' || alertType === 'low_stock') {
              icon = <AlertTriangle size={18} color="var(--status-low)" />;
              statusColor = 'var(--status-low)';
            }

            return (
              <div
                key={alert.id || alert._id}
                className="bento-card bento-card-dark"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '16px',
                  padding: '18px 22px',
                  opacity: isAck ? 0.6 : 1,
                  borderLeft: `4px solid ${isAck ? 'var(--border-subtle)' : statusColor}`
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '14px' }}>
                  <div style={{ marginTop: '2px' }}>{icon}</div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      <span style={{ 
                        background: 'rgba(255, 255, 255, 0.08)', 
                        padding: '2px 10px', 
                        borderRadius: 'var(--radius-pill)', 
                        fontSize: '0.72rem', 
                        fontWeight: 800,
                        textTransform: 'uppercase',
                        color: statusColor
                      }}>
                        {alert.severity || 'ALERT'}
                      </span>
                      <strong style={{ fontSize: '0.96rem', color: '#FFFFFF' }}>
                        {alert.zone_name || 'Shelf Zone'}
                      </strong>
                      <span style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Clock size={12} />
                        {formatTimestamp(alert.timestamp)}
                      </span>
                    </div>
                    <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      {alert.message}
                    </p>
                  </div>
                </div>

                <div>
                  {!isAck ? (
                    <button
                      onClick={() => handleAcknowledge(alert.id || alert._id)}
                      disabled={ackLoading === (alert.id || alert._id)}
                      className="btn-pill btn-pill-lime"
                      style={{
                        padding: '8px 18px',
                        fontSize: '0.8rem'
                      }}
                    >
                      <CheckCircle size={14} />
                      <span>{ackLoading === (alert.id || alert._id) ? 'Saving...' : 'Acknowledge'}</span>
                    </button>
                  ) : (
                    <span style={{ fontSize: '0.78rem', color: 'var(--accent-lime)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <CheckCheck size={15} /> Acknowledged
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
