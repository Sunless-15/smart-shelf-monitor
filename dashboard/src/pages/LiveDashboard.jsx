import React, { useState, useEffect } from 'react';
import { 
  getLiveStreamUrl, 
  getShelfStatus, 
  getLiveFrameUrl 
} from '../services/api';
import { 
  Package, 
  AlertTriangle, 
  AlertCircle, 
  Layers, 
  Clock, 
  Maximize2, 
  Camera, 
  Activity,
  CheckCircle2
} from 'lucide-react';

export default function LiveDashboard({ isOnline }) {
  const [shelfData, setShelfData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [streamError, setStreamError] = useState(false);
  const [streamKey, setStreamKey] = useState(Date.now());

  // Polling shelf status every 2 seconds
  useEffect(() => {
    let isMounted = true;

    const fetchStatus = async () => {
      try {
        const data = await getShelfStatus();
        if (isMounted) {
          setShelfData(data);
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError('Backend offline or unreachable.');
          setLoading(false);
        }
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleSnapshot = () => {
    window.open(getLiveFrameUrl(), '_blank');
  };

  const handleReloadStream = () => {
    setStreamError(false);
    setStreamKey(Date.now());
  };

  const zones = shelfData?.zones || [];
  const summary = shelfData?.summary || {
    total_items: 0,
    low_stock_zones: 0,
    empty_zones: 0,
    total_misplaced_items: 0,
  };

  return (
    <div>
      {/* Summary Metrics Grid */}
      <div className="metrics-grid">
        <div className="metric-tile glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="label">Total Zones</span>
            <Layers size={18} color="var(--accent-blue)" />
          </div>
          <span className="value">{shelfData?.total_zones || zones.length}</span>
        </div>

        <div className="metric-tile glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="label">Items In Stock</span>
            <Package size={18} color="var(--status-ok)" />
          </div>
          <span className="value" style={{ color: 'var(--status-ok)' }}>
            {summary.total_items}
          </span>
        </div>

        <div className="metric-tile glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="label">Low Stock</span>
            <AlertTriangle size={18} color="var(--status-low)" />
          </div>
          <span className="value" style={{ color: summary.low_stock_zones > 0 ? 'var(--status-low)' : 'var(--text-primary)' }}>
            {summary.low_stock_zones}
          </span>
        </div>

        <div className="metric-tile glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="label">Empty Shelves</span>
            <AlertCircle size={18} color="var(--status-empty)" />
          </div>
          <span className="value" style={{ color: summary.empty_zones > 0 ? 'var(--status-empty)' : 'var(--text-primary)' }}>
            {summary.empty_zones}
          </span>
        </div>

        <div className="metric-tile glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="label">Misplaced Items</span>
            <Activity size={18} color="var(--status-misplaced)" />
          </div>
          <span className="value" style={{ color: summary.total_misplaced_items > 0 ? 'var(--status-misplaced)' : 'var(--text-primary)' }}>
            {summary.total_misplaced_items}
          </span>
        </div>
      </div>

      {/* Main Grid: Stream on Left, Zone Cards on Right / Below */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Live Annotated Stream */}
        <div className="glass-card" style={{ padding: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ef4444', animation: 'pulse 1.5s infinite' }} />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Live Annotated Feed</h3>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              {shelfData && (
                <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <span>FPS: <strong style={{ color: 'var(--text-primary)' }}>{shelfData.fps || 0}</strong></span>
                  <span>Latency: <strong style={{ color: 'var(--text-primary)' }}>{shelfData.latency_ms || 0}ms</strong></span>
                </div>
              )}
              <button 
                onClick={handleSnapshot} 
                className="btn btn-secondary" 
                style={{ minHeight: '32px', padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                title="Open JPEG snapshot"
              >
                <Camera size={14} /> Snapshot
              </button>
            </div>
          </div>

          <div className="stream-container" id="live-stream-viewport">
            <span className="live-badge">LIVE FEED</span>
            {!streamError ? (
              <img 
                key={streamKey}
                src={getLiveStreamUrl()} 
                alt="Live Annotated Shelf Feed" 
                onError={() => setStreamError(true)}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                <AlertCircle size={40} color="var(--status-empty)" style={{ margin: '0 auto 0.5rem' }} />
                <p style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Live stream connection paused</p>
                <p style={{ fontSize: '0.85rem', marginBottom: '1rem' }}>Backend or camera source re-initializing.</p>
                <button onClick={handleReloadStream} className="btn btn-primary" style={{ minHeight: '34px', fontSize: '0.8rem' }}>
                  Reconnect Stream
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Shelf Zones Grid */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 700 }}>Shelf Zones Status</h2>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Real-time product counts, occupancy fallback, and depletion forecasts
            </p>
          </div>
        </div>

        {zones.length === 0 ? (
          <div className="glass-card" style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <Layers size={36} style={{ margin: '0 auto 0.5rem', opacity: 0.5 }} />
            <p>No shelf zones configured yet.</p>
            <p style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>Configure zones in the Zones & Settings tab.</p>
          </div>
        ) : (
          <div className="zones-grid">
            {zones.map((zone) => {
              const state = zone.state || 'ok';
              const pct = Math.round((zone.stock_percent || 0) * 100);
              const pred = zone.prediction;
              const hasMisplaced = zone.misplaced_count > 0;

              return (
                <div key={zone.zone_id} className={`zone-card state-${state}`}>
                  {/* Zone Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>{zone.name}</h3>
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                        Expected: <strong style={{ color: 'var(--text-primary)', textTransform: 'capitalize' }}>{zone.expected_class}</strong>
                      </span>
                    </div>

                    <span className={`badge badge-${state}`}>
                      {state === 'ok' && <CheckCircle2 size={12} />}
                      {state === 'low' && <AlertTriangle size={12} />}
                      {state === 'empty' && <AlertCircle size={12} />}
                      {state}
                    </span>
                  </div>

                  {/* Stock Count & Progress */}
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.88rem', marginBottom: '0.4rem' }}>
                      <span style={{ color: 'var(--text-secondary)' }}>Capacity Level</span>
                      <span style={{ fontWeight: 700 }}>
                        {zone.current_count} / {zone.full_count} items ({pct}%)
                      </span>
                    </div>

                    <div className="progress-container">
                      <div 
                        className={`progress-fill fill-${state}`} 
                        style={{ width: `${Math.min(100, Math.max(5, pct))}%` }} 
                      />
                    </div>
                  </div>

                  {/* Misplaced Warning */}
                  {hasMisplaced && (
                    <div style={{
                      background: 'var(--status-misplaced-bg)',
                      border: '1px solid rgba(217, 70, 239, 0.3)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '0.5rem 0.75rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem',
                      fontSize: '0.8rem',
                      color: 'var(--status-misplaced)',
                      fontWeight: 600
                    }}>
                      <AlertTriangle size={15} />
                      <span>
                        {zone.misplaced_count} misplaced product ({zone.misplaced_items?.map(m => m.class_name).join(', ')})
                      </span>
                    </div>
                  )}

                  {/* Depletion Forecast Box */}
                  <div style={{
                    marginTop: 'auto',
                    padding: '0.65rem 0.85rem',
                    background: 'rgba(255, 255, 255, 0.03)',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.78rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.25rem'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                      <Clock size={13} />
                      <span>Forecast</span>
                    </div>

                    {pred && pred.status === 'depleting' ? (
                      <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-primary)' }}>
                        <span>Empty in: <strong style={{ color: 'var(--status-empty)' }}>{pred.minutes_to_empty}m</strong></span>
                        <span>Low in: <strong style={{ color: 'var(--status-low)' }}>{pred.minutes_to_low}m</strong></span>
                      </div>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>
                        {pred?.message || 'Stock level steady or restocked.'}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
