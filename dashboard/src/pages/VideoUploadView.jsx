import React, { useState, useRef } from 'react';
import { uploadVideo, getJobStatus, getJobResult, API_BASE } from '../services/api';
import { 
  UploadCloud, 
  FileVideo, 
  CheckCircle2, 
  AlertCircle, 
  Play, 
  Clock, 
  Layers, 
  Activity, 
  RefreshCw 
} from 'lucide-react';

export default function VideoUploadView() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null); // queued | processing | done | failed
  const [jobProgress, setJobProgress] = useState(0);
  const [jobResult, setJobResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);
  const videoPlayerRef = useRef(null);

  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setError(null);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const startUpload = async () => {
    if (!file) return;

    setUploading(true);
    setUploadProgress(0);
    setError(null);
    setJobResult(null);
    setJobStatus('uploading');

    try {
      const res = await uploadVideo(file, (progressEvent) => {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        setUploadProgress(percent);
      });

      setUploading(false);
      setJobId(res.job_id);
      setJobStatus(res.status);
      pollJobProgress(res.job_id);
    } catch (err) {
      setUploading(false);
      setError(err.response?.data?.error || 'Failed to upload video.');
      setJobStatus(null);
    }
  };

  const pollJobProgress = (id) => {
    const pollInterval = setInterval(async () => {
      try {
        const statusRes = await getJobStatus(id);
        setJobStatus(statusRes.status);
        setJobProgress(statusRes.progress || 0);

        if (statusRes.status === 'done') {
          clearInterval(pollInterval);
          // Fetch final result
          const resultRes = await getJobResult(id);
          setJobResult(resultRes.result);
        } else if (statusRes.status === 'failed') {
          clearInterval(pollInterval);
          setError(statusRes.error || 'Video processing failed.');
        }
      } catch (err) {
        console.error('Error polling job status:', err);
      }
    }, 1500);
  };

  const seekVideo = (timeSec) => {
    if (videoPlayerRef.current) {
      videoPlayerRef.current.currentTime = timeSec;
      videoPlayerRef.current.play();
    }
  };

  return (
    <div>
      {/* Upload Header */}
      <div className="glass-card" style={{ marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.35rem', fontWeight: 700, marginBottom: '0.35rem' }}>
          Asynchronous Video Analysis & Annotation
        </h2>
        <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
          Upload recorded retail shelf footage (.mp4, .avi, .mov). The background worker samples frames, runs YOLO detection, evaluates shelf occupancy, and outputs an annotated video with an anomaly timeline.
        </p>
      </div>

      {/* File Dropzone */}
      <div 
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleFileDrop}
        onClick={() => fileInputRef.current?.click()}
        className="glass-card"
        style={{
          border: '2px dashed var(--border-subtle)',
          borderRadius: 'var(--radius-lg)',
          padding: '3rem 1.5rem',
          textAlign: 'center',
          cursor: 'pointer',
          marginBottom: '1.5rem',
          background: file ? 'rgba(59, 130, 246, 0.05)' : 'var(--bg-card)'
        }}
      >
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleFileSelect} 
          accept="video/mp4,video/avi,video/quicktime,video/x-matroska" 
          style={{ display: 'none' }} 
        />

        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          background: 'rgba(59, 130, 246, 0.15)',
          color: 'var(--accent-blue)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 1rem'
        }}>
          {file ? <FileVideo size={28} /> : <UploadCloud size={28} />}
        </div>

        {file ? (
          <div>
            <h4 style={{ fontSize: '1.1rem', fontWeight: 700 }}>{file.name}</h4>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              {(file.size / (1024 * 1024)).toFixed(2)} MB — Click to choose a different file
            </span>
          </div>
        ) : (
          <div>
            <h4 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Tap or Drop video here to upload</h4>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              Supported formats: MP4, AVI, MOV (up to 500MB)
            </span>
          </div>
        )}
      </div>

      {/* Action Button & Error */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
        <button
          onClick={startUpload}
          disabled={!file || uploading || jobStatus === 'processing'}
          className="btn btn-primary"
          style={{ minHeight: '44px', padding: '0.6rem 1.5rem', fontSize: '0.95rem' }}
        >
          <UploadCloud size={18} />
          <span>{uploading ? 'Uploading...' : (jobStatus === 'processing' ? 'Processing...' : 'Start Video Analysis')}</span>
        </button>

        {error && (
          <div style={{ color: 'var(--status-empty)', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.88rem' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Progress Card (during upload or processing) */}
      {(uploading || (jobStatus && jobStatus !== 'done')) && (
        <div className="glass-card" style={{ marginBottom: '1.5rem', padding: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.65rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <RefreshCw size={18} color="var(--accent-cyan)" className="animate-spin" />
              <strong style={{ fontSize: '0.95rem' }}>
                {uploading 
                  ? `Uploading Video: ${uploadProgress}%` 
                  : `Analyzing Frames & Transcoding: ${jobProgress}%`}
              </strong>
            </div>
            <span className="badge badge-low">{jobStatus?.toUpperCase()}</span>
          </div>

          <div className="progress-container" style={{ height: '12px' }}>
            <div 
              className="progress-fill fill-low" 
              style={{ width: `${uploading ? uploadProgress : jobProgress}%` }} 
            />
          </div>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.5rem', display: 'block' }}>
            {uploading ? 'Transferring file to backend...' : 'Running YOLO inference on ~0.5s sampled frames and generating H.264 video...'}
          </span>
        </div>
      )}

      {/* Job Results: Video Player & Timeline */}
      {jobResult && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Annotated Video Player */}
          <div className="glass-card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle2 size={20} color="var(--status-ok)" />
                <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Annotated Video Playback</h3>
              </div>
              <a 
                href={`${API_BASE}${jobResult.output_video_url}`} 
                download
                className="btn btn-secondary"
                style={{ minHeight: '32px', fontSize: '0.78rem' }}
              >
                Download MP4
              </a>
            </div>

            <div style={{ borderRadius: 'var(--radius-md)', overflow: 'hidden', background: '#000' }}>
              <video 
                ref={videoPlayerRef}
                controls 
                style={{ width: '100%', maxHeight: '480px', display: 'block' }}
                src={`${API_BASE}${jobResult.output_video_url}`}
              >
                Your browser does not support HTML5 video.
              </video>
            </div>
          </div>

          {/* Analysis Summary Statistics */}
          <div className="metrics-grid">
            <div className="metric-tile glass-card">
              <span className="label">Analyzed Samples</span>
              <span className="value" style={{ color: 'var(--accent-blue)' }}>
                {jobResult.analyzed_samples}
              </span>
            </div>

            <div className="metric-tile glass-card">
              <span className="label">Duration</span>
              <span className="value">
                {jobResult.duration_seconds}s
              </span>
            </div>

            <div className="metric-tile glass-card">
              <span className="label">Timeline Events</span>
              <span className="value" style={{ color: 'var(--status-low)' }}>
                {jobResult.total_events}
              </span>
            </div>

            <div className="metric-tile glass-card">
              <span className="label">Detected Classes</span>
              <span className="value" style={{ fontSize: '1.2rem', color: 'var(--text-secondary)' }}>
                {Object.keys(jobResult.class_counts || {}).join(', ') || 'None'}
              </span>
            </div>
          </div>

          {/* Timeline Events List */}
          <div className="glass-card" style={{ padding: '1.5rem' }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '0.25rem' }}>Anomaly Event Timeline</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
              Click any timestamp to seek video directly to the detected event
            </p>

            {jobResult.timeline?.length === 0 ? (
              <p style={{ color: 'var(--status-ok)', fontSize: '0.9rem' }}>No empty shelf or low stock events detected throughout the video.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', maxHeight: '350px', overflowY: 'auto' }}>
                {jobResult.timeline?.map((ev, i) => (
                  <div 
                    key={i}
                    onClick={() => seekVideo(ev.time_sec)}
                    style={{
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '0.65rem 0.9rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      transition: 'var(--transition)'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--accent-blue)'}
                    onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border-subtle)'}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span className={`badge badge-${ev.type === 'empty_shelf' ? 'empty' : (ev.type === 'low_stock' ? 'low' : 'misplaced')}`}>
                        {ev.type.replace('_', ' ')}
                      </span>
                      <span style={{ fontSize: '0.88rem', color: 'var(--text-primary)' }}>
                        {ev.message}
                      </span>
                    </div>

                    <button 
                      className="btn btn-secondary" 
                      style={{ minHeight: '28px', padding: '0.15rem 0.5rem', fontSize: '0.75rem', gap: '0.3rem' }}
                    >
                      <Play size={12} /> {ev.time_sec}s
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
