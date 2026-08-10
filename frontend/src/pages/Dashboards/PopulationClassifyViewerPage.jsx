import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiDownload } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

export default function PopulationClassifyViewerPage() {
    usePageTitle('Resultado - Classificador + SHAP (PopulationSpace)');

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
                <Link to="/pipelines/population-classify" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const topFeatures = (result.top_features || []).filter(f => f.mean_abs_shap > 0);
    const fileId = task.output_file_id;

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-classify" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Classificador + SHAP
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Classificador (RandomForest) + Explicação (SHAP)</h1>
                <p className="text-sm text-gray-500 mb-8">
                    {result.n_facilities ?? 0} hospitais, indicador={result.label_feature}, limiar={result.threshold?.toFixed(2)}.
                </p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Separa hospitais acima/abaixo do limiar a partir do perfil de força de trabalho e
                        demografia. SHAP mostra quais variáveis mais pesaram na decisão do modelo, não uma
                        previsão clínica validada.
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
                    <h3 className="text-xs font-black text-gray-500 uppercase mb-3">Variáveis mais importantes (|SHAP| médio)</h3>
                    <div className="space-y-1.5">
                        {topFeatures.map(f => (
                            <div key={f.feature} className="flex items-center gap-2">
                                <span className="text-xs font-mono text-gray-600 w-56 truncate">{f.feature}</span>
                                <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                                    <div
                                        className="bg-blue-600 h-2 rounded-full"
                                        style={{ width: `${Math.min(100, (f.mean_abs_shap / topFeatures[0].mean_abs_shap) * 100)}%` }}
                                    />
                                </div>
                                <span className="text-xs font-bold text-gray-500 w-16 text-right">{f.mean_abs_shap.toFixed(3)}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-x-auto mb-4">
                    <table className="min-w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Estabelecimento</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">Valor real</th>
                                <th className="px-4 py-3 text-center font-bold text-gray-500 uppercase text-xs">Classe</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">P(alto)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {(result.facilities || []).map(f => (
                                <tr key={f.facility_uri} className="border-b border-gray-100 last:border-0">
                                    <td className="px-4 py-3 font-mono text-xs">{f.facility_uri}</td>
                                    <td className="px-4 py-3 text-right">{f.actual_value.toFixed(2)}</td>
                                    <td className="px-4 py-3 text-center">
                                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold text-white ${f.label_alto ? 'bg-amber-500' : 'bg-gray-400'}`}>
                                            {f.label_alto ? 'alto' : 'baixo'}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-right font-bold">{f.predicted_probability_alto.toFixed(3)}</td>
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
