import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiClock, FiCheckCircle } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import FacilitySearchPicker from '../../components/common/FacilitySearchPicker';
import CompetenciaRangePicker from '../../components/common/CompetenciaRangePicker';
import { KNOWN_FACILITIES } from '../../config/populationSpaceFacilities';
import { triggerSurvival } from '../../services/populationSpaceService';

const EVENT_FEATURE_OPTIONS = [
    { value: 'mean_age_years', label: 'Idade média dos internados' },
    { value: 'pct_female', label: '% mulheres internadas' },
    { value: 'pct_race_white', label: '% raça/cor branca' },
    { value: 'pct_race_black', label: '% raça/cor preta' },
    { value: 'pct_race_brown', label: '% raça/cor parda' },
];

const PipelinePopulationSurvivalPage = () => {
    usePageTitle('PopulationSpace: Sobrevida (Fenótipo)');
    const navigate = useNavigate();

    const [selected, setSelected] = useState(KNOWN_FACILITIES.slice(0, 6).map(f => ({ facility_uri: f.facility_uri, uf: f.uf })));
    const [start, setStart] = useState({ ano: 2025, mes: 11 });
    const [end, setEnd] = useState({ ano: 2025, mes: 12 });
    const [eventFeature, setEventFeature] = useState('mean_age_years');
    const [eventThreshold, setEventThreshold] = useState('');
    const [k, setK] = useState(2);
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
            const { task_id } = await triggerSurvival(facilities, eventFeature, eventThreshold ? parseFloat(eventThreshold) : undefined, k);
            setTaskId(task_id);
        } catch (err) {
            alert(`Falha ao disparar análise de sobrevida: ${err.response?.data?.error || err.message}`);
        }
    };

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => navigate(`/dashboards/population-survival/viewer?taskId=${taskId}`), 1200);
        }
    }, [isSuccess, taskId, navigate]);

    const canRun = selected.length >= 6 && competenciasCount >= 2;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Sobrevida (Fenótipo)</h1>
                <p className="text-gray-500 mt-2 text-lg">Tempo até evento demográfico — PopulationSpace (BioSpace).</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Estratifica estabelecimentos por fenótipo de baseline (KMeans) e mede o tempo (em
                        competências) até a composição demográfica dos internados cruzar um limiar —
                        biospace.survival (Kaplan-Meier + Cox). Utilização hospitalar e força de trabalho são
                        cumulativas na BPHO (não variam por competência), por isso o evento é sempre sobre
                        demografia — a única Feature que de fato muda mês a mês.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <FiClock className="text-blue-500" /> Estabelecimentos (mín. 6)
                    </h2>
                    <FacilitySearchPicker selected={selected} onChange={setSelected} suggestions={KNOWN_FACILITIES} />

                    <div>
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Intervalo de competências (mín. 2 meses)</label>
                        <CompetenciaRangePicker start={start} end={end} onChange={(s, e) => { setStart(s); setEnd(e); }} nFacilities={selected.length} />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Evento (indicador demográfico)</label>
                            <select value={eventFeature} onChange={e => setEventFeature(e.target.value)} className="w-full p-2 border border-gray-300 rounded-lg text-sm">
                                {EVENT_FEATURE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                            </select>
                        </div>
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Limiar (opcional)</label>
                            <input
                                type="number" step="0.1" value={eventThreshold}
                                onChange={e => setEventThreshold(e.target.value)}
                                placeholder="mediana da amostra"
                                className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                            />
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
                                `Rodar sobrevida (${selected.length} estabelecimentos x ${competenciasCount} competências)`
                            )}
                        </span>
                    </button>
                </fieldset>
            </div>
        </div>
    );
};

export default PipelinePopulationSurvivalPage;
