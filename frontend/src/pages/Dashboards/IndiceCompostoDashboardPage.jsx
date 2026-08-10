import React, { useState, useCallback, useEffect, useMemo } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { FiPlay, FiCheckCircle, FiInfo, FiArrowUp, FiArrowDown } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import useCeleryTaskStatus from '../../hooks/useCeleryTaskStatus';
import FeedbackMessage from '../../components/common/FeedbackMessage';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import InfoCard from '../../components/common/InfoCard';
import { getIndiceSpec } from '../../config/indicesCompostosSpec';

const UFS_BRASIL = [
    'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG',
    'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
];
const ANOS_DISPONIVEIS = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026];

const authHeaders = () => ({ Authorization: `Token ${localStorage.getItem('authToken')}` });

const apiPrefix = '/api/pipelines/indices-compostos/';

const normalizar0100 = (valores) => {
    const validos = valores.filter((v) => typeof v === 'number' && !isNaN(v));
    if (validos.length === 0) return valores.map(() => 0);
    const min = Math.min(...validos);
    const max = Math.max(...validos);
    if (max === min) return valores.map(() => 50);
    return valores.map((v) => (typeof v === 'number' && !isNaN(v) ? ((v - min) / (max - min)) * 100 : 0));
};

const TriggerForm = ({ spec, onDisparado }) => {
    const [ufs, setUfs] = useState(['TO']);
    const [anos, setAnos] = useState(spec.requerVariosAnos ? [2018, 2019, 2020, 2021, 2022] : [2022]);
    const [disparando, setDisparando] = useState(false);

    const disparar = useCallback(async () => {
        setDisparando(true);
        try {
            const response = await axios.post(`${apiPrefix}trigger/`, { indice: spec.key, ufs, anos }, { headers: authHeaders() });
            onDisparado(response.data.task_id);
        } catch (err) {
            alert(`Falha ao disparar cálculo: ${err.response?.data?.error || err.message}`);
            setDisparando(false);
        }
    }, [spec.key, ufs, anos, onDisparado]);

    return (
        <div className="max-w-3xl mx-auto space-y-6">
            <InfoCard title={`Sobre o ${spec.sigla}`}>
                <p className="text-sm leading-relaxed text-gray-600 font-medium mb-2">{spec.descricao}</p>
                {spec.formula && (
                    <p className="text-xs font-mono bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 inline-block text-gray-700">
                        {spec.formula}
                    </p>
                )}
                {spec.requerVariosAnos && (
                    <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mt-3">
                        Este índice opera sobre uma série de anos — recomenda-se pelo menos {spec.anosMinimosRecomendados || 5} anos para um resultado confiável.
                    </p>
                )}
            </InfoCard>

            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
                <h2 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-6 flex items-center gap-2">
                    <FiInfo className="text-blue-500" /> Parâmetros
                </h2>
                <div className="mb-6">
                    <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">UFs</label>
                    <div className="grid grid-cols-6 sm:grid-cols-9 gap-1.5">
                        {UFS_BRASIL.map((uf) => (
                            <button key={uf} type="button"
                                onClick={() => setUfs((prev) => prev.includes(uf) ? prev.filter((u) => u !== uf) : [...prev, uf])}
                                className={`py-1.5 rounded-lg text-[11px] font-black transition-all ${ufs.includes(uf) ? 'bg-blue-600 text-white shadow-sm' : 'bg-gray-50 text-gray-400 border border-gray-200 hover:bg-gray-100'}`}>
                                {uf}
                            </button>
                        ))}
                    </div>
                </div>
                <div>
                    <label className="block text-[10px] font-bold text-gray-500 uppercase mb-2">Anos</label>
                    <div className="flex flex-wrap gap-1.5">
                        {ANOS_DISPONIVEIS.map((ano) => (
                            <button key={ano} type="button"
                                onClick={() => setAnos((prev) => prev.includes(ano) ? prev.filter((a) => a !== ano) : [...prev, ano].sort())}
                                className={`px-3 py-1.5 rounded-lg text-xs font-black transition-all ${anos.includes(ano) ? 'bg-green-600 text-white shadow-sm' : 'bg-gray-50 text-gray-400 border border-gray-200 hover:bg-gray-100'}`}>
                                {ano}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            <button
                onClick={disparar}
                disabled={disparando || ufs.length === 0 || anos.length === 0}
                className={`w-full py-4 rounded-2xl font-black text-white transition-all shadow-xl uppercase tracking-widest flex items-center justify-center gap-3
                    ${disparando || ufs.length === 0 || anos.length === 0 ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'}`}>
                {disparando ? <LoadingSpinner size="sm" color="white" /> : <FiPlay size={20} />}
                {disparando ? 'Disparando...' : `Calcular ${spec.sigla}`}
            </button>
        </div>
    );
};

const ScoreCard = ({ spec, linhas }) => {
    const scores = linhas.map((l) => Number(l[spec.colunaScore])).filter((v) => !isNaN(v));
    const media = scores.reduce((a, b) => a + b, 0) / (scores.length || 1);
    return (
        <div className="bg-white rounded-3xl shadow-sm border border-gray-200 p-8 text-center">
            <p className="text-[10px] font-black text-gray-400 uppercase tracking-[0.2em] mb-2">{spec.sigla} — média entre municípios</p>
            <p className="text-6xl font-black text-blue-600">{media.toFixed(1)}</p>
            <p className="text-xs text-gray-400 mt-3">{linhas.length} município(s) processado(s)</p>
        </div>
    );
};

const RadarComponentes = ({ spec, linhas }) => {
    const eixos = spec.componentes.filter((c) => linhas.some((l) => typeof l[c.coluna] === 'number'));
    if (eixos.length < 3) return null;

    const medias = eixos.map((c) => {
        const valores = linhas.map((l) => Number(l[c.coluna])).filter((v) => !isNaN(v));
        return valores.reduce((a, b) => a + b, 0) / (valores.length || 1);
    });
    const normalizadas = normalizar0100(medias);

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
            <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest px-2 pt-2">Decomposição (média, normalizada 0-100)</h3>
            <Plot
                data={[{
                    type: 'scatterpolar',
                    r: [...normalizadas, normalizadas[0]],
                    theta: [...eixos.map((e) => e.label), eixos[0].label],
                    fill: 'toself',
                    line: { color: '#2563eb' },
                }]}
                layout={{
                    polar: { radialaxis: { visible: true, range: [0, 100] } },
                    showlegend: false,
                    margin: { t: 30, b: 30, l: 40, r: 40 },
                    height: 380,
                }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
            />
        </div>
    );
};

const MapaMunicipios = ({ spec, linhas }) => {
    const comCoordenadas = linhas.filter((l) => typeof l.latitude === 'number' && typeof l.longitude === 'number' && typeof l[spec.colunaScore] === 'number');

    // Resize de janela único, disparado pouco depois dos dados do mapa
    // ficarem prontos — corrige o mapbox-gl inicializando com tamanho errado
    // logo após uma navegação interna do SPA (ver mesma nota em
    // AnalisePorMunicipioPage.jsx).
    useEffect(() => {
        if (comCoordenadas.length === 0) return;
        const timer = setTimeout(() => window.dispatchEvent(new Event('resize')), 200);
        return () => clearTimeout(timer);
    }, [spec.sigla, comCoordenadas.length]);

    if (comCoordenadas.length === 0) return null;

    const valores = comCoordenadas.map((l) => Number(l[spec.colunaScore]));
    const centroLat = comCoordenadas.reduce((a, l) => a + l.latitude, 0) / comCoordenadas.length;
    const centroLon = comCoordenadas.reduce((a, l) => a + l.longitude, 0) / comCoordenadas.length;

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
            <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest px-2 pt-2 pb-2">Mapa por Município</h3>
            <Plot
                key={`${spec.sigla}-${comCoordenadas.length}`}
                data={[{
                    type: 'scattermapbox',
                    lat: comCoordenadas.map((l) => l.latitude),
                    lon: comCoordenadas.map((l) => l.longitude),
                    text: comCoordenadas.map((l) => `${l.municipio}: ${Number(l[spec.colunaScore]).toFixed(1)}`),
                    hoverinfo: 'text',
                    mode: 'markers',
                    marker: {
                        size: normalizar0100(valores).map((v) => 8 + (v / 100) * 18),
                        color: valores,
                        colorscale: 'OrRd',
                        showscale: true,
                        colorbar: { title: spec.sigla },
                    },
                }]}
                layout={{
                    mapbox: { style: 'open-street-map', center: { lat: centroLat, lon: centroLon }, zoom: 5.5 },
                    margin: { t: 10, b: 10, l: 10, r: 10 },
                    height: 480,
                }}
                config={{ displayModeBar: true, responsive: true }}
                style={{ width: '100%' }}
            />
        </div>
    );
};

const TendenciaAnual = ({ spec, linhas }) => {
    const anos = [...new Set(linhas.map((l) => l.ANO))].sort();
    if (anos.length < 2) return null;

    const mediaPorAno = anos.map((ano) => {
        const valores = linhas.filter((l) => l.ANO === ano).map((l) => Number(l[spec.colunaScore])).filter((v) => !isNaN(v));
        return valores.reduce((a, b) => a + b, 0) / (valores.length || 1);
    });

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
            <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest px-2 pt-2 pb-2">Tendência (média entre municípios)</h3>
            <Plot
                data={[{ x: anos, y: mediaPorAno, type: 'scatter', mode: 'lines+markers', line: { color: '#2563eb' } }]}
                layout={{ xaxis: { title: 'Ano', type: 'category' }, yaxis: { title: spec.sigla }, margin: { t: 10, b: 40, l: 50, r: 20 }, height: 320 }}
                config={{ displayModeBar: false, responsive: true }}
                style={{ width: '100%' }}
            />
        </div>
    );
};

const RankingTable = ({ spec, linhas }) => {
    const [ordem, setOrdem] = useState('desc');
    const ultimoAno = Math.max(...linhas.map((l) => l.ANO));
    const linhasUltimoAno = linhas.filter((l) => l.ANO === ultimoAno && typeof l[spec.colunaScore] === 'number');
    const ordenadas = [...linhasUltimoAno].sort((a, b) => ordem === 'desc' ? b[spec.colunaScore] - a[spec.colunaScore] : a[spec.colunaScore] - b[spec.colunaScore]);
    const amostra = ordenadas.slice(0, 20);

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center justify-between px-2 pt-2 pb-3">
                <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest">Ranking ({ultimoAno})</h3>
                <button
                    onClick={() => setOrdem((o) => o === 'desc' ? 'asc' : 'desc')}
                    className="flex items-center gap-1 text-[10px] font-bold text-blue-600 uppercase tracking-widest hover:text-blue-800"
                >
                    {ordem === 'desc' ? <FiArrowDown size={12} /> : <FiArrowUp size={12} />}
                    {ordem === 'desc' ? 'Maiores primeiro' : 'Menores primeiro'}
                </button>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="text-left text-[10px] font-black text-gray-400 uppercase tracking-widest border-b border-gray-100">
                            <th className="px-3 py-2">#</th>
                            <th className="px-3 py-2">Município</th>
                            <th className="px-3 py-2 text-right">{spec.sigla}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {amostra.map((l, i) => (
                            <tr key={l.cod_mun_ibge_6} className="border-b border-gray-50 hover:bg-gray-50">
                                <td className="px-3 py-2 text-gray-400 font-bold">{i + 1}</td>
                                <td className="px-3 py-2 font-medium text-gray-700">{l.municipio}</td>
                                <td className="px-3 py-2 text-right font-black text-blue-600">{Number(l[spec.colunaScore]).toFixed(1)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

const PainelEstabilidadePHSI = ({ linhas }) => {
    const colunas = ['AUTOCORR_LAG1_INTERNACOES_PHSI', 'CV_INTERNACOES_PHSI', 'AUTOCORR_LAG1_MORTALIDADE_PHSI', 'CV_MORTALIDADE_PHSI'];
    if (!colunas.every((c) => linhas.some((l) => typeof l[c] === 'number'))) return null;

    const maisInstaveis = [...linhas]
        .filter((l) => typeof l.AUTOCORR_LAG1_INTERNACOES_PHSI === 'number')
        .sort((a, b) => b.AUTOCORR_LAG1_INTERNACOES_PHSI - a.AUTOCORR_LAG1_INTERNACOES_PHSI)
        .slice(0, 10);

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-amber-200 p-4">
            <h3 className="text-xs font-black text-amber-700 uppercase tracking-widest px-2 pt-2 pb-1">
                Sinal de Alerta — Autocorrelação Lag-1 mais alta (Internações)
            </h3>
            <p className="text-xs text-gray-500 px-2 pb-3">
                "Critical slowing down": municípios cuja série demora mais para voltar ao equilíbrio depois de um choque — candidatos a acompanhamento mais próximo.
            </p>
            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="text-left text-[10px] font-black text-gray-400 uppercase tracking-widest border-b border-gray-100">
                            <th className="px-3 py-2">Município</th>
                            <th className="px-3 py-2 text-right">Autocorrelação Lag-1</th>
                            <th className="px-3 py-2 text-right">Coef. Variação</th>
                        </tr>
                    </thead>
                    <tbody>
                        {maisInstaveis.map((l) => (
                            <tr key={l.cod_mun_ibge_6} className="border-b border-gray-50">
                                <td className="px-3 py-2 font-medium text-gray-700">{l.municipio}</td>
                                <td className="px-3 py-2 text-right font-black text-amber-700">{Number(l.AUTOCORR_LAG1_INTERNACOES_PHSI).toFixed(2)}</td>
                                <td className="px-3 py-2 text-right text-gray-600">{Number(l.CV_INTERNACOES_PHSI).toFixed(2)}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

const Resultados = ({ spec, linhas }) => (
    <div className="max-w-6xl mx-auto space-y-6">
        {spec.estatisticaEstadual && (
            <FeedbackMessage
                message="Este índice é uma estatística de UF, não de município — o mesmo valor aparece em todos os municípios do mesmo UF/ano."
                type="info"
            />
        )}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <ScoreCard spec={spec} linhas={linhas} />
            <div className="lg:col-span-2">
                <RadarComponentes spec={spec} linhas={linhas} />
            </div>
        </div>
        {spec.key === 'phsi' && <PainelEstabilidadePHSI linhas={linhas} />}
        <TendenciaAnual spec={spec} linhas={linhas} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <MapaMunicipios spec={spec} linhas={linhas} />
            <RankingTable spec={spec} linhas={linhas} />
        </div>
        <InfoCard title="Como interpretar">
            <p className="text-sm leading-relaxed text-gray-600 font-medium">{spec.interpretacao}</p>
        </InfoCard>
    </div>
);

const IndiceCompostoDashboardPage = () => {
    const { key } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const spec = getIndiceSpec(key);
    usePageTitle(spec ? `${spec.sigla} — Índice Composto` : 'Índice Composto');

    const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
    const taskIdInicial = queryParams.get('taskId');
    const [taskId, setTaskId] = useState(taskIdInicial);
    const [linhas, setLinhas] = useState(null);
    const [carregandoDados, setCarregandoDados] = useState(false);
    const [erroDados, setErroDados] = useState(null);

    const { isPending, isSuccess, isFailure, progress, message: taskMessage, error: taskError, result } =
        useCeleryTaskStatus(taskId, `${apiPrefix}tasks/`);

    useEffect(() => {
        if (taskId && taskId !== taskIdInicial) {
            navigate(`${location.pathname}?taskId=${taskId}`, { replace: true });
        }
    }, [taskId, taskIdInicial, navigate, location.pathname]);

    useEffect(() => {
        if (!isSuccess || !result?.arquivos_gerados?.length) return;
        const arquivoId = result.arquivos_gerados[0].id;
        setCarregandoDados(true);
        axios.get(`/api/files/${arquivoId}/data/`, { headers: authHeaders() })
            .then((res) => setLinhas(res.data))
            .catch((err) => setErroDados(err.response?.data?.error || err.message))
            .finally(() => setCarregandoDados(false));
    }, [isSuccess, result]);

    if (!spec) {
        return <FeedbackMessage message={`Índice composto não encontrado: "${key}".`} type="error" />;
    }

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <header className="mb-8 text-center">
                <p className="text-xs font-black text-blue-500 uppercase tracking-[0.3em] mb-1">{spec.grupo}</p>
                <h1 className="text-3xl font-black text-gray-800 tracking-tight">{spec.titulo}</h1>
                <p className="text-gray-400 mt-1 text-sm font-bold uppercase tracking-widest">{spec.sigla}</p>
            </header>

            {isFailure && <div className="max-w-3xl mx-auto mb-6"><FeedbackMessage message={`Erro ao calcular: ${taskError}`} type="error" /></div>}
            {erroDados && <div className="max-w-3xl mx-auto mb-6"><FeedbackMessage message={`Erro ao carregar resultado: ${erroDados}`} type="error" /></div>}

            {!taskId && <TriggerForm spec={spec} onDisparado={setTaskId} />}

            {taskId && (isPending || (isSuccess && (carregandoDados || !linhas))) && (
                <div className="flex flex-col items-center justify-center py-20">
                    <LoadingSpinner size="lg" color="blue" />
                    <p className="mt-4 text-gray-600 font-medium">{taskMessage || 'Calculando...'} {isPending && `(${progress}%)`}</p>
                </div>
            )}

            {taskId && isSuccess && linhas && !carregandoDados && (
                <>
                    <div className="max-w-6xl mx-auto mb-4 flex items-center gap-2 text-green-600 justify-center">
                        <FiCheckCircle /> <span className="text-xs font-bold uppercase tracking-widest">Cálculo concluído</span>
                    </div>
                    <Resultados spec={spec} linhas={linhas} />
                </>
            )}
        </div>
    );
};

export default IndiceCompostoDashboardPage;
