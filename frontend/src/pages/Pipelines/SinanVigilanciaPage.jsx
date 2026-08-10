import React, { useState, useEffect } from 'react';
import { FiSearch } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import { getBasesDisponiveis, getVigilanciaSummary, lookupAgravo } from '../../services/sinanVigilanciaService';

const OUTCOME_LABELS = {
    Cure: 'Cura',
    Abandonment: 'Abandono',
    DeathByThisCause: 'Óbito pelo agravo',
    DeathByOtherCause: 'Óbito por outra causa',
    CaseTransfer: 'Transferência',
    _sem_desfecho: 'Sem desfecho estruturado',
};

const OUTCOME_COLORS = {
    Cure: 'bg-emerald-500',
    Abandonment: 'bg-amber-500',
    DeathByThisCause: 'bg-red-600',
    DeathByOtherCause: 'bg-red-300',
    CaseTransfer: 'bg-sky-500',
    _sem_desfecho: 'bg-gray-300',
};

const OutcomeBar = ({ breakdown }) => {
    const total = breakdown._total || Object.entries(breakdown).reduce((s, [k, v]) => k.startsWith('_') ? s : s + v, 0);
    const entries = Object.entries(breakdown).filter(([k]) => k !== '_total');
    if (!total) return null;
    return (
        <div>
            <div className="w-full h-6 rounded-full overflow-hidden flex bg-gray-100">
                {entries.map(([k, v]) => v > 0 && (
                    <div key={k} className={OUTCOME_COLORS[k] || 'bg-gray-400'} style={{ width: `${(100 * v / total).toFixed(2)}%` }} title={`${OUTCOME_LABELS[k] || k}: ${v}`} />
                ))}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mt-3">
                {entries.filter(([, v]) => v > 0).map(([k, v]) => (
                    <div key={k} className="flex items-center gap-2 text-xs">
                        <span className={`w-3 h-3 rounded-full ${OUTCOME_COLORS[k] || 'bg-gray-400'}`}></span>
                        <span className="text-gray-600">{OUTCOME_LABELS[k] || k}</span>
                        <span className="font-black text-gray-800 ml-auto">{v.toLocaleString('pt-BR')} ({(100 * v / total).toFixed(1)}%)</span>
                    </div>
                ))}
            </div>
        </div>
    );
};

const SinanVigilanciaPage = () => {
    usePageTitle('Vigilância SINAN');

    const [bases, setBases] = useState(null);
    const [summary, setSummary] = useState(null);
    const [summaryError, setSummaryError] = useState(null);

    const [code, setCode] = useState('');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        getBasesDisponiveis().then(setBases).catch(() => {});
        getVigilanciaSummary().then(setSummary).catch(err => {
            setSummaryError(err.response?.data?.error || err.message || 'Erro ao carregar panorama nacional.');
        });
    }, []);

    const handleSearch = async () => {
        if (!code.trim()) return;
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const data = await lookupAgravo(code.trim().toUpperCase());
            setResult(data);
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Erro ao buscar agravo.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">
                    Vigilância Epidemiológica (SINAN)
                </h1>
                <p className="text-gray-500 mt-2 text-lg">
                    48 das 49 bases (agravos) reais do SINAN, direto da BPHO — busca por agravo e desfecho de caso.
                </p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="O que é isto">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Cada notificação real vira uma <code className="mx-1 px-1 bg-gray-100 rounded">NotifiableCaseInvestigation</code>,
                        com desfecho (<code className="mx-1 px-1 bg-gray-100 rounded">CaseOutcome</code>) quando um
                        código verificado existe. Duas bases (surto e tracoma) são contagens agregadas, não casos
                        individuais — respondem só com uma contagem, sem desfecho.
                    </p>
                </InfoCard>

                {summaryError && <FeedbackMessage message={summaryError} type="error" />}
                {summary && (
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-2">
                            Panorama nacional — todos os agravos juntos
                        </h2>
                        <p className="text-xs text-gray-400 mb-4">
                            {summary.total_notifiable_case_investigations.toLocaleString('pt-BR')} investigações de caso · {summary.total_aggregate_activities.toLocaleString('pt-BR')} atividades agregadas (surto/tracoma)
                        </p>
                        <OutcomeBar breakdown={summary.outcome_breakdown} />
                    </div>
                )}

                <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                    <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                        <FiSearch className="text-blue-500" /> Buscar por agravo
                    </h2>
                    <div className="flex gap-3">
                        <input
                            type="text"
                            list="agravo-codes"
                            value={code}
                            onChange={e => setCode(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && handleSearch()}
                            placeholder="Ex: TUBE, DENG, CHIK, ZIKA..."
                            className="flex-1 p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm uppercase"
                        />
                        {bases && (
                            <datalist id="agravo-codes">
                                {[...bases.case_bases, ...bases.aggregate_bases].map(c => <option key={c} value={c} />)}
                            </datalist>
                        )}
                        <button
                            onClick={handleSearch}
                            disabled={loading || !code.trim()}
                            className={`px-5 rounded-xl font-bold text-white transition-all
                                ${loading || !code.trim() ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
                        >
                            {loading ? <LoadingSpinner size="sm" color="white" /> : 'Buscar'}
                        </button>
                    </div>
                    <p className="text-xs text-gray-400 mt-2">
                        Consultas por agravo podem levar até ~2 minutos (varredura sem índice de string sobre
                        milhões de casos reais) — mesma latência já esperada no chat da BPHO.
                    </p>

                    {error && <FeedbackMessage message={error} type="error" />}

                    {result && result.is_aggregate && (
                        <div className="mt-4 p-4 bg-gray-50 rounded-xl border border-gray-200 text-center">
                            <p className="text-xs text-gray-400 mb-1">
                                {result.code} é uma ficha AGREGADA (contagem populacional, não caso individual)
                            </p>
                            <div className="text-3xl font-black text-gray-700">{result.total_aggregate_activities.toLocaleString('pt-BR')}</div>
                            <p className="text-xs text-gray-400 mt-1">atividades agregadas reais</p>
                        </div>
                    )}

                    {result && !result.is_aggregate && (
                        <div className="mt-4">
                            <p className="text-xs text-gray-400 mb-3">
                                {result.code} — {(result.outcome_breakdown._total || 0).toLocaleString('pt-BR')} casos reais
                            </p>
                            <OutcomeBar breakdown={result.outcome_breakdown} />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SinanVigilanciaPage;
