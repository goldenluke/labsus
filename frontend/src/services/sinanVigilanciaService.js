import axios from 'axios';

const getAuthToken = () => localStorage.getItem('authToken');
const authHeaders = () => ({ headers: { Authorization: `Token ${getAuthToken()}` } });

export const getBasesDisponiveis = async () => {
    const response = await axios.get('/api/pipelines/sinan-vigilancia/bases/', authHeaders());
    return response.data;
};

export const getVigilanciaSummary = async () => {
    const response = await axios.get('/api/pipelines/sinan-vigilancia/summary/', authHeaders());
    return response.data;
};

// Consultas por agravo podem levar até ~2 minutos contra dado real em
// escala (STRSTARTS sobre milhões de NotifiableCaseInvestigation, sem
// índice de string) -- timeout generoso, mesmo padrão já usado pelo chat
// e pelo PopulationSpace nesta mesma plataforma.
export const lookupAgravo = async (code) => {
    const response = await axios.get(`/api/pipelines/sinan-vigilancia/agravo/${code}/`, {
        ...authHeaders(),
        timeout: 150000,
    });
    return response.data;
};
