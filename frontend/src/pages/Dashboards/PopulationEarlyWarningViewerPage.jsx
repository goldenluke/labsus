import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { FiDownload, FiChevronDown, FiChevronUp, FiAlertTriangle, FiCheckCircle, FiMinusCircle } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

const INDICATOR_LABELS = { variance: 'Variância', autocorrelation: 'Autocorrelação (lag-1)', skewness: 'Assimetria' };

function StatusBadge({ facility }) {
    if (!facility.sufficient_data) {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold text-white bg-gray-400">
                <FiMinusCircle size={12} /> dado insuficiente
            </span>
        );
    }
    if (facility.warning) {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold text-white bg-red-600">
                <FiAlertTriangle size={12} /> alerta
            </span>
        );
    }
    return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold text-white bg-emerald-600">
            <FiCheckCircle size={12} /> estável
        </span>
    );
}

function IndicatorRow({ name, ind }) {
    if (ind.tau === null || ind.tau === undefined) {
        return (
            <div className="flex items-center justify-between text-xs text-gray-400 py-1">
                <span>{INDICATOR_LABELS[name] || name}</span>
                <span>indisponível</span>
            </div>
        );
    }
    const flag = ind.is_significant ? (ind.is_rising ? '↑ significativo' : '↓ significativo') : (ind.is_rising ? '↑' : '↓');
    const color = ind.is_rising && ind.is_significant ? 'text-red-600' : 'text-gray-600';
    return (
        <div className="flex items-center justify-between text-xs py-1">
            <span className="text-gray-500">{INDICATOR_LABELS[name] || name}</span>
            <span className={`font-mono font-bold ${color}`}>
                τ={ind.tau.toFixed(3)} (p={ind.p_value !== null ? ind.p_value.toFixed(3) : 'n/a'}) {flag}
            </span>
        </div>
    );
}

function SeriesPlot({ series }) {
    const traces = [
        {
            x: series.times_days, y: series.variance, type: 'scatter', mode: 'lines+markers',
            name: 'Variância', yaxis: 'y', line: { color: '#2563eb' },
        },
        {
            x: series.times_days, y: series.autocorrelation, type: 'scatter', mode: 'lines+markers',
            name: 'Autocorrelação', yaxis: 'y2', line: { color: '#d97706' },
        },
        {
            x: series.times_days, y: series.skewness, type: 'scatter', mode: 'lines+markers',
            name: 'Assimetria', yaxis: 'y2', line: { color: '#7c3aed' },
        },
    ];
    const layout = {
        height: 280,
        margin: { t: 20, b: 40, l: 50, r: 50 },
        xaxis: { title: 'dias desde a 1ª competência' },
        yaxis: { title: 'variância', titlefont: { color: '#2563eb' }, tickfont: { color: '#2563eb' } },
        yaxis2: { title: 'autocorr. / assimetria', overlaying: 'y', side: 'right', titlefont: { color: '#7c3aed' }, tickfont: { color: '#7c3aed' } },
        legend: { orientation: 'h', y: -0.25 },
        plot_bgcolor: 'white',
    };
    return <Plot data={traces} layout={layout} config={{ responsive: true, displayModeBar: false }} className="w-full" />;
}

export default function PopulationEarlyWarningViewerPage() {
    usePageTitle('Resultado - Alerta Precoce (PopulationSpace)');

    const location = useLocation();
    const taskId = useMemo(() => new URLSearchParams(location.search).get('taskId'), [location.search]);

    const [task, setTask] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expanded, setExpanded] = useState({});

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
                <Link to="/pipelines/population-early-warning" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const facilities = result.facilities || [];
    const fileId = task.output_file_id;

    const toggle = (uri) => setExpanded(prev => ({ ...prev, [uri]: !prev[uri] }));

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-early-warning" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Alerta Precoce
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Alerta Precoce</h1>
                <p className="text-sm text-gray-500 mb-8">
                    min_points={result.min_points}, janela={result.window_size} pontos, detrend={result.detrend_method},
                    {' '}{result.n_surrogates} substitutos AR(1).
                </p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Cada estabelecimento é analisado sobre sua própria trajetória (distância ao ponto de
                        partida, competência a competência). "Alerta" exige que pelo menos metade dos
                        indicadores disponíveis (variância, autocorrelação, assimetria) mostrem tendência
                        crescente e estatisticamente significativa (α=0.10, testado por substitutos AR(1)) —
                        não é um diagnóstico, é um sinal precoce de perda de resiliência.
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
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-gray-200">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Estabelecimentos</div>
                        <div className="text-xl font-black text-gray-800">{result.n_facilities ?? 0}</div>
                    </div>
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-red-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Com alerta</div>
                        <div className="text-xl font-black text-red-700">{result.n_warnings ?? 0}</div>
                    </div>
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-gray-200">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Dado insuficiente</div>
                        <div className="text-xl font-black text-gray-500">{result.n_insufficient_data ?? 0}</div>
                    </div>
                </div>

                <div className="space-y-3 mb-6">
                    {facilities.map(f => (
                        <div key={f.facility_uri} className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
                            <button
                                onClick={() => f.sufficient_data && toggle(f.facility_uri)}
                                className="w-full flex items-center justify-between px-4 py-3 text-left"
                            >
                                <div className="flex items-center gap-3">
                                    <span className="font-mono text-xs text-gray-700">{f.facility_uri}</span>
                                    <StatusBadge facility={f} />
                                    <span className="text-xs text-gray-400">{f.n_points} competências</span>
                                </div>
                                {f.sufficient_data && (expanded[f.facility_uri] ? <FiChevronUp /> : <FiChevronDown />)}
                            </button>

                            {f.sufficient_data && expanded[f.facility_uri] && (
                                <div className="px-4 pb-4 border-t border-gray-100 pt-3">
                                    <div className="grid grid-cols-3 gap-4 mb-3">
                                        {Object.entries(f.indicators).map(([name, ind]) => (
                                            <IndicatorRow key={name} name={name} ind={ind} />
                                        ))}
                                    </div>
                                    <SeriesPlot series={f.series} />
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                <p className="text-xs text-gray-400 italic">{result.caveat}</p>
            </div>
        </div>
    );
}
