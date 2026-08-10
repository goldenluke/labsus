// src/pages/Dashboards/VisaoGeralPage.jsx

import React, { useMemo, useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { useParams } from 'react-router-dom';
import useAnalysisData from '../../hooks/useAnalysisData';
import { INDICADORES_MAP } from '../../config/indicadores';
import { UF_CONFIGS } from '../../config/ufConfigs';
import { UF_TO_REGION_MAP } from '../../config/regioes';
import { INDICADOR_POLARIDADE } from '../../config/polaridadeIndicadores';

// --- Funções Auxiliares para Estatísticas ---
const getPercentile = (data, percentile) => {
    if (!data || data.length === 0) return 0;
    const sorted = [...data].sort((a, b) => a - b);
    const index = (percentile / 100) * (sorted.length - 1);
    if (index % 1 === 0) return sorted[index];
    const lower = Math.floor(index);
    const upper = lower + 1;
    return sorted[lower] + (index - lower) * (sorted[upper] - sorted[lower]);
};

const calculatePearsonCorrelation = (x, y) => {
    let n = x.length;
    if (n === 0) return 0;
    let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
    for (let i = 0; i < n; i++) {
        sumX += x[i];
        sumY += y[i];
        sumXY += x[i] * y[i];
        sumX2 += x[i] * x[i];
        sumY2 += y[i] * y[i];
    }
    const numerator = n * sumXY - sumX * sumY;
    const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
    if (denominator === 0) return 0;
    return numerator / denominator;
};

const interpolateColor = (color1, color2, factor) => {
    let result = color1.slice();
    for (let i = 0; i < 3; i++) {
        result[i] = Math.round(result[i] + factor * (color2[i] - color1[i]));
    }
    return `rgb(${result[0]}, ${result[1]}, ${result[2]})`;
};

const getColorForValue = (value, min, max, polarity) => {
    if (value == null || isNaN(value)) return '#E5E7EB';
    const isLowBetter = polarity === 'low';
    const normalizedValue = max - min === 0 ? 0.5 : (value - min) / (max - min);
    const factor = isLowBetter ? 1 - normalizedValue : normalizedValue;
    const green = [10, 145, 23];
    const yellow = [255, 235, 59];
    const red = [215, 58, 73];
    if (factor < 0.5) {
        return interpolateColor(red, yellow, factor * 2);
    } else {
        return interpolateColor(yellow, green, (factor - 0.5) * 2);
    }
};

const VisaoGeralPage = () => {
    const { uf: ufParam } = useParams();

    const {
        allData, loading: loadingData, error: dataError,
        availableFiles: filesForDropdown, selectedFileId, setSelectedFileId,
        selectedYear, setSelectedYear,
        selectedIndicator, setSelectedIndicator,
        scatterX, setScatterX, scatterY, setScatterY,
        availableYears, availableIndicators,
    } = useAnalysisData('BR', 2022, 'TMI', ufParam, { fetchFileList: true });

    const [statesGeojson, setStatesGeojson] = useState(null);
    const [loadingMap, setLoadingMap] = useState(true);
    const [mapError, setMapError] = useState(null);

    useEffect(() => {
        const fetchStatesGeojson = async () => {
            setLoadingMap(true);
            setMapError(null);
            try {
                const response = await fetch('/geojson/br_states.json');
                if (!response.ok) throw new Error(`Arquivo não encontrado`);
                const jsonData = await response.json();
                setStatesGeojson(jsonData);
            } catch (err) { setMapError(err.message); }
            finally { setLoadingMap(false); }
        };
        fetchStatesGeojson();
    }, []);

    const mapBrazilChartData = useMemo(() => {
        if (!statesGeojson || !allData || allData.length === 0 || !selectedIndicator || !selectedYear) return null;
        const dataForSelectedYear = allData.filter(item => item.ANO === selectedYear);
        if (dataForSelectedYear.length === 0) return null;
        const stateAverages = dataForSelectedYear.reduce((acc, item) => {
            if (item.UF && item[selectedIndicator] != null && !isNaN(item[selectedIndicator])) {
                if (!acc[item.UF]) { acc[item.UF] = { sum: 0, count: 0 }; }
                acc[item.UF].sum += item[selectedIndicator];
                acc[item.UF].count += 1;
            }
            return acc;
        }, {});
        const avgByState = Object.keys(stateAverages).map(uf => ({
            uf: uf,
            average: stateAverages[uf].sum / stateAverages[uf].count,
        }));
        if (avgByState.length === 0) return null;
        return [{
            // choroplethmapbox (não choropleth/scattergeo) desenha os estados
            // sobre tiles reais do OpenStreetMap em vez de um fundo em branco
            // (geo: {visible: false}) — mesma melhoria já aplicada aos mapas
            // de fluxo, bem mais legível como referência geográfica.
            type: 'choroplethmapbox',
            geojson: statesGeojson,
            locations: avgByState.map(s => s.uf),
                                       z: avgByState.map(s => s.average),
                                       featureidkey: 'id',
                                       text: avgByState.map(s => UF_CONFIGS[s.uf]?.nome || s.uf),
                                       hoverinfo: 'text+z',
                                       colorscale: 'Viridis',
                                       marker: { line: { color: 'white', width: 1 }, opacity: 0.75 },
                                       colorbar: { title: { text: INDICADORES_MAP[selectedIndicator] || selectedIndicator, side: 'right' } },
        }];
    }, [statesGeojson, allData, selectedIndicator, selectedYear]);

    const mapBrazilTitle = useMemo(() => `Média de ${INDICADORES_MAP[selectedIndicator] || selectedIndicator} por Estado (${selectedYear})`, [selectedIndicator, selectedYear]);

    // Resize de janela único, disparado pouco depois dos dados do mapa
    // ficarem prontos — corrige o mapbox-gl inicializando com tamanho errado
    // logo após uma navegação interna do SPA (ver mesma nota em
    // AnalisePorMunicipioPage.jsx). Evita usar useResizeHandler contínuo,
    // que pode disparar no meio da troca de instância do mapa causada pela
    // `key` e corromper o mapbox-gl.
    useEffect(() => {
        if (!mapBrazilChartData) return;
        const timer = setTimeout(() => window.dispatchEvent(new Event('resize')), 200);
        return () => clearTimeout(timer);
    }, [mapBrazilChartData]);

    const rankingStatesChartData = useMemo(() => {
        if (!allData || allData.length === 0 || !selectedIndicator || !selectedYear) return [];
        const dataForSelectedYear = allData.filter(item => item.ANO === selectedYear);
        if (dataForSelectedYear.length === 0) return [];
        const stateAverages = dataForSelectedYear.reduce((acc, item) => {
            if (item.UF && item[selectedIndicator] != null && !isNaN(item[selectedIndicator])) {
                if (!acc[item.UF]) { acc[item.UF] = { sum: 0, count: 0 }; }
                acc[item.UF].sum += item[selectedIndicator];
                acc[item.UF].count += 1;
            }
            return acc;
        }, {});
        const avgByState = Object.keys(stateAverages).map(uf => ({
            uf: uf,
            average: stateAverages[uf].sum / stateAverages[uf].count,
            nome: UF_CONFIGS[uf]?.nome || uf
        }));
        const sortedStates = avgByState.filter(s => s.average !== null && !isNaN(s.average))
        .sort((a, b) => b.average - a.average)
        .slice(0, 15);
        if (sortedStates.length === 0) return [];
        const states = sortedStates.map(s => s.nome).reverse();
        const averages = sortedStates.map(s => s.average).reverse();
        return [{
            x: averages, y: states, type: 'bar', orientation: 'h', marker: { color: 'rgba(58, 137, 187, 0.7)' }, hovertemplate: `Estado: %{y}<br>Média: %{x:.2f}<extra></extra>`,
        }];
    }, [allData, selectedIndicator, selectedYear]);

    const rankingStatesTitle = useMemo(() => `Ranking de Estados por Média de ${INDICADORES_MAP[selectedIndicator] || selectedIndicator} (${selectedYear})`, [selectedIndicator, selectedYear]);

    const historicalWithRangeData = useMemo(() => {
        if (!allData.length || !selectedIndicator) return null;
        const yearlyStats = {};
        allData.forEach(item => {
            if (item.ANO && item[selectedIndicator] != null) {
                if (!yearlyStats[item.ANO]) yearlyStats[item.ANO] = [];
                yearlyStats[item.ANO].push(item[selectedIndicator]);
            }
        });
        const years = Object.keys(yearlyStats).sort((a,b) => a - b);
        const nationalAverage = years.map(year => yearlyStats[year].reduce((a, b) => a + b, 0) / yearlyStats[year].length);
        const q1Values = years.map(year => getPercentile(yearlyStats[year], 25));
        const q3Values = years.map(year => getPercentile(yearlyStats[year], 75));
        return [
            { x: [...years, ...years.slice().reverse()], y: [...q3Values, ...q1Values.slice().reverse()], fill: 'toself', fillcolor: 'rgba(0,100,80,0.2)', line: { color: 'transparent' }, hoverinfo: 'skip', showlegend: false, name: 'Intervalo Interquartil' },
                                            { x: years, y: nationalAverage, type: 'scatter', mode: 'lines', line: { color: 'rgba(0,100,80,1)' }, name: 'Média (Todos os Estados)' }
        ];
    }, [allData, selectedIndicator]);

    const regionAnalysisData = useMemo(() => {
        if (!allData.length || !selectedIndicator || !selectedYear) return null;
        const dataForYear = allData.filter(item => item.ANO === selectedYear && item[selectedIndicator] != null);
        const dataWithRegion = dataForYear.map(item => ({ ...item, regiao: UF_TO_REGION_MAP[item.UF] })).filter(item => item.regiao);
        const regions = ['Norte', 'Nordeste', 'Centro-Oeste', 'Sudeste', 'Sul'];
        // Só inclui regiões com pelo menos um valor — o dataset carregado pode
        // conter só um punhado de UFs (ex.: uma única análise estadual), então
        // a maioria das regiões ficaria com uma caixa vazia sem esse filtro.
        const traces = regions
            .map(region => ({ y: dataWithRegion.filter(item => item.regiao === region).map(item => item[selectedIndicator]), type: 'box', name: region, boxpoints: 'all' }))
            .filter(trace => trace.y.length > 0);
        return traces.length > 0 ? traces : null;
    }, [allData, selectedIndicator, selectedYear]);

    // Matriz de correlação de Pearson entre TODOS os indicadores disponíveis
    // no arquivo carregado (não só o par X/Y do dispersão abaixo) — usa
    // calculatePearsonCorrelation, já definida no topo do arquivo.
    const correlationMatrixData = useMemo(() => {
        if (!allData.length || !selectedYear || availableIndicators.length < 2) return null;
        const dataForYear = allData.filter(item => item.ANO === selectedYear);
        const z = availableIndicators.map(indA => availableIndicators.map(indB => {
            const pares = dataForYear.filter(d => d[indA] != null && !isNaN(d[indA]) && d[indB] != null && !isNaN(d[indB]));
            if (pares.length < 3) return null;
            return calculatePearsonCorrelation(pares.map(d => d[indA]), pares.map(d => d[indB]));
        }));
        const labels = availableIndicators.map(k => INDICADORES_MAP[k] || k);
        const text = z.map(row => row.map(v => (v == null ? '' : v.toFixed(2))));
        return { z, labels, text };
    }, [allData, selectedYear, availableIndicators]);

    // Distribuição nacional (histograma) do indicador principal — complementa
    // o ranking e o box plot por região mostrando a forma completa da
    // distribuição (assimetria, caudas, concentração) em vez de só um resumo.
    const nationalHistogramData = useMemo(() => {
        if (!allData.length || !selectedIndicator || !selectedYear) return null;
        const valores = allData
            .filter(item => item.ANO === selectedYear && item[selectedIndicator] != null && !isNaN(item[selectedIndicator]))
            .map(item => item[selectedIndicator]);
        if (valores.length === 0) return null;
        return [{ x: valores, type: 'histogram', nbinsx: 30, marker: { color: 'rgba(58, 137, 187, 0.7)', line: { color: 'rgba(58, 137, 187, 1)', width: 1 } } }];
    }, [allData, selectedIndicator, selectedYear]);

    // Ranking NACIONAL por MUNICÍPIO (não por estado) — mesmo padrão do
    // ranking de estados, um nível mais granular: os 15 municípios com maior
    // e os 15 com menor valor do indicador principal, em todo o país.
    const municipalityRankingData = useMemo(() => {
        if (!allData.length || !selectedIndicator || !selectedYear) return null;
        const dataForYear = allData.filter(item => item.ANO === selectedYear && item[selectedIndicator] != null && !isNaN(item[selectedIndicator]));
        if (dataForYear.length === 0) return null;
        const ordenado = [...dataForYear].sort((a, b) => b[selectedIndicator] - a[selectedIndicator]);
        const rotulo = (item) => `${item.municipio || item.nome_mun || '—'} (${item.UF})`;
        const construirTrace = (linhas, cor) => [{
            x: linhas.map(i => i[selectedIndicator]).reverse(),
            y: linhas.map(rotulo).reverse(),
            type: 'bar', orientation: 'h', marker: { color: cor },
            hovertemplate: `%{y}<br>Valor: %{x:.2f}<extra></extra>`,
        }];
        return {
            maiores: construirTrace(ordenado.slice(0, 15), 'rgba(10,145,23,0.7)'),
            menores: construirTrace(ordenado.slice(-15).reverse(), 'rgba(215,58,73,0.7)'),
        };
    }, [allData, selectedIndicator, selectedYear]);

    const heatmapTableData = useMemo(() => {
        if (!allData.length || !selectedYear || availableIndicators.length < 2) return null;
        const dataForYear = allData.filter(item => item.ANO === selectedYear);
        const stateAverages = {};
        dataForYear.forEach(item => {
            if (!item.UF) return;
            if (!stateAverages[item.UF]) {
                stateAverages[item.UF] = { counts: {}, sums: {} };
            }
            availableIndicators.forEach(ind => {
                if (item[ind] != null && !isNaN(item[ind])) {
                    if (!stateAverages[item.UF].sums[ind]) {
                        stateAverages[item.UF].sums[ind] = 0;
                        stateAverages[item.UF].counts[ind] = 0;
                    }
                    stateAverages[item.UF].sums[ind] += item[ind];
                    stateAverages[item.UF].counts[ind]++;
                }
            });
        });
        const indicatorBounds = {};
        availableIndicators.forEach(ind => {
            const values = Object.keys(stateAverages).map(uf => {
                if (stateAverages[uf].counts[ind]) {
                    return stateAverages[uf].sums[ind] / stateAverages[uf].counts[ind];
                }
                return null;
            }).filter(v => v != null);
            if (values.length > 0) {
                indicatorBounds[ind] = { min: Math.min(...values), max: Math.max(...values) };
            }
        });
        const tableRows = Object.keys(stateAverages).map(uf => {
            const row = {
                uf: uf,
                ufName: UF_CONFIGS[uf]?.nome || uf,
                indicators: {}
            };
            availableIndicators.forEach(ind => {
                const avg = stateAverages[uf].counts[ind] ? stateAverages[uf].sums[ind] / stateAverages[uf].counts[ind] : null;
                const bounds = indicatorBounds[ind];
                row.indicators[ind] = {
                    value: avg,
                    color: bounds ? getColorForValue(avg, bounds.min, bounds.max, INDICADOR_POLARIDADE[ind]) : '#E5E7EB',
                };
            });
            return row;
        }).sort((a, b) => a.ufName.localeCompare(b.ufName));
        return tableRows;
    }, [allData, selectedYear, availableIndicators]);

    const nationalScatterChartData = useMemo(() => {
        if (!allData || allData.length === 0 || !scatterX || !scatterY || !selectedYear) return [];
        const dataForSelectedYear = allData.filter(item => item.ANO === selectedYear);
        if (dataForSelectedYear.length === 0) return [];
        const validData = dataForSelectedYear.filter(item => item[scatterX] != null && !isNaN(item[scatterX]) && item[scatterY] != null && !isNaN(item[scatterY]));
        if (validData.length === 0) return [];
        return [{
            x: validData.map(item => item[scatterX]),
                                             y: validData.map(item => item[scatterY]),
                                             mode: 'markers', type: 'scatter', name: 'Municípios',
                                             text: validData.map(item => `${item.nome_mun || item.municipio}<br>UF: ${item.UF}`),
                                             hoverinfo: 'text', marker: { size: 8, opacity: 0.7 },
        }];
    }, [allData, scatterX, scatterY, selectedYear]);

    const nationalScatterTitle = useMemo(() => {
        const xLabel = INDICADORES_MAP[scatterX] || scatterX;
        const yLabel = INDICADORES_MAP[scatterY] || scatterY;
        return `Correlação entre ${xLabel} e ${yLabel} (${selectedYear})`;
    }, [scatterX, scatterY, selectedYear]);

    const loading = loadingData || loadingMap;
    const error = dataError || mapError;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl text-center text-gray-800 mb-8">Visão Geral (Todos os estados selecionados)</h1>
        <div className="bg-white p-6 rounded-lg shadow-md mb-8 flex flex-wrap gap-4 items-center justify-center">
        <label className="flex flex-col">Arquivo de Dados: <select value={selectedFileId} onChange={(e) => setSelectedFileId(e.target.value)} className="p-2 border rounded-md">{filesForDropdown.map(file => (<option key={file.id} value={file.id}>{file.filename}</option>))}</select></label>
        <label className="flex flex-col">Ano: <select value={selectedYear} onChange={(e) => setSelectedYear(parseInt(e.target.value))} className="p-2 border rounded-md">{availableYears.map(year => (<option key={year} value={year}>{year}</option>))} </select></label>
        <label className="flex flex-col">Indicador Principal: <select value={selectedIndicator} onChange={(e) => setSelectedIndicator(e.target.value)} className="p-2 border rounded-md">{availableIndicators.map(k => (<option key={k} value={k}>{INDICADORES_MAP[k] || k}</option>))}</select></label>
        </div>

        {error && <p className="text-red-500 text-center p-4">{error}</p>}
        {loading && <p className="text-center p-4">Carregando dados...</p>}

        {!loading && !error && (
            <div className="grid grid-cols-1 gap-8 mt-6">
            <div className="bg-white p-4 rounded-lg shadow-md h-[600px] w-full">
            {mapBrazilChartData ? <Plot key={selectedFileId} data={mapBrazilChartData} layout={{ title: { text: mapBrazilTitle }, mapbox: { style: 'open-street-map', center: { lat: -14.2, lon: -51.9 }, zoom: 2.8 }, margin: { t: 50, b: 20, l: 20, r: 20 }, autosize: true, }} config={{ responsive: true, displayModeBar: true }} className="w-full h-full" /> : <p className="flex items-center justify-center h-full">Nenhum dado para o mapa.</p>}
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando a Matriz de Desempenho</h3>
            <p className="text-sm mt-1">A tabela compara todos os estados em todos os indicadores. As células são coloridas de verde (melhor desempenho) a vermelho (pior desempenho) em relação aos outros estados para aquele indicador específico.</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md w-full">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">Matriz de Desempenho Estadual ({selectedYear})</h2>
            {heatmapTableData ? (
                <div className="overflow-auto max-h-[600px]">
                <table className="min-w-full text-sm border-collapse">
                <thead className="bg-gray-100 sticky top-0">
                <tr>
                <th className="border p-1 font-semibold text-left">Estado</th>
                {availableIndicators.map(ind => <th key={ind} className="border p-1 font-semibold">{INDICADORES_MAP[ind] || ind}</th>)}
                </tr>
                </thead>
                <tbody>
                {heatmapTableData.map(row => (
                    <tr key={row.uf}>
                    <td className="border p-1 font-medium">{row.ufName}</td>
                    {availableIndicators.map(ind => (
                        <td key={ind} className="border p-1 text-center" style={{ backgroundColor: row.indicators[ind].color, color: '#111' }}>
                        {row.indicators[ind].value?.toFixed(2) || 'N/A'}
                        </td>
                    ))}
                    </tr>
                ))}
                </tbody>
                </table>
                </div>
            ) : <p>Dados insuficientes para a matriz de desempenho.</p>}
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando o Ranking de Estados</h3>
            <p className="text-sm mt-1">O gráfico exibe os 15 estados com a maior média para o indicador selecionado, permitindo uma rápida identificação de destaques nacionais.</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[650px] w-full">
            {rankingStatesChartData.length > 0 ? (
                <Plot data={rankingStatesChartData} layout={{ title: { text: rankingStatesTitle }, xaxis: { title: INDICADORES_MAP[selectedIndicator] || selectedIndicator }, yaxis: { title: 'Estado', automargin: true }, margin: { t: 60, b: 40, l: 150, r: 20 }, autosize: true }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" />
            ) : (<p className="text-center text-gray-500 flex items-center justify-center h-full">Dados insuficientes para o ranking.</p>)}
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando a Série Histórica</h3>
            <p className="text-sm mt-1">A linha representa a média do indicador de todos os estados ao longo dos anos. A área sombreada representa a variação de desempenho entre os estados (do 25º ao 75º percentil). Uma faixa mais estreita indica menor desigualdade regional.</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            {historicalWithRangeData ? <Plot data={historicalWithRangeData} layout={{ title: `Evolução de ${INDICADORES_MAP[selectedIndicator] || selectedIndicator}`, yaxis: { title: 'Valor' } }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p>Dados insuficientes.</p>}
            </div>
            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando a Análise por Região</h3>
            <p className="text-sm mt-1">O box plot compara a distribuição dos valores do indicador entre as grandes regiões do Brasil presentes no arquivo carregado. Ele destaca medianas (linha central), quartis e outliers (pontos), revelando disparidades regionais.</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            {regionAnalysisData ? <Plot data={regionAnalysisData} layout={{ title: `Distribuição de ${INDICADORES_MAP[selectedIndicator] || selectedIndicator} por Região`, yaxis: { title: 'Valor' }, showlegend: false }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p className="flex items-center justify-center h-full text-gray-500">O arquivo carregado não cobre UFs suficientes para uma análise por região.</p>}
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando a Distribuição Nacional</h3>
            <p className="text-sm mt-1">O histograma mostra quantos municípios caem em cada faixa de valor do indicador principal — revela a forma da distribuição (concentrada, espalhada, com cauda longa) que médias e medianas sozinhas escondem.</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[450px] w-full">
            {nationalHistogramData ? <Plot data={nationalHistogramData} layout={{ title: `Distribuição de ${INDICADORES_MAP[selectedIndicator] || selectedIndicator} entre Municípios (${selectedYear})`, xaxis: { title: INDICADORES_MAP[selectedIndicator] || selectedIndicator }, yaxis: { title: 'Nº de Municípios' }, bargap: 0.05 }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p className="flex items-center justify-center h-full text-gray-500">Dados insuficientes.</p>}
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando o Ranking de Municípios</h3>
            <p className="text-sm mt-1">Mesma ideia do ranking de estados, um nível mais granular: os 15 municípios com maior e os 15 com menor valor do indicador principal, em todo o território coberto pelo arquivo carregado.</p>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="bg-white p-4 rounded-lg shadow-md h-[550px] w-full">
            <h2 className="text-lg font-semibold text-gray-700 mb-2 text-center">15 Maiores Valores</h2>
            {municipalityRankingData ? <Plot data={municipalityRankingData.maiores} layout={{ xaxis: { title: INDICADORES_MAP[selectedIndicator] || selectedIndicator }, yaxis: { automargin: true }, margin: { t: 10, b: 40, l: 150, r: 20 } }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p className="flex items-center justify-center h-full text-gray-500">Dados insuficientes.</p>}
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[550px] w-full">
            <h2 className="text-lg font-semibold text-gray-700 mb-2 text-center">15 Menores Valores</h2>
            {municipalityRankingData ? <Plot data={municipalityRankingData.menores} layout={{ xaxis: { title: INDICADORES_MAP[selectedIndicator] || selectedIndicator }, yaxis: { automargin: true }, margin: { t: 10, b: 40, l: 150, r: 20 } }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p className="flex items-center justify-center h-full text-gray-500">Dados insuficientes.</p>}
            </div>
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando a Correlação</h3>
            <p className="text-sm mt-1">O gráfico de dispersão plota um indicador contra o outro para cada município do país. Ele ajuda a identificar se existe uma relação entre eles (ex: à medida que um sobe, o outro também sobe ou desce).</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[650px] w-full">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4 text-center">Correlação entre Indicadores</h2>
            <div className="flex flex-wrap gap-4 items-center justify-center mb-4">
            <label className="flex flex-col">Eixo X: <select value={scatterX} onChange={(e) => setScatterX(e.target.value)} className="p-2 border rounded-md">{availableIndicators.map(k => (<option key={k} value={k}>{INDICADORES_MAP[k] || k}</option>))}</select></label>
            <label className="flex flex-col">Eixo Y: <select value={scatterY} onChange={(e) => setScatterY(e.target.value)} className="p-2 border rounded-md">{availableIndicators.map(k => (<option key={k} value={k}>{INDICADORES_MAP[k] || k}</option>))}</select></label>
            </div>
            {nationalScatterChartData.length > 0 ? (
                <Plot data={nationalScatterChartData} layout={{ title: { text: nationalScatterTitle }, xaxis: { title: INDICADORES_MAP[scatterX] || scatterX }, yaxis: { title: INDICADORES_MAP[scatterY] || scatterY }, hovermode: 'closest', autosize: true, margin: { t: 60, b: 40, l: 60, r: 20 } }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" />
            ) : (<p className="text-center text-gray-500 flex items-center justify-center h-full">Dados insuficientes para o gráfico de dispersão.</p>)}
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando a Matriz de Correlação</h3>
            <p className="text-sm mt-1">Cada célula mostra a correlação de Pearson (-1 a 1) entre dois indicadores, considerando todos os municípios do arquivo carregado. Vermelho = correlação negativa (um sobe, o outro desce); azul = positiva (sobem/descem juntos); próximo de zero (branco) = sem relação linear aparente. A diagonal é sempre 1 (cada indicador correlacionado consigo mesmo).</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md w-full" style={{ height: `${Math.max(450, 80 + availableIndicators.length * 32)}px` }}>
            <h2 className="text-2xl font-semibold text-gray-700 mb-4 text-center">Matriz de Correlação entre Indicadores ({selectedYear})</h2>
            {correlationMatrixData ? (
                <Plot
                data={[{
                    type: 'heatmap', z: correlationMatrixData.z, x: correlationMatrixData.labels, y: correlationMatrixData.labels,
                    text: correlationMatrixData.text, texttemplate: '%{text}', textfont: { size: 10 },
                    zmin: -1, zmax: 1, colorscale: 'RdBu', reversescale: true, hoverongaps: false,
                    hovertemplate: '%{y} × %{x}<br>r = %{z:.2f}<extra></extra>',
                }]}
                layout={{ xaxis: { tickangle: -45, automargin: true }, yaxis: { automargin: true }, margin: { t: 10, b: 10, l: 10, r: 10 } }}
                config={{ responsive: true, displayModeBar: false }}
                className="w-full h-[calc(100%-3rem)]"
                />
            ) : (<p className="text-center text-gray-500 flex items-center justify-center h-full">São necessários pelo menos dois indicadores numéricos para a matriz de correlação.</p>)}
            </div>
            </div>
        )}
        </div>
    );
};

export default VisaoGeralPage;
