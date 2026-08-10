import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiDownload } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

export default function PopulationUncertaintyViewerPage() {
    usePageTitle('Resultado - Previsão com Incerteza (PopulationSpace)');

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
                <Link to="/pipelines/population-uncertainty" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
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
                <Link to="/pipelines/population-uncertainty" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Previsão com Incerteza
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Previsão com Incerteza (Processo Gaussiano)</h1>
                <p className="text-sm text-gray-500 mb-8">
                    {result.n_facilities ?? 0} hospitais, alvo={result.target_feature}, kernel={result.kernel}.
                </p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Prevê um indicador de utilização a partir do perfil de força de trabalho e demografia
                        (nunca de si mesmo). z-score grande = o valor real diverge do que o perfil dos outros
                        estabelecimentos sugeriria.
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

                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-x-auto mb-4">
                    <table className="min-w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Estabelecimento</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">Real</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">Previsto</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">± incerteza</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">z-score</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(result.facilities || []).map(f => (
                                <tr key={f.facility_uri} className="border-b border-gray-100 last:border-0">
                                    <td className="px-4 py-3 font-mono text-xs">{f.facility_uri}</td>
                                    <td className="px-4 py-3 text-right">{f.actual.toFixed(2)}</td>
                                    <td className="px-4 py-3 text-right">{f.predicted_mean.toFixed(2)}</td>
                                    <td className="px-4 py-3 text-right">{f.predicted_std.toFixed(3)}</td>
                                    <td className="px-4 py-3 text-right font-bold">{f.z_score !== null ? f.z_score.toFixed(2) : '—'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <p className="text-xs text-gray-400 italic">{result.caveat}</p>
            </div>
        </div>
    );
}
