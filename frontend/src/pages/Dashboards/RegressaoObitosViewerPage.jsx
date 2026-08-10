import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';
import { useLocation } from 'react-router-dom';
import usePageTitle from '../../hooks/usePageTitle';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import InfoCard from '../../components/common/InfoCard';
import { FiDownload } from 'react-icons/fi';

// Mapeamentos para transformar os códigos em texto legível
const mapeamentos = {
    MORTE: { 0: 'Alta', 1: 'Óbito' },
    SEXO: { '1': 'Masculino', '3': 'Feminino', '9': 'Ignorado' },
    CAR_INT: { '1': 'Eletivo', '2': 'Urgência', '3': 'Acidente Trabalho', '4': 'Outro Acidente', '5': 'Outros' },
    RACA_COR: { '1': 'Branca', '2': 'Preta', '3': 'Parda', '4': 'Amarela', '5': 'Indígena', '99': 'Ignorado' },
    TEM_COMORBIDADE: { 0: 'Não', 1: 'Sim' },
};

// Mapeamento para os nomes das features do modelo de regressão
const featureNameMap = {
    'IDADE': 'Idade',
    'TEM_COMORBIDADE': 'Presença de Diagnóstico Secundário',
    'SEXO_3': 'Sexo: Feminino',
    'CAR_INT_02': 'Caráter: Urgência',
    'CAR_INT_03': 'Caráter: Acidente de Trabalho',
    'CAR_INT_04': 'Caráter: Acidente de Trajeto',
    'CAR_INT_05': 'Caráter: Outros Acidentes de Trânsito',
    'CAR_INT_06': 'Caráter: Outras Lesões/Envenenamentos',
    'RACA_COR_02': 'Raça/Cor: Preta',
    'RACA_COR_03': 'Raça/Cor: Parda',
    'RACA_COR_04': 'Raça/Cor: Amarela',
    'RACA_COR_05': 'Raça/Cor: Indígena',
    'RACA_COR_99': 'Raça/Cor: Ignorado',
};


const RegressaoObitosViewerPage = () => {
    usePageTitle('Dashboard de Risco de Óbito');

    const location = useLocation();
    const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
    const fileIdFromUrl = queryParams.get('fileId');

    const [analysisData, setAnalysisData] = useState([]);
    const [fileDetails, setFileDetails] = useState(null);
    const [taskSummary, setTaskSummary] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!fileIdFromUrl) {
            setError("Nenhum arquivo selecionado.");
            setLoading(false);
            return;
        }
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                const token = localStorage.getItem('authToken');
                const [detailsRes, dataRes, tasksRes] = await Promise.all([
                    axios.get(`/api/files/${fileIdFromUrl}/`, { headers: { 'Authorization': `Token ${token}` } }),
                                                                          axios.get(`/api/files/${fileIdFromUrl}/data/`, { headers: { 'Authorization': `Token ${token}` } }),
                                                                          axios.get(`/api/pipelines/regressao-obitos/tasks/`, { headers: { 'Authorization': `Token ${token}` } })
                ]);

                setFileDetails(detailsRes.data);

                const rawData = dataRes.data;
                const processedData = rawData.map(item => {
                    const newItem = { ...item };
                    for (const key in newItem) {
                        if (['IDADE', 'MORTE_REAL', 'TEM_COMORBIDADE', 'MORTE_PREDITA', 'PROBABILIDADE_OBITO'].includes(key)) {
                            newItem[key] = parseFloat(String(newItem[key]).replace(',', '.'));
                        }
                    }
                    return newItem;
                });
                setAnalysisData(processedData);

                const correspondingTask = tasksRes.data.find(task => task.output_file_id === parseInt(fileIdFromUrl));
                if (correspondingTask) {
                    setTaskSummary(correspondingTask.results_summary);
                }

            } catch (err) {
                setError("Não foi possível carregar os dados da análise.");
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [fileIdFromUrl]);

    // Lógicas dos gráficos (useMemo)
    const idadePlotData = useMemo(() => {
        if (!analysisData.length) return [];
        const altaData = analysisData.filter(d => d.MORTE_REAL === 0).map(d => d.IDADE);
        const obitoData = analysisData.filter(d => d.MORTE_REAL === 1).map(d => d.IDADE);
        return [
            { y: altaData, type: 'violin', name: 'Alta', box: { visible: true }, meanline: { visible: true }, marker: { color: '#1f77b4' } },
            { y: obitoData, type: 'violin', name: 'Óbito', box: { visible: true }, meanline: { visible: true }, marker: { color: '#d62728' } }
        ];
    }, [analysisData]);

    const createGroupedBarData = (field, mapping) => {
        if (!analysisData.length) return [];
        const counts = {};
        for (const item of analysisData) {
            const category = item[field];
            const outcome = item.MORTE_REAL;
            if(category === undefined || outcome === undefined) continue;
            if (!counts[category]) counts[category] = { 0: 0, 1: 0 };
            counts[category][outcome]++;
        }
        const categories = Object.keys(counts).sort();
        const labels = categories.map(c => mapping[c] || c);

        return [
            { x: labels, y: categories.map(c => counts[c][0]), name: 'Alta', type: 'bar', marker: { color: '#1f77b4' } },
            { x: labels, y: categories.map(c => counts[c][1]), name: 'Óbito', type: 'bar', marker: { color: '#d62728' } }
        ];
    };

    const sexoPlotData = useMemo(() => createGroupedBarData('SEXO', mapeamentos.SEXO), [analysisData]);
    const carIntPlotData = useMemo(() => createGroupedBarData('CAR_INT', mapeamentos.CAR_INT), [analysisData]);
    const racaCorPlotData = useMemo(() => createGroupedBarData('RACA_COR', mapeamentos.RACA_COR), [analysisData]);
    const comorbidadePlotData = useMemo(() => createGroupedBarData('TEM_COMORBIDADE', mapeamentos.TEM_COMORBIDADE), [analysisData]);

    const oddsRatioPlotData = useMemo(() => {
        if (!taskSummary?.coefficients) return null;

        const coefs = taskSummary.coefficients['Chance (Odds Ratio)'];

        const data = Object.entries(coefs).map(([feature, value]) => {
            let label = featureNameMap[feature] || feature;

            const comorbMatch = feature.match(/TEM_COMORB_(.*)/);
            if (comorbMatch && comorbMatch[1]) {
                label = `Comorbidade (${comorbMatch[1]})`;
            }

            return { feature: label, value };
        });

        data.sort((a, b) => a.value - b.value);

        return [{
            x: data.map(d => d.value),
                                      y: data.map(d => d.feature),
                                      type: 'bar',
                                      orientation: 'h',
                                      marker: {
                                          color: data.map(d => d.value > 1 ? '#d62728' : '#2ca02c')
                                      }
        }];
    }, [taskSummary]);

    const probabilityPlotData = useMemo(() => {
        if (!analysisData.length) return null;
        const altaProbs = analysisData.filter(d => d.MORTE_REAL === 0).map(d => d.PROBABILIDADE_OBITO);
        const obitoProbs = analysisData.filter(d => d.MORTE_REAL === 1).map(d => d.PROBABILIDADE_OBITO);
        return [
            { x: altaProbs, type: 'histogram', name: 'Real: Alta', opacity: 0.75, marker: { color: '#1f77b4' } },
            { x: obitoProbs, type: 'histogram', name: 'Real: Óbito', opacity: 0.75, marker: { color: '#d62728' } }
        ];
    }, [analysisData]);

    const confusionMatrixData = useMemo(() => {
        if (!analysisData.length) return null;
        const TP = analysisData.filter(d => d.MORTE_REAL === 1 && d.MORTE_PREDITA === 1).length;
        const TN = analysisData.filter(d => d.MORTE_REAL === 0 && d.MORTE_PREDITA === 0).length;
        const FP = analysisData.filter(d => d.MORTE_REAL === 0 && d.MORTE_PREDITA === 1).length;
        const FN = analysisData.filter(d => d.MORTE_REAL === 1 && d.MORTE_PREDITA === 0).length;
        return {
            z: [[TN, FP], [FN, TP]],
            x: ['Previsto: Alta', 'Previsto: Óbito'],
            y: ['Real: Alta', 'Real: Óbito'],
            text: [[`VN: ${TN}`, `FP: ${FP}`], [`FN: ${FN}`, `VP: ${TP}`]],
        };
    }, [analysisData]);

    const rocCurveData = useMemo(() => {
        if (!analysisData.length) return null;
        const points = analysisData.map(d => ({ prob: d.PROBABILIDADE_OBITO, real: d.MORTE_REAL }));
        points.sort((a, b) => b.prob - a.prob);

        const totalPos = points.filter(p => p.real === 1).length;
        const totalNeg = points.length - totalPos;
        if(totalPos === 0 || totalNeg === 0) return null;

        let tp = 0, fp = 0;
        const tpr = [0], fpr = [0];

        for (const p of points) {
            if (p.real === 1) tp++; else fp++;
            tpr.push(tp / totalPos);
            fpr.push(fp / totalNeg);
        }

        return [
            { x: fpr, y: tpr, type: 'scatter', mode: 'lines', name: 'Curva ROC', line: { color: '#1f77b4', width: 3 } },
            { x: [0, 1], y: [0, 1], type: 'scatter', mode: 'lines', name: 'Aleatório', line: { color: 'grey', dash: 'dash' } }
        ];
    }, [analysisData]);


    let feedbackMessage = null;
    if (loading) feedbackMessage = <FeedbackMessage message="Carregando dados da análise..." />;
    else if (error) feedbackMessage = <FeedbackMessage message={`Erro: ${error}`} type="error" />;
    else if (analysisData.length === 0) feedbackMessage = <FeedbackMessage message="O arquivo de análise está vazio ou não contém dados válidos." type="info" />;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
        <h1 className="text-3xl text-center text-gray-800 mb-8">
        Dashboard - Análise de Risco de Óbito
        </h1>
        {feedbackMessage}
        {!feedbackMessage && fileDetails && (
            <>
            <div className="bg-white p-6 rounded-lg shadow-md mb-8 flex flex-col md:flex-row justify-between items-start md:items-center">
            <div>
            <h2 className="text-xl font-semibold text-gray-800 mb-2">Arquivo de Análise:</h2>
            <p className="text-gray-700 text-sm mb-1"><span className="font-medium">Nome:</span> {fileDetails.filename}</p>
            <p className="text-gray-700 text-sm mt-2"><span className="font-medium">Parâmetros:</span> {fileDetails.description}</p>
            </div>
            <a href={fileDetails.file} download={fileDetails.filename} className="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded inline-flex items-center flex-shrink-0 mt-4 md:mt-0">
            <FiDownload className="mr-2" /> Baixar CSV
            </a>
            </div>

            <h2 className="text-2xl font-bold text-gray-800 mb-4 border-b pb-2">Avaliação do Modelo Preditivo</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-6">
            <div className="space-y-4">
            <InfoCard title="Fatores de Risco (Odds Ratios)">
            <p>Este gráfico mostra o impacto de cada variável no risco de óbito. Barras vermelhas (valor &gt; 1) indicam fatores de risco. Barras verdes (valor &le; a 1) indicam fatores de proteção. A linha em '1.0' representa nenhum efeito.</p>
            </InfoCard>
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            {oddsRatioPlotData ? <Plot data={oddsRatioPlotData} layout={{ title: 'Importância de Cada Fator de Risco', xaxis: { title: 'Odds Ratio (Chance)' }, yaxis: { automargin: true }, shapes: [{type: 'line', x0: 1, y0: -1, x1: 1, y1: oddsRatioPlotData[0].y.length, line: {color: 'grey', width: 2, dash: 'dash'}}] }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p>Resumo da tarefa não encontrado para exibir os fatores de risco.</p>}
            </div>
            </div>

            <div className="space-y-4">
            <InfoCard title="Distribuição das Probabilidades Previstas">
            <p>O ideal é que as duas curvas (Alta e Óbito) estejam bem separadas. Uma grande sobreposição indica que o modelo tem dificuldade em distinguir os dois grupos.</p>
            </InfoCard>
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            {probabilityPlotData ? <Plot data={probabilityPlotData} layout={{ title: 'Distribuição da Probabilidade de Óbito', barmode: 'overlay', xaxis: { title: 'Probabilidade de Óbito Prevista (%)' }, yaxis: { title: 'Contagem de Pacientes' } }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p>Dados indisponíveis.</p>}
            </div>
            </div>

            <div className="space-y-4">
            <InfoCard title="Matriz de Confusão">
            <p>A matriz mostra os acertos e erros do modelo. O erro mais crítico é o "Falso Negativo" (FN), onde o modelo previu alta mas o paciente foi a óbito.</p>
            <ul className="list-disc list-inside text-sm mt-1">
            <li><b>VN:</b> Previu Alta e acertou.</li>
            <li><b>VP:</b> Previu Óbito e acertou.</li>
            <li><b>FP:</b> Previu Óbito e errou.</li>
            <li><b>FN:</b> Previu Alta e errou.</li>
            </ul>
            </InfoCard>
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            {confusionMatrixData ? <Plot data={[{...confusionMatrixData, type: 'heatmap', colorscale: 'Veridis', showscale: false}]} layout={{ title: 'Matriz de Confusão', annotations: confusionMatrixData.text.flatMap((row, i) => row.map((text, j) => ({ x: confusionMatrixData.x[j], y: confusionMatrixData.y[i], text: text, showarrow: false, font:{color:'black', size: 16} }))) }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p>Dados indisponíveis.</p>}
            </div>
            </div>

            <div className="space-y-4">
            <InfoCard title="Curva ROC e AUC">
            <p>A curva ROC avalia a performance geral do modelo. Quanto mais a linha azul se aproxima do canto superior esquerdo, melhor. O valor <b>AUC</b> (Área Sob a Curva) resume isso em um número (quanto mais perto de 1.0, melhor).</p>
            </InfoCard>
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            {rocCurveData ? <Plot data={rocCurveData} layout={{ title: `Curva ROC (AUC = ${taskSummary?.auc.toFixed(4) || 'N/A'})`, xaxis: { title: 'Taxa de Falsos Positivos' }, yaxis: { title: 'Taxa de Verdadeiros Positivos' }, showlegend: false }} config={{ responsive: true, displayModeBar: false }} className="w-full h-full" /> : <p>Dados indisponíveis.</p>}
            </div>
            </div>
            </div>

            <h2 className="text-2xl font-bold text-gray-800 mb-4 border-b pb-2 mt-12">Análise Exploratória dos Dados de Treinamento</h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-6">
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            <h2 className="text-xl font-semibold text-center text-gray-700 mb-4">Distribuição de Idade por Desfecho</h2>
            <Plot data={idadePlotData} layout={{ yaxis: { title: 'Idade' }, showlegend: true, legend: {orientation: 'h'} }} config={{ responsive: true, displayModeBar: false }} className="w-full h-[calc(100%-40px)]" />
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            <h2 className="text-xl font-semibold text-center text-gray-700 mb-4">Contagem de Desfechos por Sexo</h2>
            <Plot data={sexoPlotData} layout={{ barmode: 'group', yaxis: { title: 'Contagem' }, legend: {orientation: 'h'} }} config={{ responsive: true, displayModeBar: false }} className="w-full h-[calc(100%-40px)]" />
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            <h2 className="text-xl font-semibold text-center text-gray-700 mb-4">Desfechos por Caráter da Internação</h2>
            <Plot data={carIntPlotData} layout={{ barmode: 'group', yaxis: { title: 'Contagem' }, legend: {orientation: 'h'} }} config={{ responsive: true, displayModeBar: false }} className="w-full h-[calc(100%-40px)]" />
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full">
            <h2 className="text-xl font-semibold text-center text-gray-700 mb-4">Contagem de Desfechos por Raça/Cor</h2>
            <Plot data={racaCorPlotData} layout={{ barmode: 'group', yaxis: { title: 'Contagem' }, legend: {orientation: 'h'} }} config={{ responsive: true, displayModeBar: false }} className="w-full h-[calc(100%-40px)]" />
            </div>
            <div className="bg-white p-4 rounded-lg shadow-md h-[500px] w-full lg:col-span-2">
            <h2 className="text-xl font-semibold text-center text-gray-700 mb-4">Desfechos por Presença de Comorbidade</h2>
            <Plot data={comorbidadePlotData} layout={{ barmode: 'group', yaxis: { title: 'Contagem' }, legend: {orientation: 'h'} }} config={{ responsive: true, displayModeBar: false }} className="w-full h-[calc(100%-40px)]" />
            </div>
            </div>
            </>
        )}
        </div>
    );
};

export default RegressaoObitosViewerPage;
