import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiDownload, FiArrowRight } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

export default function PopulationInterveneViewerPage() {
    usePageTitle('Resultado - Intervenção (PopulationSpace)');

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
                <Link to="/pipelines/population-intervene" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const risk = result.risk;
    const cls = result.classify;
    const shiftsRaw = result.shifts_raw || {};
    const shiftsApplied = result.shifts_applied || {};
    const baselineValues = result.baseline_values || {};
    const fileId = task.output_file_id;

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-intervene" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Intervenção (Contrafactual)
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Simulação Contrafactual</h1>
                <p className="text-sm text-gray-500 mb-8 font-mono">{result.target_facility_uri}</p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Desloca Features do estabelecimento-alvo e mede o efeito no Score de Risco e na
                        probabilidade do Classificador, ambos treinados sobre os demais estabelecimentos
                        selecionados. Simulação sobre o espaço de representação, não um efeito causal validado.
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
                    <h3 className="text-xs font-black text-gray-500 uppercase mb-3">Shifts aplicados</h3>
                    <div className="overflow-x-auto">
                        <table className="min-w-full text-sm">
                            <thead className="bg-gray-50 border-b border-gray-200">
                                <tr>
                                    <th className="px-3 py-2 text-left font-bold text-gray-500 uppercase text-xs">Feature</th>
                                    <th className="px-3 py-2 text-right font-bold text-gray-500 uppercase text-xs">Delta bruto</th>
                                    <th className="px-3 py-2 text-right font-bold text-gray-500 uppercase text-xs">Delta em z-score (aplicado)</th>
                                    <th className="px-3 py-2 text-right font-bold text-gray-500 uppercase text-xs">Valor baseline</th>
                                </tr>
                            </thead>
                            <tbody>
                                {Object.keys(shiftsRaw).map(feat => (
                                    <tr key={feat} className="border-b border-gray-100 last:border-0">
                                        <td className="px-3 py-2 font-mono text-xs">{feat}</td>
                                        <td className="px-3 py-2 text-right font-bold">{shiftsRaw[feat] > 0 ? '+' : ''}{shiftsRaw[feat]}</td>
                                        <td className="px-3 py-2 text-right text-gray-500">{shiftsApplied[feat]?.toFixed(4)}</td>
                                        <td className="px-3 py-2 text-right">{baselineValues[feat] !== undefined ? baselineValues[feat].toFixed(2) : '—'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                    <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200">
                        <h3 className="text-xs font-black text-gray-500 uppercase mb-3">Score de Risco</h3>
                        <div className="flex items-center justify-center gap-3 text-2xl font-black">
                            <span className="text-gray-500">{risk.baseline_score.toFixed(3)}</span>
                            <FiArrowRight className="text-gray-300" />
                            <span className={risk.delta > 0 ? 'text-red-600' : risk.delta < 0 ? 'text-emerald-600' : 'text-gray-700'}>
                                {risk.counterfactual_score.toFixed(3)}
                            </span>
                        </div>
                        <p className={`text-center text-sm font-bold mt-2 ${risk.delta > 0 ? 'text-red-600' : risk.delta < 0 ? 'text-emerald-600' : 'text-gray-500'}`}>
                            Δ {risk.delta > 0 ? '+' : ''}{risk.delta.toFixed(3)}
                        </p>
                        <p className="text-xs text-gray-400 text-center mt-1">
                            Pesos: {Object.entries(risk.weights).map(([k, v]) => `${k}=${v}`).join(', ')}
                        </p>
                    </div>

                    <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200">
                        <h3 className="text-xs font-black text-gray-500 uppercase mb-3">Classificador — P({cls?.label_feature ?? '...'} alto)</h3>
                        {cls ? (
                            <>
                                <div className="flex items-center justify-center gap-3 text-2xl font-black">
                                    <span className="text-gray-500">{cls.baseline_probability_alto.toFixed(3)}</span>
                                    <FiArrowRight className="text-gray-300" />
                                    <span className={cls.counterfactual_probability_alto > cls.baseline_probability_alto ? 'text-red-600' : 'text-emerald-600'}>
                                        {cls.counterfactual_probability_alto.toFixed(3)}
                                    </span>
                                </div>
                                <p className={`text-center text-sm font-bold mt-2 ${cls.counterfactual_probability_alto > cls.baseline_probability_alto ? 'text-red-600' : 'text-emerald-600'}`}>
                                    Δ {(cls.counterfactual_probability_alto - cls.baseline_probability_alto) >= 0 ? '+' : ''}
                                    {(cls.counterfactual_probability_alto - cls.baseline_probability_alto).toFixed(3)}
                                </p>
                                <p className="text-xs text-gray-400 text-center mt-1">Limiar: {cls.threshold.toFixed(2)}</p>
                            </>
                        ) : (
                            <p className="text-sm text-gray-400 italic">{result.classify_error || 'Não computável.'}</p>
                        )}
                    </div>
                </div>

                <p className="text-xs text-gray-400 italic">{result.caveat}</p>
            </div>
        </div>
    );
}
