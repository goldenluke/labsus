// src/components/TriggerPipelineButton.jsx
import React from 'react';
import { getCookie } from '../utils/csrf';

function TriggerPipelineButton() {
    const handleClick = async () => {
        const csrftoken = getCookie('csrftoken');
        try {
            const response = await fetch('/api/pipelines/indicadores/trigger/', {
                method: 'POST',
                credentials: 'include', // para enviar cookies
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken,
                },
                body: JSON.stringify({
                    ufs: ['TO'],
                    anos: [2022],
                    arboviroses: ['chikungunya', 'zika'],
                    mortalidade: ['circulatorio', 'neoplasias', 'respiratorias', 'diabetes', 'externas', 'covid19'],
                    indicadores: null,
                }),
            });

            if (!response.ok) {
                throw new Error(`Erro ${response.status}`);
            }

            const data = await response.json();
            console.log('Task disparada com sucesso:', data);
            alert(`Tarefa iniciada! ID da task: ${data.task_id}`);
        } catch (error) {
            console.error('Erro ao disparar a task:', error);
            alert('Falha ao disparar pipeline');
        }
    };

    return <button onClick={handleClick}>Disparar Pipeline Indicadores</button>;
}

export default TriggerPipelineButton;
