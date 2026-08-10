// src/components/common/TabButtons.jsx

import React from 'react';

const TabButtons = ({ activeTab, setActiveTab, tabs }) => {
    // Adiciona uma verificação para garantir que 'tabs' seja um array
    if (!Array.isArray(tabs)) {
        return null; // Não renderiza nada se a prop 'tabs' não for um array
    }

    return (
        <div className="flex justify-center mb-4 space-x-2 md:space-x-4 flex-wrap">
        {tabs.map((tab) => (
            <button
            key={tab.id}
            className={`px-4 py-2 my-1 rounded-md font-semibold transition-colors duration-200
                ${activeTab === tab.id
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }
                ${tab.disabled ? 'opacity-50 cursor-not-allowed' : ''}
                `}
                onClick={() => setActiveTab(tab.id)}
                disabled={tab.disabled || false}
                >
                {tab.label}
                </button>
        ))}
        </div>
    );
};

export default TabButtons;
