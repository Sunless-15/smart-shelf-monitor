import axios from 'axios';

// Defaults to the current hostname at port 5000 so mobile phones on the same WiFi work seamlessly
export const API_BASE = 
  import.meta.env.VITE_API_URL || 
  (typeof window !== 'undefined' && window.location.hostname 
    ? `http://${window.location.hostname}:5000` 
    : 'http://localhost:5000');

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

// Stream & Media URLs
export const getLiveStreamUrl = () => `${API_BASE}/live-stream`;
export const getLiveFrameUrl = () => `${API_BASE}/live-frame?t=${Date.now()}`;
export const getOutputVideoUrl = (filename) => `${API_BASE}/outputs/${filename}`;

// API Methods
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
