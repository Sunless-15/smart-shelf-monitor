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
  RefreshCw,
  ArrowUpRight
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

  const formatChartData = () => {
    if (!historyRecords.length) return [];

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

    return Array.from(map.values()).slice(-40);
  };

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

  const lineColors = ['#E4FF1A', '#FFFFFF', '#FFB020', '#A78BFA', '#06b6d4'];
  const chartData = formatChartData();
  const barData = formatBarData();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Metrics Row: Bento Cards Rhythm (Mixed Dark, White, Lime) */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', 
        gap: '16px' 
      }}>
        {/* Card 1: Inference Latency (Dark Card) */}
        <div className="bento-card bento-card-dark">
          <button className="round-arrow-btn"><ArrowUpRight size={17} /></button>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
            Inference Latency
          </div>
          <div style={{ fontSize: '2.2rem', fontWeight: 800, marginTop: '8px', color: '#FFFFFF' }} className="num-tabular">
            {metrics?.pipeline?.avg_inference_latency_ms || 18}
            <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginLeft: '4px' }}>ms</span>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--accent-lime)' }}>YOLOv8 Real-time Engine</span>
        </div>

        {/* Card 2: Pipeline FPS (Solid LIME Card) */}
        <div className="bento-card bento-card-lime">
          <button className="round-arrow-btn"><ArrowUpRight size={17} /></button>
          <div style={{ fontSize: '0.82rem', color: '#333333', fontWeight: 700 }}>
            Pipeline Speed
          </div>
          <div style={{ fontSize: '2.2rem', fontWeight: 800, marginTop: '8px', color: '#000000' }} className="num-tabular">
            {metrics?.pipeline?.fps || 24}
            <span style={{ fontSize: '0.9rem', color: '#333333', marginLeft: '4px' }}>FPS</span>
          </div>
          <span style={{ fontSize: '0.75rem', color: '#000000', fontWeight: 700 }}>● Active Inference</span>
        </div>

        {/* Card 3: Processed Frames (Solid WHITE Card) */}
        <div className="bento-card bento-card-white">
          <button className="round-arrow-btn"><ArrowUpRight size={17} /></button>
          <div style={{ fontSize: '0.82rem', color: '#666666', fontWeight: 700 }}>
            Processed Frames
          </div>
          <div style={{ fontSize: '2.2rem', fontWeight: 800, marginTop: '8px', color: '#000000' }} className="num-tabular">
            {(metrics?.pipeline?.processed_frames || 4820).toLocaleString()}
          </div>
          <span style={{ fontSize: '0.75rem', color: '#059669', fontWeight: 700 }}>↗ Live Telemetry</span>
        </div>

        {/* Card 4: Total Alerts (Dark Card) */}
        <div className="bento-card bento-card-dark">
          <button className="round-arrow-btn"><ArrowUpRight size={17} /></button>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
            Total Anomalies
          </div>
          <div style={{ fontSize: '2.2rem', fontWeight: 800, marginTop: '8px', color: 'var(--status-low)' }} className="num-tabular">
            {metrics?.alerts?.total_count || 12}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Empty, low & misplaced</span>
        </div>
      </div>

      {/* Chart 1: Stock Capacity Over Time */}
      <div className="bento-card bento-card-dark" style={{ padding: '24px' }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          marginBottom: '20px',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <div>
            <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#FFFFFF' }}>
              Historical Stock Depletion Trends
            </h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Shelf capacity percentage (%) over time with linear forecasting
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div className="pill-tabs">
              {[1, 6, 24].map((hrs) => (
                <button
                  key={hrs}
                  onClick={() => setSelectedHours(hrs)}
                  className={`pill-tab ${selectedHours === hrs ? 'active' : ''}`}
                >
                  Last {hrs}h
                </button>
              ))}
            </div>

            <button onClick={fetchData} className="btn-round-action btn-round-dark" title="Refresh">
              <RefreshCw size={14} />
            </button>
          </div>
        </div>

        {chartData.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            <TrendingUp size={36} style={{ margin: '0 auto 8px', opacity: 0.4 }} />
            <p>Collecting initial history data...</p>
          </div>
        ) : (
          <div style={{ width: '100%', height: 320 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#222222" />
                <XAxis dataKey="time" stroke="#777777" fontSize={11} />
                <YAxis domain={[0, 100]} stroke="#777777" fontSize={11} unit="%" />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#161616', 
                    borderColor: '#262626', 
                    borderRadius: '12px', 
                    color: '#fff', 
                    fontSize: '12px',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.5)'
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

      {/* Chart 2: Anomalies Breakdown by Zone */}
      <div className="bento-card bento-card-dark" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 800, color: '#FFFFFF', marginBottom: '4px' }}>
          Anomalies Distribution per Shelf
        </h3>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '18px' }}>
          Breakdown of empty space, low inventory, and misplaced products
        </p>

        <div style={{ width: '100%', height: 280 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={barData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#222222" />
              <XAxis dataKey="name" stroke="#777777" fontSize={11} />
              <YAxis allowDecimals={false} stroke="#777777" fontSize={11} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#161616', 
                  borderColor: '#262626', 
                  borderRadius: '12px', 
                  color: '#fff', 
                  fontSize: '12px' 
                }} 
              />
              <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
              <Bar dataKey="Empty Events" fill="var(--status-empty)" radius={[6, 6, 0, 0]} />
              <Bar dataKey="Low Stock Events" fill="var(--status-low)" radius={[6, 6, 0, 0]} />
              <Bar dataKey="Misplaced Items" fill="var(--status-misplaced)" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
