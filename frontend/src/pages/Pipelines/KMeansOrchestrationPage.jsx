import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
    FiMap, FiArrowRightCircle, FiDatabase, FiSettings,
    FiLayers, FiCheckCircle, FiInfo, FiActivity
} from 'react-icons/fi';

import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import usePageTitle from '../../hooks/usePageTitle';
import { INDICADORES_MAP } from '../../config/indicadores';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import AsyncFileSelect from '../../components/common/AsyncFileSelect';
import InfoCard from '../../components/common/InfoCard';

const KMeansOrchestrationPage = () => {
    usePageTitle('Orquestrar Perfis de Saúde');
    const navigate = useNavigate();

    // Estados do Formulário
    const [selectedInputFile, setSelectedInputFile] = useState(null);
    const [selectedArchetypeFile, setSelectedArchetypeFile] = useState(null);
    const [nClusters, setNClusters] = useState(3);
    const [featuresForClustering, setFeaturesForClustering] = useState([]);
    const [outputFileName, setOutputFileName] = useState('');

    // Estados de Dados Dinâmicos
    const [availableFeatures, setAvailableFeatures] = useState([]);
    const [loadingFeatures, setLoadingFeatures] = useState(false);

    // Controle da Task
    const [kmeansTaskId, setKmeansTaskId] = useState(null);
    const {
        status, result, error: taskError, isPending,
        isSuccess, isFailure, progress, message: taskMessage
    } = useCeleryTaskStatus(kmeansTaskId, '/api/pipelines/kmeans/tasks/');

    // Carrega os indicadores do arquivo selecionado para permitir a escolha das features
    useEffect(() => {
        const fetchIndicators = async () => {
            if (!selectedInputFile?.value) {
                setAvailableFeatures([]);
                setFeaturesForClustering([]);
                return;
            }
            setLoadingFeatures(true);
            try {
                const token = localStorage.getItem('authToken');
                const response = await axios.get(`/api/files/${selectedInputFile.value}/data/`, {
                    headers: { 'Authorization': `Token ${token}` }
                });
                const data = response.data;
                if (data.length > 0) {
                    const firstItem = data[0];
                    const metadataColumns = ['cod_mun_ibge_6', 'municipio', 'UF', 'cod_mun_ibge_7', 'perfil', 'nome_uf', 'ANO', 'MES', 'populacao', 'cor', 'cluster_num', 'MES_x', 'MES_y'];
                    const indicators = Object.keys(firstItem).filter(key =>
                    !metadataColumns.includes(key) && typeof firstItem[key] === 'number'
                    ).sort((a, b) => (INDICADORES_MAP[a] || a).localeCompare(INDICADORES_MAP[b] || b));

                    setAvailableFeatures(indicators);
                    setFeaturesForClustering(indicators); // Seleciona todos por padrão
                }
            } catch (err) {
                console.error("Erro ao carregar colunas do arquivo:", err);
            } finally {
                setLoadingFeatures(false);
            }
        };
        fetchIndicators();
    }, [selectedInputFile]);

    const handleFeatureToggle = (ind) => {
        setFeaturesForClustering(prev =>
        prev.includes(ind) ? prev.filter(i => i !== ind) : [...prev, ind]
        );
    };

    const triggerKMeans = useCallback(async () => {
        if (!selectedInputFile?.value) return alert("Selecione o arquivo de indicadores.");
        if (featuresForClustering.length === 0) return alert("Selecione ao menos um indicador.");

        setKmeansTaskId(null);
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.post('/api/pipelines/kmeans/trigger/', {
                input_file_id: selectedInputFile.value,
                n_clusters: nClusters,
                features_for_clustering: featuresForClustering,
                archetype_file_id: selectedArchetypeFile?.value || null,
                output_filename: outputFileName || `perfis_kmeans_${Date.now()}`
            }, { headers: { 'Authorization': `Token ${token}` } });

            setKmeansTaskId(response.data.task_id);
        } catch (err) {
            alert(`Erro ao iniciar: ${err.response?.data?.error || err.message}`);
        }
    }, [selectedInputFile, selectedArchetypeFile, nClusters, featuresForClustering, outputFileName]);

    useEffect(() => {
        if (isSuccess && result?.output_file_id) {
            setTimeout(() => {
                navigate(`/dashboards/kmeans-perfis-saude?fileId=${result.output_file_id}`);
            }, 1500);
        }
    }, [isSuccess, result, navigate]);

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
        <header className="mb-8 text-center">
        <h1 className="text-3xl font-black text-gray-800 tracking-tight">Agrupamento de Perfis de Saúde</h1>
        <p className="text-gray-500 mt-2 text-lg">Utilize o algoritmo K-Means para segmentar territórios por comportamento epidemiológico.</p>
        </header>

        <div className="max-w-5xl mx-auto space-y-8">

        {isFailure && <FeedbackMessage message={`Erro na tarefa: ${taskError}`} type="error" />}

        <InfoCard title="Como funciona o K-Means no LabSUS?">
        <p className="text-sm leading-relaxed">
        O K-Means agrupa municípios que possuem valores similares nos indicadores selecionados.
        Se você fornecer um <strong>Arquivo de Arquétipos</strong>, o sistema comparará os grupos encontrados com suas definições teóricas para nomear cada perfil (ex: "Vulnerabilidade Alta") automaticamente.
        </p>
        </InfoCard>

        <fieldset disabled={isPending} className="space-y-6">

        {/* PASSO 1: NOME DO RESULTADO */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
        <FiActivity className="text-blue-500" /> 1. Nome do Arquivo de Saída
        </h2>
        <input
        type="text"
        value={outputFileName}
        onChange={e => setOutputFileName(e.target.value)}
        placeholder="Ex: perfis_saude_to_2023"
        className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition"
        />
        </div>

        {/* PASSO 2: ARQUIVOS DE ENTRADA */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
        <FiDatabase className="text-blue-500" /> 2. Base de Indicadores
        </h2>
        <AsyncFileSelect
        value={selectedInputFile}
        onChange={setSelectedInputFile}
        fileType="INDICATORS"
        />
        </div>

        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
        <FiLayers className="text-purple-500" /> 3. Arquétipos (Opcional)
        </h2>
        <AsyncFileSelect
        value={selectedArchetypeFile}
        onChange={setSelectedArchetypeFile}
        fileType="ARCHETYPE"
        isClearable
        placeholder="Selecione para rotular perfis..."
        />
        </div>
        </div>

        {/* PASSO 3: PARÂMETROS DO MODELO */}
        <div className={`bg-white p-6 rounded-2xl shadow-sm border border-gray-200 transition-opacity ${!selectedInputFile ? 'opacity-40 pointer-events-none' : ''}`}>
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
        <FiSettings className="text-blue-500" /> 4. Configuração do Agrupamento
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
        <div className="md:col-span-1">
        <label className="block text-xs font-bold text-gray-500 uppercase mb-3">Número de Grupos (K)</label>
        <div className="flex items-center gap-4 bg-gray-50 p-3 rounded-xl border border-gray-100">
        <input
        type="number"
        min="2"
        max="10"
        value={nClusters}
        onChange={e => setNClusters(parseInt(e.target.value) || 2)}
        className="bg-transparent text-xl font-black text-blue-600 w-full text-center outline-none"
        />
        </div>
        <p className="text-[10px] text-gray-400 mt-2 italic text-center">Recomendado: 3 a 5</p>
        </div>

        <div className="md:col-span-3">
        <div className="flex justify-between items-center mb-3">
        <label className="block text-xs font-bold text-gray-500 uppercase">Indicadores para Análise ({featuresForClustering.length})</label>
        <button
        onClick={() => setFeaturesForClustering(featuresForClustering.length === availableFeatures.length ? [] : availableFeatures)}
        className="text-[10px] font-bold text-blue-500 uppercase hover:underline"
        >
        {featuresForClustering.length === availableFeatures.length ? 'Desmarcar Todos' : 'Selecionar Todos'}
        </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-60 overflow-y-auto pr-2 scrollbar-styled p-1">
        {loadingFeatures ? <LoadingSpinner size="sm"/> : availableFeatures.map(ind => (
            <label key={ind} className="flex items-center gap-3 p-3 bg-gray-50 rounded-xl border border-gray-100 cursor-pointer hover:bg-white hover:border-blue-200 transition">
            <input
            type="checkbox"
            checked={featuresForClustering.includes(ind)}
            onChange={() => handleFeatureToggle(ind)}
            className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="text-xs font-bold text-gray-600 leading-tight">
            {INDICADORES_MAP[ind] || ind}
            </span>
            </label>
        ))}
        </div>
        </div>
        </div>
        </div>
        </fieldset>

        {/* BOTÃO DE EXECUÇÃO */}
        <div className="mt-10">
        <button
        onClick={triggerKMeans}
        disabled={isPending || !selectedInputFile || featuresForClustering.length === 0}
        className={`w-full relative py-4 rounded-2xl font-black text-white transition-all shadow-xl overflow-hidden
            ${(isPending || !selectedInputFile || featuresForClustering.length === 0) ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'}`}
            >
            {isPending && (
                <div
                className="absolute top-0 left-0 h-full bg-blue-800/40 transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
                ></div>
            )}

            <span className="relative z-10 flex items-center justify-center gap-3 tracking-widest">
            {isPending ? (
                <>
                <LoadingSpinner size="sm" color="white" />
                <span>{taskMessage || 'PROCESSANDO CLUSTERS...'} ({progress}%)</span>
                </>
            ) : isSuccess ? (
                <>
                <FiCheckCircle size={20} />
                <span>SUCESSO! REDIRECIONANDO...</span>
                </>
            ) : (
                <>
                <FiArrowRightCircle size={20} />
                <span>INICIAR AGRUPAMENTO K-MEANS</span>
                </>
            )}
            </span>
            </button>
            </div>
            </div>

            <footer className="mt-20 py-8 border-t border-gray-200 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-gray-200 shadow-sm text-[10px] font-bold text-gray-400 uppercase tracking-widest">
            <FiMap /> LabSUS Machine Learning Engine • Scikit-Learn Integration
            </div>
            </footer>
            </div>
    );
};

export default KMeansOrchestrationPage;
