import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiDownload } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

const OUTCOME_LABELS = {
    outcome_cure: 'Cura',
    outcome_abandonment: 'Abandono',
    outcome_death_by_disease: 'Óbito pela doença',
    outcome_death_by_other_cause: 'Óbito por outra causa',
    outcome_transfer: 'Transferência',
};

const COLUMN_LABELS = {
    age_years: 'Idade',
    sex_female: 'Sexo (F=1)',
    hiv_positive: 'HIV+',
    homeless: 'Situação de rua',
    n_comorbidities: 'Comorbidades',
    pulmonary_form: 'Forma pulmonar',
    time_to_closure_days: 'Dias até encerramento',
    outcome_cure: 'Cura',
    outcome_abandonment: 'Abandono',
    outcome_death_by_disease: 'Óbito (doença)',
    outcome_death_by_other_cause: 'Óbito (outra causa)',
    outcome_transfer: 'Transferência',
};

function fmtNum(v, digits = 0) {
    return v === null || v === undefined ? '—' : Number(v).toFixed(digits);
}

export default function PopulationNotificacaoViewerPage() {
    usePageTitle('Resultado - Caso de Notificação (PopulationSpace)');

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
                <Link to="/pipelines/population-notificacao" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const loaderReport = result.loader_report || {};
    const outcomeDist = result.outcome_distribution || {};
    const sampleCases = result.sample_cases || [];
    const fileId = task.output_file_id;

    const columns = [];
    for (const c of sampleCases) {
        for (const k of Object.keys(c.values || {})) {
            if (!columns.includes(k)) columns.push(k);
        }
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-notificacao" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Caso de Notificação
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Caso de Notificação ({result.disease_code})</h1>
                <p className="text-sm text-gray-500 mb-8">{loaderReport.n_cases_loaded ?? 0} caso(s) carregado(s), {loaderReport.n_with_outcome ?? 0} com desfecho reconhecido.</p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Cada notificação (não paciente, não estabelecimento) é uma unidade de análise, do perfil na
                        entrada até o desfecho no encerramento. Se o desfecho vier zerado em todas as categorias,
                        é porque o campo de origem (SITUA_ENCE para TB, EVOLUCAO para os demais agravos) não
                        estava preenchido naquele caso, ou o agravo consultado não tem esse campo populado na base
                        de origem — ausência estrutural, nunca um valor inventado.
                    </InfoCard>
                    {fileId && (
                        <a
                            href={`/api/files/${fileId}/`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors"
                        >
                            <FiDownload className="w-4 h-4" />
                            Ver CSV completo (amostra)
                        </a>
                    )}
                </div>

                <div className="grid grid-cols-3 gap-4 mb-6">
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-gray-200">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Casos carregados</div>
                        <div className="text-xl font-black text-gray-800">{loaderReport.n_cases_loaded ?? 0}</div>
                    </div>
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-blue-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Com desfecho</div>
                        <div className="text-xl font-black text-blue-700">{loaderReport.n_with_outcome ?? 0}</div>
                    </div>
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-emerald-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Dias até encerramento (média)</div>
                        <div className="text-xl font-black text-emerald-700">{fmtNum(result.avg_time_to_closure_days, 1)}</div>
                    </div>
                </div>

                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5 mb-6">
                    <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-3">Distribuição de desfecho</h3>
                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                        {Object.entries(OUTCOME_LABELS).map(([key, label]) => (
                            <div key={key} className="text-center">
                                <div className="text-lg font-black text-gray-800">{outcomeDist[key] ?? 0}</div>
                                <div className="text-[11px] text-gray-500 uppercase font-bold">{label}</div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-x-auto mb-4">
                    <table className="min-w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Caso</th>
                                {columns.map(c => (
                                    <th key={c} className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs whitespace-nowrap">
                                        {COLUMN_LABELS[c] || c}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {sampleCases.map(c => (
                                <tr key={c.case_id} className="border-b border-gray-100 last:border-0">
                                    <td className="px-4 py-3 font-mono text-xs">{c.case_id}</td>
                                    {columns.map(col => (
                                        <td key={col} className="px-4 py-3 text-right">
                                            {fmtNum(c.values?.[col], col === 'time_to_closure_days' ? 0 : 1)}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <p className="text-xs text-gray-400 italic">
                    Mostrando amostra de {sampleCases.length} caso(s) — a distribuição de desfecho acima considera
                    todos os {loaderReport.n_cases_loaded ?? 0} casos carregados, não só a amostra da tabela.
                </p>
            </div>
        </div>
    );
}
