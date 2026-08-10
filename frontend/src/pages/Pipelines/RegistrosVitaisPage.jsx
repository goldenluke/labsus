import React, { useState, useEffect } from 'react';
import { FiSearch } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import { getFacilityVitals, getVitalsSummary } from '../../services/registrosVitaisService';

const RegistrosVitaisPage = () => {
    usePageTitle('Registros Vitais (SINASC/SIM)');

    const [summary, setSummary] = useState(null);
    const [summaryError, setSummaryError] = useState(null);

    const [cnes, setCnes] = useState('');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        getVitalsSummary().then(setSummary).catch(err => {
            setSummaryError(err.response?.data?.error || err.message || 'Erro ao carregar panorama nacional.');
        });
    }, []);

    const handleSearch = async () => {
        if (!cnes.trim()) return;
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const data = await getFacilityVitals(cnes.trim());
            setResult(data);
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Erro ao buscar estabelecimento.');
        } finally {
            setLoading(false);
        }
    };

    const revisionRate = summary && summary.total_deaths > 0
        ? (100 * summary.cause_of_death_revisions / summary.total_deaths).toFixed(1)
        : null;

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">
                    Registros Vitais (SINASC/SIM)
                </h1>
                <p className="text-gray-500 mt-2 text-lg">
                    Nascimentos e óbitos reais, direto da BPHO — os dois eventos que o SINASC e o SIM registram.
                </p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="O que é isto">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Cada nascimento vira <code className="mx-1 px-1 bg-gray-100 rounded">Birth</code> (SINASC);
                        cada óbito vira <code className="mx-1 px-1 bg-gray-100 rounded">Death</code> (SIM), com a
                        causa básica codificada — e, quando a causa foi revisada depois da declaração inicial,
                        as duas versões ficam registradas (nunca sobrescritas).
                    </p>
                </InfoCard>

                {summaryError && <FeedbackMessage message={summaryError} type="error" />}
                {summary && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                            <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">Panorama nacional</h2>
                            <div className="grid grid-cols-2 gap-3">
                                <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100">
                                    <div className="text-xs font-black text-emerald-700 uppercase">Nascimentos</div>
                                    <div className="text-2xl font-black text-emerald-700 mt-1">{summary.total_births.toLocaleString('pt-BR')}</div>
                                </div>
                                <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                                    <div className="text-xs font-black text-slate-700 uppercase">Óbitos</div>
                                    <div className="text-2xl font-black text-slate-700 mt-1">{summary.total_deaths.toLocaleString('pt-BR')}</div>
                                </div>
                            </div>
                            {revisionRate && (
                                <p className="text-xs text-gray-400 mt-4">
                                    {summary.cause_of_death_revisions.toLocaleString('pt-BR')} causas básicas de óbito
                                    foram revisadas depois da declaração inicial — {revisionRate}% dos óbitos reais.
                                </p>
                            )}
                        </div>

                        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                            <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">
                                Top-15 causas básicas de óbito (código CID)
                            </h2>
                            <div className="space-y-1 max-h-56 overflow-y-auto pr-2">
                                {summary.top_causes_of_death.map((c, i) => (
                                    <div key={c.icd_code} className="flex items-center justify-between text-sm py-1 border-b border-gray-50 last:border-0">
                                        <span className="font-mono text-gray-500">#{i + 1} {c.icd_code}</span>
                                        <span className="font-black text-gray-700">{c.count.toLocaleString('pt-BR')}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <FiSearch className="text-blue-500" /> Buscar um estabelecimento (CNES)
                    </h2>
                    <div className="flex gap-3">
                        <input
                            type="text"
                            value={cnes}
                            onChange={e => setCnes(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleSearch()}
                            placeholder="Ex: 2495228"
                            className="flex-1 p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm"
                        />
                        <button
                            onClick={handleSearch}
                            disabled={loading || !cnes.trim()}
                            className={`px-5 rounded-xl font-bold text-white transition-all
                                ${loading || !cnes.trim() ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
                        >
                            {loading ? <LoadingSpinner size="sm" color="white" /> : 'Buscar'}
                        </button>
                    </div>

                    {error && <FeedbackMessage message={error} type="error" />}

                    {result && (
                        <div className="mt-4 grid grid-cols-2 gap-4">
                            <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100 text-center">
                                <div className="text-xs font-black text-emerald-700 uppercase">Nascimentos</div>
                                <div className="text-3xl font-black text-emerald-700 mt-1">{result.births}</div>
                            </div>
                            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-center">
                                <div className="text-xs font-black text-slate-700 uppercase">Óbitos</div>
                                <div className="text-3xl font-black text-slate-700 mt-1">{result.deaths}</div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default RegistrosVitaisPage;
