import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiAnchor, FiCheckCircle } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import FacilitySearchPicker from '../../components/common/FacilitySearchPicker';
import CompetenciaRangePicker from '../../components/common/CompetenciaRangePicker';
import { KNOWN_FACILITIES } from '../../config/populationSpaceFacilities';
import { triggerDynamics } from '../../services/populationSpaceService';

const PipelinePopulationDynamicsPage = () => {
    usePageTitle('PopulationSpace: Dinâmica & Estabilidade');
    const navigate = useNavigate();

    const [selected, setSelected] = useState(KNOWN_FACILITIES.slice(0, 8).map(f => ({ facility_uri: f.facility_uri, uf: f.uf })));
    const [start, setStart] = useState({ ano: 2025, mes: 10 });
    const [end, setEnd] = useState({ ano: 2025, mes: 12 });
    const [nWorst, setNWorst] = useState(5);
    const [taskId, setTaskId] = useState(null);
    const { isPending, isSuccess, isFailure, progress, message, error } = useCeleryTaskStatus(
        taskId, '/api/pipelines/population-space/tasks/'
    );

    const competenciasCount = (() => {
        if (!start || !end) return 0;
        const s = start.ano * 12 + (start.mes - 1);
        const e = end.ano * 12 + (end.mes - 1);
        return e >= s ? e - s + 1 : 0;
    })();

    const run = async () => {
        setTaskId(null);
        try {
            const s = start.ano * 12 + (start.mes - 1);
            const e = end.ano * 12 + (end.mes - 1);
            const competencias = [];
            for (let d = s; d <= e; d++) competencias.push({ ano: Math.floor(d / 12), mes: (d % 12) + 1 });

            const facilities = selected.map(f => ({ facility_uri: f.facility_uri, uf: f.uf, competencias }));
            const { task_id } = await triggerDynamics(facilities, nWorst);
            setTaskId(task_id);
        } catch (err) {
            alert(`Falha ao disparar análise de dinâmica: ${err.response?.data?.error || err.message}`);
        }
    };

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => navigate(`/dashboards/population-dynamics/viewer?taskId=${taskId}`), 1200);
        }
    }, [isSuccess, taskId, navigate]);

    const canRun = selected.length >= 6 && competenciasCount >= 2;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Dinâmica &amp; Estabilidade</h1>
                <p className="text-gray-500 mt-2 text-lg">Reversão à média por indicador — PopulationSpace (BioSpace).</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Agrupa TODOS os pares consecutivos (competência t, t+1) de TODOS os estabelecimentos
                        carregados e ajusta um processo de Ornstein-Uhlenbeck discreto POR INDICADOR (biospace.dynamics)
                        — não por estabelecimento. A pergunta é "qual destes 12 indicadores reverte à média
                        (estável) vs. diverge (instável) na população inteira, e quão rápido cada um se
                        recupera de uma perturbação?". Roda automaticamente uma checagem de robustez
                        (remove um estabelecimento por vez) sobre o indicador menos estável.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <FiAnchor className="text-blue-500" /> Estabelecimentos (mín. 6)
                    </h2>
                    <FacilitySearchPicker selected={selected} onChange={setSelected} suggestions={KNOWN_FACILITIES} />

                    <div>
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Intervalo de competências (mín. 2 meses)</label>
                        <CompetenciaRangePicker start={start} end={end} onChange={(s, e) => { setStart(s); setEnd(e); }} nFacilities={selected.length} />
                    </div>

                    <div>
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Nº de indicadores menos estáveis destacados (n_worst)</label>
                        <input
                            type="number" min="1" max="12" step="1" value={nWorst}
                            onChange={e => setNWorst(parseInt(e.target.value, 10))}
                            className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                        />
                    </div>

                    {isFailure && <FeedbackMessage message={`Erro: ${error}`} type="error" />}

                    <button
                        onClick={run}
                        disabled={isPending || !canRun}
                        className={`w-full relative py-3 rounded-xl font-black text-white uppercase text-sm tracking-widest transition-all overflow-hidden
                            ${isPending || !canRun ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'}`}
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
                                `Analisar dinâmica (${selected.length} estabelecimentos x ${competenciasCount} competências)`
                            )}
                        </span>
                    </button>
                </fieldset>
            </div>
        </div>
    );
};

export default PipelinePopulationDynamicsPage;
