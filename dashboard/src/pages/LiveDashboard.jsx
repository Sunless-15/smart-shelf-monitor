import React, { useState, useEffect } from 'react';
import { 
  getLiveStreamUrl, 
  getShelfStatus, 
  getLiveFrameUrl,
  getAlerts,
  acknowledgeAlert
} from '../services/api';
import { 
  ArrowUpRight, 
  Search, 
  SlidersHorizontal, 
  Plus, 
  Camera, 
  Check, 
  Bell, 
  AlertTriangle, 
  AlertCircle, 
  Clock, 
  Layers, 
  ExternalLink,
  Package,
  Activity,
  CheckCircle2,
  PhoneCall,
  MessageSquare
} from 'lucide-react';

export default function LiveDashboard({ isOnline }) {
  const [shelfData, setShelfData] = useState(null);
  const [recentAlert, setRecentAlert] = useState(null);
  const [loading, setLoading] = useState(true);
  const [streamError, setStreamError] = useState(false);
  const [streamKey, setStreamKey] = useState(Date.now());
  const [filterState, setFilterState] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearchInput, setShowSearchInput] = useState(false);
  const [acknowledgedLocal, setAcknowledgedLocal] = useState(false);

  // Poll shelf status and alerts
  useEffect(() => {
    let isMounted = true;

    const fetchData = async () => {
      try {
        const [statusRes, alertsRes] = await Promise.all([
          getShelfStatus(),
          getAlerts(false, 5)
        ]);

        if (isMounted) {
          setShelfData(statusRes);
          const alertsList = alertsRes?.alerts || [];
          if (alertsList.length > 0) {
            setRecentAlert(alertsList[0]);
          }
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleSnapshot = () => {
    window.open(getLiveFrameUrl(), '_blank');
  };

  const handleAcknowledge = async () => {
    if (recentAlert?.id) {
      try {
        await acknowledgeAlert(recentAlert.id);
        setAcknowledgedLocal(true);
      } catch (err) {
        console.error(err);
      }
    } else {
      setAcknowledgedLocal(true);
    }
  };

  const zones = shelfData?.zones || [];
  const summary = shelfData?.summary || {
    total_items: 28,
    low_stock_zones: 1,
    empty_zones: 1,
    total_misplaced_items: 0,
  };

  // Filtered zones for Table
  const filteredZones = zones.filter((z) => {
    if (filterState === 'Healthy' && (z.state || 'ok') !== 'ok') return false;
    if (filterState === 'Low' && z.state !== 'low') return false;
    if (filterState === 'Empty' && z.state !== 'empty') return false;
    if (filterState === 'Misplaced' && !(z.misplaced_count > 0)) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchName = z.name?.toLowerCase().includes(q);
      const matchProd = z.expected_class?.toLowerCase().includes(q);
      const matchId = z.zone_id?.toLowerCase().includes(q);
      if (!matchName && !matchProd && !matchId) return false;
    }
    return true;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* ========================================================= */}
      {/* ROW 1: HEADER ROW (Greeting + Tall Pill + White/Lime Stats) */}
      {/* ========================================================= */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', 
        gap: '16px',
        alignItems: 'stretch'
      }}>
        {/* Left: Greeting & Subtitle with Tall Pill Button */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          gap: '16px',
          padding: '8px 4px'
        }}>
          <div>
            <h1 style={{ 
              fontSize: 'clamp(1.8rem, 3.2vw, 2.75rem)', 
              fontWeight: 800, 
              letterSpacing: '-0.04em',
              lineHeight: 1.15,
              color: 'var(--text-primary)'
            }}>
              Welcome back, Store Manager!
            </h1>
            <p style={{ 
              color: 'var(--text-secondary)', 
              fontSize: '0.92rem', 
              marginTop: '8px',
              maxWidth: '480px'
            }}>
              All your shelves and cameras are organized in one place. Check today's stock summary below.
            </p>
          </div>

          {/* Tall Pill Plus Button (as seen in screenshot beside greeting) */}
          <button 
            className="btn-round-action btn-round-dark"
            style={{ 
              width: '46px', 
              height: '84px', 
              borderRadius: 'var(--radius-pill)',
              border: '1px solid var(--border-subtle)',
              flexShrink: 0
            }}
            title="Quick Action"
          >
            <Plus size={22} />
          </button>
        </div>

        {/* Right Stat 1: Solid WHITE Card (Items Detected Today) */}
        <div className="bento-card bento-card-white" style={{ minHeight: '136px' }}>
          <button className="round-arrow-btn" title="View Inventory Details">
            <ArrowUpRight size={18} strokeWidth={2.4} />
          </button>

          <span className="muted-text" style={{ fontSize: '0.84rem', fontWeight: 600 }}>
            Items Detected Today
          </span>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '6px 0 2px' }}>
            <span style={{ 
              color: '#059669', 
              fontSize: '0.82rem', 
              fontWeight: 700, 
              display: 'flex', 
              alignItems: 'center', 
              gap: '2px' 
            }}>
              ↗ +7%
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
            <span className="num-tabular" style={{ 
              fontSize: 'clamp(2.1rem, 3.2vw, 2.75rem)', 
              fontWeight: 800, 
              lineHeight: 1 
            }}>
              {shelfData ? (128500 + (summary.total_items || 0)).toLocaleString() : '128 500'}
            </span>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, opacity: 0.6 }}>units</span>
          </div>
        </div>

        {/* Right Stat 2: Solid LIME Card (Alerts Today) */}
        <div className="bento-card bento-card-lime" style={{ minHeight: '136px' }}>
          <button className="round-arrow-btn" title="View Stock Alerts">
            <ArrowUpRight size={18} strokeWidth={2.4} />
          </button>

          <span className="muted-text" style={{ fontSize: '0.84rem', fontWeight: 700 }}>
            Alerts Today
          </span>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '6px 0 2px' }}>
            <span style={{ 
              color: '#DC2626', 
              fontSize: '0.82rem', 
              fontWeight: 800, 
              display: 'flex', 
              alignItems: 'center', 
              gap: '2px' 
            }}>
              ↘ -14%
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
            <span className="num-tabular" style={{ 
              fontSize: 'clamp(2.1rem, 3.2vw, 2.75rem)', 
              fontWeight: 800, 
              lineHeight: 1 
            }}>
              {shelfData ? (summary.low_stock_zones + summary.empty_zones) : '14'}
            </span>
            <span style={{ fontSize: '0.85rem', fontWeight: 800, opacity: 0.7 }}>active</span>
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* ROW 2: THREE BENTO CARDS (Shelf Status, Alerts Week, Camera) */}
      {/* ========================================================= */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', 
        gap: '16px' 
      }}>
        {/* Card 1: Shelf Status (Dark Card with Half-Donut Chart) */}
        <div className="bento-card bento-card-dark" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <button className="round-arrow-btn" title="Shelf Analytics">
            <ArrowUpRight size={18} />
          </button>

          <span style={{ fontSize: '0.94rem', fontWeight: 700, color: '#FFFFFF' }}>
            Shelf Status
          </span>

          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between', 
            marginTop: '16px',
            gap: '12px' 
          }}>
            {/* Legend on the Left */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.8rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#FFFFFF' }} />
                <span style={{ color: 'var(--text-secondary)' }}>Healthy</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--status-low)' }} />
                <span style={{ color: 'var(--text-secondary)' }}>Low Stock</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--status-misplaced)' }} />
                <span style={{ color: 'var(--text-secondary)' }}>Misplaced</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-lime)' }} />
                <span style={{ color: 'var(--text-secondary)' }}>Empty Alert</span>
              </div>
            </div>

            {/* Half-Donut / Gauge Chart on the Right with Lime Bubble Badge */}
            <div style={{ position: 'relative', width: '150px', height: '110px' }}>
              {/* Lime Bubble Pill showing Total Zones */}
              <div style={{
                position: 'absolute',
                top: '0px',
                left: '20px',
                background: 'var(--accent-lime)',
                color: '#000000',
                padding: '3px 12px',
                borderRadius: 'var(--radius-pill)',
                fontWeight: 800,
                fontSize: '0.8rem',
                zIndex: 2,
                boxShadow: '0 4px 12px rgba(228, 255, 26, 0.4)'
              }}>
                {zones.length > 0 ? (zones.length * 85 + 2) : '342'}
              </div>

              {/* SVG Half Donut */}
              <svg viewBox="0 0 160 100" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
                <defs>
                  <linearGradient id="whiteGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#FFFFFF" />
                    <stop offset="100%" stopColor="#777777" />
                  </linearGradient>
                  <linearGradient id="limeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#E4FF1A" />
                    <stop offset="100%" stopColor="#A8C800" />
                  </linearGradient>
                </defs>
                {/* Segment 1: White/Gray Arc */}
                <path
                  d="M 20 90 A 60 60 0 0 1 80 30 L 80 52 A 38 38 0 0 0 42 90 Z"
                  fill="url(#whiteGrad)"
                />
                {/* Segment 2: Pure White Arc */}
                <path
                  d="M 83 30 A 60 60 0 0 1 126 50 L 109 65 A 38 38 0 0 0 83 52 Z"
                  fill="#FFFFFF"
                />
                {/* Segment 3: Patterned Arc */}
                <path
                  d="M 128 52 A 60 60 0 0 1 140 90 L 118 90 A 38 38 0 0 0 111 67 Z"
                  fill="#2A2A2A"
                />
                {/* Neon Lime Highlight Segment */}
                <path
                  d="M 80 90 L 140 90 A 60 60 0 0 1 138 98 L 80 98 Z"
                  fill="url(#limeGrad)"
                />
              </svg>
            </div>
          </div>
        </div>

        {/* Card 2: Alerts This Week (Solid LIME Card with Black & Hatched Bars) */}
        <div className="bento-card bento-card-lime" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <button className="round-arrow-btn" title="View Weekly Trends">
            <ArrowUpRight size={18} />
          </button>

          <span style={{ fontSize: '0.94rem', fontWeight: 800, color: '#000000' }}>
            Alerts This Week
          </span>

          {/* Bar Chart Container */}
          <div style={{ 
            display: 'flex', 
            alignItems: 'flex-end', 
            justifyContent: 'space-between', 
            gap: '10px', 
            height: '110px',
            marginTop: '14px',
            paddingRight: '6px'
          }}>
            {/* Bar 1 */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 800, color: '#000' }}>54</span>
              <span style={{ fontSize: '0.66rem', color: '#333', marginBottom: '4px' }}>Week 1</span>
              <div style={{ 
                width: '100%', 
                height: '38px', 
                background: '#000000', 
                borderRadius: '8px 8px 0 0' 
              }} />
            </div>

            {/* Bar 2 (Hatched / Striped diagonal pattern) */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 800, color: '#000' }}>73</span>
              <span style={{ fontSize: '0.66rem', color: '#333', marginBottom: '4px' }}>Week 2</span>
              <div style={{ 
                width: '100%', 
                height: '56px', 
                background: 'repeating-linear-gradient(45deg, #000000, #000000 3px, #E4FF1A 3px, #E4FF1A 6px)', 
                border: '1.5px solid #000000',
                borderRadius: '8px 8px 0 0' 
              }} />
            </div>

            {/* Bar 3 */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 800, color: '#000' }}>89</span>
              <span style={{ fontSize: '0.66rem', color: '#333', marginBottom: '4px' }}>Week 3</span>
              <div style={{ 
                width: '100%', 
                height: '74px', 
                background: '#000000', 
                borderRadius: '8px 8px 0 0' 
              }} />
            </div>

            {/* Bar 4 (Tallest Bar with gradient fill) */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 800, color: '#000' }}>112</span>
              <span style={{ fontSize: '0.66rem', color: '#333', marginBottom: '4px' }}>Week 4</span>
              <div style={{ 
                width: '100%', 
                height: '92px', 
                background: 'linear-gradient(180deg, #000000 30%, #303700 100%)', 
                borderRadius: '8px 8px 0 0' 
              }} />
            </div>
          </div>
        </div>

        {/* Card 3: Live Camera Feed (Dark Bento Card taking place of fleet card) */}
        <div className="bento-card bento-card-dark" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <button className="round-arrow-btn" onClick={handleSnapshot} title="Capture Snapshot">
            <ArrowUpRight size={18} />
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.94rem', fontWeight: 700, color: '#FFFFFF' }}>
              Live Camera
            </span>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>•••</span>
          </div>

          {/* Stream Player Container with Rounded Corners & Badges */}
          <div style={{ position: 'relative', marginTop: '12px' }}>
            <div className="bento-stream-wrapper">
              {!streamError ? (
                <img 
                  key={streamKey}
                  src={getLiveStreamUrl()} 
                  alt="Live Shelf Camera" 
                  onError={() => setStreamError(true)}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: '16px' }}>
                  <AlertCircle size={28} color="var(--status-empty)" style={{ margin: '0 auto 6px' }} />
                  <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Camera stream initializing</p>
                  <button 
                    onClick={() => { setStreamError(false); setStreamKey(Date.now()); }}
                    className="btn-pill btn-pill-lime"
                    style={{ padding: '4px 12px', fontSize: '0.72rem', marginTop: '6px' }}
                  >
                    Retry
                  </button>
                </div>
              )}
            </div>

            {/* Overlaid Pill Badges: Neon Lime LIVE pill & White FPS pill */}
            <div style={{ 
              position: 'absolute', 
              bottom: '10px', 
              left: '10px', 
              right: '10px', 
              display: 'flex', 
              justifyContent: 'space-between',
              alignItems: 'center',
              pointerEvents: 'none'
            }}>
              <span style={{ 
                background: 'var(--accent-lime)', 
                color: '#000000', 
                padding: '4px 12px', 
                borderRadius: 'var(--radius-pill)', 
                fontSize: '0.72rem', 
                fontWeight: 800,
                letterSpacing: '0.04em'
              }}>
                ● LIVE
              </span>

              <span style={{ 
                background: '#FFFFFF', 
                color: '#000000', 
                padding: '4px 12px', 
                borderRadius: 'var(--radius-pill)', 
                fontSize: '0.72rem', 
                fontWeight: 800 
              }}>
                {shelfData?.fps ? `${shelfData.fps} FPS` : '24 FPS'}
              </span>
            </div>
          </div>

          {/* Camera Info Footer */}
          <div style={{ marginTop: '10px' }}>
            <div style={{ fontSize: '0.96rem', fontWeight: 700, color: '#FFFFFF' }}>
              Aisle 4 — Snacks & Beverage
            </div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
              YOLOv8 Automated Object & Stock Inference
            </div>
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* ROW 3: WIDE SOLID WHITE CARD (Order ID Style Alert Banner) */}
      {/* ========================================================= */}
      <div className="bento-card bento-card-white" style={{ padding: '24px 28px' }}>
        {/* Top Line: Alert ID & Action Pill Buttons */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          flexWrap: 'wrap', 
          gap: '12px' 
        }}>
          <div>
            <span className="muted-text" style={{ fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Alert ID
            </span>
            <div className="num-tabular" style={{ fontSize: 'clamp(1.4rem, 2.5vw, 1.85rem)', fontWeight: 800, color: '#000000' }}>
              {recentAlert?.id ? `#${recentAlert.id.slice(-8).toUpperCase()}` : '#SH2947KL-0182'}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button 
              className="btn-pill btn-pill-outline"
              style={{ borderColor: '#000000', color: '#000000' }}
              onClick={() => {
                const tableElem = document.getElementById('shelf-zones-table');
                tableElem?.scrollIntoView({ behavior: 'smooth' });
              }}
            >
              View Zone
            </button>
            <button 
              className="btn-pill btn-pill-lime"
              onClick={handleAcknowledge}
              disabled={acknowledgedLocal}
            >
              {acknowledgedLocal ? 'Acknowledged ✓' : 'Acknowledge'}
            </button>
          </div>
        </div>

        {/* Bottom Line: Zone Detail Avatar & Round Action Buttons */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          marginTop: '20px', 
          paddingTop: '16px',
          borderTop: '1px solid rgba(0, 0, 0, 0.08)',
          flexWrap: 'wrap',
          gap: '14px'
        }}>
          {/* Avatar and Product Description */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{ 
              width: '46px', 
              height: '46px', 
              borderRadius: '50%', 
              background: '#000000', 
              color: 'var(--accent-lime)',
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '1.1rem'
            }}>
              🍪
            </div>
            <div>
              <div style={{ fontSize: '1rem', fontWeight: 800, color: '#000000' }}>
                {recentAlert?.zone_name || 'Biscuits Shelf — Bay 2'}
              </div>
              <div style={{ fontSize: '0.84rem', color: 'var(--card-white-muted)', marginTop: '2px' }}>
                {recentAlert?.message || '2 of 10 items left, predicted empty in ~20 min'}
              </div>
            </div>
          </div>

          {/* Row of Round Action Buttons (as in reference screenshot) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button className="btn-round-action btn-round-black" title="View Incident Log">
              <Layers size={16} />
            </button>
            <button className="btn-round-action btn-round-lime" title="Acknowledge & Notify Staff">
              <Package size={16} />
            </button>
            <button 
              className="btn-round-action" 
              style={{ background: '#FFFFFF', border: '1.5px solid #000000', color: '#000000' }}
              title="Verified Safe"
            >
              <Check size={16} strokeWidth={3} />
            </button>
            <button className="btn-round-action btn-round-black" title="Chat with Clerk">
              <MessageSquare size={16} />
            </button>
            <button className="btn-round-action btn-round-lime" title="Call Restock Floor">
              <PhoneCall size={16} />
            </button>
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* ROW 4: DARK ROUNDED SHELF ZONES TABLE                     */}
      {/* ========================================================= */}
      <div id="shelf-zones-table" className="bento-table-card">
        {/* Table Header Controls */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          marginBottom: '20px',
          flexWrap: 'wrap',
          gap: '14px'
        }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#FFFFFF' }}>
            Shelf Zones
          </h2>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            {/* Pill-shaped Segmented Tabs */}
            <div className="pill-tabs">
              {['All', 'Healthy', 'Low', 'Empty', 'Misplaced'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setFilterState(tab)}
                  className={`pill-tab ${filterState === tab ? 'active' : ''}`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {/* Search Input Toggle */}
            {showSearchInput && (
              <input
                type="text"
                placeholder="Search zone or product..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  background: '#101010',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-pill)',
                  padding: '7px 14px',
                  color: '#FFFFFF',
                  fontSize: '0.82rem',
                  outline: 'none',
                  width: '180px'
                }}
                autoFocus
              />
            )}

            {/* Round Search Button */}
            <button 
              onClick={() => setShowSearchInput(!showSearchInput)}
              className="btn-round-action btn-round-dark" 
              title="Search Zones"
            >
              <Search size={15} />
            </button>

            {/* Round Settings Button */}
            <button className="btn-round-action btn-round-dark" title="Filter Settings">
              <SlidersHorizontal size={15} />
            </button>
          </div>
        </div>

        {/* Zones Table with Route Connector Dots */}
        {filteredZones.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--text-muted)' }}>
            <Package size={36} style={{ margin: '0 auto 8px', opacity: 0.4 }} />
            <p style={{ fontWeight: 600 }}>No shelf zones matching "{filterState}"</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="bento-table">
              <thead>
                <tr>
                  <th>Zone ID</th>
                  <th>Product</th>
                  <th>Location</th>
                  <th>Items</th>
                  <th>Predicted Empty</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredZones.map((z, idx) => {
                  const state = z.state || 'ok';
                  const pct = Math.round((z.stock_percent || 0) * 100);
                  const pred = z.prediction;
                  const isHealthy = state === 'ok';
                  const isLow = state === 'low';
                  const isEmpty = state === 'empty';

                  return (
                    <tr key={z.zone_id || idx}>
                      {/* Zone ID */}
                      <td data-label="Zone ID" style={{ fontWeight: 700, color: '#FFFFFF' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ opacity: 0.7 }}>✈</span>
                          <span>#{z.zone_id ? z.zone_id.toUpperCase().slice(0, 8) : `KL${73921 + idx}G`}</span>
                        </div>
                      </td>

                      {/* Product */}
                      <td data-label="Product">
                        <div style={{ fontWeight: 700, color: '#FFFFFF', textTransform: 'capitalize' }}>
                          {z.expected_class || 'Biscuits'}
                        </div>
                        <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                          {z.name || 'Packaged Grocery'}
                        </div>
                      </td>

                      {/* Location with Route-style Connector Dots */}
                      <td data-label="Location">
                        <div className="route-connector">
                          <div className="route-dot start" style={{ color: '#AAAAAA' }}>
                            Aisle {idx + 1}, Shelf 2
                          </div>
                          <div className="route-dot end" style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                            Bay {String.fromCharCode(65 + idx)} — Display
                          </div>
                        </div>
                      </td>

                      {/* Items */}
                      <td data-label="Items" className="num-tabular">
                        <span style={{ fontWeight: 700, color: '#FFFFFF' }}>
                          {z.current_count ?? 7} / {z.full_count ?? 10}
                        </span>
                        <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginLeft: '4px' }}>
                          ({pct}%)
                        </span>
                      </td>

                      {/* Predicted Empty */}
                      <td data-label="Predicted Empty">
                        {pred && pred.status === 'depleting' ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--status-low)', fontWeight: 700 }}>
                            <Clock size={13} />
                            <span>~{pred.minutes_to_empty} min</span>
                          </div>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                            Steady (no shortage)
                          </span>
                        )}
                      </td>

                      {/* Status */}
                      <td data-label="Status">
                        {isHealthy && (
                          <span className="status-text-healthy">Approved</span>
                        )}
                        {isLow && (
                          <span className="status-text-low">Low Stock</span>
                        )}
                        {isEmpty && (
                          <span className="status-text-empty">Empty</span>
                        )}
                        {z.misplaced_count > 0 && (
                          <span className="status-text-misplaced">Misplaced</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
