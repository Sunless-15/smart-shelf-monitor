from pathlib import Path

settings_path = Path(r"D:\project\smart shelf\dashboard\src\pages\ZonesSettingsView.jsx")
text = settings_path.read_text(encoding="utf-8")

# 1. Update imports
old_imp = """import { 
  getZones, 
  createZone, 
  updateZone, 
  deleteZone, 
  getSource, 
  switchSource, 
  getLiveFrameUrl 
} from '../services/api';"""

new_imp = """import { 
  getZones, 
  createZone, 
  updateZone, 
  deleteZone, 
  getSource, 
  switchSource, 
  getLiveFrameUrl,
  getModelInfo,
  updateModelConfig,
  getCameraStatus,
  switchCameraMode,
  clearSimulatedData
} from '../services/api';"""
text = text.replace(old_imp, new_imp)

# Add icons: SlidersHorizontal, Cpu, Trash, ShieldAlert
text = text.replace("AlertCircle\n} from 'lucide-react';", "AlertCircle,\n  SlidersHorizontal,\n  Cpu,\n  Trash,\n  ShieldAlert,\n  Sparkles\n} from 'lucide-react';")

# 2. Add state for thresholds, camera mode, and simulated data
old_state = "const [snapshotKey, setSnapshotKey] = useState(Date.now());"
new_state = """const [snapshotKey, setSnapshotKey] = useState(Date.now());
  const [modelInfo, setModelInfo] = useState(null);
  const [confThreshold, setConfThreshold] = useState(0.35);
  const [iouThreshold, setIouThreshold] = useState(0.45);
  const [savingThresholds, setSavingThresholds] = useState(false);
  const [cameraStatus, setCameraStatus] = useState(null);
  const [cameraMode, setCameraMode] = useState('simulated');
  const [esp32Ip, setEsp32Ip] = useState('192.168.1.50');
  const [clearingSimulated, setClearingSimulated] = useState(false);"""
text = text.replace(old_state, new_state)

# 3. Load modelInfo and cameraStatus in loadData
old_load = """      const [zonesData, srcData] = await Promise.all([getZones(), getSource()]);
      setZones(zonesData || []);
      setSourceStatus(srcData);
      setSelectedSourceType(srcData.type || 'video');
      setSourceValueInput(srcData.value || '');"""

new_load = """      const [zonesData, srcData, mInfo, camStat] = await Promise.all([
        getZones(),
        getSource(),
        getModelInfo().catch(() => null),
        getCameraStatus().catch(() => null)
      ]);
      setZones(zonesData || []);
      setSourceStatus(srcData);
      setSelectedSourceType(srcData.type || 'video');
      setSourceValueInput(srcData.value || '');
      if (mInfo) {
        setModelInfo(mInfo);
        if (mInfo.confidence_threshold) setConfThreshold(mInfo.confidence_threshold);
        if (mInfo.iou_threshold) setIouThreshold(mInfo.iou_threshold);
      }
      if (camStat) {
        setCameraStatus(camStat);
        setCameraMode(camStat.camera_mode || 'simulated');
        if (camStat.source_status?.esp32_ip) setEsp32Ip(camStat.source_status.esp32_ip);
      }"""
text = text.replace(old_load, new_load)

# 4. Handlers for Thresholds, Camera Switch, and Clear Simulated
handlers = """
  const handleSaveThresholds = async () => {
    setSavingThresholds(true);
    try {
      const res = await updateModelConfig({
        confidence_threshold: confThreshold,
        iou_threshold: iouThreshold
      });
      setModelInfo(res.model_info);
      setMessage({ type: 'success', text: 'Model thresholds updated live across entire system!' });
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to update model thresholds.' });
    } finally {
      setSavingThresholds(false);
    }
  };

  const handleSwitchCameraMode = async (newMode) => {
    try {
      setSourceLoading(true);
      const res = await switchCameraMode(newMode, { esp32_ip: esp32Ip });
      setCameraMode(newMode);
      setCameraStatus(res.camera_status);
      setMessage({ type: 'success', text: `Camera source switched to: ${newMode}` });
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to switch camera mode.' });
    } finally {
      setSourceLoading(false);
    }
  };

  const handleClearSimulated = async () => {
    if (!window.confirm('Delete all simulated history snapshots and alerts from database?')) return;
    setClearingSimulated(true);
    try {
      const res = await clearSimulatedData();
      setMessage({
        type: 'success',
        text: `Cleared ${res.deleted_history_count} history records and ${res.deleted_alerts_count} alerts.`
      });
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to clear simulated records.' });
    } finally {
      setClearingSimulated(false);
    }
  };
"""
text = text.replace("const handleEditZone = (zone) => {", handlers + "\n  const handleEditZone = (zone) => {")

# 5. Insert Phase 10 Cards right above Section 1
new_cards = """      {/* Phase 10: Model Config & Hardware Camera Abstraction */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px', marginBottom: '20px' }}>
        
        {/* Model Thresholds Card */}
        <div className="bento-card bento-card-dark" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Cpu size={20} color="var(--accent-lime)" />
              <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
                YOLO Neural Network Parameters
              </h2>
            </div>
            <span style={{
              background: '#2A2A2A',
              color: 'var(--accent-lime)',
              fontSize: '0.72rem',
              fontWeight: 800,
              padding: '3px 8px',
              borderRadius: '10px'
            }}>
              {modelInfo?.model_status || 'sku_stage1 (trained)'}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '4px' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Confidence Threshold</span>
                <strong style={{ color: 'var(--accent-lime)' }}>{Math.round(confThreshold * 100)}%</strong>
              </div>
              <input
                type="range"
                min="0.10"
                max="0.85"
                step="0.05"
                value={confThreshold}
                onChange={(e) => setConfThreshold(parseFloat(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--accent-lime)', cursor: 'pointer' }}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '4px' }}>
                <span style={{ color: 'var(--text-secondary)' }}>IoU NMS Overlap Threshold</span>
                <strong style={{ color: '#FFFFFF' }}>{iouThreshold}</strong>
              </div>
              <input
                type="range"
                min="0.20"
                max="0.80"
                step="0.05"
                value={iouThreshold}
                onChange={(e) => setIouThreshold(parseFloat(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--accent-lime)', cursor: 'pointer' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px' }}>
              <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                Device: {modelInfo?.device || 'cuda:0'}
              </span>
              <button
                onClick={handleSaveThresholds}
                disabled={savingThresholds}
                className="btn-pill btn-pill-lime"
                style={{ padding: '6px 16px', fontSize: '0.78rem' }}
              >
                {savingThresholds ? 'Saving...' : 'Apply Thresholds'}
              </button>
            </div>
          </div>
        </div>

        {/* Camera Layer & Hardware Switchover Card */}
        <div className="bento-card bento-card-dark" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Camera size={20} color="var(--accent-lime)" />
              <h2 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#FFFFFF', margin: 0 }}>
                Camera Source Layer
              </h2>
            </div>
            <span style={{
              background: cameraMode === 'simulated' ? 'rgba(255, 149, 0, 0.2)' : 'rgba(52, 199, 89, 0.2)',
              color: cameraMode === 'simulated' ? '#FF9500' : '#34C759',
              fontSize: '0.72rem',
              fontWeight: 800,
              padding: '3px 8px',
              borderRadius: '10px'
            }}>
              {cameraMode.toUpperCase()}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', marginBottom: '12px' }}>
            {[
              { id: 'simulated', label: 'Simulated Scenarios' },
              { id: 'esp32_pull', label: 'ESP32 Pull (HTTP)' },
              { id: 'esp32_push', label: 'ESP32 Push (POST)' },
              { id: 'video_file', label: 'Video File Replay' }
            ].map((m) => (
              <button
                key={m.id}
                onClick={() => handleSwitchCameraMode(m.id)}
                style={{
                  background: cameraMode === m.id ? 'var(--accent-lime)' : '#1C1C1E',
                  color: cameraMode === m.id ? '#000000' : '#FFFFFF',
                  border: '1px solid #3A3A3C',
                  borderRadius: '12px',
                  padding: '8px',
                  fontSize: '0.76rem',
                  fontWeight: 700,
                  cursor: 'pointer'
                }}
              >
                {m.label}
              </button>
            ))}
          </div>

          {cameraMode === 'esp32_pull' && (
            <div style={{ marginBottom: '12px' }}>
              <label style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                ESP32-CAM Local IP Address
              </label>
              <input
                type="text"
                value={esp32Ip}
                onChange={(e) => setEsp32Ip(e.target.value)}
                placeholder="192.168.1.50"
                style={{
                  width: '100%',
                  background: '#1C1C1E',
                  border: '1px solid #3A3A3C',
                  borderRadius: '10px',
                  padding: '6px 12px',
                  color: '#fff',
                  fontSize: '0.82rem'
                }}
              />
            </div>
          )}

          {/* Clear Simulated Data Action */}
          <div style={{ borderTop: '1px solid #282828', paddingTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              Clean simulated testing data
            </span>
            <button
              onClick={handleClearSimulated}
              disabled={clearingSimulated}
              style={{
                background: 'rgba(255, 69, 58, 0.15)',
                border: '1px solid #FF453A',
                color: '#FF453A',
                borderRadius: '10px',
                padding: '4px 10px',
                fontSize: '0.74rem',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              {clearingSimulated ? 'Clearing...' : 'Clear Simulated Data'}
            </button>
          </div>
        </div>

      </div>
"""

sec1_anchor = "{/* Section 1: Video Source Layer Config */}"
text = text.replace(sec1_anchor, new_cards + "\n      " + sec1_anchor)
settings_path.write_text(text, encoding="utf-8")
print("ZonesSettingsView.jsx updated successfully!")
