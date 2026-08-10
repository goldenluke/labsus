import React from 'react';
import { Link } from 'react-router-dom';
import { FiActivity, FiBarChart2, FiGlobe, FiTool, FiSettings, FiDatabase, FiClock, FiTrello } from 'react-icons/fi';

import LabSUSLogo from '../assets/lab_icon.png';
import { useAuth } from '../context/AuthContext';
import { getCatalogoPorCategoria } from '../config/pipelineCatalog';

const HomePage = () => {
    const { hasBphoAccess } = useAuth();

    const categorias = getCatalogoPorCategoria(hasBphoAccess);

    const toolsActions = [
        {
            icon: FiTrello,
            title: "Criador de Arquétipos",
            description: "Defina perfis teóricos para rotular automaticamente clusters dos perfis de saúde.",
            path: "/pipelines/arquetipos",
            color: "teal"
        }
    ];

    const managementActions = [
        {
            icon: FiDatabase,
            title: "Banco de Dados (CSV)",
            description: "Gerencie uploads de dados brutos e resultados processados.",
            path: "/csv-manager",
            color: "amber"
        },
        {
            icon: FiClock,
            title: "Histórico de Tarefas",
            description: "Monitore o progresso das pipelines e o status do processamento.",
            path: "/tasks-history",
            color: "slate"
        }
    ];

    const getColorClasses = (color) => {
        const mapping = {
            blue: "text-gray-800 bg-white border border-gray-200/80 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.06)] hover:border-blue-300 hover:bg-gradient-to-br hover:from-blue-50/40 hover:to-white hover:shadow-[0_8px_30px_-6px_rgba(59,130,246,0.18)]",
            purple: "text-gray-800 bg-white border border-gray-200/80 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.06)] hover:border-purple-300 hover:bg-gradient-to-br hover:from-purple-50/40 hover:to-white hover:shadow-[0_8px_30px_-6px_rgba(147,51,234,0.18)]",
            cyan: "text-gray-800 bg-white border border-gray-200/80 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.06)] hover:border-cyan-300 hover:bg-gradient-to-br hover:from-cyan-50/40 hover:to-white hover:shadow-[0_8px_30px_-6px_rgba(6,182,212,0.18)]",
            indigo: "text-gray-800 bg-white border border-gray-200/80 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.06)] hover:border-indigo-300 hover:bg-gradient-to-br hover:from-indigo-50/40 hover:to-white hover:shadow-[0_8px_30px_-6px_rgba(99,102,241,0.18)]",
            emerald: "text-gray-800 bg-white border border-gray-200/80 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.06)] hover:border-emerald-300 hover:bg-gradient-to-br hover:from-emerald-50/40 hover:to-white hover:shadow-[0_8px_30px_-6px_rgba(16,185,129,0.18)]",
            rose: "text-gray-800 bg-white border border-gray-200/80 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.06)] hover:border-rose-300 hover:bg-gradient-to-br hover:from-rose-50/40 hover:to-white hover:shadow-[0_8px_30px_-6px_rgba(244,63,94,0.18)]",
            teal: "text-gray-800 bg-white border border-gray-200/80 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.06)] hover:border-teal-300 hover:bg-gradient-to-br hover:from-teal-50/40 hover:to-white hover:shadow-[0_8px_30px_-6px_rgba(20,184,166,0.18)]",
            amber: "text-gray-800 bg-white border border-gray-200/80 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.06)] hover:border-amber-300 hover:bg-gradient-to-br hover:from-amber-50/40 hover:to-white hover:shadow-[0_8px_30px_-6px_rgba(245,158,11,0.18)]",
            slate: "text-gray-800 bg-white border border-gray-200/80 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.06)] hover:border-slate-300 hover:bg-gradient-to-br hover:from-slate-50/40 hover:to-white hover:shadow-[0_8px_30px_-6px_rgba(100,116,139,0.18)]",
            green: "text-gray-800 bg-white border border-gray-200/80 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.06)] hover:border-green-300 hover:bg-gradient-to-br hover:from-green-50/40 hover:to-white hover:shadow-[0_8px_30px_-6px_rgba(34,197,94,0.18)]",
            red: "text-gray-800 bg-white border border-gray-200/80 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.06)] hover:border-red-300 hover:bg-gradient-to-br hover:from-red-50/40 hover:to-white hover:shadow-[0_8px_30px_-6px_rgba(239,68,68,0.18)]",
            orange: "text-gray-800 bg-white border border-gray-200/80 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.06)] hover:border-orange-300 hover:bg-gradient-to-br hover:from-orange-50/40 hover:to-white hover:shadow-[0_8px_30px_-6px_rgba(249,115,22,0.18)]",
            pink: "text-gray-800 bg-white border border-gray-200/80 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.06)] hover:border-pink-300 hover:bg-gradient-to-br hover:from-pink-50/40 hover:to-white hover:shadow-[0_8px_30px_-6px_rgba(236,72,153,0.18)]",
        };
        return mapping[color] || mapping.blue;
    };

    const getColorIconContainer = (color) => {
        const mapping = {
            blue: "bg-blue-50/60 border-blue-100 group-hover:bg-blue-100/80 group-hover:border-blue-200",
            purple: "bg-purple-50/60 border-purple-100 group-hover:bg-purple-100/80 group-hover:border-purple-200",
            cyan: "bg-cyan-50/60 border-cyan-100 group-hover:bg-cyan-100/80 group-hover:border-cyan-200",
            indigo: "bg-indigo-50/60 border-indigo-100 group-hover:bg-indigo-100/80 group-hover:border-indigo-200",
            emerald: "bg-emerald-50/60 border-emerald-100 group-hover:bg-emerald-100/80 group-hover:border-emerald-200",
            rose: "bg-rose-50/60 border-rose-100 group-hover:bg-rose-100/80 group-hover:border-rose-200",
            teal: "bg-teal-50/60 border-teal-100 group-hover:bg-teal-100/80 group-hover:border-teal-200",
            amber: "bg-amber-50/60 border-amber-100 group-hover:bg-amber-100/80 group-hover:border-amber-200",
            slate: "bg-slate-50/60 border-slate-100 group-hover:bg-slate-100/80 group-hover:border-slate-200",
            green: "bg-green-50/60 border-green-100 group-hover:bg-green-100/80 group-hover:border-green-200",
            red: "bg-red-50/60 border-red-100 group-hover:bg-red-100/80 group-hover:border-red-200",
            orange: "bg-orange-50/60 border-orange-100 group-hover:bg-orange-100/80 group-hover:border-orange-200",
            pink: "bg-pink-50/60 border-pink-100 group-hover:bg-pink-100/80 group-hover:border-pink-200",
        };
        return mapping[color] || mapping.blue;
    };

    const getColorIcon = (color) => {
        const mapping = {
            blue: "text-blue-500 group-hover:text-blue-600",
            purple: "text-purple-500 group-hover:text-purple-600",
            cyan: "text-cyan-500 group-hover:text-cyan-600",
            indigo: "text-indigo-500 group-hover:text-indigo-600",
            emerald: "text-emerald-500 group-hover:text-emerald-600",
            rose: "text-rose-500 group-hover:text-rose-600",
            teal: "text-teal-500 group-hover:text-teal-600",
            amber: "text-amber-500 group-hover:text-amber-600",
            slate: "text-slate-500 group-hover:text-slate-600",
            green: "text-green-500 group-hover:text-green-600",
            red: "text-red-500 group-hover:text-red-600",
            orange: "text-orange-500 group-hover:text-orange-600",
            pink: "text-pink-500 group-hover:text-pink-600",
        };
        return mapping[color] || mapping.blue;
    };

    const renderCards = (items, columns = "lg:grid-cols-4") => (
        <div className={`grid grid-cols-1 md:grid-cols-2 ${columns} gap-6`}>
        {items.map((item, index) => (
            <Link
            to={item.path}
            key={index}
            className={`group p-6 rounded-3xl transition-all duration-300 hover:-translate-y-1 flex flex-col bg-white ${getColorClasses(item.color)}`}
            >
            <div className={`p-3 rounded-2xl w-fit mb-4 group-hover:scale-110 transition-all border shadow-sm ${getColorIconContainer(item.color)}`}>
            <item.icon size={26} className={`${getColorIcon(item.color)} transition-colors`} />
            </div>
            <h3 className="text-lg font-bold text-gray-800 mb-2">{item.title}</h3>
            <p className="text-gray-500 text-xs leading-relaxed flex-grow">{item.description}</p>
            <div className="mt-4 flex items-center text-[10px] font-bold uppercase tracking-wider opacity-0 group-hover:opacity-100 transition-opacity">
            Acessar Módulo →
            </div>
            </Link>
        ))}
        </div>
    );

    // Uma seção por categoria da taxonomia única (técnica/domínio metodológico),
    // não mais uma separação entre pipelines "históricas" e "Modelagem Avançada".
    const renderSection = (title, items, sectionIcon, columns = "lg:grid-cols-4", description) => (
        <div className="mb-12">
        <div className="flex items-center gap-3 mb-2">
        <div className="p-2 bg-gray-100 rounded-lg text-gray-500">
        {sectionIcon}
        </div>
        <h2 className="text-xl font-black text-gray-800 uppercase tracking-widest">{title}</h2>
        </div>
        {description && <p className="text-sm text-gray-400 mb-6 ml-[52px] -mt-1">{description}</p>}
        {!description && <div className="mb-6" />}
        {renderCards(items, columns)}
        </div>
    );

    const colunasPorQuantidade = (n) => {
        if (n >= 5) return 'lg:grid-cols-4';
        if (n >= 3) return 'lg:grid-cols-3';
        if (n === 2) return 'lg:grid-cols-2';
        return 'lg:grid-cols-1';
    };

    return (
        <div className="max-w-7xl mx-auto py-12 px-6">
        {/* Header / Hero */}
        <div className="flex flex-col items-center text-center mb-20">
        <div className="relative mb-6">
        <div className="absolute inset-0 bg-blue-500 blur-3xl opacity-10 rounded-full"></div>
        <img src={LabSUSLogo} alt="LabSUS Logo" className="relative h-28 w-28 drop-shadow-xl" />
        </div>
        <h1 className="text-5xl font-black text-gray-900 tracking-tighter mb-4">
        LabSUS <span className="text-blue-600 font-light">Analytical Hub</span>
        </h1>
        <p className="text-gray-500 text-lg max-w-2xl font-medium italic">
        "Ciência de dados para uma gestão de saúde pública baseada em evidências."
        </p>
        <p className="text-gray-500 text-sm max-w-2xl font-medium">
        ATENÇÃO: Os anos de 2025 e 2026 ainda não foram completamente integralizados. Análises envolvendo esses anos devem ser interpretadas com parcimônia.
        </p>
        </div>

        {/* Banner Informativo */}
        <div className="mb-16 p-8 rounded-[40px] bg-gradient-to-br from-blue-600 to-indigo-700 text-white flex flex-col md:flex-row items-center justify-between gap-6 shadow-2xl">
        <div className="max-w-xl">
        <h3 className="text-2xl font-bold mb-2">
        Repositório de Dados
        </h3>
        <p className="text-blue-100 text-sm leading-relaxed">
        Acesse todos os arquivos processados e realize o download
        de painéis consolidados para uso externo em ferramentas
        como PowerBI ou Qlik.
        </p>
        </div>

        <Link
        to="/csv-manager"
        className="px-8 py-4 bg-white text-blue-600 rounded-2xl font-bold hover:bg-blue-50 transition shadow-lg whitespace-nowrap"
        >
        Explorar Arquivos
        </Link>
        </div>

        {/* Uma seção por categoria da taxonomia única de análises */}
        {categorias.map((categoria) => {
            const items = categoria.pipelines.map((p) => ({
                icon: p.icon,
                title: p.title,
                description: p.descricao,
                path: p.path,
                color: categoria.color,
            }));
            return (
                <div key={categoria.id}>
                {renderSection(
                    categoria.label,
                    items,
                    <categoria.icon />,
                    colunasPorQuantidade(items.length),
                    categoria.descricao
                )}
                </div>
            );
        })}

        {/* Seções Menores (Ajustadas para 2 colunas para não encurtar horizontalmente) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
        <div>
        {renderSection("Ferramentas", toolsActions, <FiTool />, "lg:grid-cols-1")}
        </div>
        <div>
        {renderSection("Gestão do Sistema", managementActions, <FiSettings />, "lg:grid-cols-2")}
        </div>
        </div>


        <footer className="mt-24 py-10 border-t border-gray-200 flex flex-col items-center gap-4">
        <div className="flex gap-6 text-gray-300">
        <FiBarChart2 size={20} />
        <FiActivity size={20} />
        <FiGlobe size={20} />
        </div>
        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-[0.5em]">
        Laboratório de Inteligência em Saúde • 2026
        </p>
        </footer>
        </div>
    );
};

export default HomePage;
