// src/components/dashboards/indicadores/AnalisePorMunicipioTabContent.jsx

import React, { useMemo, useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { INDICADORES_MAP } from '../../../config/indicadores';
import { INDICADOR_POLARIDADE } from '../../../config/polaridadeIndicadores';
import HistogramaIndicadorEstado from '../../charts/HistogramaIndicadorEstado';
import { UF_CONFIGS } from '../../../config/ufConfigs';


const GEOJSON_ID_KEY = 'id';


const AnalisePorMunicipioTabContent = ({
    allData,
    geojson,
    selectedUf,
    selectedIndicator,
    selectedYear,
    loadingMap,
    ufMapConfig,
    ufDataFilteredByYear,
    ufDataAllYears,
    selectedMunicipality, setSelectedMunicipality,
    mapChartData,
    mapTitle,
    availableIndicators
}) => {
    const [detailedIndicator, setDetailedIndicator] = useState('');

    const availableMunicipalities = useMemo(() => {
        if (!ufDataFilteredByYear || ufDataFilteredByYear.length === 0) return [];

        const uniqueMunicipalities = Array.from(new Map(ufDataFilteredByYear.map(item => [item.cod_mun_ibge_7, item])).values());
        return uniqueMunicipalities.sort((a, b) => (a.nome_mun || a.municipio).localeCompare(b.nome_mun || b.municipio));
    }, [ufDataFilteredByYear]);

    useEffect(() => {
        if (availableMunicipalities.length > 0) {
            if (!selectedMunicipality || !availableMunicipalities.some(m => m.cod_mun_ibge_7 === selectedMunicipality.cod_mun_ibge_7)) {
                setSelectedMunicipality(availableMunicipalities[0]);
            }
        } else {
            setSelectedMunicipality(null);
        }

        if (availableIndicators.length > 0 && !detailedIndicator) {
            setDetailedIndicator(availableIndicators[0]);
        }
    }, [availableMunicipalities, selectedMunicipality, setSelectedMunicipality, availableIndicators, detailedIndicator]);

    const selectedMunicipalityCurrentData = useMemo(() => {
        if (!selectedMunicipality || !ufDataFilteredByYear) return null;
        return ufDataFilteredByYear.find(item => item.cod_mun_ibge_7 === selectedMunicipality.cod_mun_ibge_7);
    }, [selectedMunicipality, ufDataFilteredByYear]);

    const { strongPoints, weakPoints } = useMemo(() => {
        if (!selectedMunicipalityCurrentData || ufDataFilteredByYear.length === 0) {
            return { strongPoints: [], weakPoints: [] };
        }

        const points = [];
        const indicatorsToAnalyze = availableIndicators.filter(key =>
        key !== 'ANO' && key !== 'UF' && key !== 'municipio' && key !== 'nome_mun' && key !== 'cod_mun_ibge_7' && key !== 'perfil' &&
        selectedMunicipalityCurrentData[key] !== null && selectedMunicipalityCurrentData[key] !== undefined &&
        !isNaN(parseFloat(String(selectedMunicipalityCurrentData[key]).replace(',', '.')))
        );

        indicatorsToAnalyze.forEach(indicator => {
            const munValue = selectedMunicipalityCurrentData[indicator];
            if (munValue === null || munValue === undefined || isNaN(munValue)) return;

            const allValues = ufDataFilteredByYear.map(item => item[indicator]).filter(v => v !== null && v !== undefined && !isNaN(v));
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
        };
    }, [selectedMunicipalityCurrentData, ufDataFilteredByYear, availableIndicators]);

    const historicalChartData = useMemo(() => {
        if (!selectedMunicipalityCurrentData || !ufDataAllYears || !detailedIndicator) return [];

        const munHistory = ufDataAllYears
        .filter(item => item.cod_mun_ibge_7 === selectedMunicipality.cod_mun_ibge_7 && item[detailedIndicator] !== null && !isNaN(item[detailedIndicator]))
        .sort((a, b) => a.ANO - b.ANO);

        const stateAvgByYear = ufDataAllYears.reduce((acc, item) => {
            if (item.ANO && item[detailedIndicator] !== null && !isNaN(item[detailedIndicator])) {
                if (!acc[item.ANO]) acc[item.ANO] = { sum: 0, count: 0 };
                acc[item.ANO].sum += item[detailedIndicator];
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
                x: munHistory.map(d => d.ANO),
                                        y: munHistory.map(d => d[detailedIndicator]),
                                        mode: 'lines+markers',
                                        name: selectedMunicipality.nome_mun || selectedMunicipality.municipio,
                                        line: { width: 3 },
                                        hovertemplate: `Ano: %{x}<br>${INDICADORES_MAP[detailedIndicator] || detailedIndicator}: %{y:.2f}<extra></extra>`,
            },
            {
                x: stateHistory.map(d => d.ANO),
                                        y: stateHistory.map(d => d.average),
                                        mode: 'lines',
                                        name: `Média de ${UF_CONFIGS[selectedUf]?.nome || selectedUf}`,
                                        line: { dash: 'dot', color: 'gray' },
                                        hovertemplate: `Ano: %{x}<br>Média Estadual: %{y:.2f}<extra></extra>`,
            }
        ];
    }, [selectedMunicipality, ufDataAllYears, detailedIndicator, selectedUf]);


    const municipalityHighlightTrace = useMemo(() => {
        if (!geojson || !selectedMunicipalityCurrentData) return null;

        const geoId = String(selectedMunicipalityCurrentData.cod_mun_ibge_7);
        const feature = geojson.features.find(f => String(f.properties[GEOJSON_ID_KEY]) === geoId);

        if (!feature) return null;

        return {
            type: 'scattergeo',
            locationmode: 'geojson-id',
            locations: [geoId],
            geojson: { type: 'FeatureCollection', features: [feature] },
            mode: 'lines',
            line: {
                color: '#FF0000',
                width: 3,
                simplify: false
            },
            fill: 'none',
            name: selectedMunicipalityCurrentData.nome_mun || selectedMunicipalityCurrentData.municipio,
            hoverinfo: 'name',
            showlegend: false,
        };
    }, [geojson, selectedMunicipalityCurrentData]);

    const mapContextTitle = useMemo(() => {
        const nomeUf = UF_CONFIGS[selectedUf]?.nome || selectedUf;
        return `Município Selecionado Destacado em ${nomeUf}`;
    }, [selectedUf]);


    // --- Mensagens de feedback / loading ---
    if (!allData || allData.length === 0) {
        return <p className="text-center p-4 text-gray-700">Nenhum dado disponível para a Análise por Município. Por favor, selecione um arquivo de dados válido na parte superior da página.</p>;
    }
    if (!selectedUf) {
        return <p className="text-center p-4 text-gray-700">Selecione um Estado para análise.</p>;
    }
    if (!selectedYear) {
        return <p className="text-center p-4 text-gray-700">Selecione um ano para visualizar os dados.</p>;
    }
    if (!ufDataFilteredByYear || ufDataFilteredByYear.length === 0) {
        return <p className="text-center p-4 text-gray-700">Nenhum dado encontrado para o Estado ({selectedUf}) e Ano ({selectedYear}). Ajuste os filtros.</p>;
    }
    if (loadingMap) {
        return <p className="text-center p-4 text-gray-700">Carregando mapa GeoJSON...</p>;
    }
    if (!geojson) {
        return <p className="text-center p-4 text-red-500">Não foi possível carregar o mapa GeoJSON.</p>;
    }
    if (!mapChartData) {
        return <p className="text-center p-4 text-gray-700">Dados insuficientes para exibir o mapa coroplético do estado.</p>;
    }
    if (!selectedMunicipality) {
        return <p className="text-center p-4 text-gray-700">Selecione um município para iniciar a análise detalhada.</p>;
    }
    if (!detailedIndicator) {
        return <p className="text-center p-4 text-gray-700">Selecione um indicador para a análise detalhada (Raio-X e Histórico).</p>;
    }


    return (
        <div className="flex flex-col gap-6 mt-6">
        {/* Seletor de Município */}
        <div className="bg-white p-4 rounded-lg shadow-md">
        <label className="flex flex-col font-semibold">
        Selecione um Município para Análise Detalhada:
        <select
        value={selectedMunicipality?.cod_mun_ibge_7 || ''}
        onChange={e => {
            const mun = availableMunicipalities.find(m => m.cod_mun_ibge_7 === e.target.value);
            setSelectedMunicipality(mun);
        }}
        className="p-2 border rounded-md mt-1 font-normal"
        >
        {availableMunicipalities.length > 0 ? (
            availableMunicipalities.map(mun => (
                <option key={mun.cod_mun_ibge_7} value={mun.cod_mun_ibge_7}>
                {mun.nome_mun || mun.municipio}
                </option>
            ))
        ) : (
            <option value="">Nenhum município disponível</option>
        )}
        </select>
        </label>
        </div>

        {/* Mapa Coroplético do Estado COM DESTAQUE DO MUNICÍPIO */}
        <div className="bg-white p-4 rounded-lg shadow-md h-[600px] w-full">
        <h2 className="text-2xl font-semibold text-gray-700 mb-4">{mapTitle}</h2> {/* Usar mapTitle do hook pai */}
        <Plot
        data={[
            ...(mapChartData || []), // Garante que mapChartData não seja nulo
            ...(municipalityHighlightTrace ? [municipalityHighlightTrace] : []) // Adiciona o destaque se existir
        ]}
        layout={{
            title: { text: mapTitle, font: { size: 20, color: '#333' }, xref: 'paper', x: 0.05, xanchor: 'left', yanchor: 'top' },
            geo: {
                scope: 'south america',
                showland: true,
                landcolor: 'rgb(243,243,243)',
            countrycolor: 'rgb(204,204,204)',
            projection: { type: 'mercator' },
            fitbounds: 'locations', // Fitbounds para os locations dos traces combinados
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

        {selectedMunicipalityCurrentData ? (
            <>
            {/* Raio-X: Pontos Fortes e Fracos */}
            <div className="bg-white p-4 rounded-lg shadow-md">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">
            Raio-X de {selectedMunicipalityCurrentData.nome_mun || selectedMunicipalityCurrentData.municipio} ({selectedYear})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
            <h3 className="text-xl font-semibold text-green-700 mb-2">Pontos Fortes (Top 3 vs Média Estadual)</h3>
            {strongPoints.length > 0 ? (
                <ul className="list-disc list-inside text-gray-700 space-y-1">
                {strongPoints.map(p => <li key={p.indicator}>{INDICADORES_MAP[p.indicator] || p.indicator}: <span className="font-bold text-green-600">{Math.abs(p.deviation).toFixed(1)}% melhor</span></li>)}
                </ul>
            ) : <p>Nenhum ponto forte destacado.</p>}
            </div>
            <div>
            <h3 className="text-xl font-semibold text-red-700 mb-2">Pontos de Atenção (Top 3 vs Média Estadual)</h3>
            {weakPoints.length > 0 ? (
                <ul className="list-disc list-inside text-gray-700 space-y-1">
                {weakPoints.map(p => <li key={p.indicator}>{INDICADORES_MAP[p.indicator] || p.indicator}: <span className="font-bold text-red-600">{p.deviation.toFixed(1)}% pior</span></li>)}
                </ul>
            ) : <p>Nenhum ponto de atenção destacado.</p>}
            </div>
            </div>
            </div>

            {/* Controles para Gráficos Detalhados */}
            <div className="bg-white p-4 rounded-lg shadow-md">
            <label className="flex flex-col font-semibold">
            Selecione um Indicador para Análise Detalhada:
            <select value={detailedIndicator} onChange={e => setDetailedIndicator(e.target.value)} className="p-2 border rounded-md mt-1 font-normal">
            {availableIndicators.map(ind => <option key={ind} value={ind}>{INDICADORES_MAP[ind] || ind}</option>)}
            </select>
            </label>
            </div>

            {/* Gráficos Detalhados */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            <h3 className="text-xl font-semibold text-gray-700 mb-2">Posição do Município na Distribuição Estadual</h3>
            <HistogramaIndicadorEstado data={ufDataFilteredByYear} selectedIndicator={detailedIndicator} selectedMunicipality={selectedMunicipality} selectedYear={selectedYear} ufConfig={ufMapConfig} />
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            <h3 className="text-xl font-semibold text-gray-700 mb-2">Série Histórica (Município vs. Média Estadual)</h3>
            <Plot
            data={historicalChartData}
            layout={{
                title: { text: `Série Histórica de ${INDICADORES_MAP[detailedIndicator] || detailedIndicator}`, font: { size: 16 } },
                xaxis: { title: 'Ano', type: 'category' }, yaxis: { title: 'Valor' },
                autosize: true, margin: { t: 40, b: 40, l: 60, r: 20 }, legend: { orientation: 'h', y: -0.2 }
            }}
            config={{ responsive: true, displayModeBar: false }}
            className="w-full h-full"
            />
            </div>
            </div>
            </>
        ) : (
            <p className="text-center p-4 text-gray-700">Selecione um município para iniciar a análise.</p>
        )}
        </div>
    );
};

export default AnalisePorMunicipioTabContent;
