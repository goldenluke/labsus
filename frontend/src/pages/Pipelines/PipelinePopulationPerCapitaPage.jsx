import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiCompass, FiCheckCircle } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import FacilitySearchPicker from '../../components/common/FacilitySearchPicker';
import { KNOWN_FACILITIES, DEFAULT_ANO, DEFAULT_MES } from '../../config/populationSpaceFacilities';
import { triggerPerCapita } from '../../services/populationSpaceService';

const PipelinePopulationPerCapitaPage = () => {
    usePageTitle('PopulationSpace: Per Capita (Taxa Populacional)');
    const navigate = useNavigate();

    const [selected, setSelected] = useState(KNOWN_FACILITIES.slice(0, 5).map(f => ({ facility_uri: f.facility_uri, uf: f.uf })));
    const [taskId, setTaskId] = useState(null);
    const { isPending, isSuccess, isFailure, progress, message, error } = useCeleryTaskStatus(
        taskId, '/api/pipelines/population-space/tasks/'
    );

    const run = async () => {
        setTaskId(null);
        try {
            const facilities = selected.map(f => ({ facility_uri: f.facility_uri, ano: DEFAULT_ANO, mes: DEFAULT_MES, uf: f.uf }));
            const { task_id } = await triggerPerCapita(facilities);
            setTaskId(task_id);
        } catch (err) {
            alert(`Falha ao disparar análise per capita: ${err.response?.data?.error || err.message}`);
        }
    };

    React.useEffect(() => {
        if (isSuccess && taskId) {
            setTimeout(() => navigate(`/dashboards/population-per-capita/viewer?taskId=${taskId}`), 1200);
        }
    }, [isSuccess, taskId, navigate]);

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Per Capita (Taxa Populacional)</h1>
                <p className="text-gray-500 mt-2 text-lg">Contagens do estabelecimento ÷ população do município — PopulationSpace (BioSpace).</p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Divide as contagens brutas do estabelecimento (internações, vínculos profissionais)
                        pela população do MUNICÍPIO onde ele está — mesma escala (por mil habitantes) que o
                        pipeline de Indicadores já usa. O município vem do cadastro de vínculos profissionais
                        (CNES) da própria competência: sem UF informada, ou sem nenhum vínculo carregado
                        naquele arquivo, o município (e a taxa) ficam indisponíveis — nunca um valor
                        inventado. Preencha a UF de cada estabelecimento abaixo para maximizar a resolução.
                    </p>
                </InfoCard>

                <fieldset disabled={isPending} className="space-y-4 bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                        <FiCompass className="text-blue-500" /> Estabelecimentos
                    </h2>
                    <FacilitySearchPicker selected={selected} onChange={setSelected} suggestions={KNOWN_FACILITIES} />

                    {isFailure && <FeedbackMessage message={`Erro: ${error}`} type="error" />}

                    <button
                        onClick={run}
                        disabled={isPending || selected.length < 1}
                        className={`w-full relative py-3 rounded-xl font-black text-white uppercase text-sm tracking-widest transition-all overflow-hidden
                            ${isPending || selected.length < 1 ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'}`}
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
                                `Calcular taxa (${selected.length} estabelecimentos)`
                            )}
                        </span>
                    </button>
                </fieldset>
            </div>
        </div>
    );
};

export default PipelinePopulationPerCapitaPage;
