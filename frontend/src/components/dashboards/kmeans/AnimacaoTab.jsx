// src/components/dashboards/kmeans/AnimacaoTab.jsx

import React, { useState, useMemo, useEffect, useRef } from 'react';
import Plot from 'react-plotly.js';
import { UF_CONFIGS } from '../../../config/ufConfigs';
import { FiPlay, FiPause } from 'react-icons/fi';

const AnimacaoTab = ({ allData, availableUfs, availableYears }) => {
    // ⭐ ESTADO INICIAL ATUALIZADO PARA NÃO USAR 'BR' ⭐
    const [selectedUf, setSelectedUf] = useState('');
    const [geojson, setGeojson] = useState(null);
    const [loadingMap, setLoadingMap] = useState(false);

    const [isPlaying, setIsPlaying] = useState(false);
    const [animationYear, setAnimationYear] = useState(availableYears.length > 0 ? availableYears[0] : null);
    const intervalRef = useRef(null);

    const ufConfig = UF_CONFIGS[selectedUf];
    const sortedYears = useMemo(() => [...availableYears].sort((a, b) => a - b), [availableYears]);

    // ⭐ EFEITO PARA DEFINIR O ESTADO INICIAL QUANDO OS DADOS CHEGAREM ⭐
    useEffect(() => {
        if (availableUfs.length > 0 && !selectedUf) {
            setSelectedUf(availableUfs[0]);
        }
    }, [availableUfs, selectedUf]);

    useEffect(() => {
        if (!selectedUf) return;
        const fetchGeojson = async () => {
            setLoadingMap(true);
            const url = ufConfig?.ibgePrefix ? `/geojson_uf/geojs-${ufConfig.ibgePrefix}-mun.json` : null;
            if (!url) {
                setLoadingMap(false);
                return;
            }
            try {
                const response = await fetch(url);
                if (!response.ok) throw new Error("Arquivo GeoJSON não encontrado.");
                const data = await response.json();
                setGeojson(data);
            } catch (error) {
                console.error(`Erro ao carregar GeoJSON para ${selectedUf}:`, error);
            } finally {
                setLoadingMap(false);
            }
        };
        fetchGeojson();
    }, [selectedUf, ufConfig]);

    useEffect(() => {
        if (isPlaying && sortedYears.length > 1) {
            intervalRef.current = setInterval(() => {
                setAnimationYear(prevYear => {
                    const currentIndex = sortedYears.indexOf(prevYear);
                    const nextIndex = (currentIndex + 1) % sortedYears.length;
                    return sortedYears[nextIndex];
                });
            }, 1500);
        } else {
            clearInterval(intervalRef.current);
        }
        return () => clearInterval(intervalRef.current);
    }, [isPlaying, sortedYears]);

    const mapData = useMemo(() => {
        if (!geojson || !allData.length || animationYear == null) return null;
        const allUniqueProfiles = [...new Set(allData.map(item => item.perfil).filter(Boolean))].sort();
        const colorsMap = new Map();
        allUniqueProfiles.forEach(profile => {
            const itemWithColor = allData.find(item => item.perfil === profile && item.cor);
            colorsMap.set(profile, itemWithColor ? itemWithColor.cor : '#cccccc');
        });
        const zMapping = Object.fromEntries(allUniqueProfiles.map((p, i) => [p, i]));

        let dataToPlot = allData.filter(item => item.ANO === animationYear && item.UF === selectedUf);

        const choroplethTrace = {
            type: 'choropleth',
            geojson: geojson,
            locations: dataToPlot.map(d => String(d.cod_mun_ibge_7)),
                            z: dataToPlot.map(d => zMapping[d.perfil]),
                            featureidkey: 'properties.id',
                            text: dataToPlot.map(d => d.nome_mun || d.municipio),
                            hoverinfo: 'text',
                            customdata: dataToPlot.map(d => d.perfil),
                            hovertemplate: '<b>%{text}</b><br>Perfil: %{customdata}<extra></extra>',
                            colorscale: allUniqueProfiles.map((p, i) => [i / (allUniqueProfiles.length - 1 || 1), colorsMap.get(p)]),
                            showscale: false,
                            showlegend: false,
        };
        const legendTraces = [];
        colorsMap.forEach((color, profileName) => {
            legendTraces.push({
                x: [null], y: [null], type: 'scatter', mode: 'markers',
                marker: { color: color, size: 10 },
                name: profileName,
                xaxis: 'x2',
                yaxis: 'y2'
            });
        });
        return [choroplethTrace, ...legendTraces];
    }, [geojson, allData, animationYear, selectedUf]);

    const currentYearIndex = sortedYears.indexOf(animationYear);

    return (
        <div>
        <h2 className="text-2xl font-semibold text-gray-700 mb-4">Evolução Temporal dos Perfis</h2>
        <div className="flex flex-wrap gap-4 items-center justify-center mb-4">
        <label className="flex flex-col">Estado (UF):
        <select value={selectedUf} onChange={(e) => setSelectedUf(e.target.value)} className="p-2 border rounded-md">
        {/* ⭐ OPÇÃO BRASIL REMOVIDA DAQUI ⭐ */}
        {availableUfs.map(ufCode => (<option key={ufCode} value={ufCode}>{ufCode}</option>))}
        </select>
        </label>
        </div>

        <div className="flex items-center justify-center gap-4 my-4">
        <button onClick={() => setIsPlaying(!isPlaying)} className="p-3 bg-blue-600 text-white rounded-full hover:bg-blue-700 transition-colors disabled:opacity-50" disabled={sortedYears.length < 2}>
        {isPlaying ? <FiPause size={20}/> : <FiPlay size={20}/>}
        </button>
        <span className="font-semibold text-gray-700">{sortedYears[0]}</span>
        <input
        type="range"
        min="0"
        max={sortedYears.length > 0 ? sortedYears.length - 1 : 0}
        value={currentYearIndex >= 0 ? currentYearIndex : 0}
        onChange={(e) => setAnimationYear(sortedYears[parseInt(e.target.value, 10)])}
        className="w-1/2"
        disabled={sortedYears.length < 2}
        />
        <span className="font-semibold text-gray-700">{sortedYears.length > 0 ? sortedYears[sortedYears.length - 1] : ''}</span>
        </div>
        <h3 className="text-center text-3xl font-bold text-gray-800 mb-2">{animationYear}</h3>

        <div className="h-[600px]">
        {loadingMap ? <p className='flex items-center justify-center h-full'>Carregando mapa...</p> :
            (mapData ?
            <Plot
            data={mapData}
            layout={{
                geo: { scope: 'south america', fitbounds: 'locations', visible: false },
                margin: { t: 0, b: 40, l: 0, r: 0 },
                legend: { orientation: 'h', yanchor: 'bottom', y: -0.1, xanchor: 'center', x: 0.5 },
                xaxis2: { visible: false, range: [0, 1] },
                yaxis2: { visible: false, range: [0, 1] }
            }}
            config={{ responsive: true, displayModeBar: false }}
            className="w-full h-full"
            />
            : <p className="flex items-center justify-center h-full">Nenhum dado para exibir no mapa para o ano de {animationYear}.</p>)}
            </div>
            </div>
    );
};

export default AnimacaoTab;
