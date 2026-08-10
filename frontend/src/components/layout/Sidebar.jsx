import React, { useState } from 'react';
import { NavLink, Link } from 'react-router-dom';
import {
    FiDatabase, FiClock, FiTrello,
    FiLogOut, FiChevronDown,
} from 'react-icons/fi';

import LabSUSLogo from '../../assets/lab_icon.png';
import { useAuth } from '../../context/AuthContext';
import { CATEGORIAS, getCatalogoPorCategoria } from '../../config/pipelineCatalog';

const menuGroupsEstaticos = [
    {
        title: "Gestão",
        items: [
            { path: "/csv-manager", label: "Banco de Dados", icon: FiDatabase },
            { path: "/tasks-history", label: "Histórico", icon: FiClock },
        ]
    },
    {
        title: "Ferramentas",
        items: [
            { path: "/pipelines/arquetipos", label: "Arquétipos", icon: FiTrello },
        ]
    },
];

const Sidebar = ({ isOpen, onLinkClick, handleLogout }) => {

    const { hasBphoAccess } = useAuth();
    // Todas as categorias começam recolhidas — com 13 categorias cobrindo
    // ~65 pipelines, mostrar tudo expandido de cara tornaria a busca mais
    // difícil, não mais fácil.
    const [colapsados, setColapsados] = useState(() => Object.fromEntries(CATEGORIAS.map((c) => [c.label, true])));

    // Uma única taxonomia de análises (não mais "pipelines antigas" vs.
    // "Modelagem Avançada") — cada categoria já vem filtrada pelo acesso do
    // usuário, direto do catálogo compartilhado com a HomePage.
    const categoriasAnalises = getCatalogoPorCategoria(hasBphoAccess).map((categoria) => ({
        title: categoria.label,
        collapsible: true,
        icon: categoria.icon,
        items: categoria.pipelines.map((p) => ({ path: p.path, label: p.title, icon: p.icon })),
    }));

    const visibleMenuGroups = [
        menuGroupsEstaticos[0],
        ...categoriasAnalises,
        menuGroupsEstaticos[1],
    ];

    const toggleColapso = (titulo) => setColapsados(prev => ({ ...prev, [titulo]: !prev[titulo] }));

    const activeClass = "bg-blue-600 text-white shadow-lg shadow-blue-200";
    const inactiveClass = "text-gray-500 hover:bg-gray-100 hover:text-blue-600";

    return (
        <>
        {isOpen && (
            <div
            className="fixed inset-0 bg-gray-900/20 backdrop-blur-sm z-40 md:hidden"
            onClick={onLinkClick}
            ></div>
        )}

        <aside className={`
            fixed top-0 left-0 h-screen w-64 bg-white border-r border-gray-200 z-50
            transition-all duration-300 ease-in-out flex flex-col
            ${isOpen ? 'translate-x-0' : '-translate-x-full'}
            md:translate-x-0 md:sticky
            `}>

            {/* HEADER */}
            <div className="h-20 flex items-center justify-between border-b border-gray-50 px-4">
                <Link to="/inicio" onClick={onLinkClick} className="flex items-center gap-3 overflow-hidden">
                <img src={LabSUSLogo} alt="Logo" className="h-8 w-8 shrink-0 shadow-sm rounded-lg" />
                <span className="font-black text-xl tracking-tighter text-gray-800 whitespace-nowrap">
                Lab<span className="text-blue-600">SUS</span>
                </span>
                </Link>
                </div>

                    {/* MENU */}
                    <nav className="flex-grow overflow-y-auto py-6 px-3">
                    {visibleMenuGroups.map((group, gIdx) => {
                        const estaColapsado = group.collapsible && colapsados[group.title];
                        return (
                        <div key={gIdx} className="mb-6">

                        {group.collapsible ? (
                            <button
                            type="button"
                            onClick={() => toggleColapso(group.title)}
                            className="w-full flex items-center gap-2 px-4 mb-3 group"
                            >
                            {group.icon && <group.icon size={12} className="text-gray-300 shrink-0" />}
                            <h3 className="flex-grow text-left text-[9px] font-black text-gray-400 uppercase tracking-[0.15em] group-hover:text-blue-500 truncate">
                            {group.title}
                            </h3>
                            <FiChevronDown
                            size={12}
                            className={`text-gray-400 transition-transform shrink-0 ${estaColapsado ? '-rotate-90' : ''}`}
                            />
                            </button>
                        ) : (
                            <h3 className="px-4 text-[9px] font-black text-gray-400 uppercase tracking-[0.2em] mb-3">
                            {group.title}
                            </h3>
                        )}

                        {!estaColapsado && (
                            <ul className="space-y-1">
                            {group.items.map((item, iIdx) => (
                                <li key={iIdx}>
                                <NavLink
                                to={item.path}
                                onClick={onLinkClick}
                                title={item.label}
                                className={({ isActive }) => `
                                flex items-center gap-4 px-4 py-2.5 rounded-2xl font-bold text-xs transition-all duration-200
                                ${isActive ? activeClass : inactiveClass}
                                `}
                                >
                                <item.icon size={18} className="shrink-0" />
                                <span className="truncate">{item.label}</span>
                                </NavLink>
                                </li>
                            ))}
                            </ul>
                        )}

                        </div>
                        );
                    })}
                    </nav>

                    {/* LOGOUT */}
                    <div className="p-4 border-t border-gray-100">
                    <button
                    onClick={handleLogout}
                    className="flex items-center gap-4 w-full px-4 py-3 rounded-2xl font-black text-xs uppercase tracking-widest text-red-500 hover:bg-red-50 transition-colors"
                        >
                        <FiLogOut size={20} />
                        <span>Sair</span>
                        </button>
                        </div>

                        </aside>
                        </>
    );
};

export default Sidebar;
