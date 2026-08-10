import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiClock, FiCheckCircle } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import FacilitySearchPicker from '../../components/common/FacilitySearchPicker';
import { KNOWN_FACILITIES, KNOWN_COMPETENCIAS } from '../../config/populationSpaceFacilities';
import { triggerTransitions } from '../../services/populationSpaceService';

const PipelinePopulationTransitionsPage = () => {
    usePageTitle('PopulationSpace: Transições de Fenótipo');
    const navigate = useNavigate();

    const [selected, setSelected] = useState(KNOWN_FACILITIES.slice(0, 3).map(f => ({ facility_uri: f.facility_uri, uf: f.uf })));
    const [competencias, setCompetencias] = useState(['2025-11', '2025-12']);
    const [k, setK] = useState(2);
    const [taskId, setTaskId] = useState(null);
    const { isPending, isSuccess, isFailure, progress, message, error } = useCeleryTaskStatus(
        taskId, '/api/pipelines/population-space/tasks/'
    );

    const toggleCompetencia = (key) => setCompetencias(prev => prev.includes(key) ? prev.filter(c => c !== key) : [...prev, key]);

    const run = async () => {
        setTaskId(null);
        try {
            const chosen = KNOWN_COMPETENCIAS.filter(c => competencias.includes(`${c.ano}-${String(c.mes).padStart(2, '0')}`));
            const facilities = selected.map(f => ({
                facility_uri: f.facility_uri, uf: f.uf,
                competencias: chosen.map(c => ({ ano: c.ano, mes: c.mes })),
            }));
            const { task_id } = await triggerTransitions(facilities, k);
            setTaskId(task_id);
        } catch (err) {
            alert(`Falha ao disparar transições de fenótipo: ${err.response?.data?.error || err.message}`);
        }
    };

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => navigate(`/dashboards/population-transitions/viewer?taskId=${taskId}`), 1200);
        }
    }, [isSuccess, taskId, navigate]);

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Transições de Fenótipo</h1>
                <p className="text-gray-500 mt-2 text-lg">Ao longo do tempo — PopulationSpace (BioSpace).</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Único módulo que carrega várias competências por estabelecimento — a trajetória real
                        acumula um ponto por mês. biospace.longitudinal.TransitionAnalyzer mede a probabilidade
                        de transição entre fenótipos (KMeans) e o tempo real decorrido. Mais lento (uma consulta
                        SPARQL por estabelecimento por mês); com poucos estabelecimentos e meses, a matriz é
                        ruído, não um padrão confiável.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <FiClock className="text-blue-500" /> Estabelecimentos
                    </h2>
                    <FacilitySearchPicker selected={selected} onChange={setSelected} suggestions={KNOWN_FACILITIES} />

                    <div>
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Competências (mín. 2)</label>
                        <div className="flex gap-2">
                            {KNOWN_COMPETENCIAS.map(c => {
                                const key = `${c.ano}-${String(c.mes).padStart(2, '0')}`;
                                return (
                                    <label key={key} className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 rounded-lg border border-gray-100 cursor-pointer hover:bg-white hover:border-blue-200 transition text-xs font-bold text-gray-600">
                                        <input type="checkbox" checked={competencias.includes(key)} onChange={() => toggleCompetencia(key)} className="w-3.5 h-3.5 text-blue-600 rounded" />
                                        {c.label}
                                    </label>
                                );
                            })}
                        </div>
                    </div>

                    <div>
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Número de fenótipos (K)</label>
                        <input
                            type="range" min="2" max="4" step="1" value={k}
                            onChange={e => setK(parseInt(e.target.value, 10))}
                            className="w-full h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
                        />
                        <div className="text-center text-lg font-black text-blue-600">{k}</div>
                    </div>

                    {isFailure && <FeedbackMessage message={`Erro: ${error}`} type="error" />}

                    <button
                        onClick={run}
                        disabled={isPending || selected.length < 2 || competencias.length < 2}
                        className={`w-full relative py-3 rounded-xl font-black text-white uppercase text-sm tracking-widest transition-all overflow-hidden
                            ${isPending || selected.length < 2 || competencias.length < 2 ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'}`}
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
                                `Rodar transições (${selected.length} estabelecimentos x ${competencias.length} competências)`
                            )}
                        </span>
                    </button>
                </fieldset>
            </div>
        </div>
    );
};

export default PipelinePopulationTransitionsPage;
