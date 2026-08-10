import React, { useState, useEffect } from 'react';
import { FiCpu, FiActivity, FiGlobe } from 'react-icons/fi';
import Atlas3D from '../../components/charts/Atlas3D';
import StructuralDynamicsChart from '../../components/charts/StructuralDynamicsChart';

const MetastableXComplexDashboard = () => {
    const [selectedMun, setSelectedMun] = useState("");
    const [viewMode, setViewMode] = useState("medical"); // 'medical' ou 'scientific'
    const [atlasData, setAtlasData] = useState([]);

    // Controles da Simulação (Sidebar do Streamlit agora no topo ou lateral)
    const [config, setConfig] = useState({ steps: 80, k: 0.3, sigma: 0.01 });

    return (
        <div className="p-6 bg-slate-50 min-h-screen">
        <h1 className="text-3xl font-black text-slate-800 mb-2">MetastableX — Digital Twin</h1>
        <p className="text-slate-500 mb-8">Monitoramento de Dinâmica Não-Linear e Física Estatística do SUS</p>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">

        {/* Painel de Controle Lateral (Antiga Sidebar) */}
        <div className="lg:col-span-1 space-y-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
        <h3 className="font-bold text-slate-700 mb-4 flex items-center gap-2">
        <FiCpu /> Configuração
        </h3>
        <label className="block text-sm font-medium mb-1">Município</label>
        <select className="w-full p-2 border rounded-lg mb-4" value={selectedMun} onChange={e => setSelectedMun(e.target.value)}>
        {/* options de municípios */}
        </select>

        <label className="block text-sm font-medium mb-1">Steps Dinâmica: {config.steps}</label>
        <input type="range" className="w-full mb-4" min="10" max="200" value={config.steps} onChange={e => setConfig({...config, steps: e.target.value})} />

        <button className="w-full py-2 bg-blue-600 text-white rounded-lg font-bold hover:bg-blue-700 transition">
        Simular com Ruído
        </button>
        </div>

        <div className="bg-slate-800 p-6 rounded-2xl text-white">
        <h3 className="font-bold mb-4 flex items-center gap-2"><FiActivity /> Diagnóstico</h3>
        <div className="space-y-4">
        <div>
        <span className="text-xs text-slate-400 uppercase">Regime Atual</span>
        <div className="text-2xl font-black text-cyan-400">METASTÁVEL</div>
        </div>
        <div>
        <span className="text-xs text-slate-400 uppercase">Risco Estrutural</span>
        <div className="text-2xl font-black text-orange-400">0.742</div>
        </div>
        </div>
        </div>
        </div>

        {/* Área Principal de Gráficos */}
        <div className="lg:col-span-3 space-y-6">

        {/* Linha 1: Série Temporal e Dinâmica H/I */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200">
        <h3 className="font-bold text-slate-800 mb-4">Série Temporal (Taxa/10k)</h3>
        <div className="h-[250px]">{/* Gráfico de Linha Recharts ou Plotly */}</div>
        </div>
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200">
        <h3 className="font-bold text-slate-800 mb-4">Evolução de Entropia (H) vs Coerência (I)</h3>
        <StructuralDynamicsChart />
        </div>
        </div>

        {/* Linha 2: Atlas Espaciais */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200">
        <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
        <FiGlobe /> Atlas de Estabilidade (H vs I)
        </h3>
        <div className="h-[400px]">{/* Gráfico 2D Scatter Plotly */}</div>
        </div>
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200">
        <h3 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
        <FiZap /> Atlas Energético 3D (H, I, Φ)
        </h3>
        <Atlas3D data={atlasData} />
        </div>
        </div>

        {/* Explicação Semântica */}
        <AutomatedExplanation
        risk={0.742}
        municipio={selectedMun}
        mode={viewMode}
        />
        </div>
        </div>
        </div>
    );
};

export default MetastableXComplexDashboard;
