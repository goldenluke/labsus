import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiGitMerge, FiCheckCircle } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import FacilitySearchPicker from '../../components/common/FacilitySearchPicker';
import CompetenciaRangePicker from '../../components/common/CompetenciaRangePicker';
import { KNOWN_FACILITIES, DEFAULT_ANO, DEFAULT_MES } from '../../config/populationSpaceFacilities';
import { triggerCompare } from '../../services/populationSpaceService';

const GEOMETRY_OPTIONS = [
    { value: 'euclidean', label: 'Euclidiana', description: 'Trata os 12 eixos como independentes -- padrão, mais simples de interpretar.' },
    { value: 'mahalanobis', label: 'Mahalanobis', description: 'Considera a correlação entre Features (covariância estimada da própria amostra).' },
    { value: 'cosine', label: 'Cosine', description: 'Compara só a direção do perfil, ignora magnitude -- não é uma métrica formal.' },
    { value: 'dtw', label: 'DTW (trajetória)', description: 'Compara a trajetória inteira (várias competências), não um snapshot -- precisa de intervalo de meses.' },
];

const PipelinePopulationComparePage = () => {
    usePageTitle('PopulationSpace: Comparar Estabelecimentos');
    const navigate = useNavigate();

    const [selected, setSelected] = useState(KNOWN_FACILITIES.slice(0, 3).map(f => ({ facility_uri: f.facility_uri, uf: f.uf })));
    const [geometry, setGeometry] = useState('euclidean');
    const [start, setStart] = useState({ ano: 2025, mes: 11 });
    const [end, setEnd] = useState({ ano: 2025, mes: 12 });
    const [taskId, setTaskId] = useState(null);
    const { isPending, isSuccess, isFailure, progress, message, error } = useCeleryTaskStatus(
        taskId, '/api/pipelines/population-space/tasks/'
    );

    const isDtw = geometry === 'dtw';

    const run = async () => {
        setTaskId(null);
        try {
            let facilities;
            if (isDtw) {
                const s = start.ano * 12 + (start.mes - 1);
                const e = end.ano * 12 + (end.mes - 1);
                const competencias = [];
                for (let d = s; d <= e; d++) competencias.push({ ano: Math.floor(d / 12), mes: (d % 12) + 1 });
                facilities = selected.map(f => ({ facility_uri: f.facility_uri, uf: f.uf, competencias }));
            } else {
                facilities = selected.map(f => ({ facility_uri: f.facility_uri, ano: DEFAULT_ANO, mes: DEFAULT_MES, uf: f.uf }));
            }
            const { task_id } = await triggerCompare(facilities, geometry);
            setTaskId(task_id);
        } catch (err) {
            alert(`Falha ao disparar comparação: ${err.response?.data?.error || err.message}`);
        }
    };

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => navigate(`/dashboards/population-compare/viewer?taskId=${taskId}`), 1200);
        }
    }, [isSuccess, taskId, navigate]);

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Comparar Estabelecimentos</h1>
                <p className="text-gray-500 mt-2 text-lg">PopulationSpace (BioSpace) — distância par a par, geometria à sua escolha.</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Mede a distância entre cada par de estabelecimentos selecionados no espaço de
                        representação completo (12 dimensões: utilização hospitalar, força de trabalho,
                        composição demográfica) — a geometria escolhida abaixo define o que "parecido"
                        significa (euclidiana, correlacionada, direcional, ou por trajetória).
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <FiGitMerge className="text-blue-500" /> Estabelecimentos
                    </h2>
                    <FacilitySearchPicker selected={selected} onChange={setSelected} suggestions={KNOWN_FACILITIES} />

                    <div>
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Geometria</label>
                        <select value={geometry} onChange={e => setGeometry(e.target.value)} className="w-full p-2 border border-gray-300 rounded-lg text-sm">
                            {GEOMETRY_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                        <p className="text-xs text-gray-400 mt-1">{GEOMETRY_OPTIONS.find(o => o.value === geometry)?.description}</p>
                    </div>

                    {isDtw && (
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase tracking-wide block mb-1">Intervalo de competências (mín. 2 meses)</label>
                            <CompetenciaRangePicker start={start} end={end} onChange={(s, e) => { setStart(s); setEnd(e); }} nFacilities={selected.length} />
                        </div>
                    )}

                    {isFailure && <FeedbackMessage message={`Erro: ${error}`} type="error" />}

                    <button
                        onClick={run}
                        disabled={isPending || selected.length < 2}
                        className={`w-full relative py-3 rounded-xl font-black text-white uppercase text-sm tracking-widest transition-all overflow-hidden
                            ${isPending || selected.length < 2 ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'}`}
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
                                `Comparar (${selected.length} estabelecimentos)`
                            )}
                        </span>
                    </button>
                </fieldset>
            </div>
        </div>
    );
};

export default PipelinePopulationComparePage;
