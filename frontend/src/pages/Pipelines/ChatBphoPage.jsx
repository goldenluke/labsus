import React, { useState, useRef, useEffect } from 'react';
import { FiSend, FiCpu, FiUser, FiCode } from 'react-icons/fi';
import ReactMarkdown from 'react-markdown';
import usePageTitle from '../../hooks/usePageTitle';
import InfoCard from '../../components/common/InfoCard';
import LoadingSpinner from '../../components/common/LoadingSpinner';
import { sendBphoChatMessage } from '../../services/bphoChatService';

const MARKDOWN_COMPONENTS = {
    p: ({ node, ...props }) => <p className="mb-2 last:mb-0 leading-relaxed" {...props} />,
    strong: ({ node, ...props }) => <strong className="font-bold" {...props} />,
    em: ({ node, ...props }) => <em className="italic" {...props} />,
    ul: ({ node, ...props }) => <ul className="list-disc list-inside mb-2 last:mb-0 space-y-0.5" {...props} />,
    ol: ({ node, ...props }) => <ol className="list-decimal list-inside mb-2 last:mb-0 space-y-0.5" {...props} />,
    li: ({ node, ...props }) => <li {...props} />,
    a: ({ node, ...props }) => <a className="underline hover:opacity-80" target="_blank" rel="noopener noreferrer" {...props} />,
    code: ({ node, ...props }) => <code className="px-1 py-0.5 rounded bg-black/10 font-mono text-[0.85em]" {...props} />,
    pre: ({ node, ...props }) => <pre className="mb-2 last:mb-0 p-2 rounded bg-black/10 overflow-x-auto whitespace-pre [&>code]:bg-transparent [&>code]:p-0" {...props} />,
};

const SUGGESTED_QUESTIONS = [
    {
        category: 'Contagens',
        items: [
            'Quantas Hospitalization existem no total?',
            'Quantas Affiliation existem no total?',
            'Quantas Person existem no armazenamento?',
            'Quantas NotifiableCaseInvestigation existem?',
        ],
    },
    {
        category: 'Definições',
        items: [
            'O que é uma Hospitalization?',
            'O que é um AIHRecord?',
            'Qual a diferença entre Approved, Rejected e RejectedWithError?',
            'O que é um HealthFacility?',
        ],
    },
    {
        category: 'Cruzando sistemas (o ponto real da BPHO)',
        items: [
            'Qual o estabelecimento com mais Hospitalization, e ele também tem vínculos profissionais (Affiliation) registrados?',
            'Quantos vínculos profissionais têm equipe (Team) vinculada?',
        ],
    },
    {
        category: 'Recorte temporal',
        items: [
            'Quantas admissões (Admission) aconteceram em dezembro de 2025?',
        ],
    },
    {
        category: 'Tempo de internação',
        items: [
            'Qual o tempo médio de internação no estabelecimento facility_2077396?',
        ],
    },
    {
        category: 'Comparar estabelecimentos (PopulationSpace/BioSpace)',
        items: [
            'Os estabelecimentos facility_2077396 e facility_0000434 são parecidos?',
        ],
    },
];

const ChatBphoPage = () => {
    usePageTitle('Chat com a BPHO');

    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    const handleSend = async (overrideText) => {
        const text = (overrideText ?? input).trim();
        if (!text || loading) return;

        const history = messages.map(m => ({ role: m.role, content: m.content }));
        const userMessage = { role: 'user', content: text };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setLoading(true);
        setError(null);

        try {
            const data = await sendBphoChatMessage(text, history);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: data.answer,
                sparqlQueries: data.sparql_queries || [],
            }]);
        } catch (err) {
            setError(err.response?.data?.error || err.message || 'Erro ao consultar o modelo local.');
        } finally {
            setLoading(false);
        }
    };

    const handleSuggestionClick = (question) => {
        if (loading) return;
        handleSend(question);
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="p-6 bg-gray-50 min-h-screen flex flex-col">
            <header className="mb-6 text-center">
                <h1 className="text-3xl font-black text-gray-800 tracking-tight uppercase italic">Chat com a BPHO</h1>
                <p className="text-gray-500 mt-2 text-lg">Pergunte em português sobre os dados e conceitos da ontologia.</p>
            </header>

            <div className="max-w-3xl mx-auto w-full flex-1 flex flex-col space-y-4">
                <InfoCard title="Como funciona">
                    <p className="text-sm leading-relaxed text-gray-600 font-medium">
                        Este chat roda inteiramente <strong>local</strong> (modelo Qwen3-Coder 30B via Ollama, sem API externa).
                        O modelo decide quando gerar e executar uma ou mais consultas <strong>SPARQL</strong> em sequência
                        contra o armazenamento da BPHO — inclusive perguntas que cruzam sistemas administrativos diferentes
                        (ex.: "esse estabelecimento também tem vínculo profissional registrado?") — e responde direto
                        usando as definições da ontologia para perguntas conceituais. Perguntas de <strong>similaridade entre
                        estabelecimentos</strong> (ex.: "esses dois são parecidos?") chamam o <strong>PopulationSpace</strong>
                        (BioSpace) por trás, que combina utilização hospitalar, força de trabalho e demografia numa distância
                        geométrica — essas respostas podem levar alguns minutos. Ele não sabe (e vai dizer isso) sobre
                        atributos que a BPHO não modela isoladamente, como sexo ou idade individual.
                    </p>
                </InfoCard>

                <div className="flex-1 bg-white rounded-2xl shadow-sm border border-gray-200 flex flex-col overflow-hidden" style={{ minHeight: '420px' }}>
                    <div className="flex-1 overflow-y-auto p-6 space-y-4">
                        {messages.length === 0 && (
                            <p className="text-sm text-gray-400 text-center pt-4 pb-2">
                                Escolha uma pergunta abaixo ou digite a sua.
                            </p>
                        )}
                        {messages.map((m, i) => (
                            <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                {m.role === 'assistant' && (
                                    <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0">
                                        <FiCpu size={16} />
                                    </div>
                                )}
                                <div className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm ${
                                    m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'
                                }`}>
                                    {m.role === 'assistant' ? (
                                        <ReactMarkdown components={MARKDOWN_COMPONENTS}>{m.content}</ReactMarkdown>
                                    ) : (
                                        <p className="whitespace-pre-wrap">{m.content}</p>
                                    )}
                                    {m.sparqlQueries && m.sparqlQueries.length > 0 && (
                                        <details className="mt-2 text-xs opacity-70">
                                            <summary className="cursor-pointer flex items-center gap-1">
                                                <FiCode size={12} /> {m.sparqlQueries.length} ferramenta(s)/consulta(s) usada(s)
                                            </summary>
                                            {m.sparqlQueries.map((q, qi) => (
                                                <pre key={qi} className="mt-1 p-2 bg-black/5 rounded overflow-x-auto">{q}</pre>
                                            ))}
                                        </details>
                                    )}
                                </div>
                                {m.role === 'user' && (
                                    <div className="w-8 h-8 rounded-full bg-blue-600 text-white flex items-center justify-center flex-shrink-0">
                                        <FiUser size={16} />
                                    </div>
                                )}
                            </div>
                        ))}
                        {loading && (
                            <div className="flex gap-3 justify-start">
                                <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0">
                                    <FiCpu size={16} />
                                </div>
                                <div className="rounded-2xl px-4 py-3 bg-gray-100 flex items-center gap-2">
                                    <LoadingSpinner size="sm" color="gray" />
                                    <span className="text-sm text-gray-500">Consultando o modelo local...</span>
                                </div>
                            </div>
                        )}
                        {error && <p className="text-sm text-red-600 text-center">{error}</p>}
                        <div ref={bottomRef} />
                    </div>

                    <div className="border-t border-gray-200 p-4 space-y-3">
                        {SUGGESTED_QUESTIONS.map(group => (
                            <div key={group.category} className="flex flex-wrap items-center gap-2">
                                <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest mr-1">
                                    {group.category}
                                </span>
                                {group.items.map(question => (
                                    <button
                                        key={question}
                                        onClick={() => handleSuggestionClick(question)}
                                        disabled={loading}
                                        className="text-xs px-3 py-1.5 rounded-full border border-gray-200 bg-gray-50 text-gray-600 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {question}
                                    </button>
                                ))}
                            </div>
                        ))}
                    </div>

                    <div className="border-t border-gray-200 p-4 flex gap-3">
                        <textarea
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Digite sua pergunta..."
                            rows={1}
                            disabled={loading}
                            className="flex-1 p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none transition text-sm resize-none"
                        />
                        <button
                            onClick={() => handleSend()}
                            disabled={loading || !input.trim()}
                            className={`px-5 rounded-xl font-bold text-white transition-all flex items-center gap-2
                                ${loading || !input.trim() ? 'bg-gray-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 active:scale-[0.98]'}`}
                        >
                            <FiSend size={16} />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ChatBphoPage;
