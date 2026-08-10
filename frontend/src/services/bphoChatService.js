import axios from 'axios';

const getAuthToken = () => localStorage.getItem('authToken');

export const sendBphoChatMessage = async (message, history) => {
    const token = getAuthToken();
    const response = await axios.post('/api/pipelines/ontologia/chat/', { message, history }, {
        headers: { Authorization: `Token ${token}` },
    });
    return response.data;
};
