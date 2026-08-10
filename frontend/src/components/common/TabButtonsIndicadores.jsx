// src/components/common/TabButtonsIndicadores.jsx

import React from 'react';

const TabButtonsIndicadores = ({ activeTab, setActiveTab, tabs }) => {
    return (
        <div className="flex justify-center mb-4 space-x-4">
        {tabs.map((tab) => (
            <button
            key={tab.id}
            className={`px-4 py-2 rounded-md ${activeTab === tab.id ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
            onClick={() => setActiveTab(tab.id)}
            // Para dashboards de indicadores, as abas geralmente estão sempre habilitadas
            // Se o conteúdo da aba não tiver dados, a própria aba de conteúdo exibirá uma mensagem.
            // Não há lógica complexa de desabilitar por 'availableYears' ou 'availableUfs' aqui.
            disabled={false}
            >
            {tab.label}
            </button>
        ))}
        </div>
    );
};

export default TabButtonsIndicadores;
