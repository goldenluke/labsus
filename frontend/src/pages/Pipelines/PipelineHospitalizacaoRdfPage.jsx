import React, { useState, useCallback, useMemo } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { FiDatabase, FiCheckCircle, FiShare2 } from 'react-icons/fi';

import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import usePageTitle from '../../hooks/usePageTitle';
import { UF_CONFIGS } from '../../config/ufConfigs';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import InfoCard from '../../components/common/InfoCard';

const GRUPO_OPTIONS = [
    { value: 'RD', label: 'RD — Aprovadas' },
    { value: 'RJ', label: 'RJ — Rejeitadas' },
    { value: 'ER', label: 'ER — Rejeitadas com erro' },
];

const MES_OPTIONS = Array.from({ length: 12 }, (_, i) => i + 1);

const PipelineHospitalizacaoRdfPage = () => {
    usePageTitle('Hospitalização (BPHO/RDF)');
    const navigate = useNavigate();

    const [uf, setUf] = useState('TO');
    const [ano, setAno] = useState(new Date().getFullYear());
    const [mes, setMes] = useState(1);
    const [grupo, setGrupo] = useState('RD');
    const [outputFileName, setOutputFileName] = useState('');

    const [taskId, setTaskId] = useState(null);
    const {
        isPending, isSuccess, isFailure,
        progress, message: taskMessage, error: taskError,
    } = useCeleryTaskStatus(taskId, '/api/pipelines/hospitalizacao-rdf/tasks/');

    const ufOptions = useMemo(() => Object.keys(UF_CONFIGS)
        .filter(code => code !== 'BR')
        .map(code => ({ label: `${UF_CONFIGS[code].nome} (${code})`, value: code }))
        .sort((a, b) => a.label.localeCompare(b.label)), []);

    const yearOptions = useMemo(() => {
        const currentYear = new Date().getFullYear();
        return Array.from({ length: 10 }, (_, i) => currentYear - i);
    }, []);

    const triggerPipeline = useCallback(async () => {
        setTaskId(null);
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.post('/api/pipelines/hospitalizacao-rdf/trigger/', {
                uf,
                ano,
                mes,
                grupo,
                output_filename: outputFileName || `hospitalizacao_rdf_${uf.toLowerCase()}_${ano}${String(mes).padStart(2, '0')}`,
            }, { headers: { Authorization: `Token ${token}` } });

            setTaskId(response.data.task_id);
        } catch (err) {
            alert(`Falha ao disparar pipeline: ${err.response?.data?.error || err.message}`);
        }
    }, [uf, ano, mes, grupo, outputFileName]);

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => {
                navigate(`/dashboards/hospitalizacao-rdf/viewer?taskId=${taskId}`);
            }, 1200);
        }
    }, [isSuccess, taskId, navigate]);

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Hospitalização (BPHO/RDF)</h1>
                <p className="text-gray-500 mt-2 text-lg">Carrega uma competência do SIH na ontologia (BPHO) e agrega Hospitalizations por estabelecimento via SPARQL.</p>
            </header>

            <div className="max-w-3xl mx-auto space-y-8 pb-12">
                {isFailure && <FeedbackMessage message={`Erro na tarefa: ${taskError}`} type="error" />}

                <InfoCard title="Como funciona esta pipeline?">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Diferente das outras pipelines, esta não baixa e processa dados com pandas: ela pede à <strong>BPHO
                        (Brazilian Public Health Ontology)</strong> para carregar a competência solicitada no seu armazenamento
                        RDF persistente (carga idempotente — repetir não duplica nada) e depois consulta esse armazenamento
                        por <strong>SPARQL</strong> para obter o agregado de internações por estabelecimento de saúde. Os
                        identificadores de estabelecimento (CNES) usados aqui já são compartilhados com outros dados
                        administrativos (vínculos profissionais, equipes) já carregados na ontologia.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-6">
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                            <FiDatabase className="text-blue-500" /> 1. Identificação do Relatório
                        </h2>
                        <input
                            type="text"
                            value={outputFileName}
                            onChange={e => setOutputFileName(e.target.value)}
                            placeholder="Ex: hospitalizacao_to_202512"
                            className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
                        />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                            <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">2. Estado (UF)</h2>
                            <select
                                value={uf}
                                onChange={e => setUf(e.target.value)}
                                className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
                            >
                                {ufOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                            </select>
                        </div>

                        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                            <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">3. Grupo de arquivo (SIH)</h2>
                            <select
                                value={grupo}
                                onChange={e => setGrupo(e.target.value)}
                                className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
                            >
                                {GRUPO_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                            </select>
                        </div>

                        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                            <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">4. Ano</h2>
                            <select
                                value={ano}
                                onChange={e => setAno(parseInt(e.target.value, 10))}
                                className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
                            >
                                {yearOptions.map(y => <option key={y} value={y}>{y}</option>)}
                            </select>
                        </div>

                        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                            <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">5. Mês</h2>
                            <select
                                value={mes}
                                onChange={e => setMes(parseInt(e.target.value, 10))}
                                className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
                            >
                                {MES_OPTIONS.map(m => <option key={m} value={m}>{String(m).padStart(2, '0')}</option>)}
                            </select>
                        </div>
                    </div>
                </fieldset>

                <div className="mt-10 pb-12">
                    <button
                        onClick={triggerPipeline}
                        disabled={isPending}
                        className={`w-full relative py-4 rounded-2xl font-black text-white transition-all shadow-xl overflow-hidden
                            ${isPending ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'}`}
                    >
                        {isPending && (
                            <div
                                className="absolute top-0 left-0 h-full bg-blue-800/40 transition-all duration-500 ease-out"
                                style={{ width: `${progress}%` }}
                            ></div>
                        )}
                        <span className="relative z-10 flex items-center justify-center gap-3 tracking-widest uppercase">
                            {isPending ? (
                                <>
                                    <LoadingSpinner size="sm" color="white" />
                                    <span>{taskMessage || 'PROCESSANDO...'} ({progress}%)</span>
                                </>
                            ) : isSuccess ? (
                                <>
                                    <FiCheckCircle size={20} />
                                    <span>CONCLUÍDO! REDIRECIONANDO...</span>
                                </>
                            ) : (
                                <>
                                    <FiShare2 size={20} />
                                    <span>CARREGAR E CONSULTAR NA BPHO</span>
                                </>
                            )}
                        </span>
                    </button>
                </div>
            </div>
        </div>
    );
};

export default PipelineHospitalizacaoRdfPage;
