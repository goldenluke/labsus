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

const PipelineRiscoPerinatalPage = () => {
    usePageTitle('Risco Perinatal');
    const navigate = useNavigate();

    const [patientData, setPatientData] = useState({
        IDADEMAE: 25,
        ESCMAE2010: 4,
        RACACORMAE: 1,
        QTDFILVIVO: 1,
        QTDFILMORT: 0,
        CONSPRENAT: 6,
        MESPRENAT: 2,
        PARTO: 1,
        GRAVIDEZ: 1,
        ESTCIVMAE: 1,
    });
    const [outputName, setOutputName] = useState('');

    const [taskId, setTaskId] = useState(null);
    const {
        isPending, isSuccess, isFailure,
        progress, message: taskMessage, error: taskError
    } = useCeleryTaskStatus(taskId, '/api/pipelines/risco-perinatal/tasks/');

    const handleChange = (e) => {
        const { name, value, type } = e.target;
        const parsedValue = type === 'number' ? parseInt(value, 10) : value;
        setPatientData(prev => ({ ...prev, [name]: parsedValue }));
    };

    const triggerPipeline = useCallback(async () => {
        setTaskId(null);
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.post('/api/pipelines/risco-perinatal/trigger/', {
                patient_data: patientData,
                output_filename: outputName || `risco_perinatal_${Date.now()}`,
            }, { headers: { 'Authorization': `Token ${token}` } });

            setTaskId(response.data.task_id);
        } catch (err) {
            alert(`Falha ao disparar previsão: ${err.response?.data?.error || err.message}`);
        }
    }, [patientData, outputName]);

    useEffect(() => {
        if (isSuccess && taskId) {
            const timer = setTimeout(() => {
                navigate(`/dashboards/risco-perinatal/viewer?taskId=${taskId}`);
            }, 1500);
            return () => clearTimeout(timer);
        }
    }, [isSuccess, taskId, navigate]);

    const isRunButtonDisabled = isPending;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase">Risco Perinatal</h1>
                <p className="text-gray-500 mt-2 text-lg">Previsão de risco perinatal com modelo LightGBM baseado em dados do SINASC.</p>
            </header>

            <div className="max-w-5xl mx-auto space-y-8 pb-12">

                {isFailure && <FeedbackMessage message={`Erro na previsão: ${taskError}`} type="error" />}

                <InfoCard title="Sobre este modelo de IA">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        O modelo <strong>Risco Perinatal</strong> utiliza um <strong>LightGBM Classifier</strong> treinado com
                        10 variáveis do <strong>SINASC</strong> (Sistema de Informação sobre Nascidos Vivos).
                        Avalia fatores maternos como idade, escolaridade, raça/cor, história obstétrica e cuidados pré-natal
                        para estimar o risco perinatal.
                        A explicabilidade é fornecida via <strong>SHAP</strong>.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-6">

                    {/* PASSO 1: DADOS DEMOGRÁFICOS DA MÃE */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <FiUser className="text-blue-500" /> 1. Dados Demográficos da Mãe
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Idade da Mãe</label>
                                <input type="number" name="IDADEMAE" value={patientData.IDADEMAE} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 focus:ring-2 focus:ring-blue-500 outline-none" />
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Escolaridade da Mãe</label>
                                <select name="ESCMAE2010" value={patientData.ESCMAE2010} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500">
                                    <option value={0}>Ignorado</option>
                                    <option value={1}>Sem Escolaridade</option>
                                    <option value={2}>Fund I</option>
                                    <option value={3}>Fund II</option>
                                    <option value={4}>Médio</option>
                                    <option value={5}>Superior Incompleto</option>
                                    <option value={6}>Superior Completo</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Raça/Cor da Mãe</label>
                                <select name="RACACORMAE" value={patientData.RACACORMAE} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500">
                                    <option value={1}>Branca</option>
                                    <option value={2}>Negra</option>
                                    <option value={3}>Amarela</option>
                                    <option value={4}>Parda</option>
                                    <option value={5}>Indígena</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Estado Civil da Mãe</label>
                                <select name="ESTCIVMAE" value={patientData.ESTCIVMAE} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500">
                                    <option value={1}>Solteira</option>
                                    <option value={2}>Casada</option>
                                    <option value={3}>Viúva</option>
                                    <option value={4}>Separada</option>
                                    <option value={5}>União Estável</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* PASSO 2: HISTÓRIA OBSTÉTRICA */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <FiHeart className="text-blue-500" /> 2. História Obstétrica
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Filhos Vivos Anteriores</label>
                                <input type="number" name="QTDFILVIVO" value={patientData.QTDFILVIVO} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 focus:ring-2 focus:ring-blue-500 outline-none" />
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Filhos Mortos Anteriores</label>
                                <input type="number" name="QTDFILMORT" value={patientData.QTDFILMORT} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 focus:ring-2 focus:ring-blue-500 outline-none" />
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Tipo de Gravidez</label>
                                <select name="GRAVIDEZ" value={patientData.GRAVIDEZ} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500">
                                    <option value={1}>Única</option>
                                    <option value={2}>Dupla</option>
                                    <option value={3}>Tripla+</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* PASSO 3: PRÉ-NATAL E PARTO */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <FiActivity className="text-blue-500" /> 3. Pré-Natal e Parto
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Consultas Pré-Natal</label>
                                <input type="number" name="CONSPRENAT" value={patientData.CONSPRENAT} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 focus:ring-2 focus:ring-blue-500 outline-none" />
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Mês Início Pré-Natal</label>
                                <input type="number" name="MESPRENAT" value={patientData.MESPRENAT} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 focus:ring-2 focus:ring-blue-500 outline-none" />
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Tipo de Parto</label>
                                <select name="PARTO" value={patientData.PARTO} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500">
                                    <option value={1}>Vaginal</option>
                                    <option value={2}>Cesárea</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* PASSO 4: NOME DO ARQUIVO */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <FiDatabase className="text-blue-500" /> 4. Nome do Arquivo de Saída
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

                {/* BOTÃO DE EXECUÇÃO */}
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
                                    <span>{taskMessage || 'CALCULANDO RISCO...'} ({progress}%)</span>
                                </>
                            ) : isSuccess ? (
                                <>
                                    <FiCheckCircle size={20} />
                                    <span>SUCESSO! REDIRECIONANDO...</span>
                                </>
                            ) : (
                                <>
                                    <FiHeart size={20} />
                                    <span>CALCULAR RISCO PERINATAL</span>
                                </>
                            )}
                        </span>
                    </button>
                </div>
            </div>

            <footer className="mt-20 py-8 border-t border-gray-200 text-center">
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-gray-200 shadow-sm text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                    <FiHeart /> LabSUS Risco Perinatal Engine • LightGBM Classifier
                </div>
            </footer>
        </div>
    );
};

export default PipelineRiscoPerinatalPage;
