// src/components/charts/RadarChartComponent.jsx

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { INDICADORES_MAP } from '../../config/indicadores'; // Para rótulos amigáveis

// Cores para os Perfis (deve ser consistente com o backend e arquétipos)
const MAPA_CORES_PERFIS = {
    "Vulnerabilidade Social/Sanitária": "#d73027",
    "Sobrecarga de Doenças Crônicas": "#fc8d59",
    "Atenção Primária Insuficiente": "#4575b4",
    "Atenção Primária Efetiva": "#1a9850",
    "Perfil Desconhecido": "#cccccc"
};

const RadarChartComponent = ({ data, selectedYear, featuresForClustering }) => {
    // data: Array de objetos JS, já filtrado por UF em KMeansPerfisSaudePage
    // selectedYear: ano principal selecionado
    // featuresForClustering: lista de strings de indicadores que foram usados no agrupamento (ex: ['TMI', 'TAXA_MEDICOS'])

    const plotData = useMemo(() => {
        console.log("DEBUG RADAR: Recalculando plotData para gráfico radar...");
        console.log("DEBUG RADAR: Dados de entrada (data) count:", data?.length, "selectedYear:", selectedYear);
        console.log("DEBUG RADAR: featuresForClustering:", featuresForClustering);

        if (!data || data.length === 0 || !selectedYear || !featuresForClustering || featuresForClustering.length === 0) {
            console.log("DEBUG RADAR: Condições iniciais para plotData do radar não atendidas. Retornando null.");
            return null;
        }

        const df_ano = data.filter(item => item.ANO === selectedYear);
        if (df_ano.length === 0) {
            console.log("DEBUG RADAR: Nenhum dado para o ano selecionado. Retornando null.");
            return null;
        }

        // Identifica os indicadores numéricos que realmente existem e são números válidos no DataFrame filtrado
        const indicators = featuresForClustering.filter(ind => df_ano.some(row => typeof row[ind] === 'number' && !isNaN(row[ind])));

        if (!indicators || indicators.length === 0) {
            console.log("DEBUG RADAR: Nenhuma coluna de indicador numérica válida encontrada para o radar entre as featuresForClustering. Retornando null.");
            return null;
        }

        // --- Implementação manual de StandardScaler (Padronização) em JavaScript ---
        // Calcula média e desvio padrão para cada indicador
        const means = {};
        const stds = {};
        indicators.forEach(ind => {
            const values = df_ano.map(item => item[ind]).filter(val => typeof val === 'number' && !isNaN(val));
            if (values.length > 0) {
                const mean = values.reduce((a, b) => a + b, 0) / values.length;
                const sumOfSquaredDiffs = values.map(val => (val - mean) ** 2).reduce((a, b) => a + b, 0);
                const std = Math.sqrt(sumOfSquaredDiffs / values.length); // População std dev
                means[ind] = mean;
                stds[ind] = std === 0 ? 1 : std; // Evitar divisão por zero
            } else {
                means[ind] = 0;
                stds[ind] = 1;
            }
        });

        // Aplica a padronização aos dados do ano
        const df_scaled_js = df_ano.map(item => {
            const scaledItem = { ...item };
            indicators.forEach(ind => {
                if (typeof item[ind] === 'number' && !isNaN(item[ind])) {
                    scaledItem[ind] = (item[ind] - means[ind]) / stds[ind];
                } else {
                    scaledItem[ind] = 0; // Default para valores não-numéricos/NaN após coerção
                }
            });
            return scaledItem;
        });

        // --- Implementação manual de GroupBy (Agrupamento por perfil) ---
        const groupedByProfile = {};
        df_scaled_js.forEach(item => {
            const perfil = item.perfil;
            if (!groupedByProfile[perfil]) {
                groupedByProfile[perfil] = { count: 0, sums: {} };
                indicators.forEach(ind => groupedByProfile[perfil].sums[ind] = 0); // Inicializa somas
            }
            groupedByProfile[perfil].count++;
            indicators.forEach(ind => {
                // Certifica-se de somar apenas números válidos
                if (typeof item[ind] === 'number' && !isNaN(item[ind])) {
                    groupedByProfile[perfil].sums[ind] += item[ind];
                }
            });
        });

        const perfil_medias = [];
        Object.keys(groupedByProfile).forEach(perfil => {
            const row = { perfil: perfil };
            indicators.forEach(ind => {
                row[ind] = groupedByProfile[perfil].sums[ind] / groupedByProfile[perfil].count;
            });
            perfil_medias.push(row);
        });
        console.log("DEBUG RADAR: Médias por Perfil (Padronizadas):", perfil_medias);


        const traces = [];
        perfil_medias.forEach(row => {
            const perfil_name = row.perfil;
            const r_values = indicators.map(ind => row[ind]);

            // Adiciona o primeiro valor ao final para fechar o círculo do radar
            const r_values_closed = [...r_values, r_values[0]];
            const theta_values = indicators.map(ind => INDICADORES_MAP[ind] || ind); // Rótulos amigáveis
            const theta_values_closed = [...theta_values, theta_values[0]]; // Fecha o círculo

            traces.push({
                type: 'scatterpolar',
                r: r_values_closed,
                theta: theta_values_closed,
                fill: 'toself',
                name: perfil_name,
                marker: {
                    color: MAPA_CORES_PERFIS[perfil_name] || '#cccccc' // Usa a cor do perfil
                },
                hovertemplate: `<b>Perfil: ${perfil_name}</b><br>%{theta}: %{r:.2f}<extra></extra>`
            });
        });
        console.log("DEBUG RADAR: Gráfico radar plotData gerado:", traces);
        return traces;

    }, [data, selectedYear, featuresForClustering]); // Dependências

    const layout = useMemo(() => {
        return {
            polar: {
                radialaxis: {
                    visible: true,
                    range: [-2.5, 2.5] // Ajuste o range conforme a escala padronizada
                }
            },
            showlegend: true,
            title: `Características dos Perfis (Valores Padronizados) - ${selectedYear}`,
                           title_x: 0.5,
                           font: { family: "Open Sans, sans-serif" }, // Fonte padrão para Plotly
                           autosize: true,
                           margin: { t: 60, b: 60, l: 60, r: 60 }
        };
    }, [selectedYear]);

    if (!plotData) {
        return <p className="text-gray-600 text-center mt-4">Dados insuficientes para o gráfico de radar. Verifique os filtros e indicadores.</p>;
    }

    return (
        <div className="bg-white p-4 rounded-lg shadow-md w-full h-[600px] flex flex-col justify-center items-center">
        <Plot
        data={plotData}
        layout={layout}
        config={{ responsive: true, displayModeBar: false }}
        className="w-full h-full"
        />
        </div>
    );
};

export default RadarChartComponent;
