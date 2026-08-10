// src/components/layout/DashboardLayout.jsx

import React from 'react';

const DashboardLayout = ({ title, controls, children, isLoading, errorMessage, feedbackMessage }) => {
    return (
        <div className="p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl font-bold text-center text-gray-800 mb-8">
        {title}
        </h1>

        {controls && (
            <div className="bg-white p-6 rounded-lg shadow-md mb-8 flex flex-wrap gap-4 items-center justify-center">
            {controls}
            </div>
        )}

        {/* Mensagens de feedback globais */}
        {isLoading && <p className="text-xl text-center text-gray-700 mt-8">A carregar dados...</p>}
        {errorMessage && <p className="text-xl text-center text-red-500 mt-8">{errorMessage}</p>}
        {feedbackMessage && <p className="text-xl text-center text-gray-700 mt-8">{feedbackMessage}</p>}

        {/* Renderiza os filhos apenas se não houver loading ou erro global */}
        {!isLoading && !errorMessage && !feedbackMessage && (
            <div className="grid grid-cols-1 gap-6 mt-6"> {/* Grid principal para os gráficos */}
            {children}
            </div>
        )}
        </div>
    );
};

export default DashboardLayout;
