// src/pages/Dashboards/AnalisePorEstadoPage.jsx

import React, { useState, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import Plot from 'react-plotly.js';

import useAnalysisData from '../../hooks/useAnalysisData';

import HistogramaIndicadorEstado from '../../components/charts/HistogramaIndicadorEstado';
import RankingMunicipiosEstado from '../../components/charts/RankingMunicipiosEstado';
import HistoricoIndicadorEstado from '../../components/charts/HistoricoIndicadorEstado';
import GraficoDispersaoEstado from '../../components/charts/GraficoDispersaoEstado';

import { INDICADORES_MAP } from '../../config/indicadores';
import { UF_CONFIGS } from '../../config/ufConfigs';


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

const AnalisePorEstadoPage = () => {
    const { uf: ufParam } = useParams();

    const {
        allData, loading, error,
        availableFiles, selectedFileId, setSelectedFileId,
        selectedUf, setSelectedUf, selectedYear, setSelectedYear,
        selectedIndicator, setSelectedIndicator,
        rankingType, setRankingType, scatterX, setScatterX, scatterY, setScatterY,
        selectedMunicipality, setSelectedMunicipality,
        availableUfs, availableYears, availableIndicators,
        ufDataFilteredByYear, ufDataAllYears,
        ufMapConfig, geojson, loadingMap,
        mapChartData, mapTitle,
        municipalitiesForHistoricalComparison,
    } = useAnalysisData('GO', 2022, 'TMI', ufParam, { fetchFileList: true });

    const [slopeStartYear, setSlopeStartYear] = useState(null);
    const [slopeEndYear, setSlopeEndYear] = useState(null);

    useEffect(() => {
        if (availableYears.length > 1) {
            setSlopeStartYear(availableYears[availableYears.length - 1]);
            setSlopeEndYear(availableYears[0]);
        } else if (availableYears.length === 1) {
            setSlopeStartYear(availableYears[0]);
            setSlopeEndYear(availableYears[0]);
        }
    }, [availableYears]);

    const violinChartData = useMemo(() => {
        if (!ufDataFilteredByYear.length || !allData.length || !selectedIndicator || !selectedYear) return null;
        const stateValues = ufDataFilteredByYear.map(item => item[selectedIndicator]).filter(v => v != null);
        const nationalValues = allData.filter(item => item.ANO === selectedYear).map(item => item[selectedIndicator]).filter(v => v != null);
        if (stateValues.length === 0 || nationalValues.length === 0) return null;
        return [
            { y: stateValues, type: 'violin', name: ufMapConfig?.nome || selectedUf, box: { visible: true }, meanline: { visible: true } },
            { y: nationalValues, type: 'violin', name: 'Todos os estados selecionados', box: { visible: true }, meanline: { visible: true } },
        ];
    }, [ufDataFilteredByYear, allData, selectedIndicator, selectedYear, selectedUf, ufMapConfig]);

    // choroplethmapbox (não choropleth/geo) desenha os municípios sobre tiles
    // reais do OpenStreetMap em vez de um fundo em branco — mesma melhoria já
    // aplicada aos outros mapas do sistema. A geometria/valores continuam
    // vindos do useAnalysisData (mapChartData); só o tipo do trace muda.
    const mapChartDataMapbox = useMemo(() => {
        if (!mapChartData) return null;
        return mapChartData.map(trace => ({ ...trace, type: 'choroplethmapbox' }));
    }, [mapChartData]);

    // Resize de janela único, disparado pouco depois dos dados do mapa
    // ficarem prontos — corrige o mapbox-gl inicializando com tamanho errado
    // logo após uma navegação interna do SPA (ver mesma nota em
    // AnalisePorMunicipioPage.jsx).
    useEffect(() => {
        if (!mapChartDataMapbox) return;
        const timer = setTimeout(() => window.dispatchEvent(new Event('resize')), 200);
        return () => clearTimeout(timer);
    }, [mapChartDataMapbox]);

    // Complementa a "Série Histórica" (que só mostra a média): um box plot por
    // ano revela a dispersão e os outliers por trás dessa média ao longo do tempo.
    const yearlyDistributionData = useMemo(() => {
        if (!ufDataAllYears.length || !selectedIndicator) return null;
        const years = [...new Set(ufDataAllYears.map(d => d.ANO))].filter(y => y != null).sort((a, b) => a - b);
        const traces = years
            .map(year => ({
                y: ufDataAllYears.filter(d => d.ANO === year && d[selectedIndicator] != null && !isNaN(d[selectedIndicator])).map(d => d[selectedIndicator]),
                type: 'box',
                name: String(year),
                boxpoints: 'outliers',
                marker: { color: 'rgba(58, 137, 187, 0.7)' },
            }))
            .filter(trace => trace.y.length > 0);
        return traces.length > 0 ? traces : null;
    }, [ufDataAllYears, selectedIndicator]);

    // Matriz de correlação de Pearson entre todos os indicadores disponíveis,
    // calculada só com os municípios do estado selecionado (não o país todo).
    const correlationMatrixData = useMemo(() => {
        if (!ufDataFilteredByYear.length || availableIndicators.length < 2) return null;
        const z = availableIndicators.map(indA => availableIndicators.map(indB => {
            const pares = ufDataFilteredByYear.filter(d => d[indA] != null && !isNaN(d[indA]) && d[indB] != null && !isNaN(d[indB]));
            if (pares.length < 3) return null;
            return calculatePearsonCorrelation(pares.map(d => d[indA]), pares.map(d => d[indB]));
        }));
        const labels = availableIndicators.map(k => INDICADORES_MAP[k] || k);
        const text = z.map(row => row.map(v => (v == null ? '' : v.toFixed(2))));
        return { z, labels, text };
    }, [ufDataFilteredByYear, availableIndicators]);

    const slopeChartData = useMemo(() => {
        if (!slopeStartYear || !slopeEndYear || slopeStartYear >= slopeEndYear || !ufDataAllYears.length || !selectedIndicator) return [];
        const startData = new Map(ufDataAllYears.filter(d => d.ANO === slopeStartYear).map(d => [d.cod_mun_ibge_7, d]));
        const endData = new Map(ufDataAllYears.filter(d => d.ANO === slopeEndYear).map(d => [d.cod_mun_ibge_7, d]));
        const changes = [];
        startData.forEach((startItem, munCode) => {
            const endItem = endData.get(munCode);
            if (endItem && startItem[selectedIndicator] != null && endItem[selectedIndicator] != null) {
                changes.push({
                    name: startItem.nome_mun || startItem.municipio,
                    start: startItem[selectedIndicator],
                    end: endItem[selectedIndicator],
                    change: endItem[selectedIndicator] - startItem[selectedIndicator],
                });
            }
        });
        if (changes.length === 0) return [];
        changes.sort((a,b) => Math.abs(b.change) - Math.abs(a.change));
        const topChanges = changes.slice(0, 10);
        const traces = [];
        topChanges.forEach(item => {
            traces.push({
                type: 'scatter',
                x: [slopeStartYear, slopeEndYear],
                y: [item.start, item.end],
                mode: 'lines+markers',
                name: item.name,
                text: `${item.name}<br>Variação: ${item.change.toFixed(2)}`,
                        hoverinfo: 'text',
                        line: { color: item.change > 0 ? 'green' : 'red', width: 2 },
                        marker: { size: 8 }
            });
        });
        return traces;
    }, [ufDataAllYears, selectedIndicator, slopeStartYear, slopeEndYear]);

    let feedbackMessage = null;
    if (error) feedbackMessage = <p className="text-red-500">Erro: {error}</p>;
    else if (loading) feedbackMessage = <p>A carregar dados...</p>;
    else if (!selectedFileId) feedbackMessage = <p>Por favor, selecione um ficheiro de dados.</p>;
    else if (allData.length === 0) feedbackMessage = <p>O ficheiro selecionado está vazio ou não contém dados válidos.</p>;
    else if (ufDataFilteredByYear.length === 0) feedbackMessage = <p>Nenhum dado encontrado para a UF e Ano selecionados.</p>;

    const controls = (
        <>
        <label className="flex flex-col"> Arquivo de Dados:
        <select value={selectedFileId} onChange={(e) => setSelectedFileId(e.target.value)} className="p-2 border rounded-md" >
        <option value="">Selecione um arquivo</option>
        {Array.isArray(availableFiles) && availableFiles.map(file => (<option key={file.id} value={file.id}>{file.filename} (Upload: {new Date(file.uploaded_at).toLocaleDateString()})</option>))}
        </select>
        </label>
        <label className="flex flex-col"> Estado (UF):
        <select value={selectedUf} onChange={(e) => setSelectedUf(e.target.value)} className="p-2 border rounded-md" >
        {availableUfs.map(ufCode => (<option key={ufCode} value={ufCode}>{ufCode}</option>))}
        </select>
        </label>
        <label className="flex flex-col"> Ano:
        <select value={selectedYear} onChange={(e) => setSelectedYear(parseInt(e.target.value))} className="p-2 border rounded-md" >
        {availableYears.map(year => (<option key={year} value={year}>{year}</option>))}
        </select>
        </label>
        <label className="flex flex-col"> Indicador:
        <select value={selectedIndicator} onChange={(e) => setSelectedIndicator(e.target.value)} className="p-2 border rounded-md" >
        {availableIndicators.map(indicatorKey => (<option key={indicatorKey} value={indicatorKey}>{INDICADORES_MAP[indicatorKey] || indicatorKey}</option>))}
        </select>
        </label>
        </>
    );

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl text-center text-gray-800 mb-8">Análise por Estado</h1>
        <div className="bg-white p-6 rounded-lg shadow-md mb-8 flex flex-wrap gap-4 items-center justify-center">{controls}</div>
        {feedbackMessage && (<div className="text-center p-4 bg-yellow-100 text-yellow-800 rounded-lg shadow-md mb-8">{feedbackMessage}</div>)}

        {!feedbackMessage && (
            <div className="grid grid-cols-1 gap-6 mt-6">
            <div className="bg-white p-4 rounded-lg shadow-md h-[600px] w-full">
            {mapChartDataMapbox ?
                <Plot
                key={`${selectedFileId}-${selectedUf}`}
                data={mapChartDataMapbox}
                layout={{ title: { text: mapTitle }, mapbox: { style: 'open-street-map', center: ufMapConfig.center || { lat: -14.2, lon: -51.9 }, zoom: ufMapConfig.zoom || 4 }, margin: { t: 50, b: 20, l: 20, r: 20 }, autosize: true }}
                config={{ responsive: true, displayModeBar: true }}
                className="w-full h-full"
                />
                : <p className="flex items-center justify-center h-full text-gray-500">{loadingMap ? 'Carregando mapa...' : 'Nenhum dado para o mapa.'}</p>}
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando o Histograma</h3>
            <p className="text-sm mt-1">Este gráfico mostra a frequência dos valores do indicador em todos os municípios do estado. Ele ajuda a entender se os valores são concentrados ou espalhados e a identificar padrões na distribuição.</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            <HistogramaIndicadorEstado data={ufDataFilteredByYear} selectedIndicator={selectedIndicator} selectedMunicipality={selectedMunicipality} selectedYear={selectedYear} ufConfig={ufMapConfig} />
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando o Ranking de Municípios</h3>
            <p className="text-sm mt-1">O ranking exibe os 15 municípios com os maiores ('Piores') ou menores ('Melhores') valores para o indicador selecionado, permitindo identificar rapidamente os destaques e os pontos de maior atenção no estado.</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[650px] w-full">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">Ranking de Municípios</h2>
            <div className="flex justify-center mb-4">
            <label className="mr-4"><input type="radio" value="piores" checked={rankingType === 'piores'} onChange={() => setRankingType('piores')} className="mr-2"/> Piores</label>
            <label><input type="radio" value="melhores" checked={rankingType === 'melhores'} onChange={() => setRankingType('melhores')} className="mr-2"/> Melhores</label>
            </div>
            <RankingMunicipiosEstado data={ufDataFilteredByYear} selectedIndicator={selectedIndicator} rankingType={rankingType} selectedYear={selectedYear} ufConfig={ufMapConfig} />
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando a Distribuição (Estado vs. Todos os estados selecionados)</h3>
            <p className="text-sm mt-1">O gráfico de violino compara a forma da distribuição dos valores do estado (azul) com todos os estados selecionados (laranja). Ele permite ver se o estado é mais ou menos desigual que o país e se sua mediana (linha central) é maior ou menor.</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            {violinChartData ? <Plot data={violinChartData} layout={{ title: `Distribuição de ${INDICADORES_MAP[selectedIndicator] || selectedIndicator} (${selectedYear})`, yaxis: { title: 'Valor do Indicador' }, autosize: true }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p className="flex items-center justify-center h-full">Dados insuficientes para a comparação.</p>}
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando a Variação Temporal</h3>
            <p className="text-sm mt-1">Este gráfico destaca os 10 municípios com a maior mudança (positiva ou negativa) no indicador entre dois anos. Linhas verdes indicam melhora, enquanto as vermelhas indicam piora (considerando a polaridade do indicador). Use os seletores para alterar o período.</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md w-full">
            <div className="flex flex-wrap gap-4 items-center justify-center my-4">
            <label className="flex flex-col">Ano Inicial:
            <select value={slopeStartYear || ''} onChange={(e) => setSlopeStartYear(parseInt(e.target.value))} className="p-2 border rounded-md">
            {availableYears.map(year => (<option key={`start-${year}`} value={year}>{year}</option>))}
            </select>
            </label>
            <label className="flex flex-col">Ano Final:
            <select value={slopeEndYear || ''} onChange={(e) => setSlopeEndYear(parseInt(e.target.value))} className="p-2 border rounded-md">
            {availableYears.map(year => (<option key={`end-${year}`} value={year}>{year}</option>))}
            </select>
            </label>
            </div>
            <div className="h-[500px]">
            {slopeChartData.length > 0 ? <Plot data={slopeChartData} layout={{ title: `Variação de ${INDICADORES_MAP[selectedIndicator] || selectedIndicator} (${slopeStartYear}-${slopeEndYear})`, showlegend: false, xaxis: { type: 'category' } }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p className="flex items-center justify-center h-full">Dados insuficientes ou anos inválidos para análise.</p>}
            </div>
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando a Série Histórica</h3>
            <p className="text-sm mt-1">Este gráfico mostra a evolução da média do indicador para o estado ao longo dos anos, permitindo identificar tendências de longo prazo.</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            <HistoricoIndicadorEstado data={ufDataAllYears} selectedIndicator={selectedIndicator} selectedMunicipalities={[]} ufConfig={ufMapConfig} />
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando a Distribuição por Ano</h3>
            <p className="text-sm mt-1">A "Série Histórica" acima mostra só a média estadual ano a ano. Este box plot revela o que está por trás dela: a dispersão entre municípios e os outliers em cada ano, mostrando se o estado está ficando mais homogêneo ou mais desigual ao longo do tempo.</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            {yearlyDistributionData ? <Plot data={yearlyDistributionData} layout={{ title: `Distribuição de ${INDICADORES_MAP[selectedIndicator] || selectedIndicator} por Ano`, yaxis: { title: 'Valor' }, showlegend: false, autosize: true }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p className="flex items-center justify-center h-full text-gray-500">Dados insuficientes para múltiplos anos.</p>}
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando a Correlação</h3>
            <p className="text-sm mt-1">O gráfico de dispersão plota um indicador contra o outro para cada município. Ele ajuda a identificar se existe uma relação entre eles (ex: à medida que um sobe, o outro também sobe ou desce).</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[650px] w-full">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">Correlação entre Indicadores</h2>
            <div className="flex flex-wrap gap-4 items-center justify-center mb-4">
            <label className="flex flex-col">Eixo X: <select value={scatterX} onChange={(e) => setScatterX(e.target.value)} className="p-2 border rounded-md">{availableIndicators.map(k => (<option key={k} value={k}>{INDICADORES_MAP[k] || k}</option>))}</select></label>
            <label className="flex flex-col">Eixo Y: <select value={scatterY} onChange={(e) => setScatterY(e.target.value)} className="p-2 border rounded-md">{availableIndicators.map(k => (<option key={k} value={k}>{INDICADORES_MAP[k] || k}</option>))}</select></label>
            </div>
            <GraficoDispersaoEstado data={ufDataFilteredByYear} scatterX={scatterX} scatterY={scatterY} selectedYear={selectedYear} ufConfig={ufMapConfig} />
            </div>

            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800">
            <h3 className="font-semibold text-lg">Interpretando a Matriz de Correlação</h3>
            <p className="text-sm mt-1">Complementa o gráfico de dispersão acima mostrando a correlação de Pearson entre TODOS os pares de indicadores de uma vez, calculada só com os municípios de {ufMapConfig.nome || selectedUf}. Vermelho indica correlação positiva, azul indica negativa; quanto mais escura a célula, mais forte a relação.</p>
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md w-full" style={{ height: `${Math.max(450, 80 + availableIndicators.length * 32)}px` }}>
            {correlationMatrixData ?
                <Plot
                data={[{
                    type: 'heatmap', z: correlationMatrixData.z, x: correlationMatrixData.labels, y: correlationMatrixData.labels,
                    text: correlationMatrixData.text, texttemplate: '%{text}', hoverinfo: 'x+y+z',
                    colorscale: 'RdBu', reversescale: true, zmin: -1, zmax: 1,
                    colorbar: { title: { text: 'Correlação (r)' } },
                }]}
                layout={{ title: `Matriz de Correlação entre Indicadores (${selectedYear})`, margin: { t: 60, b: 120, l: 200, r: 20 }, autosize: true, xaxis: { tickangle: -45 } }}
                config={{ responsive: true, displayModeBar: false }}
                className="w-full h-full"
                />
                : <p className="flex items-center justify-center h-full text-gray-500">Dados insuficientes para calcular correlações.</p>}
            </div>
            </div>
        )}
        </div>
    );
};

export default AnalisePorEstadoPage;
