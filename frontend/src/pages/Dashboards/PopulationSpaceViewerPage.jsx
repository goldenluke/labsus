import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { FiDownload } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

const CLUSTER_COLORS = ['#2563eb', '#dc2626', '#16a34a', '#d97706', '#7c3aed'];

export default function PopulationSpaceViewerPage() {
    usePageTitle('Resultado - PopulationSpace (BioSpace)');

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

    const facilities = task?.results_summary?.facilities || [];
    const clusterNames = useMemo(() => [...new Set(facilities.map(f => f.cluster))].sort(), [facilities]);

    const scatterData = useMemo(() => {
        return clusterNames.map((clusterName, i) => {
            const members = facilities.filter(f => f.cluster === clusterName);
            return {
                type: 'scatter',
                mode: 'markers',
                name: clusterName,
                x: members.map(f => f.values.n_hospitalizations),
                y: members.map(f => f.values.n_affiliations),
                text: members.map(f => f.facility_uri),
                marker: { size: 14, color: CLUSTER_COLORS[i % CLUSTER_COLORS.length] },
            };
        });
    }, [facilities, clusterNames]);

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
                <Link to="/pipelines/population-space" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const fileId = task.output_file_id;

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-space" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para PopulationSpace
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">
                    Resultado - Fenotipagem de Estabelecimentos (BioSpace)
                </h1>
                <p className="text-sm text-gray-500 mb-8">
                    {facilities.length} estabelecimentos, K={task.k} (KMeans) — cada ponto é um estabelecimento, não um paciente.
                </p>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                    <div className="space-y-4">
                        <InfoCard title="Como interpretar o gráfico">
                            Cada ponto é um estabelecimento de saúde, posicionado por volume de internação
                            (eixo X) e vínculos profissionais registrados (eixo Y). A cor vem do cluster
                            (KMeans, `biospace.phenotyping.kmeans`) rodado sobre as 12 dimensões do
                            RepresentationSpace — não só estas duas mostradas aqui.
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
                    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
                        <Plot
                            data={scatterData}
                            layout={{
                                xaxis: { title: 'Hospitalizations' },
                                yaxis: { title: 'Affiliations (vínculos profissionais)' },
                                margin: { l: 60, r: 20, t: 20, b: 50 },
                                height: 420,
                                legend: { orientation: 'h', y: -0.2 },
                            }}
                            config={{ displayModeBar: false }}
                            useResizeHandler
                            style={{ width: '100%' }}
                        />
                    </div>
                </div>

                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-x-auto">
                    <table className="min-w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Estabelecimento</th>
                                <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Cluster</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">Internações</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">Tempo médio (dias)</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">Vínculos</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">Idade média</th>
                            </tr>
                        </thead>
                        <tbody>
                            {facilities.map(f => (
                                <tr key={f.facility_uri} className="border-b border-gray-100 last:border-0">
                                    <td className="px-4 py-3 font-mono text-xs">{f.facility_uri}</td>
                                    <td className="px-4 py-3">
                                        <span className="px-2 py-1 rounded-full text-xs font-bold text-white" style={{
                                            backgroundColor: CLUSTER_COLORS[clusterNames.indexOf(f.cluster) % CLUSTER_COLORS.length],
                                        }}>
                                            {f.cluster}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-right">{f.values.n_hospitalizations ?? '—'}</td>
                                    <td className="px-4 py-3 text-right">{f.values.avg_length_of_stay_days?.toFixed(2) ?? '—'}</td>
                                    <td className="px-4 py-3 text-right">{f.values.n_affiliations ?? '—'}</td>
                                    <td className="px-4 py-3 text-right">{f.values.mean_age_years?.toFixed(1) ?? '— (sem UF)'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
