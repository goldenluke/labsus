import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiZap, FiCheckCircle, FiPlus, FiX } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import FacilitySearchPicker from '../../components/common/FacilitySearchPicker';
import { KNOWN_FACILITIES, DEFAULT_ANO, DEFAULT_MES } from '../../config/populationSpaceFacilities';
import { triggerIntervene } from '../../services/populationSpaceService';

const FEATURE_OPTIONS = [
    { value: 'n_hospitalizations', label: 'Nº de internações' },
    { value: 'pct_approved', label: '% AIH aprovadas' },
    { value: 'pct_rejected', label: '% AIH rejeitadas' },
    { value: 'pct_rejected_with_error', label: '% AIH rejeitadas com erro' },
    { value: 'avg_length_of_stay_days', label: 'Tempo médio de internação' },
    { value: 'n_affiliations', label: 'Nº de vínculos profissionais' },
    { value: 'pct_affiliations_with_team', label: '% vínculos com equipe' },
    { value: 'mean_age_years', label: 'Idade média dos internados' },
    { value: 'pct_female', label: '% mulheres internadas' },
    { value: 'pct_race_white', label: '% raça/cor branca' },
    { value: 'pct_race_black', label: '% raça/cor preta' },
    { value: 'pct_race_brown', label: '% raça/cor parda' },
];

const PipelinePopulationIntervenePage = () => {
    usePageTitle('PopulationSpace: Intervenção (Contrafactual)');
    const navigate = useNavigate();

    const [selected, setSelected] = useState(KNOWN_FACILITIES.slice(0, 8).map(f => ({ facility_uri: f.facility_uri, uf: f.uf })));
    const [target, setTarget] = useState(KNOWN_FACILITIES[0].facility_uri);
    const [shifts, setShifts] = useState([{ feature: 'n_affiliations', delta: 50 }]);
    const [labelFeature, setLabelFeature] = useState('avg_length_of_stay_days');
    const [threshold, setThreshold] = useState('');
    const [taskId, setTaskId] = useState(null);
    const { isPending, isSuccess, isFailure, progress, message, error } = useCeleryTaskStatus(
        taskId, '/api/pipelines/population-space/tasks/'
    );

    const addShift = () => setShifts([...shifts, { feature: 'pct_rejected', delta: 0 }]);
    const removeShift = (i) => setShifts(shifts.filter((_, idx) => idx !== i));
    const updateShift = (i, field, value) => setShifts(shifts.map((s, idx) => idx === i ? { ...s, [field]: value } : s));

    const run = async () => {
        setTaskId(null);
        try {
            const facilities = selected.map(f => ({ facility_uri: f.facility_uri, ano: DEFAULT_ANO, mes: DEFAULT_MES, uf: f.uf }));
            const shiftsPayload = Object.fromEntries(shifts.map(s => [s.feature, parseFloat(s.delta)]));
            const { task_id } = await triggerIntervene(facilities, target, shiftsPayload, null, labelFeature, threshold ? parseFloat(threshold) : undefined);
            setTaskId(task_id);
        } catch (err) {
            alert(`Falha ao disparar intervenção: ${err.response?.data?.error || err.message}`);
        }
    };

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => navigate(`/dashboards/population-intervene/viewer?taskId=${taskId}`), 1200);
        }
    }, [isSuccess, taskId, navigate]);

    const canRun = selected.length >= 6 && selected.some(f => f.facility_uri === target) && shifts.length > 0;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Intervenção (Contrafactual)</h1>
                <p className="text-gray-500 mt-2 text-lg">Simulador "e se" — PopulationSpace (BioSpace).</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Desloca Features de UM estabelecimento-alvo (biospace.intervention.FeatureShiftIntervention,
                        em unidade bruta — ex.: "+50 vínculos") e mede o efeito no Score de Risco
                        (biospace.risk) e na probabilidade do Classificador (biospace.prediction), ambos já
                        treinados sobre os demais estabelecimentos selecionados.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <FiZap className="text-blue-500" /> Hospitais (mín. 6)
                    </h2>
                    <FacilitySearchPicker selected={selected} onChange={setSelected} suggestions={KNOWN_FACILITIES} />

                    <div>
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Estabelecimento-alvo</label>
                        <select value={target} onChange={e => setTarget(e.target.value)} className="w-full p-2 border border-gray-300 rounded-lg text-sm font-mono">
                            {selected.map(f => <option key={f.facility_uri} value={f.facility_uri}>{f.facility_uri}</option>)}
                        </select>
                    </div>

                    <div>
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Shifts (deslocamentos em unidade bruta)</label>
                        <div className="space-y-2">
                            {shifts.map((s, i) => (
                                <div key={i} className="flex items-center gap-2">
                                    <select
                                        value={s.feature}
                                        onChange={e => updateShift(i, 'feature', e.target.value)}
                                        className="flex-1 p-2 border border-gray-300 rounded-lg text-sm"
                                    >
                                        {FEATURE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                                    </select>
                                    <input
                                        type="number" step="0.1" value={s.delta}
                                        onChange={e => updateShift(i, 'delta', e.target.value)}
                                        className="w-28 p-2 border border-gray-300 rounded-lg text-sm text-right"
                                    />
                                    <button type="button" onClick={() => removeShift(i)} className="text-gray-400 hover:text-red-500 p-1">
                                        <FiX size={16} />
                                    </button>
                                </div>
                            ))}
                        </div>
                        <button
                            type="button" onClick={addShift}
                            className="mt-2 flex items-center gap-1.5 text-xs font-bold text-blue-600 hover:text-blue-700"
                        >
                            <FiPlus size={14} /> Adicionar shift
                        </button>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Indicador (classificador)</label>
                            <select value={labelFeature} onChange={e => setLabelFeature(e.target.value)} className="w-full p-2 border border-gray-300 rounded-lg text-sm">
                                <option value="avg_length_of_stay_days">Tempo médio de internação</option>
                                <option value="n_hospitalizations">Número de internações</option>
                                <option value="pct_rejected">% AIH rejeitadas</option>
                            </select>
                        </div>
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Limiar (opcional)</label>
                            <input
                                type="number" step="0.1" value={threshold}
                                onChange={e => setThreshold(e.target.value)}
                                placeholder="mediana da amostra"
                                className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                            />
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
                                `Simular intervenção (${selected.length} hospitais, ${shifts.length} shift(s))`
                            )}
                        </span>
                    </button>
                </fieldset>
            </div>
        </div>
    );
};

export default PipelinePopulationIntervenePage;
