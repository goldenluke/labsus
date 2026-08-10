import React, { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
    FiGitPullRequest, FiArrowRightCircle, FiPlus, FiX,
    FiDatabase, FiMapPin, FiCalendar, FiSettings,
    FiTag, FiCheckCircle, FiActivity
} from 'react-icons/fi';

import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import usePageTitle from '../../hooks/usePageTitle';
import { UF_CONFIGS } from '../../config/ufConfigs';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import InfoCard from '../../components/common/InfoCard';

const PipelineFluxoPacientesPage = () => {
    usePageTitle('Orquestrar Fluxo de Pacientes');
    const navigate = useNavigate();

    // Estados do Formulário
    const [ufs, setUfs] = useState([]);
    const [anos, setAnos] = useState([]);
    const [diagnosticoCids, setDiagnosticoCids] = useState([]);
    const [minPacientesFluxo, setMinPacientesFluxo] = useState(5);
    const [outputFileName, setOutputFileName] = useState('');
    const [currentCidInput, setCurrentCidInput] = useState('');

    // Controle da Task Celery
    const [taskId, setTaskId] = useState(null);
    const {
        isPending, isSuccess, isFailure,
        progress, message: taskMessage, error: taskError, result
    } = useCeleryTaskStatus(taskId, '/api/pipelines/fluxo-pacientes/tasks/');

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
        if (code && !diagnosticoCids.includes(code)) {
            setDiagnosticoCids(prev => [...prev, code]);
            setCurrentCidInput('');
        }
    };

    const handleRemoveCid = (codeToRemove) => {
        setDiagnosticoCids(prev => prev.filter(code => code !== codeToRemove));
    };

    const triggerPipeline = useCallback(async () => {
        if (ufs.length === 0 || anos.length === 0 || diagnosticoCids.length === 0) {
            alert("Por favor, preencha UFs, Anos e pelo menos um CID.");
            return;
        }

        setTaskId(null);
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.post('/api/pipelines/fluxo-pacientes/trigger/', {
                ufs,
                anos,
                diagnostico_cids: diagnosticoCids,
                min_pacientes_fluxo: minPacientesFluxo,
                output_filename: outputFileName || `fluxo_pacientes_${Date.now()}`,
            }, { headers: { 'Authorization': `Token ${token}` } });

            setTaskId(response.data.task_id);
        } catch (err) {
            alert(`Falha ao disparar pipeline: ${err.response?.data?.error || err.message}`);
        }
    }, [ufs, anos, diagnosticoCids, minPacientesFluxo, outputFileName]);

    useEffect(() => {
        if (isSuccess && result?.output_file_id) {
            setTimeout(() => {
                navigate(`/dashboards/fluxo-pacientes?fileId=${result.output_file_id}`);
            }, 1500);
        }
    }, [isSuccess, result, navigate]);

    const isRunButtonDisabled = isPending || ufs.length === 0 || anos.length === 0 || diagnosticoCids.length === 0;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
        <header className="mb-8 text-center">
        <h1 className="text-3xl font-black text-gray-800 tracking-tight">Análise de Fluxo de Pacientes</h1>
        <p className="text-gray-500 mt-2 text-lg">Mapeie o deslocamento intermunicipal e identifique polos de atendimento hospitalar.</p>
        </header>

        <div className="max-w-5xl mx-auto space-y-8">

        {isFailure && <FeedbackMessage message={`Erro na tarefa: ${taskError}`} type="error" />}

        <InfoCard title="Como funciona esta análise?">
        <p className="text-sm leading-relaxed">
        O sistema cruza o <strong>Município de Residência</strong> com o <strong>Município de Internação</strong> para descobrir de onde vêm os pacientes de cada hospital.
        Isso permite visualizar a rede de referência e identificar vazios assistenciais ou sobrecarga regional.
        </p>
        </InfoCard>

        <fieldset disabled={isPending} className="space-y-6">

        {/* PASSO 1: NOME DO ARQUIVO */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
        <FiDatabase className="text-blue-500" /> 1. Nome do Arquivo de Saída
        </h2>
        <input
        type="text"
        value={outputFileName}
        onChange={e => setOutputFileName(e.target.value)}
        placeholder="Ex: fluxo_cardiologia_2024"
        className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
        />
        </div>

        {/* PASSO 2: FILTROS TÉCNICOS */}
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
        <FiCalendar className="text-blue-500" /> 3. Período Anual
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

        {/* PASSO 3: FOCO DIAGNÓSTICO */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
        <FiTag className="text-blue-500" /> 4. Diagnóstico Principal (CIDs)
        </h2>

        <form onSubmit={handleAddCid} className="flex gap-2 mb-4">
        <input
        type="text"
        value={currentCidInput}
        onChange={e => setCurrentCidInput(e.target.value)}
        placeholder="Ex: I21, J18, C"
        className="flex-1 p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
        />
        <button type="submit" className="px-6 py-3 bg-gray-800 text-white rounded-xl font-bold hover:bg-black transition flex items-center gap-2">
        <FiPlus /> Adicionar
        </button>
        </form>

        <div className="flex flex-wrap gap-2 min-h-[50px] p-3 bg-gray-50 rounded-2xl border border-gray-100">
        {diagnosticoCids.length === 0 ? (
            <span className="text-xs text-gray-400 italic">Nenhum CID adicionado...</span>
        ) : (
            diagnosticoCids.map(code => (
                <span key={code} className="flex items-center gap-2 px-3 py-1 bg-blue-600 text-white rounded-full text-xs font-black shadow-sm">
                {code}
                <button onClick={() => handleRemoveCid(code)} className="hover:text-red-200 transition">
                <FiX size={14} />
                </button>
                </span>
            ))
        )}
        </div>
        </div>

        {/* PASSO 4: PARÂMETROS OPERACIONAIS */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
        <FiSettings className="text-blue-500" /> 5. Sensibilidade do Fluxo
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
        <div>
        <label className="block text-xs font-bold text-gray-500 uppercase mb-3 text-center md:text-left">Mínimo de Pacientes por Rota</label>
        <div className="flex items-center gap-4 bg-gray-50 p-4 rounded-2xl border border-gray-100">
        <input
        type="number"
        min="1"
        value={minPacientesFluxo}
        onChange={e => setMinPacientesFluxo(parseInt(e.target.value) || 1)}
        className="bg-transparent text-2xl font-black text-blue-600 w-full text-center outline-none"
        />
        </div>
        </div>
        <div className="p-4 bg-blue-50 rounded-2xl border border-blue-100">
        <p className="text-[11px] text-blue-700 leading-relaxed">
        <strong>Dica:</strong> Para grandes centros urbanos, utilize valores entre 10 e 20 para remover ruídos. Para regiões rurais ou CIDs raros, mantenha entre 1 e 5.
        </p>
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

            <span className="relative z-10 flex items-center justify-center gap-3 tracking-widest">
            {isPending ? (
                <>
                <LoadingSpinner size="sm" color="white" />
                <span>{taskMessage || 'PROCESSANDO FLUXOS...'} ({progress}%)</span>
                </>
            ) : isSuccess ? (
                <>
                <FiCheckCircle size={20} />
                <span>CONCLUÍDO! REDIRECIONANDO...</span>
                </>
            ) : (
                <>
                <FiArrowRightCircle size={20} />
                <span>GERAR MAPA DE FLUXO</span>
                </>
            )}
            </span>
            </button>
            </div>
            </div>

            <footer className="mt-20 py-8 border-t border-gray-200 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-gray-200 shadow-sm text-[10px] font-bold text-gray-400 uppercase tracking-widest">
            <FiGitPullRequest /> LabSUS Spatial Engine • Network Analysis Integration
            </div>
            </footer>
            </div>
    );
};

export default PipelineFluxoPacientesPage;
