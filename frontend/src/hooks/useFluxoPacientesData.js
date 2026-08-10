// src/hooks/useFluxoPacientesData.js

import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useLocation } from 'react-router-dom';

// Mapeamento de Código IBGE para Sigla
const UF_CODIGOS = {
    '12': 'AC', '27': 'AL', '16': 'AP', '13': 'AM', '29': 'BA', '23': 'CE',
    '53': 'DF', '32': 'ES', '52': 'GO', '21': 'MA', '51': 'MT', '50': 'MS',
    '31': 'MG', '15': 'PA', '25': 'PB', '41': 'PR', '26': 'PE', '22': 'PI',
    '33': 'RJ', '24': 'RN', '43': 'RS', '11': 'RO', '14': 'RR', '42': 'SC',
    '35': 'SP', '28': 'SE', '17': 'TO'
};

// Função auxiliar para normalizar UF (Código -> Sigla)
const normalizeUF = (val) => {
    let strVal = String(val || '').trim().toUpperCase();
    if (UF_CODIGOS[strVal]) return UF_CODIGOS[strVal];
    return strVal;
};

export const useFluxoPacientesData = () => {
    const location = useLocation();
    const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
    const fileIdFromUrl = queryParams.get('fileId');

    const [allData, setAllData] = useState([]);
    const [availableFiles, setAvailableFiles] = useState([]);
    const [selectedFileId, setSelectedFileId] = useState(fileIdFromUrl || '');
    const [fileDetails, setFileDetails] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedUf, setSelectedUf] = useState('BR');
    const [minPacientes, setMinPacientes] = useState(5);
    const [selectedPolo, setSelectedPolo] = useState('');

    // 1. Carregar lista de arquivos
    useEffect(() => {
        const fetchFileList = async () => {
            setLoading(true);
            try {
                const token = localStorage.getItem('authToken');
                const response = await axios.get('/api/files/', { 
                    headers: { 'Authorization': `Token ${token}` }, 
                    params: { file_type: 'PATIENT_FLOW' } 
                });
                const files = response.data.results || [];
                setAvailableFiles(files);
                
                if (fileIdFromUrl && files.some(f => String(f.id) === fileIdFromUrl)) {
                    setSelectedFileId(fileIdFromUrl);
                } else if (files.length > 0) {
                    setSelectedFileId(files[0].id.toString());
                } else {
                    setLoading(false);
                }
            } catch (err) {
                setError("Não foi possível carregar a lista de ficheiros."); 
                setLoading(false);
            }
        };
        fetchFileList();
    }, [fileIdFromUrl]);

    // 2. Carregar dados do arquivo selecionado (COM NORMALIZAÇÃO DE UF)
    useEffect(() => {
        if (!selectedFileId) { 
            setAllData([]); 
            setFileDetails(null); 
            setLoading(false); 
            return; 
        }
        const fetchData = async () => {
            setLoading(true); 
            setError(null);
            try {
                const token = localStorage.getItem('authToken');
                const [detailsRes, dataRes] = await Promise.all([
                    axios.get(`/api/files/${selectedFileId}/`, { headers: { 'Authorization': `Token ${token}` } }),
                    axios.get(`/api/files/${selectedFileId}/data/`, { headers: { 'Authorization': `Token ${token}` } })
                ]);

                setFileDetails(detailsRes.data);
                
                const processedData = dataRes.data.map(item => ({
                    ...item,
                    N_PACIENTES: parseInt(item.N_PACIENTES, 10) || 0,
                    VALOR_TOTAL: parseFloat(String(item.VALOR_TOTAL).replace(',', '.')),
                    lat_origem: parseFloat(String(item.lat_origem).replace(',', '.')),
                    lon_origem: parseFloat(String(item.lon_origem).replace(',', '.')),
                    lat_destino: parseFloat(String(item.lat_destino).replace(',', '.')),
                    lon_destino: parseFloat(String(item.lon_destino).replace(',', '.')),
                    // CORREÇÃO CRÍTICA: Normaliza código numérico para sigla aqui
                    uf_origem: normalizeUF(item.uf_origem),
                    uf_destino: normalizeUF(item.uf_destino)
                }));
                setAllData(processedData);

                const minPacientesMatch = detailsRes.data.description.match(/Min. Pacientes:\s*(\d+)/);
                if (minPacientesMatch) setMinPacientes(parseInt(minPacientesMatch[1], 10));
            } catch (err) {
                setError("Não foi possível carregar os dados do ficheiro."); 
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [selectedFileId]);

    const flowData = useMemo(() => allData, [allData]);
    
    const filteredFlowData = useMemo(() => 
        flowData.filter(d => d.N_PACIENTES >= minPacientes), 
    [flowData, minPacientes]);

    const availableUfs = useMemo(() => {
        const ufs = new Set();
        flowData.forEach(d => {
            if (d.uf_origem) ufs.add(d.uf_origem);
            if (d.uf_destino) ufs.add(d.uf_destino);
        });
        const cleanUfs = Array.from(ufs).sort();
        return ['BR', ...cleanUfs];
    }, [flowData]);

    const rankingData = useMemo(() => { 
        if (!filteredFlowData.length) return { polos: [], enviadores: [] }; 
        
        const polos = filteredFlowData.reduce((acc, d) => { 
            const key = `${d.municipio_destino} (${d.uf_destino})`; 
            acc[key] = (acc[key] || 0) + d.N_PACIENTES; 
            return acc; 
        }, {}); 
        
        const enviadores = filteredFlowData.reduce((acc, d) => { 
            const key = `${d.municipio_origem} (${d.uf_origem})`; 
            acc[key] = (acc[key] || 0) + d.N_PACIENTES; 
            return acc; 
        }, {}); 
        
        const topPolos = Object.entries(polos).sort((a, b) => b[1] - a[1]).slice(0, 10); 
        const topEnviadores = Object.entries(enviadores).sort((a, b) => b[1] - a[1]).slice(0, 10); 
        
        return { polos: topPolos, enviadores: topEnviadores }; 
    }, [filteredFlowData]);

    const polosSankeyOptions = useMemo(() => { 
        if (!rankingData || !rankingData.polos) return []; 
        return rankingData.polos.map(p => p[0]); 
    }, [rankingData]);

    useEffect(() => { 
        if (polosSankeyOptions.length > 0 && (!selectedPolo || !polosSankeyOptions.includes(selectedPolo))) { 
            setSelectedPolo(polosSankeyOptions[0]); 
        } 
    }, [polosSankeyOptions, selectedPolo]);

    const sankeyDataAndLayout = useMemo(() => { 
        if (!filteredFlowData || !selectedPolo) return null; 
        
        const poloNameOnly = selectedPolo.split(' (')[0]; 
        const poloData = filteredFlowData
            .filter(d => d.municipio_destino === poloNameOnly)
            .sort((a,b) => b.N_PACIENTES - a.N_PACIENTES); 
            
        if (poloData.length === 0) return null; 
        
        const originLabels = poloData.map(d => `${d.municipio_origem} (${d.uf_origem})`); 
        const labels = [selectedPolo, ...new Set(originLabels)]; 
        const dynamicHeight = Math.max(500, labels.length * 28); 
        
        const plotData = [{ 
            type: 'sankey', 
            orientation: 'h', 
            node: { 
                pad: 10, thickness: 15, line: { color: 'black', width: 0.5 }, label: labels, 
            }, 
            link: { 
                source: poloData.map(d => labels.indexOf(`${d.municipio_origem} (${d.uf_origem})`)), 
                target: poloData.map(() => 0), 
                value: poloData.map(d => d.N_PACIENTES), 
            } 
        }]; 
        
        const layout = { 
            title: `Fluxo de Pacientes para ${selectedPolo}`, 
            height: dynamicHeight, font: { size: 12 }, margin: { t: 50, b: 50, l: 50, r: 50 } 
        }; 
        
        return { plotData, layout }; 
    }, [filteredFlowData, selectedPolo]);

    return {
        loading, error, fileDetails, availableFiles, selectedFileId, setSelectedFileId,
        flowData, filteredFlowData, availableUfs, selectedUf, setSelectedUf,
        minPacientes, setMinPacientes,
        rankingData,
        polosSankeyOptions, selectedPolo, setSelectedPolo, sankeyDataAndLayout
    };
};