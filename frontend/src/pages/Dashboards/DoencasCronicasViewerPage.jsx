import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { FiDownload, FiActivity, FiUsers, FiTarget } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getDoencasCronicasTask } from '../../services/doencasCronicasService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

export default function DoencasCronicasViewerPage() {
  usePageTitle('Resultado - Doenças Crônicas');

  const location = useLocation();
  const taskId = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get('taskId');
  }, [location.search]);

  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!taskId) {
      setError('ID da tarefa não fornecido.');
      setLoading(false);
      return;
    }

    async function fetchTask() {
      setLoading(true);
      setError(null);
      try {
        const data = await getDoencasCronicasTask(taskId);
        setTask(data);
      } catch (err) {
        setError(err.message || 'Erro ao carregar os resultados.');
      } finally {
        setLoading(false);
      }
    }

    fetchTask();
  }, [taskId]);

  const shapData = useMemo(() => {
    if (!task?.shap_data) return null;
    try {
      return typeof task.shap_data === 'string' ? JSON.parse(task.shap_data) : task.shap_data;
    } catch { return null; }
  }, [task]);

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
        <Link
          to="/pipelines/doencas-cronicas"
          className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900"
        >
          &larr; Voltar
        </Link>
      </div>
    );
  }

  const fileId = task.output_file_id;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Link
          to="/pipelines/doencas-cronicas"
          className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6"
        >
          &larr; Voltar para Doenças Crônicas
        </Link>

        <h1 className="text-2xl font-bold text-gray-900 mb-8">
          Resultado - Coorte de Doenças Crônicas
        </h1>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="space-y-6">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Parâmetros da Análise</h2>
              <dl className="space-y-3">
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">UF</dt>
                  <dd className="text-sm font-medium text-gray-900">{task.uf}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">CID-10</dt>
                  <dd className="text-sm font-medium text-gray-900">{task.cid_doenca}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">Ano de Referência</dt>
                  <dd className="text-sm font-medium text-gray-900">{task.ano_snapshot}</dd>
                </div>
              </dl>
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Resumo do Modelo</h2>
              <div className="grid grid-cols-1 gap-4">
                <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-xl border border-blue-100">
                  <FiUsers className="text-blue-600 w-6 h-6" />
                  <div>
                    <div className="text-2xl font-bold text-gray-900">{task.n_pacientes_coorte ?? '-'}</div>
                    <div className="text-xs text-gray-500">Pacientes na coorte</div>
                  </div>
                </div>
                <div className="flex items-center gap-3 p-3 bg-emerald-50 rounded-xl border border-emerald-100">
                  <FiTarget className="text-emerald-600 w-6 h-6" />
                  <div>
                    <div className="text-2xl font-bold text-gray-900">
                      {task.roc_auc != null ? task.roc_auc.toFixed(3) : 'N/A'}
                    </div>
                    <div className="text-xs text-gray-500">AUC (poder de discriminação)</div>
                  </div>
                </div>
              </div>
            </div>

            {fileId && (
              <a
                href={`/api/files/${fileId}/`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors"
              >
                <FiDownload className="w-4 h-4" />
                Ver arquivo da coorte pontuada
              </a>
            )}
          </div>

          <div className="lg:col-span-2">
            <InfoCard title="Como interpretar o gráfico">
              O gráfico abaixo mostra a importância média (SHAP) de cada variável na previsão de
              hospitalização em 6 meses, considerando toda a coorte pontuada — não é a explicação de
              um paciente individual, mas o padrão geral do modelo para este grupo.
            </InfoCard>

            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mt-6">
              {shapData?.feature_names?.length ? (
                <Plot
                  data={[
                    {
                      type: 'bar',
                      orientation: 'h',
                      y: [...shapData.feature_names].reverse(),
                      x: [...shapData.shap_values].reverse(),
                      marker: { color: '#3b82f6' },
                      text: [...shapData.shap_values].reverse().map((v) => v.toFixed(4)),
                      textposition: 'outside',
                    },
                  ]}
                  layout={{
                    title: 'Importância Média das Features (SHAP)',
                    xaxis: { title: 'Impacto médio no risco' },
                    margin: { l: 220, r: 20, t: 50, b: 50 },
                    height: 400,
                  }}
                  config={{ displayModeBar: false }}
                  useResizeHandler
                  style={{ width: '100%' }}
                />
              ) : (
                <p className="text-sm text-gray-400 text-center py-10 flex flex-col items-center gap-2">
                  <FiActivity className="w-6 h-6" />
                  Dados SHAP não disponíveis.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
