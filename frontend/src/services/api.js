// src/services/api.js
import axios from 'axios';

const getAuthToken = () => localStorage.getItem('authToken');

export const getFiles = async () => {
    const token = getAuthToken();
    const response = await axios.get('/api/files/', {
        headers: { 'Authorization': `Token ${token}` }
    });
    return response.data;
};

export const getFileContent = async (fileId) => {
    const token = getAuthToken();
    const response = await axios.get(`/api/files/${fileId}/data/`, {
        headers: { 'Authorization': `Token ${token}` }
    });
    return response.data;
};
// You can add more API calls here as needed (e.g., login, register)
