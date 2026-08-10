// src/components/charts/RankingMunicipiosEstado.jsx

import React, { useMemo } from 'react';
import Plot from 'react-plotly.js';
import { INDICADORES_MAP } from '../../config/indicadores';

const RankingMunicipiosEstado = ({ data, selectedIndicator, rankingType, selectedYear, ufConfig }) => {

    // Adicione este console.log para ver os dados que o Ranking recebe
    console.log("RankingMunicipiosEstado - Dados recebidos:", data.length, "itens. Indicador:", selectedIndicator, "Ano:", selectedYear);
    console.log("RankingMunicipiosEstado - Exemplo de dado:", data.slice(0, 5));


    const chartData = useMemo(() => {
        if (!data || data.length === 0 || !selectedIndicator || !rankingType) {
            console.warn("Ranking: Dados, indicador, tipo de ranking ou ano ausentes para plotagem.");
            return [];
        }

        // Filtra dados para garantir que o indicador selecionado tem um valor válido
        const sortedData = [...data]
        .filter(item => item[selectedIndicator] !== undefined && item[selectedIndicator] !== null && !isNaN(item[selectedIndicator]))
        .sort((a, b) => {
            // Ajuste a lógica de ordenação se "melhor" significa valores maiores para alguns indicadores
            if (rankingType === 'melhores') {
                // Para indicadores onde "melhor" é um valor MENOR (ex: Mortalidade), use a - b
                // Para indicadores onde "melhor" é um valor MAIOR (ex: Cobertura), use b - a (inverter)
                // Você pode precisar de um mapa de "direção" do indicador para isso
                return a[selectedIndicator] - b[selectedIndicator]; // Crescente para 'melhores' (para TMI, menor é melhor)
            } else {
                return b[selectedIndicator] - a[selectedIndicator]; // Decrescente para 'piores' (para TMI, maior é pior)
            }
        });

        console.log("Ranking: Dados após filtragem e ordenação (amostra):", sortedData.slice(0, 5));
        console.log("Ranking: Total de dados válidos para ranking:", sortedData.length);


        const topN = 15;
        const slicedData = sortedData.slice(0, topN);

        if (slicedData.length === 0) {
            console.warn("Ranking: Nenhum dado válido após ordenação e seleção dos top N.");
            return [];
        }

        const municipalities = slicedData.map(item => item.nome_mun || item.municipio).reverse(); // Use item.municipio como fallback
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
    }, [data, selectedIndicator, rankingType, selectedYear]); // selectedYear adicionado para dependência

    const chartTitle = useMemo(() => {
        const indicatorLabel = INDICADORES_MAP[selectedIndicator] || selectedIndicator;
        const rankingText = rankingType === 'melhores' ? 'Melhores' : 'Piores';
        const ufName = ufConfig?.nome || 'Estado';
        return `${rankingText} Municípios em ${indicatorLabel} (${ufName} - ${selectedYear})`;
    }, [selectedIndicator, rankingType, ufConfig, selectedYear]);


    if (!chartData || chartData.length === 0) return <p className="text-gray-600 text-center mt-4">Dados insuficientes ou inválidos para gerar o ranking.</p>;

    return (
        <div className="bg-white p-4 rounded-lg shadow-md h-[500px] flex flex-col justify-center items-center">
        <Plot
        data={chartData}
        layout={{
            title: {
                text: chartTitle,
                font: { size: 18, color: '#333' },
            },
            xaxis: {
                title: INDICADORES_MAP[selectedIndicator] || selectedIndicator || 'Valor do Indicador',
                automargin: true,
            },
            yaxis: {
                title: 'Município',
                automargin: true,
                tickangle: -45,
            },
            margin: { t: 60, b: 80, l: 150, r: 30 },
            autosize: true,
        }}
        config={{ responsive: true, displayModeBar: false }}
        className="w-full h-full"
        />
        </div>
    );
};

export default RankingMunicipiosEstado;
