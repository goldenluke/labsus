// src/components/charts/HistogramaIndicadorEstado.jsx

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { INDICADORES_MAP } from '../../config/indicadores';

const HistogramaIndicadorEstado = ({ data, selectedIndicator, selectedMunicipality, selectedYear, ufConfig }) => {

    // ADICIONEI ESTES CONSOLE.LOGS PARA DEPURAR OS DADOS RECEBIDOS
    console.log(`--- HistogramaIndicadorEstado Debug ---`);
    console.log("Props data:", data ? data.length + " itens" : "nulo/vazio");
    if (data && data.length > 0) {
        console.log("Primeiro item de data (Histograma):", data[0]);
    }
    console.log("Selected Indicator (Histograma):", selectedIndicator);
    console.log("Selected Year (Histograma):", selectedYear);
    console.log("---------------------------------------");


    const plotData = useMemo(() => {
        if (!data || data.length === 0 || !selectedIndicator) {
            console.warn("Histograma: Condições iniciais para useMemo não atendidas. Retornando vazio.");
            return [];
        }

        // `data` já vem filtrada por UF e Ano de AnalisePorEstadoPage.jsx (é `ufDataFilteredByYear`)
        const values = data.map(item => item[selectedIndicator]).filter(v => v !== undefined && v !== null && !isNaN(v));

        console.log("Histograma: Valores filtrados para plotagem (amostra):", values.length, values.slice(0, 10));
        console.log("Histograma: Total de valores para plotagem:", values.length);


        if (values.length === 0) {
            console.warn("Histograma: Nenhum valor numérico válido encontrado para o indicador selecionado no ano e UF filtrados. Retornando vazio.");
            return [];
        }

        let traces = [{
            x: values,
            type: 'histogram',
            marker: { color: 'rgba(58, 137, 187, 0.7)' },
                             nbinsx: Math.min(20, Math.max(5, Math.ceil(values.length / 10))),
                             name: INDICADORES_MAP[selectedIndicator] || selectedIndicator,
                             hovertemplate: 'Intervalo: %{x}<br>Frequência: %{y}<extra></extra>',
        }];

        // Adiciona uma linha vertical para um município específico, se selecionado
        if (selectedMunicipality) {
            const munData = data.find(item => item.cod_mun_ibge_7 === selectedMunicipality.cod_mun_ibge_7);
            if (munData && munData[selectedIndicator] !== undefined && munData[selectedIndicator] !== null && !isNaN(munData[selectedIndicator])) {
                traces.push({
                    x: [munData[selectedIndicator], munData[selectedIndicator]],
                    // A altura Y precisa ser ajustada dinamicamente com base na altura máxima dos bins.
                    // Para simplificar, usamos um valor fixo alto, mas pode ser impreciso.
                    y: [0, 100], // Valor arbitrário, pode precisar de ajuste manual ou cálculo mais complexo
                    mode: 'lines',
                    type: 'scatter',
                    name: `Valor de ${selectedMunicipality.nome}`,
                    marker: { color: 'red' },
                    line: { dash: 'dot', width: 2 },
                    hoverinfo: 'text',
                    text: `${selectedMunicipality.nome}: ${munData[selectedIndicator]}`,
                    showlegend: true,
                });
            } else {
                console.warn(`Histograma: Município selecionado (${selectedMunicipality.nome}) não tem dados válidos para o indicador ${selectedIndicator}.`);
            }
        }
        return traces;
    }, [data, selectedIndicator, selectedMunicipality]); // selectedYear removido pois 'data' já é filtrada por ano

    const chartTitle = useMemo(() => {
        const indicatorLabel = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
        const ufName = ufConfig?.nome || 'Estado';
        return `Distribuição de ${indicatorLabel}<br>por Município em ${ufName} (${selectedYear})`;
    }, [selectedIndicator, ufConfig, selectedYear]);

    // Guarda de renderização mais específica para feedback ao usuário
    if (!plotData || plotData.length === 0) {
        console.warn("HistogramaIndicadorEstado: plotData final está vazio. Exibindo mensagem de dados insuficientes.");
        return <p className="text-gray-600 text-center mt-4">Dados insuficientes ou inválidos para gerar este gráfico.</p>;
    }

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
                title: INDICADORES_MAP[selectedIndicator] || selectedIndicator || 'Valor',
                automargin: true,
            },
            yaxis: {
                title: 'Frequência',
                automargin: true,
            },
            margin: { t: 60, b: 60, l: 60, r: 30 },
            autosize: true,
            hovermode: 'closest',
        }}
        config={{ responsive: true, displayModeBar: false }}
        className="w-full h-full"
        />
        </div>
    );
};

export default HistogramaIndicadorEstado;
