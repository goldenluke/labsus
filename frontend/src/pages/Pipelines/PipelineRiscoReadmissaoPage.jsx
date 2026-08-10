import React, { useState, useCallback, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
    FiUserCheck, FiArrowRightCircle, FiDatabase, FiUser,
    FiActivity, FiHome, FiPlus, FiCheckCircle, FiInfo, FiX
} from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import InfoCard from '../../components/common/InfoCard';

const PipelineRiscoReadmissaoPage = () => {
    usePageTitle('Prever Risco de Readmissão');
    const navigate = useNavigate();

    // Estado do Paciente (Valores padrão baseados no modelo treinado)
    const [patientData, setPatientData] = useState({
        IDADE: 65,
        DIAS_PERM: 5,
        N_COMORBIDADES: 2,
        USOU_UTI: 0,
        SEXO: '1',
        RACA_COR: '99',
        CAR_INT: '02',
        DIAG_PRINC: 'I500',
        HOSP_NATUREZA: '3075',
        HOSP_LEITOS: 150,
    });

    const [outputCsvName, setOutputCsvName] = useState('');
    const [outputImageName, setOutputImageName] = useState('');

    // Controle da Task Celery
    const [taskId, setTaskId] = useState(null);
    const {
        isPending, isSuccess, isFailure,
        progress, message: taskMessage, error: taskError
    } = useCeleryTaskStatus(taskId, '/api/pipelines/risco-readmissao/tasks/');

    const handleChange = (e) => {
        const { name, value, type } = e.target;
        const parsedValue = type === 'number' ? parseInt(value, 10) : value;
        setPatientData(prev => ({ ...prev, [name]: parsedValue }));
    };

    const triggerPipeline = useCallback(async () => {
        setTaskId(null);
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.post('/api/pipelines/risco-readmissao/trigger/', {
                patient_data: patientData,
                output_csv_filename: outputCsvName || `previsao_paciente_${Date.now()}`,
                                              output_filename: outputImageName || `shap_explainer_${Date.now()}`,
            }, { headers: { 'Authorization': `Token ${token}` } });

            setTaskId(response.data.task_id);
        } catch (err) {
            alert(`Falha ao disparar predição: ${err.response?.data?.error || err.message}`);
        }
    }, [patientData, outputCsvName, outputImageName]);

    useEffect(() => {
        if (isSuccess && taskId) {
            const timer = setTimeout(() => {
                navigate(`/dashboards/risco-readmissao/viewer?taskId=${taskId}`);
            }, 1500);
            return () => clearTimeout(timer);
        }
    }, [isSuccess, taskId, navigate]);

    // Definição da variável que estava causando erro de ESLint
    const isRunButtonDisabled = isPending;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
        <header className="mb-8 text-center">
        <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase">Predição de Risco de Readmissão</h1>
        <p className="text-gray-500 mt-2 text-lg">Avalie a probabilidade de retorno hospitalar em 30 dias com explicabilidade via SHAP.</p>
        </header>

        <div className="max-w-5xl mx-auto space-y-8 pb-12">

        {isFailure && <FeedbackMessage message={`Erro na predição: ${taskError}`} type="error" />}

        <InfoCard title="Sobre este modelo de IA">
        <p className="text-sm leading-relaxed text-gray-600 font-medium">
        Este orquestrador utiliza um modelo <strong>LightGBM</strong> treinado em milhões de registros do SIH. Ele analisa variáveis demográficas e clínicas para gerar um score de risco individual. A saída inclui um gráfico de "cascata" (SHAP) que explica quais fatores aumentaram ou diminuíram o risco para este paciente específico.
        </p>
        </InfoCard>

        <fieldset disabled={isPending} className="space-y-6">

        {/* PASSO 1: IDENTIFICAÇÃO DOS RESULTADOS */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
        <FiDatabase className="text-blue-500" /> 1. Nomes dos Arquivos de Saída
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <input
        type="text"
        value={outputCsvName}
        onChange={e => setOutputCsvName(e.target.value)}
        placeholder="Nome do CSV de Previsão"
        className="p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
        />
        <input
        type="text"
        value={outputImageName}
        onChange={e => setOutputImageName(e.target.value)}
        placeholder="Nome da Imagem SHAP"
        className="p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
        />
        </div>
        </div>

        {/* PASSO 2: DADOS DEMOGRÁFICOS */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
        <FiUser className="text-blue-500" /> 2. Perfil Demográfico
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div>
        <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Idade do Paciente</label>
        <input type="number" name="IDADE" value={patientData.IDADE} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
        <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Sexo</label>
        <select name="SEXO" value={patientData.SEXO} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500">
        <option value="1">Masculino</option>
        <option value="3">Feminino</option>
        <option value="9">Ignorado</option>
        </select>
        </div>
        <div>
        <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Raça/Cor</label>
        <select name="RACA_COR" value={patientData.RACA_COR} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500">
        <option value="1">Branca</option>
        <option value="2">Preta</option>
        <option value="3">Parda</option>
        <option value="4">Amarela</option>
        <option value="5">Indígena</option>
        <option value="99">Ignorado</option>
        </select>
        </div>
        </div>
        </div>

        {/* PASSO 3: DETALHES CLÍNICOS */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
        <FiActivity className="text-blue-500" /> 3. Dados da Internação Atual
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
        <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Dias Permanência</label>
        <input type="number" name="DIAS_PERM" value={patientData.DIAS_PERM} onChange={handleChange} className="w-full bg-transparent font-bold text-blue-600 outline-none" />
        </div>
        <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
        <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Nº Comorbidades</label>
        <input type="number" name="N_COMORBIDADES" value={patientData.N_COMORBIDADES} onChange={handleChange} className="w-full bg-transparent font-bold text-blue-600 outline-none" />
        </div>
        <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
        <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Utilizou UTI?</label>
        <select name="USOU_UTI" value={patientData.USOU_UTI} onChange={handleChange} className="w-full bg-transparent font-bold text-blue-600 outline-none">
        <option value={0}>Não</option>
        <option value={1}>Sim</option>
        </select>
        </div>
        <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
        <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Caráter Admissão</label>
        <input type="text" name="CAR_INT" value={patientData.CAR_INT} onChange={handleChange} placeholder="Ex: 02" className="w-full bg-transparent font-bold text-blue-600 outline-none" />
        </div>
        <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
        <label className="block text-[9px] font-black text-gray-400 uppercase mb-1">Diagnóstico (CID)</label>
        <input type="text" name="DIAG_PRINC" value={patientData.DIAG_PRINC} onChange={handleChange} placeholder="Ex: I50" className="w-full bg-transparent font-bold text-blue-600 outline-none uppercase" />
        </div>
        </div>
        </div>

        {/* PASSO 4: INFRAESTRUTURA HOSPITALAR */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
        <FiHome className="text-blue-500" /> 4. Perfil da Unidade de Saúde
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
        <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Natureza Jurídica (Código)</label>
        <input type="text" name="HOSP_NATUREZA" value={patientData.HOSP_NATUREZA} onChange={handleChange} placeholder="Ex: 3075" className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
        <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Nº Total de Leitos</label>
        <input type="number" name="HOSP_LEITOS" value={patientData.HOSP_LEITOS} onChange={handleChange} className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        </div>
        </div>
        </fieldset>

        {/* BOTÃO DE EXECUÇÃO COM BARRA DE PROGRESSO INTERNA */}
        <div className="mt-10">
        <button
        onClick={triggerPipeline}
        disabled={isRunButtonDisabled}
        className={`w-full relative py-4 rounded-2xl font-black text-white transition-all shadow-xl overflow-hidden
            ${isRunButtonDisabled ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'}`}
            >
            {isPending && (
                <div
                className="absolute top-0 left-0 h-full bg-blue-800/40 transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
                ></div>
            )}

            <span className="relative z-10 flex items-center justify-center gap-3 tracking-widest uppercase">
            {isPending ? (
                <>
                <LoadingSpinner size="sm" color="white" />
                <span>{taskMessage || 'PROCESSANDO SCORE...'} ({progress}%)</span>
                </>
            ) : isSuccess ? (
                <>
                <FiCheckCircle size={20} />
                <span>SUCESSO! REDIRECIONANDO...</span>
                </>
            ) : (
                <>
                <FiUserCheck size={20} />
                <span>GERAR PREDICÃO DE READMISSÃO</span>
                </>
            )}
            </span>
            </button>
            </div>
            </div>

            <footer className="mt-20 py-8 border-t border-gray-200 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-gray-200 shadow-sm text-[10px] font-bold text-gray-400 uppercase tracking-widest">
            <FiActivity /> LabSUS Predictive Health Engine • Gradient Boosting Implementation
            </div>
            </footer>
            </div>
    );
};

export default PipelineRiscoReadmissaoPage;
