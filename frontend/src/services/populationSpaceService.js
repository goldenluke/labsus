import axios from 'axios';

const getAuthToken = () => localStorage.getItem('authToken');
const authHeaders = () => ({ headers: { Authorization: `Token ${getAuthToken()}` } });

export const getPopulationSpaceTask = async (taskId) => {
    const response = await axios.get(`/api/pipelines/population-space/tasks/${taskId}/`, authHeaders());
    return response.data;
};

export const lookupFacility = async (cnes, { ano, mes, uf, representation }) => {
    const params = { ano, mes };
    if (uf) params.uf = uf;
    if (representation) params.representation = representation;
    const response = await axios.get(`/api/pipelines/population-space/facility/${cnes}/`, { ...authHeaders(), params });
    return response.data;
};

// Busca rápida por PREFIXO de código CNES (a BPHO não modela nome/UF de
// estabelecimento, só o código) -- diferente de lookupFacility, que roda
// a consulta pesada de indicadores. Usado pelo FacilitySearchPicker.
export const searchFacilities = async (query) => {
    const response = await axios.get('/api/pipelines/population-space/facility-search/', {
        ...authHeaders(), params: { q: query },
    });
    return response.data;
};

export const triggerCompare = async (facilities, geometry = 'euclidean') => {
    const response = await axios.post('/api/pipelines/population-space/trigger/compare/', { facilities, geometry }, authHeaders());
    return response.data;
};

export const triggerCausal = async (facilities, threshold) => {
    const payload = { facilities };
    if (threshold !== undefined && threshold !== null && threshold !== '') payload.threshold = threshold;
    const response = await axios.post('/api/pipelines/population-space/trigger/causal/', payload, authHeaders());
    return response.data;
};

export const triggerAnomaly = async (facilities, contamination) => {
    const response = await axios.post('/api/pipelines/population-space/trigger/anomaly/', { facilities, contamination }, authHeaders());
    return response.data;
};

export const triggerRisk = async (facilities, weights) => {
    const payload = { facilities };
    if (weights) payload.weights = weights;
    const response = await axios.post('/api/pipelines/population-space/trigger/risk/', payload, authHeaders());
    return response.data;
};

export const triggerPredictUncertainty = async (facilities, targetFeature, kernel) => {
    const response = await axios.post('/api/pipelines/population-space/trigger/predict-uncertainty/', {
        facilities, target_feature: targetFeature, kernel,
    }, authHeaders());
    return response.data;
};

export const triggerClassify = async (facilities, labelFeature, threshold) => {
    const payload = { facilities, label_feature: labelFeature };
    if (threshold !== undefined && threshold !== null && threshold !== '') payload.threshold = threshold;
    const response = await axios.post('/api/pipelines/population-space/trigger/classify/', payload, authHeaders());
    return response.data;
};

export const triggerTransitions = async (facilities, k) => {
    const response = await axios.post('/api/pipelines/population-space/trigger/transitions/', { facilities, k }, authHeaders());
    return response.data;
};

export const triggerSurvival = async (facilities, eventFeature, eventThreshold, k) => {
    const payload = { facilities, event_feature: eventFeature, k };
    if (eventThreshold !== undefined && eventThreshold !== null && eventThreshold !== '') payload.event_threshold = eventThreshold;
    const response = await axios.post('/api/pipelines/population-space/trigger/survival/', payload, authHeaders());
    return response.data;
};

export const triggerIntervene = async (facilities, targetFacilityUri, shifts, riskWeights, labelFeature, threshold) => {
    const payload = { facilities, target_facility_uri: targetFacilityUri, shifts, label_feature: labelFeature };
    if (riskWeights) payload.risk_weights = riskWeights;
    if (threshold !== undefined && threshold !== null && threshold !== '') payload.threshold = threshold;
    const response = await axios.post('/api/pipelines/population-space/trigger/intervene/', payload, authHeaders());
    return response.data;
};

export const triggerGraph = async (facilities, geometry, k, phenotypeK) => {
    const response = await axios.post('/api/pipelines/population-space/trigger/graph/', {
        facilities, geometry, k, phenotype_k: phenotypeK,
    }, authHeaders());
    return response.data;
};

export const triggerFactor = async (facilities, nFactors) => {
    const response = await axios.post('/api/pipelines/population-space/trigger/factor/', {
        facilities, n_factors: nFactors,
    }, authHeaders());
    return response.data;
};

export const triggerTopology = async (facilities, minPersistence, maxDimension, nCubes, percOverlap) => {
    const response = await axios.post('/api/pipelines/population-space/trigger/topology/', {
        facilities, min_persistence: minPersistence, max_dimension: maxDimension, n_cubes: nCubes, perc_overlap: percOverlap,
    }, authHeaders());
    return response.data;
};

export const triggerEarlyWarning = async (facilities, minPoints, windowSize, nSurrogates, detrendMethod) => {
    const response = await axios.post('/api/pipelines/population-space/trigger/early-warning/', {
        facilities, min_points: minPoints, window_size: windowSize, n_surrogates: nSurrogates, detrend_method: detrendMethod,
    }, authHeaders());
    return response.data;
};

export const triggerGnn = async (facilities, geometry, k, phenotypeK, labelFraction, hiddenDim, epochs, learningRate) => {
    const response = await axios.post('/api/pipelines/population-space/trigger/gnn/', {
        facilities, geometry, k, phenotype_k: phenotypeK, label_fraction: labelFraction,
        hidden_dim: hiddenDim, epochs, learning_rate: learningRate,
    }, authHeaders());
    return response.data;
};

export const triggerDynamics = async (facilities, nWorst) => {
    const response = await axios.post('/api/pipelines/population-space/trigger/dynamics/', {
        facilities, n_worst: nWorst,
    }, authHeaders());
    return response.data;
};

export const triggerPerCapita = async (facilities) => {
    const response = await axios.post('/api/pipelines/population-space/trigger/per-capita/', {
        facilities,
    }, authHeaders());
    return response.data;
};

export const triggerMunicipio = async (municipios, diseases = []) => {
    const response = await axios.post('/api/pipelines/population-space/trigger/municipio/', {
        municipios,
        diseases,
    }, authHeaders());
    return response.data;
};

export const triggerNotificacao = async (diseaseCode, yearSuffixes, limit = 2000) => {
    const response = await axios.post('/api/pipelines/population-space/trigger/notificacao/', {
        disease_code: diseaseCode,
        year_suffixes: yearSuffixes,
        limit,
    }, authHeaders());
    return response.data;
};

export const triggerFamilia = async ({ familyIds, sampleSize }) => {
    const payload = familyIds && familyIds.length > 0
        ? { family_ids: familyIds }
        : { sample_size: sampleSize };
    const response = await axios.post('/api/pipelines/population-space/trigger/familia/', payload, authHeaders());
    return response.data;
};
