import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiDownload } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getPopulationSpaceTask } from '../../services/populationSpaceService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

const COLUMN_LABELS = {
    family_size: 'Tamanho',
    n_spouses: 'Cônjuges',
    n_child_dependents: 'Filhos dependentes',
    n_other_relative_dependents: 'Outros parentes dependentes',
    n_non_relative_dependents: 'Não-parentes dependentes',
};

function fmtNum(v, digits = 0) {
    return v === null || v === undefined ? '—' : Number(v).toFixed(digits);
}

export default function PopulationFamiliaViewerPage() {
    usePageTitle('Resultado - Família (PopulationSpace)');

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
                <Link to="/pipelines/population-familia" className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900">
                    &larr; Voltar
                </Link>
            </div>
        );
    }

    const result = task.results_summary || {};
    const loaderReport = result.loader_report || {};
    const families = result.families || [];
    const fileId = task.output_file_id;

    const columns = [];
    for (const f of families) {
        for (const k of Object.keys(f.values || {})) {
            if (!columns.includes(k)) columns.push(k);
        }
    }

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <Link to="/pipelines/population-familia" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6">
                    &larr; Voltar para Família
                </Link>

                <h1 className="text-2xl font-bold text-gray-900 mb-2">Resultado — Família</h1>
                <p className="text-sm text-gray-500 mb-8">
                    {loaderReport.n_families_found ?? families.length} de {loaderReport.n_families_requested ?? families.length} família(s) solicitada(s) encontrada(s).
                </p>

                <div className="space-y-4 mb-8">
                    <InfoCard title="Como interpretar">
                        Cada linha é UMA FAMÍLIA do CadÚnico (não um paciente, não um domicílio inteiro), consultada
                        em tempo real contra a BPHO ({loaderReport.sparql_url || 'SPARQL'}). Só composição
                        estrutural, por papel dos membros, é modelada aqui — o dado socioeconômico bruto (renda,
                        moradia) não está disponível neste ambiente. Amostra não é aleatória de verdade (ordem
                        depende do plano de consulta do triplestore), serve pra demonstração, não pra inferência
                        estatística sobre a população inteira.
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
                                <th className="px-4 py-3 text-left font-bold text-gray-500 uppercase text-xs">Família</th>
                                {columns.map(c => (
                                    <th key={c} className="px-4 py-3 text-right font-bold text-gray-500 uppercase text-xs whitespace-nowrap">
                                        {COLUMN_LABELS[c] || c}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {families.map(f => (
                                <tr key={f.family_id} className="border-b border-gray-100 last:border-0">
                                    <td className="px-4 py-3 font-mono text-xs">{f.family_id}</td>
                                    {columns.map(c => (
                                        <td key={c} className="px-4 py-3 text-right font-bold">
                                            {fmtNum(f.values?.[c])}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <p className="text-xs text-gray-400 italic">
                    Família não encontrada na BPHO (ID inexistente ou fora do escopo carregado) simplesmente não
                    aparece na tabela — compare o total de linhas com "encontrada(s)" acima.
                </p>
            </div>
        </div>
    );
}
