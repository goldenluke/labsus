import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useLocation } from 'react-router-dom';
import usePageTitle from '../../hooks/usePageTitle';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import InfoCard from '../../components/common/InfoCard';
import { FiDownload, FiDollarSign } from 'react-icons/fi';

const FEATURE_LABELS = {
    IDADE: 'Idade do Paciente',
    DIAS_PERM: 'Dias de Permanência',
    DIAG_PRINC: 'Diagnóstico Principal (CID-10)',
    PROC_REA: 'Procedimento Realizado (SIGTAP)',
    UTI_MES_TO: 'Total de Diárias de UTI',
    SEXO: 'Sexo',
    CAR_INT: 'Caráter da Internação',
    MORTE: 'Desfecho Óbito',
    TP_UNID: 'Tipo de Unidade Hospitalar',
    NAT_JUR: 'Natureza Jurídica do Hospital',
    LEITHOSP: 'Nº Total de Leitos do Hospital',
    ATIVIDAD: 'Hospital de Ensino/Pesquisa',
};

const CustoInternacaoViewerPage = () => {
    usePageTitle('Resultado da Previsão de Custo');
    const location = useLocation();
    const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
    const taskId = queryParams.get('taskId');

    const [taskDetails, setTaskDetails] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

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
                const response = await axios.get(`/api/pipelines/custo-internacao/tasks/${taskId}/`, {
                    headers: { 'Authorization': `Token ${token}` }
                });
                setTaskDetails(response.data);
            } catch (err) {
                setError("Não foi possível carregar os detalhes da tarefa.");
                console.error("Erro ao buscar detalhes da tarefa:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchTaskDetails();
    }, [taskId]);

    const custoPrevisto = taskDetails?.custo_previsto;

    const formatCurrency = (value) => {
        if (value == null) return '---';
        return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen p-10">
                <LoadingSpinner size="lg" color="blue" />
                <p className="mt-4 text-gray-700">Carregando resultado da previsão de custo...</p>
            </div>
        );
    }

    if (error) return <FeedbackMessage message={error} type="error" />;
    if (!taskDetails) return <FeedbackMessage message="Nenhum detalhe da tarefa encontrado." type="info" />;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <h1 className="text-3xl text-center text-gray-800 mb-8">Resultado da Previsão de Custo de Internação</h1>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 max-w-7xl mx-auto">
                {/* Coluna de Custo e Dados da Internação */}
                <div className="lg:col-span-1 space-y-8">
                    <div className="bg-white p-6 rounded-lg shadow-md text-center">
                        <h2 className="text-xl font-semibold text-gray-700 mb-2 flex items-center justify-center gap-2">
                            <FiDollarSign className="text-green-600" /> Custo Estimado
                        </h2>
                        <div className="p-4 rounded-lg bg-green-600 text-white">
                            <p className="text-4xl font-black">{formatCurrency(custoPrevisto)}</p>
                        </div>
                        <p className="text-xs text-gray-500 mt-2">Custo total previsto para esta internação.</p>
                    </div>

                    <div className="bg-white p-6 rounded-lg shadow-md">
                        <h2 className="text-xl font-semibold text-gray-700 mb-4">Dados da Internação</h2>
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

                {/* Coluna da Explicação SHAP */}
                <div className="lg:col-span-2 space-y-4">
                    <InfoCard title="Como Interpretar o Gráfico de Explicação (SHAP)">
                        <p>Este gráfico "waterfall" mostra como cada característica da internação influenciou o custo previsto.</p>
                        <ul className="list-disc list-inside space-y-1 mt-2 text-xs">
                            <li><b className="text-gray-800">Valor Base (E[f(x)]):</b> É o custo médio (em log) de todas as internações no conjunto de treino.</li>
                            <li><b className="text-red-600">Setas Vermelhas (↗):</b> Fatores que AUMENTARAM o custo estimado.</li>
                            <li><b className="text-blue-600">Setas Azuis (↘):</b> Fatores que DIMINUÍRAM o custo estimado.</li>
                            <li><b className="text-gray-800">Valor Final (f(x)):</b> O custo final previsto (em log) após somar todos os impactos.</li>
                        </ul>
                    </InfoCard>

                    <div className="bg-white p-4 rounded-lg shadow-md">
                        <h2 className="text-xl font-semibold text-gray-700 mb-2">Explicação da Previsão de Custo</h2>
                        {taskDetails.output_image_url ? (
                            <>
                                <a href={taskDetails.output_image_url} target="_blank" rel="noopener noreferrer" className="block border rounded-lg overflow-hidden hover:opacity-90 transition-opacity">
                                    <img src={taskDetails.output_image_url} alt="Gráfico SHAP - Explicação do Custo" className="w-full h-auto" />
                                </a>
                                <a
                                    href={taskDetails.output_image_url}
                                    download={`shap_custo_${taskId.substring(0, 8)}.png`}
                                    className="mt-4 bg-green-600 hover:bg-green-700 text-white font-bold py-2 px-4 rounded inline-flex items-center"
                                >
                                    <FiDownload className="mr-2" /> Baixar Imagem SHAP
                                </a>
                            </>
                        ) : (
                            <FeedbackMessage message="Imagem SHAP não disponível para esta tarefa." type="info" />
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CustoInternacaoViewerPage;
