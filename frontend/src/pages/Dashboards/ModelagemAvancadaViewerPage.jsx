import React from 'react';
import { useParams } from 'react-router-dom';

import GenericResultsViewer from '../../components/modelagem/GenericResultsViewer';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import { getModelagemSpec } from '../../config/modelagemAvancadaSpec';

const ModelagemAvancadaViewerPage = () => {
    const { slug } = useParams();
    const config = getModelagemSpec(slug);

    if (!config) {
        return <FeedbackMessage message={`Modelo de Modelagem Avançada não encontrado: "${slug}".`} type="error" />;
    }

    return <GenericResultsViewer config={config} />;
};

export default ModelagemAvancadaViewerPage;
