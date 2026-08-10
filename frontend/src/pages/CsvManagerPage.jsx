import React, { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import {
    FiDatabase, FiSearch, FiDownload, FiTrash2,
    FiExternalLink, FiInfo, FiChevronLeft, FiChevronRight,
    FiBarChart2, FiMap, FiTrendingUp, FiGitPullRequest,
    FiCrosshair, FiUserCheck, FiTrello, FiFileText, FiAlertCircle,
    FiGlobe, FiMapPin, FiActivity, FiCpu, FiTag, FiClock, FiShield, FiDollarSign, FiHeart, FiUsers,
    FiGrid, FiShare2, FiGitMerge, FiAlertOctagon, FiTarget, FiZap, FiBox, FiRepeat, FiTrendingDown, FiSliders, FiHexagon, FiLayers, FiGitCommit, FiBell, FiGitBranch, FiAnchor, FiCompass, FiFlag
} from 'react-icons/fi';

import usePageTitle from '../hooks/usePageTitle';
import LoadingSpinner from '../components/common/LoadingSpinner';
import FeedbackMessage from '../components/common/FeedbackMessage';
import { PIPELINES, CATEGORIAS } from '../config/pipelineCatalog';

// --- CONFIGURAÇÃO VISUAL E DE ROTAS ---
const FILE_TYPE_CONFIGS_LEGADO = {
    'INDICATORS': { label: 'Indicadores', icon: FiBarChart2, color: 'blue' },
    'K_MEANS': { label: 'Perfis (K-Means)', icon: FiMap, color: 'purple', path: '/dashboards/kmeans-perfis-saude' },
    'PREDICTION': { label: 'Predição', icon: FiTrendingUp, color: 'indigo', path: '/dashboards/predicao-internacoes' },
    'PATIENT_FLOW': { label: 'Fluxo', icon: FiGitPullRequest, color: 'cyan', path: '/dashboards/fluxo-pacientes' },
    'LOGISTIC_REGRESSION': { label: 'Regressão', icon: FiCrosshair, color: 'rose', path: '/dashboards/regressao-obitos' },
    'RISK_PREDICTION': { label: 'Risco Individual', icon: FiUserCheck, color: 'emerald', path: '/dashboards/risco-readmissao/viewer' },
    'COST_PREDICTION': { label: 'Previsão de Custo', icon: FiDollarSign, color: 'green', path: '/dashboards/custo-internacao/viewer' },
    'DETECCAO_SURTOS': { label: 'Detecção de Surtos', icon: FiAlertCircle, color: 'red', path: '/dashboards/deteccao-surtos/viewer' },
    'LOS_HIBRIDO': { label: 'LOS Híbrido', icon: FiClock, color: 'orange', path: '/dashboards/los-hibrido/viewer' },
    'RISK_PRENATAL': { label: 'Risco Perinatal', icon: FiHeart, color: 'pink', path: '/dashboards/risco-perinatal/viewer' },
    'INFANT_SURVIVAL': { label: 'Sobrevida Infantil', icon: FiUsers, color: 'rose', path: '/dashboards/sobrevida-infantil/viewer' },
    'COX_READMISSION': { label: 'Cox Readmissão', icon: FiActivity, color: 'violet', path: '/dashboards/risco-readmissao/viewer' },
    'DOENCAS_CRONICAS': { label: 'Doenças Crônicas', icon: FiActivity, color: 'amber', path: '/dashboards/doencas-cronicas/viewer' },
    'ARCHETYPE': { label: 'Arquétipo', icon: FiTrello, color: 'teal', path: '/pipelines/arquetipos' },
    'HOSPITALIZACAO_RDF': { label: 'Hospitalização (BPHO)', icon: FiShare2, color: 'blue', path: '/dashboards/hospitalizacao-rdf/viewer' },
    'POPULATION_SPACE': { label: 'PopulationSpace', icon: FiGrid, color: 'blue', path: '/dashboards/population-space/viewer' },
    'POP_COMPARE': { label: 'PopSpace: Comparação', icon: FiGitMerge, color: 'blue', path: '/dashboards/population-compare/viewer' },
    'POP_CAUSAL': { label: 'PopSpace: Causal', icon: FiActivity, color: 'blue', path: '/dashboards/population-causal/viewer' },
    'POP_ANOMALY': { label: 'PopSpace: Anomalias', icon: FiAlertOctagon, color: 'red', path: '/dashboards/population-anomaly/viewer' },
    'POP_RISK': { label: 'PopSpace: Risco', icon: FiTarget, color: 'orange', path: '/dashboards/population-risk/viewer' },
    'POP_UNCERTAINTY': { label: 'PopSpace: Incerteza', icon: FiZap, color: 'purple', path: '/dashboards/population-uncertainty/viewer' },
    'POP_CLASSIFY': { label: 'PopSpace: Classificador', icon: FiBox, color: 'indigo', path: '/dashboards/population-classify/viewer' },
    'POP_TRANSITIONS': { label: 'PopSpace: Transições', icon: FiRepeat, color: 'teal', path: '/dashboards/population-transitions/viewer' },
    'POP_SURVIVAL': { label: 'PopSpace: Sobrevida', icon: FiTrendingDown, color: 'teal', path: '/dashboards/population-survival/viewer' },
    'POP_INTERVENE': { label: 'PopSpace: Intervenção', icon: FiSliders, color: 'indigo', path: '/dashboards/population-intervene/viewer' },
    'POP_GRAPH': { label: 'PopSpace: Grafo', icon: FiHexagon, color: 'blue', path: '/dashboards/population-graph/viewer' },
    'POP_FACTOR': { label: 'PopSpace: Fatores', icon: FiLayers, color: 'blue', path: '/dashboards/population-factor/viewer' },
    'POP_TOPOLOGY': { label: 'PopSpace: Topologia', icon: FiGitCommit, color: 'blue', path: '/dashboards/population-topology/viewer' },
    'POP_EARLY_WARNING': { label: 'PopSpace: Alerta Precoce', icon: FiBell, color: 'teal', path: '/dashboards/population-early-warning/viewer' },
    'POP_GNN': { label: 'PopSpace: GNN', icon: FiGitBranch, color: 'blue', path: '/dashboards/population-gnn/viewer' },
    'POP_DYNAMICS': { label: 'PopSpace: Dinâmica', icon: FiAnchor, color: 'teal', path: '/dashboards/population-dynamics/viewer' },
    'POP_PER_CAPITA': { label: 'PopSpace: Per Capita', icon: FiCompass, color: 'orange', path: '/dashboards/population-per-capita/viewer' },
    'POP_MUNICIPIO': { label: 'PopSpace: Município', icon: FiFlag, color: 'orange', path: '/dashboards/population-municipio/viewer' },
    'POP_NOTIFICACAO': { label: 'PopSpace: Notificação', icon: FiFileText, color: 'orange', path: '/dashboards/population-notificacao/viewer' },
    'POP_FAMILIA': { label: 'PopSpace: Família', icon: FiUsers, color: 'orange', path: '/dashboards/population-familia/viewer' },
    'OTHER': { label: 'Outro', icon: FiFileText, color: 'slate', path: null },
};

// Os 30 modelos de Modelagem Avançada seguem uma convenção fixa: o nome do
// FileType no backend (api/models.py) é sempre o slug do pipeline em
// MAIÚSCULAS_COM_UNDERSCORE (ex.: 'moran-mortalidade' -> 'MORAN_MORTALIDADE').
// Gerar as entradas aqui a partir do catálogo único evita duplicar 30
// labels/ícones/rotas manualmente e mantém tudo em sincronia com a Sidebar/Home.
const FILE_TYPE_CONFIGS_MODELAGEM = {};
PIPELINES
    .filter((p) => p.path.startsWith('/pipelines/modelagem/'))
    .forEach((p) => {
        const fileTypeKey = p.key.toUpperCase().replace(/-/g, '_');
        const categoria = CATEGORIAS.find((c) => c.id === p.categoria);
        FILE_TYPE_CONFIGS_MODELAGEM[fileTypeKey] = {
            label: p.title,
            icon: p.icon,
            color: categoria?.color || 'slate',
            path: `/dashboards/modelagem/${p.key}`,
            usesTaskId: true,
        };
    });

const FILE_TYPE_CONFIGS = { ...FILE_TYPE_CONFIGS_LEGADO, ...FILE_TYPE_CONFIGS_MODELAGEM };

const CsvManagerPage = () => {
    usePageTitle('Banco de Dados');

    const [files, setFiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterType, setFilterType] = useState('ALL');
    const [selectedFiles, setSelectedFiles] = useState([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);

    const fetchFiles = useCallback(async (page = 1) => {
        setLoading(true);
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.get('/api/files/', {
                headers: { 'Authorization': `Token ${token}` },
                params: {
                    page: page,
                    search: searchTerm,
                    file_type: filterType === 'ALL' ? undefined : filterType,
                    page_size: 12
                }
            });
            setFiles(response.data.results);
            setTotalPages(Math.ceil(response.data.count / 12));
            setCurrentPage(page);
        } catch (err) {
            setError("Falha ao carregar o repositório de arquivos.");
        } finally {
            setLoading(false);
        }
    }, [searchTerm, filterType]);

    useEffect(() => {
        const timer = setTimeout(() => fetchFiles(1), 400);
        return () => clearTimeout(timer);
    }, [fetchFiles]);

    const handleDelete = async (id) => {
        if (!window.confirm("Deseja excluir permanentemente este arquivo?")) return;
        try {
            const token = localStorage.getItem('authToken');
            await axios.delete(`/api/files/${id}/`, { headers: { 'Authorization': `Token ${token}` } });
            fetchFiles(currentPage);
        } catch (err) { alert("Erro ao excluir arquivo."); }
    };

    const handleBatchDelete = async () => {
        if (!window.confirm(`Excluir ${selectedFiles.length} arquivos selecionados?`)) return;
        setLoading(true);
        try {
            const token = localStorage.getItem('authToken');
            await Promise.all(selectedFiles.map(id =>
            axios.delete(`/api/files/${id}/`, { headers: { 'Authorization': `Token ${token}` } })
            ));
            setSelectedFiles([]);
            fetchFiles(1);
        } catch (err) { alert("Erro na exclusão em lote."); } finally { setLoading(false); }
    };

    const toggleSelect = (id) => {
        setSelectedFiles(prev => prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]);
    };

    // --- FUNÇÃO PARA RENDERIZAR DETALHES TÉCNICOS EXTRAÍDOS DA DESCRIÇÃO ---
    const renderTaskSpecs = (file) => {
        if (!file.description) return null;

        const specs = {
            ufs: file.description.match(/UFs:\s*\[?'?([\w, \s]+)'?\]?/)?.[1],
            regime: file.description.match(/Regime:\s*(\w+)/)?.[1],
            resilience: file.description.match(/Resiliência:\s*([\d.]+)/)?.[1],
            cids: file.description.match(/CIDs:\s*\[?'?([\w, \s]+)'?\]?/)?.[1],
            custo: file.description.match(/Custo Estimado:\s*([\d.,R$\s]+)/)?.[1],
            idade: file.description.match(/Idade:\s*(\d+)/)?.[1],
            diagnostico: file.description.match(/Diagnóstico:\s*(\S+)/)?.[1],
            procedimento: file.description.match(/Procedimento:\s*(\S+)/)?.[1],
            agravo: file.description.match(/surto\s*-\s*(.+?)\s*\(/)?.[1],
            alertas: file.description.match(/\((\d+)\s*alertas?\)/)?.[1],
            departamento_los: file.description.match(/LOS Híbrido\s*-\s*(.+?)\./)?.[1],
            classificacao_los: file.description.match(/Classificação:\s*(\w+)/)?.[1],
            probabilidade_los: file.description.match(/p=([\d.]+)/)?.[1],
            previsao_dias_los: file.description.match(/Previsão:\s*([\d.]+)/)?.[1],
        };

        const isCost = file.file_type === 'COST_PREDICTION';
        const isOutbreak = file.file_type === 'DETECCAO_SURTOS';
        const isLosHibrido = file.file_type === 'LOS_HIBRIDO';
        const hasCostSpecs = specs.custo || specs.idade || specs.diagnostico || specs.procedimento;
        const hasKmeansSpecs = specs.regime || specs.resilience || specs.ufs;
        const hasOutbreakSpecs = specs.agravo || specs.alertas;
        const hasLosSpecs = specs.departamento_los || specs.classificacao_los || specs.probabilidade_los || specs.previsao_dias_los;

        if (!hasCostSpecs && !hasKmeansSpecs && !hasOutbreakSpecs && !hasLosSpecs) return null;

        return (
            <div className="mt-4 pt-3 border-t border-gray-100 space-y-2">
            <div className="flex items-center justify-between text-[9px] font-black uppercase tracking-tighter">
            <span className="text-gray-400">Especificações Técnicas</span>
            {file.task_id && <span className="text-blue-500 font-mono">ID: {String(file.task_id).substring(0,6)}</span>}
            </div>

            <div className="grid grid-cols-2 gap-2">
            {isCost && hasCostSpecs && (
                <>
                {specs.custo && (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-green-50 rounded-lg border border-green-100 col-span-2">
                    <FiDollarSign size={10} className="text-green-600" />
                    <span className="text-[9px] font-bold text-green-700 truncate">{specs.custo.trim()}</span>
                    </div>
                )}
                {specs.idade && (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-50 rounded-lg border border-slate-100">
                    <FiClock size={10} className="text-indigo-500" />
                    <span className="text-[9px] font-bold text-slate-600">{specs.idade} anos</span>
                    </div>
                )}
                {specs.diagnostico && (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-50 rounded-lg border border-slate-100">
                    <FiActivity size={10} className="text-rose-500" />
                    <span className="text-[9px] font-bold text-slate-600 truncate">{specs.diagnostico}</span>
                    </div>
                )}
                {specs.procedimento && (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-50 rounded-lg border border-slate-100">
                    <FiTag size={10} className="text-blue-500" />
                    <span className="text-[9px] font-bold text-slate-600 truncate">{specs.procedimento}</span>
                    </div>
                )}
                </>
            )}
            {!isCost && hasKmeansSpecs && (
                <>
                {specs.regime && (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-50 rounded-lg border border-slate-100">
                    <FiActivity size={10} className="text-indigo-500" />
                    <span className="text-[9px] font-bold text-slate-600 truncate">{specs.regime}</span>
                    </div>
                )}
                {specs.resilience && (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-50 rounded-lg border border-slate-100">
                    <FiShield size={10} className="text-emerald-500" />
                    <span className="text-[9px] font-bold text-slate-600">RES: {specs.resilience}</span>
                    </div>
                )}
                {specs.ufs && (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-50 rounded-lg border border-slate-100 col-span-2">
                    <FiMapPin size={10} className="text-blue-500" />
                    <span className="text-[9px] font-bold text-slate-600 truncate">{specs.ufs}</span>
                    </div>
                )}
                </>
            )}
            {isOutbreak && hasOutbreakSpecs && (
                <>
                {specs.agravo && (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-red-50 rounded-lg border border-red-100">
                    <FiActivity size={10} className="text-red-500" />
                    <span className="text-[9px] font-bold text-red-700 truncate">{specs.agravo}</span>
                    </div>
                )}
                {specs.alertas && (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-amber-50 rounded-lg border border-amber-100">
                    <FiAlertCircle size={10} className="text-amber-500" />
                    <span className="text-[9px] font-bold text-amber-700">{specs.alertas} alertas</span>
                    </div>
                )}
                </>
            )}
            {isLosHibrido && hasLosSpecs && (
                <>
                {specs.departamento_los && (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-orange-50 rounded-lg border border-orange-100">
                    <FiActivity size={10} className="text-orange-500" />
                    <span className="text-[9px] font-bold text-orange-700 truncate">{specs.departamento_los}</span>
                    </div>
                )}
                {specs.classificacao_los && (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-50 rounded-lg border border-slate-100">
                    <FiTag size={10} className="text-indigo-500" />
                    <span className="text-[9px] font-bold text-slate-600">{specs.classificacao_los}</span>
                    </div>
                )}
                {specs.probabilidade_los && (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-slate-50 rounded-lg border border-slate-100">
                    <FiCrosshair size={10} className="text-blue-500" />
                    <span className="text-[9px] font-bold text-slate-600">p={specs.probabilidade_los}</span>
                    </div>
                )}
                {specs.previsao_dias_los && (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-blue-50 rounded-lg border border-blue-100">
                    <FiClock size={10} className="text-blue-600" />
                    <span className="text-[9px] font-bold text-blue-700">{specs.previsao_dias_los} dias</span>
                    </div>
                )}
                </>
            )}
            </div>
            </div>
        );
    };

    return (
        <div className="p-6 bg-gray-50 min-h-screen text-gray-800">
        {/* HEADER */}
        <header className="flex flex-col md:flex-row justify-between items-center mb-10 gap-6">
        <div>
        <h1 className="text-3xl font-black text-gray-900 tracking-tight flex items-center gap-3">
        <FiDatabase className="text-blue-600" /> Repositório de <span className="text-blue-600 font-light">Dados</span>
        </h1>
        <p className="text-gray-500 text-sm font-medium mt-1 uppercase tracking-widest font-mono">Gestão de Ativos e Resultados de Análise</p>
        </div>
        {selectedFiles.length > 0 && (
            <button onClick={handleBatchDelete} className="px-6 py-3 bg-red-600 text-white rounded-2xl text-xs font-black hover:bg-red-700 transition shadow-lg flex items-center gap-2">
            <FiTrash2 /> EXCLUIR SELECIONADOS ({selectedFiles.length})
            </button>
        )}
        </header>

        {/* FILTROS */}
        <div className="bg-white p-4 rounded-3xl border border-gray-200 shadow-sm mb-8 flex flex-col md:flex-row gap-4 items-center">
        <div className="flex-1 relative w-full">
        <FiSearch className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
        type="text"
        placeholder="Pesquisar arquivo..."
        className="w-full pl-12 pr-4 py-3 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 transition shadow-inner"
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        />
        </div>
        <select
        value={filterType}
        onChange={(e) => setFilterType(e.target.value)}
        className="w-full md:w-48 p-3 bg-gray-50 border-none rounded-2xl text-xs font-bold text-gray-600 outline-none"
        >
        <option value="ALL">TODOS OS TIPOS</option>
        {Object.entries(FILE_TYPE_CONFIGS).map(([key, cfg]) => (
            <option key={key} value={key}>{cfg.label.toUpperCase()}</option>
        ))}
        </select>
        </div>

        {/* GRID DE CARDS */}
        {loading ? (
            <div className="p-20 text-center"><LoadingSpinner size="lg" /></div>
        ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-12">
            {files.map((file) => {
                const cfg = FILE_TYPE_CONFIGS[file.file_type] || FILE_TYPE_CONFIGS.OTHER;
                const Icon = cfg.icon;
                const isIndicator = file.file_type === 'INDICATORS';

                return (
                    <div key={file.id} className="group bg-white rounded-[32px] border border-gray-200 shadow-sm hover:shadow-xl transition-all duration-300 flex flex-col overflow-hidden relative">
                    {/* Checkbox Seleção */}
                    <div className="absolute top-4 left-4 z-10">
                    <input type="checkbox" checked={selectedFiles.includes(file.id)} onChange={() => toggleSelect(file.id)} className="w-5 h-5 rounded-lg border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer" />
                    </div>

                    <div className="p-6 pt-12 flex-grow">
                    <div className={`p-3 rounded-2xl w-fit mb-4 bg-${cfg.color}-50 text-${cfg.color}-600`}>
                    <Icon size={24} />
                    </div>
                    <h3 className="text-sm font-black text-gray-900 line-clamp-1 mb-1">{file.filename.replace(/\.[^/.]+$/, "")}</h3>
                    <p className="text-[10px] text-gray-400 font-bold uppercase mb-4">{cfg.label} • {new Date(file.uploaded_at).toLocaleDateString()}</p>

                    {/* EXIBIÇÃO DE DETALHES TÉCNICOS DA TASK */}
                    {renderTaskSpecs(file)}

                    {/* BOTOES ANALÍTICOS PARA INDICADORES */}
                    {isIndicator && (
                        <div className="flex flex-col gap-2 mt-4">
                        <Link to={`/dashboards/visao-geral?fileId=${file.id}`} className="flex items-center gap-2 p-2 bg-blue-50 text-blue-700 rounded-xl text-[10px] font-black hover:bg-blue-600 hover:text-white transition uppercase tracking-tighter">
                        <FiGlobe size={14}/> Visão Geral
                        </Link>
                        <Link to={`/dashboards/analise-estado?fileId=${file.id}`} className="flex items-center gap-2 p-2 bg-blue-50 text-blue-700 rounded-xl text-[10px] font-black hover:bg-blue-600 hover:text-white transition uppercase tracking-tighter">
                        <FiMap size={14}/> Análise por Estado
                        </Link>
                        <Link to={`/dashboards/analise-municipio?fileId=${file.id}`} className="flex items-center gap-2 p-2 bg-blue-50 text-blue-700 rounded-xl text-[10px] font-black hover:bg-blue-600 hover:text-white transition uppercase tracking-tighter">
                        <FiMapPin size={14}/> Análise por Município
                        </Link>
                        </div>
                    )}
                    </div>

                    {/* AÇÕES PADRÃO NO RODAPÉ DO CARD */}
                    <div className="p-4 bg-gray-50/50 border-t border-gray-100 flex gap-2">
                    <a href={file.file} download className="flex-1 flex items-center justify-center p-2 bg-white border border-gray-200 rounded-xl text-gray-500 hover:text-blue-600 transition shadow-sm" title="Download"><FiDownload size={16} /></a>
                    <button onClick={() => handleDelete(file.id)} className="flex-1 flex items-center justify-center p-2 bg-white border border-gray-200 rounded-xl text-gray-500 hover:text-red-600 transition shadow-sm" title="Remover"><FiTrash2 size={16} /></button>

                    {/* Link de visualização para outros tipos que não sejam indicadores */}
                    {!isIndicator && cfg.path && (() => {
                        const usesTaskId = Boolean(cfg.usesTaskId) || file.file_type === 'RISK_PREDICTION' || file.file_type === 'COST_PREDICTION' || file.file_type === 'DETECCAO_SURTOS' || file.file_type === 'LOS_HIBRIDO' || file.file_type === 'RISK_PRENATAL' || file.file_type === 'INFANT_SURVIVAL' || file.file_type === 'COX_READMISSION' || file.file_type === 'DOENCAS_CRONICAS' || file.file_type === 'POPULATION_SPACE' || file.file_type === 'POP_COMPARE' || file.file_type === 'POP_CAUSAL' || file.file_type === 'POP_ANOMALY' || file.file_type === 'POP_RISK' || file.file_type === 'POP_UNCERTAINTY' || file.file_type === 'POP_CLASSIFY' || file.file_type === 'POP_TRANSITIONS' || file.file_type === 'POP_SURVIVAL' || file.file_type === 'POP_INTERVENE' || file.file_type === 'POP_GRAPH' || file.file_type === 'POP_FACTOR' || file.file_type === 'POP_TOPOLOGY' || file.file_type === 'POP_EARLY_WARNING' || file.file_type === 'POP_GNN' || file.file_type === 'POP_DYNAMICS' || file.file_type === 'POP_PER_CAPITA' || file.file_type === 'POP_MUNICIPIO' || file.file_type === 'POP_NOTIFICACAO' || file.file_type === 'POP_FAMILIA';
                        const param = usesTaskId ? 'taskId' : 'fileId';
                        const value = usesTaskId ? file.task_id : file.id;
                        return (
                            <Link
                                to={`${cfg.path}?${param}=${value}`}
                                className="flex-1 flex items-center justify-center p-2 bg-gray-900 text-white rounded-xl hover:bg-blue-600 transition shadow-md"
                                title="Visualizar Dashboard"
                            >
                                <FiExternalLink size={16} />
                            </Link>
                        );
                    })()}
                    </div>
                    </div>
                );
            })}
            </div>
        )}

        {/* PAGINAÇÃO */}
        {totalPages > 1 && (
            <div className="flex justify-center items-center gap-4 mt-8 pb-12 text-gray-400">
            <button onClick={() => fetchFiles(currentPage - 1)} disabled={currentPage === 1} className="p-3 bg-white border border-gray-200 rounded-xl disabled:opacity-30 hover:bg-gray-50 transition"><FiChevronLeft /></button>
            <span className="text-xs font-black uppercase tracking-widest font-mono">Pág {currentPage} de {totalPages}</span>
            <button onClick={() => fetchFiles(currentPage + 1)} disabled={currentPage === totalPages} className="p-3 bg-white border border-gray-200 rounded-xl disabled:opacity-30 hover:bg-gray-50 transition"><FiChevronRight /></button>
            </div>
        )}
        </div>
    );
};

export default CsvManagerPage;
