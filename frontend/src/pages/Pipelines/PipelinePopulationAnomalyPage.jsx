import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiAlertOctagon, FiCheckCircle } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import FacilitySearchPicker from '../../components/common/FacilitySearchPicker';
import { KNOWN_FACILITIES, DEFAULT_ANO, DEFAULT_MES } from '../../config/populationSpaceFacilities';
import { triggerAnomaly } from '../../services/populationSpaceService';

const PipelinePopulationAnomalyPage = () => {
    usePageTitle('PopulationSpace: Detecção de Anomalias');
    const navigate = useNavigate();

    const [selected, setSelected] = useState(KNOWN_FACILITIES.slice(0, 5).map(f => ({ facility_uri: f.facility_uri, uf: f.uf })));
    const [contamination, setContamination] = useState('auto');
    const [taskId, setTaskId] = useState(null);
    const { isPending, isSuccess, isFailure, progress, message, error } = useCeleryTaskStatus(
        taskId, '/api/pipelines/population-space/tasks/'
    );

    const run = async () => {
        setTaskId(null);
        try {
            const facilities = selected.map(f => ({ facility_uri: f.facility_uri, ano: DEFAULT_ANO, mes: DEFAULT_MES, uf: f.uf }));
            const value = contamination === 'auto' ? 'auto' : parseFloat(contamination);
            const { task_id } = await triggerAnomaly(facilities, value);
            setTaskId(task_id);
        } catch (err) {
            alert(`Falha ao disparar detecção de anomalias: ${err.response?.data?.error || err.message}`);
        }
    };

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => navigate(`/dashboards/population-anomaly/viewer?taskId=${taskId}`), 1200);
        }
    }, [isSuccess, taskId, navigate]);

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Detecção de Anomalias</h1>
                <p className="text-gray-500 mt-2 text-lg">IsolationForest sobre o PopulationSpace (BioSpace).</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        biospace.anomaly.SklearnOutlierDetector sobre o RepresentationSpace completo —
                        sinaliza hospitais estatisticamente atípicos frente ao grupo selecionado (não uma
                        inspeção clínica individual).
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <FiAlertOctagon className="text-blue-500" /> Hospitais
                    </h2>
                    <FacilitySearchPicker selected={selected} onChange={setSelected} suggestions={KNOWN_FACILITIES} />

                    <div className="flex items-center gap-3">
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wide whitespace-nowrap">Contaminação</label>
                        <select
                            value={contamination}
                            onChange={e => setContamination(e.target.value)}
                            className="flex-1 p-2 border border-gray-300 rounded-lg text-sm"
                        >
                            <option value="auto">auto (heurística padrão do sklearn)</option>
                            <option value="0.1">0.1 (~10% esperado anômalo)</option>
                            <option value="0.2">0.2 (~20% esperado anômalo)</option>
                        </select>
                    </div>

                    {isFailure && <FeedbackMessage message={`Erro: ${error}`} type="error" />}

                    <button
                        onClick={run}
                        disabled={isPending || selected.length < 3}
                        className={`w-full relative py-3 rounded-xl font-black text-white uppercase text-sm tracking-widest transition-all overflow-hidden
                            ${isPending || selected.length < 3 ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'}`}
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
                                `Detectar anomalias (${selected.length} hospitais, mín. 3)`
                            )}
                        </span>
                    </button>
                </fieldset>
            </div>
        </div>
    );
};

export default PipelinePopulationAnomalyPage;
