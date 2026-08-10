import React, { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
    FiCrosshair, FiArrowRightCircle, FiPlus, FiX,
    FiDatabase, FiMapPin, FiCalendar, FiActivity,
    FiSliders, FiCheckCircle, FiTag
} from 'react-icons/fi';

import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import usePageTitle from '../../hooks/usePageTitle';
import { UF_CONFIGS } from '../../config/ufConfigs';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import InfoCard from '../../components/common/InfoCard';

const PipelineRegressaoObitosPage = () => {
    usePageTitle('Orquestrar Regressão de Óbito');
    const navigate = useNavigate();

    // Estados do Formulário
    const [ufs, setUfs] = useState([]);
    const [anos, setAnos] = useState([]);
    const [diagnosticoCids, setDiagnosticoCids] = useState([]);
    const [comorbidadeCids, setComorbidadeCids] = useState([]);
    const [outputFileName, setOutputFileName] = useState('');
    const [decisionThreshold, setDecisionThreshold] = useState(0.5);

    // Estados de Input para CIDs
    const [currentDiagInput, setCurrentDiagInput] = useState('');
    const [currentComorbInput, setCurrentComorbInput] = useState('');

    // Controle da Task Celery
    const [taskId, setTaskId] = useState(null);
    const {
        isPending, isSuccess, isFailure,
        progress, message: taskMessage, error: taskError, result
    } = useCeleryTaskStatus(taskId, '/api/pipelines/regressao-obitos/tasks/');

    // Configurações de Opções
    const ufOptions = useMemo(() => Object.keys(UF_CONFIGS)
    .filter(uf => uf !== 'BR')
    .map(ufCode => ({
        label: `${UF_CONFIGS[ufCode].nome} (${ufCode})`,
                    value: ufCode
    })).sort((a, b) => a.label.localeCompare(b.label)), []);

    const yearOptions = useMemo(() => {
        const currentYear = new Date().getFullYear();
        return Array.from({ length: 15 }, (_, i) => currentYear - i);
    }, []);

    // Handlers para CIDs (Tags)
    const handleAddCid = (type) => (e) => {
        e.preventDefault();
        if (type === 'diagnostico') {
            const code = currentDiagInput.trim().toUpperCase();
            if (code && !diagnosticoCids.includes(code)) {
                setDiagnosticoCids(prev => [...prev, code]);
                setCurrentDiagInput('');
            }
        } else {
            const code = currentComorbInput.trim().toUpperCase();
            if (code && !comorbidadeCids.includes(code)) {
                setComorbidadeCids(prev => [...prev, code]);
                setCurrentComorbInput('');
            }
        }
    };

    const handleRemoveCid = (type, codeToRemove) => {
        if (type === 'diagnostico') {
            setDiagnosticoCids(prev => prev.filter(code => code !== codeToRemove));
        } else {
            setComorbidadeCids(prev => prev.filter(code => code !== codeToRemove));
        }
    };

    const triggerPipeline = useCallback(async () => {
        if (ufs.length === 0 || anos.length === 0 || diagnosticoCids.length === 0) {
            alert("Por favor, preencha UFs, Anos e pelo menos um CID de Diagnóstico Principal.");
            return;
        }

        setTaskId(null);
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.post('/api/pipelines/regressao-obitos/trigger/', {
                ufs,
                anos,
                diagnostico_cids: diagnosticoCids,
                comorbidade_cids: comorbidadeCids.length > 0 ? comorbidadeCids : null,
                output_filename: outputFileName || `risco_obito_${Date.now()}`,
                                              decision_threshold: decisionThreshold
            }, { headers: { 'Authorization': `Token ${token}` } });

            setTaskId(response.data.task_id);
        } catch (err) {
            alert(`Falha ao disparar pipeline: ${err.response?.data?.error || err.message}`);
        }
    }, [ufs, anos, diagnosticoCids, comorbidadeCids, outputFileName, decisionThreshold]);

    useEffect(() => {
        if (isSuccess && result?.output_file_id) {
            setTimeout(() => {
                navigate(`/dashboards/regressao-obitos?fileId=${result.output_file_id}`);
            }, 1500);
        }
    }, [isSuccess, result, navigate]);

    const isRunButtonDisabled = isPending || ufs.length === 0 || anos.length === 0 || diagnosticoCids.length === 0;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
        <header className="mb-8 text-center">
        <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Análise de Risco de Óbito</h1>
        <p className="text-gray-500 mt-2 text-lg">Treine modelos de regressão logística para identificar fatores de risco em internações específicas.</p>
        </header>

        <div className="max-w-5xl mx-auto space-y-8 pb-12">

        {isFailure && <FeedbackMessage message={`Erro na tarefa: ${taskError}`} type="error" />}

        <InfoCard title="Como funciona este modelo?">
        <p className="text-sm leading-relaxed text-gray-600 font-medium">
        Esta pipeline utiliza <strong>Regressão Logística</strong> para calcular a probabilidade de óbito. Ela analisa variáveis como idade, sexo e caráter da internação, comparando o impacto de cada uma (Odds Ratio). O resultado permite entender quais fatores clínicos ou demográficos aumentam a vulnerabilidade do paciente.
        </p>
        </InfoCard>

        <fieldset disabled={isPending} className="space-y-6">

        {/* PASSO 1: NOME DO ARQUIVO */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
        <FiDatabase className="text-blue-500" /> 1. Identificação do Relatório
        </h2>
        <input
        type="text"
        value={outputFileName}
        onChange={e => setOutputFileName(e.target.value)}
        placeholder="Ex: analise_risco_pneumonia_2023"
        className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
        />
        </div>

        {/* PASSO 2: ESCOPO TERRITORIAL E TEMPORAL */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
        <FiMapPin className="text-blue-500" /> 2. Estados (UFs)
        </h2>
        <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-2 scrollbar-styled p-1">
        {ufOptions.map(option => (
            <label key={option.value} className="flex items-center gap-3 p-2 bg-gray-50 rounded-xl border border-gray-100 cursor-pointer hover:bg-white hover:border-blue-200 transition">
            <input
            type="checkbox"
            checked={ufs.includes(option.value)}
            onChange={e => setUfs(e.target.checked ? [...ufs, option.value] : ufs.filter(u => u !== option.value))}
            className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="text-xs font-bold text-gray-600">{option.label}</span>
            </label>
        ))}
        </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
        <FiCalendar className="text-blue-500" /> 3. Anos de Referência
        </h2>
        <div className="grid grid-cols-3 gap-2 max-h-48 overflow-y-auto pr-2 scrollbar-styled p-1">
        {yearOptions.map(year => (
            <label key={year} className="flex items-center gap-3 p-2 bg-gray-50 rounded-xl border border-gray-100 cursor-pointer hover:bg-white hover:border-blue-200 transition">
            <input
            type="checkbox"
            checked={anos.includes(year)}
            onChange={e => setAnos(e.target.checked ? [...anos, year] : anos.filter(a => a !== year))}
            className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="text-xs font-bold text-gray-600">{year}</span>
            </label>
        ))}
        </div>
        </div>
        </div>

        {/* PASSO 3: DEFINIÇÕES CLÍNICAS */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
        <FiTag className="text-red-500" /> 4. Diagnóstico Principal (CIDs)
        </h2>
        <form onSubmit={handleAddCid('diagnostico')} className="flex gap-2 mb-4">
        <input
        type="text"
        value={currentDiagInput}
        onChange={e => setCurrentDiagInput(e.target.value)}
        placeholder="Ex: J18"
        className="flex-1 p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
        />
        <button type="submit" className="p-3 bg-gray-800 text-white rounded-xl hover:bg-black transition"><FiPlus /></button>
        </form>
        <div className="flex flex-wrap gap-2 min-h-[50px] p-3 bg-gray-50 rounded-xl border border-gray-100">
        {diagnosticoCids.map(code => (
            <span key={code} className="flex items-center gap-2 px-3 py-1 bg-red-600 text-white rounded-full text-[10px] font-black shadow-sm">
            {code} <button onClick={() => handleRemoveCid('diagnostico', code)}><FiX size={12} /></button>
            </span>
        ))}
        </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
        <FiTag className="text-teal-500" /> 5. Comorbidades (Opcional)
        </h2>
        <form onSubmit={handleAddCid('comorbidade')} className="flex gap-2 mb-4">
        <input
        type="text"
        value={currentComorbInput}
        onChange={e => setCurrentComorbInput(e.target.value)}
        placeholder="Ex: E11, I10"
        className="flex-1 p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
        />
        <button type="submit" className="p-3 bg-gray-800 text-white rounded-xl hover:bg-black transition"><FiPlus /></button>
        </form>
        <div className="flex flex-wrap gap-2 min-h-[50px] p-3 bg-gray-50 rounded-xl border border-gray-100">
        {comorbidadeCids.map(code => (
            <span key={code} className="flex items-center gap-2 px-3 py-1 bg-teal-600 text-white rounded-full text-[10px] font-black shadow-sm">
            {code} <button onClick={() => handleRemoveCid('comorbidade', code)}><FiX size={12} /></button>
            </span>
        ))}
        </div>
        </div>
        </div>

        {/* PASSO 4: SENSIBILIDADE DO MODELO */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
        <FiSliders className="text-blue-500" /> 6. Sensibilidade (Decision Threshold)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 items-center">
        <div className="md:col-span-1 text-center">
        <div className="text-4xl font-black text-blue-600 font-mono tracking-tighter">
        {decisionThreshold.toFixed(2)}
        </div>
        <p className="text-[10px] text-gray-400 uppercase font-bold mt-1">Limiar de Corte</p>
        </div>
        <div className="md:col-span-3">
        <input
        type="range" min="0.05" max="0.95" step="0.01"
        value={decisionThreshold}
        onChange={e => setDecisionThreshold(parseFloat(e.target.value))}
        className="w-full h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <div className="flex justify-between mt-2 text-[10px] text-gray-400 font-bold uppercase tracking-widest">
        <span>Mais Alertas (Sensível)</span>
        <span>Padrão (0.50)</span>
        <span>Mais Rigoroso (Específico)</span>
        </div>
        </div>
        </div>
        </div>
        </fieldset>

        {/* BOTÃO DE EXECUÇÃO */}
        <div className="mt-10 pb-12">
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
                <span>{taskMessage || 'TREINANDO MODELO...'} ({progress}%)</span>
                </>
            ) : isSuccess ? (
                <>
                <FiCheckCircle size={20} />
                <span>MODELO PRONTO! REDIRECIONANDO...</span>
                </>
            ) : (
                <>
                <FiCrosshair size={20} />
                <span>INICIAR ANÁLISE DE REGRESSÃO</span>
                </>
            )}
            </span>
            </button>
            </div>
            </div>

            <footer className="mt-20 py-8 border-t border-gray-200 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-gray-200 shadow-sm text-[10px] font-bold text-gray-400 uppercase tracking-widest">
            <FiActivity /> LabSUS Predictive Health Hub • Logistic Regression Integration
            </div>
            </footer>
            </div>
    );
};

export default PipelineRegressaoObitosPage;
