import { useState, useEffect, useMemo, useCallback } from 'react';
import axios from 'axios';
import { useLocation } from 'react-router-dom';

import { UF_CONFIGS } from '../config/ufConfigs';
import { INDICADORES_MAP } from '../config/indicadores';

// Constantes permanecem as mesmas
export const GEOJSON_PATHS = {
    'AC': 'geojs-12-mun.json', 'AL': 'geojs-27-mun.json', 'AM': 'geojs-13-mun.json',
    'AP': 'geojs-16-mun.json', 'BA': 'geojs-29-mun.json', 'CE': 'geojs-23-mun.json',
    'DF': 'geojs-53-mun.json', 'ES': 'geojs-32-mun.json', 'GO': 'geojs-52-mun.json',
    'MA': 'geojs-21-mun.json', 'MG': 'geojs-31-mun.json', 'MS': 'geojs-50-mun.json',
    'MT': 'geojs-51-mun.json', 'PA': 'geojs-15-mun.json', 'PB': 'geojs-25-mun.json',
    'PE': 'geojs-26-mun.json', 'PI': 'geojs-22-mun.json', 'PR': 'geojs-41-mun.json',
    'RJ': 'geojs-33-mun.json', 'RN': 'geojs-24-mun.json', 'RO': 'geojs-11-mun.json',
    'RR': 'geojs-14-mun.json', 'RS': 'geojs-43-mun.json', 'SC': 'geojs-42-mun.json',
    'SE': 'geojs-28-mun.json', 'SP': 'geojs-35-mun.json', 'TO': 'geojs-17-mun.json',
    'BR': 'geojs-100-mun.json',
};

export const GEOJSON_ID_KEY = 'id';

const useAnalysisData = (
    initialUf = 'GO',
    initialYear = 2022,
    initialIndicator = 'TMI',
    ufParamFromUrl = null,
    options = { fetchFileList: false, fileType: null }
) => {
    const location = useLocation();
    const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
    const fileIdFromUrl = queryParams.get('fileId');

    const [allData, setAllData] = useState([]);
    const [loading, setLoading] = useState(options.fetchFileList);
    const [error, setError] = useState(null);

    const [availableFiles, setAvailableFiles] = useState([]);
    const [selectedFileId, setSelectedFileId] = useState(fileIdFromUrl || '');
    const [selectedFileDetails, setSelectedFileDetails] = useState(null);

    const [selectedUf, setSelectedUf] = useState(ufParamFromUrl ? ufParamFromUrl.toUpperCase() : initialUf.toUpperCase());
    const [selectedYear, setSelectedYear] = useState(initialYear);
    const [selectedIndicator, setSelectedIndicator] = useState(initialIndicator);

    const [scatterX, setScatterX] = useState('');
    const [scatterY, setScatterY] = useState('');
    const [rankingType, setRankingType] = useState('piores');
    const [selectedMunicipality, setSelectedMunicipality] = useState(null);

    const [geojson, setGeojson] = useState(null);
    const [loadingMap, setLoadingMap] = useState(false);

    useEffect(() => {
        if (!options.fetchFileList) return;

        // --- INÍCIO DA CORREÇÃO DE PAGINAÇÃO ---
        const fetchAllFiles = async () => {
            setLoading(true);
            setError(null);

            let allFiles = [];
            let nextUrl = '/api/files/'; // URL inicial da API
            const token = localStorage.getItem('authToken');

            try {
                // Loop para buscar todas as páginas de resultados
                while (nextUrl) {
                    const response = await axios.get(nextUrl, {
                        headers: { 'Authorization': `Token ${token}` },
                        params: {
                            // Garante que o filtro de tipo de arquivo seja reaplicado a cada página
                            // (O axios une os params da URL com os daqui)
                            file_type: options.fileType,
                        }
                    });

                    const filesFromPage = response.data.results || [];
                    allFiles = [...allFiles, ...filesFromPage];
                    nextUrl = response.data.next; // URL da próxima página, ou null se for a última
                }

                setAvailableFiles(allFiles);

                // Lógica para selecionar o arquivo inicial após carregar todos
                if (allFiles.length > 0) {
                    if (fileIdFromUrl) {
                        const fileExists = allFiles.some(f => String(f.id) === fileIdFromUrl);
                        setSelectedFileId(fileExists ? fileIdFromUrl : allFiles[0].id.toString());
                    } else {
                        setSelectedFileId(allFiles[0].id.toString());
                    }
                }
            } catch (err) {
                setError("Não foi possível carregar a lista de arquivos.");
                console.error("Erro ao carregar lista de arquivos paginada:", err);
            } finally {
                setLoading(false);
            }
        };

        fetchAllFiles();
        // --- FIM DA CORREÇÃO DE PAGINAÇÃO ---

    }, [fileIdFromUrl, options.fetchFileList, options.fileType]);

    // O restante do hook permanece o mesmo, pois ele depende do 'selectedFileId' que
    // agora é definido corretamente a partir da lista completa de arquivos.

    const fetchData = useCallback(async () => {
        if (!selectedFileId) { setAllData([]); return; }
        setLoading(true);
        setError(null);
        try {
            const token = localStorage.getItem('authToken');
            const [detailsRes, dataRes] = await Promise.all([
                axios.get(`/api/files/${selectedFileId}/`, { headers: { 'Authorization': `Token ${token}` } }),
                                                            axios.get(`/api/files/${selectedFileId}/data/`, { headers: { 'Authorization': `Token ${token}` } })
            ]);
            setSelectedFileDetails(detailsRes.data);
            const data = dataRes.data.map(item => {
                const newItem = { ...item };
                for (const key in newItem) {
                    if (!['cod_mun_ibge_6', 'cod_mun_ibge_7'].includes(key)) {
                        const val = String(newItem[key]).replace(',', '.');
                        const num = parseFloat(val);
                        if (!isNaN(num)) newItem[key] = num;
                    }
                }
                return newItem;
            });
            setAllData(data);
        } catch (err) {
            setError("Não foi possível carregar os dados do arquivo.");
            setAllData([]);
        } finally { setLoading(false); }
    }, [selectedFileId]);

    useEffect(() => { fetchData(); }, [fetchData]);

    const availableIndicators = useMemo(() => {
        if (!allData || allData.length === 0) return [];
        const firstItem = allData[0];
        const metadataColumns = [
            'cod_mun_ibge_6', 'municipio', 'UF', 'cod_mun_ibge_7', 'perfil', 'nome_uf',
            'ANO', 'populacao', 'cor', 'cluster_num', 'ds', 'y',
            'yhat', 'yhat_lower', 'yhat_upper', 'trend', 'yearly', 'weekly',
            'MES', 'MES_x', 'MES_y'
        ];
        return Object.keys(firstItem).filter(key =>
        !metadataColumns.includes(key) && typeof firstItem[key] === 'number'
        ).sort();
    }, [allData]);

    useEffect(() => {
        if (availableIndicators.length > 0) {
            if (!selectedIndicator || !availableIndicators.includes(selectedIndicator)) setSelectedIndicator(availableIndicators[0]);
            if (!scatterX || !availableIndicators.includes(scatterX)) setScatterX(availableIndicators[0]);
            if (!scatterY || !availableIndicators.includes(scatterY)) setScatterY(availableIndicators.length > 1 ? availableIndicators[1] : availableIndicators[0]);
        }
    }, [availableIndicators, selectedIndicator, scatterX, scatterY]);

    useEffect(() => {
        if (allData.length > 0) {
            const ufsInAllData = [...new Set(allData.map(item => item.UF))].filter(Boolean).sort();
            const yearsInAllData = [...new Set(allData.map(item => item.ANO).filter(y => y != null))].sort((a, b) => b - a);
            if (ufsInAllData.length > 0 && (!selectedUf || !ufsInAllData.includes(selectedUf))) {
                setSelectedUf(ufParamFromUrl ? ufParamFromUrl.toUpperCase() : ufsInAllData[0]);
            }
            if (yearsInAllData.length > 0 && !yearsInAllData.includes(selectedYear)) {
                setSelectedYear(yearsInAllData[0]);
            }
        }
    }, [allData, selectedUf, selectedYear, ufParamFromUrl]);

    useEffect(() => {
        if (!selectedUf) return;
        const fetchGeojson = async () => {
            setLoadingMap(true);
            setError(null);
            const fileName = GEOJSON_PATHS[selectedUf.toUpperCase()];
            if (!fileName) {
                setLoadingMap(false);
                setError(`Mapa não disponível para a UF: ${selectedUf}.`);
                return;
            }
            const geojsonUrl = `/geojson_uf/${fileName}`;
            const maxAttempts = 3;
            let lastErr = null;
            for (let attempt = 1; attempt <= maxAttempts; attempt++) {
                try {
                    // cache: 'no-store' avoids the browser disk cache, which can
                    // intermittently fail to write large files (e.g. the ~22MB Brazil geojson).
                    const response = await fetch(geojsonUrl, { cache: 'no-store' });
                    if (!response.ok) throw new Error(`Arquivo não encontrado em '${geojsonUrl}'`);
                    const geojsonData = await response.json();
                    setGeojson(geojsonData);
                    setLoadingMap(false);
                    return;
                } catch (err) {
                    lastErr = err;
                }
            }
            console.error(`Erro ao buscar GeoJSON local para ${selectedUf}:`, lastErr);
            setError(`Não foi possível carregar o mapa para ${selectedUf}.`);
            setGeojson(null);
            setLoadingMap(false);
        };
        fetchGeojson();
    }, [selectedUf]);

    const availableYears = useMemo(() => {
        return [...new Set(allData.map(item => item.ANO).filter(y => y != null))].sort((a, b) => b - a);
    }, [allData]);

    const availableUfs = useMemo(() => {
        return [...new Set(allData.map(item => item.UF))].filter(Boolean).sort();
    }, [allData]);

    const ufDataFilteredByYear = useMemo(() => {
        if (!selectedUf || allData.length === 0 || selectedYear == null) return [];
        let filtered = allData;
        if (selectedUf !== 'BR') {
            filtered = allData.filter(item => item.UF === selectedUf);
        }
        return filtered.filter(item => item.ANO === selectedYear);
    }, [allData, selectedUf, selectedYear]);

    const ufDataAllYears = useMemo(() => {
        if (!selectedUf || allData.length === 0) return [];
        if (selectedUf === 'BR') return allData;
        return allData.filter(item => item.UF === selectedUf);
    }, [allData, selectedUf]);

    const ufMapConfig = UF_CONFIGS[selectedUf] || {};

    const mapChartData = useMemo(() => {
        if (!geojson || ufDataFilteredByYear.length === 0 || !selectedIndicator) return null;
        const municipalityDataMap = new Map();
        ufDataFilteredByYear.forEach(item => {
            municipalityDataMap.set(String(item.cod_mun_ibge_7), item[selectedIndicator]);
        });
        const locations = [];
        const zValues = [];
        const textValues = [];
        geojson.features.forEach(feature => {
            const geoId = String(feature.properties[GEOJSON_ID_KEY]);
            const indicatorValue = municipalityDataMap.get(geoId);
            const municipioName = feature.properties.name;
            if (indicatorValue !== undefined && indicatorValue !== null) {
                locations.push(geoId);
                zValues.push(indicatorValue);
                const indicatorLabel = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
                textValues.push(`${municipioName}<br>${indicatorLabel}: ${indicatorValue.toFixed(2)}`);
            }
        });
        if (locations.length === 0) return null;
        return [{
            type: 'choropleth', geojson, locations, z: zValues, text: textValues,
            hoverinfo: 'text', featureidkey: `properties.${GEOJSON_ID_KEY}`,
            colorscale: 'Viridis', colorbar: { title: { text: INDICADORES_MAP[selectedIndicator] || selectedIndicator, side: 'right' }, len: 0.75, x: 0.95, y: 0.5 },
            marker: { line: { color: 'white', width: 0.5 } },
        }];
    }, [ufDataFilteredByYear, selectedIndicator, geojson]);

    const mapTitle = useMemo(() => {
        const indicatorLabel = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
        const ufName = ufMapConfig.nome || selectedUf.toUpperCase();
        return `Distribuição de ${indicatorLabel} em ${ufName} (${selectedYear})`;
    }, [selectedIndicator, ufMapConfig, selectedUf, selectedYear]);

    const municipalitiesForHistoricalComparison = useMemo(() => {
        if (ufDataAllYears.length > 0) {
            const uniqueMuns = new Map();
            for (const item of ufDataAllYears) {
                if (!uniqueMuns.has(item.cod_mun_ibge_7)) {
                    uniqueMuns.set(item.cod_mun_ibge_7, {
                        cod_mun_ibge_7: item.cod_mun_ibge_7,
                        nome_mun: item.nome_mun || item.municipio,
                    });
                }
            }
            return Array.from(uniqueMuns.values()).sort((a,b) => a.nome_mun.localeCompare(b.nome_mun));
        }
        return [];
    }, [ufDataAllYears]);

    return {
        allData, loading, error,
        availableFiles, selectedFileId, setSelectedFileId, selectedFileDetails,
        selectedUf, setSelectedUf, selectedYear, setSelectedYear,
        selectedIndicator, setSelectedIndicator,
        rankingType, setRankingType, scatterX, setScatterX, scatterY, setScatterY,
        selectedMunicipality, setSelectedMunicipality,
        availableUfs, availableYears, availableIndicators,
        ufDataFilteredByYear, ufDataAllYears, ufMapConfig, geojson, loadingMap,
        mapChartData, mapTitle,
        municipalitiesForHistoricalComparison,
    };
};

export default useAnalysisData;
