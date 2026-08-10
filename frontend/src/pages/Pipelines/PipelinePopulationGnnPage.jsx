import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiGitBranch, FiCheckCircle } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import FacilitySearchPicker from '../../components/common/FacilitySearchPicker';
import { KNOWN_FACILITIES } from '../../config/populationSpaceFacilities';
import { triggerGnn } from '../../services/populationSpaceService';

const POINT_GEOMETRY_OPTIONS = [
    { value: 'euclidean', label: 'Euclidiana', description: 'Trata os 12 eixos como independentes -- padrão, mais simples de interpretar.' },
    { value: 'mahalanobis', label: 'Mahalanobis', description: 'Considera a correlação entre Features (covariância estimada da própria amostra).' },
    { value: 'cosine', label: 'Cosine', description: 'Compara só a direção do perfil, ignora magnitude -- não é uma métrica formal.' },
];

const PipelinePopulationGnnPage = () => {
    usePageTitle('PopulationSpace: GNN (Classificação de Nós)');
    const navigate = useNavigate();

    const [selected, setSelected] = useState(KNOWN_FACILITIES.slice(0, 10).map(f => ({ facility_uri: f.facility_uri, uf: f.uf })));
    const [geometry, setGeometry] = useState('euclidean');
    const [k, setK] = useState(5);
    const [phenotypeK, setPhenotypeK] = useState(3);
    const [labelFraction, setLabelFraction] = useState(0.5);
    const [hiddenDim, setHiddenDim] = useState(16);
    const [epochs, setEpochs] = useState(300);
    const [learningRate, setLearningRate] = useState(0.05);
    const [taskId, setTaskId] = useState(null);
    const { isPending, isSuccess, isFailure, progress, message, error } = useCeleryTaskStatus(
        taskId, '/api/pipelines/population-space/tasks/'
    );

    const nLabeled = Math.round(labelFraction * selected.length);
    const nTest = selected.length - nLabeled;

    const run = async () => {
        setTaskId(null);
        try {
            const facilities = selected.map(f => ({ facility_uri: f.facility_uri, ano: 2025, mes: 12, uf: f.uf }));
            const { task_id } = await triggerGnn(facilities, geometry, k, phenotypeK, labelFraction, hiddenDim, epochs, learningRate);
            setTaskId(task_id);
        } catch (err) {
            alert(`Falha ao disparar GNN: ${err.response?.data?.error || err.message}`);
        }
    };

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => navigate(`/dashboards/population-gnn/viewer?taskId=${taskId}`), 1200);
        }
    }, [isSuccess, taskId, navigate]);

    const canRun = selected.length >= 6 && nLabeled >= 2 && nTest >= 2;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">GNN (Classificação de Nós)</h1>
                <p className="text-gray-500 mt-2 text-lg">Graph Convolutional Network sobre o grafo de similaridade — PopulationSpace (BioSpace).</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Constrói o mesmo grafo k-NN do módulo Grafo de Similaridade e treina uma GCN de 2
                        camadas (biospace.gnn.SimpleGCN, NumPy puro, Kipf &amp; Welling 2017) para propagar o
                        fenótipo (KMeans) pela estrutura do grafo. Só uma fração dos estabelecimentos entra
                        "rotulada" (treino); os demais participam da propagação mas são avaliados como
                        "teste" — a pergunta é se a topologia do grafo sozinha recupera o fenótipo de quem
                        não foi rotulado, comparado a um baseline ingênuo (sempre prever a classe majoritária).
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <FiGitBranch className="text-blue-500" /> Estabelecimentos (mín. 6)
                    </h2>
                    <FacilitySearchPicker selected={selected} onChange={setSelected} suggestions={KNOWN_FACILITIES} />

                    <div>
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Geometria</label>
                        <select value={geometry} onChange={e => setGeometry(e.target.value)} className="w-full p-2 border border-gray-300 rounded-lg text-sm">
                            {POINT_GEOMETRY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                        <p className="text-xs text-gray-400 mt-1">{POINT_GEOMETRY_OPTIONS.find(o => o.value === geometry)?.description}</p>
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Vizinhos por nó (K)</label>
                            <input
                                type="range" min="2" max="10" step="1" value={k}
                                onChange={e => setK(parseInt(e.target.value, 10))}
                                className="w-full h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
                            />
                            <div className="text-center text-lg font-black text-blue-600">{k}</div>
                        </div>
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Fenótipos (K)</label>
                            <input
                                type="range" min="2" max="4" step="1" value={phenotypeK}
                                onChange={e => setPhenotypeK(parseInt(e.target.value, 10))}
                                className="w-full h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
                            />
                            <div className="text-center text-lg font-black text-blue-600">{phenotypeK}</div>
                        </div>
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Fração rotulada (treino)</label>
                            <input
                                type="range" min="0.1" max="0.9" step="0.1" value={labelFraction}
                                onChange={e => setLabelFraction(parseFloat(e.target.value))}
                                className="w-full h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-blue-600"
                            />
                            <div className="text-center text-lg font-black text-blue-600">{labelFraction.toFixed(1)}</div>
                        </div>
                    </div>

                    <p className="text-xs text-gray-400">
                        {selected.length} estabelecimento(s) &rarr; ~{nLabeled} rotulado(s) (treino), ~{nTest} de teste (avaliação).
                    </p>

                    <div className="grid grid-cols-3 gap-3">
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Camada oculta (dim)</label>
                            <input
                                type="number" min="4" max="64" step="4" value={hiddenDim}
                                onChange={e => setHiddenDim(parseInt(e.target.value, 10))}
                                className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                            />
                        </div>
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Épocas</label>
                            <input
                                type="number" min="50" max="1000" step="50" value={epochs}
                                onChange={e => setEpochs(parseInt(e.target.value, 10))}
                                className="w-full p-2 border border-gray-300 rounded-lg text-sm"
                            />
                        </div>
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Taxa de aprendizado</label>
                            <input
                                type="number" min="0.001" max="0.5" step="0.005" value={learningRate}
                                onChange={e => setLearningRate(parseFloat(e.target.value))}
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
                                `Treinar GNN (${selected.length} estabelecimentos)`
                            )}
                        </span>
                    </button>
                </fieldset>
            </div>
        </div>
    );
};

export default PipelinePopulationGnnPage;
