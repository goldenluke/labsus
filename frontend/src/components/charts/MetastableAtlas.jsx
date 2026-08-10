import React from 'react';
import Plot from 'react-plotly.js';

export const Atlas2D = ({ data }) => (
    <Plot
    data={[{
        x: data.map(d => d.H),
                                      y: data.map(d => d.I),
                                      mode: 'markers',
                                      type: 'scatter',
                                      marker: { size: 10, color: data.map(d => d.risk), colorscale: 'Viridis' },
                                      text: data.map(d => d.municipio),
    }]}
    layout={{ title: 'Atlas de Estabilidade (H vs I)', xaxis: {title: 'Complexidade (H)'}, yaxis: {title: 'Estabilidade (I)'}, autosize: true }}
    config={{ responsive: true }}
    style={{ width: '100%', height: '400px' }}
    />
);

export const Atlas3D = ({ data }) => (
    <Plot
    data={[{
        x: data.map(d => d.H),
                                      y: data.map(d => d.I),
                                      z: data.map(d => d.Phi),
                                      mode: 'markers',
                                      type: 'scatter3d',
                                      marker: { size: 4, color: data.map(d => d.risk), colorscale: 'Viridis', opacity: 0.8 },
                                      text: data.map(d => d.municipio),
    }]}
    layout={{
        title: 'Atlas Energético 3D (H, I, Φ)',
                                      scene: { xaxis: {title: 'H'}, yaxis: {title: 'I'}, zaxis: {title: 'Φ'} },
                                      margin: { l: 0, r: 0, b: 0, t: 30 }
    }}
    config={{ responsive: true }}
    style={{ width: '100%', height: '400px' }}
    />
);
