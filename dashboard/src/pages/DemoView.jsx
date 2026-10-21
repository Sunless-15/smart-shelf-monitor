import React, { useState, useEffect, useRef } from 'react';
import {
  Upload,
  Image as ImageIcon,
  Sliders,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Layers,
  Clock,
  Sparkles,
  Info,
  RefreshCw,
  PlusCircle,
  Eye
} from 'lucide-react';
import {
  getDemoSamples,
  analyzeDemoSample,
  analyzeUploadedImage,
  importDemoSample,
  getModelInfo,
  API_BASE
} from '../services/api';

export default function DemoView() {
  const [samples, setSamples] = useState([]);
  const [selectedSample, setSelectedSample] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploadedPreview, setUploadedPreview] = useState(null);
  
  const [confidence, setConfidence] = useState(0.35);
  const [iou, setIou] = useState(0.45);
  const [modelInfo, setModelInfo] = useState(null);

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Import modal state
  const [showImportModal, setShowImportModal] = useState(false);
  const [importTitle, setImportTitle] = useState('');
  const [importCategory, setImportCategory] = useState('custom_test');
  const [importFile, setImportFile] = useState(null);
  const [importLoading, setImportLoading] = useState(false);

  const fileInputRef = useRef(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [samplesData, mInfo] = await Promise.all([
        getDemoSamples(),
        getModelInfo()
      ]);
      setSamples(samplesData || []);
      setModelInfo(mInfo || null);
      if (mInfo && mInfo.confidence_threshold) {
        setConfidence(mInfo.confidence_threshold);
      }
      if (samplesData && samplesData.length > 0) {
        handleSelectSample(samplesData[0], mInfo?.confidence_threshold || 0.35);
      }
    } catch (err) {
      console.error('Failed to load demo data:', err);
      setError('Could not connect to backend demo services.');
    }
  };

  const handleSelectSample = async (sample, confVal = confidence) => {
    setSelectedSample(sample);
    setUploadedFile(null);
    setUploadedPreview(null);
    setLoading(true);
    setError(null);

    try {
      const res = await analyzeDemoSample(sample.id, { confidence: confVal, iou });
      setResult(res);
    } catch (err) {
      console.error('Error analyzing sample:', err);
      setError('Failed to analyze selected sample image.');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file, confVal = confidence) => {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      setError('File exceeds maximum upload size of 10 MB.');
      return;
    }

    setUploadedFile(file);
    setSelectedSample(null);
    setError(null);

    const reader = new FileReader();
    reader.onload = (e) => setUploadedPreview(e.target.result);
    reader.readAsDataURL(file);

    setLoading(true);
    try {
      const res = await analyzeUploadedImage(file, { confidence: confVal, iou });
      setResult(res);
    } catch (err) {
      console.error('Error analyzing uploaded file:', err);
      setError('Failed to analyze uploaded image. Please ensure it is a valid JPG/PNG.');
    } finally {
      setLoading(false);
    }
  };

  const handleRerunDetection = () => {
    if (selectedSample) {
      handleSelectSample(selectedSample, confidence);
    } else if (uploadedFile) {
      handleFileUpload(uploadedFile, confidence);
    }
  };

  const handleImportSubmit = async (e) => {
    e.preventDefault();
    if (!importFile) return;

    setImportLoading(true);
    try {
      const fd = new FormData();
      fd.append('image', importFile);
      fd.append('title', importTitle || 'Custom Imported Test');
      fd.append('category', importCategory);

      await importDemoSample(fd);
      setShowImportModal(false);
      setImportFile(null);
      setImportTitle('');
      const updatedSamples = await getDemoSamples();
      setSamples(updatedSamples);
    } catch (err) {
      console.error('Import failed:', err);
      alert('Failed to import sample image.');
    } finally {
      setImportLoading(false);
    }
  };
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', paddingBottom: '3rem' }}>
      
      {/* Top Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(228, 255, 26, 0.08), rgba(22, 22, 22, 0.95))',
        border: '1px solid rgba(228, 255, 26, 0.3)',
        borderRadius: '24px',
        padding: '1.25rem 1.75rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{
            background: '#E4FF1A',
            color: '#000',
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 800,
            flexShrink: 0
          }}>
            <Sparkles size={20} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0, color: '#FFFFFF' }}>
                ShelfSense Vision Studio (Demo & Sandbox)
              </h2>
              <span style={{
                background: 'rgba(228, 255, 26, 0.15)',
                color: '#E4FF1A',
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '12px',
                textTransform: 'uppercase'
              }}>
                Isolated Sandbox
              </span>
            </div>
            <p style={{ fontSize: '0.82rem', color: '#8E8E93', margin: '0.2rem 0 0 0' }}>
              Test model inference and zone logic on unseen dataset test splits or your own photos.
            </p>
          </div>
        </div>

        {modelInfo && (
          <div style={{
            background: '#1C1C1E',
            border: '1px solid #2C2C2E',
            borderRadius: '16px',
            padding: '0.6rem 1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            fontSize: '0.8rem'
          }}>
            <div>
              <span style={{ color: '#8E8E93' }}>Model: </span>
              <strong style={{ color: '#E4FF1A' }}>{modelInfo.model_status}</strong>
            </div>
            <div style={{ height: '14px', width: '1px', background: '#3A3A3C' }} />
            <div>
              <span style={{ color: '#8E8E93' }}>Device: </span>
              <strong style={{ color: '#FFFFFF' }}>{modelInfo.device}</strong>
            </div>
          </div>
        )}
      </div>

      {/* Main Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(320px, 380px) 1fr',
        gap: '1.5rem',
        alignItems: 'start'
      }} className="demo-grid-layout">
        
        {/* LEFT COLUMN: Input Source Selection */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          
          {/* 1. Upload My Own Image */}
          <div style={{
            background: '#161616',
            border: '1px solid #2C2C2E',
            borderRadius: '24px',
            padding: '1.25rem'
          }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, margin: '0 0 0.85rem 0', color: '#FFFFFF', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Upload size={16} color="#E4FF1A" />
              1. Upload Your Shelf Photo
            </h3>

            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                if (e.dataTransfer.files?.[0]) {
                  handleFileUpload(e.dataTransfer.files[0]);
                }
              }}
              style={{
                border: '2px dashed #3A3A3C',
                borderRadius: '16px',
                padding: '1.5rem 1rem',
                textAlign: 'center',
                cursor: 'pointer',
                background: uploadedFile ? 'rgba(228, 255, 26, 0.04)' : '#1C1C1E',
                borderColor: uploadedFile ? '#E4FF1A' : '#3A3A3C',
                transition: 'all 0.2s ease'
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                style={{ display: 'none' }}
                onChange={(e) => {
                  if (e.target.files?.[0]) {
                    handleFileUpload(e.target.files[0]);
                  }
                }}
              />
              <Upload size={28} color={uploadedFile ? '#E4FF1A' : '#8E8E93'} style={{ margin: '0 auto 0.5rem auto' }} />
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#FFFFFF' }}>
                {uploadedFile ? uploadedFile.name : 'Tap to browse or drag & drop'}
              </div>
              <div style={{ fontSize: '0.72rem', color: '#8E8E93', marginTop: '0.25rem' }}>
                JPG, PNG, WebP up to 10 MB
              </div>
            </div>
          </div>

          {/* 2. Sliders */}
          <div style={{
            background: '#161616',
            border: '1px solid #2C2C2E',
            borderRadius: '24px',
            padding: '1.25rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0, color: '#FFFFFF', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sliders size={16} color="#E4FF1A" />
                Detection Parameters
              </h3>
              <button
                onClick={handleRerunDetection}
                disabled={loading}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#E4FF1A',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.3rem'
                }}
              >
                <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
                Re-run
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.3rem' }}>
                  <span style={{ color: '#8E8E93' }}>Confidence Threshold</span>
                  <strong style={{ color: '#E4FF1A' }}>{Math.round(confidence * 100)}%</strong>
                </div>
                <input
                  type="range"
                  min="0.10"
                  max="0.90"
                  step="0.05"
                  value={confidence}
                  onChange={(e) => setConfidence(parseFloat(e.target.value))}
                  onMouseUp={handleRerunDetection}
                  onTouchEnd={handleRerunDetection}
                  style={{ width: '100%', accentColor: '#E4FF1A', cursor: 'pointer' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.3rem' }}>
                  <span style={{ color: '#8E8E93' }}>IoU NMS Overlap Threshold</span>
                  <strong style={{ color: '#FFFFFF' }}>{iou}</strong>
                </div>
                <input
                  type="range"
                  min="0.20"
                  max="0.80"
                  step="0.05"
                  value={iou}
                  onChange={(e) => setIou(parseFloat(e.target.value))}
                  onMouseUp={handleRerunDetection}
                  onTouchEnd={handleRerunDetection}
                  style={{ width: '100%', accentColor: '#E4FF1A', cursor: 'pointer' }}
                />
              </div>
            </div>
          </div>

          {/* 3. Sample Gallery */}
          <div style={{
            background: '#161616',
            border: '1px solid #2C2C2E',
            borderRadius: '24px',
            padding: '1.25rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
              <div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0, color: '#FFFFFF', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <ImageIcon size={16} color="#E4FF1A" />
                  2. Test Split Sample Gallery
                </h3>
                <span style={{ fontSize: '0.72rem', color: '#8E8E93' }}>
                  {samples.length} images strictly from unseen test split
                </span>
              </div>
              <button
                onClick={() => setShowImportModal(true)}
                title="Import image into gallery"
                style={{
                  background: 'rgba(255,255,255,0.08)',
                  border: '1px solid #3A3A3C',
                  color: '#FFFFFF',
                  borderRadius: '12px',
                  padding: '4px 8px',
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.3rem'
                }}
              >
                <PlusCircle size={13} color="#E4FF1A" />
                Import
              </button>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: '0.65rem',
              maxHeight: '340px',
              overflowY: 'auto',
              paddingRight: '4px'
            }}>
              {samples.map((s) => {
                const isSelected = selectedSample?.id === s.id;
                return (
                  <div
                    key={s.id}
                    onClick={() => handleSelectSample(s)}
                    style={{
                      background: isSelected ? 'rgba(228, 255, 26, 0.12)' : '#1C1C1E',
                      border: isSelected ? '2px solid #E4FF1A' : '1px solid #2C2C2E',
                      borderRadius: '14px',
                      overflow: 'hidden',
                      cursor: 'pointer',
                      transition: 'transform 0.15s ease'
                    }}
                  >
                    <img
                      src={`${API_BASE}${s.image_url}`}
                      alt={s.title}
                      loading="lazy"
                      style={{
                        width: '100%',
                        height: '75px',
                        objectFit: 'cover',
                        display: 'block'
                      }}
                    />
                    <div style={{ padding: '0.4rem 0.5rem' }}>
                      <div style={{
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        color: isSelected ? '#E4FF1A' : '#FFFFFF',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis'
                      }}>
                        {s.title}
                      </div>
                      <div style={{ fontSize: '0.65rem', color: '#8E8E93', textTransform: 'capitalize' }}>
                        {s.category.replace('_', ' ')}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

        </div>
        {/* RIGHT COLUMN: Side-by-Side Visualization & Metrics */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          
          {error && (
            <div style={{
              background: 'rgba(255, 69, 58, 0.12)',
              border: '1px solid #FF453A',
              color: '#FF453A',
              borderRadius: '16px',
              padding: '0.85rem 1.2rem',
              fontSize: '0.85rem'
            }}>
              {error}
            </div>
          )}

          {/* Plain-Language Caption Card */}
          {result && (
            <div style={{
              background: '#FFFFFF',
              color: '#000000',
              borderRadius: '24px',
              padding: '1.25rem 1.5rem',
              boxShadow: '0 4px 20px rgba(0,0,0,0.2)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
                <Info size={16} color="#000" />
                <span style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  What this shows
                </span>
                <span style={{
                  marginLeft: 'auto',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  background: '#000',
                  color: '#E4FF1A',
                  padding: '2px 8px',
                  borderRadius: '12px'
                }}>
                  {result.latency_ms} ms inference
                </span>
              </div>
              <p style={{ fontSize: '0.95rem', fontWeight: 600, lineHeight: 1.4, margin: 0 }}>
                {result.caption}
              </p>
            </div>
          )}

          {/* Side-by-Side Images Card */}
          <div style={{
            background: '#161616',
            border: '1px solid #2C2C2E',
            borderRadius: '24px',
            padding: '1.25rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                <Eye size={18} color="#E4FF1A" />
                <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, color: '#FFFFFF' }}>
                  Visual Side-by-Side Comparison
                </h3>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.75rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', color: '#8E8E93' }}>
                  <span style={{ width: '10px', height: '10px', background: '#00FF66', borderRadius: '2px' }} />
                  Products
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', color: '#8E8E93' }}>
                  <span style={{ width: '10px', height: '10px', background: '#00E5FF', borderRadius: '2px' }} />
                  Empty Slots
                </span>
              </div>
            </div>

            {loading ? (
              <div style={{
                height: '320px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.75rem',
                color: '#8E8E93',
                background: '#1C1C1E',
                borderRadius: '16px'
              }}>
                <RefreshCw size={32} className="animate-spin" color="#E4FF1A" />
                <span style={{ fontSize: '0.88rem' }}>Running YOLOv8 inference & zone mapping...</span>
              </div>
            ) : result ? (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: '1rem'
              }}>
                {/* Original Frame */}
                <div>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#8E8E93', marginBottom: '0.4rem' }}>
                    Original Input
                  </div>
                  <div style={{ borderRadius: '16px', overflow: 'hidden', border: '1px solid #2C2C2E', background: '#000' }}>
                    <img
                      src={result.original_image}
                      alt="Original"
                      style={{ width: '100%', height: 'auto', display: 'block', maxHeight: '420px', objectFit: 'contain' }}
                    />
                  </div>
                </div>

                {/* Annotated Output */}
                <div>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#E4FF1A', marginBottom: '0.4rem', display: 'flex', justifyContent: 'space-between' }}>
                    <span>YOLO Detections & Zone Overlay</span>
                    <span>{result.products_count} items detected</span>
                  </div>
                  <div style={{ borderRadius: '16px', overflow: 'hidden', border: '1px solid rgba(228, 255, 26, 0.4)', background: '#000' }}>
                    <img
                      src={result.annotated_image}
                      alt="Annotated"
                      style={{ width: '100%', height: 'auto', display: 'block', maxHeight: '420px', objectFit: 'contain' }}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div style={{
                height: '240px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#8E8E93',
                background: '#1C1C1E',
                borderRadius: '16px'
              }}>
                Select an image from the gallery or upload your own to begin analysis.
              </div>
            )}
          </div>

          {/* Per-Zone Result Cards */}
          {result && result.zones && result.zones.length > 0 && (
            <div style={{
              background: '#161616',
              border: '1px solid #2C2C2E',
              borderRadius: '24px',
              padding: '1.25rem'
            }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, margin: '0 0 1rem 0', color: '#FFFFFF', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Layers size={16} color="#E4FF1A" />
                Shelf Zone Evaluation
              </h3>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: '0.85rem'
              }}>
                {result.zones.map((z) => {
                  const statusColors = {
                    ok: { bg: 'rgba(52, 199, 89, 0.12)', text: '#34C759', label: 'Healthy', icon: CheckCircle },
                    low: { bg: 'rgba(255, 149, 0, 0.15)', text: '#FF9500', label: 'Low Stock', icon: AlertTriangle },
                    empty: { bg: 'rgba(255, 69, 58, 0.15)', text: '#FF453A', label: 'Empty Shelf', icon: XCircle }
                  };
                  const st = statusColors[z.state] || statusColors.ok;
                  const Icon = st.icon;

                  return (
                    <div
                      key={z.zone_id}
                      style={{
                        background: '#1C1C1E',
                        border: `1px solid ${st.text}40`,
                        borderRadius: '16px',
                        padding: '1rem'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                        <span style={{ fontSize: '0.88rem', fontWeight: 700, color: '#FFFFFF' }}>{z.name}</span>
                        <span style={{
                          background: st.bg,
                          color: st.text,
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '12px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.3rem'
                        }}>
                          <Icon size={12} />
                          {st.label}
                        </span>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginTop: '0.5rem' }}>
                        <div>
                          <span style={{ fontSize: '1.4rem', fontWeight: 800, color: '#FFFFFF' }}>{z.current_count}</span>
                          <span style={{ fontSize: '0.8rem', color: '#8E8E93' }}> / {z.full_count} items</span>
                        </div>
                        <span style={{ fontSize: '1.1rem', fontWeight: 700, color: st.text }}>
                          {Math.round(z.stock_percent * 100)}%
                        </span>
                      </div>

                      {z.empty_slot_count > 0 && (
                        <div style={{ fontSize: '0.72rem', color: '#00E5FF', marginTop: '0.4rem' }}>
                          Evidence: {z.empty_slot_count} empty slot boxes mapped
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Raw Detections Table Card */}
          {result && result.detections && result.detections.length > 0 && (
            <div style={{
              background: '#161616',
              border: '1px solid #2C2C2E',
              borderRadius: '24px',
              padding: '1.25rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0, color: '#FFFFFF' }}>
                  Raw Detection Records ({result.detections.length} objects)
                </h3>
              </div>

              <div style={{ maxHeight: '220px', overflowY: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #2C2C2E', color: '#8E8E93', textAlign: 'left' }}>
                      <th style={{ padding: '6px' }}>#</th>
                      <th style={{ padding: '6px' }}>Class</th>
                      <th style={{ padding: '6px' }}>Confidence</th>
                      <th style={{ padding: '6px' }}>Pixel Coordinates</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.detections.map((d, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #1C1C1E', color: '#FFFFFF' }}>
                        <td style={{ padding: '6px', color: '#8E8E93' }}>{idx + 1}</td>
                        <td style={{ padding: '6px' }}>
                          <span style={{
                            background: d.class_name === 'product' ? 'rgba(0, 255, 102, 0.15)' : 'rgba(0, 229, 255, 0.15)',
                            color: d.class_name === 'product' ? '#00FF66' : '#00E5FF',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontWeight: 600
                          }}>
                            {d.class_name}
                          </span>
                        </td>
                        <td style={{ padding: '6px', fontWeight: 600 }}>{Math.round(d.confidence * 100)}%</td>
                        <td style={{ padding: '6px', fontFamily: 'monospace', color: '#8E8E93' }}>
                          [{d.pixel_box.join(', ')}]
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>

      </div>

      {/* Import Modal */}
      {showImportModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100000,
          padding: '1rem'
        }}>
          <div style={{
            background: '#1C1C1E',
            border: '1px solid #2C2C2E',
            borderRadius: '24px',
            padding: '1.75rem',
            maxWidth: '440px',
            width: '100%'
          }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: '0 0 1rem 0', color: '#FFFFFF' }}>
              Import Image to Demo Gallery
            </h3>
            <form onSubmit={handleImportSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ fontSize: '0.8rem', color: '#8E8E93', display: 'block', marginBottom: '0.3rem' }}>
                  Image Title
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Full Shelf Test 25"
                  value={importTitle}
                  onChange={(e) => setImportTitle(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.6rem 0.8rem',
                    background: '#2C2C2E',
                    border: '1px solid #3A3A3C',
                    borderRadius: '12px',
                    color: '#fff',
                    fontSize: '0.85rem'
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', color: '#8E8E93', display: 'block', marginBottom: '0.3rem' }}>
                  Category
                </label>
                <select
                  value={importCategory}
                  onChange={(e) => setImportCategory(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.6rem 0.8rem',
                    background: '#2C2C2E',
                    border: '1px solid #3A3A3C',
                    borderRadius: '12px',
                    color: '#fff',
                    fontSize: '0.85rem'
                  }}
                >
                  <option value="full_shelf">Full Shelf</option>
                  <option value="half_empty">Half Empty</option>
                  <option value="nearly_empty">Nearly Empty</option>
                  <option value="completely_empty">Completely Empty</option>
                  <option value="misplaced">Misplaced Item</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', color: '#8E8E93', display: 'block', marginBottom: '0.3rem' }}>
                  Select Image File (Test Split Only)
                </label>
                <input
                  type="file"
                  required
                  accept="image/jpeg,image/png"
                  onChange={(e) => setImportFile(e.target.files?.[0] || null)}
                  style={{ color: '#fff', fontSize: '0.8rem' }}
                />
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => setShowImportModal(false)}
                  style={{
                    flex: 1,
                    padding: '0.65rem',
                    borderRadius: '12px',
                    border: '1px solid #3A3A3C',
                    background: 'none',
                    color: '#fff',
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={importLoading}
                  style={{
                    flex: 1,
                    padding: '0.65rem',
                    borderRadius: '12px',
                    border: 'none',
                    background: '#E4FF1A',
                    color: '#000',
                    fontWeight: 700,
                    cursor: 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  {importLoading ? 'Importing...' : 'Add to Gallery'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
