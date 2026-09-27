import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

const api = axios.create({ baseURL: API_BASE_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("okdriver_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("okdriver_token");
      localStorage.removeItem("okdriver_user");
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export function streamUrl(cameraId) {
  const token = localStorage.getItem("okdriver_token");
  return `${API_BASE_URL}/cameras/${cameraId}/stream?token=${encodeURIComponent(token || "")}`;
}

export function snapshotUrl(cameraId) {
  const token = localStorage.getItem("okdriver_token");
  return `${API_BASE_URL}/cameras/${cameraId}/snapshot?token=${encodeURIComponent(token || "")}&t=${Date.now()}`;
}

export default api;
