// src/pages/Dashboards/AnalisePorMunicipioPage.jsx

import React, { useMemo, useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { useParams } from 'react-router-dom';

import useAnalysisData from '../../hooks/useAnalysisData';

import HistogramaIndicadorEstado from '../../components/charts/HistogramaIndicadorEstado';

import { INDICADORES_MAP } from '../../config/indicadores';
import { INDICADOR_POLARIDADE } from '../../config/polaridadeIndicadores';

// Centroide aproximado (média das coordenadas dos anéis) de uma feature
// GeoJSON Polygon/MultiPolygon — suficiente para posicionar o marcador de
// destaque do município no mapa, não precisa ser um centroide de área exato.
const getFeatureCentroid = (feature) => {
    const geom = feature?.geometry;
    if (!geom) return null;
    const depthByType = { Polygon: 2, MultiPolygon: 3 };
    const depth = depthByType[geom.type];
    if (depth == null) return null;
    const coords = [];
    const flatten = (arr, d) => { if (d === 0) { coords.push(arr); return; } arr.forEach(sub => flatten(sub, d - 1)); };
    flatten(geom.coordinates, depth);
    if (coords.length === 0) return null;
    const lon = coords.reduce((s, c) => s + c[0], 0) / coords.length;
    const lat = coords.reduce((s, c) => s + c[1], 0) / coords.length;
    return { lat, lon };
};

const AnalisePorMunicipioPage = () => {
    const { uf: ufParam } = useParams();

    const [selectedMunicipalityCode, setSelectedMunicipalityCode] = useState('');
    const [availableMunicipalities, setAvailableMunicipalities] = useState([]);
    const [selectedDetailedIndicator, setDetailedIndicator] = useState('');

    const {
        allData, loading, error,
        availableFiles, selectedFileId, setSelectedFileId,
        selectedUf, setSelectedUf, selectedYear, setSelectedYear,
        availableUfs, availableYears, availableIndicators,
        ufDataFilteredByYear, ufDataAllYears,
        ufMapConfig, geojson, loadingMap,
    } = useAnalysisData('GO', 2022, 'TMI', ufParam, { fetchFileList: true });

    useEffect(() => {
        if (ufDataFilteredByYear && ufDataFilteredByYear.length > 0) {
            const uniqueMuns = Array.from(new Map(ufDataFilteredByYear.map(item => [item.cod_mun_ibge_7, {
                cod_mun_ibge_7: item.cod_mun_ibge_7,
                nome_mun: item.nome_mun || item.municipio
            }])).values()).sort((a, b) => a.nome_mun.localeCompare(b.nome_mun));

            setAvailableMunicipalities(uniqueMuns);
            if (uniqueMuns.length > 0 && (!selectedMunicipalityCode || !uniqueMuns.some(mun => String(mun.cod_mun_ibge_7) === String(selectedMunicipalityCode)))) {
                setSelectedMunicipalityCode(uniqueMuns[0].cod_mun_ibge_7);
            }
        } else {
            setAvailableMunicipalities([]);
            setSelectedMunicipalityCode('');
        }
    }, [ufDataFilteredByYear, selectedMunicipalityCode]);

    const selectedMunicipalityData = useMemo(() => {
        if (!selectedMunicipalityCode || !ufDataFilteredByYear) return null;
        return ufDataFilteredByYear.find(mun => String(mun.cod_mun_ibge_7) === String(selectedMunicipalityCode));
    }, [selectedMunicipalityCode, ufDataFilteredByYear]);

    useEffect(() => {
        if (availableIndicators.length > 0 && (!selectedDetailedIndicator || !availableIndicators.includes(selectedDetailedIndicator))) {
            setDetailedIndicator(availableIndicators[0]);
        }
    }, [availableIndicators, selectedDetailedIndicator]);

    const { strongPoints, weakPoints, allPoints } = useMemo(() => {
        if (!selectedMunicipalityData || !ufDataFilteredByYear || ufDataFilteredByYear.length === 0) {
            return { strongPoints: [], weakPoints: [], allPoints: [] };
        }
        const points = [];
        availableIndicators.forEach(indicator => {
            const munValue = selectedMunicipalityData[indicator];
            if (munValue == null) return;
            const allValues = ufDataFilteredByYear.map(item => item[indicator]).filter(v => v != null);
            if (allValues.length < 2) return;
            const stateAverage = allValues.reduce((sum, val) => sum + val, 0) / allValues.length;
            if (stateAverage === 0) return;
            const deviation = ((munValue - stateAverage) / stateAverage) * 100;
            const polarity = INDICADOR_POLARIDADE[indicator];
            if (polarity === 'high' && deviation !== 0) {
                points.push({ type: deviation > 0 ? 'strong' : 'weak', indicator, deviation });
            } else if (polarity === 'low' && deviation !== 0) {
                points.push({ type: deviation < 0 ? 'strong' : 'weak', indicator, deviation });
            }
        });
        points.sort((a, b) => Math.abs(b.deviation) - Math.abs(a.deviation));
        return {
            strongPoints: points.filter(p => p.type === 'strong').slice(0, 3),
                                                 weakPoints: points.filter(p => p.type === 'weak').slice(0, 3),
                                                 allPoints: points,
        };
    }, [selectedMunicipalityData, ufDataFilteredByYear, availableIndicators]);

    // Versão completa (todos os indicadores, não só os 3 melhores/piores) do
    // Raio-X acima, como um "tornado chart" — mesmo dado, visão de conjunto.
    const deviationChartData = useMemo(() => {
        if (!allPoints.length) return null;
        const sorted = [...allPoints].sort((a, b) => Math.abs(a.deviation) - Math.abs(b.deviation));
        return [{
            type: 'bar', orientation: 'h',
            y: sorted.map(p => INDICADORES_MAP[p.indicator] || p.indicator),
            x: sorted.map(p => p.deviation),
            marker: { color: sorted.map(p => p.type === 'strong' ? '#16a34a' : '#dc2626') },
            text: sorted.map(p => `${p.deviation > 0 ? '+' : ''}${p.deviation.toFixed(1)}%`),
            textposition: 'auto',
            hovertemplate: '%{y}: %{x:.1f}%<extra></extra>',
        }];
    }, [allPoints]);

    // choropleth (SVG, sem WebGL) dos municípios do estado, com um marcador
    // de destaque sobre o município selecionado, para dar contexto
    // geográfico de onde ele está e como se compara visualmente aos
    // vizinhos no indicador em foco. Usa `choropleth`/`geo` em vez de
    // `choroplethmapbox`/`mapbox` — a versão com tiles reais do OSM depende
    // de WebGL (mapbox-gl), que se mostrou pouco confiável em alguns
    // ambientes (mapa ficava em branco); esta versão sempre renderiza.
    const mapChartData = useMemo(() => {
        if (!geojson || !ufDataFilteredByYear.length || !selectedDetailedIndicator || !selectedMunicipalityData) return null;
        const municipalityDataMap = new Map();
        ufDataFilteredByYear.forEach(item => municipalityDataMap.set(String(item.cod_mun_ibge_7), item));
        const locations = [];
        const zValues = [];
        const textValues = [];
        geojson.features.forEach(feature => {
            const geoId = String(feature.properties.id);
            const item = municipalityDataMap.get(geoId);
            const indicatorValue = item ? item[selectedDetailedIndicator] : null;
            if (indicatorValue != null && !isNaN(indicatorValue)) {
                locations.push(geoId);
                zValues.push(indicatorValue);
                const label = INDICADORES_MAP[selectedDetailedIndicator] || selectedDetailedIndicator;
                textValues.push(`${feature.properties.name}<br>${label}: ${indicatorValue.toFixed(2)}`);
            }
        });
        if (locations.length === 0) return null;

        const choroplethTrace = {
            type: 'choropleth', geojson, locations, z: zValues, text: textValues,
            hoverinfo: 'text', featureidkey: 'properties.id', colorscale: 'Viridis',
            marker: { line: { color: 'white', width: 0.5 }, opacity: 0.85 },
            colorbar: { title: { text: INDICADORES_MAP[selectedDetailedIndicator] || selectedDetailedIndicator, side: 'right' } },
            showlegend: false,
        };

        const traces = [choroplethTrace];
        const selectedFeature = geojson.features.find(f => String(f.properties.id) === String(selectedMunicipalityData.cod_mun_ibge_7));
        const centroid = selectedFeature ? getFeatureCentroid(selectedFeature) : null;
        if (centroid) {
            traces.push({
                type: 'scattergeo', lat: [centroid.lat], lon: [centroid.lon], mode: 'markers+text',
                marker: { size: 16, color: '#e11d48' },
                text: [selectedMunicipalityData.nome_mun || selectedMunicipalityData.municipio],
                textposition: 'top center', textfont: { size: 13, color: '#e11d48' },
                hoverinfo: 'text', showlegend: false,
            });
        }
        return traces;
    }, [geojson, ufDataFilteredByYear, selectedDetailedIndicator, selectedMunicipalityData]);

    const historicalChartData = useMemo(() => {
        if (!selectedMunicipalityData || !ufDataAllYears || !selectedDetailedIndicator) return [];
        const munHistory = ufDataAllYears
        .filter(item => String(item.cod_mun_ibge_7) === String(selectedMunicipalityData.cod_mun_ibge_7) && item[selectedDetailedIndicator] != null)
        .sort((a, b) => a.ANO - b.ANO);
        const stateAvgByYear = ufDataAllYears.reduce((acc, item) => {
            if (item.ANO && item[selectedDetailedIndicator] != null) {
                if (!acc[item.ANO]) acc[item.ANO] = { sum: 0, count: 0 };
                acc[item.ANO].sum += item[selectedDetailedIndicator];
                acc[item.ANO].count++;
            }
            return acc;
        }, {});
        const stateHistory = Object.keys(stateAvgByYear).map(year => ({
            ANO: parseInt(year),
                                                                      average: stateAvgByYear[year].sum / stateAvgByYear[year].count
        })).sort((a, b) => a.ANO - b.ANO);
        return [
            {
                x: munHistory.map(d => d.ANO), y: munHistory.map(d => d[selectedDetailedIndicator]),
                                        mode: 'lines+markers', name: selectedMunicipalityData.nome_mun || selectedMunicipalityData.municipio, line: { width: 3 },
            },
            {
                x: stateHistory.map(d => d.ANO), y: stateHistory.map(d => d.average),
                                        mode: 'lines', name: `Média de ${selectedUf}`, line: { dash: 'dot', color: 'gray' },
            }
        ];
    }, [selectedMunicipalityData, ufDataAllYears, selectedDetailedIndicator, selectedUf]);

    const comparativeBarChartData = useMemo(() => {
        if (!selectedMunicipalityData || !ufDataFilteredByYear || !allData || !selectedDetailedIndicator) return null;
        const munValue = selectedMunicipalityData[selectedDetailedIndicator];
        const stateValues = ufDataFilteredByYear.map(item => item[selectedDetailedIndicator]).filter(v => v != null);
        const stateAverage = stateValues.length > 0 ? stateValues.reduce((a, b) => a + b, 0) / stateValues.length : 0;
        const nationalValues = allData.filter(item => item.ANO === selectedYear).map(item => item[selectedDetailedIndicator]).filter(v => v != null);
        const nationalAverage = nationalValues.length > 0 ? nationalValues.reduce((a, b) => a + b, 0) / nationalValues.length : 0;
        return [{
            x: [selectedMunicipalityData.nome_mun || selectedMunicipalityData.municipio, `Média ${selectedUf}`, 'Média de todos os estados selecionados'],
            y: [munValue, stateAverage, nationalAverage],
            type: 'bar',
            text: [munValue?.toFixed(2), stateAverage?.toFixed(2), nationalAverage?.toFixed(2)],
                                            textposition: 'auto',
                                            marker: { color: ['#1f77b4', '#ff7f0e', '#2ca02c'] }
        }];
    }, [selectedMunicipalityData, ufDataFilteredByYear, allData, selectedDetailedIndicator, selectedYear, selectedUf]);

    const radarChartData = useMemo(() => {
        if (!selectedMunicipalityData || !ufDataFilteredByYear) return null;
        const radarIndicators = ['TMI', 'COBERTURA_PRENATAL', 'TAXA_MEDICOS', 'PROP_CESAREOS', 'TAXA_EQUIPES_ESF', 'TAXA_MORT_PREM_DCNT', 'PROP_MAE_ADOL', 'TAXA_INCIDENCIA_TB'].filter(ind => availableIndicators.includes(ind));
        if (radarIndicators.length < 3) return null;
        const municipalityPercentiles = [];
        const stateAveragePercentiles = [];
        radarIndicators.forEach(indicator => {
            const allStateValues = ufDataFilteredByYear.map(item => item[indicator]).filter(v => v != null).sort((a,b) => a-b);
            if (allStateValues.length === 0) {
                municipalityPercentiles.push(0);
                stateAveragePercentiles.push(50);
                return;
            }
            const munValue = selectedMunicipalityData[indicator];
            if (munValue == null) {
                municipalityPercentiles.push(0);
                stateAveragePercentiles.push(50);
                return;
            }
            const rank = allStateValues.findIndex(v => v >= munValue);
            const percentile = (rank / (allStateValues.length -1)) * 100;
            if (INDICADOR_POLARIDADE[indicator] === 'low') {
                municipalityPercentiles.push(100 - percentile);
            } else {
                municipalityPercentiles.push(percentile);
            }
            stateAveragePercentiles.push(50);
        });
        const indicatorLabels = radarIndicators.map(ind => INDICADORES_MAP[ind] || ind);
        return [
            { type: 'scatterpolar', r: [...municipalityPercentiles, municipalityPercentiles[0]], theta: [...indicatorLabels, indicatorLabels[0]], fill: 'toself', name: selectedMunicipalityData.nome_mun || selectedMunicipalityData.municipio, },
            { type: 'scatterpolar', r: [...stateAveragePercentiles, stateAveragePercentiles[0]], theta: [...indicatorLabels, indicatorLabels[0]], fill: 'toself', name: `Média ${selectedUf}`, opacity: 0.3 }
        ];
    }, [selectedMunicipalityData, ufDataFilteredByYear, availableIndicators, selectedUf]);

    const tableDataWithSparklines = useMemo(() => {
        if (!selectedMunicipalityData || !ufDataAllYears) return [];
        return availableIndicators.map(indicator => {
            const history = ufDataAllYears
            .filter(item => String(item.cod_mun_ibge_7) === String(selectedMunicipalityData.cod_mun_ibge_7) && item[indicator] != null)
            .sort((a, b) => a.ANO - b.ANO);
            return {
                indicatorName: INDICADORES_MAP[indicator] || indicator,
                municipalityValue: selectedMunicipalityData[indicator],
                sparklineData: { x: history.map(d => d.ANO), y: history.map(d => d[indicator]) }
            };
        });
    }, [selectedMunicipalityData, ufDataAllYears, availableIndicators]);

    let feedbackMessage = null;
    if (error) feedbackMessage = <p className="text-red-500">{error}</p>;
    else if (loading) feedbackMessage = <p>A carregar dados...</p>;
    else if (availableFiles.length === 0) feedbackMessage = <p>Nenhum ficheiro CSV foi enviado para o seu usuário.</p>;
    else if (allData.length === 0) feedbackMessage = <p>O ficheiro selecionado está vazio ou não contém dados válidos.</p>;
    else if (ufDataFilteredByYear.length === 0) feedbackMessage = <p>Nenhum dado encontrado para a UF e Ano selecionados.</p>;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl text-center text-gray-800 mb-8">Análise por Município</h1>
        <div className="bg-white p-6 rounded-lg shadow-md mb-8 flex flex-wrap gap-4 items-center justify-center">
        <label className="flex flex-col"> Arquivo de Dados:
        <select value={selectedFileId} onChange={(e) => setSelectedFileId(e.target.value)} className="p-2 border rounded-md">
        <option value="">Selecione um arquivo</option>
        {availableFiles.map(file => ( <option key={file.id} value={file.id}> {file.filename} </option>))}
        </select>
        </label>
        <label className="flex flex-col"> Estado (UF):
        <select value={selectedUf} onChange={(e) => setSelectedUf(e.target.value)} className="p-2 border rounded-md">
        {availableUfs.map(ufCode => (<option key={ufCode} value={ufCode}>{ufCode}</option>))}
        </select>
        </label>
        <label className="flex flex-col"> Ano:
        <select value={selectedYear} onChange={(e) => setSelectedYear(parseInt(e.target.value))} className="p-2 border rounded-md">
        {availableYears.map(year => (<option key={year} value={year}>{year}</option>))}
        </select>
        </label>
        </div>

        {feedbackMessage && (<div className="text-center p-4 bg-yellow-100 text-yellow-800 rounded-lg shadow-md mb-8">{feedbackMessage}</div>)}

        {!feedbackMessage && (
            <div className="grid grid-cols-1 gap-6 mt-6">
            <div className="bg-white p-4 rounded-lg shadow-md">
            <label className="flex flex-col font-semibold"> Selecione um Município para Análise:
            <select value={selectedMunicipalityCode} onChange={e => setSelectedMunicipalityCode(e.target.value)} className="p-2 border rounded-md mt-1 font-normal">
            {availableMunicipalities.map(mun => (<option key={mun.cod_mun_ibge_7} value={mun.cod_mun_ibge_7}>{mun.nome_mun}</option>))}
            </select>
            </label>
            </div>

            {selectedMunicipalityData ? (
                <>
                <div className="bg-white p-4 rounded-lg shadow-md">
                <label className="flex flex-col font-semibold"> Selecione um Indicador para Análise Detalhada:
                <select value={selectedDetailedIndicator} onChange={e => setDetailedIndicator(e.target.value)} className="p-2 border rounded-md mt-1 font-normal">
                {availableIndicators.map(ind => <option key={ind} value={ind}>{INDICADORES_MAP[ind] || ind}</option>)}
                </select>
                </label>
                </div>

                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
                <h3 className="font-semibold text-lg">Interpretando o Mapa</h3>
                <p className="text-sm mt-1">O mapa mostra todos os municípios de {selectedUf} coloridos pelo indicador em análise detalhada (selecionado abaixo), com {selectedMunicipalityData.nome_mun || selectedMunicipalityData.municipio} destacado em vermelho — contexto geográfico de onde ele está e como se compara visualmente aos vizinhos.</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md h-[550px] w-full">
                {mapChartData ?
                    <Plot
                    data={mapChartData}
                    layout={{ title: { text: `${INDICADORES_MAP[selectedDetailedIndicator] || selectedDetailedIndicator} em ${selectedUf} (${selectedYear})` }, geo: { scope: 'south america', fitbounds: 'locations', visible: false }, margin: { t: 50, b: 20, l: 20, r: 20 }, autosize: true }}
                    config={{ responsive: true, displayModeBar: true }}
                    className="w-full h-full"
                    />
                    : <p className="flex items-center justify-center h-full text-gray-500">{loadingMap ? 'Carregando mapa...' : 'Nenhum dado para o mapa.'}</p>}
                </div>

                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
                <h3 className="font-semibold text-lg">Interpretando o Raio-X</h3>
                <p className="text-sm mt-1">Esta seção destaca os três melhores e piores desempenhos do município em comparação com a média de todos os municípios do estado no ano selecionado.</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md w-full">
                <h2 className="text-2xl font-semibold text-gray-700 mb-4">Raio-X de {selectedMunicipalityData.nome_mun || selectedMunicipalityData.municipio} ({selectedYear})</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                <h3 className="text-xl font-semibold text-green-700 mb-2">Pontos Fortes</h3>
                {strongPoints.length > 0 ? (<ul className="list-disc list-inside text-gray-700 space-y-1">{strongPoints.map(p => <li key={p.indicator}>{INDICADORES_MAP[p.indicator] || p.indicator}: <span className="font-bold text-green-600">{Math.abs(p.deviation).toFixed(1)}% melhor</span></li>)}</ul>) : <p>Nenhum ponto forte destacado.</p>}
                </div>
                <div>
                <h3 className="text-xl font-semibold text-red-700 mb-2">Pontos de Atenção</h3>
                {weakPoints.length > 0 ? (<ul className="list-disc list-inside text-gray-700 space-y-1">{weakPoints.map(p => <li key={p.indicator}>{INDICADORES_MAP[p.indicator] || p.indicator}: <span className="font-bold text-red-600">{p.deviation.toFixed(1)}% pior</span></li>)}</ul>) : <p>Nenhum ponto de atenção destacado.</p>}
                </div>
                </div>
                </div>

                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
                <h3 className="font-semibold text-lg">Interpretando o Painel Completo de Desvios</h3>
                <p className="text-sm mt-1">Versão completa do Raio-X acima: todos os indicadores disponíveis, não só os 3 melhores/piores, ordenados pela magnitude do desvio em relação à média do estado. Verde indica desempenho favorável, vermelho indica desempenho desfavorável (já considerando se para aquele indicador é melhor ter valor alto ou baixo).</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md w-full" style={{ height: `${Math.max(400, 60 + allPoints.length * 28)}px` }}>
                {deviationChartData ? <Plot data={deviationChartData} layout={{ xaxis: { title: 'Desvio em relação à média do estado (%)' }, yaxis: { automargin: true, autorange: 'reversed' }, margin: { t: 10, b: 40, l: 220, r: 20 }, autosize: true }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p className="flex items-center justify-center h-full text-gray-500">Dados insuficientes.</p>}
                </div>

                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
                <h3 className="font-semibold text-lg">Interpretando o Gráfico Comparativo</h3>
                <p className="text-sm mt-1">Este gráfico compara o valor do indicador selecionado para o município com a média do estado ({selectedUf}) e a média nacional para o mesmo ano.</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
                {comparativeBarChartData ? <Plot data={comparativeBarChartData} layout={{ yaxis: { title: 'Valor' }, autosize: true, margin: { t: 10, b: 40, l: 60, r: 20 } }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p>Selecione um indicador para ver a comparação.</p>}
                </div>

                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
                <h3 className="font-semibold text-lg">Interpretando o Perfil do Município</h3>
                <p className="text-sm mt-1">O gráfico de radar mostra o "perfil" do município. Cada eixo é um indicador, e a linha azul mostra o quão bem o município se classifica (seu percentil) em relação a todos os outros no estado (0 = pior, 100 = melhor). A área laranja representa o desempenho mediano (percentil 50).</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
                {radarChartData ? <Plot data={radarChartData} layout={{ polar: { radialaxis: { visible: true, range: [0, 100] } }, showlegend: true, autosize: true, legend: {orientation: 'h'} }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p className="flex items-center justify-center h-full">Dados insuficientes para gerar o perfil.</p>}
                </div>

                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
                <h3 className="font-semibold text-lg">Interpretando a Posição na Distribuição</h3>
                <p className="text-sm mt-1">O histograma mostra a frequência dos valores do indicador em todos os municípios do estado. A linha vermelha marca a posição exata do município selecionado.</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
                <HistogramaIndicadorEstado data={ufDataFilteredByYear} selectedIndicator={selectedDetailedIndicator} selectedMunicipality={selectedMunicipalityData} selectedYear={selectedYear} ufConfig={ufMapConfig} />
                </div>

                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
                <h3 className="font-semibold text-lg">Interpretando a Série Histórica</h3>
                <p className="text-sm mt-1">Este gráfico mostra a evolução do indicador ao longo dos anos para o município selecionado (linha sólida) em comparação com a tendência da média de todo o estado (linha pontilhada).</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
                <Plot data={historicalChartData} layout={{ title: { text: ``, font: { size: 16 } }, xaxis: { title: 'Ano', type: 'category' }, yaxis: { title: 'Valor' }, autosize: true, margin: { t: 10, b: 40, l: 60, r: 20 }, legend: { orientation: 'h', y: -0.2 } }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" />
                </div>

                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
                <h3 className="font-semibold text-lg">Interpretando o Painel de Indicadores</h3>
                <p className="text-sm mt-1">A tabela abaixo lista o valor de todos os indicadores disponíveis para o município no ano selecionado, junto com um minigráfico (sparkline) que mostra a tendência histórica de cada um.</p>
                </div>
                <div className="bg-white p-4 rounded-lg shadow-md w-full">
                <h2 className="text-2xl font-semibold text-gray-700 mb-2">Painel de Indicadores ({selectedMunicipalityData.nome_mun || selectedMunicipalityData.municipio}, {selectedYear})</h2>
                <div className="overflow-x-auto max-h-96">
                <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0"><tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Indicador</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Valor</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tendência Histórica</th>
                </tr></thead>
                <tbody className="bg-white divide-y divide-gray-200">
                {tableDataWithSparklines.map(row => (
                    <tr key={row.indicatorName}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{row.indicatorName}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.municipalityValue?.toFixed(2) || 'N/A'}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 w-48 h-16">
                    {row.sparklineData.x.length > 1 ? <Plot data={[{ x: row.sparklineData.x, y: row.sparklineData.y, type: 'scatter', mode: 'lines', line:{color: 'rgba(58, 137, 187, 0.7)'} }]} layout={{ autosize: true, margin: { t: 5, b: 5, l: 5, r: 5 }, xaxis: { visible: false }, yaxis: { visible: false } }} config={{ staticPlot: true }} className="w-full h-full" /> : <p className='text-xs'>Dados insuficientes</p>}
                    </td>
                    </tr>
                ))}
                </tbody>
                </table>
                </div>
                </div>
                </>
            ) : (
                <p className="text-center p-4 text-gray-700">Selecione um município para iniciar a análise.</p>
            )}
            </div>
        )}
        </div>
    );
};

export default AnalisePorMunicipioPage;
