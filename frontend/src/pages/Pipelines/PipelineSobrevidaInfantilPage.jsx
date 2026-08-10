import React, { useState, useCallback, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
    FiHeart, FiArrowRightCircle, FiDatabase, FiUser,
    FiActivity, FiHome, FiCheckCircle
} from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import InfoCard from '../../components/common/InfoCard';

const PipelineSobrevidaInfantilPage = () => {
    usePageTitle('Sobrevida Infantil');
    const navigate = useNavigate();

    const [patientData, setPatientData] = useState({
        PESO: 3200,
        GESTACAO: 5,
        APGAR5: 8,
        IDADEMAE: 28,
        ESCMAE2010: 4,
        CONSPRENAT: 6,
        QTDFILVIVO: 1,
        QTDFILMORT: 0,
        PARTO: 1,
        RACACORMAE: 1,
        QTLEIT39: 5,
        ATIVIDAD: 3,
    });

    const [taskId, setTaskId] = useState(null);
    const {
        isPending, isSuccess, isFailure,
        progress, message: taskMessage, error: taskError
    } = useCeleryTaskStatus(taskId, '/api/pipelines/sobrevida-infantil/tasks/');

    const handleChange = (e) => {
        const { name, value, type } = e.target;
        const parsedValue = type === 'number' ? parseInt(value, 10) : value;
        setPatientData(prev => ({ ...prev, [name]: parsedValue }));
    };

    const triggerPipeline = useCallback(async () => {
        setTaskId(null);
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.post('/api/pipelines/sobrevida-infantil/trigger/', {
                patient_data: patientData,
            }, { headers: { 'Authorization': `Token ${token}` } });

            setTaskId(response.data.task_id);
        } catch (err) {
            alert(`Falha ao disparar previsão: ${err.response?.data?.error || err.message}`);
        }
    }, [patientData]);

    useEffect(() => {
        if (isSuccess && taskId) {
            const timer = setTimeout(() => {
                navigate(`/dashboards/sobrevida-infantil/viewer?taskId=${taskId}`);
            }, 1500);
            return () => clearTimeout(timer);
        }
    }, [isSuccess, taskId, navigate]);

    const isRunButtonDisabled = isPending;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase">Sobrevida Infantil</h1>
                <p className="text-gray-500 mt-2 text-lg">Previsão de probabilidade de mortalidade infantil com base em dados do SINASC.</p>
            </header>

            <div className="max-w-5xl mx-auto space-y-8 pb-12">

                {isFailure && <FeedbackMessage message={`Erro na previsão: ${taskError}`} type="error" />}

                <InfoCard title="Sobre este modelo de IA">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        O modelo <strong>Sobrevida Infantil</strong> utiliza um <strong>LightGBM</strong> classificador
                        treinado com 12 variáveis do <strong>SINASC</strong> (Sistema de Informação sobre Nascidos Vivos)
                        para prever a probabilidade de mortalidade infantil.
                        A explicabilidade é fornecida via <strong>SHAP</strong>, permitindo identificar
                        quais fatores mais influenciam a previsão para cada caso.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-6">

                    {/* PASSO 1: DADOS DO RECÉM-NASCIDO */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <FiHeart className="text-red-500" /> 1. Dados do Recém-Nascido
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Peso ao Nascer (g)</label>
                                <input type="number" name="PESO" value={patientData.PESO} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 focus:ring-2 focus:ring-red-500 outline-none" />
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Gestação</label>
                                <select name="GESTACAO" value={patientData.GESTACAO} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-red-500">
                                    <option value={1}>&lt;22 semanas</option>
                                    <option value={2}>22-27 semanas</option>
                                    <option value={3}>28-31 semanas</option>
                                    <option value={4}>32-36 semanas</option>
                                    <option value={5}>37-41 semanas</option>
                                    <option value={6}>42+ semanas</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">APGAR 5min</label>
                                <input type="number" name="APGAR5" value={patientData.APGAR5} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 focus:ring-2 focus:ring-red-500 outline-none" />
                            </div>
                        </div>
                    </div>

                    {/* PASSO 2: DADOS DA MÃE */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <FiUser className="text-red-500" /> 2. Dados da Mãe
                        </h2>
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                            <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                                <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Idade da Mãe</label>
                                <input type="number" name="IDADEMAE" value={patientData.IDADEMAE} onChange={handleChange} className="w-full bg-transparent font-bold text-red-600 outline-none" />
                            </div>
                            <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                                <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Escolaridade da Mãe</label>
                                <select name="ESCMAE2010" value={patientData.ESCMAE2010} onChange={handleChange} className="w-full bg-transparent font-bold text-red-600 outline-none">
                                    <option value={0}>Ignorado</option>
                                    <option value={1}>Sem Escolaridade</option>
                                    <option value={2}>Fundamental I</option>
                                    <option value={3}>Fundamental II</option>
                                    <option value={4}>Médio</option>
                                    <option value={5}>Superior Incompleto</option>
                                    <option value={6}>Superior Completo</option>
                                </select>
                            </div>
                            <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                                <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Raça/Cor da Mãe</label>
                                <select name="RACACORMAE" value={patientData.RACACORMAE} onChange={handleChange} className="w-full bg-transparent font-bold text-red-600 outline-none">
                                    <option value={1}>Branca</option>
                                    <option value={2}>Negra</option>
                                    <option value={3}>Amarela</option>
                                    <option value={4}>Parda</option>
                                    <option value={5}>Indígena</option>
                                </select>
                            </div>
                            <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                                <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Filhos Vivos Anteriores</label>
                                <input type="number" name="QTDFILVIVO" value={patientData.QTDFILVIVO} onChange={handleChange} className="w-full bg-transparent font-bold text-red-600 outline-none" />
                            </div>
                            <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                                <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Filhos Mortos Anteriores</label>
                                <input type="number" name="QTDFILMORT" value={patientData.QTDFILMORT} onChange={handleChange} className="w-full bg-transparent font-bold text-red-600 outline-none" />
                            </div>
                            <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                                <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Consultas Pré-Natal</label>
                                <input type="number" name="CONSPRENAT" value={patientData.CONSPRENAT} onChange={handleChange} className="w-full bg-transparent font-bold text-red-600 outline-none" />
                            </div>
                            <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                                <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Tipo de Parto</label>
                                <select name="PARTO" value={patientData.PARTO} onChange={handleChange} className="w-full bg-transparent font-bold text-red-600 outline-none">
                                    <option value={1}>Vaginal</option>
                                    <option value={2}>Cesárea</option>
                                </select>
                            </div>
                            <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                                <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Atividade Profissional</label>
                                <select name="ATIVIDAD" value={patientData.ATIVIDAD} onChange={handleChange} className="w-full bg-transparent font-bold text-red-600 outline-none">
                                    <option value={1}>Doméstica</option>
                                    <option value={2}>Estudante</option>
                                    <option value={3}>Assalariada</option>
                                    <option value={4}>Autônoma</option>
                                    <option value={5}>Outra</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* PASSO 3: DADOS DO HOSPITAL */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <FiHome className="text-red-500" /> 3. Dados do Hospital
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Nº Leitos Hospital</label>
                                <input type="number" name="QTLEIT39" value={patientData.QTLEIT39} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-red-500" />
                            </div>
                        </div>
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
                                    <span>{taskMessage || 'CALCULANDO SOBREVIVÊNCIA...'} ({progress}%)</span>
                                </>
                            ) : isSuccess ? (
                                <>
                                    <FiCheckCircle size={20} />
                                    <span>SUCESSO! REDIRECIONANDO...</span>
                                </>
                            ) : (
                                <>
                                    <FiHeart size={20} />
                                    <span>CALCULAR SOBREVIVÊNCIA INFANTIL</span>
                                </>
                            )}
                        </span>
                    </button>
                </div>
            </div>

            <footer className="mt-20 py-8 border-t border-gray-200 text-center">
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-gray-200 shadow-sm text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                    <FiHeart /> LabSUS Sobrevida Infantil Engine • LightGBM Classifier
                </div>
            </footer>
        </div>
    );
};

export default PipelineSobrevidaInfantilPage;
