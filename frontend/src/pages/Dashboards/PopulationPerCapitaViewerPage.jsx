import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiDownload } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

function fmtNum(v, digits = 1) {
    return v === null || v === undefined ? '—' : v.toFixed(digits);
}

export default function PopulationPerCapitaViewerPage() {
    usePageTitle('Resultado - Per Capita (PopulationSpace)');

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
                <Link to="/pipelines/population-per-capita" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const facilities = result.facilities || [];
    const fileId = task.output_file_id;

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-per-capita" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Per Capita
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Per Capita (Taxa Populacional)</h1>
                <p className="text-sm text-gray-500 mb-8">{result.n_facilities ?? 0} estabelecimentos analisados.</p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Taxa = (contagem do estabelecimento ÷ população do município) × 1.000 — mesma escala
                        usada pelos indicadores por município do LabSUS. Município vem do cadastro de
                        vínculos profissionais (CNES) da própria competência; sem vínculo carregado naquele
                        arquivo, ou sem UF informada, a linha mostra "—" em vez de um valor inventado.
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
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-blue-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Município resolvido</div>
                        <div className="text-xl font-black text-blue-700">{result.n_municipio_resolved ?? 0}</div>
                    </div>
                    <div className="p-4 bg-white rounded-2xl shadow-sm border border-emerald-100">
                        <div className="text-xs text-gray-500 uppercase font-bold mb-1">Taxa calculada</div>
                        <div className="text-xl font-black text-emerald-700">{result.n_populacao_resolved ?? 0}</div>
                    </div>
                </div>

                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-x-auto mb-4">
                    <table className="min-w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Estabelecimento</th>
                                <th className="px-4 py-3 text-center font-bold text-gray-500 uppercase text-xs">Município (IBGE-6)</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">População</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">Internações</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">Taxa internação/mil</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">Vínculos</th>
                                <th className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs">Taxa vínculos/mil</th>
                            </tr>
                        </thead>
                        <tbody>
                            {facilities.map(f => (
                                <tr key={f.facility_uri} className={`border-b border-gray-100 last:border-0 ${f.taxa_internacao_por_mil === null ? 'bg-gray-50/60' : ''}`}>
                                    <td className="px-4 py-3 font-mono text-xs">{f.facility_uri}</td>
                                    <td className="px-4 py-3 text-center font-mono text-xs">{f.municipio_cod_ibge_6 ?? '—'}</td>
                                    <td className="px-4 py-3 text-right">{f.populacao !== null ? f.populacao.toLocaleString('pt-BR') : '—'}</td>
                                    <td className="px-4 py-3 text-right">{f.n_hospitalizations ?? '—'}</td>
                                    <td className="px-4 py-3 text-right font-bold">{fmtNum(f.taxa_internacao_por_mil, 3)}</td>
                                    <td className="px-4 py-3 text-right">{f.n_affiliations ?? '—'}</td>
                                    <td className="px-4 py-3 text-right font-bold">{fmtNum(f.taxa_vinculos_por_mil, 3)}</td>
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
