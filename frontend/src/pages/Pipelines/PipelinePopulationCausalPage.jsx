import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiActivity, FiCheckCircle } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import FacilitySearchPicker from '../../components/common/FacilitySearchPicker';
import { KNOWN_FACILITIES, DEFAULT_ANO, DEFAULT_MES } from '../../config/populationSpaceFacilities';
import { triggerCausal } from '../../services/populationSpaceService';

const PipelinePopulationCausalPage = () => {
    usePageTitle('PopulationSpace: Análise Causal');
    const navigate = useNavigate();

    const [selected, setSelected] = useState(KNOWN_FACILITIES.slice(0, 8).map(f => ({ facility_uri: f.facility_uri, uf: f.uf })));
    const [threshold, setThreshold] = useState('');
    const [taskId, setTaskId] = useState(null);
    const { isPending, isSuccess, isFailure, progress, message, error } = useCeleryTaskStatus(
        taskId, '/api/pipelines/population-space/tasks/'
    );

    const run = async () => {
        setTaskId(null);
        try {
            const facilities = selected.map(f => ({ facility_uri: f.facility_uri, ano: DEFAULT_ANO, mes: DEFAULT_MES, uf: f.uf }));
            const { task_id } = await triggerCausal(facilities, threshold ? parseFloat(threshold) : undefined);
            setTaskId(task_id);
        } catch (err) {
            alert(`Falha ao disparar análise causal: ${err.response?.data?.error || err.message}`);
        }
    };

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => navigate(`/dashboards/population-causal/viewer?taskId=${taskId}`), 1200);
        }
    }, [isSuccess, taskId, navigate]);

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Análise Causal</h1>
                <p className="text-gray-500 mt-2 text-lg">Densidade de força de trabalho x tempo de internação (PopulationSpace/BioSpace).</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Pareamento por escore de propensão (biospace.causal) entre hospitais de alta e baixa
                        densidade de vínculos/internação. Dado é cross-seccional (1 snapshot/estabelecimento) —
                        o resultado é uma comparação pós-pareamento, não uma diferença-em-diferenças, e com
                        poucos hospitais é ruído, não um efeito confiável.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <FiActivity className="text-blue-500" /> Hospitais
                    </h2>
                    <FacilitySearchPicker selected={selected} onChange={setSelected} suggestions={KNOWN_FACILITIES} />

                    <div className="flex items-center gap-3">
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wide whitespace-nowrap">
                            Limiar de densidade (opcional)
                        </label>
                        <input
                            type="number" step="0.1" value={threshold}
                            onChange={e => setThreshold(e.target.value)}
                            placeholder="mediana da amostra"
                            className="flex-1 p-2 border border-gray-300 rounded-lg text-sm"
                        />
                    </div>

                    {isFailure && <FeedbackMessage message={`Erro: ${error}`} type="error" />}

                    <button
                        onClick={run}
                        disabled={isPending || selected.length < 4}
                        className={`w-full relative py-3 rounded-xl font-black text-white uppercase text-sm tracking-widest transition-all overflow-hidden
                            ${isPending || selected.length < 4 ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'}`}
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
                                `Rodar análise causal (${selected.length} hospitais, mín. 4)`
                            )}
                        </span>
                    </button>
                </fieldset>
            </div>
        </div>
    );
};

export default PipelinePopulationCausalPage;
