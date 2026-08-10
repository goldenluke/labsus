import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { FiDownload } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

const PHENOTYPE_COLORS = ['#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed', '#0891b2'];

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

function phenotypeColor(name, labelNames) {
    const idx = labelNames.indexOf(name);
    return PHENOTYPE_COLORS[idx >= 0 ? idx % PHENOTYPE_COLORS.length : 0];
}

function buildNodeTraces(nodes, labelNames) {
    const labeled = nodes.filter(n => n.is_labeled);
    const testCorrect = nodes.filter(n => !n.is_labeled && n.correct);
    const testWrong = nodes.filter(n => !n.is_labeled && !n.correct);

    const trace = (group, name, symbol, lineColor) => ({
        x: group.map(n => n.x),
        y: group.map(n => n.y),
        type: 'scatter', mode: 'markers',
        name,
        marker: {
            size: 14,
            symbol,
            color: group.map(n => phenotypeColor(n.true_phenotype, labelNames)),
            line: { width: lineColor ? 3 : 1, color: lineColor || '#fff' },
        },
        text: group.map(n => `${n.facility_uri}<br>real: ${n.true_phenotype ?? '—'}<br>previsto: ${n.predicted_phenotype ?? '—'}`),
        hoverinfo: 'text',
    });

    return [
        trace(labeled, 'Rotulado (treino)', 'circle'),
        trace(testCorrect, 'Teste — acerto', 'circle-open'),
        trace(testWrong, 'Teste — erro', 'circle-open', '#dc2626'),
    ];
}

export default function PopulationGnnViewerPage() {
    usePageTitle('Resultado - GNN (PopulationSpace)');

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
                <Link to="/pipelines/population-gnn" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const nodes = result.nodes || [];
    const edges = result.edges || [];
    const labelNames = result.label_names || [];
    const nodesById = Object.fromEntries(nodes.map(n => [n.facility_uri, n]));
    const fileId = task.output_file_id;

    const plotData = [buildEdgeTrace(nodesById, edges), ...buildNodeTraces(nodes, labelNames)];
    const plotLayout = {
        xaxis: { visible: false, zeroline: false },
        yaxis: { visible: false, zeroline: false },
        margin: { t: 10, b: 10, l: 10, r: 10 },
        height: 480,
        hovermode: 'closest',
        legend: { orientation: 'h', y: -0.05 },
        plot_bgcolor: 'white',
    };

    const lossHistory = result.loss_history || [];
    const lossLayout = {
        height: 220,
        margin: { t: 20, b: 40, l: 50, r: 20 },
        xaxis: { title: 'época' },
        yaxis: { title: 'perda' },
        plot_bgcolor: 'white',
    };

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-gnn" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para GNN
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — GNN (Classificação de Nós)</h1>
                <p className="text-sm text-gray-500 mb-8">
                    {result.n_facilities ?? 0} estabelecimentos, geometria={result.geometry}, K={result.k} vizinhos,
                    {' '}{result.phenotype_k} fenótipos, {result.epochs} épocas.
                </p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Nós rotulados (círculo preenchido) entraram no treino; nós de teste (contorno) foram
                        avaliados às cegas — vermelho quando a GCN errou o fenótipo. Compare sempre
                        "acurácia de teste" contra o "baseline" (sempre prever a classe majoritária entre os
                        rotulados): só supera o baseline é evidência de que a estrutura do grafo carrega
                        informação real sobre o fenótipo.
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

                <div className="grid grid-cols-4 gap-4 mb-6">
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-emerald-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Acurácia de teste</div>
                        <div className="text-xl font-black text-emerald-700">{(result.test_accuracy * 100).toFixed(1)}%</div>
                    </div>
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-gray-200">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Baseline (classe majoritária)</div>
                        <div className="text-xl font-black text-gray-500">{(result.test_baseline_accuracy * 100).toFixed(1)}%</div>
                    </div>
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-gray-200">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Rotulados / Teste</div>
                        <div className="text-xl font-black text-gray-800">{result.n_labeled} / {result.n_test}</div>
                    </div>
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-indigo-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Acurácia de treino</div>
                        <div className="text-xl font-black text-indigo-700">{(result.train_accuracy * 100).toFixed(1)}%</div>
                    </div>
                </div>

                <div className="bg-white p-2 rounded-2xl shadow-sm border border-gray-200 mb-6">
                    <Plot data={plotData} layout={plotLayout} config={{ responsive: true, displayModeBar: false }} className="w-full" />
                </div>

                <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200 mb-6">
                    <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-2">Curva de perda (treino)</h3>
                    <Plot
                        data={[{ x: lossHistory.map((_, i) => i), y: lossHistory, type: 'scatter', mode: 'lines', line: { color: '#2563eb' } }]}
                        layout={lossLayout}
                        config={{ responsive: true, displayModeBar: false }}
                        className="w-full"
                    />
                </div>

                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-x-auto mb-4">
                    <table className="min-w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Estabelecimento</th>
                                <th className="px-4 py-3 text-center font-bold text-gray-500 uppercase text-xs">Grupo</th>
                                <th className="px-4 py-3 text-center font-bold text-gray-500 uppercase text-xs">Fenótipo real</th>
                                <th className="px-4 py-3 text-center font-bold text-gray-500 uppercase text-xs">Fenótipo previsto</th>
                                <th className="px-4 py-3 text-center font-bold text-gray-500 uppercase text-xs">Acerto</th>
                            </tr>
                        </thead>
                        <tbody>
                            {nodes.map(n => (
                                <tr key={n.facility_uri} className={`border-b border-gray-100 last:border-0 ${!n.is_labeled && !n.correct ? 'bg-red-50' : ''}`}>
                                    <td className="px-4 py-3 font-mono text-xs">{n.facility_uri}</td>
                                    <td className="px-4 py-3 text-center">
                                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold text-white ${n.is_labeled ? 'bg-blue-500' : 'bg-gray-400'}`}>
                                            {n.is_labeled ? 'treino' : 'teste'}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-center">{n.true_phenotype ?? '—'}</td>
                                    <td className="px-4 py-3 text-center">{n.predicted_phenotype ?? '—'}</td>
                                    <td className="px-4 py-3 text-center">
                                        {n.is_labeled ? '—' : (n.correct ? '✓' : '✗')}
                                    </td>
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
