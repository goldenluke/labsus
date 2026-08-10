// src/components/common/FeedbackMessage.jsx

import React from 'react';

const TYPE_STYLES = {
    error: 'bg-red-100 text-red-800',
    info: 'bg-blue-100 text-blue-800',
    loading: 'bg-yellow-100 text-yellow-800',
};

const FeedbackMessage = ({ message, type = 'info' }) => {
    if (!message) return null;
    const style = TYPE_STYLES[type] || TYPE_STYLES.info;
    return (
        <div className={`text-center p-4 ${style} rounded-lg shadow-md mb-8`}>
            {message}
        </div>
    );
};

export default FeedbackMessage;
