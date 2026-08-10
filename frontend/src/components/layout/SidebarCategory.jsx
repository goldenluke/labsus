// === Início do arquivo: src/components/layout/SidebarCategory.jsx (VERSÃO FINAL CORRIGIDA) ===

import React, { useState } from 'react'; // Import useState do React
import { NavLink } from 'react-router-dom';
import { FiChevronDown, FiChevronUp } from 'react-icons/fi';

const SidebarCategory = ({ title, icon: TitleIcon, links, isCompact, getNavLinkClass, onLinkClick }) => {

    // --- CORREÇÃO APLICADA AQUI ---
    // Todos os Hooks devem ser chamados no nível superior do componente,
    // incondicionalmente.
    const [isAccordionOpen, setAccordionOpen] = useState(false);

    // --- MODO EXPANDIDO (agora sem erro de hook) ---
    if (!isCompact) {
        return (
            <li className="mb-2">
            <button
            className="flex items-center justify-between w-full px-4 py-2 text-sm font-semibold text-gray-300 rounded-md hover:bg-gray-700 transition-colors duration-200"
            onClick={() => setAccordionOpen(!isAccordionOpen)}
            >
            <span className="flex items-center">
            {TitleIcon && <TitleIcon className="inline-block mr-3 text-lg" />}
            {title}
            </span>
            {isAccordionOpen ? <FiChevronUp className="text-lg" /> : <FiChevronDown className="text-lg" />}
            </button>
            {isAccordionOpen && (
                <ul className="ml-6 mt-2 space-y-1">
                {links.map((link, index) => (
                    <li key={index}>
                    <NavLink to={link.path} className={getNavLinkClass} onClick={onLinkClick}>
                    {link.icon && <link.icon className="inline-block mr-3 text-lg" />}
                    <span>{link.label}</span>
                    </NavLink>
                    </li>
                ))}
                </ul>
            )}
            </li>
        );
    }

    // --- MODO COMPACTO (com a lógica de hover puramente em CSS via 'group') ---
    return (
        <li className="relative group">

        <div className="flex items-center justify-center w-full px-4 py-2 text-lg font-semibold text-gray-300 rounded-md cursor-pointer group-hover:bg-gray-700">
        {TitleIcon && <TitleIcon />}
        </div>

        <div className="
        absolute left-full top-0 ml-2 z-50 w-56
        bg-gray-800 rounded-md shadow-lg p-2
        opacity-0 invisible group-hover:opacity-100 group-hover:visible
        transition-all duration-200
        ">
        <div className="px-4 py-2 text-sm font-bold text-white border-b border-gray-700 mb-2">
        {title}
        </div>
        <ul className="space-y-1">
        {links.map((link, index) => (
            <li key={index}>
            <NavLink
            to={link.path}
            className={getNavLinkClass}
            onClick={onLinkClick}
            >
            {link.icon && <link.icon className="inline-block mr-3 text-lg" />}
            <span>{link.label}</span>
            </NavLink>
            </li>
        ))}
        </ul>
        </div>
        </li>
    );
};

export default SidebarCategory;
