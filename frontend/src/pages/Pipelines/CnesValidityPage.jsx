import React, { useState, useEffect } from 'react';
import { FiSearch, FiShield } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import { getFacilityValidity, getValiditySummary } from '../../services/cnesValidityService';

const KIND_LABELS = {
    ServiceQualification: 'Habilitação de serviço',
    ManagementGoal: 'Meta de gestão',
    FinancialIncentive: 'Incentivo financeiro',
    ContractualRule: 'Regra contratual',
    PhilanthropicStatus: 'Estabelecimento filantrópico',
    TeachingFacilityStatus: 'Estabelecimento de ensino',
};

const KIND_COLORS = {
    ServiceQualification: 'bg-blue-50 border-blue-100 text-blue-700',
    ManagementGoal: 'bg-emerald-50 border-emerald-100 text-emerald-700',
    FinancialIncentive: 'bg-amber-50 border-amber-100 text-amber-700',
    ContractualRule: 'bg-purple-50 border-purple-100 text-purple-700',
    PhilanthropicStatus: 'bg-pink-50 border-pink-100 text-pink-700',
    TeachingFacilityStatus: 'bg-sky-50 border-sky-100 text-sky-700',
};

const fmtDate = (iso) => {
    if (!iso) return null;
    return iso.slice(0, 10).split('-').reverse().join('/');
};

const CnesValidityPage = () => {
    usePageTitle('Qualificações CNES (Validity)');

    const [summary, setSummary] = useState(null);
    const [summaryError, setSummaryError] = useState(null);

    const [cnes, setCnes] = useState('');
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        getValiditySummary().then(setSummary).catch(err => {
            setSummaryError(err.response?.data?.error || err.message || 'Erro ao carregar panorama nacional.');
        });
    }, []);

    const handleSearch = async () => {
        if (!cnes.trim()) return;
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const data = await getFacilityValidity(cnes.trim());
            setResult(data);
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Erro ao buscar estabelecimento.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">
                    Qualificações CNES (Validity)
                </h1>
                <p className="text-gray-500 mt-2 text-lg">
                    Habilitações, metas, incentivos e status regulatórios de um estabelecimento — direto da BPHO.
                </p>
            </header>

            <div className="max-w-4xl mx-auto space-y-8 pb-12">
                <InfoCard title="O que é isto">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Seis grupos do CNES compartilham o mesmo formato real — início/fim de vigência mais o
                        instrumento normativo (portaria) que concedeu o status — modelados na BPHO como
                        <code className="mx-1 px-1 bg-gray-100 rounded">Validity</code>. Um estabelecimento pode
                        ter zero, uma ou várias qualificações reais; ausência não é erro.
                    </p>
                </InfoCard>

                {summaryError && <FeedbackMessage message={summaryError} type="error" />}
                {summary && (
                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                        <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">
                            Panorama nacional — {summary.total.toLocaleString('pt-BR')} qualificações reais
                        </h2>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                            {Object.entries(summary.by_kind).map(([kind, n]) => (
                                <div key={kind} className={`p-3 rounded-xl border ${KIND_COLORS[kind] || 'bg-gray-50 border-gray-100'}`}>
                                    <div className="text-xs font-black uppercase tracking-wide">{KIND_LABELS[kind] || kind}</div>
                                    <div className="text-2xl font-black mt-1">{n.toLocaleString('pt-BR')}</div>
                                    <div className="text-xs opacity-75 mt-1">
                                        {(summary.still_open_by_kind[kind] || 0).toLocaleString('pt-BR')} ainda em vigor
                                    </div>
                                </div>
                            ))}
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
                            placeholder="Ex: 2077647"
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
                        <div className="mt-4">
                            {result.count === 0 ? (
                                <p className="text-sm text-gray-500 italic">
                                    Nenhuma qualificação real encontrada para facility_{result.cnes} — ausência
                                    estrutural, não um erro de busca.
                                </p>
                            ) : (
                                <div className="space-y-2">
                                    <p className="text-xs text-gray-400 mb-2">
                                        {result.count} qualificação(ões) real(is) encontrada(s):
                                    </p>
                                    {result.qualifications.map((q, i) => (
                                        <div key={i} className={`p-3 rounded-xl border flex items-center justify-between ${KIND_COLORS[q.kind] || 'bg-gray-50 border-gray-100'}`}>
                                            <div>
                                                <div className="text-sm font-black">{KIND_LABELS[q.kind] || q.kind}</div>
                                                <div className="text-xs opacity-75 mt-0.5">
                                                    desde {fmtDate(q.valid_from)}
                                                    {q.valid_until ? ` até ${fmtDate(q.valid_until)}` : ' — ainda em vigor'}
                                                </div>
                                            </div>
                                            <FiShield className="opacity-40" size={22} />
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CnesValidityPage;
