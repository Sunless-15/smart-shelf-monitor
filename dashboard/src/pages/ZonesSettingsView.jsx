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
  AlertCircle
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Toast Alert */}
      {message && (
        <div style={{
          background: message.type === 'success' ? 'var(--accent-lime-muted)' : 'rgba(255, 77, 79, 0.15)',
          color: message.type === 'success' ? 'var(--accent-lime)' : '#FF4D4F',
          border: `1px solid ${message.type === 'success' ? 'rgba(228, 255, 26, 0.4)' : 'rgba(255, 77, 79, 0.4)'}`,
          padding: '12px 18px',
          borderRadius: 'var(--radius-card-sm)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '0.88rem',
          fontWeight: 600
        }}>
          {message.type === 'success' ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Section 1: Video Source Layer Config */}
      <div className="bento-card bento-card-dark" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
          <Video size={22} color="var(--accent-lime)" />
          <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#FFFFFF' }}>
            Pluggable Video & Camera Source
          </h2>
        </div>
        <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginBottom: '18px' }}>
          Switch camera feeds seamlessly at runtime. Select local webcam, looped demo video, or paste the ESP32-CAM MJPEG stream URL (e.g. <code>http://&lt;esp32-ip&gt;:81/stream</code>).
        </p>

        {/* Source Radio Selector */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '18px' }}>
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
                  background: isSelected ? 'var(--accent-lime-muted)' : '#101010',
                  border: isSelected ? '1.5px solid var(--accent-lime)' : '1px solid var(--border-subtle)',
                  borderRadius: '16px',
                  padding: '14px 18px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  transition: 'all 0.15s ease'
                }}
              >
                <Icon size={18} color={isSelected ? 'var(--accent-lime)' : 'var(--text-muted)'} />
                <span style={{ fontSize: '0.88rem', fontWeight: isSelected ? 700 : 500, color: isSelected ? '#FFFFFF' : 'var(--text-secondary)' }}>
                  {src.label}
                </span>
              </div>
            );
          })}
        </div>

        {/* Source Value Input */}
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '240px' }}>
            <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
              {selectedSourceType === 'webcam' && 'Webcam Device Index (0 = built-in camera, 1 = external USB)'}
              {selectedSourceType === 'video' && 'Path to Video File on Disk (looped playback)'}
              {selectedSourceType === 'stream' && 'ESP32-CAM / MJPEG HTTP Stream URL'}
            </label>
            <input 
              type="text" 
              value={sourceValueInput} 
              onChange={(e) => setSourceValueInput(e.target.value)} 
              placeholder={selectedSourceType === 'stream' ? 'http://192.168.1.100:81/stream' : 'Source value'} 
              style={{
                width: '100%',
                background: '#101010',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-pill)',
                padding: '10px 18px',
                color: '#FFFFFF',
                fontSize: '0.88rem',
                outline: 'none'
              }}
            />
          </div>

          <button 
            onClick={handleSourceSwitch} 
            disabled={sourceLoading}
            className="btn-pill btn-pill-lime"
            style={{ padding: '10px 22px' }}
          >
            <Save size={16} />
            <span>{sourceLoading ? 'Switching...' : 'Apply Video Source'}</span>
          </button>
        </div>

        {/* Active Source Health Badge */}
        {sourceStatus && (
          <div style={{ marginTop: '16px', fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span>Active Source: <strong style={{ color: '#FFFFFF' }}>{sourceStatus.type}</strong> ({sourceStatus.value})</span>
            <span style={{
              background: sourceStatus.is_active ? 'var(--accent-lime)' : 'var(--status-empty-bg)',
              color: sourceStatus.is_active ? '#000000' : 'var(--status-empty)',
              padding: '2px 10px',
              borderRadius: 'var(--radius-pill)',
              fontWeight: 800,
              fontSize: '0.7rem'
            }}>
              {sourceStatus.is_active ? 'ACTIVE' : 'OFFLINE'}
            </span>
          </div>
        )}
      </div>

      {/* Section 2: Shelf Zones Configuration */}
      <div className="bento-card bento-card-dark" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Sliders size={20} color="var(--accent-lime)" />
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#FFFFFF' }}>Shelf Zone Definitions</h2>
            </div>
            <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
              Configure named normalized detection rectangles (0.0 to 1.0 coordinates)
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button 
              onClick={() => setSnapshotKey(Date.now())} 
              className="btn-pill btn-pill-dark" 
              style={{ padding: '8px 16px', fontSize: '0.8rem' }}
            >
              <RefreshCw size={14} /> Refresh Frame
            </button>
            <button 
              onClick={startNewZone} 
              className="btn-pill btn-pill-lime" 
              style={{ padding: '8px 18px', fontSize: '0.8rem' }}
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
          borderRadius: '18px', 
          overflow: 'hidden', 
          marginBottom: '20px',
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
                  border: isEditing ? '2.5px solid var(--accent-lime)' : '2px dashed #FFFFFF',
                  background: isEditing ? 'rgba(228, 255, 26, 0.25)' : 'rgba(255, 255, 255, 0.08)',
                  pointerEvents: 'none',
                  display: 'flex',
                  alignItems: 'flex-start',
                  padding: '4px'
                }}
              >
                <span style={{ 
                  background: isEditing ? 'var(--accent-lime)' : '#FFFFFF', 
                  color: '#000000', 
                  fontSize: '11px', 
                  fontWeight: 800, 
                  padding: '2px 6px', 
                  borderRadius: '4px' 
                }}>
                  {z.name}
                </span>
              </div>
            );
          })}
        </div>

        {/* Zone Editor Form */}
        {editingZoneId && (
          <div style={{
            background: '#101010',
            border: '1.5px solid var(--accent-lime)',
            borderRadius: '18px',
            padding: '20px',
            marginBottom: '20px'
          }}>
            <h4 style={{ fontSize: '1.05rem', fontWeight: 800, color: '#FFFFFF', marginBottom: '14px' }}>
              {editingZoneId === 'new' ? 'New Shelf Zone' : `Editing: ${zoneForm.name}`}
            </h4>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginBottom: '14px' }}>
              <div>
                <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Zone Name</label>
                <input 
                  type="text" 
                  value={zoneForm.name} 
                  onChange={(e) => setZoneForm({ ...zoneForm, name: e.target.value })} 
                  style={{
                    width: '100%',
                    background: '#1A1A1A',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-pill)',
                    padding: '8px 16px',
                    color: '#FFFFFF',
                    fontSize: '0.86rem',
                    outline: 'none'
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Expected Product Class</label>
                <input 
                  type="text" 
                  value={zoneForm.expected_class} 
                  onChange={(e) => setZoneForm({ ...zoneForm, expected_class: e.target.value.toLowerCase() })} 
                  style={{
                    width: '100%',
                    background: '#1A1A1A',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-pill)',
                    padding: '8px 16px',
                    color: '#FFFFFF',
                    fontSize: '0.86rem',
                    outline: 'none'
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Full Capacity Count</label>
                <input 
                  type="number" 
                  min="1" 
                  value={zoneForm.full_count} 
                  onChange={(e) => setZoneForm({ ...zoneForm, full_count: parseInt(e.target.value) || 1 })} 
                  style={{
                    width: '100%',
                    background: '#1A1A1A',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-pill)',
                    padding: '8px 16px',
                    color: '#FFFFFF',
                    fontSize: '0.86rem',
                    outline: 'none'
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>Low Stock Threshold (0.0 - 1.0)</label>
                <input 
                  type="number" 
                  step="0.05" 
                  min="0.05" 
                  max="0.9" 
                  value={zoneForm.low_threshold} 
                  onChange={(e) => setZoneForm({ ...zoneForm, low_threshold: parseFloat(e.target.value) || 0.35 })} 
                  style={{
                    width: '100%',
                    background: '#1A1A1A',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-pill)',
                    padding: '8px 16px',
                    color: '#FFFFFF',
                    fontSize: '0.86rem',
                    outline: 'none'
                  }}
                />
              </div>
            </div>

            {/* Coordinates */}
            <div style={{ marginBottom: '14px' }}>
              <label style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                Normalized Coordinates (X1: {zoneForm.coords.x1}, Y1: {zoneForm.coords.y1}, X2: {zoneForm.coords.x2}, Y2: {zoneForm.coords.y2})
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
                {['x1', 'y1', 'x2', 'y2'].map((coordKey) => (
                  <div key={coordKey}>
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
                      style={{
                        width: '100%',
                        background: '#1A1A1A',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-pill)',
                        padding: '8px 12px',
                        color: '#FFFFFF',
                        fontSize: '0.84rem',
                        outline: 'none'
                      }}
                    />
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button onClick={handleSaveZone} className="btn-pill btn-pill-lime" style={{ padding: '8px 18px', fontSize: '0.84rem' }}>
                <Save size={14} /> Save Zone
              </button>
              <button onClick={() => setEditingZoneId(null)} className="btn-pill btn-pill-dark" style={{ padding: '8px 18px', fontSize: '0.84rem' }}>
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Existing Zones List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {zones.map((zone) => {
            const zid = zone.id || zone._id;
            return (
              <div 
                key={zid}
                style={{
                  background: '#121212',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '16px',
                  padding: '14px 20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '12px'
                }}
              >
                <div>
                  <strong style={{ fontSize: '0.98rem', color: '#FFFFFF' }}>{zone.name}</strong>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'flex', gap: '12px', marginTop: '3px' }}>
                    <span>Product: <strong style={{ color: 'var(--accent-lime)' }}>{zone.expected_class}</strong></span>
                    <span>Full: <strong>{zone.full_count} items</strong></span>
                    <span>Threshold: <strong>{Math.round(zone.low_threshold * 100)}%</strong></span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button 
                    onClick={() => handleEditZone(zone)}
                    className="btn-pill btn-pill-dark"
                    style={{ padding: '6px 14px', fontSize: '0.78rem' }}
                  >
                    Edit
                  </button>
                  <button 
                    onClick={() => handleDeleteZone(zid)}
                    className="btn-round-action btn-round-dark"
                    style={{ width: '34px', height: '34px', color: 'var(--status-empty)' }}
                    title="Delete Zone"
                  >
                    <Trash2 size={14} />
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
