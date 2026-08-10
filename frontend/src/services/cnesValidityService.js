import axios from 'axios';

const getAuthToken = () => localStorage.getItem('authToken');
const authHeaders = () => ({ headers: { Authorization: `Token ${getAuthToken()}` } });

export const getFacilityValidity = async (cnes) => {
    const response = await axios.get(`/api/pipelines/cnes-validity/facility/${cnes}/`, authHeaders());
    return response.data;
};

export const getValiditySummary = async () => {
    const response = await axios.get('/api/pipelines/cnes-validity/summary/', authHeaders());
    return response.data;
};
