import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiDownload } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

export default function PopulationTransitionsViewerPage() {
    usePageTitle('Resultado - Transições de Fenótipo (PopulationSpace)');

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
                <Link to="/pipelines/population-transitions" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const facilities = result.facilities || [];
    const transitionSummary = result.transition_summary || [];
    const fileId = task.output_file_id;

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-transitions" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Transições de Fenótipo
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Transições de Fenótipo ao Longo do Tempo</h1>
                <p className="text-sm text-gray-500 mb-8">
                    {facilities.length} estabelecimentos, K={result.k ?? '—'}.
                </p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Cada linha é a trajetória de fenótipo (KMeans) de um estabelecimento ao longo das
                        competências carregadas. Com poucos estabelecimentos e meses, a matriz de transição é
                        ruído, não um padrão confiável.
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

                <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200 mb-6">
                    <h3 className="text-xs font-black text-gray-500 uppercase mb-3">Sequência de fenótipos por estabelecimento</h3>
                    <div className="overflow-x-auto">
                        <table className="min-w-full text-xs">
                            <thead className="bg-gray-50 border-b border-gray-200">
                                <tr>
                                    <th className="px-3 py-2 text-left font-bold text-gray-500 uppercase">Estabelecimento</th>
                                    {facilities[0]?.sequence.map(s => (
                                        <th key={s.competencia} className="px-3 py-2 text-center font-bold text-gray-500 uppercase">{s.competencia}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {facilities.map(f => (
                                    <tr key={f.facility_uri} className="border-b border-gray-100 last:border-0">
                                        <td className="px-3 py-2 font-mono">{f.facility_uri}</td>
                                        {f.sequence.map((s, i) => (
                                            <td key={i} className="px-3 py-2 text-center">
                                                <span className="px-2 py-0.5 rounded-full text-xs font-bold text-white bg-indigo-500">{s.phenotype ?? '—'}</span>
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {transitionSummary.length > 0 && (
                    <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200 mb-6">
                        <h3 className="text-xs font-black text-gray-500 uppercase mb-3">Transições observadas</h3>
                        <div className="overflow-x-auto">
                            <table className="min-w-full text-xs">
                                <thead className="bg-gray-50 border-b border-gray-200">
                                    <tr>
                                        <th className="px-3 py-2 text-left font-bold text-gray-500 uppercase">De</th>
                                        <th className="px-3 py-2 text-left font-bold text-gray-500 uppercase">Para</th>
                                        <th className="px-3 py-2 text-right font-bold text-gray-500 uppercase">N</th>
                                        <th className="px-3 py-2 text-right font-bold text-gray-500 uppercase">Média (dias)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {transitionSummary.map((t, i) => (
                                        <tr key={i} className="border-b border-gray-100 last:border-0">
                                            <td className="px-3 py-2">{t.from}</td>
                                            <td className="px-3 py-2">{t.to}</td>
                                            <td className="px-3 py-2 text-right">{t.n}</td>
                                            <td className="px-3 py-2 text-right">{t.media_dias.toFixed(1)}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                <p className="text-xs text-gray-400 italic">{result.caveat}</p>
            </div>
        </div>
    );
}
