import axios from 'axios';

// Resolve API base URL:
// 1. Build-time environment variable VITE_API_URL (e.g. from Vercel)
// 2. Or current browser hostname on port 5000 (for local dev / mobile WiFi)
// 3. Fallback to localhost:5000
const envUrl = (import.meta.env.VITE_API_URL || '').trim().replace(/\/$/, '');
const isBrowser = typeof window !== 'undefined';
const hostName = isBrowser ? window.location.hostname : '';
const isVercel = isBrowser && hostName.includes('vercel.app');

export const API_BASE = 
  envUrl || 
  (isVercel ? '' : `${isBrowser ? window.location.protocol : 'http:'}//${hostName || 'localhost'}:5000`);

// Token Management
export const getAuthToken = () => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('smart_shelf_token') || '';
  }
  return '';
};

export const setAuthToken = (token) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem('smart_shelf_token', token);
  }
};

export const clearAuthToken = () => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('smart_shelf_token');
  }
};

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// Attach JWT Bearer token to all requests if present
apiClient.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor to detect 401s
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('auth_required'));
      }
    }
    return Promise.reject(error);
  }
);

// Stream & Media URLs with token parameter
export const getLiveStreamUrl = () => {
  const token = getAuthToken();
  const sep = token ? `?token=${encodeURIComponent(token)}` : '';
  return `${API_BASE}/live-stream${sep}`;
};

export const getLiveFrameUrl = () => {
  const token = getAuthToken();
  const sep = token ? `&token=${encodeURIComponent(token)}` : '';
  return `${API_BASE}/live-frame?t=${Date.now()}${sep}`;
};

export const getOutputVideoUrl = (filename) => {
  const token = getAuthToken();
  const sep = token ? `?token=${encodeURIComponent(token)}` : '';
  return `${API_BASE}/outputs/${filename}${sep}`;
};

// API Methods
export const login = async (password) => {
  const res = await apiClient.post('/login', { password });
  if (res.data && res.data.token) {
    setAuthToken(res.data.token);
  }
  return res.data;
};

export const getHealth = async () => {
  const res = await apiClient.get('/health');
  return res.data;
};

export const getShelfStatus = async () => {
  const res = await apiClient.get('/shelf-status');
  return res.data;
};

export const getAlerts = async (unacknowledged = false, limit = 50) => {
  const res = await apiClient.get('/alerts', {
    params: { unacknowledged, limit }
  });
  return res.data;
};

export const acknowledgeAlert = async (alertId) => {
  const res = await apiClient.post(`/alerts/${alertId}/ack`);
  return res.data;
};

export const getHistory = async (zoneId = null, hours = 24) => {
  const params = { hours };
  if (zoneId) params.zone = zoneId;
  const res = await apiClient.get('/history', { params });
  return res.data;
};

export const getZones = async () => {
  const res = await apiClient.get('/zones');
  return res.data;
};

export const createZone = async (zoneData) => {
  const res = await apiClient.post('/zones', zoneData);
  return res.data;
};

export const updateZone = async (zoneId, zoneData) => {
  const res = await apiClient.put(`/zones/${zoneId}`, zoneData);
  return res.data;
};

export const deleteZone = async (zoneId) => {
  const res = await apiClient.delete(`/zones/${zoneId}`);
  return res.data;
};

export const getSource = async () => {
  const res = await apiClient.get('/source');
  return res.data;
};

export const switchSource = async (type, value) => {
  const res = await apiClient.post('/source', { type, value });
  return res.data;
};

export const uploadVideo = async (file, onUploadProgress) => {
  const formData = new FormData();
  formData.append('video', file);
  const res = await apiClient.post('/upload-video', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  });
  return res.data;
};

export const getJobStatus = async (jobId) => {
  const res = await apiClient.get(`/job-status/${jobId}`);
  return res.data;
};

export const getJobResult = async (jobId) => {
  const res = await apiClient.get(`/job-result/${jobId}`);
  return res.data;
};

export const getMetrics = async () => {
  const res = await apiClient.get('/metrics');
  return res.data;
};

// -----------------------------------------------------------------------------
// Phase 10: Model Info, Demo Studio & Camera Abstraction APIs
// -----------------------------------------------------------------------------

export const getModelInfo = async () => {
  const res = await apiClient.get('/model-info');
  return res.data;
};

export const updateModelConfig = async (thresholds) => {
  const res = await apiClient.post('/model-config', thresholds);
  return res.data;
};

export const getDemoSamples = async () => {
  const res = await apiClient.get('/demo/samples');
  return res.data;
};

export const analyzeDemoSample = async (sampleId, options = {}) => {
  const res = await apiClient.post(`/demo/analyze-sample/${sampleId}`, options);
  return res.data;
};

export const analyzeUploadedImage = async (formDataOrFile, options = {}) => {
  let body = formDataOrFile;
  let headers = {};
  if (formDataOrFile instanceof File) {
    const fd = new FormData();
    fd.append('image', formDataOrFile);
    if (options.confidence) fd.append('confidence', options.confidence);
    if (options.iou) fd.append('iou', options.iou);
    body = fd;
    headers['Content-Type'] = 'multipart/form-data';
  }
  const res = await apiClient.post('/analyze-image', body, {
    headers,
    params: options
  });
  return res.data;
};

export const importDemoSample = async (formData) => {
  const res = await apiClient.post('/demo/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return res.data;
};

export const getCameraStatus = async () => {
  const res = await apiClient.get('/camera/status');
  return res.data;
};

export const switchCameraMode = async (mode, extra = {}) => {
  const res = await apiClient.post('/camera/mode', { mode, ...extra });
  return res.data;
};

export const controlCamera = async (action, extra = {}) => {
  const res = await apiClient.post('/camera/control', { action, ...extra });
  return res.data;
};

export const clearSimulatedData = async () => {
  const res = await apiClient.post('/camera/clear-simulated');
  return res.data;
};
