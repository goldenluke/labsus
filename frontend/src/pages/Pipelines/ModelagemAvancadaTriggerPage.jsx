import React from 'react';
import { useParams } from 'react-router-dom';

import GenericPipelineTriggerForm from '../../components/modelagem/GenericPipelineTriggerForm';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import { getModelagemSpec } from '../../config/modelagemAvancadaSpec';

const ModelagemAvancadaTriggerPage = () => {
    const { slug } = useParams();
    const config = getModelagemSpec(slug);

    if (!config) {
        return <FeedbackMessage message={`Modelo de Modelagem Avançada não encontrado: "${slug}".`} type="error" />;
    }

    return <GenericPipelineTriggerForm config={config} />;
};

export default ModelagemAvancadaTriggerPage;
