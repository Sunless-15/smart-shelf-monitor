import React, { useState, useEffect } from 'react';
import { getHistory, getMetrics, getZones } from '../services/api';
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Legend, 
  BarChart, 
  Bar, 
  CartesianGrid 
} from 'recharts';
import { 
  TrendingUp, 
  Cpu, 
  Gauge, 
  ShieldAlert, 
  Clock, 
  RefreshCw 
} from 'lucide-react';

export default function AnalyticsView() {
  const [historyRecords, setHistoryRecords] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [zones, setZones] = useState([]);
  const [selectedHours, setSelectedHours] = useState(6);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [histData, metricsData, zonesData] = await Promise.all([
        getHistory(null, selectedHours),
        getMetrics(),
        getZones(),
      ]);

      setHistoryRecords(histData.history || []);
      setMetrics(metricsData);
      setZones(zonesData || []);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [selectedHours]);

  // Group history data by timestamp for Recharts multi-line chart
  const formatChartData = () => {
    if (!historyRecords.length) return [];

    // Bucket by rounded minute or second
    const map = new Map();
    historyRecords.forEach((item) => {
      const timeStr = new Date(item.timestamp * 1000).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });

      if (!map.has(timeStr)) {
        map.set(timeStr, { time: timeStr });
      }
      const entry = map.get(timeStr);
      const zoneKey = item.zone_name || item.zone_id;
      entry[zoneKey] = Math.round((item.stock_percent || 0) * 100);
    });

    return Array.from(map.values()).slice(-40); // Last 40 points
  };

  // Build Zone Alert Distribution data
  const formatBarData = () => {
    return zones.map((z) => {
      const zid = z.id || z._id;
      const zHistory = historyRecords.filter((h) => h.zone_id === zid);
      const emptyEvents = zHistory.filter((h) => h.state === 'empty').length;
      const lowEvents = zHistory.filter((h) => h.state === 'low').length;
      const misplacedEvents = zHistory.reduce((acc, h) => acc + (h.misplaced_count || 0), 0);

      return {
        name: z.name.length > 15 ? z.name.slice(0, 15) + '...' : z.name,
        'Empty Events': emptyEvents,
        'Low Stock Events': lowEvents,
        'Misplaced Items': misplacedEvents,
      };
    });
  };

  const lineColors = ['#10b981', '#3b82f6', '#f59e0b', '#d946ef', '#06b6d4'];
  const chartData = formatChartData();
  const barData = formatBarData();

  return (
    <div>
      {/* Metrics Row */}
      <div className="metrics-grid">
        <div className="metric-tile glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="label">Inference Latency</span>
            <Cpu size={18} color="var(--accent-cyan)" />
          </div>
          <span className="value" style={{ color: 'var(--accent-cyan)' }}>
            {metrics?.pipeline?.avg_inference_latency_ms || 0}
            <small style={{ fontSize: '0.9rem', fontWeight: 500, marginLeft: '4px' }}>ms</small>
          </span>
        </div>

        <div className="metric-tile glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="label">Pipeline FPS</span>
            <Gauge size={18} color="var(--status-ok)" />
          </div>
          <span className="value" style={{ color: 'var(--status-ok)' }}>
            {metrics?.pipeline?.fps || 0}
          </span>
        </div>

        <div className="metric-tile glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="label">Processed Frames</span>
            <TrendingUp size={18} color="var(--accent-blue)" />
          </div>
          <span className="value">
            {metrics?.pipeline?.processed_frames || 0}
          </span>
        </div>

        <div className="metric-tile glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="label">Total Alert Events</span>
            <ShieldAlert size={18} color="var(--status-low)" />
          </div>
          <span className="value" style={{ color: 'var(--status-low)' }}>
            {metrics?.alerts?.total_count || 0}
          </span>
        </div>
      </div>

      {/* Time Window Selector */}
      <div className="glass-card" style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Historical Stock Trends</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Stock capacity percentage (%) across time per shelf</p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {[1, 6, 24].map((hrs) => (
            <button
              key={hrs}
              onClick={() => setSelectedHours(hrs)}
              className={`btn ${selectedHours === hrs ? 'btn-primary' : 'btn-secondary'}`}
              style={{ minHeight: '32px', padding: '0.25rem 0.75rem', fontSize: '0.78rem' }}
            >
              Last {hrs}h
            </button>
          ))}
          <button onClick={fetchData} className="btn btn-secondary" style={{ minHeight: '32px', padding: '0.25rem 0.5rem' }}>
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Chart 1: Stock Capacity Over Time */}
      <div className="glass-card" style={{ marginBottom: '1.75rem', padding: '1.5rem 1rem' }}>
        {chartData.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <TrendingUp size={36} style={{ margin: '0 auto 0.5rem', opacity: 0.5 }} />
            <p>Collecting initial history data...</p>
            <p style={{ fontSize: '0.85rem' }}>The pipeline snapshots stock levels every 5 seconds.</p>
          </div>
        ) : (
          <div style={{ width: '100%', height: 320 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.08)" />
                <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={11} />
                <YAxis domain={[0, 100]} stroke="var(--text-muted)" fontSize={11} unit="%" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'rgba(17, 24, 39, 0.95)', 
                    borderColor: 'var(--border-subtle)',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '12px'
                  }} 
                />
                <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                {zones.map((z, idx) => (
                  <Line
                    key={z.name}
                    type="monotone"
                    dataKey={z.name}
                    stroke={lineColors[idx % lineColors.length]}
                    strokeWidth={2.5}
                    dot={false}
                    activeDot={{ r: 5 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Chart 2: Alerts Breakdown by Zone */}
      <div className="glass-card" style={{ padding: '1.5rem 1rem' }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.25rem' }}>Anomalies Distribution per Shelf</h3>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Breakdown of empty space, low inventory, and misplaced products
        </p>

        <div style={{ width: '100%', height: 280 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={barData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.08)" />
              <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={11} />
              <YAxis allowDecimals={false} stroke="var(--text-muted)" fontSize={11} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'rgba(17, 24, 39, 0.95)', 
                  borderColor: 'var(--border-subtle)',
                  borderRadius: '8px',
                  color: '#fff',
                  fontSize: '12px'
                }} 
              />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
              <Bar dataKey="Empty Events" fill="var(--status-empty)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Low Stock Events" fill="var(--status-low)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Misplaced Items" fill="var(--status-misplaced)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
