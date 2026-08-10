import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiFlag, FiCheckCircle, FiPlus, FiX } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import { DEFAULT_ANO, DEFAULT_MES } from '../../config/populationSpaceFacilities';
import { triggerMunicipio } from '../../services/populationSpaceService';

const DEFAULT_MUNICIPIOS = [
    { cod_ibge: '520870', uf: 'GO', ano: DEFAULT_ANO, mes: DEFAULT_MES },
    { cod_ibge: '520110', uf: 'GO', ano: DEFAULT_ANO, mes: DEFAULT_MES },
];

const PipelinePopulationMunicipioPage = () => {
    usePageTitle('PopulationSpace: Município');
    const navigate = useNavigate();

    const [municipios, setMunicipios] = useState(DEFAULT_MUNICIPIOS);
    const [diseaseName, setDiseaseName] = useState('Tuberculose');
    const [diseaseCode, setDiseaseCode] = useState('TUBE');
    const [taskId, setTaskId] = useState(null);
    const { isPending, isSuccess, isFailure, progress, message, error } = useCeleryTaskStatus(
        taskId, '/api/pipelines/population-space/tasks/'
    );

    const updateRow = (idx, field, value) => {
        setMunicipios(rows => rows.map((r, i) => (i === idx ? { ...r, [field]: value } : r)));
    };
    const addRow = () => setMunicipios(rows => [...rows, { cod_ibge: '', uf: '', ano: DEFAULT_ANO, mes: DEFAULT_MES }]);
    const removeRow = (idx) => setMunicipios(rows => rows.filter((_, i) => i !== idx));

    const run = async () => {
        setTaskId(null);
        try {
            const payload = municipios.map(m => ({
                cod_ibge: m.cod_ibge, uf: m.uf, ano: Number(m.ano), mes: m.mes ? Number(m.mes) : undefined,
            }));
            const diseases = diseaseCode ? [[diseaseName || diseaseCode, diseaseCode]] : [];
            const { task_id } = await triggerMunicipio(payload, diseases);
            setTaskId(task_id);
        } catch (err) {
            alert(`Falha ao disparar análise de município: ${err.response?.data?.error || err.message}`);
        }
    };

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => navigate(`/dashboards/population-municipio/viewer?taskId=${taskId}`), 1200);
        }
    }, [isSuccess, taskId, navigate]);

    const validRows = municipios.filter(m => m.cod_ibge && m.uf && m.ano);

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Município</h1>
                <p className="text-gray-500 mt-2 text-lg">SIH + SIM + SINASC + SINAN do mesmo território — PopulationSpace (BioSpace).</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Trata um MUNICÍPIO (não um estabelecimento) como unidade de análise, cruzando internações
                        (SIH, mensal), óbitos (SIM, anual) e nascimentos (SINASC, anual) do mesmo território ao
                        longo do tempo — mais incidência de um agravo do SINAN (anual), se informado abaixo. Código
                        IBGE de 6 dígitos (ex.: Goiânia/GO = 520870). Ainda não há busca por nome — preencha os
                        campos diretamente.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <FiFlag className="text-blue-500" /> Municípios
                    </h2>

                    <div className="space-y-2">
                        {municipios.map((m, idx) => (
                            <div key={idx} className="flex items-center gap-2">
                                <input
                                    type="text" placeholder="Cód. IBGE (6 díg.)" value={m.cod_ibge}
                                    onChange={e => updateRow(idx, 'cod_ibge', e.target.value)}
                                    className="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-sm font-mono"
                                />
                                <input
                                    type="text" placeholder="UF" value={m.uf} maxLength={2}
                                    onChange={e => updateRow(idx, 'uf', e.target.value.toUpperCase())}
                                    className="w-16 px-3 py-2 rounded-lg border border-gray-200 text-sm font-mono uppercase"
                                />
                                <input
                                    type="number" placeholder="Ano" value={m.ano}
                                    onChange={e => updateRow(idx, 'ano', e.target.value)}
                                    className="w-24 px-3 py-2 rounded-lg border border-gray-200 text-sm font-mono"
                                />
                                <input
                                    type="number" placeholder="Mês" value={m.mes} min={1} max={12}
                                    onChange={e => updateRow(idx, 'mes', e.target.value)}
                                    className="w-20 px-3 py-2 rounded-lg border border-gray-200 text-sm font-mono"
                                />
                                <button onClick={() => removeRow(idx)} className="p-2 text-gray-400 hover:text-red-500">
                                    <FiX />
                                </button>
                            </div>
                        ))}
                    </div>

                    <button onClick={addRow} className="flex items-center gap-2 text-sm font-bold text-blue-600 hover:text-blue-700">
                        <FiPlus /> Adicionar município
                    </button>

                    <div className="pt-2 border-t border-gray-100">
                        <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-2">
                            Agravo SINAN (opcional)
                        </h3>
                        <div className="flex items-center gap-2">
                            <input
                                type="text" placeholder="Nome (ex.: Tuberculose)" value={diseaseName}
                                onChange={e => setDiseaseName(e.target.value)}
                                className="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-sm"
                            />
                            <input
                                type="text" placeholder="Código (ex.: TUBE)" value={diseaseCode} maxLength={4}
                                onChange={e => setDiseaseCode(e.target.value.toUpperCase())}
                                className="w-32 px-3 py-2 rounded-lg border border-gray-200 text-sm font-mono uppercase"
                            />
                        </div>
                    </div>

                    {isFailure && <FeedbackMessage message={`Erro: ${error}`} type="error" />}

                    <button
                        onClick={run}
                        disabled={isPending || validRows.length < 1}
                        className={`w-full relative py-3 rounded-xl font-black text-white uppercase text-sm tracking-widest transition-all overflow-hidden
                            ${isPending || validRows.length < 1 ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'}`}
                    >
                        {isPending && (
                            <div className="absolute top-0 left-0 h-full bg-blue-800/40 transition-all duration-500 ease-out" style={{ width: `${progress}%` }}></div>
                        )}
                        <span className="relative z-10 flex items-center justify-center gap-2">
                            {isPending ? (
                                <><LoadingSpinner size="sm" color="white" /> {message || 'Processando...'} ({progress}%)</>
                            ) : isSuccess ? (
                                <><FiCheckCircle size={18} /> Concluído! Redirecionando...</>
                            ) : (
                                `Carregar município(s) (${validRows.length})`
                            )}
                        </span>
                    </button>
                </fieldset>
            </div>
        </div>
    );
};

export default PipelinePopulationMunicipioPage;
