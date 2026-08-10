import React from 'react';
import Plot from 'react-plotly.js';

const ResilienceMonitor = ({ score, regime }) => {
    const value = score * 100;
    const color = value < 45 ? "#ef4444" : value < 65 ? "#f59e0b" : "#10b981";

    return (
        <div className="flex flex-col items-center">
        <Plot
        data={[{
            type: "indicator",
            mode: "gauge+number",
            value: value,
            title: { text: `Resiliência: ${regime}`, font: { size: 18 } },
            gauge: {
                axis: { range: [0, 100] },
            bar: { color: "#1f2937" },
            steps: [
                { range: [0, 45], color: "#fee2e2" },
            { range: [45, 65], color: "#fef3c7" },
            { range: [65, 100], color: "#d1fae5" }
            ],
            threshold: {
                line: { color: "black", width: 4 },
            thickness: 0.75,
            value: value
            }
            }
        }]}
        layout={{ width: 300, height: 250, margin: { t: 30, b: 30, l: 30, r: 30 }, paper_bgcolor: "transparent" }}
        config={{ responsive: true, displayModeBar: false }}
        />
        </div>
    );
};

export default ResilienceMonitor;
