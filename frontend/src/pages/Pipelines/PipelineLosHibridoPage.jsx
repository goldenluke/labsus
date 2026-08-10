import React, { useState, useCallback, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
    FiClock, FiArrowRightCircle, FiDatabase, FiUser,
    FiActivity, FiHome, FiCheckCircle
} from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import InfoCard from '../../components/common/InfoCard';

const DEPARTAMENTOS = [
    { value: 'Cirurgia', label: 'Cirurgia' },
    { value: 'Clinica_Medica', label: 'Clínica Médica' },
    { value: 'Obstetricia', label: 'Obstetrícia' },
    { value: 'Pediatria', label: 'Pediatria' },
];

const PipelineLosHibridoPage = () => {
    usePageTitle('LOS Híbrido - Tempo de Permanência');
    const navigate = useNavigate();

    const [departamento, setDepartamento] = useState('Cirurgia');
    const [patientData, setPatientData] = useState({
        IDADE: 55,
        UTI_MES_TO: 0,
        LEITHOSP: 200,
        COMPLEXIDADE_MEDIA: 3,
        SEXO: 1,
        CAR_INT: 2,
        TP_UNID: 5,
        ATIVIDAD: 0,
        CAPITULO_CID: 9,
    });
    const [outputName, setOutputName] = useState('');

    const [taskId, setTaskId] = useState(null);
    const {
        isPending, isSuccess, isFailure,
        progress, message: taskMessage, error: taskError
    } = useCeleryTaskStatus(taskId, '/api/pipelines/los-hibrido/tasks/');

    const handleChange = (e) => {
        const { name, value, type } = e.target;
        const parsedValue = type === 'number' ? parseInt(value, 10) : value;
        setPatientData(prev => ({ ...prev, [name]: parsedValue }));
    };

    const triggerPipeline = useCallback(async () => {
        setTaskId(null);
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.post('/api/pipelines/los-hibrido/trigger/', {
                patient_data: patientData,
                departamento: departamento,
                output_filename: outputName || `los_${departamento}_${Date.now()}`,
            }, { headers: { 'Authorization': `Token ${token}` } });

            setTaskId(response.data.task_id);
        } catch (err) {
            alert(`Falha ao disparar previsão: ${err.response?.data?.error || err.message}`);
        }
    }, [patientData, departamento, outputName]);

    useEffect(() => {
        if (isSuccess && taskId) {
            const timer = setTimeout(() => {
                navigate(`/dashboards/los-hibrido/viewer?taskId=${taskId}`);
            }, 1500);
            return () => clearTimeout(timer);
        }
    }, [isSuccess, taskId, navigate]);

    const isRunButtonDisabled = isPending;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase">LOS Híbrido</h1>
                <p className="text-gray-500 mt-2 text-lg">Previsão de tempo de permanência hospitalar com modelo híbrido (classificação + regressão).</p>
            </header>

            <div className="max-w-5xl mx-auto space-y-8 pb-12">

                {isFailure && <FeedbackMessage message={`Erro na previsão: ${taskError}`} type="error" />}

                <InfoCard title="Sobre este modelo de IA">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        O modelo <strong>LOS Híbrido</strong> utiliza dois estágios de <strong>LightGBM</strong>:
                        um classificador binário prevê se a permanência será <em>curta</em> ou <em>longa</em>,
                        e então um regressor especializado estima a quantidade exata de dias.
                        Cada departamento (Cirurgia, Clínica Médica, Obstetrícia, Pediatria) possui seus próprios modelos treinados.
                        A explicabilidade é fornecida via <strong>SHAP</strong>.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-6">

                    {/* PASSO 1: DEPARTAMENTO */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <FiActivity className="text-blue-500" /> 1. Departamento
                        </h2>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {DEPARTAMENTOS.map(d => (
                                <button
                                    key={d.value}
                                    onClick={() => setDepartamento(d.value)}
                                    className={`p-3 rounded-xl text-sm font-bold transition-all border-2 ${
                                        departamento === d.value
                                            ? 'bg-blue-600 text-white border-blue-600 shadow-md'
                                            : 'bg-gray-50 text-gray-600 border-gray-200 hover:border-blue-300'
                                    }`}
                                >
                                    {d.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* PASSO 2: DADOS DO PACIENTE */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <FiUser className="text-blue-500" /> 2. Dados do Paciente
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Idade</label>
                                <input type="number" name="IDADE" value={patientData.IDADE} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 focus:ring-2 focus:ring-blue-500 outline-none" />
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Sexo</label>
                                <select name="SEXO" value={patientData.SEXO} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500">
                                    <option value={1}>Masculino</option>
                                    <option value={3}>Feminino</option>
                                    <option value={9}>Ignorado</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Capítulo CID-10</label>
                                <input type="number" name="CAPITULO_CID" value={patientData.CAPITULO_CID} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 focus:ring-2 focus:ring-blue-500 outline-none" />
                            </div>
                        </div>
                    </div>

                    {/* PASSO 3: DADOS DA INTERNAÇÃO */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <FiActivity className="text-blue-500" /> 3. Dados da Internação
                        </h2>
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                            <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                                <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Diárias de UTI</label>
                                <input type="number" name="UTI_MES_TO" value={patientData.UTI_MES_TO} onChange={handleChange} className="w-full bg-transparent font-bold text-blue-600 outline-none" />
                            </div>
                            <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                                <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Caráter Admissão</label>
                                <select name="CAR_INT" value={patientData.CAR_INT} onChange={handleChange} className="w-full bg-transparent font-bold text-blue-600 outline-none">
                                    <option value={1}>Eletivo</option>
                                    <option value={2}>Urgência</option>
                                    <option value={3}>Acidente do Trabalho</option>
                                    <option value={4}>Outros Tipos</option>
                                </select>
                            </div>
                            <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                                <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Complexidade Média</label>
                                <input type="number" name="COMPLEXIDADE_MEDIA" value={patientData.COMPLEXIDADE_MEDIA} onChange={handleChange} min={1} max={5} className="w-full bg-transparent font-bold text-blue-600 outline-none" />
                            </div>
                        </div>
                    </div>

                    {/* PASSO 4: DADOS HOSPITALARES */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                            <FiHome className="text-blue-500" /> 4. Dados do Hospital
                        </h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Nº Total de Leitos</label>
                                <input type="number" name="LEITHOSP" value={patientData.LEITHOSP} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500" />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Tipo de Unidade</label>
                                <select name="TP_UNID" value={patientData.TP_UNID} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500">
                                    <option value={5}>Hospital Geral</option>
                                    <option value={1}>Ambulatório</option>
                                    <option value={2}>Centro de Especialidade</option>
                                    <option value={3}>Unidade Básica</option>
                                    <option value={4}>Hospital Especializado</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Hospital de Ensino</label>
                                <select name="ATIVIDAD" value={patientData.ATIVIDAD} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500">
                                    <option value={0}>Não</option>
                                    <option value={1}>Sim</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* PASSO 5: NOME DO ARQUIVO */}
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <FiDatabase className="text-blue-500" /> 5. Nome do Arquivo de Saída
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
                                    <span>{taskMessage || 'CALCULANDO LOS...'} ({progress}%)</span>
                                </>
                            ) : isSuccess ? (
                                <>
                                    <FiCheckCircle size={20} />
                                    <span>SUCESSO! REDIRECIONANDO...</span>
                                </>
                            ) : (
                                <>
                                    <FiClock size={20} />
                                    <span>PREVER TEMPO DE PERMANÊNCIA</span>
                                </>
                            )}
                        </span>
                    </button>
                </div>
            </div>

            <footer className="mt-20 py-8 border-t border-gray-200 text-center">
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-gray-200 shadow-sm text-[10px] font-bold text-gray-400 uppercase tracking-widest">
                    <FiClock /> LabSUS LOS Híbrido Engine • LightGBM Classifier + Regressor
                </div>
            </footer>
        </div>
    );
};

export default PipelineLosHibridoPage;
