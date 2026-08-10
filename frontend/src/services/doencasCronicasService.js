import axios from 'axios';

const getAuthToken = () => localStorage.getItem('authToken');

export const getDoencasCronicasTask = async (taskId) => {
    const token = getAuthToken();
    const response = await axios.get(`/api/pipelines/doencas-cronicas/tasks/${taskId}/`, {
        headers: { Authorization: `Token ${token}` },
    });
    return response.data;
};
