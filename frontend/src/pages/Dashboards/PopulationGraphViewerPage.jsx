import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { FiDownload } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

const COMMUNITY_COLORS = ['#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed', '#0891b2', '#db2777', '#65a30d'];

function buildEdgeTrace(nodesById, edges) {
    const x = [];
    const y = [];
    for (const e of edges) {
        const a = nodesById[e.source];
        const b = nodesById[e.target];
        if (!a || !b) continue;
        x.push(a.x, b.x, null);
        y.push(a.y, b.y, null);
    }
    return {
        x, y, type: 'scatter', mode: 'lines',
        line: { width: 1, color: 'rgba(148, 163, 184, 0.5)' },
        hoverinfo: 'none', showlegend: false,
    };
}

function buildNodeTraces(nodes) {
    const byCommunity = {};
    for (const n of nodes) {
        (byCommunity[n.community] ??= []).push(n);
    }
    return Object.keys(byCommunity).sort((a, b) => a - b).map(community => {
        const group = byCommunity[community];
        return {
            x: group.map(n => n.x),
            y: group.map(n => n.y),
            type: 'scatter', mode: 'markers',
            name: `Comunidade ${community}`,
            marker: {
                size: group.map(n => 10 + n.degree * 2.5),
                color: COMMUNITY_COLORS[community % COMMUNITY_COLORS.length],
                line: { width: 1, color: '#fff' },
            },
            text: group.map(n => `${n.facility_uri}<br>fenótipo: ${n.phenotype ?? '—'}<br>grau: ${n.degree}`),
            hoverinfo: 'text',
        };
    });
}

export default function PopulationGraphViewerPage() {
    usePageTitle('Resultado - Grafo de Similaridade (PopulationSpace)');

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
                <Link to="/pipelines/population-graph" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const nodes = result.nodes || [];
    const edges = result.edges || [];
    const nodesById = Object.fromEntries(nodes.map(n => [n.facility_uri, n]));
    const fileId = task.output_file_id;

    const plotData = [buildEdgeTrace(nodesById, edges), ...buildNodeTraces(nodes)];
    const plotLayout = {
        xaxis: { visible: false, zeroline: false },
        yaxis: { visible: false, zeroline: false },
        margin: { t: 10, b: 10, l: 10, r: 10 },
        height: 520,
        hovermode: 'closest',
        legend: { orientation: 'h', y: -0.05 },
        plot_bgcolor: 'white',
    };

    const divergent = nodes.filter(n => {
        const sameCommunityPhenotypes = nodes.filter(o => o.community === n.community).map(o => o.phenotype);
        const majority = sameCommunityPhenotypes.sort((a, b) =>
            sameCommunityPhenotypes.filter(v => v === a).length - sameCommunityPhenotypes.filter(v => v === b).length
        ).pop();
        return n.phenotype !== majority;
    });

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-graph" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Grafo de Similaridade
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Grafo de Similaridade</h1>
                <p className="text-sm text-gray-500 mb-8">
                    {result.n_facilities ?? 0} estabelecimentos, geometria={result.geometry}, K={result.k} vizinhos.
                </p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Cada nó é um estabelecimento; arestas ligam vizinhos mais próximos. Cores = comunidades
                        detectadas pela TOPOLOGIA do grafo (Louvain); o rótulo no hover mostra o fenótipo
                        (KMeans, calculado direto no espaço de representação) — quando um nó tem fenótipo
                        diferente da maioria da sua comunidade, é um sinal de divergência entre as duas visões.
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
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-indigo-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Comunidades</div>
                        <div className="text-xl font-black text-indigo-700">{result.n_communities}</div>
                    </div>
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-emerald-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Modularidade</div>
                        <div className="text-xl font-black text-emerald-700">{result.modularity?.toFixed(3)}</div>
                    </div>
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-amber-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Nós ÷ fenótipo divergente</div>
                        <div className="text-xl font-black text-amber-700">{divergent.length}</div>
                    </div>
                </div>

                <div className="bg-white p-2 rounded-2xl shadow-sm border border-gray-200 mb-6">
                    <Plot data={plotData} layout={plotLayout} config={{ responsive: true, displayModeBar: false }} className="w-full" />
                </div>

                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-x-auto mb-4">
                    <table className="min-w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Estabelecimento</th>
                                <th className="px-4 py-3 text-center font-bold text-gray-500 uppercase text-xs">Comunidade</th>
                                <th className="px-4 py-3 text-center font-bold text-gray-500 uppercase text-xs">Fenótipo</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">Grau</th>
                            </tr>
                        </thead>
                        <tbody>
                            {nodes.map(n => {
                                const isDivergent = divergent.some(d => d.facility_uri === n.facility_uri);
                                return (
                                    <tr key={n.facility_uri} className={`border-b border-gray-100 last:border-0 ${isDivergent ? 'bg-amber-50' : ''}`}>
                                        <td className="px-4 py-3 font-mono text-xs">{n.facility_uri}</td>
                                        <td className="px-4 py-3 text-center">
                                            <span
                                                className="px-2 py-0.5 rounded-full text-xs font-bold text-white"
                                                style={{ backgroundColor: COMMUNITY_COLORS[n.community % COMMUNITY_COLORS.length] }}
                                            >
                                                {n.community}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-center">
                                            <span className="px-2 py-0.5 rounded-full text-xs font-bold text-white bg-gray-500">{n.phenotype ?? '—'}</span>
                                            {isDivergent && <span className="ml-1 text-amber-600" title="Diverge da maioria da comunidade">⚠</span>}
                                        </td>
                                        <td className="px-4 py-3 text-right">{n.degree}</td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>

                <p className="text-xs text-gray-400 italic">{result.caveat}</p>
            </div>
        </div>
    );
}
