import axios from 'axios';

const getAuthToken = () => localStorage.getItem('authToken');

export const getRiscoPerinatalTask = async (taskId) => {
    const token = getAuthToken();
    const response = await axios.get(`/api/pipelines/risco-perinatal/tasks/${taskId}/`, {
        headers: { Authorization: `Token ${token}` },
    });
    return response.data;
};
