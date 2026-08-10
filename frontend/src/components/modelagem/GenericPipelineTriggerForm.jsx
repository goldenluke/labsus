import React, { useState, useCallback, useEffect, useMemo } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { FiPlay, FiCheckCircle, FiPlus, FiX, FiInfo } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import FeedbackMessage from '../common/FeedbackMessage';
import LoadingSpinner from '../common/LoadingSpinner';
import InfoCard from '../common/InfoCard';
import AsyncFileSelect from '../common/AsyncFileSelect';

const UFS_BRASIL = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG',
    'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
];

const ANOS_DISPONIVEIS = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];

const valorInicial = (campo) => (Array.isArray(campo.default) ? [...campo.default] : campo.default);

const construirValoresIniciais = (campos) => {
    const valores = {};
    campos.forEach((campo) => { valores[campo.nome] = valorInicial(campo); });
    return valores;
};

const campoPreenchido = (campo, valor) => {
    if (!campo.obrigatorio) return true;
    if (campo.tipo === 'ufs' || campo.tipo === 'anos' || campo.tipo === 'texts') {
        return Array.isArray(valor) && valor.length > 0;
    }
    return valor !== null && valor !== undefined && String(valor).trim() !== '';
};

const TagListInput = ({ valor, onChange, placeholder }) => {
    const [rascunho, setRascunho] = useState('');

    const adicionar = () => {
        const item = rascunho.trim();
        if (item && !valor.includes(item)) onChange([...valor, item]);
        setRascunho('');
    };

    const remover = (item) => onChange(valor.filter((v) => v !== item));

    return (
        <div>
            <div className="flex gap-2">
                <input
                    type="text"
                    value={rascunho}
                    onChange={(e) => setRascunho(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); adicionar(); } }}
                    placeholder={placeholder}
                    className="flex-grow p-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                    type="button"
                    onClick={adicionar}
                    className="px-3 rounded-xl bg-gray-100 text-gray-500 hover:bg-blue-50 hover:text-blue-600 transition-colors"
                >
                    <FiPlus />
                </button>
            </div>
            {valor.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-3">
                    {valor.map((item) => (
                        <span key={item} className="flex items-center gap-1.5 bg-blue-50 text-blue-700 text-xs font-bold px-3 py-1.5 rounded-full">
                            {item}
                            <button type="button" onClick={() => remover(item)} className="hover:text-blue-900">
                                <FiX size={12} />
                            </button>
                        </span>
                    ))}
                </div>
            )}
        </div>
    );
};

const CampoField = ({ campo, valor, onChange }) => {
    switch (campo.tipo) {
        case 'uf':
            return (
                <select
                    value={valor || ''}
                    onChange={(e) => onChange(e.target.value)}
                    className="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-xl font-bold text-gray-700 text-sm outline-none focus:ring-2 focus:ring-blue-500"
                >
                    {UFS_BRASIL.map((uf) => <option key={uf} value={uf}>{uf}</option>)}
                </select>
            );
        case 'ufs':
            return (
                <div className="grid grid-cols-6 sm:grid-cols-9 gap-1.5">
                    {UFS_BRASIL.map((uf) => (
                        <button
                            key={uf}
                            type="button"
                            onClick={() => onChange(valor.includes(uf) ? valor.filter((u) => u !== uf) : [...valor, uf])}
                            className={`py-1.5 rounded-lg text-[11px] font-black transition-all
                                ${valor.includes(uf) ? 'bg-blue-600 text-white shadow-sm' : 'bg-gray-50 text-gray-400 border border-gray-200 hover:bg-gray-100'}`}
                        >
                            {uf}
                        </button>
                    ))}
                </div>
            );
        case 'ano':
            return (
                <input
                    type="number"
                    value={valor ?? ''}
                    onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
                    className="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-blue-500"
                />
            );
        case 'anos':
            return (
                <div className="flex flex-wrap gap-1.5">
                    {ANOS_DISPONIVEIS.map((ano) => (
                        <button
                            key={ano}
                            type="button"
                            onClick={() => onChange(valor.includes(ano) ? valor.filter((a) => a !== ano) : [...valor, ano].sort())}
                            className={`px-3 py-1.5 rounded-lg text-xs font-black transition-all
                                ${valor.includes(ano) ? 'bg-green-600 text-white shadow-sm' : 'bg-gray-50 text-gray-400 border border-gray-200 hover:bg-gray-100'}`}
                        >
                            {ano}
                        </button>
                    ))}
                </div>
            );
        case 'text':
            return (
                <input
                    type="text"
                    value={valor ?? ''}
                    onChange={(e) => onChange(e.target.value)}
                    className="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-blue-500"
                />
            );
        case 'texts':
            return <TagListInput valor={valor || []} onChange={onChange} placeholder="Digite e pressione Enter para adicionar" />;
        case 'int':
            return (
                <input
                    type="number"
                    step="1"
                    value={valor ?? ''}
                    onChange={(e) => onChange(e.target.value === '' ? null : parseInt(e.target.value, 10))}
                    className="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-blue-500"
                />
            );
        case 'int_optional':
            return (
                <input
                    type="number"
                    step="1"
                    value={valor ?? ''}
                    placeholder="automático"
                    onChange={(e) => onChange(e.target.value === '' ? null : parseInt(e.target.value, 10))}
                    className="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-blue-500"
                />
            );
        case 'float':
            return (
                <input
                    type="number"
                    step="0.01"
                    value={valor ?? ''}
                    onChange={(e) => onChange(e.target.value === '' ? null : parseFloat(e.target.value))}
                    className="w-full p-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-blue-500"
                />
            );
        case 'file_csv':
            return (
                <AsyncFileSelect
                    value={valor}
                    onChange={(opt) => onChange(opt ? opt.value : null)}
                    isClearable
                    placeholder="Buscar CSV já processado..."
                />
            );
        default:
            return null;
    }
};

const GenericPipelineTriggerForm = ({ config }) => {
    usePageTitle(config.title);
    const navigate = useNavigate();

    const [valores, setValores] = useState(() => construirValoresIniciais(config.campos));
    const [taskId, setTaskId] = useState(null);

    const apiPrefix = `/api/pipelines/${config.key}/`;
    const viewerPath = `/dashboards/modelagem/${config.key}`;

    const {
        isPending, isSuccess, isFailure,
        progress, message: taskMessage, error: taskError,
    } = useCeleryTaskStatus(taskId, `${apiPrefix}tasks/`);

    useEffect(() => {
        setValores(construirValoresIniciais(config.campos));
        setTaskId(null);
    }, [config.key]);

    const setCampo = useCallback((nome, valor) => {
        setValores((prev) => ({ ...prev, [nome]: valor }));
    }, []);

    const camposIncompletos = useMemo(
        () => config.campos.filter((campo) => !campoPreenchido(campo, valores[campo.nome])),
        [config.campos, valores]
    );

    const triggerPipeline = useCallback(async () => {
        setTaskId(null);
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.post(apiPrefix + 'trigger/', valores, {
                headers: { Authorization: `Token ${token}` },
            });
            setTaskId(response.data.task_id);
        } catch (err) {
            alert(`Falha ao disparar análise: ${err.response?.data?.error || err.message}`);
        }
    }, [apiPrefix, valores]);

    useEffect(() => {
        if (isSuccess && taskId) {
            const timer = setTimeout(() => {
                navigate(`${viewerPath}?taskId=${taskId}`);
            }, 1500);
            return () => clearTimeout(timer);
        }
    }, [isSuccess, taskId, navigate, viewerPath]);

    const isRunButtonDisabled = isPending || camposIncompletos.length > 0;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase">{config.title}</h1>
                <p className="text-gray-500 mt-2 text-lg">{config.descricao}</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                {isFailure && <FeedbackMessage message={`Erro na análise: ${taskError}`} type="error" />}

                <InfoCard title="Sobre este modelo">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        {config.sobre || (
                            <>
                                Este modelo faz parte do módulo de <strong>Modelagem Avançada</strong>. Ele baixa os dados
                                necessários do DATASUS (quando aplicável), executa a análise e disponibiliza os arquivos
                                gerados (CSV/imagens) para consulta e download.
                            </>
                        )}
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                        <FiInfo className="text-blue-500" /> Parâmetros
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {config.campos.map((campo) => (
                            <div key={campo.nome} className={campo.tipo === 'ufs' || campo.tipo === 'texts' ? 'md:col-span-2' : ''}>
                                <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">
                                    {campo.label} {campo.obrigatorio && <span className="text-red-500">*</span>}
                                </label>
                                <CampoField campo={campo} valor={valores[campo.nome]} onChange={(v) => setCampo(campo.nome, v)} />
                            </div>
                        ))}
                    </div>
                </fieldset>

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
                            />
                        )}
                        <span className="relative z-10 flex items-center justify-center gap-3 tracking-widest uppercase">
                            {isPending ? (
                                <>
                                    <LoadingSpinner size="sm" color="white" />
                                    <span>{taskMessage || 'EXECUTANDO...'} ({progress}%)</span>
                                </>
                            ) : isSuccess ? (
                                <>
                                    <FiCheckCircle size={20} />
                                    <span>SUCESSO! REDIRECIONANDO...</span>
                                </>
                            ) : (
                                <>
                                    <FiPlay size={20} />
                                    <span>Executar Análise</span>
                                </>
                            )}
                        </span>
                    </button>
                    {!isPending && camposIncompletos.length > 0 && (
                        <p className="text-center text-xs text-gray-400 mt-3">
                            Preencha os campos obrigatórios: {camposIncompletos.map((c) => c.label).join(', ')}
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
};

export default GenericPipelineTriggerForm;
