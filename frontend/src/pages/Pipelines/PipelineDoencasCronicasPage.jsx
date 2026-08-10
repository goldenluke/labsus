import React, { useState, useCallback, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
    FiActivity, FiArrowRightCircle, FiDatabase, FiMapPin,
    FiCheckCircle
} from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import InfoCard from '../../components/common/InfoCard';

const UFS_BRASIL = [
    'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG',
    'PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'
];

const ANOS_DISPONIVEIS = [2021, 2022, 2023, 2024, 2025];

const PipelineDoencasCronicasPage = () => {
    usePageTitle('Doenças Crônicas');
    const navigate = useNavigate();

    const [uf, setUf] = useState('TO');
    const [cidDoenca, setCidDoenca] = useState('I50');
    const [anoSnapshot, setAnoSnapshot] = useState(2023);
    const [outputName, setOutputName] = useState('');

    const [taskId, setTaskId] = useState(null);
    const {
        isPending, isSuccess, isFailure,
        progress, message: taskMessage, error: taskError
    } = useCeleryTaskStatus(taskId, '/api/pipelines/doencas-cronicas/tasks/');

    const triggerPipeline = useCallback(async () => {
        setTaskId(null);
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.post('/api/pipelines/doencas-cronicas/trigger/', {
                uf,
                cid_doenca: cidDoenca,
                ano_snapshot: anoSnapshot,
                output_filename: outputName || `doencas_cronicas_${Date.now()}`,
            }, { headers: { 'Authorization': `Token ${token}` } });

            setTaskId(response.data.task_id);
        } catch (err) {
            alert(`Falha ao disparar análise: ${err.response?.data?.error || err.message}`);
        }
    }, [uf, cidDoenca, anoSnapshot, outputName]);

    useEffect(() => {
        if (isSuccess && taskId) {
            const timer = setTimeout(() => {
                navigate(`/dashboards/doencas-cronicas/viewer?taskId=${taskId}`);
            }, 1500);
            return () => clearTimeout(timer);
        }
    }, [isSuccess, taskId, navigate]);

    const isRunButtonDisabled = isPending || !uf || !cidDoenca || !anoSnapshot;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase">Doenças Crônicas</h1>
                <p className="text-gray-500 mt-2 text-lg">Identificação de coorte de pacientes crônicos com risco de hospitalização em 6 meses.</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">

                {isFailure && <FeedbackMessage message={`Erro na análise: ${taskError}`} type="error" />}

                <InfoCard title="Sobre este modelo de IA">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Este modelo usa um <strong>LightGBM Classifier</strong> treinado sobre a jornada de atendimento
                        (SIH + SIA) de pacientes com uma doença crônica específica, para prever a probabilidade de
                        <strong> hospitalização nos 6 meses seguintes</strong> ao ano de referência. O resultado é uma
                        coorte inteira de pacientes pontuados, não uma previsão individual.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-6">

                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <FiMapPin className="text-blue-500" /> 1. Estado (UF)
                        </h2>
                        <div className="grid grid-cols-6 sm:grid-cols-9 md:grid-cols-10 lg:grid-cols-14 gap-2">
                            {UFS_BRASIL.map(item => (
                                <button
                                    key={item}
                                    type="button"
                                    onClick={() => setUf(item)}
                                    className={`py-2 rounded-xl text-xs font-black transition-all ${
                                        uf === item
                                            ? 'bg-blue-600 text-white shadow-md'
                                            : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
                                    }`}
                                >
                                    {item}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <FiActivity className="text-blue-500" /> 2. Doença e Ano de Referência
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">CID-10 (Doença Crônica)</label>
                                <input
                                    type="text"
                                    value={cidDoenca}
                                    onChange={e => setCidDoenca(e.target.value.toUpperCase())}
                                    placeholder="Ex: I50 (Insuficiência Cardíaca)"
                                    className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 focus:ring-2 focus:ring-blue-500 outline-none"
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Ano de Referência (Snapshot)</label>
                                <select
                                    value={anoSnapshot}
                                    onChange={e => setAnoSnapshot(parseInt(e.target.value, 10))}
                                    className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    {ANOS_DISPONIVEIS.map(ano => (
                                        <option key={ano} value={ano}>{ano}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                        <p className="text-xs text-gray-400 mt-4">
                            O histórico dos 12 meses anteriores a 1º de janeiro deste ano será usado como features;
                            os 6 meses seguintes serão usados para avaliar se o paciente foi de fato hospitalizado.
                        </p>
                    </div>

                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <FiDatabase className="text-blue-500" /> 3. Nome do Arquivo de Saída
                        </h2>
                        <input
                            type="text"
                            value={outputName}
                            onChange={e => setOutputName(e.target.value)}
                            placeholder="Nome do CSV de resultado (opcional)"
                            className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
                        />
                    </div>
                </fieldset>

                <div className="mt-10">
                    <button
                        onClick={triggerPipeline}
                        disabled={isRunButtonDisabled}
                        className={`w-full relative py-4 rounded-2xl font-black text-white transition-all shadow-xl overflow-hidden
                            ${isRunButtonDisabled ? 'bg-gray-300 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700 active:scale-[0.98]'}`}
                    >
                        {isPending && (
                            <div
                                className="absolute top-0 left-0 h-full bg-green-800/40 transition-all duration-500 ease-out"
                                style={{ width: `${progress}%` }}
                            ></div>
                        )}

                        <span className="relative z-10 flex items-center justify-center gap-3 tracking-widest uppercase">
                            {isPending ? (
                                <>
                                    <LoadingSpinner size="sm" color="white" />
                                    <span>{taskMessage || 'PROCESSANDO...'} ({progress}%)</span>
                                </>
                            ) : isSuccess ? (
                                <>
                                    <FiCheckCircle size={20} />
                                    <span>SUCESSO! REDIRECIONANDO...</span>
                                </>
                            ) : (
                                <>
                                    <FiArrowRightCircle size={20} />
                                    <span>ANALISAR COORTE DE PACIENTES CRÔNICOS</span>
                                </>
                            )}
                        </span>
                    </button>
                </div>
            </div>

            <footer className="mt-20 py-8 border-t border-gray-200 text-center">
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-gray-200 shadow-sm text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                    <FiActivity /> LabSUS Doenças Crônicas Engine • LightGBM Classifier
                </div>
            </footer>
        </div>
    );
};

export default PipelineDoencasCronicasPage;
