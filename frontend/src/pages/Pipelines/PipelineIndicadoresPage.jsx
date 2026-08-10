import React, { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { FiArrowRightCircle, FiDatabase, FiCheckCircle, FiInfo, FiChevronDown, FiChevronUp } from 'react-icons/fi';

import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import usePageTitle from '../../hooks/usePageTitle';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import InfoCard from '../../components/common/InfoCard';

// Configurações Globais
import { INDICADORES_MAP } from '../../config/indicadores';
import { UF_CONFIGS } from '../../config/ufConfigs';
import {
    SISTEMAS_ORIGEM, ORDEM_SISTEMAS, DOMINIOS, ORDEM_DOMINIOS,
    INDICADOR_CLASSIFICACAO, CLASSIFICACAO_PADRAO,
} from '../../config/indicadorClassificacao';

const PipelineIndicadoresPage = () => {
    usePageTitle('Orquestrar Indicadores');
    const navigate = useNavigate();

    // Estados de Opções
    const [availableYears, setAvailableYears] = useState([]);
    const [availableUFs, setAvailableUFs] = useState([]);
    const [availableIndicators, setAvailableIndicators] = useState([]);

    // Estados de Seleção
    const [selectedYears, setSelectedYears] = useState([]);
    const [selectedUFs, setSelectedUFs] = useState([]);
    const [selectedIndicators, setSelectedIndicators] = useState([]);
    const [outputFileName, setOutputFileName] = useState('');

    // Sistema de origem DATASUS que está expandido na UI (acordeão) — todos
    // colapsados por padrão, já que a lista completa (76 indicadores) não
    // cabe de forma navegável de outro jeito.
    const [expandedSystems, setExpandedSystems] = useState({});
    const toggleSystem = (sistema) => setExpandedSystems(prev => ({ ...prev, [sistema]: !prev[sistema] }));

    // Controle da Task Celery
    const [currentTaskId, setCurrentTaskId] = useState(null);
    const {
        isPending,
        isSuccess,
        isFailure,
        progress,
        message: taskMessage,
        error: taskError,
        result
    } = useCeleryTaskStatus(currentTaskId, '/api/pipelines/indicadores/integracao/tasks/');

    // Limites de Segurança
    const MAX_UFS = 5;
    const MAX_YEARS = 5;
    const MAX_INDICATORS = 20;

    useEffect(() => {
        // Gera anos de 2001 até o atual
        const endYear = new Date().getFullYear();
        const yearsRange = Array.from({ length: endYear - 2000 }, (_, i) => endYear - i);

        // Formata UFs a partir da config
        const ufsOptions = Object.keys(UF_CONFIGS)
        .filter(uf => uf !== 'BR')
        .map(ufCode => ({
            label: `${UF_CONFIGS[ufCode].nome} (${ufCode})`,
                        value: ufCode
        })).sort((a, b) => a.label.localeCompare(b.label));

        // Formata Indicadores a partir do Map
        const indicatorsOptions = Object.keys(INDICADORES_MAP).sort((a, b) =>
        INDICADORES_MAP[a].localeCompare(INDICADORES_MAP[b])
        );

        setAvailableYears(yearsRange);
        setAvailableUFs(ufsOptions);
        setAvailableIndicators(indicatorsOptions);
    }, []);

    // Agrupa os indicadores em dois níveis — sistema de origem DATASUS (eixo
    // principal, acordeão) e domínio temático (sub-agrupamento dentro de cada
    // sistema) — para que a lista de ~76 indicadores fique navegável.
    const indicadoresAgrupados = useMemo(() => {
        const porSistema = {};
        availableIndicators.forEach(key => {
            const { sistema, dominio } = INDICADOR_CLASSIFICACAO[key] || CLASSIFICACAO_PADRAO;
            if (!porSistema[sistema]) porSistema[sistema] = {};
            if (!porSistema[sistema][dominio]) porSistema[sistema][dominio] = [];
            porSistema[sistema][dominio].push(key);
        });

        return ORDEM_SISTEMAS
            .filter(sistema => porSistema[sistema])
            .map(sistema => ({
                sistema,
                total: Object.values(porSistema[sistema]).reduce((acc, arr) => acc + arr.length, 0),
                grupos: ORDEM_DOMINIOS
                    .filter(dominio => porSistema[sistema][dominio])
                    .map(dominio => ({
                        dominio,
                        indicadores: porSistema[sistema][dominio].sort((a, b) =>
                            (INDICADORES_MAP[a] || a).localeCompare(INDICADORES_MAP[b] || b)
                        ),
                    })),
            }));
    }, [availableIndicators]);

    // Handlers de Seleção
    const handleYearChange = (e) => {
        const year = parseInt(e.target.value);
        setSelectedYears(prev => e.target.checked
        ? [...prev, year]
        : prev.filter(y => y !== year)
        );
    };

    const handleUfChange = (e) => {
        const uf = e.target.value;
        setSelectedUFs(prev => e.target.checked
        ? [...prev, uf]
        : prev.filter(u => u !== uf)
        );
    };

    const handleIndicatorChange = (e) => {
        const indicator = e.target.value;
        setSelectedIndicators(prev => e.target.checked
        ? [...prev, indicator]
        : prev.filter(i => i !== indicator)
        );
    };

    // Disparo da Pipeline
    const handleRunPipeline = useCallback(async () => {
        if (selectedUFs.length === 0 || selectedYears.length === 0 || selectedIndicators.length === 0) {
            alert("Por favor, selecione pelo menos uma UF, um ano e um indicador.");
            return;
        }

        setCurrentTaskId(null); // Reseta task anterior

        try {
            const token = localStorage.getItem('authToken');
            const requestData = {
                ufs: selectedUFs,
                anos: selectedYears,
                indicadores: selectedIndicators,
                output_csv_filename: outputFileName || `painel_integrado_${Date.now()}`,
            };

            const response = await axios.post('/api/pipelines/indicadores/integracao/trigger/', requestData, {
                headers: { 'Authorization': `Token ${token}` }
            });

            setCurrentTaskId(response.data.task_id);
        } catch (error) {
            console.error("Erro ao disparar pipeline:", error);
            alert("Erro ao executar pipeline: " + (error.response?.data?.error || error.message));
        }
    }, [selectedUFs, selectedYears, selectedIndicators, outputFileName]);

    // Redirecionamento Automático após Sucesso
    useEffect(() => {
        if (isSuccess && result?.output_file_id) {
            // Pequeno delay para o usuário ver a mensagem de sucesso
            const timer = setTimeout(() => {
                navigate(`/dashboards/visao-geral?fileId=${result.output_file_id}`);
            }, 1500);
            return () => clearTimeout(timer);
        }
    }, [isSuccess, result, navigate]);

    const isRunButtonDisabled = isPending || selectedYears.length === 0 || selectedUFs.length === 0 || selectedIndicators.length === 0;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
        <header className="mb-8 text-center">
        <h1 className="text-3xl font-black text-gray-800">Integração Multidimensonal de Indicadores</h1>
        <p className="text-gray-500 mt-2">Consolide dados do SIM, SIA, SIH, SINASC, SINAN e CNES em um único painel analítico.</p>
        </header>

        {isFailure && <FeedbackMessage message={`Falha na Integração: ${taskError}`} type="error" />}

        <div className="max-w-5xl mx-auto space-y-8">

        <InfoCard title="Como funciona a orquestração?">
        <p className="text-sm">Esta ferramenta automatiza a coleta de dados brutos do DATASUS. Ao selecionar os indicadores abaixo, o sistema irá processar cada base de dados, aplicar as fórmulas de taxas e realizar o <strong>Join</strong> (junção) automático por município e ano.</p>
        </InfoCard>

        <fieldset disabled={isPending} className="space-y-6">
        {/* 1. Nome do Arquivo */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-lg font-bold text-gray-700 mb-4 flex items-center gap-2">
        <FiDatabase className="text-blue-500" /> 1. Nome do Arquivo de Saída
        </h2>
        <input
        type="text"
        value={outputFileName}
        onChange={(e) => setOutputFileName(e.target.value)}
        placeholder="Ex: indicadores_saude_to_2022"
        className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition"
        />
        <p className="text-[10px] text-gray-400 mt-2 uppercase font-bold">O formato .csv será adicionado automaticamente.</p>
        </div>

        {/* 2. Filtros de Escopo */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">Anos ({selectedYears.length}/{MAX_YEARS})</h2>
        <div className="grid grid-cols-3 gap-2 max-h-40 overflow-y-auto pr-2 scrollbar-styled">
        {availableYears.map(year => (
            <label key={year} className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded-lg cursor-pointer transition">
            <input
            type="checkbox"
            value={year}
            checked={selectedYears.includes(year)}
            onChange={handleYearChange}
            disabled={selectedYears.length >= MAX_YEARS && !selectedYears.includes(year)}
            className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="text-sm font-medium text-gray-700">{year}</span>
            </label>
        ))}
        </div>
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">Estados ({selectedUFs.length}/{MAX_UFS})</h2>
        <div className="grid grid-cols-1 gap-1 max-h-40 overflow-y-auto pr-2 scrollbar-styled">
        {availableUFs.map(option => (
            <label key={option.value} className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded-lg cursor-pointer transition">
            <input
            type="checkbox"
            value={option.value}
            checked={selectedUFs.includes(option.value)}
            onChange={handleUfChange}
            disabled={selectedUFs.length >= MAX_UFS && !selectedUFs.includes(option.value)}
            className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="text-sm font-medium text-gray-700">{option.label}</span>
            </label>
        ))}
        </div>
        </div>
        </div>

        {/* 3. Seleção de Indicadores, agrupados por sistema de origem DATASUS (acordeão) e domínio temático */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">Indicadores ({selectedIndicators.length}/{MAX_INDICATORS})</h2>
        <div className="space-y-2">
        {indicadoresAgrupados.map(({ sistema, total, grupos }) => {
            const selecionadosNoSistema = grupos.reduce(
                (acc, g) => acc + g.indicadores.filter(i => selectedIndicators.includes(i)).length, 0
            );
            const isOpen = !!expandedSystems[sistema];
            return (
                <div key={sistema} className="border border-gray-200 rounded-xl overflow-hidden">
                <button
                type="button"
                onClick={() => toggleSystem(sistema)}
                className="w-full flex items-center justify-between gap-3 p-3 bg-gray-50 hover:bg-gray-100 transition text-left"
                >
                <span className="text-sm font-bold text-gray-700">{SISTEMAS_ORIGEM[sistema]}</span>
                <span className="flex items-center gap-3 shrink-0">
                <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${selecionadosNoSistema > 0 ? 'bg-blue-100 text-blue-700' : 'bg-gray-200 text-gray-500'}`}>
                {selecionadosNoSistema > 0 ? `${selecionadosNoSistema}/${total}` : total}
                </span>
                {isOpen ? <FiChevronUp className="text-gray-400" /> : <FiChevronDown className="text-gray-400" />}
                </span>
                </button>

                {isOpen && (
                    <div className="p-4 space-y-4">
                    {grupos.map(({ dominio, indicadores }) => (
                        <div key={dominio}>
                        <h3 className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">{DOMINIOS[dominio]}</h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1">
                        {indicadores.map(indicator => (
                            <label key={indicator} className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded-lg cursor-pointer transition">
                            <input
                            type="checkbox"
                            value={indicator}
                            checked={selectedIndicators.includes(indicator)}
                            onChange={handleIndicatorChange}
                            disabled={selectedIndicators.length >= MAX_INDICATORS && !selectedIndicators.includes(indicator)}
                            className="w-4 h-4 text-blue-600 rounded"
                            />
                            <span className="text-xs font-medium text-gray-700 leading-tight">
                            {INDICADORES_MAP[indicator] || indicator}
                            </span>
                            </label>
                        ))}
                        </div>
                        </div>
                    ))}
                    </div>
                )}
                </div>
            );
        })}
        </div>
        </div>
        </fieldset>

        {/* Botão de Execução com Barra de Progresso Interna */}
        <div className="mt-10">
        <button
        onClick={handleRunPipeline}
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
                <span>{taskMessage || 'PROCESSANDO...'} ({progress}%)</span>
                </>
            ) : isSuccess ? (
                <>
                <FiCheckCircle size={20} />
                <span>CONCLUÍDO! REDIRECIONANDO...</span>
                </>
            ) : (
                <>
                <FiArrowRightCircle size={20} />
                <span>EXECUTAR INTEGRAÇÃO</span>
                </>
            )}
            </span>
            </button>
            </div>
            </div>

            <footer className="mt-20 py-8 border-t border-gray-200 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-gray-200 shadow-sm text-[10px] font-bold text-gray-400 uppercase tracking-widest">
            <FiInfo /> LabSUS Engine v2.5 • Extração Síncrona via PySUS
            </div>
            </footer>
            </div>
    );
};

export default PipelineIndicadoresPage;
