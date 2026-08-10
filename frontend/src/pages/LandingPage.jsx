import React from 'react';
import { Link } from 'react-router-dom';
import {
    FiLogIn, FiUserPlus, FiArrowRight, FiTrendingUp,
    FiGlobe, FiActivity, FiWatch, FiAlertOctagon, FiCheckCircle,
} from 'react-icons/fi';

import LabSUSLogo from '../assets/lab_icon.png';
import usePageTitle from '../hooks/usePageTitle';
import { getCatalogoPorCategoria, PIPELINES } from '../config/pipelineCatalog';
import { ORDEM_SISTEMAS, SISTEMAS_ORIGEM } from '../config/indicadorClassificacao';
import { INDICADORES_MAP } from '../config/indicadores';

// Página pública (sem login), servida em "/" para dar às ferramentas de
// busca algo de fato indexável — o resto da aplicação exige autenticação
// (ver App.js) e não é rastreável. Números e categorias vêm dos mesmos
// catálogos que alimentam a Sidebar/HomePage e a Integração de Indicadores,
// para nunca ficarem desatualizados em relação à aplicação real.
// `getCatalogoPorCategoria(false)`: mesmo filtro aplicado a um usuário sem
// acesso BPHO — a família PopulationSpace e o bloco de Vigilância &
// Ontologia não aparecem aqui.
const CHAVES_DESTAQUE = ['moran-mortalidade', 'previsao-obitos', 'isolation-forest', 'sobrevida-tb', 'hsri'];
const ICONES_DESTAQUE = { 'moran-mortalidade': FiGlobe, 'previsao-obitos': FiTrendingUp, 'isolation-forest': FiAlertOctagon, 'sobrevida-tb': FiWatch, hsri: FiActivity };

// Barras do mini-gráfico do mockup (alturas fixas — é decorativo, não um
// gráfico real, só para o hero parecer o produto rodando de verdade).
const BARRAS_MOCKUP = [38, 62, 45, 80, 55, 70, 48, 90, 60];

// Mockup estático do dashboard, para o hero mostrar o produto em vez de só
// descrevê-lo em texto — sem isso a landing lê como um panfleto, não como
// a interface de algo que já roda de verdade.
const DashboardMockup = () => (
    <div className="relative">
        <div className="absolute -inset-4 bg-gradient-to-br from-blue-200 to-indigo-200 rounded-[36px] blur-2xl opacity-40" aria-hidden="true"></div>
        <div className="relative bg-white rounded-3xl shadow-2xl border border-gray-100 overflow-hidden -rotate-1">
            <div className="flex items-center gap-1.5 px-4 py-3 border-b border-gray-100 bg-gray-50">
                <span className="w-2.5 h-2.5 rounded-full bg-red-300"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-amber-300"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-300"></span>
                <span className="ml-3 px-3 py-1 bg-white rounded-md text-[10px] text-gray-400 font-mono border border-gray-100">labsus.com.br</span>
            </div>
            <div className="p-6">
                <div className="flex items-center justify-between mb-5">
                    <div>
                        <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Moran Global</p>
                        <p className="font-bold text-gray-800 text-sm">Mortalidade Infantil &middot; TO, 2022</p>
                    </div>
                    <span className="flex items-center gap-1 text-[10px] font-black text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full">
                        <FiCheckCircle size={11} /> CONCLUÍDO
                    </span>
                </div>
                <div className="grid grid-cols-3 gap-3 mb-6">
                    {[
                        { valor: '139', label: 'municípios' },
                        { valor: '0.42', label: "Moran's I" },
                        { valor: 'p<0.01', label: 'significância' },
                    ].map((kpi) => (
                        <div key={kpi.label} className="bg-gray-50 rounded-xl p-3">
                            <p className="font-display text-xl font-semibold text-gray-900 [font-variant-numeric:tabular-nums]">{kpi.valor}</p>
                            <p className="text-[9px] text-gray-400 font-bold uppercase tracking-wide">{kpi.label}</p>
                        </div>
                    ))}
                </div>
                <div className="flex items-end gap-1.5 h-24 px-1">
                    {BARRAS_MOCKUP.map((altura, i) => (
                        <div
                            key={i}
                            className="flex-1 rounded-t-md bg-gradient-to-t from-blue-600 to-blue-400"
                            style={{ height: `${altura}%` }}
                        ></div>
                    ))}
                </div>
            </div>
        </div>
    </div>
);

const LandingPage = () => {
    usePageTitle('UFT | Analytical Hub');

    const categorias = getCatalogoPorCategoria(false);
    const totalModulos = PIPELINES.length;
    const totalIndicadores = Object.keys(INDICADORES_MAP).length;
    const totalSistemas = ORDEM_SISTEMAS.filter((s) => s !== 'MULTISSISTEMA').length;

    const destaques = CHAVES_DESTAQUE
        .map((chave) => PIPELINES.find((p) => p.key === chave))
        .filter(Boolean);

    return (
        <div className="-m-6 bg-white">
            {/* Barra superior */}
            <div className="max-w-6xl mx-auto px-6 pt-6 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <img src={LabSUSLogo} alt="LabSUS" className="h-7 w-7" />
                    <span className="font-black text-lg tracking-tight text-gray-800">Lab<span className="text-blue-600">SUS</span></span>
                </div>
                <div className="flex gap-2">
                    <Link to="/login" className="px-4 py-2 text-sm font-bold text-gray-600 hover:text-blue-600 transition">Entrar</Link>
                    <Link to="/register" className="px-4 py-2 text-sm font-bold bg-gray-900 text-white rounded-lg hover:bg-blue-600 transition">Criar conta</Link>
                </div>
            </div>

            {/* Hero */}
            <div
                className="relative overflow-hidden"
                style={{ backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(37,99,235,0.14) 1px, transparent 0)', backgroundSize: '28px 28px' }}
            >
                <div className="absolute inset-0 bg-gradient-to-b from-blue-50/60 via-white/40 to-white pointer-events-none" aria-hidden="true"></div>
                <div className="relative max-w-6xl mx-auto px-6 pt-14 pb-20 grid grid-cols-1 lg:grid-cols-2 gap-14 items-center">
                    <div>
                        <p className="text-[11px] font-black text-blue-600 uppercase tracking-[0.3em] mb-5">
                            Laboratório de Inteligência em Saúde &middot; UFT
                        </p>
                        <h1 className="font-display text-[2.5rem] md:text-5xl font-semibold text-gray-900 leading-[1.1] tracking-tight text-balance mb-6">
                            Dados brutos do SUS viram <span className="text-blue-600">decisão</span>, não planilha.
                        </h1>
                        <p className="text-lg text-gray-500 leading-relaxed mb-4">
                            Consolide SIM, SIH, SIA, SINASC, SINAN, CNES e IBGE num painel único e rode dezenas de
                            modelos estatísticos e de aprendizado de máquina sobre eles — direto no navegador, sem
                            escrever uma linha de código.
                        </p>
                        <p className="flex items-center gap-2 text-sm text-gray-400 font-medium mb-9">
                            <FiCheckCircle className="text-emerald-500 shrink-0" /> Dados reais do DATASUS, sem simulação.
                        </p>
                        <div className="flex items-center gap-4">
                            <Link to="/register" className="flex items-center gap-2 px-7 py-3.5 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 transition shadow-lg shadow-blue-600/20">
                                Começar agora <FiArrowRight />
                            </Link>
                            <Link to="/login" className="flex items-center gap-2 px-7 py-3.5 text-gray-700 font-bold hover:text-blue-600 transition">
                                <FiLogIn /> Já tenho conta
                            </Link>
                        </div>
                    </div>
                    <DashboardMockup />
                </div>

                {/* Números */}
                <div className="relative border-t border-gray-100 bg-white/70">
                    <div className="max-w-6xl mx-auto px-6 grid grid-cols-3 gap-6 py-10">
                        {[
                            { valor: `${totalModulos}+`, label: 'módulos e modelos' },
                            { valor: `${totalIndicadores}+`, label: 'indicadores de saúde' },
                            { valor: totalSistemas, label: 'sistemas do DATASUS' },
                        ].map((stat) => (
                            <div key={stat.label} className="text-center">
                                <p className="font-display text-4xl font-semibold text-gray-900 [font-variant-numeric:tabular-nums]">{stat.valor}</p>
                                <p className="text-xs text-gray-400 font-bold uppercase tracking-wide mt-1">{stat.label}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Como funciona */}
            <div className="bg-gray-50 border-b border-gray-100 py-20">
                <div className="max-w-5xl mx-auto px-6">
                    <h2 className="font-display text-2xl font-semibold text-gray-900 text-center mb-12">Como funciona</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {[
                            { titulo: 'Consolidar', texto: 'Escolha UFs, anos e indicadores. O LabSUS baixa e junta os dados brutos do DATASUS num painel único por município.' },
                            { titulo: 'Analisar', texto: 'Aplique o modelo certo para a pergunta: séries temporais, análise espacial, sobrevivência, risco individual e mais.' },
                            { titulo: 'Decidir', texto: 'Veja o resultado em dashboard interativo e baixe o CSV consolidado para usar em PowerBI, Qlik ou onde for preciso.' },
                        ].map((passo, i) => (
                            <div key={passo.titulo} className="relative">
                                <div className="flex items-center gap-3 mb-3">
                                    <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0 font-display font-semibold">
                                        {i + 1}
                                    </div>
                                    <span className="font-display text-lg font-semibold text-gray-900">{passo.titulo}</span>
                                </div>
                                <p className="text-sm text-gray-500 leading-relaxed">{passo.texto}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Modelos em destaque */}
            <div className="max-w-5xl mx-auto px-6 py-20">
                <h2 className="font-display text-2xl font-semibold text-gray-900 text-center mb-2">Alguns dos modelos</h2>
                <p className="text-sm text-gray-400 text-center mb-12">Uma amostra do que já está rodando — a lista completa fica disponível depois do login.</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                    {destaques.map((item) => {
                        const Icone = ICONES_DESTAQUE[item.key] || FiActivity;
                        return (
                            <div key={item.key} className="p-6 rounded-2xl border border-gray-100 hover:border-blue-200 hover:shadow-md transition-all bg-white">
                                <div className="flex items-start gap-4">
                                    <div className="p-2.5 rounded-xl bg-blue-50 text-blue-600 shrink-0">
                                        <Icone size={20} />
                                    </div>
                                    <div>
                                        <h3 className="font-bold text-gray-800 mb-1">{item.title}</h3>
                                        <p className="text-sm text-gray-500 leading-relaxed">{item.descricao}</p>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Categorias — grade compacta com contagem, não a lista inteira */}
            <div className="bg-gray-50 border-y border-gray-100 py-20">
                <div className="max-w-6xl mx-auto px-6">
                    <h2 className="font-display text-2xl font-semibold text-gray-900 text-center mb-12">Organizado por técnica e domínio de saúde</h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {categorias.map((categoria) => (
                            <div key={categoria.id} className="p-5 rounded-2xl bg-white border border-gray-100">
                                <div className="flex items-center justify-between mb-2">
                                    <div className="p-2 bg-gray-50 rounded-lg text-gray-500">
                                        <categoria.icon size={16} />
                                    </div>
                                    <span className="text-xs font-black text-gray-300 [font-variant-numeric:tabular-nums]">{categoria.pipelines.length}</span>
                                </div>
                                <h3 className="font-bold text-gray-800 text-sm leading-snug">{categoria.label}</h3>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Indicadores */}
            <div className="max-w-4xl mx-auto px-6 py-20 text-center">
                <h2 className="font-display text-2xl font-semibold text-gray-900 mb-4">De mortalidade infantil a doenças raras</h2>
                <p className="text-gray-500 leading-relaxed max-w-2xl mx-auto mb-8">
                    Mais de {totalIndicadores} indicadores já calculados, prontos para entrar num painel consolidado por
                    município e ano: mortalidade, saúde materno-infantil, doenças crônicas, agravos de notificação
                    compulsória, saúde do trabalhador, violência e qualidade da informação.
                </p>
                <div className="flex flex-wrap justify-center gap-2">
                    {ORDEM_SISTEMAS.filter((s) => s !== 'MULTISSISTEMA').map((sistema) => (
                        <span key={sistema} className="px-3 py-1.5 rounded-full bg-blue-50 text-blue-700 text-xs font-bold">
                            {SISTEMAS_ORIGEM[sistema].split(' — ')[0]}
                        </span>
                    ))}
                </div>
            </div>

            {/* CTA final */}
            <div className="max-w-5xl mx-auto px-6 pb-24">
                <div className="rounded-[32px] bg-gradient-to-br from-blue-600 to-indigo-700 p-12 text-center text-white">
                    <h2 className="font-display text-3xl font-semibold mb-3">Pronto para começar?</h2>
                    <p className="text-blue-100 mb-8 max-w-xl mx-auto">
                        Crie uma conta e monte seu primeiro painel de indicadores em minutos.
                    </p>
                    <Link to="/register" className="inline-flex items-center gap-2 px-8 py-4 bg-white text-blue-600 rounded-2xl font-bold hover:bg-blue-50 transition shadow-lg">
                        <FiUserPlus /> Criar conta
                    </Link>
                </div>
            </div>

            <footer className="py-10 border-t border-gray-100 flex flex-col items-center gap-4">
                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-[0.5em]">
                    Laboratório de Inteligência em Saúde &middot; 2026
                </p>
            </footer>
        </div>
    );
};

export default LandingPage;
