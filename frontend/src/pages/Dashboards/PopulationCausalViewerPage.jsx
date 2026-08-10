import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiDownload } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

export default function PopulationCausalViewerPage() {
    usePageTitle('Resultado - Análise Causal (PopulationSpace)');

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
                <Link to="/pipelines/population-causal" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const fileId = task.output_file_id;

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-causal" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Análise Causal
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Densidade de Força de Trabalho x Tempo de Internação</h1>
                <p className="text-sm text-gray-500 mb-8">{result.n_facilities ?? 0} hospitais analisados.</p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Pareamento por escore de propensão (biospace.causal) entre hospitais de alta e baixa
                        densidade de vínculos/internação. Dado cross-seccional — comparação pós-pareamento,
                        não diferença-em-diferenças.
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

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-blue-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Limiar (densidade)</div>
                        <div className="text-xl font-black text-blue-700">{result.threshold?.toFixed(2) ?? '—'}</div>
                    </div>
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-emerald-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">AUC (propensão, CV)</div>
                        <div className="text-xl font-black text-emerald-700">{result.propensity_cv_auc?.toFixed(2) ?? '—'}</div>
                    </div>
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-purple-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Pares pareados</div>
                        <div className="text-xl font-black text-purple-700">{result.matched_pairs?.length ?? 0}</div>
                    </div>
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-amber-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">SMD médio (antes → depois)</div>
                        <div className="text-lg font-black text-amber-700">
                            {result.mean_absolute_smd_before?.toFixed(2)} → {result.mean_absolute_smd_after?.toFixed(2)}
                        </div>
                    </div>
                </div>

                {result.los_comparison && (
                    <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200 text-sm mb-6">
                        <h3 className="text-xs font-black text-gray-500 uppercase mb-2">Tempo de internação: tratado x controle (pareados)</h3>
                        <div className="flex justify-between"><span>Alta densidade (tratado)</span><span className="font-bold">{result.los_comparison.treated_mean_los_days.toFixed(2)} dias</span></div>
                        <div className="flex justify-between"><span>Baixa densidade (controle)</span><span className="font-bold">{result.los_comparison.control_mean_los_days.toFixed(2)} dias</span></div>
                        <div className="flex justify-between border-t border-gray-200 mt-1 pt-1"><span>Diferença</span><span className="font-black">{result.los_comparison.difference_days.toFixed(2)} dias</span></div>
                    </div>
                )}

                {result.matched_pairs?.length > 0 && (
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-x-auto mb-6">
                        <table className="min-w-full text-sm">
                            <thead className="bg-gray-50 border-b border-gray-200">
                                <tr>
                                    <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Alta densidade</th>
                                    <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Baixa densidade (pareado)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {result.matched_pairs.map(([a, b], i) => (
                                    <tr key={i} className="border-b border-gray-100 last:border-0">
                                        <td className="px-4 py-3 font-mono text-xs">{a}</td>
                                        <td className="px-4 py-3 font-mono text-xs">{b}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                <p className="text-xs text-gray-400 italic">{result.caveat}</p>
            </div>
        </div>
    );
}
