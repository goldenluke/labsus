import React, { useState, useCallback, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
    FiAlertTriangle, FiDatabase, FiMapPin, FiCalendar,
    FiCheckCircle, FiActivity
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

const ANOS_DISPONIVEIS = [2020, 2021, 2022, 2023, 2024, 2025, 2026];

const PipelineDeteccaoSurtosPage = () => {
    usePageTitle('Detecção de Surtos');
    const navigate = useNavigate();

    const [ufs, setUfs] = useState(['TO']);
    const [anos, setAnos] = useState([2021, 2022, 2023, 2024]);
    const [agravo, setAgravo] = useState('DENG');
    const [gravos, setGravos] = useState([]);
    const [outputCsvName, setOutputCsvName] = useState('');

    const [taskId, setTaskId] = useState(null);
    const {
        isPending, isSuccess, isFailure,
        progress, message: taskMessage, error: taskError
    } = useCeleryTaskStatus(taskId, '/api/pipelines/deteccao-surtos/tasks/');

    useEffect(() => {
        const fetchGravos = async () => {
            try {
                const token = localStorage.getItem('authToken');
                const res = await axios.get('/api/pipelines/deteccao-surtos/gravos/', {
                    headers: { 'Authorization': `Token ${token}` }
                });
                setGravos(res.data);
            } catch (err) {
                console.error("Erro ao carregar gravos:", err);
            }
        };
        fetchGravos();
    }, []);

    const toggleUf = (uf) => {
        setUfs(prev => prev.includes(uf) ? prev.filter(u => u !== uf) : [...prev, uf]);
    };

    const toggleAno = (ano) => {
        setAnos(prev => prev.includes(ano) ? prev.filter(a => a !== ano) : [...prev, ano]);
    };

    const triggerPipeline = useCallback(async () => {
        setTaskId(null);
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.post('/api/pipelines/deteccao-surtos/trigger/', {
                ufs,
                anos,
                agravo,
                output_filename: outputCsvName || `alertas_${agravo}_${Date.now()}`,
            }, { headers: { 'Authorization': `Token ${token}` } });

            setTaskId(response.data.task_id);
        } catch (err) {
            alert(`Falha ao disparar detecção: ${err.response?.data?.error || err.message}`);
        }
    }, [ufs, anos, agravo, outputCsvName]);

    useEffect(() => {
        if (isSuccess && taskId) {
            const timer = setTimeout(() => {
                navigate(`/dashboards/deteccao-surtos/viewer?taskId=${taskId}`);
            }, 1500);
            return () => clearTimeout(timer);
        }
    }, [isSuccess, taskId, navigate]);

    const isRunButtonDisabled = isPending || ufs.length === 0 || anos.length === 0;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase">Detecção de Surtos Epidemiológicos</h1>
                <p className="text-gray-500 mt-2 text-lg">Alerta precoce para epidemias usando Prophet e Canal Endêmico Dinâmico.</p>
            </header>

            <div className="max-w-5xl mx-auto space-y-8 pb-12">

                {isFailure && <FeedbackMessage message={`Erro na detecção: ${taskError}`} type="error" />}

                <InfoCard title="Sobre este modelo de IA">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Este pipeline utiliza <strong>Facebook Prophet</strong> para construir um Canal Endêmico Dinâmico para cada município.
                        É treinado com histórico de notificações do <strong>SINAN</strong> (3-4 anos) para aprender a sazonalidade. Quando os casos
                        observados superam o <strong>limite superior de 95% de confiança</strong> por 2+ semanas consecutivas, um alerta de surto é gerado.
                        Requer pelo menos 20 semanas de dados por município.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-6">

                    {/* PASSO 1: NOME DO RELATÓRIO */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <FiDatabase className="text-blue-500" /> 1. Nome do Relatório de Saída
                        </h2>
                        <input
                            type="text"
                            value={outputCsvName}
                            onChange={e => setOutputCsvName(e.target.value)}
                            placeholder="Nome do CSV de alertas (opcional)"
                            className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
                        />
                    </div>

                    {/* PASSO 2: AGRAVO */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <FiActivity className="text-blue-500" /> 2. Agravo de Notificação
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Doença</label>
                                <select
                                    value={agravo}
                                    onChange={e => setAgravo(e.target.value)}
                                    className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    {gravos.length > 0 ? (
                                        gravos.map(g => (
                                            <option key={g.value} value={g.value}>{g.label} ({g.value})</option>
                                        ))
                                    ) : (
                                        <>
                                            <option value="DENG">Dengue (DENG)</option>
                                            <option value="CHIK">Chikungunya (CHIK)</option>
                                            <option value="ZIKA">Zika (ZIKA)</option>
                                            <option value="MALA">Malária (MALA)</option>
                                            <option value="LEPT">Leptospirose (LEPT)</option>
                                            <option value="HANT">Hantavirose (HANT)</option>
                                            <option value="TUBE">Tuberculose (TUBE)</option>
                                            <option value="MENI">Meningite (MENI)</option>
                                            <option value="COQU">Coqueluche (COQU)</option>
                                            <option value="HEPA">Hepatites Virais (HEPA)</option>
                                            <option value="SIFA">Sífilis Adquirida (SIFA)</option>
                                            <option value="SIFC">Sífilis Congênita (SIFC)</option>
                                        </>
                                    )}
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* PASSO 3: ESTADOS */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <FiMapPin className="text-blue-500" /> 3. Estados (UFs)
                        </h2>
                        <div className="grid grid-cols-6 sm:grid-cols-9 md:grid-cols-10 lg:grid-cols-14 gap-2">
                            {UFS_BRASIL.map(uf => (
                                <button
                                    key={uf}
                                    type="button"
                                    onClick={() => toggleUf(uf)}
                                    className={`py-2 rounded-xl text-xs font-black transition-all
                                        ${ufs.includes(uf)
                                            ? 'bg-blue-600 text-white shadow-md'
                                            : 'bg-gray-50 text-gray-400 border border-gray-200 hover:bg-gray-100 hover:text-gray-600'}`}
                                >
                                    {uf}
                                </button>
                            ))}
                        </div>
                        <p className="text-[10px] font-bold text-gray-400 uppercase mt-3 tracking-widest">
                            Selecionados: {ufs.length} estado(s)
                        </p>
                    </div>

                    {/* PASSO 4: ANOS */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <FiCalendar className="text-blue-500" /> 4. Anos Históricos
                        </h2>
                        <p className="text-[10px] font-bold text-gray-400 uppercase mb-4 tracking-widest">
                            Recomenda-se 3-4 anos para o Prophet aprender a sazonalidade anual.
                        </p>
                        <div className="flex flex-wrap gap-2">
                            {ANOS_DISPONIVEIS.map(ano => (
                                <button
                                    key={ano}
                                    type="button"
                                    onClick={() => toggleAno(ano)}
                                    className={`px-5 py-2.5 rounded-xl text-sm font-black transition-all
                                        ${anos.includes(ano)
                                            ? 'bg-green-600 text-white shadow-md'
                                            : 'bg-gray-50 text-gray-400 border border-gray-200 hover:bg-gray-100 hover:text-gray-600'}`}
                                >
                                    {ano}
                                </button>
                            ))}
                        </div>
                        <p className="text-[10px] font-bold text-gray-400 uppercase mt-3 tracking-widest">
                            Selecionados: {anos.length} ano(s)
                        </p>
                    </div>
                </fieldset>

                {/* BOTÃO DE EXECUÇÃO */}
                <div className="mt-10">
                    <button
                        onClick={triggerPipeline}
                        disabled={isRunButtonDisabled}
                        className={`w-full relative py-4 rounded-2xl font-black text-white transition-all shadow-xl overflow-hidden
                            ${isRunButtonDisabled ? 'bg-gray-300 cursor-not-allowed' : 'bg-red-600 hover:bg-red-700 active:scale-[0.98]'}`}
                    >
                        {isPending && (
                            <div
                                className="absolute top-0 left-0 h-full bg-red-800/40 transition-all duration-500 ease-out"
                                style={{ width: `${progress}%` }}
                            ></div>
                        )}

                        <span className="relative z-10 flex items-center justify-center gap-3 tracking-widest uppercase">
                            {isPending ? (
                                <>
                                    <LoadingSpinner size="sm" color="white" />
                                    <span>{taskMessage || 'DETECTANDO SURTOS...'} ({progress}%)</span>
                                </>
                            ) : isSuccess ? (
                                <>
                                    <FiCheckCircle size={20} />
                                    <span>SUCESSO! REDIRECIONANDO...</span>
                                </>
                            ) : (
                                <>
                                    <FiAlertTriangle size={20} />
                                    <span>INICIAR DETECÇÃO DE SURTOS</span>
                                </>
                            )}
                        </span>
                    </button>
                </div>
            </div>

            <footer className="mt-20 py-8 border-t border-gray-200 text-center">
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-gray-200 shadow-sm text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                    <FiAlertTriangle /> LabSUS Outbreak Detection Engine • Prophet + SINAN
                </div>
            </footer>
        </div>
    );
};

export default PipelineDeteccaoSurtosPage;
