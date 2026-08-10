import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiHome, FiCheckCircle } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import { triggerFamilia } from '../../services/populationSpaceService';

const PipelinePopulationFamiliaPage = () => {
    usePageTitle('PopulationSpace: Família');
    const navigate = useNavigate();

    const [mode, setMode] = useState('sample'); // 'sample' | 'ids'
    const [sampleSize, setSampleSize] = useState(5);
    const [idsText, setIdsText] = useState('');
    const [taskId, setTaskId] = useState(null);
    const { isPending, isSuccess, isFailure, progress, message, error } = useCeleryTaskStatus(
        taskId, '/api/pipelines/population-space/tasks/'
    );

    const familyIds = idsText.split(/[\s,]+/).map(s => s.trim()).filter(Boolean);

    const run = async () => {
        setTaskId(null);
        try {
            const { task_id } = mode === 'ids'
                ? await triggerFamilia({ familyIds })
                : await triggerFamilia({ sampleSize: Number(sampleSize) });
            setTaskId(task_id);
        } catch (err) {
            alert(`Falha ao disparar análise de família: ${err.response?.data?.error || err.message}`);
        }
    };

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => navigate(`/dashboards/population-familia/viewer?taskId=${taskId}`), 1200);
        }
    }, [isSuccess, taskId, navigate]);

    const canRun = mode === 'ids' ? familyIds.length > 0 : Number(sampleSize) > 0;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Família</h1>
                <p className="text-gray-500 mt-2 text-lg">Composição estrutural via CadÚnico — PopulationSpace (BioSpace).</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Trata uma FAMÍLIA do CadÚnico (não um paciente, não um domicílio inteiro) como unidade de
                        análise: tamanho e composição por papel dos membros (cônjuge, filho dependente, outro
                        parente dependente, não-parente dependente), consultada em tempo real contra a BPHO. Só
                        composição estrutural — o dado socioeconômico bruto (renda, moradia) não está disponível
                        neste ambiente, por isso não aparece aqui; é um recorte deliberado, não um erro.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <FiHome className="text-blue-500" /> Famílias
                    </h2>

                    <div className="flex gap-2">
                        <button
                            onClick={() => setMode('sample')}
                            className={`flex-1 py-2 rounded-lg text-sm font-bold ${mode === 'sample' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-500'}`}
                        >
                            Amostra
                        </button>
                        <button
                            onClick={() => setMode('ids')}
                            className={`flex-1 py-2 rounded-lg text-sm font-bold ${mode === 'ids' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-500'}`}
                        >
                            IDs específicos
                        </button>
                    </div>

                    {mode === 'sample' ? (
                        <div className="flex items-center gap-2">
                            <label className="text-xs font-bold text-gray-500 uppercase w-32">Tamanho da amostra</label>
                            <input
                                type="number" value={sampleSize} min={1} max={50}
                                onChange={e => setSampleSize(e.target.value)}
                                className="w-32 px-3 py-2 rounded-lg border border-gray-200 text-sm font-mono"
                            />
                            <span className="text-xs text-gray-400">não é amostra aleatória de verdade — ver InfoCard acima</span>
                        </div>
                    ) : (
                        <div>
                            <label className="text-xs font-bold text-gray-500 uppercase block mb-1">IDs (fam_..., separados por vírgula ou espaço)</label>
                            <textarea
                                value={idsText} onChange={e => setIdsText(e.target.value)}
                                placeholder="fam_2077396, fam_2082187, ..."
                                rows={3}
                                className="w-full px-3 py-2 rounded-lg border border-gray-200 text-sm font-mono"
                            />
                        </div>
                    )}

                    {isFailure && <FeedbackMessage message={`Erro: ${error}`} type="error" />}

                    <button
                        onClick={run}
                        disabled={isPending || !canRun}
                        className={`w-full relative py-3 rounded-xl font-black text-white uppercase text-sm tracking-widest transition-all overflow-hidden
                            ${isPending || !canRun ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'}`}
                    >
                        {isPending && (
                            <div className="absolute top-0 left-0 h-full bg-blue-800/40 transition-all duration-500 ease-out" style={{ width: `${progress}%` }}></div>
                        )}
                        <span className="relative z-10 flex items-center justify-center gap-2">
                            {isPending ? (
                                <><LoadingSpinner size="sm" color="white" /> {message || 'Processando...'} ({progress}%)</>
                            ) : isSuccess ? (
                                <><FiCheckCircle size={18} /> Concluído! Redirecionando...</>
                            ) : (
                                'Consultar composição'
                            )}
                        </span>
                    </button>
                </fieldset>
            </div>
        </div>
    );
};

export default PipelinePopulationFamiliaPage;
