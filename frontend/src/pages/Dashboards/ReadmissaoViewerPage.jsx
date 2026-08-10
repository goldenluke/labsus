import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useLocation, Link } from 'react-router-dom';
import Plot from 'react-plotly.js';
import usePageTitle from '../../hooks/usePageTitle';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import InfoCard from '../../components/common/InfoCard';
import { FiActivity, FiClock } from 'react-icons/fi';

const FEATURE_LABELS = {
    IDADE: 'Idade',
    DIAS_PERM: 'Dias de Permanência',
    N_COMORBIDADES: 'Nº de Comorbidades',
    USOU_UTI: 'Utilizou UTI',
    SEXO: 'Sexo',
    RACA_COR: 'Raça/Cor',
    CAR_INT: 'Caráter da Internação',
    DIAG_PRINC: 'Diagnóstico Principal',
    HOSP_NATUREZA: 'Natureza do Hospital',
    HOSP_LEITOS: 'Nº de Leitos do Hospital',
};

const ReadmissaoViewerPage = () => {
    usePageTitle('Resultado da Previsão de Readmissão');
    const location = useLocation();
    const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
    const taskId = queryParams.get('taskId');

    const [taskDetails, setTaskDetails] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState('lgbm');
    const [coxData, setCoxData] = useState(null);
    const [coxLoading, setCoxLoading] = useState(false);

    useEffect(() => {
        if (!taskId) {
            setError("Nenhum ID de tarefa foi fornecido.");
            setLoading(false);
            return;
        }
        const fetchTaskDetails = async () => {
            setLoading(true);
            setError(null);
            try {
                const token = localStorage.getItem('authToken');
                const response = await axios.get(`/api/pipelines/risco-readmissao/tasks/${taskId}/`, {
                    headers: { 'Authorization': `Token ${token}` }
                });
                setTaskDetails(response.data);

                if (response.data.shap_data && response.data.shap_data.survival_curve) {
                    setCoxData(response.data.shap_data);
                    if (!response.data.shap_data.feature_names) {
                        setActiveTab('cox');
                    }
                }
            } catch (err) {
                setError("Não foi possível carregar os detalhes da tarefa.");
                console.error("Erro ao buscar detalhes da tarefa:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchTaskDetails();
    }, [taskId]);

    const triggerCoxAnalysis = async () => {
        if (!taskDetails?.patient_data) return;
        setCoxLoading(true);
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.post('/api/pipelines/risco-readmissao/cox-trigger/', {
                patient_data: taskDetails.patient_data,
            }, { headers: { 'Authorization': `Token ${token}` } });

            const coxTaskId = response.data.task_id;
            const pollInterval = setInterval(async () => {
                try {
                    const statusRes = await axios.get(`/api/pipelines/risco-readmissao/tasks/${coxTaskId}/status/`, {
                        headers: { 'Authorization': `Token ${token}` }
                    });
                    if (statusRes.data.status === 'SUCCESS') {
                        clearInterval(pollInterval);
                        const detailRes = await axios.get(`/api/pipelines/risco-readmissao/tasks/${coxTaskId}/`, {
                            headers: { 'Authorization': `Token ${token}` }
                        });
                        if (detailRes.data.shap_data) {
                            setCoxData(detailRes.data.shap_data);
                            setActiveTab('cox');
                        }
                        setCoxLoading(false);
                    } else if (statusRes.data.status === 'FAILURE') {
                        clearInterval(pollInterval);
                        setCoxLoading(false);
                        alert("Falha na análise Cox.");
                    }
                } catch (e) {
                    clearInterval(pollInterval);
                    setCoxLoading(false);
                }
            }, 2000);
        } catch (err) {
            setCoxLoading(false);
            alert("Erro ao disparar análise Cox.");
        }
    };

    const riskScore = taskDetails?.risk_score;
    const riskLevel = useMemo(() => {
        if (riskScore == null) return null;
        if (riskScore >= 0.75) return { text: 'Altíssimo', color: 'bg-red-700' };
        if (riskScore >= 0.50) return { text: 'Alto', color: 'bg-red-500' };
        if (riskScore >= 0.25) return { text: 'Moderado', color: 'bg-yellow-500' };
        return { text: 'Baixo', color: 'bg-green-500' };
    }, [riskScore]);

    const medianSurvival = coxData?.survival_curve?.median_survival;
    const hasMedianSurvival = Number.isFinite(medianSurvival);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen p-10">
                <LoadingSpinner size="lg" color="blue" />
                <p className="mt-4 text-gray-700">Carregando resultado da previsão...</p>
            </div>
        );
    }

    if (error) return <FeedbackMessage message={error} type="error" />;
    if (!taskDetails) return <FeedbackMessage message="Nenhum detalhe da tarefa encontrado." type="info" />;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <h1 className="text-3xl text-center text-gray-800 mb-6">Resultado da Previsão de Risco de Readmissão</h1>

            {/* Tab Toggle */}
            <div className="flex justify-center gap-2 mb-8">
                <button
                    onClick={() => setActiveTab('lgbm')}
                    className={`px-6 py-2 rounded-xl text-sm font-bold transition-all ${
                        activeTab === 'lgbm'
                            ? 'bg-blue-600 text-white shadow-md'
                            : 'bg-white text-gray-600 border border-gray-200 hover:border-blue-300'
                    }`}
                >
                    <FiActivity className="inline mr-2" /> LightGBM (30 dias)
                </button>
                <button
                    onClick={() => {
                        if (!coxData) {
                            triggerCoxAnalysis();
                        } else {
                            setActiveTab('cox');
                        }
                    }}
                    disabled={coxLoading}
                    className={`px-6 py-2 rounded-xl text-sm font-bold transition-all ${
                        activeTab === 'cox'
                            ? 'bg-violet-600 text-white shadow-md'
                            : 'bg-white text-gray-600 border border-gray-200 hover:border-violet-300'
                    } ${coxLoading ? 'opacity-60 cursor-wait' : ''}`}
                >
                    <FiClock className="inline mr-2" />
                    {coxLoading ? 'Calculando Cox...' : 'Cox (Sobrevivência)'}
                </button>
            </div>

            {activeTab === 'lgbm' ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-1 space-y-8">
                        <div className="bg-white p-6 rounded-lg shadow-md text-center">
                            <h2 className="text-xl font-semibold text-gray-700 mb-2">Score de Risco</h2>
                            <div className={`p-4 rounded-lg text-white ${riskLevel?.color || 'bg-gray-400'}`}>
                                <p className="text-6xl font-bold">{((riskScore || 0) * 100).toFixed(1)}%</p>
                                <p className="text-2xl font-semibold">{riskLevel?.text || 'N/A'}</p>
                            </div>
                            <p className="text-xs text-gray-500 mt-2">Probabilidade de readmissão em 30 dias.</p>
                        </div>

                        <div className="bg-white p-6 rounded-lg shadow-md">
                            <h2 className="text-xl font-semibold text-gray-700 mb-4">Dados do Paciente</h2>
                            <ul className="space-y-2 text-sm">
                                {Object.entries(taskDetails.patient_data).map(([key, value]) => (
                                    <li key={key} className="flex justify-between border-b pb-1">
                                        <span className="font-semibold text-gray-600">{FEATURE_LABELS[key] || key}:</span>
                                        <span className="text-gray-800">{String(value)}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    <div className="lg:col-span-2 space-y-4">
                        <InfoCard title="Como Interpretar o Gráfico de Explicação (SHAP)">
                            <p>Este gráfico "waterfall" mostra como cada característica do paciente influenciou a previsão de risco.</p>
                            <ul className="list-disc list-inside space-y-1 mt-2 text-xs">
                                <li><b className="text-gray-800">Valor Base:</b> Risco médio de readmissão.</li>
                                <li><b className="text-red-600">Setas Vermelhas:</b> Fatores que AUMENTARAM o risco.</li>
                                <li><b className="text-blue-600">Setas Azuis:</b> Fatores que DIMINUÍRAM o risco.</li>
                                <li><b className="text-gray-800">Valor Final:</b> Score final do paciente.</li>
                            </ul>
                        </InfoCard>
                        <div className="bg-white p-4 rounded-lg shadow-md">
                            <h2 className="text-xl font-semibold text-gray-700 mb-2">Explicação da Previsão</h2>
                            {taskDetails.shap_data && taskDetails.shap_data.feature_names && taskDetails.shap_data.shap_values ? (
                                <Plot
                                    data={[{
                                        type: 'waterfall',
                                        orientation: 'h',
                                        y: [...taskDetails.shap_data.feature_names].reverse(),
                                        x: [...taskDetails.shap_data.shap_values].reverse(),
                                        connector: { line: { color: '#e5e7eb' } },
                                        increasing: { marker: { color: '#ef4444' } },
                                        decreasing: { marker: { color: '#3b82f6' } },
                                        textposition: 'outside',
                                        text: [...taskDetails.shap_data.shap_values].reverse()
                                            .map((v) => (v > 0 ? `+${v.toFixed(4)}` : v.toFixed(4))),
                                    }]}
                                    layout={{
                                        xaxis: { title: 'Impacto no Risco', gridcolor: '#f3f4f6' },
                                        margin: { l: 200, r: 20, t: 10, b: 50 },
                                        height: 500,
                                    }}
                                    config={{ displayModeBar: false }}
                                    useResizeHandler
                                    style={{ width: '100%' }}
                                />
                            ) : (
                                <FeedbackMessage message="Dados SHAP não disponíveis para esta tarefa." type="info" />
                            )}
                        </div>
                    </div>
                </div>
            ) : (
                /* Cox Tab */
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-1 space-y-8">
                        <div className="bg-white p-6 rounded-lg shadow-md text-center">
                            <h2 className="text-xl font-semibold text-gray-700 mb-2">Hazard Parcial</h2>
                            <div className="p-4 rounded-lg bg-violet-600 text-white">
                                <p className="text-4xl font-bold">{coxData?.partial_hazard?.toFixed(3) || 'N/A'}</p>
                            </div>
                            <p className="text-xs text-gray-500 mt-2">Risco relativo (Cox PH).</p>
                        </div>

                        <div className="bg-white p-6 rounded-lg shadow-md text-center">
                            <h2 className="text-xl font-semibold text-gray-700 mb-2">Mediana de Sobrevivência</h2>
                            <div className="p-4 rounded-lg bg-blue-600 text-white">
                                <p className="text-4xl font-bold">
                                    {hasMedianSurvival ? `${medianSurvival.toFixed(0)} dias` : 'N/A'}
                                </p>
                            </div>
                            <p className="text-xs text-gray-500 mt-2">
                                {hasMedianSurvival
                                    ? 'Tempo mediano até readmissão.'
                                    : 'A curva não atingiu 50% de sobrevivência.'}
                            </p>
                        </div>

                        <div className="bg-white p-6 rounded-lg shadow-md">
                            <h2 className="text-sm font-semibold text-gray-700 mb-2">Concordance Index</h2>
                            <p className="text-2xl font-bold text-violet-600">{coxData?.concordance_index?.toFixed(3) || 'N/A'}</p>
                            <p className="text-xs text-gray-500 mt-1">Poder de discriminação do modelo (0.5 = aleatório, 1.0 = perfeito).</p>
                        </div>

                        <div className="bg-white p-6 rounded-lg shadow-md">
                            <h2 className="text-xl font-semibold text-gray-700 mb-4">Dados do Paciente</h2>
                            <ul className="space-y-2 text-sm">
                                {coxData?.patient_data && Object.entries(coxData.patient_data).map(([key, value]) => (
                                    <li key={key} className="flex justify-between border-b pb-1">
                                        <span className="font-semibold text-gray-600">{FEATURE_LABELS[key] || key}:</span>
                                        <span className="text-gray-800">{String(value)}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>

                    <div className="lg:col-span-2 space-y-6">
                        <InfoCard title="Sobre o Modelo Cox (Sobrevivência)">
                            <p className="text-sm text-gray-600">
                                O modelo <strong>Cox Proportional Hazards</strong> estima a probabilidade de sobrevivência (sem readmissão) ao longo do tempo.
                                Diferente do LightGBM que prevê risco em 30 dias, o Cox mostra a curva temporal completa de readmissão.
                            </p>
                        </InfoCard>

                        {/* Survival Curve */}
                        <div className="bg-white p-6 rounded-lg shadow-md">
                            <h2 className="text-xl font-semibold text-gray-700 mb-4">Curva de Sobrevivência</h2>
                            {coxData?.survival_curve ? (
                                <Plot
                                    data={[{
                                        type: 'scatter',
                                        mode: 'lines',
                                        x: coxData.survival_curve.time,
                                        y: coxData.survival_curve.probability,
                                        fill: 'tozeroy',
                                        fillcolor: 'rgba(139, 92, 246, 0.1)',
                                        line: { color: '#8b5cf6', width: 2 },
                                        name: 'P(Sem Readmissão)',
                                    }]}
                                    layout={{
                                        xaxis: { title: 'Dias desde a Internação', gridcolor: '#f3f4f6' },
                                        yaxis: { title: 'Probabilidade de Sobrevivência', range: [0, 1], gridcolor: '#f3f4f6' },
                                        margin: { l: 60, r: 20, t: 20, b: 50 },
                                        height: 350,
                                        shapes: [{
                                            type: 'line',
                                            x0: 0, x1: coxData.survival_curve.time?.slice(-1)?.[0] || 700,
                                            y0: 0.5, y1: 0.5,
                                            line: { color: '#ef4444', width: 1, dash: 'dash' }
                                        }],
                                        annotations: hasMedianSurvival ? [{
                                            x: medianSurvival,
                                            y: 0.5,
                                            text: `Mediana: ${medianSurvival.toFixed(0)} dias`,
                                            showarrow: true,
                                            arrowhead: 2,
                                            ax: 40, ay: -30,
                                            font: { color: '#ef4444', size: 11 }
                                        }] : []
                                    }}
                                    config={{ displayModeBar: false }}
                                    className="w-full"
                                />
                            ) : (
                                <LoadingSpinner size="sm" />
                            )}
                        </div>

                        {/* Hazard Ratios */}
                        <div className="bg-white p-6 rounded-lg shadow-md">
                            <h2 className="text-xl font-semibold text-gray-700 mb-4">Hazard Ratios (Fatores de Risco)</h2>
                            {coxData?.hazard_ratios ? (
                                <Plot
                                    data={[{
                                        type: 'bar',
                                        orientation: 'h',
                                        y: coxData.hazard_ratios.slice(0, 15).map(h => h.feature),
                                        x: coxData.hazard_ratios.slice(0, 15).map(h => h.hr),
                                        error_x: {
                                            type: 'data',
                                            symmetric: false,
                                            array: coxData.hazard_ratios.slice(0, 15).map(h => h.ci_upper - h.hr),
                                            arrayminus: coxData.hazard_ratios.slice(0, 15).map(h => h.hr - h.ci_lower),
                                            color: '#9ca3af',
                                        },
                                        marker: {
                                            color: coxData.hazard_ratios.slice(0, 15).map(h =>
                                                h.hr > 1 ? '#ef4444' : '#3b82f6'
                                            ),
                                        },
                                        text: coxData.hazard_ratios.slice(0, 15).map(h => `${h.hr.toFixed(2)}x`),
                                        textposition: 'outside',
                                    }]}
                                    layout={{
                                        xaxis: { title: 'Hazard Ratio (1.0 = sem efeito)', gridcolor: '#f3f4f6' },
                                        margin: { l: 180, r: 50, t: 10, b: 50 },
                                        height: 450,
                                        shapes: [{
                                            type: 'line',
                                            x0: 1, x1: 1,
                                            y0: -0.5, y1: coxData.hazard_ratios.slice(0, 15).length - 0.5,
                                            line: { color: '#6b7280', width: 1, dash: 'dash' }
                                        }]
                                    }}
                                    config={{ displayModeBar: false }}
                                    className="w-full"
                                />
                            ) : (
                                <LoadingSpinner size="sm" />
                            )}
                        </div>
                    </div>
                </div>
            )}

            <div className="mt-8 text-center">
                <Link to="/pipelines/risco-readmissao" className="text-blue-600 hover:underline text-sm font-bold">
                    ← Voltar para a Pipeline de Readmissão
                </Link>
            </div>
        </div>
    );
};

export default ReadmissaoViewerPage;
