import { useState, useEffect, useMemo } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Plot from 'react-plotly.js';
import { FiDownload, FiHeart, FiAlertTriangle, FiCheckCircle } from 'react-icons/fi';
import usePageTitle from '../../hooks/usePageTitle';
import { getRiscoPerinatalTask } from '../../services/riscoPerinatalService';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';

const FEATURE_LABELS = {
  IDADEMAE: 'Idade da Mãe',
  ESCMAE2010: 'Escolaridade da Mãe',
  RACACORMAE: 'Raça/Cor da Mãe',
  QTDFILVIVO: 'Filhos Vivos',
  QTDFILMORT: 'Filhos Mortos',
  CONSPRENAT: 'Consultas Pré-Natal',
  MESPRENAT: 'Mês Início Pré-Natal',
  PARTO: 'Tipo de Parto',
  GRAVIDEZ: 'Tipo de Gravidez',
  ESTCIVMAE: 'Estado Civil da Mãe',
};

function getRiskColor(classification) {
  switch (classification) {
    case 'BAIXO':
      return 'text-green-600 bg-green-50 border-green-200';
    case 'MODERADO':
      return 'text-amber-600 bg-amber-50 border-amber-200';
    case 'ALTO':
      return 'text-red-600 bg-red-50 border-red-200';
    default:
      return 'text-gray-600 bg-gray-50 border-gray-200';
  }
}

function getRiskIcon(classification) {
  switch (classification) {
    case 'ALTO':
      return <FiAlertTriangle className="w-5 h-5" />;
    case 'MODERADO':
      return <FiHeart className="w-5 h-5" />;
    case 'BAIXO':
      return <FiCheckCircle className="w-5 h-5" />;
    default:
      return <FiHeart className="w-5 h-5" />; // eslint-disable-line no-unused-vars
  }
}

function formatPatientValue(value) {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'number') return value.toString();
  return String(value);
}

export default function RiscoPerinatalViewerPage() {
  usePageTitle('Resultado do Risco Perinatal');

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
        const data = await getRiscoPerinatalTask(taskId);
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

  const patientData = useMemo(() => {
    if (!task?.patient_data) return {};
    try {
      return typeof task.patient_data === 'string' ? JSON.parse(task.patient_data) : task.patient_data;
    } catch { return {}; }
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
          to="/pipelines/risco-perinatal"
          className="mt-4 inline-flex items-center text-sm text-gray-600 hover:text-gray-900"
        >
          &larr; Voltar
        </Link>
      </div>
    );
  }

  const riskScore = task.risk_score;
  const riskClassification = task.risk_classification;
  const fileId = task.output_file_id;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Link
          to="/pipelines/risco-perinatal"
          className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700 mb-6"
        >
          &larr; Voltar para Risco Perinatal
        </Link>

        <h1 className="text-2xl font-bold text-gray-900 mb-8">
          Resultado do Risco Perinatal
        </h1>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="space-y-6">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Dados da Paciente</h2>
              <dl className="space-y-3">
                {Object.entries(patientData).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <dt className="text-sm text-gray-500">
                      {FEATURE_LABELS[key] || key}
                    </dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {formatPatientValue(value)}
                    </dd>
                  </div>
                ))}
                {Object.keys(patientData).length === 0 && (
                  <p className="text-sm text-gray-400">Sem dados disponíveis.</p>
                )}
              </dl>
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Classificação de Risco</h2>
              <div className="text-center">
                <div className="text-4xl font-bold text-gray-900 mb-2">
                  {riskScore != null ? (riskScore * 100).toFixed(1) + '%' : '-'}
                </div>
                <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border text-sm font-semibold ${getRiskColor(riskClassification)}`}>
                  {getRiskIcon(riskClassification)}
                  {riskClassification || '-'}
                </div>
              </div>
            </div>

            {fileId && (
              <a
                href={`/api/pipelines/risco-perinatal/tasks/${taskId}/download/`}
                download
                className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors"
              >
                <FiDownload className="w-4 h-4" />
                Download CSV
              </a>
            )}
          </div>

          <div className="lg:col-span-2">
            <InfoCard title="Como interpretar o gráfico SHAP">
              O gráfico abaixo mostra como cada variável contribuiu para o risco calculado.
              Barras vermelhas aumentam o risco, barras azuis diminuem o risco.
              O valor no eixo X indica a magnitude do impacto de cada variável.
            </InfoCard>

            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mt-6">
              {shapData ? (
                <Plot
                  data={[
                    {
                      type: 'waterfall',
                      orientation: 'h',
                      y: shapData.feature_names.reverse(),
                      x: shapData.shap_values.reverse(),
                      connector: { line: { color: '#e5e7eb' } },
                      increasing: { marker: { color: '#ef4444' } },
                      decreasing: { marker: { color: '#3b82f6' } },
                      textposition: 'outside',
                      text: shapData.shap_values
                        .reverse()
                        .map((v) => (v > 0 ? `+${v.toFixed(3)}` : v.toFixed(3))),
                    },
                  ]}
                  layout={{
                    title: 'Explicação SHAP - Risco Perinatal',
                    xaxis: { title: 'Impacto no Risco' },
                    margin: { l: 200, r: 20, t: 50, b: 50 },
                    height: 500,
                  }}
                  config={{ displayModeBar: false }}
                  useResizeHandler
                  style={{ width: '100%' }}
                />
              ) : (
                <p className="text-sm text-gray-400 text-center py-10">
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
