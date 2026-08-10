import axios from "axios";
import Cookies from "js-cookie";

const api = axios.create({
  baseURL: process.env.REACT_APP_BACKEND_URL || "https://labsus-api.ngrok-free.app",
  withCredentials: true,
});

api.defaults.xsrfCookieName = "csrftoken";
api.defaults.xsrfHeaderName = "X-CSRFToken";

// interceptor garante CSRF sempre
api.interceptors.request.use((config) => {
  const token = Cookies.get("csrftoken");
  if (token) {
    config.headers["X-CSRFToken"] = token;
  }
  return config;
});

export default api;
