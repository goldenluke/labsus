import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiDownload } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

const COLUMN_LABELS = {
    n_hospitalizations_municipio: 'Internações',
    hospitalizations_per_1000: 'Internações/mil',
    avg_length_of_stay_days_municipio: 'Permanência média (dias)',
    in_hospital_death_rate_pct: 'Óbito hospitalar (%)',
    deaths_per_1000: 'Mortalidade/mil',
    births_per_1000: 'Natalidade/mil',
};

function labelFor(key) {
    if (COLUMN_LABELS[key]) return COLUMN_LABELS[key];
    if (key.endsWith('_incidence_per_100k')) {
        return `Incidência ${key.replace('_incidence_per_100k', '').toUpperCase()}/100mil`;
    }
    return key;
}

function fmtNum(v, digits = 2) {
    return v === null || v === undefined ? '—' : Number(v).toFixed(digits);
}

export default function PopulationMunicipioViewerPage() {
    usePageTitle('Resultado - Município (PopulationSpace)');

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
                <Link to="/pipelines/population-municipio" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const municipios = result.municipios || [];
    const fileId = task.output_file_id;

    const columns = [];
    for (const m of municipios) {
        for (const k of Object.keys(m.values || {})) {
            if (!columns.includes(k)) columns.push(k);
        }
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-municipio" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Município
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Município</h1>
                <p className="text-sm text-gray-500 mb-8">{result.loader_report?.n_municipios ?? municipios.length} município(s) analisado(s).</p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Cada linha é um MUNICÍPIO (não um estabelecimento), cruzando SIH (internação, mensal),
                        SIM (óbito, anual) e SINASC (nascimento, anual) do mesmo território — mais SINAN
                        (incidência de agravo, anual), se informado no disparo. Coluna ausente ("—") é ausência
                        estrutural do dado de origem (arquivo não disponível, ou município não encontrado nele),
                        nunca um zero inventado.
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

                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-x-auto mb-4">
                    <table className="min-w-full text-sm">
                        <thead className="bg-gray-50 border-b border-gray-200">
                            <tr>
                                <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Município (IBGE-6)</th>
                                {columns.map(c => (
                                    <th key={c} className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs whitespace-nowrap">
                                        {labelFor(c)}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {municipios.map(m => (
                                <tr key={m.cod_ibge} className="border-b border-gray-100 last:border-0">
                                    <td className="px-4 py-3 font-mono text-xs">{m.cod_ibge}</td>
                                    {columns.map(c => (
                                        <td key={c} className="px-4 py-3 text-right font-bold">
                                            {fmtNum(m.values?.[c])}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <p className="text-xs text-gray-400 italic">
                    População (denominador dos indicadores "/mil"/"/100mil") vem da série de estimativa por
                    spline do IBGE já usada no pipeline de Indicadores. Anos ≥ 2025 são extrapolação
                    estatística, não censo oficial.
                </p>
            </div>
        </div>
    );
}
