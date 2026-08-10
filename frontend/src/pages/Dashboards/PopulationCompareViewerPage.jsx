import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiDownload } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

export default function PopulationCompareViewerPage() {
    usePageTitle('Resultado - Comparar Estabelecimentos (PopulationSpace)');

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
                <Link to="/pipelines/population-compare" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const distances = [...(result.distances || [])].sort((a, b) => a.distance - b.distance);
    const fileId = task.output_file_id;
    const geometry = result.geometry || 'euclidean';
    const geometryLabel = { euclidean: 'euclidiana', mahalanobis: 'Mahalanobis', cosine: 'cosine', dtw: 'DTW (trajetória)' }[geometry] || geometry;

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-compare" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Comparar Estabelecimentos
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Comparação par a par</h1>
                <p className="text-sm text-gray-500 mb-8">
                    {result.facilities?.length ?? 0} estabelecimentos, {distances.length} par(es) comparado(s) por distância {geometryLabel}.
                </p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Distância menor = perfis mais parecidos no espaço de representação completo
                        (12 dimensões: utilização hospitalar, força de trabalho, composição demográfica).
                        {geometry === 'mahalanobis' && ' Mahalanobis considera a correlação entre Features, ao contrário da euclidiana.'}
                        {geometry === 'cosine' && ' Cosine compara só a direção do perfil (ignora magnitude) e não é uma métrica formal (viola desigualdade triangular).'}
                        {geometry === 'dtw' && ' DTW compara a trajetória inteira ao longo das competências carregadas, não um snapshot único.'}
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

                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-x-auto">
                    <table className="min-w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Estabelecimento A</th>
                                <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Estabelecimento B</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">Distância ({geometryLabel})</th>
                            </tr>
                        </thead>
                        <tbody>
                            {distances.map((d, i) => (
                                <tr key={i} className="border-b border-gray-100 last:border-0">
                                    <td className="px-4 py-3 font-mono text-xs">{d.facility_a}</td>
                                    <td className="px-4 py-3 font-mono text-xs">{d.facility_b}</td>
                                    <td className="px-4 py-3 text-right font-bold">{d.distance.toFixed(3)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
