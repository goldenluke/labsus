import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom';
import {
    FiClock, FiCheckCircle, FiXCircle, FiRefreshCcw, FiExternalLink,
    FiActivity, FiDatabase, FiLayers, FiTrendingUp, FiGitPullRequest,
    FiCrosshair, FiUserCheck, FiInfo, FiSearch, FiFilter
} from 'react-icons/fi';

import usePageTitle from '../hooks/usePageTitle';
import LoadingSpinner from '../components/common/LoadingSpinner';
import FeedbackMessage from '../components/common/FeedbackMessage';

// --- CONFIGURAÇÃO DAS PIPELINES ---
const PIPELINE_CONFIGS = {
    'integracao': {
        label: 'Integração',
        icon: FiDatabase,
        color: 'blue',
        listUrl: '/api/pipelines/indicadores/integracao/tasks/',
        viewerPath: '/dashboards/visao-geral'
    },
    'kmeans': {
        label: 'Perfis (K-Means)',
        icon: FiLayers,
        color: 'purple',
        listUrl: '/api/pipelines/kmeans/tasks/',
        viewerPath: '/dashboards/kmeans-perfis-saude'
    },
    'fluxo': {
        label: 'Fluxo Pacientes',
        icon: FiGitPullRequest,
        color: 'cyan',
        listUrl: '/api/pipelines/fluxo-pacientes/tasks/',
        viewerPath: '/dashboards/fluxo-pacientes'
    },
    'predicao': {
        label: 'Predição Internações',
        icon: FiTrendingUp,
        color: 'indigo',
        listUrl: '/api/pipelines/predicao/internacoes/tasks/',
        viewerPath: '/dashboards/predicao-internacoes'
    },
    'regressao': {
        label: 'Risco de Óbito',
        icon: FiCrosshair,
        color: 'rose',
        listUrl: '/api/pipelines/regressao-obitos/tasks/',
        viewerPath: '/dashboards/regressao-obitos'
    },
    'readmissao': {
        label: 'Risco Readmissão',
        icon: FiUserCheck,
        color: 'emerald',
        listUrl: '/api/pipelines/risco-readmissao/tasks/',
        viewerPath: '/dashboards/risco-readmissao/viewer'
    }
};

const TaskHistoryPage = () => {
    usePageTitle('Histórico de Tarefas');

    const [tasks, setTasks] = useState({});
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('integracao');
    const [searchTerm, setSearchTerm] = useState('');
    const pollingIntervals = useRef({});

    const fetchTasksForType = useCallback(async (type) => {
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.get(PIPELINE_CONFIGS[type].listUrl, {
                headers: { 'Authorization': `Token ${token}` }
            });
            setTasks(prev => ({ ...prev, [type]: response.data }));
        } catch (err) {
            console.error(`Erro ao carregar ${type}:`, err);
        }
    }, []);

    // Carregamento Inicial
    useEffect(() => {
        const loadAll = async () => {
            setLoading(true);
            await Promise.all(Object.keys(PIPELINE_CONFIGS).map(type => fetchTasksForType(type)));
            setLoading(false);
        };
        loadAll();
    }, [fetchTasksForType]);

    // Lógica de Polling para tarefas ativas
    useEffect(() => {
        Object.values(pollingIntervals.current).forEach(clearInterval);

        Object.keys(PIPELINE_CONFIGS).forEach(type => {
            const activeTasks = (tasks[type] || []).filter(t =>
            ['PENDING', 'STARTED', 'PROGRESS'].includes(t.status)
            );

            if (activeTasks.length > 0) {
                pollingIntervals.current[type] = setInterval(() => fetchTasksForType(type), 4000);
            }
        });

        return () => Object.values(pollingIntervals.current).forEach(clearInterval);
    }, [tasks, fetchTasksForType]);

    const getStatusStyle = (status) => {
        switch (status) {
            case 'SUCCESS': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
            case 'FAILURE': return 'bg-red-50 text-red-700 border-red-200';
            case 'PROGRESS':
            case 'STARTED': return 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse';
            default: return 'bg-gray-50 text-gray-500 border-gray-200';
        }
    };

    const getStatusIcon = (status) => {
        switch (status) {
            case 'SUCCESS': return <FiCheckCircle />;
            case 'FAILURE': return <FiXCircle />;
            case 'PROGRESS':
            case 'STARTED': return <FiRefreshCcw className="animate-spin" />;
            default: return <FiClock />;
        }
    };

    const filteredTasks = (tasks[activeTab] || []).filter(t =>
    t.task_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (t.message && t.message.toLowerCase().includes(searchTerm.toLowerCase()))
    );

    const stats = useMemo(() => {
        const all = Object.values(tasks).flat();
        return {
            total: all.length,
            success: all.filter(t => t.status === 'SUCCESS').length,
                          running: all.filter(t => ['PROGRESS', 'STARTED'].includes(t.status)).length
        };
    }, [tasks]);

    return (
        <div className="p-6 bg-gray-50 min-h-screen text-gray-800">
        {/* HEADER COM SUMMARY */}
        <header className="flex flex-col md:flex-row justify-between items-center mb-8 gap-6">
        <div>
        <h1 className="text-3xl font-black text-gray-900 tracking-tight flex items-center gap-3">
        <FiClock className="text-blue-600" /> Centro de <span className="text-blue-600 font-light">Operações</span>
        </h1>
        <p className="text-gray-500 text-sm font-medium mt-1 uppercase tracking-widest font-mono">Monitoramento de Processamento Assíncrono</p>
        </div>

        <div className="flex gap-4">
        <div className="bg-white px-6 py-3 rounded-2xl border border-gray-200 shadow-sm text-center">
        <span className="block text-[10px] font-black text-gray-400 uppercase tracking-widest">Total Análises</span>
        <span className="text-xl font-black text-gray-800">{stats.total}</span>
        </div>
        <div className="bg-white px-6 py-3 rounded-2xl border border-gray-200 shadow-sm text-center">
        <span className="block text-[10px] font-black text-emerald-400 uppercase tracking-widest">Concluídas</span>
        <span className="text-xl font-black text-emerald-600">{stats.success}</span>
        </div>
        <div className="bg-blue-600 px-6 py-3 rounded-2xl text-white shadow-lg text-center">
        <span className="block text-[10px] font-black opacity-60 uppercase tracking-widest">Em Execução</span>
        <span className="text-xl font-black">{stats.running}</span>
        </div>
        </div>
        </header>

        {/* BARRA DE FILTROS E PESQUISA */}
        <div className="bg-white p-4 rounded-3xl border border-gray-200 shadow-sm mb-8 flex flex-col md:flex-row gap-4 items-center">
        <div className="flex-1 relative w-full">
        <FiSearch className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
        type="text"
        placeholder="Buscar por ID ou mensagem da tarefa..."
        className="w-full pl-12 pr-4 py-3 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 transition"
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        />
        </div>
        <div className="flex gap-2 overflow-x-auto pb-2 md:pb-0 w-full md:w-auto scrollbar-hidden">
        {Object.entries(PIPELINE_CONFIGS).map(([key, cfg]) => (
            <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition whitespace-nowrap border-2
                ${activeTab === key
                    ? `bg-${cfg.color}-50 border-${cfg.color}-500 text-${cfg.color}-700`
                    : 'bg-white border-transparent text-gray-500 hover:bg-gray-50'}`}
                    >
                    <cfg.icon /> {cfg.label}
                    </button>
        ))}
        </div>
        </div>

        {/* TABELA DE TAREFAS */}
        <div className="bg-white rounded-[40px] border border-gray-200 shadow-xl overflow-hidden mb-12">
        {loading ? (
            <div className="p-20 text-center"><LoadingSpinner size="lg" /></div>
        ) : filteredTasks.length === 0 ? (
            <div className="p-20 text-center">
            <FiInfo size={48} className="mx-auto text-gray-200 mb-4" />
            <p className="text-gray-400 font-medium">Nenhuma tarefa encontrada para este filtro.</p>
            </div>
        ) : (
            <div className="overflow-x-auto scrollbar-styled">
            <table className="w-full border-collapse">
            <thead>
            <tr className="bg-gray-50 border-b border-gray-100">
            <th className="px-8 py-5 text-left text-[10px] font-black text-gray-400 uppercase tracking-widest">ID / Timestamp</th>
            <th className="px-8 py-5 text-left text-[10px] font-black text-gray-400 uppercase tracking-widest">Status da Operação</th>
            <th className="px-8 py-5 text-left text-[10px] font-black text-gray-400 uppercase tracking-widest">Progresso</th>
            <th className="px-8 py-5 text-left text-[10px] font-black text-gray-400 uppercase tracking-widest">Logs / Mensagens</th>
            <th className="px-8 py-5 text-right text-[10px] font-black text-gray-400 uppercase tracking-widest">Ações</th>
            </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
            {filteredTasks.map((task) => (
                <tr key={task.task_id} className="hover:bg-gray-50/50 transition-colors group">
                <td className="px-8 py-6">
                <div className="font-mono text-xs font-bold text-gray-800 uppercase">{task.task_id.substring(0, 8)}</div>
                <div className="text-[10px] text-gray-400 mt-1">
                {new Date(task.created_at).toLocaleString('pt-BR')}
                </div>
                </td>
                <td className="px-8 py-6">
                <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-black border ${getStatusStyle(task.status)}`}>
                {getStatusIcon(task.status)}
                {task.status}
                </div>
                </td>
                <td className="px-8 py-6">
                <div className="w-full max-w-[100px] bg-gray-100 h-1.5 rounded-full overflow-hidden">
                <div
                className="bg-blue-500 h-full transition-all duration-500"
                style={{ width: `${task.progress || (task.status === 'SUCCESS' ? 100 : 0)}%` }}
                ></div>
                </div>
                <span className="text-[10px] font-bold text-gray-400 mt-1 block">
                {task.progress || (task.status === 'SUCCESS' ? 100 : 0)}%
                </span>
                </td>
                <td className="px-8 py-6">
                <p className="text-xs text-gray-600 font-medium line-clamp-2 max-w-xs" title={task.message}>
                {task.message || 'Sem logs registrados.'}
                </p>
                {task.output_file_filename && (
                    <div className="flex items-center gap-1 mt-1 text-blue-500 text-[10px] font-bold">
                    <FiDatabase size={10}/> {task.output_file_filename}
                    </div>
                )}
                </td>
                <td className="px-8 py-6 text-right">
                {task.output_file_id ? (
                    <Link
                    to={`${PIPELINE_CONFIGS[activeTab].viewerPath}?fileId=${task.output_file_id}`}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-xl text-[10px] font-black hover:bg-blue-600 transition shadow-lg shadow-gray-200"
                    >
                    <FiExternalLink /> ABRIR RESULTADO
                    </Link>
                ) : (
                    <span className="text-[10px] font-bold text-gray-300 italic">Processando...</span>
                )}
                </td>
                </tr>
            ))}
            </tbody>
            </table>
            </div>
        )}
        </div>

        <footer className="mt-20 border-t border-gray-200 py-12 text-center text-gray-400">
        <div className="flex items-center justify-center gap-3 mb-4">
        <FiActivity />
        <span className="text-[10px] font-bold uppercase tracking-[0.4em]">LabSUS Task Manager v2.0</span>
        </div>
        </footer>
        </div>
    );
};

export default TaskHistoryPage;
