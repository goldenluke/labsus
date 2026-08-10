// src/components/common/LoadingSpinner.jsx (Crie este arquivo)

import React from 'react';

const LoadingSpinner = ({ size = 'md', color = 'blue' }) => {
    const spinnerSize = {
        'sm': 'w-4 h-4',
        'md': 'w-8 h-8',
        'lg': 'w-12 h-12',
    }[size];

    const spinnerColor = {
        'blue': 'border-blue-500',
        'gray': 'border-gray-500',
        'white': 'border-white',
    }[color];

    return (
        <div className="flex justify-center items-center">
        <div
        className={`inline-block animate-spin rounded-full border-4 border-solid border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite] ${spinnerSize} ${spinnerColor}`}
        role="status"
        >
        <span className="!absolute !-m-px !h-px !w-px !overflow-hidden !whitespace-nowrap !border-0 !p-0 ![clip:rect(0,0,0,0)]">
        Loading...
        </span>
        </div>
        </div>
    );
};

export default LoadingSpinner;
