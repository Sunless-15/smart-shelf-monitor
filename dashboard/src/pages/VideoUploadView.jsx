import React, { useState, useRef } from 'react';
import { uploadVideo, getJobStatus, getJobResult, API_BASE } from '../services/api';
import { 
  UploadCloud, 
  FileVideo, 
  CheckCircle2, 
  AlertCircle, 
  Play, 
  RefreshCw,
  ArrowUpRight,
  Download
} from 'lucide-react';

export default function VideoUploadView() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
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
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Upload Header Bento Card */}
      <div className="bento-card bento-card-dark" style={{ padding: '24px 28px' }}>
        <h2 style={{ fontSize: '1.35rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#FFFFFF', marginBottom: '6px' }}>
          Asynchronous Video Analysis & Annotation Studio
        </h2>
        <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
          Upload recorded retail shelf footage (.mp4, .avi, .mov). The background worker runs YOLO object detection, evaluates shelf occupancy, and outputs an annotated video with an interactive anomaly timeline.
        </p>
      </div>

      {/* File Dropzone Bento Card */}
      <div 
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleFileDrop}
        onClick={() => fileInputRef.current?.click()}
        className="bento-card bento-card-dark"
        style={{
          border: '2px dashed var(--border-subtle)',
          padding: '48px 24px',
          textAlign: 'center',
          cursor: 'pointer',
          background: file ? 'rgba(228, 255, 26, 0.04)' : 'var(--card-dark-bg)',
          transition: 'all 0.2s ease'
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
          width: '60px',
          height: '60px',
          borderRadius: '50%',
          background: 'var(--accent-lime-muted)',
          color: 'var(--accent-lime)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 16px'
        }}>
          {file ? <FileVideo size={28} /> : <UploadCloud size={28} />}
        </div>

        {file ? (
          <div>
            <h4 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#FFFFFF' }}>{file.name}</h4>
            <span style={{ fontSize: '0.84rem', color: 'var(--accent-lime)' }}>
              {(file.size / (1024 * 1024)).toFixed(2)} MB — Ready to analyze
            </span>
          </div>
        ) : (
          <div>
            <h4 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#FFFFFF' }}>Drag & drop shelf video here</h4>
            <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Supported: MP4, AVI, MOV up to 500MB
            </span>
          </div>
        )}
      </div>

      {/* Action Button & Error */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <button
          onClick={startUpload}
          disabled={!file || uploading || jobStatus === 'processing'}
          className="btn-pill btn-pill-lime"
          style={{ padding: '12px 28px', fontSize: '0.92rem' }}
        >
          <UploadCloud size={18} />
          <span>{uploading ? 'Uploading...' : (jobStatus === 'processing' ? 'Processing Inference...' : 'Start Video Analysis')}</span>
        </button>

        {error && (
          <div style={{ color: 'var(--status-empty)', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.88rem' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Progress Card */}
      {(uploading || (jobStatus && jobStatus !== 'done')) && (
        <div className="bento-card bento-card-dark" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <RefreshCw size={18} color="var(--accent-lime)" className="animate-spin" />
              <strong style={{ fontSize: '0.94rem', color: '#FFFFFF' }}>
                {uploading 
                  ? `Uploading Video: ${uploadProgress}%` 
                  : `Running YOLO Detection & Encoding: ${jobProgress}%`}
              </strong>
            </div>
            <span style={{
              background: 'var(--accent-lime)',
              color: '#000000',
              padding: '4px 12px',
              borderRadius: 'var(--radius-pill)',
              fontWeight: 800,
              fontSize: '0.72rem'
            }}>
              {jobStatus?.toUpperCase()}
            </span>
          </div>

          <div style={{ width: '100%', height: '8px', background: '#222', borderRadius: 'var(--radius-pill)', overflow: 'hidden' }}>
            <div 
              style={{ 
                width: `${uploading ? uploadProgress : jobProgress}%`, 
                height: '100%', 
                background: 'var(--accent-lime)',
                transition: 'width 0.3s ease'
              }} 
            />
          </div>
        </div>
      )}

      {/* Results View */}
      {jobResult && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Annotated Video Player */}
          <div className="bento-card bento-card-dark" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckCircle2 size={20} color="var(--accent-lime)" />
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#FFFFFF' }}>
                  Annotated Detection Playback
                </h3>
              </div>
              <a 
                href={`${API_BASE}${jobResult.output_video_url}`} 
                download
                className="btn-pill btn-pill-dark"
                style={{ padding: '8px 16px', fontSize: '0.8rem' }}
              >
                <Download size={14} /> Download MP4
              </a>
            </div>

            <div style={{ borderRadius: '18px', overflow: 'hidden', background: '#000' }}>
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

          {/* Timeline Events List */}
          <div className="bento-card bento-card-dark" style={{ padding: '24px' }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: '#FFFFFF', marginBottom: '4px' }}>
              Anomaly Event Timeline
            </h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Click any timestamp to seek video directly to the detected event
            </p>

            {jobResult.timeline?.length === 0 ? (
              <p style={{ color: 'var(--accent-lime)', fontSize: '0.88rem' }}>No empty shelf or low stock events detected throughout the video.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {jobResult.timeline?.map((ev, i) => (
                  <div 
                    key={i}
                    onClick={() => seekVideo(ev.time_sec)}
                    style={{
                      background: '#1A1A1A',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: '14px',
                      padding: '12px 18px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span style={{
                        background: ev.type === 'empty_shelf' ? 'var(--status-empty-bg)' : 'var(--status-low-bg)',
                        color: ev.type === 'empty_shelf' ? 'var(--status-empty)' : 'var(--status-low)',
                        padding: '3px 10px',
                        borderRadius: 'var(--radius-pill)',
                        fontSize: '0.72rem',
                        fontWeight: 800,
                        textTransform: 'uppercase'
                      }}>
                        {ev.type.replace('_', ' ')}
                      </span>
                      <span style={{ fontSize: '0.88rem', color: '#FFFFFF' }}>
                        {ev.message}
                      </span>
                    </div>

                    <button 
                      className="btn-pill btn-pill-lime" 
                      style={{ padding: '4px 12px', fontSize: '0.74rem' }}
                    >
                      <Play size={11} fill="#000" /> {ev.time_sec}s
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
