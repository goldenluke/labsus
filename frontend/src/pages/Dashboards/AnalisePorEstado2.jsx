// src/pages/Dashboards/AnalisePorEstadoPage.jsx

import React, { useMemo, useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import Plot from 'react-plotly.js';
import axios from 'axios';

// Importa os componentes de gráfico
import MapaCoropleticoEstado from '../../components/charts/MapaCoropleticoEstado';
import HistogramaIndicadorEstado from '../../components/charts/HistogramaIndicadorEstado';
import RankingMunicipiosEstado from '../../components/charts/RankingMunicipiosEstado';
import HistoricoIndicadorEstado from '../../components/charts/HistoricoIndicadorEstado';
import GraficoDispersaoEstado from '../../components/charts/GraficoDispersaoEstado';

// Importa mapas de configuração e indicadores
import { INDICADORES_MAP } from '../../config/indicadores';
import { UF_CONFIGS } from '../../config/ufConfigs';
const LOCAL_MAP_CONFIGS = UF_CONFIGS;


// Dicionário que mapeia a sigla da UF para o nome do seu arquivo GeoJSON na pasta 'public'
const GEOJSON_PATHS = { 'AC': 'geojs-12-mun', 'AL': 'geojs-27-mun', 'AP': 'geojs-16-mun', 'AM': 'geojs-13-mun', 'BA': 'geojs-29-mun', 'CE': 'geojs-23-mun', 'DF': 'geojs-53-mun', 'ES': 'geojs-32-mun', 'GO': 'geojs-52-mun', 'MA': 'geojs-21-mun', 'MT': 'geojs-51-mun', 'MS': 'geojs-50-mun', 'MG': 'geojs-31-mun', 'PA': 'geojs-15-mun', 'PB': 'geojs-25-mun', 'PR': 'geojs-41-mun', 'PE': 'geojs-26-mun', 'PI': 'geojs-22-mun', 'RJ': 'geojs-33-mun', 'RN': 'geojs-24-mun', 'RS': 'geojs-43-mun', 'RO': 'geojs-11-mun', 'RR': 'geojs-14-mun', 'SC': 'geojs-42-mun', 'SP': 'geojs-35-mun', 'SE': 'geojs-28-mun', 'TO': 'geojs-17-mun', 'BR': 'geojs-100-mun' };

// A chave de identificação dentro da propriedade 'properties' do seu GeoJSON
const GEOJSON_ID_KEY = 'id';

// Dicionário com as configurações de centro e zoom para cada mapa estadual
const MAP_CONFIGS = {
    'AC': { nome: 'Acre', center: { lat: -9.02, lon: -70.81 }, scale: 5, ibgePrefix: '12' },
    'AL': { nome: 'Alagoas', center: { lat: -9.57, lon: -36.78 }, scale: 8, ibgePrefix: '27' },
    'AP': { nome: 'Amapá', center: { lat: 1.41, lon: -51.77 }, scale: 5, ibgePrefix: '16' },
    'AM': { nome: 'Amazonas', center: { lat: -3.41, lon: -65.85 }, scale: 4, ibgePrefix: '13' },
    'BA': { nome: 'Bahia', center: { lat: -12.96, lon: -41.81 }, scale: 5, ibgePrefix: '29' },
    'CE': { nome: 'Ceará', center: { lat: -5.20, lon: -39.53 }, scale: 6, ibgePrefix: '23' },
    'DF': { nome: 'Distrito Federal', center: { lat: -15.78, lon: -47.92 }, scale: 9, ibgePrefix: '53' },
    'ES': { nome: 'Espírito Santo', center: { lat: -19.18, lon: -40.30 }, scale: 8, ibgePrefix: '32' },
    'GO': { nome: 'Goiás', center: { lat: -15.98, lon: -49.86 }, scale: 5.5, ibgePrefix: '52' },
    'MA': { nome: 'Maranhão', center: { lat: -5.42, lon: -45.44 }, scale: 5, ibgePrefix: '21' },
    'MT': { nome: 'Mato Grosso', center: { lat: -12.64, lon: -55.42 }, scale: 4.5, ibgePrefix: '51' },
    'MS': { nome: 'Mato Grosso do Sul', center: { lat: -20.51, lon: -54.54 }, scale: 5, ibgePrefix: '50' },
    'MG': { nome: 'Minas Gerais', center: { lat: -18.55, lon: -44.55 }, scale: 5.5, ibgePrefix: '31' },
    'PA': { nome: 'Pará', center: { lat: -3.79, lon: -52.48 }, scale: 4, ibgePrefix: '15' },
    'PB': { nome: 'Paraíba', center: { lat: -7.28, lon: -36.72 }, scale: 8, ibgePrefix: '25' },
    'PR': { nome: 'Paraná', center: { lat: -24.89, lon: -51.55 }, scale: 6, ibgePrefix: '41' },
    'PE': { nome: 'Pernambuco', center: { lat: -8.38, lon: -37.86 }, scale: 6, ibgePrefix: '26' },
    'PI': { nome: 'Piauí', center: { lat: -7.76, lon: -42.75 }, scale: 5.5, ibgePrefix: '22' },
    'RJ': { nome: 'Rio de Janeiro', center: { lat: -22.25, lon: -42.66 }, scale: 7.5, ibgePrefix: '33' },
    'RN': { nome: 'Rio Grande do Norte', center: { lat: -5.81, lon: -36.56 }, scale: 8, ibgePrefix: '24' },
    'RS': { nome: 'Rio Grande do Sul', center: { lat: -30.17, lon: -53.50 }, scale: 5.5, ibgePrefix: '43' },
    'RO': { nome: 'Rondônia', center: { lat: -10.83, lon: -63.34 }, scale: 5, ibgePrefix: '11' },
    'RR': { nome: 'Roraima', center: { lat: 2.73, lon: -61.22 }, scale: 5, ibgePrefix: '14' },
    'SC': { nome: 'Santa Catarina', center: { lat: -27.45, lon: -50.21 }, scale: 6.5, ibgePrefix: '42' },
    'SP': { nome: 'São Paulo', center: { lat: -22.19, lon: -48.79 }, scale: 6, ibgePrefix: '35' },
    'SE': { nome: 'Sergipe', center: { lat: -10.57, lon: -37.45 }, scale: 9, ibgePrefix: '28' },
    'TO': { nome: 'Tocantins', center: { lat: -9.46, lon: -48.26 }, scale: 5.5, ibgePrefix: '17' },
    'BR': { nome: 'Brasil', center: { lat: -14, lon: -50 }, scale: 2.5, ibgePrefix: '' },
};


const AnalisePorEstadoPage = () => {
    const [allData, setAllData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const [availableFiles, setAvailableFiles] = useState([]);
    const [selectedFileId, setSelectedFileId] = useState('');
    const { uf: ufParam } = useParams();
    const [selectedUf, setSelectedUf] = useState(ufParam ? ufParam.toUpperCase() : 'GO');
    const [availableIndicators, setAvailableIndicators] = useState([]);
    const [selectedIndicator, setSelectedIndicator] = useState('TMI');
    const [selectedYear, setSelectedYear] = useState(2022);

    const [rankingType, setRankingType] = useState('piores');
    const [scatterX, setScatterX] = useState('TAXA_MEDICOS');
    const [scatterY, setScatterY] = useState('TMI');
    const [selectedMunicipality, setSelectedMunicipality] = useState(null);

    const [geojson, setGeojson] = useState(null);
    const [loadingMap, setLoadingMap] = useState(true);

    const availableUfs = useMemo(() => {
        if (!allData || allData.length === 0) return [];
        const ufs = [...new Set(allData.map(item => item.UF))].sort();
        return ufs;
    }, [allData]);


    useEffect(() => {
        if (ufParam && ufParam.toUpperCase() !== selectedUf) {
            setSelectedUf(ufParam.toUpperCase());
        }
    }, [ufParam, selectedUf]);

    useEffect(() => {
        const fetchFiles = async () => {
            setLoading(true);
            setError('');
            try {
                const token = localStorage.getItem('authToken');
                const response = await axios.get('/api/files/', { headers: { 'Authorization': `Token ${token}` } });
                setAvailableFiles(response.data);
                if (response.data.length > 0) {
                    setSelectedFileId(response.data[0].id.toString());
                } else {
                    setLoading(false);
                    setError('Nenhum ficheiro CSV foi enviado para o seu usuário. Por favor, faça upload de um arquivo na página de gestão de ficheiros.');
                }
            } catch (err) {
                console.error('Falha ao buscar a lista de ficheiros:', err);
                setError(`Falha ao buscar a lista de ficheiros: ${err.response?.data?.detail || err.message}`);
                setLoading(false);
            }
        };
        fetchFiles();
    }, []);

    const fetchData = useCallback(async () => {
        if (!selectedFileId) {
            setAllData([]);
            if (availableFiles.length > 0) {
                setLoading(false);
            }
            return;
        }

        setLoading(true);
        setError('');
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.get(`/api/files/${selectedFileId}/data/`, { headers: { 'Authorization': `Token ${token}` } });
            const data = response.data;

            const indicators = [];
            if (data.length > 0) {
                const firstItem = data[0];
                console.log("Primeira linha de dados do CSV:", firstItem);

                const metadataColumns = [
                    'cod_mun_ibge_6', 'municipio', 'UF', 'cod_mun_ibge_7', 'perfil', 'nome_uf'
                ];

                for (const key of Object.keys(firstItem)) {
                    console.log(`Analisando coluna: '${key}'`);
                    if (metadataColumns.includes(key)) {
                        console.log(`  -> Ignorada: "${key}" é coluna de metadado.`);
                        continue;
                    }

                    const value = String(firstItem[key]).replace(',', '.');
                    const numericValue = parseFloat(value);

                    if (!isNaN(numericValue)) {
                        indicators.push(key);
                        console.log(`  -> Adicionada como indicador: "${key}" (valor: ${firstItem[key]}, convertido: ${numericValue})`);
                    } else {
                        console.log(`  -> Ignorada: "${key}" não parece ser um número na primeira linha (valor: "${firstItem[key]}").`);
                    }
                }
            }

            const dataNumerica = data.map(item => {
                const newItem = { ...item };

                // Os logs de DEBUG ANO foram mantidos para sua referência, mas o tratamento já vem do backend.
                // console.log(`DEBUG ANO: Item original: ${item.ANO}, Tipo original: ${typeof item.ANO}`);
                // if (newItem.ANO !== undefined && typeof newItem.ANO === 'string') {
                //     newItem.ANO = parseInt(newItem.ANO);
                //     if (isNaN(newItem.ANO)) newItem.ANO = null;
                //     console.log(`DEBUG ANO: Item convertido: ${newItem.ANO}, Tipo convertido: ${typeof newItem.ANO}`);
                // } else if (typeof newItem.ANO === 'number') {
                //     console.log(`DEBUG ANO: Item já era número: ${newItem.ANO}`);
                // } else {
                //     console.log(`DEBUG ANO: Item.ANO é indefinido ou não é string/número: ${newItem.ANO}`);
                // }

                // Não precisa mais dessas conversões se o backend já as faz para ANO e populacao
                // if (newItem.populacao !== undefined && typeof newItem.populacao === 'string') {
                //     newItem.populacao = parseFloat(newItem.populacao.replace(',', '.'));
                //     if (isNaN(newItem.populacao)) newItem.populacao = null;
                // }

                indicators.forEach(ind => {
                    const val = String(newItem[ind]).replace(',', '.');
                    newItem[ind] = parseFloat(val);
                    if (isNaN(newItem[ind])) {
                        newItem[ind] = null;
                    }
                });
                return newItem;
            });
            setAllData(dataNumerica);

            setAvailableIndicators(indicators);

            if (indicators.length > 0 && !selectedIndicator) {
                setSelectedIndicator(indicators[0]);
            } else if (indicators.length === 0) {
                setSelectedIndicator('');
                setError('Nenhum indicador numérico válido foi encontrado no arquivo CSV. Verifique o formato do seu arquivo.');
            }

        } catch (err) {
            console.error('Falha ao carregar os dados do ficheiro:', err);
            setError(`Falha ao carregar os dados do ficheiro: ${err.response?.data?.error || err.message}`);
            setAllData([]);
        } finally {
            setLoading(false);
        }
    }, [selectedFileId, availableFiles.length, selectedIndicator]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    useEffect(() => {
        if (allData.length > 0) {
            console.log("--- Dados Brutos Carregados (Primeiras 5 linhas) ---");
            allData.slice(0, 5).forEach(item => console.log(item));

            const ufsInAllData = [...new Set(allData.map(item => item.UF))].sort();
            console.log("UFs disponíveis nos dados brutos:", ufsInAllData);

            const yearsInAllData = [...new Set(allData.map(item => item.ANO).filter(year => typeof year === 'number' && year !== null))].sort((a,b) => b-a);
            console.log("Anos disponíveis nos dados brutos:", yearsInAllData);

            if (ufsInAllData.length > 0 && (!selectedUf || !ufsInAllData.includes(selectedUf)) ) {
                setSelectedUf(ufParam ? ufParam.toUpperCase() : ufsInAllData[0]);
            }
            if (yearsInAllData.length > 0 && (selectedYear === null || selectedYear === undefined || !yearsInAllData.includes(selectedYear)) ) {
                setSelectedYear(yearsInAllData[0]);
            }

            console.log("selectedUf atual:", selectedUf);
            console.log("selectedYear atual:", selectedYear);
        }
    }, [allData, selectedUf, selectedYear, ufParam]);

    // availableUfs já é um useMemo diretamente.


    useEffect(() => {
        if (!selectedUf) {
            setGeojson(null);
            setLoadingMap(false);
            return;
        }
        const fetchGeojson = async () => {
            setLoadingMap(true);
            setError('');
            const fileName = GEOJSON_PATHS[selectedUf.toUpperCase()];
            if (!fileName) {
                setLoadingMap(false);
                setError(`Nome de arquivo GeoJSON não encontrado para a UF: ${selectedUf}`);
                console.warn(`GeoJSON filename not found for UF: ${selectedUf}`);
                return;
            }

            const fileUrl = `/geojson_uf/${fileName}.json`;

            try {
                const response = await fetch(fileUrl);
                if (!response.ok) {
                    throw new Error(`Erro de rede ou arquivo não encontrado: ${response.status} ${response.statusText}`);
                }
                const jsonData = await response.json();
                setGeojson(jsonData);
            } catch (error) {
                console.error(`Erro ao buscar GeoJSON para ${selectedUf} do diretório público:`, error);
                setGeojson(null);
                setError(`Não foi possível carregar o mapa GeoJSON para ${selectedUf}. Verifique a conexão ou os arquivos GeoJSON no frontend (public/geojson_uf/).`);
            } finally {
                setLoadingMap(false);
            }
        };
        fetchGeojson();
    }, [selectedUf]);


    const ufDataFilteredByYear = useMemo(() => {
        if (!selectedUf || !allData || allData.length === 0 || selectedYear === null || selectedYear === undefined) {
            console.log("Filtro: Condições iniciais não atendidas para ufDataFilteredByYear.");
            console.log(`selectedUf: ${selectedUf}, allData.length: ${allData.length}, selectedYear: ${selectedYear}`);
            return [];
        }

        const ufConfigForFilter = LOCAL_MAP_CONFIGS[selectedUf];
        let filteredData = [];

        console.log(`Filtro: Tentando filtrar por UF: '${selectedUf}' (ibgePrefix: '${ufConfigForFilter?.ibgePrefix}')`);

        if (ufConfigForFilter && ufConfigForFilter.ibgePrefix) {
            filteredData = allData.filter(item => {
                const muniCode = String(item.cod_mun_ibge_7);
                const ufPrefix = muniCode.substring(0, 2);
                const isMatch = ufPrefix === ufConfigForFilter.ibgePrefix;
                return isMatch;
            });
            console.log(`Filtro: Após filtro por IBGE Prefix ('${ufConfigForFilter.ibgePrefix}'), ${filteredData.length} itens encontrados.`);
        } else {
            console.log(`Filtro: Usando coluna 'UF' para filtrar, pois ibgePrefix não disponível para '${selectedUf}'.`);
            filteredData = allData.filter(item => {
                const itemUf = item.UF;
                const isMatch = itemUf === selectedUf;
                return isMatch;
            });
            console.log(`Filtro: Após filtro por coluna 'UF' ('${selectedUf}'), ${filteredData.length} itens encontrados.`);
        }

        const finalFilteredData = filteredData.filter(item => {
            const itemYear = item.ANO;
            const isYearMatch = itemYear === selectedYear;
            return isYearMatch;
        });

        console.log(`Filtro: Dados finais após filtro por UF e Ano (total de itens): ${finalFilteredData.length}`);
        return finalFilteredData;

    }, [allData, selectedUf, selectedYear]);

    const availableYears = useMemo(() => {
        const years = new Set(allData.map(item => item.ANO).filter(year => typeof year === 'number' && year !== null));
        return Array.from(years).sort((a,b) => b-a);
    }, [allData]);


    const ufMapConfig = LOCAL_MAP_CONFIGS[selectedUf] || {};

    const mapChartData = useMemo(() => {
        if (!geojson || !ufDataFilteredByYear || ufDataFilteredByYear.length === 0 || !selectedIndicator) return null;

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
            const municipioName = feature.properties.nome;

            if (indicatorValue !== undefined && indicatorValue !== null) {
                locations.push(geoId);
                zValues.push(indicatorValue);
                const indicatorLabel = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
                textValues.push(`${municipioName}<br>${indicatorLabel}: ${indicatorValue}`);
            }
        });

        if (locations.length === 0) {
            console.warn("Nenhum dado correspondente encontrado para o indicador e UF selecionados no GeoJSON.");
            return null;
        }

        return [{
            type: 'choropleth',
            geojson: geojson,
            locations: locations,
            z: zValues,
            text: textValues,
            hoverinfo: 'text',
            featureidkey: `properties.${GEOJSON_ID_KEY}`,
            colorscale: 'Viridis',
            colorbar: {
                title: {
                    text: INDICADORES_MAP[selectedIndicator] || selectedIndicator,
                    side: 'right'
                },
                len: 0.75,
                x: 0.95,
                y: 0.5,
            },
            marker: {
                line: {
                    color: 'white',
                    width: 0.5
                }
            },
        }];
    }, [ufDataFilteredByYear, selectedIndicator, geojson]);

    const mapTitle = useMemo(() => {
        const indicatorLabel = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
        const ufName = ufMapConfig.nome || selectedUf.toUpperCase();
        return `Distribuição de ${indicatorLabel} em ${ufName} (${selectedYear})`;
    }, [selectedIndicator, ufMapConfig, selectedUf, selectedYear]);

    const municipalitiesForHistoricalComparison = useMemo(() => {
        if (ufDataFilteredByYear.length > 0) {
            return ufDataFilteredByYear.slice(0, 2).map(item => ({
                cod_mun_ibge_7: item.cod_mun_ibge_7,
                nome_mun: item.nome_mun
            }));
        }
        return [];
    }, [ufDataFilteredByYear]);


    // --- Guardas de Renderização e Mensagens de Feedback ---
    if (error) return <p className="text-center p-10 font-semibold text-lg text-red-500">{error}</p>;

    // 1. Carregando a lista de arquivos (primeiro passo)
    if (loading && availableFiles.length === 0 && selectedFileId === '') return <p className="text-center p-10 font-semibold text-lg">A carregar lista de ficheiros do usuário...</p>;

    // 2. Não há arquivos enviados pelo usuário
    if (!loading && availableFiles.length === 0 && selectedFileId === '') return <p className="text-center p-10 font-semibold text-lg">Nenhum ficheiro CSV foi enviado para o seu usuário. Por favor, faça upload de um arquivo na página de gestão de ficheiros.</p>;

    // 3. Arquivos disponíveis, mas nenhum selecionado (após erro ou reset)
    if (!selectedFileId) return (
        <div className="text-center p-10 font-semibold text-lg">
        <p>Por favor, selecione um ficheiro de dados para começar.</p>
        </div>
    );

    // 4. Carregando dados do arquivo selecionado
    if (loading && selectedFileId) return <p className="text-center p-10 font-semibold text-lg">A carregar dados do ficheiro selecionado...</p>;

    // 5. O arquivo selecionado não contém dados ou não tem as colunas esperadas
    if (allData.length === 0 && !loading) return (
        <div className="text-center p-10 font-semibold text-lg">
        <p>O ficheiro selecionado está vazio ou não contém dados válidos.</p>
        <p>Por favor, verifique o conteúdo do arquivo CSV.</p>
        </div>
    );

    // 6. Dados carregados, mas nenhuma UF foi identificada no arquivo
    if (availableUfs.length === 0 && allData.length > 0) return <p className="text-center p-10 font-semibold text-lg">Nenhuma UF identificada no ficheiro selecionado. Verifique a coluna 'UF' no CSV.</p>;

    // 7. Nenhuma UF selecionada (apesar de haver UFs disponíveis)
    if (!selectedUf && availableUfs.length > 0) return <p className="text-center p-10 font-semibold text-lg">Por favor, selecione uma UF para visualizar os dados.</p>;

    // 8. UF selecionada, mas não há dados filtrados por UF e Ano
    if (ufDataFilteredByYear.length === 0 && selectedUf && allData.length > 0 && selectedYear !== undefined && selectedYear !== null) return <p className="text-center p-10 font-semibold text-lg">Nenhum dado encontrado para a UF ({selectedUf}) e Ano ({selectedYear}) no ficheiro selecionado. Verifique os dados ou os filtros.</p>;


    // 9. Nenhum indicador identificado no arquivo
    if (availableIndicators.length === 0 && allData.length > 0) return <p className="text-center p-10 font-semibold text-lg">Nenhum indicador numérico foi identificado no ficheiro selecionado. Verifique as colunas e o formato numérico no CSV.</p>;

    // 10. Nenhum indicador selecionado
    if (!selectedIndicator && availableIndicators.length > 0) return <p className="text-center p-10 font-semibold text-lg">Por favor, selecione um indicador para visualizar o mapa.</p>;

    // 11. Carregando mapa GeoJSON
    if (loadingMap) return <p className="text-center p-10 font-semibold text-lg">A carregar mapa GeoJSON para {selectedUf}...</p>;

    // 12. Falha ao carregar GeoJSON
    if (!geojson) return <p className="text-center p-10 font-semibold text-lg">Não foi possível carregar o mapa GeoJSON para {selectedUf}. Verifique a conexão ou os arquivos GeoJSON no frontend (public/geojson_uf/).</p>;

    // 13. GeoJSON e dados prontos, mas sem dados correspondentes para o mapa
    if (!mapChartData && !loadingMap) return <p className="text-center p-10 font-semibold text-lg">Mapa carregado, mas sem dados correspondentes para exibir com os filtros atuais.</p>;


    return (
        <div className="bg-gray-50 min-h-screen">
        <h1 className="text-3xl font-bold text-center text-gray-800 mb-8">
        Análise por Estado
        </h1>

        {/* Controles de Filtro */}
        <div className="bg-white p-6 rounded-lg shadow-md mb-8 flex flex-wrap gap-4 items-center justify-center">
        <label className="flex flex-col">
        Arquivo de Dados:
        <select
        value={selectedFileId}
        onChange={(e) => setSelectedFileId(e.target.value)}
        className="p-2 border rounded-md"
        >
        <option value="">Selecione um arquivo</option>
        {availableFiles.map(file => (
            <option key={file.id} value={file.id}>
            {file.filename} (Upload: {new Date(file.uploaded_at).toLocaleDateString()})
            </option>
        ))}
        </select>
        </label>

        <label className="flex flex-col">
        Estado (UF):
        <select
        value={selectedUf}
        onChange={(e) => setSelectedUf(e.target.value)}
        className="p-2 border rounded-md"
        >
        {availableUfs.map(ufCode => (
            <option key={ufCode} value={ufCode}>{ufCode}</option>
        ))}
        </select>
        </label>

        <label className="flex flex-col">
        Ano:
        <select
        value={selectedYear}
        onChange={(e) => setSelectedYear(parseInt(e.target.value))}
        className="p-2 border rounded-md"
        >
        {availableYears.map(year => (
            <option key={year} value={year}>{year}</option>
        ))}
        </select>
        </label>

        <label className="flex flex-col">
        Indicador:
        <select
        value={selectedIndicator}
        onChange={(e) => setSelectedIndicator(e.target.value)}
        className="p-2 border rounded-md"
        >
        {availableIndicators.map(indicatorKey => (
            <option key={indicatorKey} value={indicatorKey}>
            {INDICADORES_MAP[indicatorKey] || indicatorKey}
            </option>
        ))}
        </select>
        </label>
        </div>

        {/* Gráfico do Mapa */}
        <div className="bg-white p-4 rounded-lg shadow-md h-[600px] flex flex-col justify-center items-center">
        {mapChartData && (
            <Plot
            data={mapChartData}
            layout={{
                title: {
                    text: mapTitle,
                    font: { size: 20, color: '#333' },
                    xref: 'paper',
                    x: 0.05,
                    xanchor: 'left',
                    yanchor: 'top',
                },
                geo: {
                    scope: 'south america',
                    showland: true,
                    landcolor: 'rgb(243,243,243)',
                          countrycolor: 'rgb(204,204,204)',
                          projection: { type: 'mercator' },

                          fitbounds: 'locations',
                          visible: false,

                          subunitcolor: 'rgb(204,204,243)',
                          coastlinecolor: 'rgb(204,204,204)',
                },
                margin: { t: 50, b: 20, l: 20, r: 20 },
                autosize: true,
            }}
            config={{ responsive: true, displayModeBar: false }}
            className="w-full h-full"
            />
        )}
        </div>

        {/* Seção dos Outros Gráficos */}
        <div className="flex flex-col gap-6 mt-6">
        {/* Histograma do Indicador */}
        <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
        <h2 className="text-2xl font-semibold text-gray-700 mb-4">Histograma do Indicador</h2>
        <HistogramaIndicadorEstado
        data={ufDataFilteredByYear}
        selectedIndicator={selectedIndicator}
        selectedMunicipality={selectedMunicipality}
        selectedYear={selectedYear}
        ufConfig={ufMapConfig}
        />
        </div>

        {/* Ranking de Municípios */}
        <div className="bg-white p-4 rounded-lg shadow-md h-[650px] w-full">
        <h2 className="text-2xl font-semibold text-gray-700 mb-4">Ranking de Municípios</h2>
        <div className="flex justify-center mb-4">
        <label className="mr-4">
        <input
        type="radio"
        value="piores"
        checked={rankingType === 'piores'}
        onChange={() => setRankingType('piores')}
        className="mr-2"
        />
        Piores
        </label>
        <label>
        <input
        type="radio"
        value="melhores"
        checked={rankingType === 'melhores'}
        onChange={() => setRankingType('melhores')}
        className="mr-2"
        />
        Melhores
        </label>
        </div>
        <RankingMunicipiosEstado
        data={ufDataFilteredByYear}
        selectedIndicator={selectedIndicator}
        rankingType={rankingType}
        selectedYear={selectedYear}
        ufConfig={ufMapConfig}
        />
        </div>

        {/* Série Histórica do Indicador */}
        <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
        <h2 className="text-2xl font-semibold text-gray-700 mb-4">Série Histórica do Indicador</h2>
        <HistoricoIndicadorEstado
        data={allData.filter(item => {
            const ufConfigForFilter = LOCAL_MAP_CONFIGS[selectedUf];
            if (ufConfigForFilter && ufConfigForFilter.ibgePrefix) {
                return String(item.cod_mun_ibge_7).startsWith(ufConfigForFilter.ibgePrefix);
            }
            return item.UF === selectedUf;
        })}
        selectedIndicator={selectedIndicator}
        selectedMunicipalities={municipalitiesForHistoricalComparison}
        ufConfig={ufMapConfig}
        />
        </div>

        {/* Gráfico de Dispersão */}
        <div className="bg-white p-4 rounded-lg shadow-md h-[650px] w-full">
        <h2 className="text-2xl font-semibold text-gray-700 mb-4">Correlação entre Indicadores</h2>
        <div className="flex flex-wrap gap-4 items-center justify-center mb-4">
        <label className="flex flex-col">
        Eixo X:
        <select
        value={scatterX}
        onChange={(e) => setScatterX(e.target.value)}
        className="p-2 border rounded-md"
        >
        {availableIndicators.map(indicatorKey => (
            <option key={indicatorKey} value={indicatorKey}>
            {INDICADORES_MAP[indicatorKey] || indicatorKey}
            </option>
        ))}
        </select>
        </label>
        <label className="flex flex-col">
        Eixo Y:
        <select
        value={scatterY}
        onChange={(e) => setScatterY(e.target.value)}
        className="p-2 border rounded-md"
        >
        {availableIndicators.map(indicatorKey => (
            <option key={indicatorKey} value={indicatorKey}>
            {INDICADORES_MAP[indicatorKey] || indicatorKey}
            </option>
        ))}
        </select>
        </label>
        </div>
        <GraficoDispersaoEstado
        data={ufDataFilteredByYear}
        scatterX={scatterX}
        scatterY={scatterY}
        selectedYear={selectedYear}
        ufConfig={ufMapConfig}
        />
        </div>
        </div>
        </div>
    );
};

export default AnalisePorEstadoPage;
