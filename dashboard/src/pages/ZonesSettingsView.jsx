import React, { useState, useEffect } from 'react';
import { 
  getZones, 
  createZone, 
  updateZone, 
  deleteZone, 
  getSource, 
  switchSource, 
  getLiveFrameUrl 
} from '../services/api';
import { 
  Sliders, 
  Video, 
  Camera, 
  Globe, 
  Plus, 
  Trash2, 
  Save, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle,
  Eye
} from 'lucide-react';

export default function ZonesSettingsView() {
  const [zones, setZones] = useState([]);
  const [sourceStatus, setSourceStatus] = useState(null);
  const [selectedSourceType, setSelectedSourceType] = useState('video');
  const [sourceValueInput, setSourceValueInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sourceLoading, setSourceLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [snapshotKey, setSnapshotKey] = useState(Date.now());

  // Editing zone state
  const [editingZoneId, setEditingZoneId] = useState(null);
  const [zoneForm, setZoneForm] = useState({
    name: '',
    expected_class: 'bottle',
    full_count: 5,
    low_threshold: 0.35,
    coords: { x1: 0.1, y1: 0.1, x2: 0.5, y2: 0.5 }
  });

  const loadData = async () => {
    try {
      setLoading(true);
      const [zonesData, srcData] = await Promise.all([getZones(), getSource()]);
      setZones(zonesData || []);
      setSourceStatus(srcData);
      setSelectedSourceType(srcData.type || 'video');
      setSourceValueInput(srcData.value || '');
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSourceSwitch = async () => {
    setSourceLoading(true);
    setMessage(null);
    try {
      const res = await switchSource(selectedSourceType, sourceValueInput);
      setSourceStatus(res.source);
      setMessage({ type: 'success', text: res.message || 'Source switched successfully!' });
      setSnapshotKey(Date.now());
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.message || 'Failed to switch source.' });
    } finally {
      setSourceLoading(false);
    }
  };

  const handleEditZone = (zone) => {
    const zid = zone.id || zone._id;
    setEditingZoneId(zid);
    setZoneForm({
      name: zone.name,
      expected_class: zone.expected_class,
      full_count: zone.full_count,
      low_threshold: zone.low_threshold,
      coords: { ...zone.coords }
    });
  };

  const handleSaveZone = async () => {
    try {
      if (editingZoneId === 'new') {
        const created = await createZone(zoneForm);
        setZones([...zones, created]);
        setMessage({ type: 'success', text: `Zone "${zoneForm.name}" created.` });
      } else {
        const updated = await updateZone(editingZoneId, zoneForm);
        setZones(zones.map((z) => ((z.id || z._id) === editingZoneId ? updated : z)));
        setMessage({ type: 'success', text: `Zone "${zoneForm.name}" updated.` });
      }
      setEditingZoneId(null);
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to save zone.' });
    }
  };

  const handleDeleteZone = async (zid) => {
    if (!confirm('Are you sure you want to delete this shelf zone?')) return;
    try {
      await deleteZone(zid);
      setZones(zones.filter((z) => (z.id || z._id) !== zid));
      if (editingZoneId === zid) setEditingZoneId(null);
      setMessage({ type: 'success', text: 'Zone deleted.' });
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to delete zone.' });
    }
  };

  const startNewZone = () => {
    setEditingZoneId('new');
    setZoneForm({
      name: `Zone ${zones.length + 1}`,
      expected_class: 'bottle',
      full_count: 5,
      low_threshold: 0.35,
      coords: { x1: 0.15, y1: 0.2, x2: 0.85, y2: 0.6 }
    });
  };

  return (
    <div>
      {/* Toast Alert */}
      {message && (
        <div style={{
          background: message.type === 'success' ? 'var(--status-ok-bg)' : 'var(--status-empty-bg)',
          color: message.type === 'success' ? 'var(--status-ok)' : 'var(--status-empty)',
          border: `1px solid ${message.type === 'success' ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)'}`,
          padding: '0.75rem 1rem',
          borderRadius: 'var(--radius-md)',
          marginBottom: '1.25rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.9rem',
          fontWeight: 600
        }}>
          {message.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Section 1: Video Source Layer Config */}
      <div className="glass-card" style={{ marginBottom: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', marginBottom: '0.5rem' }}>
          <Video size={22} color="var(--accent-blue)" />
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Pluggable Video Source</h2>
        </div>
        <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>
          Switch camera feeds seamlessly at runtime. Select local webcam, looped demo video, or paste the ESP32-CAM MJPEG stream URL (e.g. <code>http://&lt;esp32-ip&gt;:81/stream</code>).
        </p>

        {/* Source Radio Selector */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '1.25rem' }}>
          {[
            { id: 'webcam', label: 'Laptop Webcam', icon: Camera, defaultVal: '0' },
            { id: 'video', label: 'Sample Video File', icon: Video, defaultVal: 'sample_data/sample_shelf.mp4' },
            { id: 'stream', label: 'ESP32-CAM Stream', icon: Globe, defaultVal: 'http://192.168.1.100:81/stream' },
          ].map((src) => {
            const Icon = src.icon;
            const isSelected = selectedSourceType === src.id;
            return (
              <div
                key={src.id}
                onClick={() => {
                  setSelectedSourceType(src.id);
                  setSourceValueInput(src.defaultVal);
                }}
                style={{
                  background: isSelected ? 'rgba(59, 130, 246, 0.15)' : 'var(--bg-input)',
                  border: isSelected ? '1px solid var(--accent-blue)' : '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '0.9rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.65rem',
                  transition: 'var(--transition)'
                }}
              >
                <Icon size={18} color={isSelected ? 'var(--accent-blue)' : 'var(--text-muted)'} />
                <span style={{ fontSize: '0.88rem', fontWeight: 600 }}>{src.label}</span>
              </div>
            );
          })}
        </div>

        {/* Source Value Input */}
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '240px' }}>
            <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
              {selectedSourceType === 'webcam' && 'Webcam Device Index (0 = built-in camera, 1 = external USB)'}
              {selectedSourceType === 'video' && 'Path to Video File on Disk (looped playback)'}
              {selectedSourceType === 'stream' && 'ESP32-CAM / MJPEG HTTP Stream URL'}
            </label>
            <input 
              type="text" 
              value={sourceValueInput} 
              onChange={(e) => setSourceValueInput(e.target.value)} 
              placeholder={selectedSourceType === 'stream' ? 'http://192.168.1.100:81/stream' : 'Source value'} 
              className="input-field"
            />
          </div>

          <button 
            onClick={handleSourceSwitch} 
            disabled={sourceLoading}
            className="btn btn-primary"
            style={{ minHeight: '42px', marginTop: '1.25rem' }}
          >
            <Save size={16} />
            <span>{sourceLoading ? 'Switching...' : 'Apply Video Source'}</span>
          </button>
        </div>

        {/* Active Source Health Badge */}
        {sourceStatus && (
          <div style={{ marginTop: '1rem', fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span>Active Source: <strong style={{ color: 'var(--text-primary)' }}>{sourceStatus.type}</strong> ({sourceStatus.value})</span>
            <span className={`badge ${sourceStatus.is_active ? 'badge-ok' : 'badge-empty'}`}>
              {sourceStatus.is_active ? 'ACTIVE' : 'OFFLINE'}
            </span>
          </div>
        )}
      </div>

      {/* Section 2: Shelf Zones Configuration & Visual Alignment */}
      <div className="glass-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Sliders size={20} color="var(--accent-cyan)" />
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Shelf Zone Definitions</h2>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Configure named normalized detection rectangles (0.0 to 1.0 coordinates)
            </p>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button 
              onClick={() => setSnapshotKey(Date.now())} 
              className="btn btn-secondary" 
              style={{ minHeight: '34px', fontSize: '0.8rem' }}
            >
              <RefreshCw size={14} /> Refresh Snapshot
            </button>
            <button 
              onClick={startNewZone} 
              className="btn btn-primary" 
              style={{ minHeight: '34px', fontSize: '0.8rem' }}
            >
              <Plus size={14} /> Add Shelf Zone
            </button>
          </div>
        </div>

        {/* Live Visual Snapshot Overlay Preview */}
        <div style={{ 
          position: 'relative', 
          width: '100%', 
          aspectRatio: '16 / 9', 
          background: '#000', 
          borderRadius: 'var(--radius-md)', 
          overflow: 'hidden', 
          marginBottom: '1.5rem',
          border: '1px solid var(--border-subtle)'
        }}>
          <img 
            key={snapshotKey}
            src={`${getLiveFrameUrl()}&_k=${snapshotKey}`} 
            alt="Zone Calibration Snapshot" 
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />

          {/* Render zone preview boxes over the image */}
          {zones.map((z) => {
            const isEditing = editingZoneId === (z.id || z._id);
            const c = isEditing ? zoneForm.coords : z.coords;
            const left = `${(c.x1 || 0) * 100}%`;
            const top = `${(c.y1 || 0) * 100}%`;
            const width = `${Math.max(2, ((c.x2 || 1) - (c.x1 || 0)) * 100)}%`;
            const height = `${Math.max(2, ((c.y2 || 1) - (c.y1 || 0)) * 100)}%`;

            return (
              <div 
                key={z.id || z._id}
                style={{
                  position: 'absolute',
                  left,
                  top,
                  width,
                  height,
                  border: isEditing ? '2px solid #3b82f6' : '2px dashed #10b981',
                  background: isEditing ? 'rgba(59, 130, 246, 0.2)' : 'rgba(16, 185, 129, 0.1)',
                  pointerEvents: 'none',
                  display: 'flex',
                  alignItems: 'flex-start',
                  padding: '2px 4px'
                }}
              >
                <span style={{ 
                  background: isEditing ? '#3b82f6' : '#10b981', 
                  color: '#fff', 
                  fontSize: '10px', 
                  fontWeight: 700, 
                  padding: '1px 4px', 
                  borderRadius: '3px' 
                }}>
                  {z.name}
                </span>
              </div>
            );
          })}
        </div>

        {/* Zone Editor Modal / Form */}
        {editingZoneId && (
          <div style={{
            background: 'rgba(255, 255, 255, 0.04)',
            border: '1px solid var(--accent-blue)',
            borderRadius: 'var(--radius-md)',
            padding: '1.25rem',
            marginBottom: '1.5rem'
          }}>
            <h4 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '1rem' }}>
              {editingZoneId === 'new' ? 'New Shelf Zone' : `Editing: ${zoneForm.name}`}
            </h4>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Zone Name</label>
                <input 
                  type="text" 
                  value={zoneForm.name} 
                  onChange={(e) => setZoneForm({ ...zoneForm, name: e.target.value })} 
                  className="input-field" 
                />
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Expected Product Class (COCO/YOLO)</label>
                <input 
                  type="text" 
                  value={zoneForm.expected_class} 
                  onChange={(e) => setZoneForm({ ...zoneForm, expected_class: e.target.value.toLowerCase() })} 
                  className="input-field" 
                />
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Full Capacity Count</label>
                <input 
                  type="number" 
                  min="1" 
                  value={zoneForm.full_count} 
                  onChange={(e) => setZoneForm({ ...zoneForm, full_count: parseInt(e.target.value) || 1 })} 
                  className="input-field" 
                />
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Low Stock Threshold (0.0 - 1.0)</label>
                <input 
                  type="number" 
                  step="0.05" 
                  min="0.05" 
                  max="0.9" 
                  value={zoneForm.low_threshold} 
                  onChange={(e) => setZoneForm({ ...zoneForm, low_threshold: parseFloat(e.target.value) || 0.35 })} 
                  className="input-field" 
                />
              </div>
            </div>

            {/* Coordinates (x1, y1, x2, y2) */}
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem' }}>
                Normalized Coordinates (X1: {zoneForm.coords.x1}, Y1: {zoneForm.coords.y1}, X2: {zoneForm.coords.x2}, Y2: {zoneForm.coords.y2})
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem' }}>
                {['x1', 'y1', 'x2', 'y2'].map((coordKey) => (
                  <div key={coordKey}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{coordKey}</span>
                    <input 
                      type="number" 
                      step="0.02" 
                      min="0.0" 
                      max="1.0" 
                      value={zoneForm.coords[coordKey]} 
                      onChange={(e) => setZoneForm({
                        ...zoneForm,
                        coords: {
                          ...zoneForm.coords,
                          [coordKey]: parseFloat(e.target.value) || 0.0
                        }
                      })} 
                      className="input-field" 
                    />
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button onClick={handleSaveZone} className="btn btn-primary" style={{ minHeight: '36px', fontSize: '0.85rem' }}>
                <Save size={14} /> Save Zone
              </button>
              <button onClick={() => setEditingZoneId(null)} className="btn btn-secondary" style={{ minHeight: '36px', fontSize: '0.85rem' }}>
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Existing Zones Table/Cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
          {zones.map((zone) => {
            const zid = zone.id || zone._id;
            return (
              <div 
                key={zid}
                style={{
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  padding: '0.75rem 1rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '0.75rem'
                }}
              >
                <div>
                  <strong style={{ fontSize: '0.95rem' }}>{zone.name}</strong>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'flex', gap: '0.75rem', marginTop: '0.2rem' }}>
                    <span>Product: <strong>{zone.expected_class}</strong></span>
                    <span>Full Capacity: <strong>{zone.full_count}</strong></span>
                    <span>Threshold: <strong>{Math.round(zone.low_threshold * 100)}%</strong></span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.4rem' }}>
                  <button 
                    onClick={() => handleEditZone(zone)}
                    className="btn btn-secondary"
                    style={{ minHeight: '30px', padding: '0.25rem 0.65rem', fontSize: '0.75rem' }}
                  >
                    Edit
                  </button>
                  <button 
                    onClick={() => handleDeleteZone(zid)}
                    className="btn btn-secondary"
                    style={{ minHeight: '30px', padding: '0.25rem 0.65rem', fontSize: '0.75rem', color: 'var(--status-empty)' }}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
