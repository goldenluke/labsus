import React, { useState, useEffect } from 'react';
import { FiBookOpen } from 'react-icons/fi';
import { getBphoClasses } from '../../services/ontologiaService';

// Painel supletivo: mostra a definição formal (rdfs:label/rdfs:comment) de classes
// da BPHO (Brazilian Public Health Ontology) relevantes para os dados exibidos na
// página. Não substitui os dicionários de código de campo do DATASUS (SEXO,
// RACA_COR, CID etc.) já usados nas páginas — isso é um problema diferente
// (tradução de código bruto), enquanto este painel explica os conceitos
// estruturais por trás dos dados (o que é uma Hospitalization, um AIHRecord...).
const BphoDefinitionsPanel = ({ classNames, title = 'Sobre estes dados (BPHO)' }) => {
    const [definitions, setDefinitions] = useState([]);
    const [status, setStatus] = useState('loading'); // 'loading' | 'ready' | 'unavailable'

    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const classes = await getBphoClasses();
                if (cancelled) return;
                const byName = Object.fromEntries(classes.map(c => [c.name, c]));
                const found = classNames
                    .map(name => byName[name])
                    .filter(c => c && (c.label || c.comment));
                setDefinitions(found);
                setStatus('ready');
            } catch (err) {
                if (!cancelled) setStatus('unavailable');
            }
        })();
        return () => { cancelled = true; };
    }, [classNames]);

    if (status === 'unavailable' || (status === 'ready' && definitions.length === 0)) {
        return null;
    }

    return (
        <div className="bg-indigo-50 border-l-4 border-indigo-400 p-4 rounded-r-lg text-gray-800 mb-8">
            <h3 className="font-semibold text-lg flex items-center">
                <FiBookOpen className="mr-2 flex-shrink-0" />
                {title}
            </h3>
            <p className="text-xs text-gray-500 mt-1 pl-6">
                Definições formais da <a href="https://github.com/goldenluke/BPHO" target="_blank" rel="noopener noreferrer" className="underline hover:text-indigo-600">BPHO (Brazilian Public Health Ontology)</a>, obtidas via SPARQL — complementam, sem substituir, os dicionários de código de campo abaixo.
            </p>
            {status === 'loading' ? (
                <p className="text-sm mt-2 pl-6 text-gray-400">Carregando definições...</p>
            ) : (
                <dl className="mt-3 pl-6 space-y-2">
                    {definitions.map(def => (
                        <div key={def.uri}>
                            <dt className="text-sm font-bold text-indigo-800">{def.label || def.name}</dt>
                            {def.comment && <dd className="text-sm text-gray-600">{def.comment}</dd>}
                        </div>
                    ))}
                </dl>
            )}
        </div>
    );
};

export default BphoDefinitionsPanel;
