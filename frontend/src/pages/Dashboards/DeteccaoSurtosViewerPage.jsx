import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';
import { useLocation, Link } from 'react-router-dom';
import usePageTitle from '../../hooks/usePageTitle';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import InfoCard from '../../components/common/InfoCard';
import { FiDownload, FiExternalLink } from 'react-icons/fi';

const DeteccaoSurtosViewerPage = () => {
    usePageTitle('Resultado da Detecção de Surtos');
    const location = useLocation();
    const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
    const taskId = queryParams.get('taskId');

    const [taskDetails, setTaskDetails] = useState(null);
    const [outputFileUrl, setOutputFileUrl] = useState(null);
    const [chartData, setChartData] = useState(null);
    const [selectedMun, setSelectedMun] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!taskId) {
            setError("Nenhum ID de tarefa foi fornecido.");
            setLoading(false);
            return;
        }
        const fetchAll = async () => {
            setLoading(true);
            setError(null);
            try {
                const token = localStorage.getItem('authToken');
                const response = await axios.get(`/api/pipelines/deteccao-surtos/tasks/${taskId}/`, {
                    headers: { 'Authorization': `Token ${token}` }
                });
                setTaskDetails(response.data);

                const outputId = response.data.output_file_id || response.data.output_file;
                if (outputId) {
                    try {
                        const fileRes = await axios.get(`/api/files/${outputId}/`, {
                            headers: { 'Authorization': `Token ${token}` }
                        });
                        setOutputFileUrl(fileRes.data.file);
                    } catch (fileErr) {
                        console.error("Erro ao buscar detalhes do arquivo:", fileErr);
                    }
                }

                const chartFileId = response.data.chart_data_file_id || response.data.chart_data_file;
                if (chartFileId) {
                    try {
                        const chartRes = await axios.get(`/api/files/${chartFileId}/data/`, {
                            headers: { 'Authorization': `Token ${token}` }
                        });
                        setChartData(chartRes.data);
                    } catch (chartErr) {
                        console.error("Erro ao buscar dados do gráfico:", chartErr);
                    }
                }
            } catch (err) {
                setError("Não foi possível carregar os detalhes da tarefa.");
                console.error("Erro ao buscar detalhes:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchAll();
    }, [taskId]);

    const alertas = taskDetails?.total_alertas || 0;
    const ufs = taskDetails?.ufs || [];
    const anos = taskDetails?.anos || [];
    const agravo = taskDetails?.agravo || '';

    const municipios = useMemo(() => {
        if (!chartData || chartData.length === 0) return [];
        const map = new Map();
        chartData.forEach(d => {
            if (d.MUNICIPIO_IBGE && !map.has(d.MUNICIPIO_IBGE)) {
                map.set(d.MUNICIPIO_IBGE, d.MUNICIPIO_NOME || d.MUNICIPIO_IBGE);
            }
        });
        return Array.from(map.entries()).map(([code, name]) => ({ code, name: String(name) })).sort((a, b) => a.name.localeCompare(b.name));
    }, [chartData]);

    useEffect(() => {
        if (municipios.length > 0 && !selectedMun) {
            setSelectedMun(municipios[0].code);
        }
    }, [municipios, selectedMun]);

    const filteredData = useMemo(() => {
        if (!chartData || !selectedMun) return [];
        return chartData.filter(d => String(d.MUNICIPIO_IBGE) === String(selectedMun));
    }, [chartData, selectedMun]);

    const mainPlotData = useMemo(() => {
        if (!filteredData.length) return [];

        const withY = filteredData.filter(d => d.y != null);
        const withYhat = filteredData.filter(d => d.yhat != null && d.yhat_lower != null && d.yhat_upper != null);
        const outbreakPoints = filteredData.filter(d => d.y > d.yhat_upper && d.y > 5);

        return [
            {
                x: [...withYhat.map(d => new Date(d.ds)), ...withYhat.map(d => new Date(d.ds)).reverse()],
                y: [...withYhat.map(d => d.yhat_upper), ...withYhat.map(d => d.yhat_lower).reverse()],
                fill: 'toself',
                fillcolor: 'rgba(255,0,0,0.12)',
                line: { color: 'transparent' },
                hoverinfo: 'skip',
                name: 'Canal Endêmico (IC 95%)',
            },
            {
                x: withYhat.map(d => new Date(d.ds)),
                y: withYhat.map(d => d.yhat),
                mode: 'lines',
                line: { color: 'rgb(0,176,246)', width: 2 },
                name: 'Canal Endêmico (yhat)',
                hovertemplate: 'Data: %{x|%d/%m/%Y}<br>Esperado: %{y:.0f}<extra></extra>',
            },
            {
                x: withY.map(d => new Date(d.ds)),
                y: withY.map(d => d.y),
                mode: 'lines+markers',
                marker: { color: '#1f1f1f', size: 3 },
                line: { width: 1.5, color: '#1f1f1f' },
                name: 'Casos Observados',
                hovertemplate: 'Data: %{x|%d/%m/%Y}<br>Casos: %{y}<extra></extra>',
            },
            ...(outbreakPoints.length > 0 ? [{
                x: outbreakPoints.map(d => new Date(d.ds)),
                y: outbreakPoints.map(d => d.y),
                mode: 'markers',
                marker: { color: 'red', size: 9, symbol: 'triangle-up', line: { color: 'darkred', width: 1 } },
                name: 'Surto Detectado',
                hovertemplate: 'Data: %{x|%d/%m/%Y}<br>Casos: %{y}<br>SURTO<extra></extra>',
            }] : []),
        ];
    }, [filteredData]);

    const trendPlotData = useMemo(() => {
        const withTrend = filteredData.filter(d => d.trend != null);
        if (!withTrend.length) return [];
        return [{
            x: withTrend.map(d => new Date(d.ds)),
            y: withTrend.map(d => d.trend),
            mode: 'lines',
            line: { color: 'orange', width: 2 },
            name: 'Tendência',
            hovertemplate: 'Data: %{x|%d/%m/%Y}<br>Tendência: %{y:.1f}<extra></extra>',
        }];
    }, [filteredData]);

    const selectedMunName = municipios.find(m => m.code === selectedMun)?.name || selectedMun;

    const getSeverity = (count) => {
        if (count === 0) return { text: 'Sem Alertas', color: 'bg-green-500', icon: '✅' };
        if (count <= 5) return { text: 'Baixo', color: 'bg-yellow-500', icon: '⚠️' };
        if (count <= 15) return { text: 'Moderado', color: 'bg-orange-500', icon: '🔶' };
        return { text: 'Alto', color: 'bg-red-600', icon: '🚨' };
    };

    const severity = getSeverity(alertas);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen p-10">
                <LoadingSpinner size="lg" color="blue" />
                <p className="mt-4 text-gray-700">Carregando resultado da detecção de surtos...</p>
            </div>
        );
    }

    if (error) return <FeedbackMessage message={error} type="error" />;
    if (!taskDetails) return <FeedbackMessage message="Nenhum detalhe da tarefa encontrado." type="info" />;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <h1 className="text-3xl text-center text-gray-800 mb-8">Resultado da Detecção de Surtos</h1>

            <div className="max-w-6xl mx-auto space-y-8">

                {/* Resumo */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-white p-6 rounded-lg shadow-md text-center">
                        <h2 className="text-sm font-bold text-gray-400 uppercase mb-2">Status</h2>
                        <div className={`p-3 rounded-lg text-white ${severity.color}`}>
                            <p className="text-3xl font-black">{severity.icon} {alertas}</p>
                            <p className="text-sm font-bold mt-1">Alerta(s) Detectado(s)</p>
                            <p className="text-xs mt-1 opacity-80">Nível: {severity.text}</p>
                        </div>
                    </div>

                    <div className="bg-white p-6 rounded-lg shadow-md">
                        <h2 className="text-sm font-bold text-gray-400 uppercase mb-3">Parâmetros</h2>
                        <ul className="space-y-2 text-sm">
                            <li className="flex justify-between border-b pb-1">
                                <span className="font-semibold text-gray-600">Agravo:</span>
                                <span className="text-gray-800 font-bold">{agravo}</span>
                            </li>
                            <li className="flex justify-between border-b pb-1">
                                <span className="font-semibold text-gray-600">UFs:</span>
                                <span className="text-gray-800">{ufs.join(', ')}</span>
                            </li>
                            <li className="flex justify-between border-b pb-1">
                                <span className="font-semibold text-gray-600">Anos:</span>
                                <span className="text-gray-800">{anos.join(', ')}</span>
                            </li>
                            <li className="flex justify-between">
                                <span className="font-semibold text-gray-600">Status:</span>
                                <span className={`font-bold ${taskDetails.status === 'SUCCESS' ? 'text-green-600' : 'text-red-600'}`}>
                                    {taskDetails.status}
                                </span>
                            </li>
                        </ul>
                    </div>

                    <div className="bg-white p-6 rounded-lg shadow-md">
                        <h2 className="text-sm font-bold text-gray-400 uppercase mb-3">Ações</h2>
                        <div className="space-y-3">
                            {outputFileUrl && (
                                <a
                                    href={outputFileUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="block w-full text-center bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-lg transition-colors"
                                >
                                    <FiExternalLink className="inline mr-2" /> Ver Relatório CSV
                                </a>
                            )}
                            {outputFileUrl && (
                                <a
                                    href={outputFileUrl}
                                    download
                                    className="block w-full text-center bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded-lg transition-colors"
                                >
                                    <FiDownload className="inline mr-2" /> Baixar CSV
                                </a>
                            )}
                            <Link
                                to="/pipelines/deteccao-surtos"
                                className="block w-full text-center bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-bold py-2 px-4 rounded-lg transition-colors"
                            >
                                Nova Análise
                            </Link>
                        </div>
                    </div>
                </div>

                {taskDetails.message && (
                    <InfoCard title="Detalhes da Execução">
                        <p className="text-sm text-gray-600">{taskDetails.message}</p>
                    </InfoCard>
                )}

                {/* Gráficos Prophet */}
                {chartData && chartData.length > 0 && (
                    <>
                        <div className="bg-white p-4 rounded-lg shadow-md">
                            <div className="flex items-center gap-4 mb-4">
                                <label className="text-sm font-bold text-gray-600 uppercase">Município:</label>
                                <select
                                    value={selectedMun}
                                    onChange={(e) => setSelectedMun(e.target.value)}
                                    className="p-2 border border-gray-300 rounded-lg text-sm bg-white min-w-[300px]"
                                >
                                    {municipios.map(m => (
                                        <option key={m.code} value={m.code}>{m.name} ({m.code})</option>
                                    ))}
                                </select>
                            </div>

                            <div className="h-[500px]">
                                <Plot
                                    data={mainPlotData}
                                    layout={{
                                        title: {
                                            text: `Canal Endêmico - ${selectedMunName} (${agravo})`,
                                            font: { size: 18, color: '#333' },
                                        },
                                        xaxis: { title: 'Data', type: 'date', automargin: true },
                                        yaxis: { title: 'Casos Notificados Semanais', automargin: true, rangemode: 'tozero' },
                                        legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 },
                                        margin: { t: 80, b: 60, l: 60, r: 30 },
                                        autosize: true,
                                        hovermode: 'x unified',
                                    }}
                                    config={{ responsive: true, displayModeBar: false }}
                                    className="w-full h-full"
                                />
                            </div>
                        </div>

                        {trendPlotData.length > 0 && (
                            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                                <div>
                                    <InfoCard title="Tendência">
                                        <p className="text-sm text-gray-600">
                                            A tendência representa o comportamento geral das notificações ao longo do tempo,
                                            removendo efeitos sazonais e oscilações de curto prazo.
                                        </p>
                                    </InfoCard>
                                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 h-[420px] mt-4">
                                        <Plot
                                            data={trendPlotData}
                                            layout={{
                                                title: { text: `Tendência - ${selectedMunName}`, font: { size: 16 } },
                                                xaxis: { title: 'Data', type: 'date' },
                                                yaxis: { title: 'Valor da Tendência' },
                                                margin: { t: 60, b: 60, l: 60, r: 30 },
                                                autosize: true,
                                                showlegend: false,
                                                hovermode: 'x unified',
                                            }}
                                            config={{ responsive: true, displayModeBar: false }}
                                            className="w-full h-full"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <InfoCard title="Como Interpretar">
                                        <ul className="list-disc list-inside space-y-2 text-sm text-gray-600">
                                            <li><b className="text-gray-800">Casos Observados:</b> Número real de notificações por semana.</li>
                                            <li><b className="text-gray-800">Canal Endêmico:</b> Estimativa Prophet com intervalo de confiança de 95%.</li>
                                            <li><b className="text-gray-800">Triângulos vermelhos:</b> Semanas onde o excesso de casos indica surto (y &gt; limite superior E y &gt; 5).</li>
                                            <li><b className="text-gray-800">Tendência:</b> Comportamento de longo prazo, sem sazonalidade.</li>
                                        </ul>
                                    </InfoCard>
                                </div>
                            </div>
                        )}
                    </>
                )}

                {!chartData && taskDetails.status === 'SUCCESS' && (
                    <>
                        <FeedbackMessage
                            message="Os dados do gráfico Prophet não estão disponíveis. O arquivo de dados foi removido ou a tarefa ainda não gerou os dados do gráfico."
                            type="error"
                        />
                        <InfoCard title="Como Interpretar os Resultados">
                            <div className="space-y-2 text-sm text-gray-600">
                                <p>
                                    <strong>Agravo {agravo}:</strong> Cada alerta significa que, em uma determinada semana epidemiológica,
                                    o número de casos notificados no município superou o esperado pelo Canal Endêmico Dinâmico.
                                </p>
                                <ul className="list-disc list-inside space-y-1 mt-2">
                                    <li><b className="text-gray-800">Casos Observados:</b> Número real de notificações na semana.</li>
                                    <li><b className="text-gray-800">Limite Esperado:</b> Limite superior do intervalo de confiança de 95% do Prophet.</li>
                                    <li><b className="text-gray-800">Excesso de Casos:</b> Diferença entre observado e esperado (quanto maior, mais crítico).</li>
                                </ul>
                            </div>
                        </InfoCard>
                    </>
                )}
            </div>
        </div>
    );
};

export default DeteccaoSurtosViewerPage;
