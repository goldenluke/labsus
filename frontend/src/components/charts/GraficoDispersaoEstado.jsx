// src/components/charts/GraficoDispersaoEstado.jsx

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { INDICADORES_MAP } from '../../config/indicadores';

const GraficoDispersaoEstado = ({ data, scatterX, scatterY, selectedYear, ufConfig }) => {

    // Adicione este console.log para ver os dados que o Gráfico de Dispersão recebe
    console.log("GraficoDispersaoEstado - Dados recebidos:", data.length, "itens. Eixo X:", scatterX, "Eixo Y:", scatterY, "Ano:", selectedYear);
    console.log("GraficoDispersaoEstado - Exemplo de dado:", data.slice(0, 5));


    const plotData = useMemo(() => {
        if (!data || data.length === 0 || !scatterX || !scatterY) {
            console.warn("Dispersão: Dados, eixos X/Y ausentes para plotagem.");
            return [];
        }

        // Agrupa dados por 'perfil' (se existir)
        const groupedData = data.reduce((acc, item) => {
            // Garante que o perfil seja uma string (ou "Desconhecido")
            const profile = item.perfil ? String(item.perfil) : 'Desconhecido';
        if (!acc[profile]) {
            acc[profile] = [];
        }
        // Garante que ambos os valores dos indicadores para dispersão sejam numéricos e válidos
        if (item[scatterX] !== undefined && item[scatterX] !== null && !isNaN(item[scatterX]) &&
            item[scatterY] !== undefined && item[scatterY] !== null && !isNaN(item[scatterY])) {
            acc[profile].push(item);
            } else {
                console.warn(`Dispersão: Item ignorado devido a valores inválidos. Mun: ${item.municipio || item.nome_mun}, X: ${item[scatterX]}, Y: ${item[scatterY]}`);
            }
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
                                                                    return `${item.nome_mun || item.municipio}<br>${xLabel}: ${item[scatterX]}<br>${yLabel}: ${item[scatterY]}`;
                                                                }),
                                                                hoverinfo: 'text',
                                                                marker: { size: 8, opacity: 0.7 },
        }));

        console.log("Dispersão: Total de traces gerados:", traces.length);
        // Verifique se todos os traces estão vazios
        const hasValidTraces = traces.some(trace => trace.x.length > 0);
        if (!hasValidTraces) {
            console.warn("Dispersão: Todos os traces estão vazios após a filtragem por valores válidos.");
            return [];
        }

        return traces;
    }, [data, scatterX, scatterY, selectedYear]); // selectedYear adicionado para dependência

    const chartTitle = useMemo(() => {
        const xLabel = INDICADORES_MAP[scatterX] || scatterX;
        const yLabel = INDICADORES_MAP[scatterY] || scatterY;
        const ufName = ufConfig?.nome || 'Estado';
        return `Correlação entre ${xLabel} e ${yLabel} (${ufName} - ${selectedYear})`;
    }, [scatterX, scatterY, ufConfig, selectedYear]);

    if (!plotData || plotData.length === 0) return <p className="text-gray-600 text-center mt-4">Dados insuficientes ou inválidos para gerar o gráfico de dispersão.</p>;

    return (
        <div className="bg-white p-4 rounded-lg shadow-md h-[500px] flex flex-col justify-center items-center">
        <Plot
        data={plotData}
        layout={{
            title: {
                text: chartTitle,
                font: { size: 18, color: '#333' },
            },
            xaxis: {
                title: INDICADORES_MAP[scatterX] || scatterX || 'Valor do Eixo X',
                automargin: true,
            },
            yaxis: {
                title: INDICADORES_MAP[scatterY] || scatterY || 'Valor do Eixo Y',
                automargin: true,
            },
            hovermode: 'closest',
            showlegend: true,
            legend: {
                orientation: 'h',
                yanchor: 'bottom',
                y: 1.02,
                xanchor: 'right',
                x: 1
            },
            margin: { t: 60, b: 60, l: 60, r: 30 },
            autosize: true,
        }}
        config={{ responsive: true, displayModeBar: false }}
        className="w-full h-full"
        />
        </div>
    );
};

export default GraficoDispersaoEstado;
