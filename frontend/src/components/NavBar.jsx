import React from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function NavBar() {
    const location = useLocation();

    const isActive = (path) => location.pathname.startsWith(path);

    return (
        <aside className="flex flex-col w-64 h-screen bg-blue-700 text-white p-6 fixed">
        <div className="text-3xl font-bold mb-8">LabSUS</div>
        <nav className="flex flex-col gap-4">
        <p className="uppercase text-sm font-semibold mb-2">Orquestrar</p>
        <ul className="flex flex-col gap-2">
        <li>
        <Link
        to="/pipelines/indicadores"
        className={`block px-3 py-2 rounded hover:bg-blue-600 ${
            isActive('/pipelines/indicadores') ? 'bg-blue-800' : ''
        }`}
        >
        Integração de Indicadores
        </Link>
        </li>
        <li>
        <Link
        to="/pipelines/clusters"
        className={`block px-3 py-2 rounded hover:bg-blue-600 ${
            isActive('/pipelines/clusters') ? 'bg-blue-800' : ''
        }`}
        >
        Clusters de Saúde
        </Link>
        </li>
        <li>
        <Link
        to="/pipelines/preditiva"
        className={`block px-3 py-2 rounded hover:bg-blue-600 ${
            isActive('/pipelines/preditiva') ? 'bg-blue-800' : ''
        }`}
        >
        Análises Preditivas
        </Link>
        </li>
        </ul>

        <div className="mt-8">
        <p className="uppercase text-sm font-semibold mb-2">Dashboards</p>
        <ul className="flex flex-col gap-2">
        <li>
        <Link
        to="/dashboards/visao-geral"
        className={`block px-3 py-2 rounded hover:bg-blue-600 ${
            isActive('/dashboards/visao-geral') ? 'bg-blue-800' : ''
        }`}
        >
        Visão Geral
        </Link>
        </li>
        <li>
        <Link
        to="/dashboards/estado"
        className={`block px-3 py-2 rounded hover:bg-blue-600 ${
            isActive('/dashboards/estado') ? 'bg-blue-800' : ''
        }`}
        >
        Análise por Estado
        </Link>
        </li>
        <li>
        <Link
        to="/dashboards/municipio"
        className={`block px-3 py-2 rounded hover:bg-blue-600 ${
            isActive('/dashboards/municipio') ? 'bg-blue-800' : ''
        }`}
        >
        Análise por Município
        </Link>
        </li>
        </ul>
        </div>
        </nav>
        </aside>
    );
}
