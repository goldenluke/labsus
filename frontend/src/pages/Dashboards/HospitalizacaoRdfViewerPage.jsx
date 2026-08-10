import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { FiDownload, FiShare2, FiLayers, FiCheckCircle } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getHospitalizacaoRdfTask } from '../../services/hospitalizacaoRdfService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

const STATUS_LABELS = {
    Approved: 'Aprovada',
    Rejected: 'Rejeitada',
    RejectedWithError: 'Rejeitada com erro',
};

export default function HospitalizacaoRdfViewerPage() {
    usePageTitle('Resultado - Hospitalização (BPHO/RDF)');

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
                const data = await getHospitalizacaoRdfTask(taskId);
                setTask(data);
            } catch (err) {
                setError(err.response?.data?.error || err.message || 'Erro ao carregar os resultados.');
            } finally {
                setLoading(false);
            }
        })();
    }, [taskId]);

    const summary = task?.results_summary || {};
    const topFacilities = useMemo(() => summary.top_facilities || [], [summary]);
    const byStatus = useMemo(() => summary.by_status || {}, [summary]);

    const facilityPlotData = useMemo(() => {
        if (!topFacilities.length) return null;
        const sorted = [...topFacilities].sort((a, b) => a.hospitalizations - b.hospitalizations);
        return [{
            type: 'bar',
            orientation: 'h',
            y: sorted.map(f => f.cnes),
            x: sorted.map(f => f.hospitalizations),
            marker: { color: '#2563eb' },
            text: sorted.map(f => f.hospitalizations),
            textposition: 'outside',
        }];
    }, [topFacilities]);

    const statusPlotData = useMemo(() => {
        const entries = Object.entries(byStatus);
        if (!entries.length) return null;
        return [{
            type: 'bar',
            x: entries.map(([k]) => STATUS_LABELS[k] || k),
            y: entries.map(([, v]) => v),
            marker: { color: ['#2563eb', '#dc2626', '#f59e0b'] },
        }];
    }, [byStatus]);

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
                <Link to="/pipelines/hospitalizacao-rdf" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const fileId = task.output_file_id;

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/hospitalizacao-rdf" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Hospitalização (BPHO/RDF)
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-8">
                    Resultado - Hospitalizações agregadas via SPARQL (BPHO)
                </h1>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="space-y-6">
                        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
                            <h2 className="text-lg font-semibold text-gray-900 mb-4">Parâmetros da Carga</h2>
                            <dl className="space-y-3">
                                <div className="flex justify-between">
                                    <dt className="text-sm text-gray-500">UF</dt>
                                    <dd className="text-sm font-medium text-gray-900">{task.uf}</dd>
                                </div>
                                <div className="flex justify-between">
                                    <dt className="text-sm text-gray-500">Competência</dt>
                                    <dd className="text-sm font-medium text-gray-900">{String(task.mes).padStart(2, '0')}/{task.ano}</dd>
                                </div>
                                <div className="flex justify-between">
                                    <dt className="text-sm text-gray-500">Grupo SIH</dt>
                                    <dd className="text-sm font-medium text-gray-900">{task.grupo}</dd>
                                </div>
                            </dl>
                        </div>

                        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
                            <h2 className="text-lg font-semibold text-gray-900 mb-4">Armazenamento BPHO</h2>
                            <div className="grid grid-cols-1 gap-4">
                                <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-xl border border-blue-100">
                                    <FiLayers className="text-blue-600 w-6 h-6" />
                                    <div>
                                        <div className="text-2xl font-bold text-gray-900">
                                            {summary.total_hospitalizations_no_store?.toLocaleString('pt-BR') ?? '-'}
                                        </div>
                                        <div className="text-xs text-gray-500">Hospitalizations no armazenamento (total acumulado)</div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-3 p-3 bg-emerald-50 rounded-xl border border-emerald-100">
                                    <FiCheckCircle className="text-emerald-600 w-6 h-6" />
                                    <div>
                                        <div className="text-2xl font-bold text-gray-900">{topFacilities.length}</div>
                                        <div className="text-xs text-gray-500">Estabelecimentos no top-20 desta consulta</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {fileId && (
                            <a
                                href={`/api/files/${fileId}/`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors"
                            >
                                <FiDownload className="w-4 h-4" />
                                Ver CSV do agregado
                            </a>
                        )}
                    </div>

                    <div className="lg:col-span-2 space-y-6">
                        <InfoCard title="Como interpretar estes gráficos">
                            O gráfico de estabelecimentos vem de uma consulta <strong>SPARQL</strong> direta contra o
                            armazenamento RDF da BPHO (não um groupby de DataFrame) — cada estabelecimento é identificado
                            pelo mesmo código CNES usado em outros dados administrativos já carregados na ontologia. O
                            total de Hospitalizations por status reflete apenas o grupo de arquivo carregado nesta
                            requisição.
                        </InfoCard>

                        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
                            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                                <FiShare2 className="text-blue-500" /> Top-20 estabelecimentos por volume (CNES)
                            </h2>
                            {facilityPlotData ? (
                                <Plot
                                    data={facilityPlotData}
                                    layout={{
                                        xaxis: { title: 'Hospitalizations' },
                                        yaxis: { type: 'category', title: 'CNES', automargin: true },
                                        margin: { l: 90, r: 30, t: 20, b: 40 },
                                        height: 500,
                                    }}
                                    config={{ displayModeBar: false }}
                                    useResizeHandler
                                    style={{ width: '100%' }}
                                />
                            ) : (
                                <p className="text-sm text-gray-400 text-center py-10">Nenhum estabelecimento encontrado.</p>
                            )}
                        </div>

                        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
                            <h2 className="text-lg font-semibold text-gray-900 mb-4">Hospitalizations por status da AIH</h2>
                            {statusPlotData ? (
                                <Plot
                                    data={statusPlotData}
                                    layout={{ yaxis: { title: 'Contagem' }, margin: { l: 60, r: 30, t: 20, b: 40 }, height: 320 }}
                                    config={{ displayModeBar: false }}
                                    useResizeHandler
                                    style={{ width: '100%' }}
                                />
                            ) : (
                                <p className="text-sm text-gray-400 text-center py-10">Dados de status indisponíveis.</p>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
