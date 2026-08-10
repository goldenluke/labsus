import axios from 'axios';

const getAuthToken = () => localStorage.getItem('authToken');
const authHeaders = () => ({ headers: { Authorization: `Token ${getAuthToken()}` } });

export const getFacilityVitals = async (cnes) => {
    const response = await axios.get(`/api/pipelines/registros-vitais/facility/${cnes}/`, authHeaders());
    return response.data;
};

export const getVitalsSummary = async () => {
    const response = await axios.get('/api/pipelines/registros-vitais/summary/', authHeaders());
    return response.data;
};
