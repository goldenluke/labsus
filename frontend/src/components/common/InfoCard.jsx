// === Início do arquivo: src/components/common/InfoCard.jsx (NOVO ARQUIVO) ===

import React from 'react';
import { FiInfo } from 'react-icons/fi';

const InfoCard = ({ title, children }) => {
    return (
        <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg text-gray-800 mb-8">
        <h3 className="font-semibold text-lg flex items-center">
        <FiInfo className="mr-2 flex-shrink-0" />
        {title}
        </h3>
        <div className="text-sm mt-2 space-y-2 pl-6">
        {children}
        </div>
        </div>
    );
};

export default InfoCard;
