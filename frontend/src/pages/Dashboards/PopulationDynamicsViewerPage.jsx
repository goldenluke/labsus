import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiDownload, FiCheckCircle, FiAlertTriangle } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

export default function PopulationDynamicsViewerPage() {
    usePageTitle('Resultado - Dinâmica & Estabilidade (PopulationSpace)');

    const location = useLocation();
    const taskId = useMemo(() => new URLSearchParams(location.search).get('taskId'), [location.search]);

    const [task, setTask] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!taskId) {
            setError('ID da tarefa não fornecido.');
            setLoading(false);
            return;
        }
        (async () => {
            setLoading(true);
            setError(null);
            try {
                const data = await getPopulationSpaceTask(taskId);
                setTask(data);
            } catch (err) {
                setError(err.response?.data?.error || err.message || 'Erro ao carregar os resultados.');
            } finally {
                setLoading(false);
            }
        })();
    }, [taskId]);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-50">
                <LoadingSpinner />
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gray-50 p-6">
                <FeedbackMessage type="error" message={error} />
                <Link to="/pipelines/population-dynamics" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const features = result.features || [];
    const robustness = result.robustness;
    const fileId = task.output_file_id;
    const maxAbsPhi = Math.max(...features.map(f => Math.abs(f.phi_per_day)), 1e-9);

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-dynamics" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Dinâmica &amp; Estabilidade
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Dinâmica &amp; Estabilidade</h1>
                <p className="text-sm text-gray-500 mb-8">
                    {result.n_facilities ?? 0} estabelecimentos, {result.n_features} indicador(es) analisado(s).
                </p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Cada barra é UM indicador (não um estabelecimento): φ é a taxa de contração diária de
                        um modelo de reversão à média AJUSTADO SOBRE TODA A POPULAÇÃO carregada — |φ| &lt; 1
                        (verde) significa que perturbações se dissipam (estável); |φ| &gt;= 1 (vermelho)
                        significa que o indicador diverge, na amostra atual. Indicadores cumulativos da BPHO
                        (utilização/força de trabalho) tendem a aparecer como "instáveis" só porque não variam
                        por competência nos dados carregados — isso é uma limitação dos DADOS, não do método.
                    </InfoCard>
                    {fileId && (
                        <a
                            href={`/api/files/${fileId}/`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors"
                        >
                            <FiDownload className="w-4 h-4" />
                            Ver CSV completo
                        </a>
                    )}
                </div>

                <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-gray-200">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Indicadores</div>
                        <div className="text-xl font-black text-gray-800">{result.n_features ?? 0}</div>
                    </div>
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-emerald-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Estáveis</div>
                        <div className="text-xl font-black text-emerald-700">{result.n_stable ?? 0}</div>
                    </div>
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-red-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Instáveis</div>
                        <div className="text-xl font-black text-red-700">{result.n_unstable ?? 0}</div>
                    </div>
                </div>

                <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200 mb-6">
                    <h3 className="text-xs font-black text-gray-500 uppercase mb-3">Taxa de contração diária (φ) por indicador</h3>
                    <div className="space-y-2">
                        {features.map(f => {
                            const pct = Math.min(100, (Math.abs(f.phi_per_day) / maxAbsPhi) * 100);
                            return (
                                <div key={f.name} className="flex items-center gap-2">
                                    <span className="text-xs font-mono text-gray-600 w-72 truncate" title={f.name}>{f.name}</span>
                                    <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                                        <div
                                            className={`h-2 rounded-full ${f.is_stable ? 'bg-emerald-500' : 'bg-red-500'}`}
                                            style={{ width: `${pct}%` }}
                                        />
                                    </div>
                                    <span className={`text-xs font-bold w-20 text-right ${f.is_stable ? 'text-emerald-700' : 'text-red-700'}`}>
                                        φ={f.phi_per_day.toFixed(3)}
                                    </span>
                                    <span className="text-xs text-gray-400 w-28 text-right">
                                        {f.half_life_days !== null ? `t½=${f.half_life_days.toFixed(0)}d` : '—'}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {robustness && (
                    <div className={`p-4 rounded-2xl shadow-sm border mb-6 ${robustness.conclusion_is_robust ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200'}`}>
                        <h3 className="text-xs font-black text-gray-500 uppercase mb-2 flex items-center gap-2">
                            {robustness.conclusion_is_robust ? <FiCheckCircle className="text-emerald-600" /> : <FiAlertTriangle className="text-amber-600" />}
                            Checagem de robustez — indicador menos estável
                        </h3>
                        <p className="text-sm text-gray-700 font-mono mb-1">{robustness.feature_name}</p>
                        <p className="text-sm text-gray-600">
                            φ completo = {robustness.phi_full.toFixed(4)} ({robustness.is_stable_full ? 'estável' : 'INSTÁVEL'}),
                            {' '}testado removendo {robustness.n_facilities_tested} estabelecimento(s) individualmente.
                        </p>
                        {robustness.conclusion_is_robust ? (
                            <p className="text-sm text-emerald-700 font-bold mt-1">Conclusão robusta — não depende de nenhum estabelecimento isolado.</p>
                        ) : (
                            <p className="text-sm text-amber-700 font-bold mt-1">
                                ⚠ Removendo o estabelecimento "{robustness.most_influential_facility}" sozinho, φ vira {robustness.most_influential_phi?.toFixed(4)}
                                {' '}— a conclusão depende deste estabelecimento.
                            </p>
                        )}
                    </div>
                )}

                <p className="text-xs text-gray-400 italic">{result.caveat}</p>
            </div>
        </div>
    );
}
