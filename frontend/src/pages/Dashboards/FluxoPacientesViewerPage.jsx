import React, { useState, useEffect, useMemo } from 'react';
import Plot from 'react-plotly.js';
import usePageTitle from '../../hooks/usePageTitle';
import { useFluxoPacientesData } from '../../hooks/useFluxoPacientesData';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';
import { FiDownload, FiRefreshCw } from 'react-icons/fi';
import { UF_CONFIGS } from '../../config/ufConfigs';
import LoadingSpinner from '../../components/common/LoadingSpinner';

// Escala de cor para as linhas (Azul -> Roxo -> Laranja -> Amarelo)
const plasmaColorScale = (value) => {
    const colors = [ [0.0, [13, 8, 135]], [0.1, [70, 3, 163]], [0.2, [118, 0, 168]], [0.3, [160, 20, 146]], [0.4, [195, 56, 120]], [0.5, [222, 92, 91]], [0.6, [241, 130, 63]], [0.7, [252, 169, 40]], [0.8, [252, 208, 26]], [0.9, [240, 249, 23]], [1.0, [255, 255, 255]] ];
    for (let i = 0; i < colors.length - 1; i++) {
        const c1_val = colors[i][0]; const c2_val = colors[i + 1][0];
        if (value >= c1_val && value <= c2_val) {
            const t = (value - c1_val) / (c2_val - c1_val);
            const c1_rgb = colors[i][1]; const c2_rgb = colors[i + 1][1];
            const r = Math.round(c1_rgb[0] * (1 - t) + c2_rgb[0] * t);
            const g = Math.round(c1_rgb[1] * (1 - t) + c2_rgb[1] * t);
            const b = Math.round(c1_rgb[2] * (1 - t) + c2_rgb[2] * t);
            return `rgb(${r},${g},${b})`;
        }
    }
    return `rgb(13, 8, 135)`;
};

const FluxoPacientesViewerPage = () => {
    usePageTitle('Fluxo de Pacientes (por CID)');

    const {
        loading, error, fileDetails, availableFiles, selectedFileId, setSelectedFileId,
        flowData,
        availableUfs,
        rankingData,
        polosSankeyOptions, selectedPolo, setSelectedPolo, sankeyDataAndLayout
    } = useFluxoPacientesData();

    const [ufFiltro, setUfFiltro] = useState('BR');
    const [minPacientesFiltro, setMinPacientesFiltro] = useState(5);
    const [filtrosAplicados, setFiltrosAplicados] = useState(null);

    // Reseta filtros ao trocar arquivo
    useEffect(() => {
        setFiltrosAplicados(null);
        setUfFiltro('BR');
        setMinPacientesFiltro(5);
    }, [selectedFileId]);

    const handleAtualizarMapa = () => {
        setFiltrosAplicados({ uf: ufFiltro, min: minPacientesFiltro });
    };

    const filteredFlowData = useMemo(() => {
        if (!filtrosAplicados || !flowData) return [];
        return flowData.filter(d => d.N_PACIENTES >= filtrosAplicados.min);
    }, [flowData, filtrosAplicados]);

    // --- LÓGICA DO MAPA (Plotly scattermapbox — mesmo padrão visual dos
    // mapas de fluxo mais novos: tiles reais do OpenStreetMap em vez de um
    // contorno SVG cinza, o que deixa o mapa muito mais legível e "bonito"). ---
    const mapPlotData = useMemo(() => {
        if (!filtrosAplicados || !filteredFlowData.length) return null;

        const { uf } = filtrosAplicados;
        const dataForMap = uf === 'BR' ? filteredFlowData : filteredFlowData.filter(d => d.uf_destino === uf || d.uf_origem === uf);

        // Ordena por número de pacientes para que as linhas mais grossas fiquem por cima
        // e limita a 1000 linhas para não sobrecarregar o navegador.
        const validDataForMap = dataForMap
            .filter(d => !isNaN(d.lat_origem) && !isNaN(d.lon_origem) && !isNaN(d.lat_destino) && !isNaN(d.lon_destino))
            .sort((a, b) => a.N_PACIENTES - b.N_PACIENTES)
            .slice(-1000); // Pega os últimos (maiores) 1000 fluxos se houver muitos

        if (validDataForMap.length === 0) return null;

        const vals = validDataForMap.map(d => d.N_PACIENTES).filter(n => n > 0);
        const minVal = Math.min(...vals) || 1;
        const maxVal = Math.max(...vals) || 1;
        const minLog = Math.log(minVal);
        const maxLog = Math.log(maxVal);

        // Arrays para a camada de interação (Pontos Médios Invisíveis)
        const midLons = [];
        const midLats = [];
        const midTexts = [];

        // 1. Camada de Fluxos (Linhas)
        const flowLinesTraces = validDataForMap.map(row => {
            const val = row.N_PACIENTES;
            const logVal = Math.log(val > 0 ? val : 1);
            const ratio = (maxLog - minLog) === 0 ? 0.5 : (logVal - minLog) / (maxLog - minLog);

            // Prepara dados para o ponto médio (Interação)
            const midLon = (row.lon_origem + row.lon_destino) / 2;
            const midLat = (row.lat_origem + row.lat_destino) / 2;
            const hoverText = `<b>Fluxo Intermunicipal</b><br>🛫 Origem: ${row.municipio_origem} (${row.uf_origem})<br>🛬 Destino: ${row.municipio_destino} (${row.uf_destino})<br>👥 Pacientes: <b>${row.N_PACIENTES}</b>`;

            midLons.push(midLon);
            midLats.push(midLat);
            midTexts.push(hoverText);

            return {
                type: 'scattermapbox',
                mode: 'lines',
                lon: [row.lon_origem, row.lon_destino],
                lat: [row.lat_origem, row.lat_destino],
                line: {
                    width: 1 + (ratio * 5),
                    color: plasmaColorScale(ratio),
                },
                hoverinfo: 'skip', // Desativa hover na linha (difícil de acertar)
                opacity: 0.75,
                showlegend: false,
            };
        });

        // 2. Camada de Interação (Pontos Médios Invisíveis)
        const interactionTrace = {
            type: 'scattermapbox',
            mode: 'markers',
            lon: midLons,
            lat: midLats,
            text: midTexts,
            hoverinfo: 'text',
            marker: {
                size: 15, // Hitbox grande
                color: 'transparent', // Invisível
                opacity: 0,
            },
            showlegend: false,
            name: 'Info Fluxo',
        };

        // 3. Camada de Cidades (Pontos Visíveis nas extremidades)
        const cityMap = new Map();
        validDataForMap.forEach(d => {
             cityMap.set(d.municipio_origem, {lat: d.lat_origem, lon: d.lon_origem, nome: d.municipio_origem, uf: d.uf_origem});
             cityMap.set(d.municipio_destino, {lat: d.lat_destino, lon: d.lon_destino, nome: d.municipio_destino, uf: d.uf_destino});
        });
        const uniqueCities = Array.from(cityMap.values());

        const cityPointsTrace = {
            type: 'scattermapbox',
            mode: 'markers',
            lon: uniqueCities.map(c => c.lon),
            lat: uniqueCities.map(c => c.lat),
            text: uniqueCities.map(c => `<b>${c.nome}</b> (${c.uf})`),
            marker: { size: 6, color: '#1f2937', opacity: 0.85 },
            hoverinfo: 'text',
            name: 'Municípios',
            showlegend: false,
        };

        // Adiciona a camada de interação POR CIMA das linhas
        return [...flowLinesTraces, cityPointsTrace, interactionTrace];
    }, [filtrosAplicados, filteredFlowData]);

    // Resize de janela único, disparado pouco depois dos dados do mapa
    // ficarem prontos — corrige o mapbox-gl inicializando com tamanho errado
    // logo após uma navegação interna do SPA (ver mesma nota em
    // AnalisePorMunicipioPage.jsx).
    useEffect(() => {
        if (!mapPlotData) return;
        const timer = setTimeout(() => window.dispatchEvent(new Event('resize')), 200);
        return () => clearTimeout(timer);
    }, [mapPlotData]);

    const mapLayout = useMemo(() => {
        const { uf } = filtrosAplicados || { uf: 'BR' };
        const config = UF_CONFIGS[uf] || UF_CONFIGS['BR'];

        return {
            showlegend: false,
            margin: { t: 0, b: 0, l: 0, r: 0 },
            mapbox: {
                style: 'open-street-map',
                center: { lat: config.center.lat, lon: config.center.lon },
                zoom: config.zoom,
            },
            dragmode: 'pan',
            hovermode: 'closest',
            hoverlabel: {
                bgcolor: "#FFF",
                bordercolor: "#888",
                font: { size: 13, color: "#333" }
            }
        };
    }, [filtrosAplicados]);

    if (loading && !fileDetails) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen p-10">
                <LoadingSpinner size="lg" color="blue" />
                <p className="mt-4 text-gray-700">Carregando dados...</p>
            </div>
        );
    }

    if (error) return <FeedbackMessage message={`Erro: ${error}`} type="error" />;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <h1 className="text-3xl text-center text-gray-800 mb-8">Fluxo de Pacientes (por CID)</h1>

            {/* Seletor de Arquivo */}
            <div className="bg-white p-6 rounded-lg shadow-md mb-8">
                 <label className="flex flex-col font-semibold">Selecione o ficheiro de análise:
                    <select 
                        value={selectedFileId} 
                        onChange={e => setSelectedFileId(e.target.value)} 
                        className="p-2 border rounded-md mt-1 font-normal"
                    >
                        <option value="">-- Selecione um ficheiro --</option>
                        {availableFiles.map(file => (
                            <option key={file.id} value={file.id}>{file.filename}</option>
                        ))}
                    </select>
                </label>
            </div>

            {!selectedFileId && !loading && <FeedbackMessage message="Por favor, selecione um ficheiro para começar." type="info" />}

            {selectedFileId && fileDetails && (
                <>
                    <div className="bg-white p-6 rounded-lg shadow-md mb-8 flex flex-col md:flex-row justify-between items-start md:items-center">
                        <div>
                            <h2 className="text-xl font-semibold text-gray-800 mb-2">Ficheiro de Análise:</h2>
                            <p className="text-gray-700 text-sm mb-1"><span className="font-medium">Nome:</span> {fileDetails.filename}</p>
                            <p className="text-gray-700 text-sm mt-2"><span className="font-medium">Parâmetros:</span> {fileDetails.description}</p>
                        </div>
                        <a href={fileDetails.file} download={fileDetails.filename} className="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded inline-flex items-center flex-shrink-0 mt-4 md:mt-0">
                            <FiDownload className="mr-2" /> Baixar CSV
                        </a>
                    </div>

                    <InfoCard title="Mapa de Fluxo Intermunicipal">
                        <p>O mapa exibe as rotas de deslocamento de pacientes. <strong>Passe o mouse sobre o meio das linhas coloridas</strong> para ver os detalhes do fluxo (Origem, Destino e Quantidade).</p>
                    </InfoCard>
                    
                    <div className="bg-white p-4 rounded-lg shadow-md w-full mt-4">
                        <div className="flex flex-wrap gap-4 p-4 items-center">
                            <label className="flex flex-col font-semibold">Focar em UF:
                                <select value={ufFiltro} onChange={e => setUfFiltro(e.target.value)} className="p-2 border rounded-md mt-1 font-normal">
                                    {availableUfs.map(uf => <option key={uf} value={uf}>{uf}</option>)}
                                </select>
                            </label>
                            <label className="flex flex-col font-semibold w-full max-w-xs">Mínimo de Pacientes: {minPacientesFiltro}
                                <input type="range" min="1" max="100" step="1" value={minPacientesFiltro} onChange={e => setMinPacientesFiltro(parseInt(e.target.value, 10))} className="w-full" />
                            </label>
                            <button
                                onClick={handleAtualizarMapa}
                                className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg inline-flex items-center shadow-md transition-opacity disabled:opacity-50"
                            >
                                <FiRefreshCw className="mr-2" />
                                Atualizar Visualização
                            </button>
                        </div>

                        <div className="h-[600px] w-full">
                            {filtrosAplicados ? (
                                mapPlotData ?
                                    <Plot
                                        key={`${selectedFileId}-${JSON.stringify(filtrosAplicados)}`}
                                        data={mapPlotData}
                                        layout={mapLayout}
                                        config={{ responsive: true, displayModeBar: true, scrollZoom: true }}
                                        className="w-full h-full"
                                    />
                                    : <div className="flex flex-col items-center justify-center h-full text-gray-500">
                                        <p className="text-lg font-semibold">Sem dados de fluxo para exibir com os filtros aplicados.</p>
                                        <p className="text-sm">Tente reduzir o mínimo de pacientes ou mudar a UF.</p>
                                      </div>
                            ) : (
                                <div className="flex items-center justify-center h-full bg-gray-100 rounded-md">
                                    <p className="text-gray-500">Ajuste os filtros e clique em "Atualizar Visualização" para gerar o mapa.</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* SEÇÃO INFERIOR: RANKING E SANKEY */}
                    {filtrosAplicados && (
                        <>
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
                                <div className="space-y-4">
                                    <InfoCard title="Principais Polos de Atendimento">
                                        <p>Municípios que mais receberam pacientes de outras cidades (Top 10).</p>
                                    </InfoCard>
                                    <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
                                        {rankingData.polos.length > 0 ? 
                                            <Plot 
                                                data={[{ 
                                                    x: rankingData.polos.map(p => p[1]), 
                                                    y: rankingData.polos.map(p => p[0]), 
                                                    type: 'bar', 
                                                    orientation: 'h' 
                                                }]} 
                                                layout={{ 
                                                    title: 'Top 10 Destinos (Polos)', 
                                                    yaxis: { autorange: 'reversed', automargin: true }, 
                                                    xaxis: {title: 'Nº Pacientes'} 
                                                }} 
                                                config={{ responsive: true }} 
                                                className="w-full h-full" 
                                            />
                                        : <p className="text-center pt-20">Sem dados de Ranking para exibir.</p>}
                                    </div>
                                </div>
                                <div className="space-y-4">
                                    <InfoCard title="Principais Municípios de Origem">
                                        <p>Municípios que mais enviaram pacientes para fora (Top 10).</p>
                                    </InfoCard>
                                    <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
                                        {rankingData.enviadores.length > 0 ?
                                            <Plot 
                                                data={[{ 
                                                    x: rankingData.enviadores.map(p => p[1]), 
                                                    y: rankingData.enviadores.map(p => p[0]), 
                                                    type: 'bar', 
                                                    orientation: 'h', 
                                                    marker: {color: '#ff7f0e'} 
                                                }]} 
                                                layout={{ 
                                                    title: 'Top 10 Origens', 
                                                    yaxis: { autorange: 'reversed', automargin: true }, 
                                                    xaxis: {title: 'Nº Pacientes'} 
                                                }} 
                                                config={{ responsive: true }} 
                                                className="w-full h-full" 
                                            />
                                        : <p className="text-center pt-20">Sem dados de Ranking para exibir.</p>}
                                    </div>
                                </div>
                            </div>

                            <div className="mt-8 space-y-4">
                                <InfoCard title="Detalhamento de Fluxo (Sankey)">
                                    <p>Selecione um polo abaixo para ver a origem exata dos seus pacientes.</p>
                                </InfoCard>
                                <div className="bg-white p-4 rounded-lg shadow-md w-full">
                                    <label className="flex flex-col font-semibold max-w-sm mx-auto mb-4">
                                        Selecione um Polo:
                                        <select 
                                            value={selectedPolo} 
                                            onChange={e => setSelectedPolo(e.target.value)} 
                                            className="p-2 border rounded-md mt-1 font-normal"
                                        >
                                            {polosSankeyOptions.map(polo => <option key={polo} value={polo}>{polo}</option>)}
                                        </select>
                                    </label>
                                    {sankeyDataAndLayout ?
                                        <Plot
                                            data={sankeyDataAndLayout.plotData}
                                            layout={sankeyDataAndLayout.layout}
                                            config={{ responsive: true }}
                                            className="w-full"
                                        />
                                        : <div className="h-[300px] flex items-center justify-center text-gray-500">
                                            Selecione um polo válido acima.
                                          </div>
                                    }
                                </div>
                            </div>
                        </>
                    )}
                </>
            )}
        </div>
    );
};

export default FluxoPacientesViewerPage;