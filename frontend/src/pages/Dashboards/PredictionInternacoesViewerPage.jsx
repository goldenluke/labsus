// src/pages/predictions/PredictionInternacoesViewerPage.jsx

import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';
import { FiDownload } from 'react-icons/fi';
import { useLocation } from 'react-router-dom';

import DashboardLayout from '../../components/layout/DashboardLayout';
import InfoCard from '../../components/common/InfoCard';

const PredictionInternacoesViewerPage = () => {
    const location = useLocation();

    const queryParams = useMemo(
        () => new URLSearchParams(location.search),
                                [location.search]
    );

    const fileIdFromUrl = queryParams.get('fileId');

    const [predictionData, setPredictionData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedFileUrl, setSelectedFileUrl] = useState(null);
    const [fileDetails, setFileDetails] = useState(null);

    useEffect(() => {
        const fetchPredictionData = async () => {
            if (!fileIdFromUrl) {
                setError(
                    'Nenhum arquivo de previsão selecionado para visualização.'
                );
                setLoading(false);
                return;
            }

            setLoading(true);
            setError(null);

            try {
                const token = localStorage.getItem('authToken');

                const fileDetailResponse = await axios.get(
                    `/api/files/${fileIdFromUrl}/`,
                    {
                        headers: {
                            Authorization: `Token ${token}`,
                        },
                    }
                );

                setFileDetails(fileDetailResponse.data);
                setSelectedFileUrl(fileDetailResponse.data.file);

                const dataResponse = await axios.get(
                    `/api/files/${fileIdFromUrl}/data/`,
                    {
                        headers: {
                            Authorization: `Token ${token}`,
                        },
                    }
                );

                setPredictionData(dataResponse.data);
            } catch (err) {
                console.error(
                    'Erro ao carregar dados da previsão:',
                    err
                );

                setError(
                    'Não foi possível carregar os dados do arquivo de previsão.'
                );
            } finally {
                setLoading(false);
            }
        };

        fetchPredictionData();
    }, [fileIdFromUrl]);

    const chartTitles = useMemo(() => {
        const baseTitles = {
            main: 'Previsão de Internações',
            trend: 'Tendência de Internações',
            seasonality: 'Sazonalidade Anual de Internações',
        };

        if (!fileDetails) {
            return baseTitles;
        }

        let subtitle = '';

    if (fileDetails.description) {
        const cidMatch =
        fileDetails.description.match(
            /cids:\s*([^.]+)/i
        );

        if (cidMatch && cidMatch[1]) {
            subtitle = `(CID: ${cidMatch[1].trim()})`;
        }
    }

    if (!subtitle && fileDetails.filename) {
        const cleanFileName = fileDetails.filename
        .replace(/_(\d{14})\.csv$/, '')
        .replace(/_/g, ' ');

        subtitle = `(${cleanFileName})`;
    }

    return {
        main: `${baseTitles.main} ${subtitle}`.trim(),
                                trend: `${baseTitles.trend} ${subtitle}`.trim(),
                                seasonality:
                                `${baseTitles.seasonality} ${subtitle}`.trim(),
                                download: `Previsão_${subtitle.replace(
                                    /[()]/g,
                                                                       ''
                                )}.csv`,
    };
    }, [fileDetails]);

    const mainPredictionPlotData = useMemo(() => {
        if (!predictionData) return [];

        const historicalData = predictionData.filter(
            (d) => d.y != null
        );

        const predictionPlotData = predictionData.filter(
            (d) =>
            d.yhat != null &&
            d.yhat_lower != null &&
            d.yhat_upper != null
        );

        return [
            {
                x: predictionPlotData
                .map((d) => new Date(d.ds))
                .concat(
                    predictionPlotData
                    .map((d) => new Date(d.ds))
                    .reverse()
                ),

                y: predictionPlotData
                .map((d) => d.yhat_upper)
                .concat(
                    predictionPlotData
                    .map((d) => d.yhat_lower)
                    .reverse()
                ),

                fill: 'toself',
                fillcolor: 'rgba(0,176,246,0.2)',
                                           line: { color: 'transparent' },
                                           hoverinfo: 'skip',
                                           name: 'Intervalo de Confiança',
            },

            {
                x: predictionPlotData.map(
                    (d) => new Date(d.ds)
                ),
                y: predictionPlotData.map((d) => d.yhat),

                                           mode: 'lines',
                                           line: {
                                               color: 'rgb(0,176,246)',
                                           width: 2,
                                           },

                                           name: 'Previsão',

                                           hovertemplate:
                                           'Data: %{x|%Y-%m-%d}<br>Previsão: %{y:.0f}<extra></extra>',
            },

            {
                x: historicalData.map(
                    (d) => new Date(d.ds)
                ),

                y: historicalData.map((d) => d.y),

                                           mode: 'lines+markers',

                                           marker: {
                                               color: 'black',
                                               size: 4,
                                           },

                                           line: {
                                               width: 2,
                                           },

                                           name: 'Dados Históricos Reais',

                                           hovertemplate:
                                           'Data: %{x|%Y-%m-%d}<br>Internações Reais: %{y}<extra></extra>',
            },
        ];
    }, [predictionData]);

    const trendPlotData = useMemo(() => {
        const relevantData =
        predictionData?.filter(
            (d) => d.trend != null
        );

        if (!relevantData?.length) return [];

        return [
            {
                x: relevantData.map(
                    (d) => new Date(d.ds)
                ),

                y: relevantData.map((d) => d.trend),

                                  mode: 'lines',

                                  name: 'Tendência',

                                  line: {
                                      color: 'orange',
                                      width: 2,
                                  },

                                  hovertemplate:
                                  'Data: %{x|%Y-%m-%d}<br>Tendência: %{y:.0f}<extra></extra>',
            },
        ];
    }, [predictionData]);

    const yearlySeasonalityPlotData = useMemo(() => {
        const relevantData =
        predictionData?.filter(
            (d) => d.yearly != null
        );

        if (!relevantData?.length) return [];

        return [
            {
                x: relevantData.map(
                    (d) => new Date(d.ds)
                ),

                y: relevantData.map((d) => d.yearly),

                                              mode: 'lines',

                                              name: 'Sazonalidade Anual',

                                              line: {
                                                  color: 'green',
                                                  width: 2,
                                              },

                                              hovertemplate:
                                              'Data: %{x|%Y-%m-%d}<br>Sazonalidade Anual: %{y:.2f}<extra></extra>',
            },
        ];
    }, [predictionData]);

    const controls = fileDetails && (
        <>
        <div className="flex flex-col min-w-[250px]">
        <span className="text-xs uppercase text-gray-500">
        Arquivo
        </span>

        <span className="font-semibold">
        {fileDetails.filename}
        </span>
        </div>

        <div className="flex flex-col min-w-[180px]">
        <span className="text-xs uppercase text-gray-500">
        Usuário
        </span>

        <span className="font-semibold">
        {fileDetails.uploader_username}
        </span>
        </div>

        <a
        href={selectedFileUrl}
        download={chartTitles.download}
        className="
        bg-green-600
        hover:bg-green-700
        text-white
        font-semibold
        py-2
        px-4
        rounded-lg
        inline-flex
        items-center
        gap-2
        "
        >
        <FiDownload />
        Baixar CSV
        </a>
        </>
    );

    return (
        <DashboardLayout
        title="Visualizador de Previsão de Internações"
        controls={controls}
        isLoading={loading}
        errorMessage={error}
        feedbackMessage={
            !loading &&
            (!predictionData ||
            predictionData.length === 0)
            ? 'O arquivo de previsão selecionado está vazio ou não contém dados válidos.'
            : null
        }
        >
        <InfoCard title="Como Interpretar a Previsão">
        <ul className="list-disc list-inside space-y-2">
        <li>
        <strong>Dados Históricos:</strong>{' '}
        representam as internações reais
        observadas.
        </li>

        <li>
        <strong>Previsão:</strong> representa a
        estimativa do modelo para períodos
        futuros.
        </li>

        <li>
        <strong>
        Intervalo de Confiança:
        </strong>{' '}
        mostra a faixa provável onde os
        valores futuros podem ocorrer.
        </li>
        </ul>
        </InfoCard>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 h-[650px]">
        <Plot
        data={mainPredictionPlotData}
        layout={{
            title: {
                text: chartTitles.main,
                font: {
                    size: 20,
                    color: '#333',
                },
            },

            xaxis: {
                title: 'Data',
                type: 'date',
                automargin: true,
            },

            yaxis: {
                title:
                'Número de Internações',
                automargin: true,
                rangemode: 'tozero',
            },

            legend: {
                orientation: 'h',
                yanchor: 'bottom',
                y: 1.02,
                xanchor: 'right',
                x: 1,
            },

            margin: {
                t: 80,
                b: 60,
                l: 60,
                r: 30,
            },

            autosize: true,
            hovermode: 'x unified',
        }}
        config={{
            responsive: true,
            displayModeBar: false,
        }}
        className="w-full h-full"
        />
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div>
        <InfoCard title="Tendência">
        <p>
        A tendência representa o
        comportamento geral das
        internações ao longo do tempo,
        removendo efeitos sazonais e
        oscilações de curto prazo.
        </p>
        </InfoCard>

        {trendPlotData.length > 0 && (
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 h-[420px] mt-4">
            <Plot
            data={trendPlotData}
            layout={{
                title: {
                    text: chartTitles.trend,
                    font: {
                        size: 18,
                    },
                },

                xaxis: {
                    title: 'Data',
                    type: 'date',
                },

                yaxis: {
                    title:
                    'Valor da Tendência',
                },

                margin: {
                    t: 60,
                    b: 60,
                    l: 60,
                    r: 30,
                },

                autosize: true,
                showlegend: false,
                hovermode:
                'x unified',
            }}
            config={{
                responsive: true,
                displayModeBar:
                false,
            }}
            className="w-full h-full"
            />
            </div>
        )}
        </div>

        <div>
        <InfoCard title="Sazonalidade Anual">
        <p>
        A sazonalidade mostra padrões
        recorrentes ao longo dos anos,
        identificando períodos com maior
        ou menor número esperado de
        internações.
        </p>
        </InfoCard>

        {yearlySeasonalityPlotData.length >
            0 && (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 h-[420px] mt-4">
                <Plot
                data={
                    yearlySeasonalityPlotData
                }
                layout={{
                    title: {
                        text: chartTitles.seasonality,
                        font: {
                            size: 18,
                        },
                    },

                    xaxis: {
                        title: 'Data',
                        type: 'date',
                    },

                    yaxis: {
                        title:
                        'Impacto da Sazonalidade',
                    },

                    margin: {
                        t: 60,
                        b: 60,
                        l: 60,
                        r: 30,
                    },

                    autosize: true,
                    showlegend: false,
                    hovermode:
                    'x unified',
                }}
                config={{
                    responsive: true,
                    displayModeBar:
                    false,
                }}
                className="w-full h-full"
                />
                </div>
            )}
            </div>
            </div>
            </DashboardLayout>
    );
};

export default PredictionInternacoesViewerPage;
