import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiFileText, FiCheckCircle, FiPlus, FiX } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import { triggerNotificacao } from '../../services/populationSpaceService';

const PipelinePopulationNotificacaoPage = () => {
    usePageTitle('PopulationSpace: Caso de Notificação');
    const navigate = useNavigate();

    const [diseaseCode, setDiseaseCode] = useState('TUBE');
    const [years, setYears] = useState(['22']);
    const [limit, setLimit] = useState(2000);
    const [taskId, setTaskId] = useState(null);
    const { isPending, isSuccess, isFailure, progress, message, error } = useCeleryTaskStatus(
        taskId, '/api/pipelines/population-space/tasks/'
    );

    const updateYear = (idx, value) => setYears(ys => ys.map((y, i) => (i === idx ? value : y)));
    const addYear = () => setYears(ys => [...ys, '']);
    const removeYear = (idx) => setYears(ys => ys.filter((_, i) => i !== idx));

    const validYears = years.map(y => y.trim()).filter(Boolean);

    const run = async () => {
        setTaskId(null);
        try {
            const { task_id } = await triggerNotificacao(diseaseCode.toUpperCase(), validYears, Number(limit));
            setTaskId(task_id);
        } catch (err) {
            alert(`Falha ao disparar análise de notificação: ${err.response?.data?.error || err.message}`);
        }
    };

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => navigate(`/dashboards/population-notificacao/viewer?taskId=${taskId}`), 1200);
        }
    }, [isSuccess, taskId, navigate]);

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Caso de Notificação</h1>
                <p className="text-gray-500 mt-2 text-lg">Perfil e desfecho de casos do SINAN — PopulationSpace (BioSpace).</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Trata cada NOTIFICAÇÃO de um agravo do SINAN (não o paciente, não o estabelecimento) como
                        unidade de análise, do perfil no registro até o desfecho no encerramento. Tuberculose
                        (código TUBE) tem perfil completo e os 5 desfechos verificados (SITUA_ENCE). Qualquer
                        outro agravo com o campo EVOLUCAO usa o caminho genérico: só perfil universal
                        (idade/sexo/data) e 3 desfechos (cura, óbito pela doença, óbito por outra causa) — alguns
                        agravos (ex. violência interpessoal/VIOL) têm o campo de desfecho inteiramente vazio na
                        base de origem, e isso aparece como ausência, nunca um valor inventado.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <FiFileText className="text-blue-500" /> Agravo e competências
                    </h2>

                    <div className="flex items-center gap-2">
                        <label className="text-xs font-bold text-gray-500 uppercase w-32">Código (SINAN)</label>
                        <input
                            type="text" placeholder="ex.: TUBE" value={diseaseCode} maxLength={4}
                            onChange={e => setDiseaseCode(e.target.value.toUpperCase())}
                            className="w-32 px-3 py-2 rounded-lg border border-gray-200 text-sm font-mono uppercase"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs font-bold text-gray-500 uppercase">Competências (ano, 2 dígitos)</label>
                        {years.map((y, idx) => (
                            <div key={idx} className="flex items-center gap-2">
                                <input
                                    type="text" placeholder="ex.: 22" value={y} maxLength={2}
                                    onChange={e => updateYear(idx, e.target.value)}
                                    className="w-24 px-3 py-2 rounded-lg border border-gray-200 text-sm font-mono"
                                />
                                <button onClick={() => removeYear(idx)} className="p-2 text-gray-400 hover:text-red-500">
                                    <FiX />
                                </button>
                            </div>
                        ))}
                        <button onClick={addYear} className="flex items-center gap-2 text-sm font-bold text-blue-600 hover:text-blue-700">
                            <FiPlus /> Adicionar competência
                        </button>
                    </div>

                    <div className="flex items-center gap-2">
                        <label className="text-xs font-bold text-gray-500 uppercase w-32">Limite de linhas</label>
                        <input
                            type="number" value={limit} min={100} step={100}
                            onChange={e => setLimit(e.target.value)}
                            className="w-32 px-3 py-2 rounded-lg border border-gray-200 text-sm font-mono"
                        />
                        <span className="text-xs text-gray-400">por arquivo/competência — protege a interface de carregar uma base inteira</span>
                    </div>

                    {isFailure && <FeedbackMessage message={`Erro: ${error}`} type="error" />}

                    <button
                        onClick={run}
                        disabled={isPending || !diseaseCode || validYears.length < 1}
                        className={`w-full relative py-3 rounded-xl font-black text-white uppercase text-sm tracking-widest transition-all overflow-hidden
                            ${isPending || !diseaseCode || validYears.length < 1 ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'}`}
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
                                `Carregar notificações (${diseaseCode || '—'})`
                            )}
                        </span>
                    </button>
                </fieldset>
            </div>
        </div>
    );
};

export default PipelinePopulationNotificacaoPage;
