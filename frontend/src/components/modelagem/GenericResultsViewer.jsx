import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';
import { useLocation, Link } from 'react-router-dom';
import { FiDownload, FiExternalLink, FiFileText, FiTable, FiFile } from 'react-icons/fi';

import usePageTitle from '../../hooks/usePageTitle';
import FeedbackMessage from '../common/FeedbackMessage';
import LoadingSpinner from '../common/LoadingSpinner';
import InfoCard from '../common/InfoCard';

const authHeaders = () => ({ Authorization: `Token ${localStorage.getItem('authToken')}` });

const isImagem = (filename = '') => /\.(png|jpe?g)$/i.test(filename);
const isCsv = (filename = '') => /\.csv$/i.test(filename);

const CORES = ['#2563eb', '#16a34a', '#dc2626', '#9333ea', '#ea580c', '#0891b2', '#db2777', '#65a30d'];
const REGEX_COLUNA_DATA = /^(ds|data|date|dt_|competencia|periodo)/i;

// A API de dados de CSV desserializa 'True'/'False' do pandas como booleans
// JS nativos — e !isNaN(true) é 'false' (Number(true) === 1), então sem essa
// checagem uma coluna booleana (ex.: TEM_RECURSO) passaria como "numérica".
const ehValorNumerico = (v) => v !== null && v !== undefined && v !== '' && typeof v !== 'boolean' && !isNaN(v) && isFinite(v);

// Classifica as colunas de um CSV genérico para decidir que tipo de gráfico
// Plotly faz sentido, sem exigir configuração manual por modelo.
const classificarColunas = (linhas) => {
    if (!linhas || linhas.length === 0) return null;
    const colunas = Object.keys(linhas[0]);
    const amostra = linhas.slice(0, Math.min(linhas.length, 300));

    let colunaData = null;
    const colunasNumericas = [];
    let colunaCategorica = null;

    colunas.forEach((col) => {
        const valores = amostra.map((l) => l[col]).filter((v) => v !== null && v !== undefined && v !== '');
        if (valores.length === 0) return;

        if (!colunaData && REGEX_COLUNA_DATA.test(col)) {
            const validas = valores.filter((v) => !isNaN(Date.parse(v))).length;
            if (validas / valores.length > 0.8) {
                colunaData = col;
                return;
            }
        }

        const proporcaoNumerica = valores.filter(ehValorNumerico).length / valores.length;
        if (proporcaoNumerica > 0.9) {
            colunasNumericas.push(col);
        } else if (!colunaCategorica) {
            colunaCategorica = col;
        }
    });

    return { colunaData, colunasNumericas, colunaCategorica };
};

const interpolarCor = (t, corInicio = [186, 222, 247], corFim = [178, 34, 34]) => {
    const r = Math.round(corInicio[0] + (corFim[0] - corInicio[0]) * t);
    const g = Math.round(corInicio[1] + (corFim[1] - corInicio[1]) * t);
    const b = Math.round(corInicio[2] + (corFim[2] - corInicio[2]) * t);
    return `rgb(${r},${g},${b})`;
};

const mediaCoordenadas = (valores) => valores.reduce((a, b) => a + b, 0) / valores.length;

// Mapa de fluxo (origem -> destino): detecta CSVs com LAT_ORIGEM/LON_ORIGEM/
// LAT_DESTINO/LON_DESTINO (gerados pelos modelos de "Fluxo de..."), uma
// coluna N_* de peso, e desenha rotas num Scattermapbox — espessura e cor
// da linha proporcionais ao peso (escala log).
const construirMapaFluxoPlotly = (linhas, colunas) => {
    const temColunas = ['LAT_ORIGEM', 'LON_ORIGEM', 'LAT_DESTINO', 'LON_DESTINO'].every((c) => colunas.includes(c));
    if (!temColunas) return null;
    const colPeso = colunas.find((c) => /^N_/.test(c) && ehValorNumerico(linhas[0][c]));
    if (!colPeso) return null;

    const pesos = linhas.map((l) => Number(l[colPeso])).filter((v) => !isNaN(v));
    const min = Math.min(...pesos);
    const max = Math.max(...pesos);
    const normalizar = (v) => (max > min ? (Math.log(v + 1) - Math.log(min + 1)) / (Math.log(max + 1) - Math.log(min + 1)) : 0.5);

    const linhasMapa = linhas.map((l) => {
        const t = normalizar(Number(l[colPeso]));
        return {
            type: 'scattermapbox',
            mode: 'lines',
            lon: [Number(l.LON_ORIGEM), Number(l.LON_DESTINO)],
            lat: [Number(l.LAT_ORIGEM), Number(l.LAT_DESTINO)],
            line: { width: 1.5 + t * 6, color: interpolarCor(t) },
            hoverinfo: 'text',
            text: `${l.NOME_ORIGEM || l.MUNIC_RES || ''} → ${l.NOME_DESTINO || l.MUNIC_MOV || ''}: ${l[colPeso]}`,
            showlegend: false,
        };
    });

    const todasLat = linhas.flatMap((l) => [Number(l.LAT_ORIGEM), Number(l.LAT_DESTINO)]);
    const todasLon = linhas.flatMap((l) => [Number(l.LON_ORIGEM), Number(l.LON_DESTINO)]);

    return {
        tipo: 'mapa-fluxo',
        data: linhasMapa,
        layout: {
            mapbox: { style: 'open-street-map', center: { lat: mediaCoordenadas(todasLat), lon: mediaCoordenadas(todasLon) }, zoom: 5.5 },
        },
        nota: `${linhas.length} rota(s) — espessura e cor da linha (escala log) = ${colPeso}.`,
    };
};

// Mapa de pontos (bolhas), com animação por período se houver uma coluna de
// data/periodo: detecta CSVs com latitude/longitude (municipios.csv) + um
// valor numérico associado.
const construirMapaPontosPlotly = (linhas, colunas) => {
    const colLat = colunas.find((c) => c.toLowerCase() === 'latitude');
    const colLon = colunas.find((c) => c.toLowerCase() === 'longitude');
    if (!colLat || !colLon) return null;

    const colValor = colunas.find((c) => c !== colLat && c !== colLon && !/^cod/i.test(c) && ehValorNumerico(linhas[0][c]) && linhas.some((l) => ehValorNumerico(l[c])));
    if (!colValor) return null;

    const colNome = colunas.find((c) => /^munic/i.test(c)) || null;
    const colPeriodo = colunas.find((c) => REGEX_COLUNA_DATA.test(c));

    const valoresTodos = linhas.map((l) => Number(l[colValor])).filter((v) => !isNaN(v));
    const cmax = Math.max(...valoresTodos) || 1;
    const todasLat = linhas.map((l) => Number(l[colLat]));
    const todasLon = linhas.map((l) => Number(l[colLon]));
    const layoutBase = {
        mapbox: { style: 'open-street-map', center: { lat: mediaCoordenadas(todasLat), lon: mediaCoordenadas(todasLon) }, zoom: 5.5 },
    };

    const construirTrace = (subset) => ({
        type: 'scattermapbox',
        mode: 'markers',
        lat: subset.map((l) => Number(l[colLat])),
        lon: subset.map((l) => Number(l[colLon])),
        text: subset.map((l) => `${colNome ? l[colNome] : ''}: ${l[colValor]}`),
        hoverinfo: 'text',
        marker: {
            size: subset.map((l) => 6 + 22 * (Number(l[colValor]) / cmax)),
            color: subset.map((l) => Number(l[colValor])),
            colorscale: 'OrRd',
            cmin: 0,
            cmax,
            showscale: true,
            colorbar: { title: colValor },
        },
    });

    if (colPeriodo) {
        const periodos = [...new Set(linhas.map((l) => l[colPeriodo]))].sort();
        if (periodos.length < 2) return null;
        const frames = periodos.map((p) => ({ name: String(p), data: [construirTrace(linhas.filter((l) => l[colPeriodo] === p))] }));
        return {
            tipo: 'mapa-animado',
            data: frames[0].data,
            frames,
            layout: {
                ...layoutBase,
                updatemenus: [{
                    type: 'buttons', showactive: false, x: 0, y: 0, xanchor: 'left', yanchor: 'top',
                    buttons: [{ label: '▶ Reproduzir', method: 'animate', args: [null, { fromcurrent: true, frame: { duration: 700, redraw: true }, transition: { duration: 200 } }] }],
                }],
                sliders: [{
                    currentvalue: { prefix: 'Período: ', font: { size: 12 } },
                    steps: periodos.map((p) => ({ label: String(p), method: 'animate', args: [[String(p)], { mode: 'immediate', frame: { duration: 0, redraw: true } }] })),
                }],
            },
            nota: `Animação por ${colPeriodo} — ${periodos.length} período(s). Use o play ▶ ou arraste o controle deslizante.`,
        };
    }

    return {
        tipo: 'mapa-pontos',
        data: [construirTrace(linhas)],
        layout: layoutBase,
        nota: `${linhas.length} município(s) — tamanho e cor da bolha = ${colValor}.`,
    };
};

// Monta uma figura Plotly a partir dos dados crus do CSV (sem depender de
// nenhuma configuração específica do modelo): mapa (fluxo ou pontos) se as
// colunas geográficas estiverem presentes, senão série temporal se houver
// uma coluna de data, barras agrupadas se houver uma coluna categórica de
// baixa cardinalidade, ou dispersão entre as duas primeiras colunas numéricas.
const construirGraficoPlotly = (linhas) => {
    if (!linhas || linhas.length === 0) return null;
    const colunas = Object.keys(linhas[0]);

    const mapaFluxo = construirMapaFluxoPlotly(linhas, colunas);
    if (mapaFluxo) return mapaFluxo;
    const mapaPontos = construirMapaPontosPlotly(linhas, colunas);
    if (mapaPontos) return mapaPontos;

    // Uma única linha é um registro-resumo (ex.: resultado de um teste
    // estatístico como Moran Bivariado/Global), não uma série a visualizar —
    // colunas como ANO viram "barras" sem sentido ao lado de índices e
    // p-valores. A tabela abaixo já comunica isso melhor que um gráfico
    // forçado de 1 ponto por coluna.
    if (linhas.length === 1) return null;

    const classificacao = classificarColunas(linhas);
    if (!classificacao) return null;
    const { colunaData, colunasNumericas, colunaCategorica } = classificacao;

    if (colunaData && colunasNumericas.length > 0) {
        const ordenadas = [...linhas].sort((a, b) => new Date(a[colunaData]) - new Date(b[colunaData]));
        return {
            tipo: 'linha',
            data: colunasNumericas.slice(0, 8).map((col, i) => ({
                x: ordenadas.map((l) => l[colunaData]),
                y: ordenadas.map((l) => (ehValorNumerico(l[col]) ? Number(l[col]) : null)),
                type: 'scatter',
                mode: 'lines+markers',
                name: col,
                line: { color: CORES[i % CORES.length] },
                marker: { size: 4 },
            })),
            layout: { xaxis: { title: colunaData, type: 'date' }, yaxis: { title: 'Valor' }, hovermode: 'x unified' },
        };
    }

    if (colunaCategorica && colunasNumericas.length > 0) {
        const categoriasUnicas = [...new Set(linhas.map((l) => l[colunaCategorica]))];
        if (categoriasUnicas.length > 40) return null;

        let linhasGrafico = linhas;
        let nota = null;
        if (linhas.length > 60) {
            const soma = {};
            const contagem = {};
            linhas.forEach((l) => {
                const cat = l[colunaCategorica];
                if (!soma[cat]) { soma[cat] = {}; contagem[cat] = 0; }
                contagem[cat] += 1;
                colunasNumericas.forEach((col) => {
                    if (ehValorNumerico(l[col])) soma[cat][col] = (soma[cat][col] || 0) + Number(l[col]);
                });
            });
            linhasGrafico = Object.keys(soma).map((cat) => {
                const linha = { [colunaCategorica]: cat };
                colunasNumericas.forEach((col) => { linha[col] = (soma[cat][col] || 0) / contagem[cat]; });
                return linha;
            });
            nota = `Média por categoria — ${linhasGrafico.length} grupo(s) a partir de ${linhas.length} linha(s).`;
        }

        return {
            tipo: 'barra',
            data: colunasNumericas.slice(0, 8).map((col, i) => ({
                x: linhasGrafico.map((l) => l[colunaCategorica]),
                y: linhasGrafico.map((l) => l[col]),
                type: 'bar',
                name: col,
                marker: { color: CORES[i % CORES.length] },
            })),
            layout: { xaxis: { title: colunaCategorica }, yaxis: { title: 'Valor' }, barmode: 'group' },
            nota,
        };
    }

    if (colunasNumericas.length >= 2) {
        const passo = linhas.length > 2000 ? Math.ceil(linhas.length / 2000) : 1;
        const amostra = linhas.filter((_, i) => i % passo === 0);
        const colunaCor = colunasNumericas[2];
        return {
            tipo: 'dispersao',
            data: [{
                x: amostra.map((l) => Number(l[colunasNumericas[0]])),
                y: amostra.map((l) => Number(l[colunasNumericas[1]])),
                mode: 'markers',
                type: 'scatter',
                marker: colunaCor
                    ? { color: amostra.map((l) => Number(l[colunaCor])), colorscale: 'Viridis', showscale: true, colorbar: { title: colunaCor }, size: 6 }
                    : { color: '#2563eb', size: 6 },
            }],
            layout: { xaxis: { title: colunasNumericas[0] }, yaxis: { title: colunasNumericas[1] } },
            nota: passo > 1 ? `Amostra de ${amostra.length} de ${linhas.length} pontos.` : null,
        };
    }

    return null;
};

const CsvPreviewTable = ({ linhas }) => {
    if (!linhas || linhas.length === 0) return <p className="text-sm text-gray-400 italic">Sem linhas para exibir.</p>;
    const colunas = Object.keys(linhas[0]);
    const amostra = linhas.slice(0, 25);
    return (
        <div className="overflow-x-auto border border-gray-100 rounded-xl">
            <table className="min-w-full text-xs">
                <thead className="bg-gray-50">
                    <tr>
                        {colunas.map((c) => (
                            <th key={c} className="px-3 py-2 text-left font-bold text-gray-500 uppercase whitespace-nowrap">{c}</th>
                        ))}
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                    {amostra.map((linha, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                            {colunas.map((c) => (
                                <td key={c} className="px-3 py-2 whitespace-nowrap text-gray-700">{String(linha[c] ?? '')}</td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
            {linhas.length > amostra.length && (
                <p className="text-[10px] text-gray-400 px-3 py-2 uppercase tracking-widest">
                    Mostrando {amostra.length} de {linhas.length} linhas — baixe o CSV para o conjunto completo.
                </p>
            )}
        </div>
    );
};

const ArquivoCsvResultado = ({ arquivo }) => {
    const [detalhe, setDetalhe] = useState(null);
    const [linhasCsv, setLinhasCsv] = useState(null);
    const [carregando, setCarregando] = useState(true);
    const [mostrarTabela, setMostrarTabela] = useState(false);

    useEffect(() => {
        let ativo = true;
        const carregar = async () => {
            setCarregando(true);
            try {
                const [res, dataRes] = await Promise.all([
                    axios.get(`/api/files/${arquivo.id}/`, { headers: authHeaders() }),
                    axios.get(`/api/files/${arquivo.id}/data/`, { headers: authHeaders() }),
                ]);
                if (!ativo) return;
                setDetalhe(res.data);
                setLinhasCsv(dataRes.data);
            } catch (e) {
                console.error('Erro ao carregar arquivo:', e);
            } finally {
                if (ativo) setCarregando(false);
            }
        };
        carregar();
        return () => { ativo = false; };
    }, [arquivo.id]);

    const grafico = useMemo(() => construirGraficoPlotly(linhasCsv), [linhasCsv]);

    // Resize de janela único, disparado pouco depois dos dados do gráfico
    // ficarem prontos — corrige o mapbox-gl inicializando com tamanho errado
    // logo após uma navegação interna do SPA, nos casos em que `grafico` é um
    // mapa (ver mesma nota em AnalisePorMunicipioPage.jsx).
    useEffect(() => {
        if (!grafico?.tipo?.startsWith('mapa')) return;
        const timer = setTimeout(() => window.dispatchEvent(new Event('resize')), 200);
        return () => clearTimeout(timer);
    }, [grafico]);

    if (carregando) {
        return (
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200 flex justify-center">
                <LoadingSpinner size="sm" />
            </div>
        );
    }

    if (!detalhe) return null;

    return (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-200">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
                <h3 className="text-sm font-black text-gray-700 flex items-center gap-2">
                    <FiFileText className="text-blue-500" /> {arquivo.filename}
                </h3>
                <div className="flex gap-2">
                    <button
                        type="button"
                        onClick={() => setMostrarTabela((v) => !v)}
                        className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200"
                    >
                        <FiTable size={12} /> {mostrarTabela ? 'Ocultar Tabela' : 'Ver Tabela'}
                    </button>
                    <a
                        href={detalhe.file}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg bg-blue-50 text-blue-600 hover:bg-blue-100"
                    >
                        <FiExternalLink size={12} /> Abrir
                    </a>
                    <a
                        href={detalhe.file}
                        download
                        className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200"
                    >
                        <FiDownload size={12} /> Baixar
                    </a>
                </div>
            </div>

            {grafico && (() => {
                const ehMapa = grafico.tipo?.startsWith('mapa');
                return (
                    <div className={ehMapa ? 'h-[560px]' : 'h-[420px]'}>
                        <Plot
                            key={`${detalhe.file}-${grafico.tipo}`}
                            data={grafico.data}
                            frames={grafico.frames}
                            layout={{
                                ...grafico.layout,
                                autosize: true,
                                margin: ehMapa ? { t: 10, b: 10, l: 10, r: 10 } : { t: 20, b: 60, l: 60, r: 30 },
                                ...(ehMapa ? {} : { legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'right', x: 1 } }),
                            }}
                            config={{ responsive: true, displayModeBar: ehMapa }}
                            className="w-full h-full"
                        />
                    </div>
                );
            })()}
            {grafico?.nota && <p className="text-[10px] text-gray-400 uppercase tracking-widest mt-2">{grafico.nota}</p>}

            {(mostrarTabela || !grafico) && (
                <div className={grafico ? 'mt-6' : ''}>
                    <CsvPreviewTable linhas={linhasCsv} />
                </div>
            )}
        </div>
    );
};

const LinkArquivoEstatico = ({ arquivo }) => {
    const [url, setUrl] = useState(null);

    useEffect(() => {
        let ativo = true;
        axios.get(`/api/files/${arquivo.id}/`, { headers: authHeaders() })
            .then((res) => { if (ativo) setUrl(res.data.file); })
            .catch((e) => console.error('Erro ao carregar imagem:', e));
        return () => { ativo = false; };
    }, [arquivo.id]);

    if (!url) {
        return (
            <span className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg bg-gray-100 text-gray-400">
                <FiFile size={12} /> {arquivo.filename}
            </span>
        );
    }

    return (
        <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200"
        >
            <FiFile size={12} /> {arquivo.filename}
        </a>
    );
};

const ArquivosEstaticos = ({ arquivos }) => {
    if (arquivos.length === 0) return null;
    return (
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-200">
            <h3 className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-3">
                Imagens estáticas geradas
            </h3>
            <div className="flex flex-wrap gap-2">
                {arquivos.map((arquivo) => (
                    <LinkArquivoEstatico key={arquivo.id} arquivo={arquivo} />
                ))}
            </div>
        </div>
    );
};

const GenericResultsViewer = ({ config }) => {
    usePageTitle(`Resultado — ${config.title}`);
    const location = useLocation();
    const queryParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
    const taskId = queryParams.get('taskId');

    const [taskDetails, setTaskDetails] = useState(null);
    const [arquivos, setArquivos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const apiPrefix = `/api/pipelines/${config.key}/`;

    useEffect(() => {
        if (!taskId) {
            setError('Nenhum ID de tarefa foi fornecido.');
            setLoading(false);
            return;
        }
        const fetchAll = async () => {
            setLoading(true);
            setError(null);
            try {
                const detailRes = await axios.get(`${apiPrefix}tasks/${taskId}/`, { headers: authHeaders() });
                setTaskDetails(detailRes.data);

                let listaArquivos = [];
                try {
                    const statusRes = await axios.get(`${apiPrefix}tasks/${taskId}/status/`, { headers: authHeaders() });
                    if (statusRes.data.status === 'SUCCESS' && statusRes.data.result?.arquivos_gerados) {
                        listaArquivos = statusRes.data.result.arquivos_gerados;
                    }
                } catch (e) {
                    console.error('Erro ao consultar status da task:', e);
                }

                if (listaArquivos.length === 0 && detailRes.data.output_file_id) {
                    listaArquivos = [{
                        id: detailRes.data.output_file_id,
                        filename: detailRes.data.output_file_filename || 'resultado.csv',
                    }];
                }
                setArquivos(listaArquivos);
            } catch (err) {
                setError('Não foi possível carregar os detalhes da tarefa.');
                console.error('Erro ao buscar detalhes:', err);
            } finally {
                setLoading(false);
            }
        };
        fetchAll();
    }, [taskId, apiPrefix]);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-screen p-10">
                <LoadingSpinner size="lg" color="blue" />
                <p className="mt-4 text-gray-700">Carregando resultado da análise...</p>
            </div>
        );
    }

    if (error) return <FeedbackMessage message={error} type="error" />;
    if (!taskDetails) return <FeedbackMessage message="Nenhum detalhe da tarefa encontrado." type="info" />;

    const arquivosCsv = arquivos.filter((a) => isCsv(a.filename));
    const arquivosImagem = arquivos.filter((a) => isImagem(a.filename));

    return (
        <div className="p-6 bg-gray-50 min-h-screen">
            <h1 className="text-3xl text-center text-gray-800 mb-8 font-black tracking-tight">{config.title}</h1>

            <div className="max-w-5xl mx-auto space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-white p-6 rounded-lg shadow-md md:col-span-2">
                        <h2 className="text-sm font-bold text-gray-400 uppercase mb-3">Parâmetros</h2>
                        <ul className="space-y-1.5 text-sm">
                            {Object.entries(taskDetails.parametros || {}).map(([chave, val]) => (
                                <li key={chave} className="flex justify-between border-b pb-1 gap-4">
                                    <span className="font-semibold text-gray-600 shrink-0">{chave}:</span>
                                    <span className="text-gray-800 text-right break-all">{Array.isArray(val) ? val.join(', ') : String(val)}</span>
                                </li>
                            ))}
                        </ul>
                    </div>

                    <div className="bg-white p-6 rounded-lg shadow-md">
                        <h2 className="text-sm font-bold text-gray-400 uppercase mb-3">Status</h2>
                        <p className={`text-lg font-black ${taskDetails.status === 'SUCCESS' ? 'text-green-600' : 'text-red-600'}`}>
                            {taskDetails.status}
                        </p>
                        <Link
                            to={`/pipelines/modelagem/${config.key}`}
                            className="block w-full text-center mt-4 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-bold py-2 px-4 rounded-lg transition-colors text-sm"
                        >
                            Nova Análise
                        </Link>
                    </div>
                </div>

                {taskDetails.message && (
                    <InfoCard title="Detalhes da Execução">
                        <p className="text-sm text-gray-600">{taskDetails.message}</p>
                    </InfoCard>
                )}

                {config.comoInterpretar && config.comoInterpretar.length > 0 && (
                    <InfoCard title="Como Interpretar os Resultados">
                        <ul className="list-disc list-inside space-y-2 text-sm text-gray-600">
                            {config.comoInterpretar.map((linha, i) => (
                                <li key={i}>{linha}</li>
                            ))}
                        </ul>
                    </InfoCard>
                )}

                {arquivos.length === 0 && taskDetails.status === 'SUCCESS' && (
                    <FeedbackMessage message="Nenhum arquivo de resultado foi encontrado para esta tarefa." type="info" />
                )}

                {arquivosCsv.map((arquivo) => (
                    <ArquivoCsvResultado key={arquivo.id} arquivo={arquivo} />
                ))}

                <ArquivosEstaticos arquivos={arquivosImagem} />
            </div>
        </div>
    );
};

export default GenericResultsViewer;
