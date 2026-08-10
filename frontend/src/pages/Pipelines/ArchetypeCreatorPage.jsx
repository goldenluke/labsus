import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import {
    FiTrello, FiPlus, FiDatabase, FiTrash2,
    FiCheckCircle, FiInfo, FiLayers, FiEdit3, FiSave
} from 'react-icons/fi';

import { INDICADORES_MAP } from '../../config/indicadores';
import usePageTitle from '../../hooks/usePageTitle';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import AsyncFileSelect from '../../components/common/AsyncFileSelect';
import InfoCard from '../../components/common/InfoCard';

const ArchetypeCreatorPage = () => {
    usePageTitle('Criador de Arquétipos');
    const navigate = useNavigate();

    // Estados do Formulário
    const [selectedInputFile, setSelectedInputFile] = useState(null);
    const [profileName, setProfileName] = useState('');
    const [colorHex, setColorHex] = useState('#3b82f6');
    const [indicatorsData, setIndicatorsData] = useState({});
    const [archetypesList, setArchetypesList] = useState([]);
    const [outputFilename, setOutputFilename] = useState('');

    // Estados de Controle
    const [loadingIndicators, setLoadingIndicators] = useState(false);
    const [dynamicIndicators, setDynamicIndicators] = useState([]);
    const [submissionStatus, setSubmissionStatus] = useState(null);
    const [submissionMessage, setSubmissionMessage] = useState('');

    // Carrega colunas do arquivo selecionado para servirem de base
    useEffect(() => {
        const loadIndicators = async () => {
            if (!selectedInputFile?.value) {
                setDynamicIndicators([]);
                return;
            }
            setLoadingIndicators(true);
            try {
                const token = localStorage.getItem('authToken');
                const res = await axios.get(`/api/files/${selectedInputFile.value}/data/`, {
                    headers: { 'Authorization': `Token ${token}` }
                });
                if (res.data.length > 0) {
                    const first = res.data[0];
                    const meta = ['cod_mun_ibge_6', 'municipio', 'UF', 'cod_mun_ibge_7', 'perfil', 'ANO', 'MES', 'populacao', 'cor', 'cluster_num', 'MES_x', 'MES_y'];
                    const filtered = Object.keys(first)
                    .filter(key => !meta.includes(key) && typeof first[key] === 'number')
                    .sort((a, b) => (INDICADORES_MAP[a] || a).localeCompare(INDICADORES_MAP[b] || b));
                    setDynamicIndicators(filtered);
                }
            } catch (err) {
                console.error("Erro ao carregar colunas:", err);
            } finally {
                setLoadingIndicators(false);
            }
        };
        loadIndicators();
    }, [selectedInputFile]);

    const handleAddArchetype = () => {
        if (!profileName.trim()) {
            alert('Dê um nome ao perfil.');
            return;
        }
        const row = { 'Perfil': profileName, 'Cor_Hex': colorHex };
        dynamicIndicators.forEach(ind => {
            row[ind] = parseFloat(indicatorsData[ind] || 0);
        });
        setArchetypesList([...archetypesList, row]);
        setProfileName('');
        setIndicatorsData({});
    };

    const handleRemoveArchetype = (index) => {
        setArchetypesList(archetypesList.filter((_, i) => i !== index));
    };

    const handleSave = async () => {
        if (archetypesList.length === 0) return;
        setSubmissionStatus('loading');
        try {
            const token = localStorage.getItem('authToken');
            await axios.post('/api/archetypes/save/', {
                filename: outputFilename || `arquetipos_${Date.now()}`,
                             data_rows: archetypesList,
                             indicator_columns: dynamicIndicators,
                             profile_column_name: 'Perfil',
                             color_column_name: 'Cor_Hex',
            }, { headers: { 'Authorization': `Token ${token}` } });

            setSubmissionStatus('success');
            setTimeout(() => navigate('/csv-manager'), 1500);
        } catch (err) {
            setSubmissionStatus('error');
            setSubmissionMessage(err.response?.data?.error || 'Erro ao salvar.');
        }
    };

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
        <header className="mb-8 text-center">
        <h1 className="text-3xl font-black text-gray-800">Criador de Arquétipos</h1>
        <p className="text-gray-500 mt-2">Defina perfis teóricos para orientar a rotulagem do K-Means.</p>
        </header>

        <div className="max-w-5xl mx-auto space-y-8">

        <InfoCard title="O que é um Arquétipo?">
        <p className="text-sm leading-relaxed">
        Arquétipos são "municípios modelos" que você define com valores ideais. O sistema usa esses modelos para nomear os clusters gerados pelo K-Means.
        <strong> Exemplo:</strong> Crie um perfil chamado "Alta Mortalidade" e atribua valores altos aos indicadores de óbito.
        </p>
        </InfoCard>

        {/* PASSO 1: SELEÇÃO DA BASE */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
        <FiDatabase className="text-blue-500" /> 1. Arquivo de Referência
        </h2>
        <AsyncFileSelect
        value={selectedInputFile}
        onChange={setSelectedInputFile}
        fileType="INDICATORS"
        />
        <p className="text-[10px] text-gray-400 mt-2 font-bold uppercase">
        Os indicadores deste arquivo serão usados como colunas do arquétipo.
        </p>
        </div>

        {/* PASSO 2: DEFINIÇÃO DO PERFIL */}
        <div className={`bg-white p-6 rounded-2xl shadow-sm border border-gray-200 transition-opacity ${!selectedInputFile ? 'opacity-40 pointer-events-none' : ''}`}>
        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
        <FiEdit3 className="text-blue-500" /> 2. Configurar Novo Perfil
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="md:col-span-2">
        <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Nome do Perfil</label>
        <input
        type="text"
        value={profileName}
        onChange={e => setProfileName(e.target.value)}
        placeholder="Ex: Vulnerabilidade Social Crítica"
        className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition"
        />
        </div>
        <div>
        <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Cor de Identificação</label>
        <div className="flex gap-2">
        <input
        type="color"
        value={colorHex}
        onChange={e => setColorHex(e.target.value)}
        className="h-12 w-20 border border-gray-300 rounded-xl cursor-pointer bg-white p-1"
        />
        <input
        type="text"
        value={colorHex}
        onChange={e => setColorHex(e.target.value)}
        className="flex-1 p-3 border border-gray-300 rounded-xl text-center font-mono text-sm"
        />
        </div>
        </div>
        </div>

        <div className="space-y-4">
        <label className="block text-xs font-bold text-gray-500 uppercase">Valores Referenciais</label>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 max-h-80 overflow-y-auto pr-2 scrollbar-styled p-1">
        {loadingIndicators ? <LoadingSpinner size="sm"/> : dynamicIndicators.map(ind => (
            <div key={ind} className="p-3 bg-gray-50 rounded-xl border border-gray-100">
            <span className="block text-[10px] font-bold text-gray-400 uppercase truncate mb-1" title={INDICADORES_MAP[ind] || ind}>
            {INDICADORES_MAP[ind] || ind}
            </span>
            <input
            type="number"
            step="any"
            value={indicatorsData[ind] || ''}
            onChange={e => setIndicatorsData({...indicatorsData, [ind]: e.target.value})}
            className="w-full bg-transparent border-b border-gray-300 focus:border-blue-500 outline-none text-sm font-bold text-gray-700"
            />
            </div>
        ))}
        </div>
        </div>

        <button
        onClick={handleAddArchetype}
        className="mt-8 w-full md:w-auto px-8 py-3 bg-blue-600 text-white rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-blue-700 transition shadow-lg shadow-blue-200"
        >
        <FiPlus /> Adicionar Perfil à Lista
        </button>
        </div>

        {/* PASSO 3: LISTA E SALVAMENTO */}
        {archetypesList.length > 0 && (
            <div className="space-y-6">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
            <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
            <FiLayers className="text-blue-500" /> 3. Perfis Criados ({archetypesList.length})
            </h2>

            <div className="overflow-x-auto scrollbar-styled">
            <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
            <tr>
            <th className="px-4 py-3 text-left text-[10px] font-black text-gray-400 uppercase">Cor</th>
            <th className="px-4 py-3 text-left text-[10px] font-black text-gray-400 uppercase">Nome do Perfil</th>
            <th className="px-4 py-3 text-right text-[10px] font-black text-gray-400 uppercase">Ações</th>
            </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
            {archetypesList.map((arc, idx) => (
                <tr key={idx} className="hover:bg-gray-50 transition">
                <td className="px-4 py-3">
                <div className="w-6 h-6 rounded-full shadow-inner border border-white" style={{backgroundColor: arc.Cor_Hex}}></div>
                </td>
                <td className="px-4 py-3 font-bold text-gray-700">{arc.Perfil}</td>
                <td className="px-4 py-3 text-right">
                <button onClick={() => handleRemoveArchetype(idx)} className="text-red-400 hover:text-red-600 transition">
                <FiTrash2 />
                </button>
                </td>
                </tr>
            ))}
            </tbody>
            </table>
            </div>
            </div>

            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
            <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
            <FiSave className="text-blue-500" /> 4. Finalizar e Exportar
            </h2>
            <div className="flex flex-col md:flex-row gap-4 items-end">
            <div className="flex-1 w-full">
            <label className="block text-xs font-bold text-gray-500 uppercase mb-2">Nome do Arquivo</label>
            <input
            type="text"
            value={outputFilename}
            onChange={e => setOutputFilename(e.target.value)}
            placeholder="Ex: arquetipos_saude_mental_2026"
            className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition"
            />
            </div>
            <button
            onClick={handleSave}
            disabled={submissionStatus === 'loading'}
            className="w-full md:w-auto px-10 py-3 bg-green-600 text-white rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-green-700 transition shadow-lg shadow-green-200 disabled:bg-gray-300"
            >
            {submissionStatus === 'loading' ? <LoadingSpinner size="sm" color="white"/> : <><FiCheckCircle /> Salvar Arquivo</>}
            </button>
            </div>
            {submissionStatus === 'error' && <div className="mt-4"><FeedbackMessage message={submissionMessage} type="error" /></div>}
            </div>
            </div>
        )}
        </div>

        <footer className="mt-20 py-8 border-t border-gray-200 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-white rounded-full border border-gray-200 shadow-sm text-[10px] font-bold text-gray-400 uppercase tracking-widest">
        <FiTrello /> LabSUS Design System • 2026
        </div>
        </footer>
        </div>
    );
};

export default ArchetypeCreatorPage;
