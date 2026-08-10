import axios from 'axios';

const getAuthToken = () => localStorage.getItem('authToken');

export const getBphoClasses = async () => {
    const token = getAuthToken();
    const response = await axios.get('/api/pipelines/ontologia/classes/', {
        headers: { Authorization: `Token ${token}` },
    });
    return response.data.classes || [];
};
