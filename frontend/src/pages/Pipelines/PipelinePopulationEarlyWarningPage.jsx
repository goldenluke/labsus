import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiBell, FiCheckCircle } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import FacilitySearchPicker from '../../components/common/FacilitySearchPicker';
import CompetenciaRangePicker from '../../components/common/CompetenciaRangePicker';
import { KNOWN_FACILITIES } from '../../config/populationSpaceFacilities';
import { triggerEarlyWarning } from '../../services/populationSpaceService';

const DETREND_OPTIONS = [
    { value: 'linear', label: 'Linear' },
    { value: 'gaussian', label: 'Kernel gaussiano' },
];

const PipelinePopulationEarlyWarningPage = () => {
    usePageTitle('PopulationSpace: Alerta Precoce');
    const navigate = useNavigate();

    const [selected, setSelected] = useState(KNOWN_FACILITIES.slice(0, 2).map(f => ({ facility_uri: f.facility_uri, uf: f.uf })));
    const [start, setStart] = useState({ ano: 2025, mes: 1 });
    const [end, setEnd] = useState({ ano: 2025, mes: 12 });
    const [minPoints, setMinPoints] = useState(8);
    const [windowSize, setWindowSize] = useState(4);
    const [nSurrogates, setNSurrogates] = useState(200);
    const [detrendMethod, setDetrendMethod] = useState('linear');
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
            const { task_id } = await triggerEarlyWarning(facilities, minPoints, windowSize, nSurrogates, detrendMethod);
            setTaskId(task_id);
        } catch (err) {
            alert(`Falha ao disparar análise de alerta precoce: ${err.response?.data?.error || err.message}`);
        }
    };

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => navigate(`/dashboards/population-early-warning/viewer?taskId=${taskId}`), 1200);
        }
    }, [isSuccess, taskId, navigate]);

    const canRun = selected.length >= 1 && competenciasCount >= 1;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Alerta Precoce</h1>
                <p className="text-gray-500 mt-2 text-lg">Critical slowing down entre competências — PopulationSpace (BioSpace).</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Mede, competência a competência, a distância de cada estabelecimento ao seu próprio
                        ponto de partida e busca sinais de "critical slowing down" (Scheffer et al. 2009,
                        Dakos et al. 2012) — variância, autocorrelação e assimetria crescentes, com
                        significância testada por substitutos AR(1) — antes que uma deterioração apareça nos
                        indicadores brutos. Precisa de trajetórias longas: por padrão, pelo menos {minPoints}{' '}
                        competências por estabelecimento para um resultado com dado suficiente.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <FiBell className="text-blue-500" /> Estabelecimentos
                    </h2>
                    <FacilitySearchPicker selected={selected} onChange={setSelected} suggestions={KNOWN_FACILITIES} />

                    <div>
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">
                            Intervalo de competências (recomendado: {'>='} {minPoints} meses)
                        </label>
                        <CompetenciaRangePicker start={start} end={end} onChange={(s, e) => { setStart(s); setEnd(e); }} nFacilities={selected.length} />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Mín. competências (min_points)</label>
                            <input
                                type="number" min="4" max="24" step="1" value={minPoints}
                                onChange={e => setMinPoints(parseInt(e.target.value, 10))}
                                className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                            />
                        </div>
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Janela deslizante (pontos)</label>
                            <input
                                type="number" min="2" max="12" step="1" value={windowSize}
                                onChange={e => setWindowSize(parseInt(e.target.value, 10))}
                                className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                            />
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Substitutos AR(1) para significância</label>
                            <input
                                type="number" min="0" max="1000" step="50" value={nSurrogates}
                                onChange={e => setNSurrogates(parseInt(e.target.value, 10))}
                                className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                            />
                        </div>
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Método de detrend</label>
                            <select value={detrendMethod} onChange={e => setDetrendMethod(e.target.value)} className="w-full p-2 border border-gray-300 rounded-lg text-sm">
                                {DETREND_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                            </select>
                        </div>
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
                                `Rodar alerta precoce (${selected.length} estabelecimentos x ${competenciasCount} competências)`
                            )}
                        </span>
                    </button>
                </fieldset>
            </div>
        </div>
    );
};

export default PipelinePopulationEarlyWarningPage;
