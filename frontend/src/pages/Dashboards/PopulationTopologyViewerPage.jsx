import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { FiDownload } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

function buildMapperTraces(nodes, edges) {
    const nodesById = Object.fromEntries(nodes.map(n => [n.node, n]));
    const edgeX = [];
    const edgeY = [];
    for (const e of edges) {
        const a = nodesById[e.source];
        const b = nodesById[e.target];
        if (!a || !b) continue;
        edgeX.push(a.x, b.x, null);
        edgeY.push(a.y, b.y, null);
    }
    const edgeTrace = {
        x: edgeX, y: edgeY, type: 'scatter', mode: 'lines',
        line: { width: 1, color: 'rgba(148, 163, 184, 0.6)' },
        hoverinfo: 'none', showlegend: false,
    };
    const nodeTrace = {
        x: nodes.map(n => n.x),
        y: nodes.map(n => n.y),
        type: 'scatter', mode: 'markers',
        name: 'Nó Mapper',
        marker: { size: nodes.map(n => 10 + n.size * 4), color: '#4f46e5', line: { width: 1, color: '#fff' } },
        text: nodes.map(n => `${n.node}<br>${n.size} estabelecimento(s)<br>${n.members.join(', ')}`),
        hoverinfo: 'text',
    };
    return [edgeTrace, nodeTrace];
}

export default function PopulationTopologyViewerPage() {
    usePageTitle('Resultado - Topologia (PopulationSpace)');

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
                <Link to="/pipelines/population-topology" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const bettiNumbers = result.betti_numbers || {};
    const topPersistences = result.top_persistences || {};
    const mapper = result.mapper || { nodes: [], edges: [] };
    const fileId = task.output_file_id;
    const dimensions = Object.keys(bettiNumbers);

    const plotData = buildMapperTraces(mapper.nodes || [], mapper.edges || []);
    const plotLayout = {
        xaxis: { visible: false, zeroline: false },
        yaxis: { visible: false, zeroline: false },
        margin: { t: 10, b: 10, l: 10, r: 10 },
        height: 460,
        hovermode: 'closest',
        showlegend: false,
        plot_bgcolor: 'white',
    };

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-topology" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Topologia
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Topologia (Persistência + Mapper)</h1>
                <p className="text-sm text-gray-500 mb-8">
                    {result.n_facilities ?? 0} estabelecimentos, limiar de persistência={result.min_persistence}.
                </p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Betti number = nº de características topológicas (componentes em H_0, "buracos" em
                        H_1) com persistência acima do limiar escolhido — não é um número universal, depende
                        inteiramente desse limiar. O grafo Mapper resume a forma do espaço: cada nó é um
                        cluster de estabelecimentos numa faixa da lente (norma L2), arestas ligam nós com
                        estabelecimentos em comum. Com poucos estabelecimentos, ambos tendem a ficar
                        instáveis — ilustrativo do método, não uma segmentação validada.
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
                    {dimensions.map(dim => (
                        <div key={dim} className="p-4 bg-white rounded-2xl shadow-sm border border-indigo-100">
                            <div className="text-xs text-gray-500 uppercase font-bold mb-1">Betti {dim}</div>
                            <div className="text-xl font-black text-indigo-700">{bettiNumbers[dim]}</div>
                        </div>
                    ))}
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-emerald-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Mapper</div>
                        <div className="text-xl font-black text-emerald-700">{mapper.n_nodes} nó(s) / {mapper.n_edges} aresta(s)</div>
                    </div>
                </div>

                {dimensions.map(dim => (
                    <div key={dim} className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200 mb-6">
                        <h3 className="text-xs font-black text-gray-500 uppercase mb-3">Top persistências — {dim}</h3>
                        {(topPersistences[dim] || []).length > 0 ? (
                            <div className="space-y-1.5">
                                {topPersistences[dim].map((p, i) => {
                                    const max = Math.max(...topPersistences[dim], 1e-9);
                                    return (
                                        <div key={i} className="flex items-center gap-2">
                                            <span className="text-xs font-mono text-gray-500 w-24">#{i + 1}</span>
                                            <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                                                <div className="bg-indigo-500 h-2 rounded-full" style={{ width: `${Math.min(100, (p / max) * 100)}%` }} />
                                            </div>
                                            <span className="text-xs font-bold text-gray-600 w-16 text-right">{p.toFixed(3)}</span>
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <p className="text-sm text-gray-400 italic">Nenhuma característica topológica nesta dimensão.</p>
                        )}
                    </div>
                ))}

                <div className="bg-white p-2 rounded-2xl shadow-sm border border-gray-200 mb-6">
                    <h3 className="text-xs font-black text-gray-500 uppercase px-2 pt-2">Grafo Mapper — {mapper.lens_description}</h3>
                    {mapper.nodes && mapper.nodes.length > 0 ? (
                        <Plot data={plotData} layout={plotLayout} config={{ responsive: true, displayModeBar: false }} className="w-full" />
                    ) : (
                        <p className="text-sm text-gray-400 italic p-4">Grafo Mapper vazio (amostra pequena demais para os parâmetros escolhidos).</p>
                    )}
                </div>

                <p className="text-xs text-gray-400 italic">{result.caveat}</p>
            </div>
        </div>
    );
}
