import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiGitCommit, FiCheckCircle } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import FacilitySearchPicker from '../../components/common/FacilitySearchPicker';
import { KNOWN_FACILITIES } from '../../config/populationSpaceFacilities';
import { triggerTopology } from '../../services/populationSpaceService';

const PipelinePopulationTopologyPage = () => {
    usePageTitle('PopulationSpace: Topologia');
    const navigate = useNavigate();

    const [selected, setSelected] = useState(KNOWN_FACILITIES.slice(0, 8).map(f => ({ facility_uri: f.facility_uri, uf: f.uf })));
    const [minPersistence, setMinPersistence] = useState(0.5);
    const [maxDimension, setMaxDimension] = useState(1);
    const [nCubes, setNCubes] = useState(5);
    const [percOverlap, setPercOverlap] = useState(0.3);
    const [taskId, setTaskId] = useState(null);
    const { isPending, isSuccess, isFailure, progress, message, error } = useCeleryTaskStatus(
        taskId, '/api/pipelines/population-space/tasks/'
    );

    const run = async () => {
        setTaskId(null);
        try {
            const facilities = selected.map(f => ({ facility_uri: f.facility_uri, ano: 2025, mes: 12, uf: f.uf }));
            const { task_id } = await triggerTopology(facilities, minPersistence, maxDimension, nCubes, percOverlap);
            setTaskId(task_id);
        } catch (err) {
            alert(`Falha ao disparar análise topológica: ${err.response?.data?.error || err.message}`);
        }
    };

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => navigate(`/dashboards/population-topology/viewer?taskId=${taskId}`), 1200);
        }
    }, [isSuccess, taskId, navigate]);

    const canRun = selected.length >= 6;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Topologia</h1>
                <p className="text-gray-500 mt-2 text-lg">Homologia persistente + Mapper — PopulationSpace (BioSpace).</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Computa homologia persistente (biospace.topology, via ripser — Betti numbers) e um
                        grafo Mapper (via kmapper) sobre o mesmo espaço de representação usado em Comparar/
                        Grafo/Fatores — uma visão não-linear do "formato" da população de estabelecimentos.
                        O módulo mais exploratório desta série: com poucos estabelecimentos, tanto a
                        persistência quanto o Mapper tendem a ficar instáveis/degenerados — resultado
                        ilustrativo do método, nunca uma segmentação populacional validada.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <FiGitCommit className="text-blue-500" /> Estabelecimentos (mín. 6)
                    </h2>
                    <FacilitySearchPicker selected={selected} onChange={setSelected} suggestions={KNOWN_FACILITIES} />

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Limiar de persistência</label>
                            <input
                                type="range" min="0.1" max="2" step="0.1" value={minPersistence}
                                onChange={e => setMinPersistence(parseFloat(e.target.value))}
                                className="w-full h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
                            />
                            <div className="text-center text-lg font-black text-blue-600">{minPersistence.toFixed(1)}</div>
                        </div>
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Dimensão máxima (H_k)</label>
                            <input
                                type="range" min="0" max="2" step="1" value={maxDimension}
                                onChange={e => setMaxDimension(parseInt(e.target.value, 10))}
                                className="w-full h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
                            />
                            <div className="text-center text-lg font-black text-blue-600">H_{maxDimension}</div>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Mapper: nº de cubos</label>
                            <input
                                type="number" min="2" max="15" step="1" value={nCubes}
                                onChange={e => setNCubes(parseInt(e.target.value, 10))}
                                className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                            />
                        </div>
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Mapper: % sobreposição</label>
                            <input
                                type="number" min="0.1" max="0.9" step="0.1" value={percOverlap}
                                onChange={e => setPercOverlap(parseFloat(e.target.value))}
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
                                `Analisar topologia (${selected.length} estabelecimentos)`
                            )}
                        </span>
                    </button>
                </fieldset>
            </div>
        </div>
    );
};

export default PipelinePopulationTopologyPage;
