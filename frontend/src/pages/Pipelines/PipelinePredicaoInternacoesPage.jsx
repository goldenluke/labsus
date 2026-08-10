import React, { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
    FiTrendingUp, FiArrowRightCircle, FiPlus, FiX,
    FiDatabase, FiMapPin, FiCalendar, FiTag,
    FiClock, FiCheckCircle, FiActivity
} from 'react-icons/fi';

import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import usePageTitle from '../../hooks/usePageTitle';
import { UF_CONFIGS } from '../../config/ufConfigs';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import InfoCard from '../../components/common/InfoCard';

const PipelinePredicaoInternacoesPage = () => {
    usePageTitle('Orquestrar Predição');
    const navigate = useNavigate();

    // Estados do Formulário
    const [ufs, setUfs] = useState([]);
    const [anosHistorico, setAnosHistorico] = useState([]);
    const [cidCodes, setCidCodes] = useState([]);
    const [mesesPrevisao, setMesesPrevisao] = useState(6);
    const [outputFileName, setOutputFileName] = useState('');
    const [currentCidInput, setCurrentCidInput] = useState('');

    // Controle da Task Celery
    const [predictionTaskId, setPredictionTaskId] = useState(null);
    const {
        isPending, isSuccess, isFailure,
        progress, message: taskMessage, error: taskError, result
    } = useCeleryTaskStatus(predictionTaskId, '/api/pipelines/predicao/internacoes/tasks/');

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

    // Handlers
    const handleAddCid = (e) => {
        e.preventDefault();
        const code = currentCidInput.trim().toUpperCase();
        if (code && !cidCodes.includes(code)) {
            setCidCodes(prev => [...prev, code]);
            setCurrentCidInput('');
        }
    };

    const handleRemoveCid = (codeToRemove) => {
        setCidCodes(prev => prev.filter(code => code !== codeToRemove));
    };

    const triggerPrediction = useCallback(async () => {
        if (ufs.length === 0 || anosHistorico.length === 0 || cidCodes.length === 0) {
            alert("Por favor, preencha UFs, Anos e pelo menos um código CID.");
            return;
        }

        setPredictionTaskId(null);
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.post('/api/pipelines/predicao/internacoes/trigger/', {
                ufs,
                anos_historico: anosHistorico,
                cid_codes: cidCodes,
                meses_previsao: mesesPrevisao,
                output_filename: outputFileName || `predicao_internacoes_${Date.now()}`,
            }, { headers: { 'Authorization': `Token ${token}` } });

            setPredictionTaskId(response.data.task_id);
        } catch (err) {
            alert(`Falha ao disparar pipeline: ${err.response?.data?.error || err.message}`);
        }
    }, [ufs, anosHistorico, cidCodes, mesesPrevisao, outputFileName]);

    useEffect(() => {
        if (isSuccess && result?.output_file_id) {
            setTimeout(() => {
                navigate(`/dashboards/predicao-internacoes?fileId=${result.output_file_id}`);
            }, 1500);
        }
    }, [isSuccess, result, navigate]);

    const isRunButtonDisabled = isPending || ufs.length === 0 || anosHistorico.length === 0 || cidCodes.length === 0;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
        <header className="mb-8 text-center">
        <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase">Predição de Demanda Hospitalar</h1>
        <p className="text-gray-500 mt-2 text-lg">Projete o volume futuro de internações utilizando Inteligência Artificial (Prophet).</p>
        </header>

        <div className="max-w-5xl mx-auto space-y-8">

        {isFailure && <FeedbackMessage message={`Erro na tarefa: ${taskError}`} type="error" />}

        <InfoCard title="Como funciona a predição?">
        <p className="text-sm leading-relaxed">
        Esta ferramenta utiliza o modelo de séries temporais <strong>Prophet</strong>. O algoritmo analisa os ciclos sazonais e tendências dos dados históricos que você selecionar e projeta o comportamento estatístico mais provável para os próximos meses.
        </p>
        </InfoCard>

        <fieldset disabled={isPending} className="space-y-6">

        {/* PASSO 1: NOME DO RESULTADO */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
        <FiDatabase className="text-blue-500" /> 1. Identificação da Análise
        </h2>
        <input
        type="text"
        value={outputFileName}
        onChange={e => setOutputFileName(e.target.value)}
        placeholder="Ex: previsao_pneumonia_norte_2025"
        className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
        />
        </div>

        {/* PASSO 2: ESCOPO DOS DADOS */}
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
        <FiCalendar className="text-blue-500" /> 3. Anos Históricos
        </h2>
        <div className="grid grid-cols-3 gap-2 max-h-48 overflow-y-auto pr-2 scrollbar-styled p-1">
        {yearOptions.map(year => (
            <label key={year} className="flex items-center gap-3 p-2 bg-gray-50 rounded-xl border border-gray-100 cursor-pointer hover:bg-white hover:border-blue-200 transition">
            <input
            type="checkbox"
            checked={anosHistorico.includes(year)}
            onChange={e => setAnosHistorico(e.target.checked ? [...anosHistorico, year] : anosHistorico.filter(a => a !== year))}
            className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="text-xs font-bold text-gray-600">{year}</span>
            </label>
        ))}
        </div>
        </div>
        </div>

        {/* PASSO 3: ALVO CLÍNICO */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
        <FiTag className="text-blue-500" /> 4. Doenças Analisadas (CID-10)
        </h2>

        <form onSubmit={handleAddCid} className="flex gap-2 mb-4">
        <input
        type="text"
        value={currentCidInput}
        onChange={e => setCurrentCidInput(e.target.value)}
        placeholder="Ex: J18, I21, A, C"
        className="flex-1 p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
        />
        <button type="submit" className="px-6 py-3 bg-gray-800 text-white rounded-xl font-bold hover:bg-black transition flex items-center gap-2">
        <FiPlus /> Adicionar
        </button>
        </form>

        <div className="flex flex-wrap gap-2 min-h-[50px] p-3 bg-gray-50 rounded-2xl border border-gray-100">
        {cidCodes.length === 0 ? (
            <span className="text-xs text-gray-400 italic font-medium">Nenhum código adicionado...</span>
        ) : (
            cidCodes.map(code => (
                <span key={code} className="flex items-center gap-2 px-3 py-1 bg-indigo-600 text-white rounded-full text-xs font-black shadow-sm tracking-tighter">
                {code}
                <button onClick={() => handleRemoveCid(code)} className="hover:text-red-200 transition">
                <FiX size={14} />
                </button>
                </span>
            ))
        )}
        </div>
        </div>

        {/* PASSO 4: HORIZONTE DE PREVISÃO */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
        <FiClock className="text-blue-500" /> 5. Horizonte de Tempo
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
        <div>
        <label className="block text-xs font-bold text-gray-500 uppercase mb-3 text-center md:text-left">Meses para Previsão Futura</label>
        <div className="flex items-center gap-4 bg-gray-50 p-4 rounded-2xl border border-gray-100">
        <input
        type="number"
        min="1"
        max="24"
        value={mesesPrevisao}
        onChange={e => setMesesPrevisao(parseInt(e.target.value) || 1)}
        className="bg-transparent text-2xl font-black text-blue-600 w-full text-center outline-none"
        />
        </div>
        </div>
        <div className="p-4 bg-blue-50 rounded-2xl border border-blue-100">
        <p className="text-[11px] text-blue-700 leading-relaxed font-medium">
        <strong>Recomendação:</strong> Para predições sazonais confiáveis, utilize um horizonte de <strong>6 a 12 meses</strong>. Valores acima de 18 meses podem apresentar maior margem de incerteza.
        </p>
        </div>
        </div>
        </div>
        </fieldset>

        {/* BOTÃO DE EXECUÇÃO COM BARRA DE PROGRESSO */}
        <div className="mt-10 pb-12">
        <button
        onClick={triggerPrediction}
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
                <span>{taskMessage || 'PROCESSANDO PREDIÇÃO...'} ({progress}%)</span>
                </>
            ) : isSuccess ? (
                <>
                <FiCheckCircle size={20} />
                <span>CONCLUÍDO! REDIRECIONANDO...</span>
                </>
            ) : (
                <>
                <FiTrendingUp size={20} />
                <span>INICIAR CÁLCULO DE PROJEÇÃO</span>
                </>
            )}
            </span>
            </button>
            </div>
            </div>

            <footer className="mt-20 py-8 border-t border-gray-200 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-gray-200 shadow-sm text-[10px] font-bold text-gray-400 uppercase tracking-widest">
            <FiTrendingUp /> LabSUS Predictive Engine • Prophet AI Implementation
            </div>
            </footer>
            </div>
    );
};

export default PipelinePredicaoInternacoesPage;
