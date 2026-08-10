import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiTrendingUp, FiCheckCircle } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import FacilitySearchPicker from '../../components/common/FacilitySearchPicker';
import { KNOWN_FACILITIES, DEFAULT_ANO, DEFAULT_MES } from '../../config/populationSpaceFacilities';
import { triggerPredictUncertainty } from '../../services/populationSpaceService';

const PipelinePopulationUncertaintyPage = () => {
    usePageTitle('PopulationSpace: Previsão com Incerteza');
    const navigate = useNavigate();

    const [selected, setSelected] = useState(KNOWN_FACILITIES.slice(0, 8).map(f => ({ facility_uri: f.facility_uri, uf: f.uf })));
    const [targetFeature, setTargetFeature] = useState('avg_length_of_stay_days');
    const [kernel, setKernel] = useState('rbf');
    const [taskId, setTaskId] = useState(null);
    const { isPending, isSuccess, isFailure, progress, message, error } = useCeleryTaskStatus(
        taskId, '/api/pipelines/population-space/tasks/'
    );

    const run = async () => {
        setTaskId(null);
        try {
            const facilities = selected.map(f => ({ facility_uri: f.facility_uri, ano: DEFAULT_ANO, mes: DEFAULT_MES, uf: f.uf }));
            const { task_id } = await triggerPredictUncertainty(facilities, targetFeature, kernel);
            setTaskId(task_id);
        } catch (err) {
            alert(`Falha ao disparar previsão com incerteza: ${err.response?.data?.error || err.message}`);
        }
    };

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => navigate(`/dashboards/population-uncertainty/viewer?taskId=${taskId}`), 1200);
        }
    }, [isSuccess, taskId, navigate]);

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Previsão com Incerteza</h1>
                <p className="text-gray-500 mt-2 text-lg">Processo Gaussiano (PopulationSpace/BioSpace).</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Prevê um indicador de utilização a partir do perfil de força de trabalho e demografia
                        (nunca a partir de si mesmo) — biospace.bayesian.GaussianProcessOperator devolve uma
                        faixa de incerteza por estabelecimento, não só um valor pontual. Com poucos
                        estabelecimentos frente ao número de variáveis, o modelo pode memorizar cada ponto
                        quase exatamente (std baixo para todos) — isso não é bom ajuste, é sinal de amostra
                        pequena demais.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <FiTrendingUp className="text-blue-500" /> Hospitais
                    </h2>
                    <FacilitySearchPicker selected={selected} onChange={setSelected} suggestions={KNOWN_FACILITIES} />

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Indicador alvo</label>
                            <select value={targetFeature} onChange={e => setTargetFeature(e.target.value)} className="w-full p-2 border border-gray-300 rounded-lg text-sm">
                                <option value="avg_length_of_stay_days">Tempo médio de internação</option>
                                <option value="n_hospitalizations">Número de internações</option>
                                <option value="pct_rejected">% AIH rejeitadas</option>
                            </select>
                        </div>
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Kernel (geometria)</label>
                            <select value={kernel} onChange={e => setKernel(e.target.value)} className="w-full p-2 border border-gray-300 rounded-lg text-sm">
                                <option value="rbf">RBF</option>
                                <option value="matern">Matérn</option>
                                <option value="linear">Linear</option>
                                <option value="periodic">Periódico</option>
                            </select>
                        </div>
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
                                `Prever com incerteza (${selected.length} hospitais, mín. 4)`
                            )}
                        </span>
                    </button>
                </fieldset>
            </div>
        </div>
    );
};

export default PipelinePopulationUncertaintyPage;
