// src/api/axiosClient.js (ou onde você configura o axios)
import axios from 'axios';

const axiosClient = axios.create({
    baseURL: process.env.REACT_APP_BACKEND_URL,
});

// Isso adiciona o token automaticamente em TODAS as chamadas
axiosClient.interceptors.request.use((config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
        config.headers.Authorization = `Token ${token}`;
    }
    return config;
});

export default axiosClient;
