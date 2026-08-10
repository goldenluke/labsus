import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';
import { useLocation, Link } from 'react-router-dom';
import usePageTitle from '../../hooks/usePageTitle';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';
import { FiDownload, FiHeart, FiAlertTriangle, FiCheckCircle } from 'react-icons/fi';

const FEATURE_LABELS = {
    PESO: 'Peso ao Nascer',
    GESTACAO: 'Gestação',
    APGAR5: 'APGAR 5min',
    IDADEMAE: 'Idade da Mãe',
    ESCMAE2010: 'Escolaridade',
    RACACORMAE: 'Raça/Cor',
    CONSPRENAT: 'Consultas Pré-Natal',
    QTDFILVIVO: 'Filhos Vivos',
    QTDFILMORT: 'Filhos Mortos',
    PARTO: 'Tipo de Parto',
    QTLEIT39: 'Nº Leitos',
    ATIVIDAD: 'Atividade Profissional',
};

const SobrevidaInfantilViewerPage = () => {
    usePageTitle('Resultado da Sobrevida Infantil');
    const location = useLocation();
    const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
    const taskId = queryParams.get('taskId');

    const [taskDetails, setTaskDetails] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!taskId) {
            setError('Nenhum ID de tarefa foi fornecido.');
            setLoading(false);
            return;
        }

        const fetchTaskDetails = async () => {
            setLoading(true);
            setError(null);
            try {
                const token = localStorage.getItem('authToken');
                const response = await axios.get(`/api/pipelines/sobrevida-infantil/tasks/${taskId}/`, {
                    headers: { Authorization: `Token ${token}` },
                });
                setTaskDetails(response.data);
            } catch (err) {
                setError('Não foi possível carregar os detalhes da tarefa. Verifique se a tarefa existe e se você tem permissão para a ver.');
                console.error('Erro ao buscar detalhes da tarefa:', err);
            } finally {
                setLoading(false);
            }
        };
        fetchTaskDetails();
    }, [taskId]);

    const mortalityProbability = taskDetails?.mortality_probability;
    const riskClassification = taskDetails?.risk_classification;
    const shapData = useMemo(() => {
        if (!taskDetails?.shap_data) return null;
        try {
            return typeof taskDetails.shap_data === 'string'
                ? JSON.parse(taskDetails.shap_data)
                : taskDetails.shap_data;
        } catch {
            return null;
        }
    }, [taskDetails]);

    const riskLevel = useMemo(() => {
        if (mortalityProbability == null) return null;
        if (mortalityProbability < 0.15) return { text: 'BAIXO', color: 'bg-green-500', textColor: 'text-green-700', borderColor: 'border-green-400', icon: <FiCheckCircle className="text-green-500 text-xl" /> };
        if (mortalityProbability <= 0.4) return { text: 'MODERADO', color: 'bg-amber-500', textColor: 'text-amber-700', borderColor: 'border-amber-400', icon: <FiAlertTriangle className="text-amber-500 text-xl" /> };
        return { text: 'ALTO', color: 'bg-red-500', textColor: 'text-red-700', borderColor: 'border-red-400', icon: <FiAlertTriangle className="text-red-500 text-xl" /> };
    }, [mortalityProbability]);

    const shapPlotData = useMemo(() => {
        if (!shapData) return [];
        const featureNames = [...shapData.feature_names].map((f) => FEATURE_LABELS[f] || f).reverse();
        const shapValues = [...shapData.shap_values].reverse();
        return [
            {
                type: 'waterfall',
                orientation: 'h',
                y: featureNames,
                x: shapValues,
                connector: { line: { color: '#e5e7eb' } },
                increasing: { marker: { color: '#ef4444' } },
                decreasing: { marker: { color: '#3b82f6' } },
                textposition: 'outside',
                text: shapValues.map((v) => (v > 0 ? `+${v.toFixed(3)}` : v.toFixed(3))),
            },
        ];
    }, [shapData]);

    const handleDownloadCsv = () => {
        if (!taskDetails?.output_file_id) return;
        window.open(`/api/files/${taskDetails.output_file_id}/`, '_blank');
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen p-10">
                <LoadingSpinner size="lg" color="blue" />
                <p className="mt-4 text-gray-700">A carregar resultado da sobrevida infantil...</p>
            </div>
        );
    }

    if (error) return <FeedbackMessage message={error} type="error" />;
    if (!taskDetails) return <FeedbackMessage message="Nenhum detalhe da tarefa encontrado." type="info" />;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <Link
                to="/pipelines/sobrevida-infantil"
                className="text-blue-600 hover:text-blue-800 inline-flex items-center gap-1 mb-6 text-sm"
            >
                &larr; Voltar para Sobrevida Infantil
            </Link>

            <h1 className="text-3xl text-center text-gray-800 mb-8">Resultado da Sobrevida Infantil</h1>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Coluna Esquerda (1/3): Score e Dados do Paciente */}
                <div className="lg:col-span-1 space-y-6">
                    <div className="bg-white p-6 rounded-lg shadow-md text-center">
                        <div className="flex items-center justify-center gap-2 mb-2">
                            <FiHeart className="text-red-500 text-xl" />
                            <h2 className="text-xl font-semibold text-gray-700">Probabilidade de Óbito</h2>
                        </div>
                        <div className={`p-4 rounded-lg text-white ${riskLevel.color}`}>
                            <p className="text-6xl font-bold">{(mortalityProbability * 100).toFixed(1)}%</p>
                            <div className="flex items-center justify-center gap-2 mt-1">
                                {riskLevel.icon}
                                <p className="text-2xl font-semibold">{riskLevel.text}</p>
                            </div>
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                            Classificação: <span className={`font-semibold ${riskLevel.textColor}`}>{riskClassification}</span>
                        </p>
                    </div>

                    <div className="bg-white p-6 rounded-lg shadow-md">
                        <h2 className="text-xl font-semibold text-gray-700 mb-4">Dados do Paciente</h2>
                        <ul className="space-y-2 text-sm">
                            {taskDetails.patient_data &&
                                Object.entries(taskDetails.patient_data).map(([key, value]) => (
                                    <li key={key} className="flex justify-between border-b pb-1">
                                        <span className="font-semibold text-gray-600">
                                            {FEATURE_LABELS[key] || key}:
                                        </span>
                                        <span className="text-gray-800">{String(value)}</span>
                                    </li>
                                ))}
                        </ul>
                    </div>
                </div>

                {/* Coluna Direita (2/3): SHAP e Download */}
                <div className="lg:col-span-2 space-y-4">
                    <InfoCard title="Como Interpretar o Gráfico de Explicação (SHAP)">
                        <p>Este gráfico "waterfall" mostra como cada característica do paciente influenciou a previsão de risco de óbito.</p>
                        <ul className="list-disc list-inside space-y-1 mt-2 text-xs">
                            <li>
                                <b className="text-gray-800">Valor Base (E[f(x)]):</b> É o risco médio de óbito para todos os pacientes no conjunto de dados de teste.
                            </li>
                            <li>
                                <b className="text-red-600">Setas Vermelhas:</b> Fatores que AUMENTARAM o risco de óbito para este paciente.
                            </li>
                            <li>
                                <b className="text-blue-600">Setas Azuis:</b> Fatores que DIMINUÍRAM o risco de óbito.
                            </li>
                            <li>
                                <b className="text-gray-800">Valor Final (f(x)):</b> É o risco final do paciente após somar todos os impactos.
                            </li>
                        </ul>
                    </InfoCard>

                    <div className="bg-white p-4 rounded-lg shadow-md">
                        {shapPlotData.length > 0 ? (
                            <Plot
                                data={shapPlotData}
                                layout={{
                                    title: 'Explicação SHAP - Sobrevida Infantil',
                                    xaxis: { title: 'Impacto no Risco de Óbito' },
                                    margin: { l: 200, r: 20, t: 50, b: 50 },
                                    height: 500,
                                }}
                                config={{ displayModeBar: false }}
                            />
                        ) : (
                            <p className="text-center text-gray-500 p-8">Dados SHAP indisponíveis para esta tarefa.</p>
                        )}
                    </div>

                    {taskDetails.output_file_id && (
                        <button
                            onClick={handleDownloadCsv}
                            className="bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded inline-flex items-center"
                        >
                            <FiDownload className="mr-2" /> Baixar CSV
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SobrevidaInfantilViewerPage;
