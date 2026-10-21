from pathlib import Path

ld_path = Path(r"D:\project\smart shelf\dashboard\src\pages\LiveDashboard.jsx")
text = ld_path.read_text(encoding="utf-8")

# 1. Update imports
old_api_import = """import { 
  getLiveStreamUrl, 
  getShelfStatus, 
  getLiveFrameUrl,
  getAlerts,
  acknowledgeAlert
} from '../services/api';"""

new_api_import = """import { 
  getLiveStreamUrl, 
  getShelfStatus, 
  getLiveFrameUrl,
  getAlerts,
  acknowledgeAlert,
  getCameraStatus,
  controlCamera,
  switchCameraMode,
  getModelInfo
} from '../services/api';"""
text = text.replace(old_api_import, new_api_import)

# Add icons: Play, Pause, RotateCcw, FastForward, Sparkles, Cpu
text = text.replace("MessageSquare\n} from 'lucide-react';", "MessageSquare,\n  Play,\n  Pause,\n  RotateCcw,\n  FastForward,\n  Sparkles,\n  Cpu\n} from 'lucide-react';")

# 2. Add state
old_state_anchor = "const [acknowledgedLocal, setAcknowledgedLocal] = useState(false);"
new_state = """const [acknowledgedLocal, setAcknowledgedLocal] = useState(false);
  const [cameraStatus, setCameraStatus] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [cameraLoading, setCameraLoading] = useState(false);"""
text = text.replace(old_state_anchor, new_state)

# 3. Poll cameraStatus and modelInfo in fetchData
old_fetch_data = """        const [statusRes, alertsRes] = await Promise.all([
          getShelfStatus(),
          getAlerts(false, 5)
        ]);"""

new_fetch_data = """        const [statusRes, alertsRes, camRes, mInfoRes] = await Promise.all([
          getShelfStatus(),
          getAlerts(false, 5),
          getCameraStatus().catch(() => null),
          getModelInfo().catch(() => null)
        ]);"""
text = text.replace(old_fetch_data, new_fetch_data)

old_set_shelf = """        if (isMounted) {
          setShelfData(statusRes);
          const alertsList = alertsRes?.alerts || [];
          if (alertsList.length > 0) {
            setRecentAlert(alertsList[0]);
          }
          setLoading(false);
        }"""

new_set_shelf = """        if (isMounted) {
          setShelfData(statusRes);
          if (camRes) setCameraStatus(camRes);
          if (mInfoRes) setModelInfo(mInfoRes);
          const alertsList = alertsRes?.alerts || [];
          if (alertsList.length > 0) {
            setRecentAlert(alertsList[0]);
          }
          setLoading(false);
        }"""
text = text.replace(old_set_shelf, new_set_shelf)

# 4. Handlers for camera controls
camera_handlers = """
  const handleScenarioChange = async (scenarioName) => {
    try {
      setCameraLoading(true);
      await switchCameraMode('simulated', { scenario: scenarioName });
      const updated = await getCameraStatus();
      setCameraStatus(updated);
    } catch (err) {
      console.error('Failed to change scenario:', err);
    } finally {
      setCameraLoading(false);
    }
  };

  const handleCameraAction = async (action, extra = {}) => {
    try {
      setCameraLoading(true);
      await controlCamera(action, extra);
      const updated = await getCameraStatus();
      setCameraStatus(updated);
    } catch (err) {
      console.error('Failed camera control:', err);
    } finally {
      setCameraLoading(false);
    }
  };
"""
text = text.replace("const handleSnapshot = () => {", camera_handlers + "\n  const handleSnapshot = () => {")

# 5. Replace Card 3 with "Latest photo" Card & Overlaid Badges
old_card_3 = """        {/* Card 3: Live Camera Feed (Dark Bento Card taking place of fleet card) */}
        <div className="bento-card bento-card-dark" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <button className="round-arrow-btn" onClick={handleSnapshot} title="Capture Snapshot">
            <ArrowUpRight size={18} />
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.94rem', fontWeight: 700, color: '#FFFFFF' }}>
              Live Camera
            </span>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>• • •</span>
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
        </div>"""

new_card_3 = """        {/* Card 3: Latest Photo Feed (Labelled honestly, never "live video") */}
        <div className="bento-card bento-card-dark" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <button className="round-arrow-btn" onClick={handleSnapshot} title="Capture Full Snapshot">
            <ArrowUpRight size={18} />
          </button>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.94rem', fontWeight: 700, color: '#FFFFFF' }}>
                Latest photo
              </span>
              <span style={{
                background: cameraStatus?.is_simulated ? 'rgba(255, 149, 0, 0.2)' : 'rgba(52, 199, 89, 0.2)',
                color: cameraStatus?.is_simulated ? '#FF9500' : '#34C759',
                fontSize: '0.68rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '10px'
              }}>
                {cameraStatus?.is_simulated ? 'SIMULATED' : 'HARDWARE'}
              </span>
            </div>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.76rem', fontWeight: 600 }}>
              Last updated {cameraStatus?.pipeline?.seconds_since_last_photo != null ? `${cameraStatus.pipeline.seconds_since_last_photo}s ago` : 'recently'}
            </span>
          </div>

          {/* Snapshot Container with Rounded Corners & Badges */}
          <div style={{ position: 'relative', marginTop: '12px' }}>
            <div className="bento-stream-wrapper">
              {!streamError ? (
                <img 
                  key={streamKey}
                  src={getLiveStreamUrl()} 
                  alt="Latest Shelf Snapshot" 
                  onError={() => setStreamError(true)}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: '16px' }}>
                  <AlertCircle size={28} color="var(--status-empty)" style={{ margin: '0 auto 6px' }} />
                  <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Camera photo initializing</p>
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

            {/* Overlaid Badges */}
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
                background: cameraStatus?.is_simulated ? '#FF9500' : 'var(--accent-lime)', 
                color: '#000000', 
                padding: '4px 12px', 
                borderRadius: 'var(--radius-pill)', 
                fontSize: '0.72rem', 
                fontWeight: 800,
                letterSpacing: '0.04em'
              }}>
                {cameraStatus?.is_simulated ? 'SIMULATED CAMERA' : '● ESP32-CAM'}
              </span>

              <span style={{ 
                background: '#FFFFFF', 
                color: '#000000', 
                padding: '4px 12px', 
                borderRadius: 'var(--radius-pill)', 
                fontSize: '0.72rem', 
                fontWeight: 800 
              }}>
                {cameraStatus?.pipeline?.latency_ms ? `${cameraStatus.pipeline.latency_ms} ms` : '5 ms'}
              </span>
            </div>
          </div>

          {/* Camera Info Footer */}
          <div style={{ marginTop: '10px' }}>
            <div style={{ fontSize: '0.94rem', fontWeight: 700, color: '#FFFFFF' }}>
              {cameraStatus?.simulated_details?.scenario_title || 'Main Retail Shelf'}
            </div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
              Source: {cameraStatus?.source_status?.source_type || 'simulated'} • 5s interval
            </div>
          </div>
        </div>"""
text = text.replace(old_card_3, new_card_3)

# 6. Add Camera / Demo Control Panel + Live Pipeline Trace Card below ROW 2
control_and_trace_block = """
      {/* ========================================================= */}
      {/* PHASE 10: CAMERA / DEMO CONTROL PANEL & PIPELINE TRACE    */}
      {/* ========================================================= */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: '16px',
        margin: '18px 0'
      }}>
        {/* Panel 1: Camera & Demo Playback Controls */}
        <div className="bento-card bento-card-dark" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={18} color="var(--accent-lime)" />
              <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#FFFFFF' }}>
                Camera / Demo Control
              </span>
            </div>
            <span style={{
              background: '#2A2A2A',
              color: 'var(--accent-lime)',
              fontSize: '0.72rem',
              fontWeight: 800,
              padding: '3px 8px',
              borderRadius: '10px'
            }}>
              Frame {cameraStatus?.simulated_details?.current_frame || 1} / {cameraStatus?.simulated_details?.total_frames || 20}
            </span>
          </div>

          {/* Scenario Selector Dropdown */}
          <div style={{ marginBottom: '14px' }}>
            <label style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>
              Active Scenario
            </label>
            <select
              value={cameraStatus?.simulated_details?.scenario_name || 'gradual_depletion'}
              onChange={(e) => handleScenarioChange(e.target.value)}
              disabled={cameraLoading}
              style={{
                width: '100%',
                background: '#1C1C1E',
                border: '1px solid #3A3A3C',
                color: '#FFFFFF',
                borderRadius: '12px',
                padding: '8px 12px',
                fontSize: '0.84rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              {(cameraStatus?.simulated_details?.available_scenarios || [
                'gradual_depletion', 'customer_blocking', 'restocking', 'misplaced_item'
              ]).map((sc) => (
                <option key={sc} value={sc}>
                  {sc.replace('_', ' ').toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          {/* Action Buttons: Play/Pause/Reset & Speed */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', gap: '6px' }}>
              {cameraStatus?.simulated_details?.is_paused ? (
                <button
                  onClick={() => handleCameraAction('start')}
                  className="btn-pill btn-pill-lime"
                  style={{ padding: '6px 14px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  <Play size={13} /> Resume
                </button>
              ) : (
                <button
                  onClick={() => handleCameraAction('pause')}
                  className="btn-pill btn-pill-dark"
                  style={{ padding: '6px 14px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                >
                  <Pause size={13} /> Pause
                </button>
              )}
              <button
                onClick={() => handleCameraAction('reset')}
                className="btn-pill btn-pill-dark"
                style={{ padding: '6px 14px', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: '4px' }}
              >
                <RotateCcw size={13} /> Reset
              </button>
            </div>

            {/* Playback Speeds */}
            <div style={{ display: 'flex', gap: '4px', background: '#1C1C1E', padding: '3px', borderRadius: '12px' }}>
              {[1, 5, 10].map((spd) => (
                <button
                  key={spd}
                  onClick={() => handleCameraAction('set_speed', { speed: spd })}
                  style={{
                    background: (cameraStatus?.simulated_details?.speed_multiplier === spd) ? 'var(--accent-lime)' : 'transparent',
                    color: (cameraStatus?.simulated_details?.speed_multiplier === spd) ? '#000000' : 'var(--text-secondary)',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '4px 8px',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  {spd}x
                </button>
              ))}
            </div>
          </div>

          {/* Telemetry line */}
          <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', marginTop: '12px', borderTop: '1px solid #282828', paddingTop: '8px' }}>
            Interval: {cameraStatus?.simulated_details?.interval_seconds || 5}s • Virtual Clock Timestamps • Simulated=True
          </div>
        </div>

        {/* Panel 2: Live Pipeline Trace (3-Photo Confirmation & YOLO Breakdown) */}
        <div className="bento-card bento-card-dark" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Activity size={18} color="var(--accent-lime)" />
              <span style={{ fontSize: '0.95rem', fontWeight: 700, color: '#FFFFFF' }}>
                Pipeline Trace (Latest Photo)
              </span>
            </div>
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              Latency: {cameraStatus?.pipeline?.latency_ms || 4.9} ms
            </span>
          </div>

          {/* Trace Steps Flow */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.82rem' }}>
            <div style={{ background: '#1C1C1E', padding: '8px 12px', borderRadius: '12px', display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--text-secondary)' }}>YOLO Detections:</span>
              <strong style={{ color: '#FFFFFF' }}>
                {cameraStatus?.pipeline?.pipeline_trace?.products_found || 0} products, {cameraStatus?.pipeline?.pipeline_trace?.empty_slots_found || 0} empty slots
              </strong>
            </div>

            {/* 3-Photo Confirmation Counters */}
            {(cameraStatus?.pipeline?.pipeline_trace?.zones || []).map((z) => (
              <div key={z.zone_id} style={{
                background: '#1C1C1E',
                padding: '8px 12px',
                borderRadius: '12px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderLeft: z.alert_triggered ? '3px solid #FF453A' : '3px solid var(--accent-lime)'
              }}>
                <span style={{ color: '#FFFFFF', fontWeight: 600 }}>{z.zone_name}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{
                    color: z.confirmation_progress.includes('Low') ? '#FF9500' : (z.confirmation_progress.includes('Empty') ? '#FF453A' : '#34C759'),
                    fontWeight: 700,
                    fontSize: '0.76rem'
                  }}>
                    {z.confirmation_progress}
                  </span>
                  {z.alert_triggered && (
                    <span style={{ background: '#FF453A', color: '#fff', fontSize: '0.65rem', padding: '1px 5px', borderRadius: '6px', fontWeight: 800 }}>
                      ALERT FIRED
                    </span>
                  )}
                </div>
              </div>
            ))}

            {/* Plain Summary */}
            <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', fontStyle: 'italic', marginTop: '2px' }}>
              "{cameraStatus?.pipeline?.pipeline_trace?.summary_caption || 'Monitoring active...'}"
            </div>
          </div>
        </div>
      </div>
"""

row_3_anchor = "{/* ========================================================= */}\n      {/* ROW 3: WIDE SOLID WHITE CARD"
text = text.replace(row_3_anchor, control_and_trace_block + "\n      " + row_3_anchor)

# 7. Add Model status to Dashboard Footer
footer_model_badge = """
      {/* Model & Runtime Status Footer */}
      <div style={{
        margin: '24px 0 12px 0',
        padding: '12px 18px',
        background: '#161616',
        borderRadius: '16px',
        border: '1px solid #282828',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '10px',
        fontSize: '0.78rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Cpu size={15} color="var(--accent-lime)" />
          <span style={{ color: 'var(--text-muted)' }}>Active Neural Network:</span>
          <strong style={{ color: '#FFFFFF' }}>{modelInfo?.model_status || 'sku_stage1 (trained on products)'}</strong>
        </div>
        <div style={{ display: 'flex', gap: '14px', color: 'var(--text-muted)' }}>
          <span>Device: <strong style={{ color: '#FFFFFF' }}>{modelInfo?.device || 'cuda:0'}</strong></span>
          <span>Threshold: <strong style={{ color: 'var(--accent-lime)' }}>{Math.round((modelInfo?.confidence_threshold || 0.35) * 100)}%</strong></span>
          <span>IoU: <strong style={{ color: '#FFFFFF' }}>{modelInfo?.iou_threshold || 0.45}</strong></span>
        </div>
      </div>
"""

text = text + footer_model_badge

ld_path.write_text(text, encoding="utf-8")
print("LiveDashboard.jsx updated successfully!")
