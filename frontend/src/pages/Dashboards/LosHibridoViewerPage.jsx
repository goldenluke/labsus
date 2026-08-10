import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useLocation, Link } from 'react-router-dom';
import usePageTitle from '../../hooks/usePageTitle';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import InfoCard from '../../components/common/InfoCard';
import { FiDownload, FiExternalLink, FiClock } from 'react-icons/fi';

const FEATURE_LABELS = {
    IDADE: 'Idade do Paciente',
    UTI_MES_TO: 'Total de Diárias de UTI',
    LEITHOSP: 'Nº Total de Leitos do Hospital',
    COMPLEXIDADE_MEDIA: 'Complexidade Média',
    SEXO: 'Sexo',
    CAR_INT: 'Caráter da Internação',
    TP_UNID: 'Tipo de Unidade Hospitalar',
    ATIVIDAD: 'Hospital de Ensino/Pesquisa',
    CAPITULO_CID: 'Capítulo CID-10',
};

const DEPT_LABELS = {
    Cirurgia: 'Cirurgia',
    Clinica_Medica: 'Clínica Médica',
    Obstetricia: 'Obstetrícia',
    Pediatria: 'Pediatria',
};

const LosHibridoViewerPage = () => {
    usePageTitle('Resultado LOS Híbrido');
    const location = useLocation();
    const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
    const taskId = queryParams.get('taskId');

    const [taskDetails, setTaskDetails] = useState(null);
    const [outputFileUrl, setOutputFileUrl] = useState(null);
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
                const response = await axios.get(`/api/pipelines/los-hibrido/tasks/${taskId}/`, {
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
            } catch (err) {
                setError("Não foi possível carregar os detalhes da tarefa.");
                console.error("Erro ao buscar detalhes:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchAll();
    }, [taskId]);

    const getSeverity = (classificacao, prob) => {
        if (classificacao === 'Longa' && prob > 0.7) return { text: 'Alto Risco', color: 'bg-red-600', icon: '🔴' };
        if (classificacao === 'Longa') return { text: 'Risco Moderado', color: 'bg-orange-500', icon: '🟠' };
        return { text: 'Baixo Risco', color: 'bg-green-500', icon: '🟢' };
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen p-10">
                <LoadingSpinner size="lg" color="blue" />
                <p className="mt-4 text-gray-700">Carregando resultado do LOS Híbrido...</p>
            </div>
        );
    }

    if (error) return <FeedbackMessage message={error} type="error" />;
    if (!taskDetails) return <FeedbackMessage message="Nenhum detalhe da tarefa encontrado." type="info" />;

    const classificacao = taskDetails.permanencia_classificada;
    const probabilidade = taskDetails.probabilidade_longa;
    const previsaoDias = taskDetails.previsao_dias;
    const departamento = taskDetails.departamento;
    const severity = getSeverity(classificacao, probabilidade);

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <h1 className="text-3xl text-center text-gray-800 mb-8">Resultado do LOS Híbrido</h1>

            <div className="max-w-6xl mx-auto space-y-8">

                {/* Resumo */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-white p-6 rounded-lg shadow-md text-center">
                        <h2 className="text-sm font-bold text-gray-400 uppercase mb-2">Classificação</h2>
                        <div className={`p-3 rounded-lg text-white ${severity.color}`}>
                            <p className="text-3xl font-black">{severity.icon} {classificacao || '---'}</p>
                            <p className="text-sm font-bold mt-1">Permanência {classificacao}</p>
                            <p className="text-xs mt-1 opacity-80">Nível: {severity.text}</p>
                        </div>
                    </div>

                    <div className="bg-white p-6 rounded-lg shadow-md text-center">
                        <h2 className="text-sm font-bold text-gray-400 uppercase mb-2">Previsão de Dias</h2>
                        <div className="p-3 rounded-lg bg-blue-600 text-white">
                            <p className="text-4xl font-black">{previsaoDias != null ? previsaoDias : '---'}</p>
                            <p className="text-sm font-bold mt-1">dia(s) de permanência</p>
                        </div>
                        <p className="text-xs text-gray-500 mt-2">
                            Probabilidade de longa: {probabilidade != null ? `${(probabilidade * 100).toFixed(1)}%` : '---'}
                        </p>
                    </div>

                    <div className="bg-white p-6 rounded-lg shadow-md">
                        <h2 className="text-sm font-bold text-gray-400 uppercase mb-3">Parâmetros</h2>
                        <ul className="space-y-2 text-sm">
                            <li className="flex justify-between border-b pb-1">
                                <span className="font-semibold text-gray-600">Departamento:</span>
                                <span className="text-gray-800 font-bold">{DEPT_LABELS[departamento] || departamento}</span>
                            </li>
                            <li className="flex justify-between border-b pb-1">
                                <span className="font-semibold text-gray-600">Status:</span>
                                <span className={`font-bold ${taskDetails.status === 'SUCCESS' ? 'text-green-600' : 'text-red-600'}`}>
                                    {taskDetails.status}
                                </span>
                            </li>
                            <li className="flex justify-between">
                                <span className="font-semibold text-gray-600">Modelo:</span>
                                <span className="text-gray-800">LightGBM Híbrido</span>
                            </li>
                        </ul>
                    </div>
                </div>

                {/* Ações */}
                <div className="bg-white p-4 rounded-lg shadow-md flex flex-wrap gap-3 justify-center">
                    {outputFileUrl && (
                        <a href={outputFileUrl} target="_blank" rel="noopener noreferrer"
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold rounded-lg transition flex items-center gap-2">
                            <FiExternalLink /> Ver CSV
                        </a>
                    )}
                    {outputFileUrl && (
                        <a href={outputFileUrl} download
                            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm font-bold rounded-lg transition flex items-center gap-2">
                            <FiDownload /> Baixar CSV
                        </a>
                    )}
                    <Link to="/pipelines/los-hibrido"
                        className="px-4 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-bold rounded-lg transition">
                        Nova Previsão
                    </Link>
                </div>

                {taskDetails.message && (
                    <InfoCard title="Detalhes da Execução">
                        <p className="text-sm text-gray-600">{taskDetails.message}</p>
                    </InfoCard>
                )}

                {/* SHAP Image */}
                {taskDetails.output_image_url ? (
                    <div className="bg-white p-4 rounded-lg shadow-md">
                        <h2 className="text-xl font-semibold text-gray-700 mb-3">Explicação SHAP</h2>
                        <InfoCard title="Como Interpretar o Gráfico SHAP">
                            <p className="text-sm text-gray-600">O gráfico "waterfall" mostra como cada característica influenciou a previsão de dias de permanência.</p>
                            <ul className="list-disc list-inside space-y-1 mt-2 text-xs">
                                <li><b className="text-red-600">Setas Vermelhas:</b> Fatores que AUMENTARAM a previsão de dias.</li>
                                <li><b className="text-blue-600">Setas Azuis:</b> Fatores que DIMINUÍRAM a previsão de dias.</li>
                            </ul>
                        </InfoCard>
                        <a href={taskDetails.output_image_url} target="_blank" rel="noopener noreferrer"
                            className="block border rounded-lg overflow-hidden hover:opacity-90 transition-opacity mt-3">
                            <img src={taskDetails.output_image_url} alt="SHAP - LOS Híbrido" className="w-full h-auto" />
                        </a>
                        <a href={taskDetails.output_image_url} download
                            className="mt-3 bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded inline-flex items-center">
                            <FiDownload className="mr-2" /> Baixar Imagem SHAP
                        </a>
                    </div>
                ) : (
                    <FeedbackMessage message="Imagem SHAP não disponível para esta tarefa." type="info" />
                )}

                {/* Dados de Entrada */}
                <div className="bg-white p-6 rounded-lg shadow-md">
                    <h2 className="text-xl font-semibold text-gray-700 mb-4">Dados de Entrada</h2>
                    <ul className="space-y-2 text-sm">
                        {taskDetails.patient_data && Object.entries(taskDetails.patient_data).map(([key, value]) => (
                            <li key={key} className="flex justify-between border-b pb-1">
                                <span className="font-semibold text-gray-600">{FEATURE_LABELS[key] || key}:</span>
                                <span className="text-gray-800 text-right max-w-[60%] truncate">{String(value)}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            </div>
        </div>
    );
};

export default LosHibridoViewerPage;
