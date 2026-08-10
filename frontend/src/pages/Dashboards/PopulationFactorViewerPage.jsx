import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiDownload } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

export default function PopulationFactorViewerPage() {
    usePageTitle('Resultado - Fatores Latentes (PopulationSpace)');

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
                <Link to="/pipelines/population-factor" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const loadings = result.loadings || [];
    const facilities = result.facilities || [];
    const factorNames = loadings.map(l => `factor_${l.factor}`);
    const fileId = task.output_file_id;

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-factor" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Fatores Latentes
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Fatores Latentes (Análise Fatorial)</h1>
                <p className="text-sm text-gray-500 mb-8">
                    {result.n_facilities ?? 0} estabelecimentos, {result.n_factors} fator(es).
                </p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Cada fator é um eixo estatístico de variação COMPARTILHADA entre as 12 Features de
                        entrada — as barras mostram quais Features mais "carregam" nesse eixo (positivo ou
                        negativo). O que o fator "significa" na prática é uma hipótese exploratória, nunca um
                        construto validado só porque o método é rigoroso.
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

                {loadings.map(l => {
                    const maxAbs = Math.max(...l.top_features.map(f => Math.abs(f.loading)), 1e-9);
                    return (
                        <div key={l.factor} className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200 mb-6">
                            <h3 className="text-xs font-black text-gray-500 uppercase mb-3">Fator {l.factor} — cargas por Feature</h3>
                            <div className="space-y-1.5">
                                {l.top_features.map(f => {
                                    const pct = Math.min(100, (Math.abs(f.loading) / maxAbs) * 100);
                                    const positive = f.loading >= 0;
                                    return (
                                        <div key={f.feature} className="flex items-center gap-2">
                                            <span className="text-xs font-mono text-gray-600 w-56 truncate">{f.feature}</span>
                                            <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                                                <div
                                                    className={`h-2 rounded-full ${positive ? 'bg-blue-600' : 'bg-rose-500'}`}
                                                    style={{ width: `${pct}%` }}
                                                />
                                            </div>
                                            <span className={`text-xs font-bold w-16 text-right ${positive ? 'text-blue-700' : 'text-rose-700'}`}>
                                                {f.loading >= 0 ? '+' : ''}{f.loading.toFixed(3)}
                                            </span>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    );
                })}

                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-x-auto mb-4">
                    <table className="min-w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Estabelecimento</th>
                                {factorNames.map(fn => (
                                    <th key={fn} className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">{fn}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {facilities.map(f => (
                                <tr key={f.facility_uri} className="border-b border-gray-100 last:border-0">
                                    <td className="px-4 py-3 font-mono text-xs">{f.facility_uri}</td>
                                    {factorNames.map(fn => (
                                        <td key={fn} className="px-4 py-3 text-right font-bold">
                                            {f.factor_scores[fn] !== undefined ? f.factor_scores[fn].toFixed(3) : '—'}
                                        </td>
                                    ))}
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
