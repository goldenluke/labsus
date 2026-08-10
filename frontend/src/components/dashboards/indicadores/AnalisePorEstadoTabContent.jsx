// src/components/dashboards/indicadores/AnalisePorEstadoTabContent.jsx

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';

import { INDICADORES_MAP } from '../../../config/indicadores';
import { UF_CONFIGS } from '../../../config/ufConfigs';

const GEOJSON_ID_KEY = 'id';

const AnalisePorEstadoTabContent = ({
    // allData não é mais usado diretamente aqui, é melhor usar os dados já filtrados pelo hook pai
    geojson,
    selectedUf,
    setSelectedUf, // Adicionado setter para UF
    selectedIndicator,
    setSelectedIndicator, // Adicionado setter para Indicador
    selectedYear,
    setSelectedYear, // Adicionado setter para Ano
    loadingMap, // Mantido, embora o carregamento do mapa seja do hook
    availableUfs, // Adicionado para popular o dropdown de UFs
    availableYears, // Adicionado para popular o dropdown de Anos
    availableIndicators, // Adicionado para popular o dropdown de Indicadores
    ufMapConfig, // Configurações do mapa da UF (zoom, center)
ufDataFilteredByYear, // Dados já filtrados por UF e Ano pelo hook pai
ufDataAllYears, // Dados já filtrados por UF para todos os anos pelo hook pai
mapChartData, // Dados do mapa coroplético já preparados pelo hook pai
mapTitle, // Título do mapa já preparado pelo hook pai
rankingType, // Tipo de ranking (melhores/piores)
setRankingType, // Setter para o tipo de ranking
scatterX, // Indicador para eixo X do gráfico de dispersão
setScatterX, // Setter para scatterX
scatterY, // Indicador para eixo Y do gráfico de dispersão
setScatterY, // Setter para scatterY
selectedMunicipality, // Município selecionado para destaque no histograma
setSelectedMunicipality, // Setter para selectedMunicipality
}) => {
    // --- 1. Mapa coroplético do estado ---
    // mapChartData e mapTitle já são recebidos como props do hook pai.
    // Nenhuma lógica de cálculo é necessária aqui.

    // --- 2. Histograma da distribuição do indicador nos municípios do estado ---
    const histogramaData = useMemo(() => {
        if (!ufDataFilteredByYear || ufDataFilteredByYear.length === 0 || !selectedIndicator) return [];

        const values = ufDataFilteredByYear.map(item => item[selectedIndicator]).filter(v => v !== undefined && v !== null && !isNaN(v));

        if (values.length === 0) {
            return [];
        }

        let traces = [{
            x: values,
            type: 'histogram',
            marker: { color: 'rgba(58, 137, 187, 0.7)' },
                                   opacity: 0.75,
                                   nbinsx: Math.min(20, Math.max(5, Math.ceil(values.length / 10))),
                                   name: INDICADORES_MAP[selectedIndicator] || selectedIndicator,
                                   hovertemplate: 'Intervalo: %{x}<br>Frequência: %{y}<extra></extra>',
        }];

        // Adiciona uma linha vertical para um município específico, se selecionado
        if (selectedMunicipality) {
            const munData = ufDataFilteredByYear.find(item => item.cod_mun_ibge_7 === selectedMunicipality.cod_mun_ibge_7);
            if (munData && munData[selectedIndicator] !== undefined && munData[selectedIndicator] !== null && !isNaN(munData[selectedIndicator])) {
                traces.push({
                    x: [munData[selectedIndicator], munData[selectedIndicator]],
                    y: [0, Math.max(...values.map(v => 0)) * 0.1 || 100], // Ajuste Y baseado nos dados
                            mode: 'lines',
                            type: 'scatter',
                            name: `Valor de ${selectedMunicipality.nome_mun || selectedMunicipality.municipio}`,
                            marker: { color: 'red' },
                            line: { dash: 'dot', width: 2 },
                            hoverinfo: 'text',
                            text: `${selectedMunicipality.nome_mun || selectedMunicipality.municipio}: ${munData[selectedIndicator]}`,
                            showlegend: true,
                });
            }
        }
        return traces;
    }, [ufDataFilteredByYear, selectedIndicator, selectedMunicipality]);

    const histogramaTitle = useMemo(() => {
        const indicador = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
        const nomeUf = ufMapConfig?.nome || selectedUf;
        return `Distribuição de ${indicador} nos Municípios de ${nomeUf} (${selectedYear})`;
    }, [selectedIndicator, selectedYear, selectedUf, ufMapConfig]);

    // --- 3. Ranking Top 15 Municípios ---
    const rankingMunicipiosData = useMemo(() => {
        if (!ufDataFilteredByYear || ufDataFilteredByYear.length === 0 || !selectedIndicator || !rankingType) return [];

        const filteredData = ufDataFilteredByYear.filter(item =>
        item[selectedIndicator] !== undefined && item[selectedIndicator] !== null && !isNaN(item[selectedIndicator])
        );

        const sorted = [...filteredData].sort((a, b) => {
            // Lógica de polaridade para ordenação
            const polarity = INDICADORES_MAP[selectedIndicator]?.includes('(por 1.000 nascidos vivos)') ||
            INDICADORES_MAP[selectedIndicator]?.includes('Mortalidade') ||
            INDICADORES_MAP[selectedIndicator]?.includes('Proporção de Óbitos') ||
            INDICADORES_MAP[selectedIndicator]?.includes('Internações') ||
            INDICADORES_MAP[selectedIndicator]?.includes('Incidência') ||
            INDICADORES_MAP[selectedIndicator]?.includes('Abandono')
            ? 'low' : 'high'; // Exemplo simples, idealmente viria de um config

        if (rankingType === 'melhores') {
            return polarity === 'high' ? b[selectedIndicator] - a[selectedIndicator] : a[selectedIndicator] - b[selectedIndicator];
        } else { // 'piores'
            return polarity === 'high' ? a[selectedIndicator] - b[selectedIndicator] : b[selectedIndicator] - a[selectedIndicator];
        }
        });

        const topN = 15;
        const slicedData = sorted.slice(0, topN);

        if (slicedData.length === 0) {
            return [];
        }

        const municipalities = slicedData.map(item => item.nome_mun || item.municipio).reverse();
        const indicatorValues = slicedData.map(item => item[selectedIndicator]).reverse();

        return [{
            x: indicatorValues,
            y: municipalities,
            type: 'bar',
            orientation: 'h',
            marker: { color: rankingType === 'melhores' ? 'rgba(76, 175, 80, 0.8)' : 'rgba(244, 67, 54, 0.8)' },
                                          name: 'Ranking',
                                          hovertemplate: `Município: %{y}<br>${INDICADORES_MAP[selectedIndicator] || selectedIndicator}: %{x}<extra></extra>`,
        }];
    }, [ufDataFilteredByYear, selectedIndicator, rankingType]);

    const rankingMunicipiosTitle = useMemo(() => {
        const indicador = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
        const rankingText = rankingType === 'melhores' ? 'Melhores' : 'Piores';
        const nomeUf = ufMapConfig?.nome || selectedUf;
        return `${rankingText} Municípios em ${indicador} em ${nomeUf} (${selectedYear})`;
    }, [selectedIndicator, rankingType, selectedYear, selectedUf, ufMapConfig]);

    // --- 4. Histórico anual do indicador médio no estado ---
    const historicoData = useMemo(() => {
        if (!ufDataAllYears || ufDataAllYears.length === 0 || !selectedIndicator) return [];

        const groupedByYear = {};

        ufDataAllYears.forEach(item => {
            if (
                item[selectedIndicator] !== undefined &&
                item[selectedIndicator] !== null &&
                !isNaN(item[selectedIndicator]) &&
                item.ANO
            ) {
                if (!groupedByYear[item.ANO]) {
                    groupedByYear[item.ANO] = { sum: 0, count: 0 };
                }
                groupedByYear[item.ANO].sum += item[selectedIndicator];
                groupedByYear[item.ANO].count += 1;
            }
        });

        const years = Object.keys(groupedByYear).sort();
        if (years.length === 0) return [];

        const avgValues = years.map(year => groupedByYear[year].sum / groupedByYear[year].count);

        return [{
            x: years,
            y: avgValues,
            mode: 'lines+markers',
            name: 'Média Estadual',
            marker: { color: 'green' },
            hovertemplate: 'Ano: %{x}<br>Média: %{y:.2f}<extra></extra>',
        }];
    }, [ufDataAllYears, selectedIndicator]);

    const historicoTitle = useMemo(() => {
        const indicador = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
        const nomeUf = ufMapConfig?.nome || selectedUf;
        return `Série Histórica Anual de ${indicador} em ${nomeUf}`;
    }, [selectedIndicator, selectedUf, ufMapConfig]);

    // --- 5. Gráfico de dispersão correlacionando dois indicadores ---
    const graficoDispersaoData = useMemo(() => {
        if (!ufDataFilteredByYear || ufDataFilteredByYear.length === 0 || !scatterX || !scatterY) return [];

        const dataForYear = ufDataFilteredByYear.filter(item =>
        item[scatterX] !== undefined && item[scatterX] !== null && !isNaN(item[scatterX]) &&
        item[scatterY] !== undefined && item[scatterY] !== null && !isNaN(item[scatterY])
        );

        if (dataForYear.length === 0) return [];

        return [{
            x: dataForYear.map(item => item[scatterX]),
                                         y: dataForYear.map(item => item[scatterY]),
                                         mode: 'markers',
                                         type: 'scatter',
                                         marker: { size: 8, opacity: 0.7, color: 'rgba(58, 137, 187, 0.7)' },
                                         text: dataForYear.map(item =>
                                         `${item.nome_mun || item.municipio}<br>UF: ${item.UF}<br>${INDICADORES_MAP[scatterX] || scatterX}: ${item[scatterX]}<br>${INDICADORES_MAP[scatterY] || scatterY}: ${item[scatterY]}`
                                         ),
                                         hoverinfo: 'text',
                                         name: 'Municípios',
        }];
    }, [ufDataFilteredByYear, scatterX, scatterY]);

    const graficoDispersaoTitle = useMemo(() => {
        const labelX = INDICADORES_MAP[scatterX] || scatterX;
        const labelY = INDICADORES_MAP[scatterY] || scatterY;
        const nomeUf = ufMapConfig?.nome || selectedUf;
        return `Correlação entre ${labelX} e ${labelY} em ${nomeUf} (${selectedYear})`;
    }, [scatterX, scatterY, selectedUf, selectedYear, ufMapConfig]);

    // --- Mensagens de feedback e carregamento ---
    // A validação de `allData`, `loadingMap`, `geojson`, etc. é feita no componente pai `IndicadoresViewerPage`.
    // Aqui, assumimos que se este componente está sendo renderizado, os dados básicos estão disponíveis.
    // O foco aqui é se há dados SUFICIENTES para CADA GRÁFICO específico, após os filtros de UF/Ano.

    if (ufDataFilteredByYear.length === 0) {
        return <p className="text-center p-4 text-gray-700">Nenhum dado encontrado para o Estado e Ano selecionados. Ajuste os filtros.</p>;
    }
    if (!selectedIndicator) {
        return <p className="text-center p-4 text-gray-700">Selecione um indicador para visualizar os gráficos.</p>;
    }
    // Assegura que scatterX e scatterY tenham valores antes de tentar renderizar o gráfico de dispersão
    if ((!scatterX || !scatterY) && availableIndicators.length > 1) {
        return <p className="text-center p-4 text-gray-700">Selecione dois indicadores para o gráfico de dispersão.</p>;
    }


    return (
        <div className="flex flex-col gap-6 mt-6">
        {/* Controles de filtro para Estado, Ano, Indicador (agora dentro do AnalisePorEstadoTabContent) */}
        <div className="bg-white p-6 rounded-lg shadow-md mb-4 flex flex-wrap gap-4 items-center justify-center">
        <label className="flex flex-col">
        Estado:
        <select
        value={selectedUf}
        onChange={e => setSelectedUf(e.target.value)}
        className="p-2 border rounded-md"
        >
        {Array.isArray(availableUfs) && availableUfs.map(ufCode => (
            <option key={ufCode} value={ufCode}>
            {UF_CONFIGS[ufCode]?.nome || ufCode}
            </option>
        ))}
        </select>
        </label>

        <label className="flex flex-col">
        Ano:
        <select
        value={selectedYear}
        onChange={e => setSelectedYear(parseInt(e.target.value))}
        className="p-2 border rounded-md"
        >
        {Array.isArray(availableYears) && availableYears.map(year => (
            <option key={year} value={year}>{year}</option>
        ))}
        </select>
        </label>

        <label className="flex flex-col">
        Indicador:
        <select
        value={selectedIndicator}
        onChange={e => setSelectedIndicator(e.target.value)}
        className="p-2 border rounded-md"
        >
        {Array.isArray(availableIndicators) && availableIndicators.map(indicatorKey => (
            <option key={indicatorKey} value={indicatorKey}>
            {INDICADORES_MAP[indicatorKey] || indicatorKey}
            </option>
        ))}
        </select>
        </label>
        </div>

        {/* 1. Mapa coroplético */}
        {mapChartData && (
            <div className="bg-white p-4 rounded-lg shadow-md h-[600px] w-full">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">{mapTitle}</h2>
            <Plot
            data={mapChartData}
            layout={{
                title: { text: mapTitle, font: { size: 20, color: '#333' }, xref: 'paper', x: 0.05, xanchor: 'left', yanchor: 'top' },
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
            </div>
        )}

        {/* 2. Histograma */}
        {histogramaData.length > 0 && (
            <div className="bg-white p-4 rounded-lg shadow-md h-[400px] w-full">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">{histogramaTitle}</h2>
            <Plot
            data={histogramaData}
            layout={{
                title: { text: histogramaTitle, font: { size: 18, color: '#333' } },
                xaxis: { title: INDICADORES_MAP[selectedIndicator] || selectedIndicator, automargin: true },
                yaxis: { title: 'Frequência', automargin: true },
                margin: { t: 60, b: 60, l: 60, r: 30 },
                autosize: true,
                hovermode: 'closest',
            }}
            config={{ responsive: true, displayModeBar: false }}
            className="w-full h-full"
            />
            </div>
        )}

        {/* 3. Ranking Top 15 Municípios */}
        {rankingMunicipiosData.length > 0 && (
            <div className="bg-white p-4 rounded-lg shadow-md h-[600px] w-full">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">{rankingMunicipiosTitle}</h2>
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
            <Plot
            data={rankingMunicipiosData}
            layout={{
                title: { text: rankingMunicipiosTitle, font: { size: 18, color: '#333' } },
                xaxis: { title: INDICADORES_MAP[selectedIndicator] || selectedIndicator, automargin: true },
                yaxis: { title: 'Município', automargin: true, tickangle: -45 },
                margin: { t: 60, b: 80, l: 150, r: 30 },
                autosize: true,
            }}
            config={{ responsive: true, displayModeBar: false }}
            className="w-full h-full"
            />
            </div>
        )}

        {/* 4. Histórico anual */}
        {historicoData.length > 0 && (
            <div className="bg-white p-4 rounded-lg shadow-md h-[400px] w-full">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">{historicoTitle}</h2>
            <Plot
            data={historicoData}
            layout={{
                title: { text: historicoTitle, font: { size: 18, color: '#333' } },
                xaxis: { title: 'Ano', automargin: true, type: 'category' },
                yaxis: { title: INDICADORES_MAP[selectedIndicator] || selectedIndicator, automargin: true },
                margin: { t: 60, b: 60, l: 60, r: 30 },
                autosize: true,
            }}
            config={{ responsive: true, displayModeBar: false }}
            className="w-full h-full"
            />
            </div>
        )}

        {/* 5. Gráfico de dispersão */}
        <div className="bg-white p-4 rounded-lg shadow-md h-[400px] w-full">
        <h2 className="text-2xl font-semibold text-gray-700 mb-4">{graficoDispersaoTitle}</h2>
        <div className="flex flex-wrap gap-4 items-center justify-center mb-4">
        <label className="flex flex-col">
        Eixo X:
        <select
        value={scatterX}
        onChange={(e) => setScatterX(e.target.value)}
        className="p-2 border rounded-md"
        >
        {Array.isArray(availableIndicators) && availableIndicators.map(indicatorKey => (
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
        {Array.isArray(availableIndicators) && availableIndicators.map(indicatorKey => (
            <option key={indicatorKey} value={indicatorKey}>
            {INDICADORES_MAP[indicatorKey] || indicatorKey}
            </option>
        ))}
        </select>
        </label>
        </div>
        {graficoDispersaoData.length > 0 ? (
            <Plot
            data={graficoDispersaoData}
            layout={{
                title: { text: graficoDispersaoTitle, font: { size: 18, color: '#333' } },
                xaxis: { title: INDICADORES_MAP[scatterX] || scatterX, automargin: true },
                yaxis: { title: INDICADORES_MAP[scatterY] || scatterY, automargin: true },
                margin: { t: 60, b: 60, l: 60, r: 30 },
                autosize: true,
                hovermode: 'closest',
            }}
            config={{ responsive: true, displayModeBar: false }}
            className="w-full h-full"
            />
        ) : (
            <p className="text-gray-600 text-center mt-4">Dados insuficientes ou inválidos para gerar o gráfico de dispersão.</p>
        )}
        </div>
        </div>
    );
};

export default AnalisePorEstadoTabContent;
