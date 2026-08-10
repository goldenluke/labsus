// src/hooks/useCeleryTaskStatus.js

import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';

// Adicionado 'endpointPrefix' como um argumento.
// Ex: '/api/pipelines/indicadores/tasks/' ou '/api/pipelines/indicadores/integracao/tasks/'
const useCeleryTaskStatus = (taskId, endpointPrefix, pollingInterval = 2000) => {
    const [status, setStatus] = useState('IDLE'); // Começa como 'IDLE' se não há taskId
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const [progress, setProgress] = useState(0);
    const [message, setMessage] = useState('');

    const intervalRef = useRef(null);

    const checkStatus = useCallback(async () => {
        if (!taskId || !endpointPrefix) { // Verifica se endpointPrefix também é fornecido
            clearInterval(intervalRef.current);
            setStatus('IDLE');
            return;
        }

        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.get(`${endpointPrefix}${taskId}/status/`, { // Usa endpointPrefix
                headers: { 'Authorization': `Token ${token}` }
            });
            const data = response.data;
            setStatus(data.status);
            setMessage(data.message || '');

            if (data.status === 'PROGRESS') {
                setProgress(data.progress || 0);
            } else if (data.status === 'SUCCESS') {
                setResult(data.result);
                clearInterval(intervalRef.current);
            } else if (data.status === 'FAILURE' || data.status === 'REVOKED') {
                setError(data.result || data.error || 'Erro desconhecido.');
                clearInterval(intervalRef.current);
            }
        } catch (err) {
            console.error(`Erro ao verificar status da task ${taskId} no endpoint ${endpointPrefix}:`, err);
            setError(`Erro ao verificar status: ${err.response?.data?.error || err.message}`);
            clearInterval(intervalRef.current);
        }
    }, [taskId, endpointPrefix, pollingInterval]); // endpointPrefix adicionado como dependência

    useEffect(() => {
        if (taskId) {
            setStatus('PENDING');
            setResult(null);
            setError(null);
            setProgress(0);
            setMessage('');

            checkStatus(); // Verifica o status imediatamente

            // Inicia o polling
            intervalRef.current = setInterval(checkStatus, pollingInterval);
        } else {
            // Limpa o intervalo se não houver taskId
            clearInterval(intervalRef.current);
            setStatus('IDLE');
        }

        // Limpa o intervalo no unmount
        return () => {
            clearInterval(intervalRef.current);
        };
    }, [taskId, checkStatus, pollingInterval]);

    return {
        status,
        result,
        error,
        progress,
        message,
        isPending: status === 'PENDING' || status === 'STARTED' || status === 'PROGRESS',
        isSuccess: status === 'SUCCESS',
        isFailure: status === 'FAILURE' || status === 'REVOKED',
    };
};

export default useCeleryTaskStatus;
