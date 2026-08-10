import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiDownload } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

export default function PopulationSurvivalViewerPage() {
    usePageTitle('Resultado - Sobrevida (PopulationSpace)');

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
                <Link to="/pipelines/population-survival" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const facilities = result.facilities || [];
    const km = result.kaplan_meier;
    const cox = result.cox;
    const eventFeature = result.event_feature;
    const fileId = task.output_file_id;

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-survival" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Sobrevida (Fenótipo)
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Sobrevida (Kaplan-Meier + Cox)</h1>
                <p className="text-sm text-gray-500 mb-8">
                    {facilities.length} estabelecimentos, K={result.k ?? '—'}, evento: {eventFeature} &gt; {result.event_threshold?.toFixed(2)}.
                </p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Estratifica estabelecimentos por fenótipo de baseline e mede o tempo (em competências,
                        não dias de calendário) até a composição demográfica dos internados cruzar o limiar.
                        Utilização/força de trabalho são cumulativas na BPHO — o evento é sempre demográfico.
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
                    <h3 className="text-xs font-black text-gray-500 uppercase mb-3">Kaplan-Meier por fenótipo</h3>
                    {km ? (
                        <>
                            <p className="text-sm mb-3">
                                Log-rank p={km.logrank_p.toFixed(3)}
                                {km.logrank_p < 0.05 ? ' — diferença estatisticamente significativa entre grupos.' : ' — sem diferença significativa entre grupos.'}
                            </p>
                            <div className="overflow-x-auto">
                                <table className="min-w-full text-sm">
                                    <thead className="bg-gray-50 border-b border-gray-200">
                                        <tr>
                                            <th className="px-3 py-2 text-left font-bold text-gray-500 uppercase text-xs">Fenótipo</th>
                                            <th className="px-3 py-2 text-right font-bold text-gray-500 uppercase text-xs">N</th>
                                            <th className="px-3 py-2 text-right font-bold text-gray-500 uppercase text-xs">Sobrevida mediana (competências)</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {Object.keys(km.n_por_grupo).map(grupo => (
                                            <tr key={grupo} className="border-b border-gray-100 last:border-0">
                                                <td className="px-3 py-2 font-mono">{grupo}</td>
                                                <td className="px-3 py-2 text-right">{km.n_por_grupo[grupo]}</td>
                                                <td className="px-3 py-2 text-right font-bold">
                                                    {km.median_survival[grupo] !== null ? km.median_survival[grupo].toFixed(1) : 'não atingida'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    ) : (
                        <p className="text-sm text-gray-400 italic">Não computável (menos de 2 grupos de fenótipo distintos entre os estabelecimentos incluídos).</p>
                    )}
                </div>

                <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200 mb-6">
                    <h3 className="text-xs font-black text-gray-500 uppercase mb-3">Cox — hazard ratio por covariável (baseline)</h3>
                    {cox ? (
                        <>
                            <p className="text-sm mb-3">
                                Índice de concordância: {cox.concordance_index.toFixed(3)} · {cox.n_used} estabelecimento(s) usados
                                {cox.n_excluded_from_cox > 0 ? ` (${cox.n_excluded_from_cox} excluído(s) por covariável ausente)` : ''}.
                            </p>
                            <div className="overflow-x-auto">
                                <table className="min-w-full text-sm">
                                    <thead className="bg-gray-50 border-b border-gray-200">
                                        <tr>
                                            <th className="px-3 py-2 text-left font-bold text-gray-500 uppercase text-xs">Covariável</th>
                                            <th className="px-3 py-2 text-right font-bold text-gray-500 uppercase text-xs">Hazard ratio</th>
                                            <th className="px-3 py-2 text-right font-bold text-gray-500 uppercase text-xs">p-valor</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {Object.keys(cox.hazard_ratios).map(cov => (
                                            <tr key={cov} className="border-b border-gray-100 last:border-0">
                                                <td className="px-3 py-2 font-mono text-xs">{cov}</td>
                                                <td className="px-3 py-2 text-right font-bold">{cox.hazard_ratios[cov].toFixed(3)}</td>
                                                <td className="px-3 py-2 text-right">{cox.p_values[cov].toFixed(3)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    ) : (
                        <p className="text-sm text-gray-400 italic">{result.cox_error || 'Não computável.'}</p>
                    )}
                </div>

                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-x-auto mb-4">
                    <table className="min-w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Estabelecimento</th>
                                <th className="px-4 py-3 text-center font-bold text-gray-500 uppercase text-xs">Fenótipo</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">Duração</th>
                                <th className="px-4 py-3 text-center font-bold text-gray-500 uppercase text-xs">Evento?</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">{eventFeature} (baseline → final)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {facilities.map(f => (
                                <tr key={f.facility_uri} className={`border-b border-gray-100 last:border-0 ${f.event ? 'bg-red-50' : ''}`}>
                                    <td className="px-4 py-3 font-mono text-xs">{f.facility_uri}</td>
                                    <td className="px-4 py-3 text-center">
                                        <span className="px-2 py-0.5 rounded-full text-xs font-bold text-white bg-indigo-500">{f.phenotype ?? '—'}</span>
                                    </td>
                                    <td className="px-4 py-3 text-right">{f.duration}</td>
                                    <td className="px-4 py-3 text-center">
                                        {f.event ? (
                                            <span className="px-2 py-0.5 rounded-full text-xs font-bold text-white bg-red-500">SIM</span>
                                        ) : (
                                            <span className="px-2 py-0.5 rounded-full text-xs font-bold text-gray-400 bg-gray-100">censurado</span>
                                        )}
                                    </td>
                                    <td className="px-4 py-3 text-right">
                                        {f[`${eventFeature}_baseline`] !== null && f[`${eventFeature}_baseline`] !== undefined ? f[`${eventFeature}_baseline`].toFixed(1) : '—'}
                                        {' → '}
                                        {f[`${eventFeature}_final`] !== null && f[`${eventFeature}_final`] !== undefined ? f[`${eventFeature}_final`].toFixed(1) : '—'}
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
