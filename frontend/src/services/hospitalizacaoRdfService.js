import axios from 'axios';

const getAuthToken = () => localStorage.getItem('authToken');

export const getHospitalizacaoRdfTask = async (taskId) => {
    const token = getAuthToken();
    const response = await axios.get(`/api/pipelines/hospitalizacao-rdf/tasks/${taskId}/`, {
        headers: { Authorization: `Token ${token}` },
    });
    return response.data;
};
