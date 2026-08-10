// src/components/dashboards/indicadores/VisaoGeralTabContent.jsx

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';

// Importa mapas de configuração e indicadores
import { INDICADORES_MAP } from '../../../config/indicadores';
import { UF_CONFIGS } from '../../../config/ufConfigs';

const GEOJSON_ID_KEY = 'id';


const VisaoGeralTabContent = ({
    allData,
    geojson,
    selectedIndicator,
    selectedYear,
    scatterX,
    scatterY,
    setScatterX, // Setter para o eixo X do scatter
    setScatterY, // Setter para o eixo Y do scatter
    loadingMap,
    availableIndicators // Lista de indicadores disponíveis
}) => {

    // 1. Mapa Coroplético do Brasil por Média Estadual
    const mapBrazilChartData = useMemo(() => {
        if (!geojson || !allData || allData.length === 0 || !selectedIndicator || selectedYear === null || selectedYear === undefined) return null;

        const dataForSelectedYear = allData.filter(item => item.ANO === selectedYear);
        if (dataForSelectedYear.length === 0) return null;

        const stateAverages = dataForSelectedYear.reduce((acc, item) => {
            if (item.UF && item[selectedIndicator] !== undefined && item[selectedIndicator] !== null && !isNaN(item[selectedIndicator])) {
                if (!acc[item.UF]) {
                    acc[item.UF] = { sum: 0, count: 0 };
                }
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

        const municipalityDataMapForMap = new Map();
        dataForSelectedYear.forEach(item => {
            const stateAvg = avgByState.find(s => s.uf === item.UF)?.average;
            if (stateAvg !== undefined) {
                municipalityDataMapForMap.set(String(item.cod_mun_ibge_7), stateAvg);
            }
        });

        const locations = [];
        const zValues = [];
        const textValues = [];

        geojson.features.forEach(feature => {
            const geoId = String(feature.properties[GEOJSON_ID_KEY]);
            const stateAverageValue = municipalityDataMapForMap.get(geoId);
            const municipioName = feature.properties.nome;
            const ufCodeFromGeoId = String(feature.properties[GEOJSON_ID_KEY]).substring(0,2);
            const ufNameInGeojson = UF_CONFIGS[Object.keys(UF_CONFIGS).find(key => UF_CONFIGS[key].ibgePrefix === ufCodeFromGeoId)]?.nome || feature.properties.UF || ufCodeFromGeoId;


            locations.push(geoId);

            if (stateAverageValue !== undefined && stateAverageValue !== null) {
                let hoverText = `${municipioName} (${ufNameInGeojson})`;

                zValues.push(stateAverageValue);
                const indicatorLabel = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
                hoverText += `<br>${indicatorLabel}: ${typeof stateAverageValue === 'number' ? stateAverageValue.toFixed(2) : stateAverageValue}`;
                textValues.push(hoverText);
            } else {
                zValues.push(null);
                textValues.push(`${municipioName} (${ufNameInGeojson})<br>Sem dados para ${selectedYear}`);
            }
        });

        if (locations.length === 0) return null;

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
                title: { text: `Média Estadual de<br>${INDICADORES_MAP[selectedIndicator] || selectedIndicator}`, side: 'right' },
                len: 0.75, x: 0.95, y: 0.5,
            },
            marker: { line: { color: 'white', width: 0.5 } },
        }];
    }, [geojson, allData, selectedIndicator, selectedYear]);

    const mapBrazilTitle = useMemo(() => {
        const indicatorLabel = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
        return `Média Estadual de ${indicatorLabel} em todos os Estados (${selectedYear})`;
    }, [selectedIndicator, selectedYear]);


    // 2. Gráfico de Barras de Ranking de Estados
    const rankingStatesChartData = useMemo(() => {
        if (!allData || allData.length === 0 || !selectedIndicator || selectedYear === null || selectedYear === undefined) return [];

        const dataForSelectedYear = allData.filter(item => item.ANO === selectedYear);
        if (dataForSelectedYear.length === 0) return [];

        const stateAverages = dataForSelectedYear.reduce((acc, item) => {
            if (item.UF && item[selectedIndicator] !== undefined && item[selectedIndicator] !== null && !isNaN(item[selectedIndicator])) {
                if (!acc[item.UF]) {
                    acc[item.UF] = { sum: 0, count: 0 };
                }
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
            x: averages,
            y: states,
            type: 'bar',
            orientation: 'h',
            marker: { color: 'rgba(58, 137, 187, 0.7)' },
                                           hovertemplate: `Estado: %{y}<br>Média: %{x:.2f}<extra></extra>`,
        }];
    }, [allData, selectedIndicator, selectedYear]);

    const rankingStatesTitle = useMemo(() => {
        const indicatorLabel = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
        return `Ranking de Estados por Média de ${indicatorLabel}<br>(${selectedYear})`;
    }, [selectedIndicator, selectedYear]);


    // 3. Gráfico de Linha de Série Histórica Nacional
    const nationalHistoricalChartData = useMemo(() => {
        if (!allData || allData.length === 0 || !selectedIndicator) return [];

        const nationalAveragesByYear = {};
        allData.forEach(item => {
            if (item.ANO && item[selectedIndicator] !== undefined && item[selectedIndicator] !== null && !isNaN(item[selectedIndicator])) {
                if (!nationalAveragesByYear[item.ANO]) {
                    nationalAveragesByYear[item.ANO] = { sum: 0, count: 0 };
                }
                nationalAveragesByYear[item.ANO].sum += item[selectedIndicator];
                nationalAveragesByYear[item.ANO].count += 1;
            }
        });

        const years = Object.keys(nationalAveragesByYear).filter(year => nationalAveragesByYear[year].count > 0).sort((a,b) => a-b);
        const avgValues = years.map(year => nationalAveragesByYear[year].sum / nationalAveragesByYear[year].count);

        if (years.length === 0) return [];

        return [{
            x: years,
            y: avgValues,
            mode: 'lines+markers',
            name: 'Média Nacional',
            marker: { color: 'green' },
            hovertemplate: 'Ano: %{x}<br>Média Nacional: %{y:.2f}<extra></extra>',
        }];
    }, [allData, selectedIndicator]);

    const nationalHistoricalTitle = useMemo(() => {
        const indicatorLabel = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
        return `Série Histórica Nacional de ${indicatorLabel}`;
    }, [selectedIndicator]);


    // 4. Box Plot por Estado
    const boxPlotChartData = useMemo(() => {
        if (!allData || allData.length === 0 || !selectedIndicator || selectedYear === null || selectedYear === undefined) return [];

        const dataForSelectedYear = allData.filter(item => item.ANO === selectedYear);
        if (dataForSelectedYear.length === 0) return [];

        const validData = dataForSelectedYear.filter(item =>
        item.UF && item[selectedIndicator] !== undefined && item[selectedIndicator] !== null && typeof item[selectedIndicator] === 'number' && !isNaN(item[selectedIndicator])
        );

        const traces = [];
        const ufs = [...new Set(validData.map(item => item.UF))].sort();

        ufs.forEach(uf => {
            const ufValues = validData.filter(item => item.UF === uf).map(item => item[selectedIndicator])
            .filter(v => typeof v === 'number' && !isNaN(v)); // Filtra apenas números válidos
            if (ufValues.length > 0) {
                traces.push({
                    y: ufValues,
                    name: UF_CONFIGS[uf]?.nome || uf,
                    type: 'box',
                    boxpoints: 'outliers',
                    hovertemplate: `Estado: ${UF_CONFIGS[uf]?.nome || uf}<br>Valor: %{y}<extra></extra>`,
                });
            }
        });

        if (traces.length === 0) return [];
        return traces;
    }, [allData, selectedIndicator, selectedYear]);

    const boxPlotTitle = useMemo(() => {
        const indicatorLabel = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
        return `Distribuição de ${indicatorLabel}<br>por Estado (${selectedYear})`;
    }, [selectedIndicator, selectedYear]);


    // 5. Gráfico de Dispersão de Correlação Nacional
    const nationalScatterChartData = useMemo(() => {
        const indicatorsArray = Array.isArray(availableIndicators) ? availableIndicators : [];

        // Condição mais robusta para retornar vazio e exibir mensagem
        if (!allData || allData.length === 0 || !selectedYear || indicatorsArray.length < 2 || !scatterX || !scatterY || !indicatorsArray.includes(scatterX) || !indicatorsArray.includes(scatterY)) {
            return [];
        }

        const dataForSelectedYear = allData.filter(item => item.ANO === selectedYear);
        if (dataForSelectedYear.length === 0) {
            return [];
        }

        const validData = dataForSelectedYear.filter(item =>
        typeof item[scatterX] === 'number' && !isNaN(item[scatterX]) &&
        typeof item[scatterY] === 'number' && !isNaN(item[scatterY]) &&
        (item.perfil || 'Desconhecido')
        );

        if (validData.length === 0) {
            return [];
        }

        const groupedData = validData.reduce((acc, item) => {
            const profile = item.perfil ? String(item.perfil) : 'Desconhecido';
        if (!acc[profile]) {
            acc[profile] = [];
        }
        acc[profile].push(item);
        return acc;
        }, {});

        const traces = Object.keys(groupedData).map(profile => ({
            x: groupedData[profile].map(item => item[scatterX]),
                                                                y: groupedData[profile].map(item => item[scatterY]),
                                                                mode: 'markers',
                                                                type: 'scatter',
                                                                name: profile,
                                                                text: groupedData[profile].map(item => {
                                                                    const xLabel = INDICADORES_MAP[scatterX] || scatterX;
                                                                    const yLabel = INDICADORES_MAP[scatterY] || scatterY;
                                                                    return `${item.nome_mun || item.municipio}<br>UF: ${item.UF}<br>${xLabel}: ${item[scatterX]}<br>${yLabel}: ${item[scatterY]}`;
                                                                }),
                                                                hoverinfo: 'text',
                                                                marker: { size: 8, opacity: 0.7 },
        }));

        if (traces.every(trace => trace.x.length === 0)) {
            return [];
        }
        return traces;

    }, [allData, scatterX, scatterY, selectedYear, availableIndicators]);

    const nationalScatterTitle = useMemo(() => {
        const xLabel = INDICADORES_MAP[scatterX] || scatterX;
        const yLabel = INDICADORES_MAP[scatterY] || scatterY;
        return `Correlação entre ${xLabel}<br>e ${yLabel} em todos os Estados (${selectedYear})`;
    }, [scatterX, scatterY, selectedYear]);


    // --- Mensagens de feedback / loading ---
    if (!allData || allData.length === 0) {
        return <p className="text-center p-4 text-gray-700">Nenhum dado disponível para a Visão Geral. Por favor, selecione um arquivo de dados válido na parte superior da página.</p>;
    }
    if (loadingMap) {
        return <p className="text-center p-4 text-gray-700">Carregando mapa GeoJSON do Brasil...</p>;
    }
    if (!geojson) {
        return <p className="text-center p-4 text-red-500">Não foi possível carregar o mapa GeoJSON para o Brasil.</p>;
    }
    if (!selectedIndicator) {
        return <p className="text-center p-4 text-gray-700">Selecione um indicador para visualizar os gráficos.</p>;
    }
    if (!selectedYear) {
        return <p className="text-center p-4 text-gray-700">Selecione um ano para visualizar os dados.</p>;
    }
    // Para gráficos de dispersão, verificar se scatterX e scatterY estão selecionados
    if (!scatterX || !scatterY) {
        return <p className="text-center p-4 text-gray-700">Selecione dois indicadores para o gráfico de dispersão.</p>;
    }


    return (
        <div className="flex flex-col gap-6 mt-6">
        {/* Gráfico do Mapa Coroplético do Brasil por Média Estadual */}
        {mapBrazilChartData && (
            <div className="bg-white p-4 rounded-lg shadow-md h-[600px] w-full">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">Mapa do Brasil por Média Estadual</h2>
            <Plot
            data={mapBrazilChartData}
            layout={{
                title: {
                    text: mapBrazilTitle,
                    font: { size: 20, color: '#333' },
                    xref: 'paper', x: 0.05, xanchor: 'left', yanchor: 'top',
                },
                geo: {
                    scope: 'south america',
                    showland: true, landcolor: 'rgb(243,243,243)',
                                countrycolor: 'rgb(204,204,204)', projection: { type: 'mercator' },
                                fitbounds: false,
                                center: { lat: -14, lon: -50 },
                                lataxis: { range: [-35, 5] },
                                lonaxis: { range: [-75, -30] },
                                visible: false,
                                subunitcolor: 'rgb(204,204,243)', coastlinecolor: 'rgb(204,204,204)',
                },
                margin: { t: 50, b: 20, l: 20, r: 20 }, autosize: true,
            }}
            config={{ responsive: true, displayModeBar: false }}
            className="w-full h-full"
            />
            </div>
        )}

        {/* Gráfico de Barras de Ranking de Estados */}
        {rankingStatesChartData.length > 0 && (
            <div className="bg-white p-4 rounded-lg shadow-md h-[650px] w-full">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">Ranking de Estados</h2>
            <Plot
            data={rankingStatesChartData}
            layout={{
                title: { text: rankingStatesTitle, font: { size: 18, color: '#333' } },
                xaxis: { title: INDICADORES_MAP[selectedIndicator] || selectedIndicator, automargin: true },
                yaxis: { title: 'Estado', automargin: true, tickangle: -45 },
                margin: { t: 60, b: 80, l: 150, r: 30 }, autosize: true,
            }}
            config={{ responsive: true, displayModeBar: false }}
            className="w-full h-full"
            />
            </div>
        )}

        {/* Gráfico de Linha de Série Histórica Nacional */}
        {nationalHistoricalChartData.length > 0 && (
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">Série Histórica Nacional</h2>
            <Plot
            data={nationalHistoricalChartData}
            layout={{
                title: { text: nationalHistoricalTitle, font: { size: 18, color: '#333' } },
                xaxis: { title: 'Ano', type: 'category', automargin: true },
                yaxis: { title: INDICADORES_MAP[selectedIndicator] || selectedIndicator, automargin: true },
                legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 },
                margin: { t: 60, b: 60, l: 60, r: 30 }, autosize: true, hovermode: 'closest',
            }}
            config={{ responsive: true, displayModeBar: false }}
            className="w-full h-full"
            />
            </div>
        )}

        {/* Box Plot por Estado */}
        {boxPlotChartData.length > 0 && (
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">Distribuição por Estado</h2>
            <Plot
            data={boxPlotChartData}
            layout={{
                title: { text: boxPlotTitle, font: { size: 18, color: '#333' } },
                xaxis: { title: 'Estado', automargin: true },
                yaxis: { title: INDICADORES_MAP[selectedIndicator] || selectedIndicator, automargin: true },
                margin: { t: 60, b: 60, l: 60, r: 30 }, autosize: true, hovermode: 'closest',
            }}
            config={{ responsive: true, displayModeBar: false }}
            className="w-full h-full"
            />
            </div>
        )}

        {/* Gráfico de Dispersão de Correlação Nacional */}
        {/* O contêiner de dispersão é renderizado se as condições básicas permitem,
            e o Plot é renderizado apenas se nationalScatterChartData não é vazio. */}
            {(Array.isArray(availableIndicators) && availableIndicators.length > 1 && allData && allData.length > 0 && selectedYear !== null && selectedYear !== undefined && scatterX && scatterY) ? (
                <div className="bg-white p-4 rounded-lg shadow-md h-[650px] w-full">
                <h2 className="text-2xl font-semibold text-gray-700 mb-4">Correlação Nacional</h2>
                {/* DROPDOWNS MOVIDAS PARA CIMA DO GRÁFICO */}
                <div className="flex flex-wrap gap-4 items-center justify-center mb-4">
                {Array.isArray(availableIndicators) && availableIndicators.length > 0 && (
                    <>
                    <label className="flex flex-col">
                    Eixo X:
                    <select
                    value={scatterX}
                    onChange={e => setScatterX(e.target.value)}
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
                    onChange={e => setScatterY(e.target.value)}
                    className="p-2 border rounded-md"
                    >
                    {availableIndicators.map(indicatorKey => (
                        <option key={indicatorKey} value={indicatorKey}>
                        {INDICADORES_MAP[indicatorKey] || indicatorKey}
                        </option>
                    ))}
                    </select>
                    </label>
                    </>
                )}
                </div>
                {nationalScatterChartData && nationalScatterChartData.length > 0 ? (
                    <Plot
                    data={nationalScatterChartData}
                    layout={{
                        title: { text: nationalScatterTitle, font: { size: 20, color: '#333' } },
                        xaxis: { title: INDICADORES_MAP[scatterX] || scatterX, automargin: true },
                        yaxis: { title: INDICADORES_MAP[scatterY] || scatterY, automargin: true },
                        hovermode: 'closest', showlegend: true,
                        legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 },
                        margin: { t: 60, b: 60, l: 60, r: 30 }, autosize: true,
                    }}
                    config={{ responsive: true, displayModeBar: false }}
                    className="w-full h-full"
                    />
                ) : (
                    <div className="flex items-center justify-center h-full text-gray-600">
                    {(!scatterX || !scatterY || !availableIndicators.includes(scatterX) || !availableIndicators.includes(scatterY)) ? (
                        <p>Selecione dois indicadores válidos nos dropdowns acima para visualizar a correlação.</p>
                    ) : (
                        <p>Não há dados válidos para exibir o gráfico de correlação com os indicadores selecionados no ano {selectedYear}.</p>
                    )}
                    </div>
                )}
                </div>
            ) : (
                <div className="bg-white p-4 rounded-lg shadow-md h-[650px] w-full flex items-center justify-center">
                <p className="text-gray-600 text-center">
                Carregando dados para o gráfico de correlação...
                </p>
                </div>
            )}
            </div>
    );
};

export default VisaoGeralTabContent;
