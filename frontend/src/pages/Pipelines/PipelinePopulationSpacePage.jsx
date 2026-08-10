import React, { useState, useCallback } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { FiSearch, FiCheckCircle, FiLayers } from 'react-icons/fi';

import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import usePageTitle from '../../hooks/usePageTitle';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import FacilitySearchPicker from '../../components/common/FacilitySearchPicker';
import { KNOWN_FACILITIES, KNOWN_PRIMARY_CARE_FACILITIES, DEFAULT_ANO, DEFAULT_MES } from '../../config/populationSpaceFacilities';
import { lookupFacility } from '../../services/populationSpaceService';

const PipelinePopulationSpacePage = () => {
    usePageTitle('PopulationSpace (BioSpace)');
    const navigate = useNavigate();

    // --- Representação: hospital (SIH) x atenção primária (ESF/SIA) --
    // populações estruturalmente disjuntas nesta base (Fase 64) -- trocar o
    // toggle troca a lista de estabelecimentos conhecidos e o loader usado
    // no backend (load_population_cohort x load_primary_care_cohort).
    const [representation, setRepresentation] = useState('hospital');
    const activeFacilities = representation === 'hospital' ? KNOWN_FACILITIES : KNOWN_PRIMARY_CARE_FACILITIES;

    // --- Busca individual por CNES ---
    const [cnes, setCnes] = useState('');
    const [uf, setUf] = useState('SP');
    const [lookupResult, setLookupResult] = useState(null);
    const [lookupLoading, setLookupLoading] = useState(false);
    const [lookupError, setLookupError] = useState(null);

    const handleLookup = async () => {
        if (!cnes.trim()) return;
        setLookupLoading(true);
        setLookupError(null);
        setLookupResult(null);
        try {
            const data = await lookupFacility(cnes.trim(), {
                ano: DEFAULT_ANO, mes: DEFAULT_MES, uf: uf || undefined, representation,
            });
            setLookupResult(data);
        } catch (err) {
            setLookupError(err.response?.data?.error || err.message || 'Erro ao buscar estabelecimento.');
        } finally {
            setLookupLoading(false);
        }
    };

    // --- Fenotipagem em lote ---
    const [selected, setSelected] = useState(KNOWN_FACILITIES.slice(0, 3).map(f => ({ facility_uri: f.facility_uri, uf: f.uf })));
    const [k, setK] = useState(2);
    const [taskId, setTaskId] = useState(null);
    const {
        isPending, isSuccess, isFailure,
        progress, message: taskMessage, error: taskError,
    } = useCeleryTaskStatus(taskId, '/api/pipelines/population-space/tasks/');

    const changeRepresentation = (rep) => {
        setRepresentation(rep);
        const list = rep === 'hospital' ? KNOWN_FACILITIES : KNOWN_PRIMARY_CARE_FACILITIES;
        setSelected(list.slice(0, 3).map(f => ({ facility_uri: f.facility_uri, uf: f.uf })));
        setLookupResult(null);
    };

    const triggerPipeline = useCallback(async () => {
        if (selected.length < 2) {
            alert('Selecione pelo menos 2 estabelecimentos para a fenotipagem.');
            return;
        }
        setTaskId(null);
        try {
            const token = localStorage.getItem('authToken');
            const facilities = selected.map(f => ({ facility_uri: f.facility_uri, ano: DEFAULT_ANO, mes: DEFAULT_MES, uf: f.uf }));

            const response = await axios.post('/api/pipelines/population-space/trigger/', {
                facilities, k, representation,
            }, { headers: { Authorization: `Token ${token}` } });

            setTaskId(response.data.task_id);
        } catch (err) {
            alert(`Falha ao disparar pipeline: ${err.response?.data?.error || err.message}`);
        }
    }, [selected, k, representation]);

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => {
                navigate(`/dashboards/population-space/viewer?taskId=${taskId}`);
            }, 1200);
        }
    }, [isSuccess, taskId, navigate]);

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">PopulationSpace (BioSpace)</h1>
                <p className="text-gray-500 mt-2 text-lg">
                    Estabelecimento de saúde como unidade de análise — não paciente. Reaproveita o
                    BioSpace (biospace/plugins/population/) sobre dados reais da BPHO + parquet do SIH.
                </p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Cada estabelecimento vira um ponto num espaço de representação (12 dimensões:
                        utilização hospitalar, força de trabalho, composição demográfica). A busca individual
                        consulta um único estabelecimento na hora; a fenotipagem em lote roda K-Means (BioSpace,
                        sem nenhuma modificação) sobre o conjunto selecionado e agrupa estabelecimentos parecidos.
                        As demais análises (comparação, causal, anomalia, risco, incerteza, classificador,
                        transições) têm cada uma sua própria página no menu.
                    </p>
                </InfoCard>

                {/* TOGGLE DE REPRESENTAÇÃO */}
                <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200 flex items-center justify-center gap-2">
                    <button
                        onClick={() => changeRepresentation('hospital')}
                        className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all
                            ${representation === 'hospital' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-blue-600'}`}
                    >
                        Hospitais (SIH)
                    </button>
                    <button
                        onClick={() => changeRepresentation('primary_care')}
                        className={`px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all
                            ${representation === 'primary_care' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-blue-600'}`}
                    >
                        Atenção Primária (ESF/SIA)
                    </button>
                </div>

                {/* BUSCA INDIVIDUAL */}
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <FiSearch className="text-blue-500" /> Buscar um estabelecimento (CNES)
                    </h2>
                    <div className="flex gap-3">
                        <input
                            type="text"
                            value={cnes}
                            onChange={e => setCnes(e.target.value)}
                            placeholder="Ex: 2077396"
                            className="flex-1 p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
                        />
                        <input
                            type="text"
                            value={uf}
                            onChange={e => setUf(e.target.value.toUpperCase())}
                            placeholder="UF (opcional)"
                            maxLength={2}
                            className="w-32 p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
                        />
                        <button
                            onClick={handleLookup}
                            disabled={lookupLoading || !cnes.trim()}
                            className={`px-5 rounded-xl font-bold text-white transition-all
                                ${lookupLoading || !cnes.trim() ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
                        >
                            {lookupLoading ? <LoadingSpinner size="sm" color="white" /> : 'Buscar'}
                        </button>
                    </div>
                    <p className="text-xs text-gray-400 mt-2">
                        Competência fixa em {String(DEFAULT_MES).padStart(2, '0')}/{DEFAULT_ANO}. Sem UF, a composição demográfica fica ausente (não inventada).
                    </p>

                    {lookupError && <FeedbackMessage message={lookupError} type="error" />}

                    {lookupResult && representation === 'hospital' && (
                        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="p-4 bg-blue-50 rounded-xl border border-blue-100">
                                <h3 className="text-xs font-black text-blue-700 uppercase mb-2">Utilização Hospitalar</h3>
                                <dl className="text-sm space-y-1">
                                    <div className="flex justify-between"><dt>Internações</dt><dd className="font-bold">{lookupResult.values.n_hospitalizations ?? '—'}</dd></div>
                                    <div className="flex justify-between"><dt>% Aprovadas</dt><dd className="font-bold">{lookupResult.values.pct_approved?.toFixed(1) ?? '—'}</dd></div>
                                    <div className="flex justify-between"><dt>Tempo médio (dias)</dt><dd className="font-bold">{lookupResult.values.avg_length_of_stay_days?.toFixed(2) ?? '—'}</dd></div>
                                </dl>
                            </div>
                            <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100">
                                <h3 className="text-xs font-black text-emerald-700 uppercase mb-2">Força de Trabalho</h3>
                                <dl className="text-sm space-y-1">
                                    <div className="flex justify-between"><dt>Vínculos</dt><dd className="font-bold">{lookupResult.values.n_affiliations ?? '—'}</dd></div>
                                    <div className="flex justify-between"><dt>% Com equipe</dt><dd className="font-bold">{lookupResult.values.pct_affiliations_with_team?.toFixed(1) ?? '—'}</dd></div>
                                </dl>
                            </div>
                            <div className="p-4 bg-purple-50 rounded-xl border border-purple-100">
                                <h3 className="text-xs font-black text-purple-700 uppercase mb-2">Composição Demográfica</h3>
                                <dl className="text-sm space-y-1">
                                    <div className="flex justify-between"><dt>Idade média</dt><dd className="font-bold">{lookupResult.values.mean_age_years?.toFixed(1) ?? '— (sem UF)'}</dd></div>
                                    <div className="flex justify-between"><dt>% Feminino</dt><dd className="font-bold">{lookupResult.values.pct_female?.toFixed(1) ?? '—'}</dd></div>
                                    <div className="flex justify-between"><dt>% Raça branca</dt><dd className="font-bold">{lookupResult.values.pct_race_white?.toFixed(1) ?? '—'}</dd></div>
                                </dl>
                            </div>
                        </div>
                    )}

                    {lookupResult && representation === 'primary_care' && (
                        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100">
                                <h3 className="text-xs font-black text-emerald-700 uppercase mb-2">Força de Trabalho (Atenção Primária)</h3>
                                <dl className="text-sm space-y-1">
                                    <div className="flex justify-between"><dt>Vínculos</dt><dd className="font-bold">{lookupResult.values.n_affiliations ?? '—'}</dd></div>
                                    <div className="flex justify-between"><dt>Equipes</dt><dd className="font-bold">{lookupResult.values.n_teams ?? '—'}</dd></div>
                                    <div className="flex justify-between"><dt>Profissionais/equipe</dt><dd className="font-bold">{lookupResult.values.staff_per_team?.toFixed?.(1) ?? lookupResult.values.staff_per_team ?? '—'}</dd></div>
                                    <div className="flex justify-between"><dt>Ocupações distintas</dt><dd className="font-bold">{lookupResult.values.n_roles ?? '—'}</dd></div>
                                </dl>
                            </div>
                        </div>
                    )}
                </div>

                {/* FENOTIPAGEM EM LOTE */}
                <fieldset disabled={isPending} className="space-y-6">
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <FiLayers className="text-blue-500" /> Estabelecimentos para fenotipar
                        </h2>
                        <FacilitySearchPicker selected={selected} onChange={setSelected} suggestions={activeFacilities} />
                    </div>

                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">Número de clusters (K)</h2>
                        <input
                            type="range" min="2" max="5" step="1"
                            value={k}
                            onChange={e => setK(parseInt(e.target.value, 10))}
                            className="w-full h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
                        />
                        <div className="text-center text-2xl font-black text-blue-600 mt-2">{k}</div>
                    </div>
                </fieldset>

                {isFailure && <FeedbackMessage message={`Erro na tarefa: ${taskError}`} type="error" />}

                <button
                    onClick={triggerPipeline}
                    disabled={isPending || selected.length < 2}
                    className={`w-full relative py-4 rounded-2xl font-black text-white transition-all shadow-xl overflow-hidden
                        ${isPending || selected.length < 2 ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'}`}
                >
                    {isPending && (
                        <div className="absolute top-0 left-0 h-full bg-blue-800/40 transition-all duration-500 ease-out" style={{ width: `${progress}%` }}></div>
                    )}
                    <span className="relative z-10 flex items-center justify-center gap-3 tracking-widest uppercase">
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
                            <span>RODAR FENOTIPAGEM ({selected.length} estabelecimentos)</span>
                        )}
                    </span>
                </button>
            </div>
        </div>
    );
};

export default PipelinePopulationSpacePage;
