// src/components/charts/HistoricoIndicadorEstado.jsx

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { INDICADORES_MAP } from '../../config/indicadores';

const HistoricoIndicadorEstado = ({ data, selectedIndicator, selectedMunicipalities, ufConfig }) => {

    // Adicione este console.log para ver os dados que HistoricoIndicadorEstado recebe
    console.log("HistoricoIndicadorEstado - Dados recebidos:", data.length, "itens. Indicador:", selectedIndicator);
    console.log("HistoricoIndicadorEstado - Exemplo de dado:", data.slice(0, 5));


    const plotData = useMemo(() => {
        if (!data || data.length === 0 || !selectedIndicator) return [];

        const traces = [];

        const stateAverages = {};
        data.forEach(item => {
            // Use item.ANO, pois já vem do backend como float/int
            if (item.ANO !== undefined && item.ANO !== null &&
                item[selectedIndicator] !== undefined && item[selectedIndicator] !== null) {
                if (!stateAverages[item.ANO]) { // Use item.ANO aqui
                    stateAverages[item.ANO] = { sum: 0, count: 0 };
                }
                stateAverages[item.ANO].sum += item[selectedIndicator]; // Use item.ANO aqui
                stateAverages[item.ANO].count += 1; // Use item.ANO aqui
                }
        });

        // Garante que apenas anos com dados sejam usados
        const years = Object.keys(stateAverages).filter(year => stateAverages[year].count > 0).sort();
        const avgValues = years.map(year => stateAverages[year].sum / stateAverages[year].count);

        if (years.length === 0) {
            console.warn("HistoricoIndicadorEstado - Nenhum dado válido para média estadual.");
            return [];
        }

        traces.push({
            x: years,
            y: avgValues,
            mode: 'lines+markers',
            name: 'Média Estadual',
            marker: { color: 'blue' },
            hovertemplate: 'Ano: %{x}<br>Média Estadual: %{y:.2f}<extra></extra>',
        });

        if (selectedMunicipalities && selectedMunicipalities.length > 0) {
            selectedMunicipalities.forEach(mun => {
                const munData = data.filter(item => item.cod_mun_ibge_7 === mun.cod_mun_ibge_7);
                const munYears = munData.map(item => item.ANO).filter(year => typeof year === 'number' && year !== null).sort(); // Use item.ANO
                const munValues = munYears.map(year => {
                    const item = munData.find(d => d.ANO === year); // Use d.ANO
                    return item ? item[selectedIndicator] : null;
                });

                if (munYears.length > 0) { // Adicionado check para ter certeza que há dados para o município
                    traces.push({
                        x: munYears,
                        y: munValues,
                        mode: 'lines+markers',
                        name: mun.nome_mun,
                        marker: { size: 6 },
                        line: { dash: 'dot' },
                        hovertemplate: `Município: ${mun.nome_mun}<br>Ano: %{x}<br>Valor: %{y:.2f}<extra></extra>`,
                    });
                }
            });
        }

        return traces;
    }, [data, selectedIndicator, selectedMunicipalities]);

    const chartTitle = useMemo(() => {
        const indicatorLabel = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
        const ufName = ufConfig?.nome || 'Estado';
        return `Série Histórica de ${indicatorLabel} (${ufName})`;
    }, [selectedIndicator, ufConfig]);

    // O guarda de renderização deve ser mais informativo
    if (!plotData || plotData.length === 0) return <p className="text-gray-600 text-center mt-4">Dados insuficientes ou inválidos para gerar a série histórica.</p>;

    return (
        <div className="bg-white p-4 rounded-lg shadow-md h-[400px] flex flex-col justify-center items-center">
        <Plot
        data={plotData}
        layout={{
            title: {
                text: chartTitle,
                font: { size: 18, color: '#333' },
            },
            xaxis: {
                title: 'Ano',
                type: 'category',
                automargin: true,
            },
            yaxis: {
                title: INDICADORES_MAP[selectedIndicator] || selectedIndicator || 'Valor do Indicador', // Fallback se INDICADORES_MAP[selectedIndicator] for undefined
                automargin: true,
            },
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

export default HistoricoIndicadorEstado;
