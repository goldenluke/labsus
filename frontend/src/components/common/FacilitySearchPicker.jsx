import React, { useState, useEffect, useRef } from 'react';
import { FiSearch, FiX, FiPlus } from 'react-icons/fi';
import { searchFacilities } from '../../services/populationSpaceService';

// Substitui a antiga lista fixa de estabelecimentos por busca real contra a
// BPHO (por prefixo de código CNES -- a BPHO não modela nome/UF de
// estabelecimento, ver docstring de facility_search no backend) + uma lista
// de sugestões conhecidas para adicionar com um clique. `selected` é sempre
// um array de {facility_uri, uf}, não mais um array de strings cruzado
// contra uma lista estática.
export default function FacilitySearchPicker({ selected, onChange, suggestions = [] }) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState([]);
    const [searching, setSearching] = useState(false);
    const [searchError, setSearchError] = useState(null);
    const debounceRef = useRef(null);

    useEffect(() => {
        clearTimeout(debounceRef.current);
        const digits = query.replace(/\D/g, '');
        if (digits.length < 2) {
            setResults([]);
            setSearchError(null);
            return;
        }
        debounceRef.current = setTimeout(async () => {
            setSearching(true);
            setSearchError(null);
            try {
                const data = await searchFacilities(digits);
                setResults(data.facilities || []);
            } catch (err) {
                setSearchError(err.response?.data?.error || err.message || 'Erro na busca.');
            } finally {
                setSearching(false);
            }
        }, 350);
        return () => clearTimeout(debounceRef.current);
    }, [query]);

    const isSelected = (uri) => selected.some(s => s.facility_uri === uri);

    const add = (uri, uf = null) => {
        if (isSelected(uri)) return;
        onChange([...selected, { facility_uri: uri, uf }]);
    };

    const remove = (uri) => {
        onChange(selected.filter(s => s.facility_uri !== uri));
    };

    const setUf = (uri, uf) => {
        onChange(selected.map(s => s.facility_uri === uri ? { ...s, uf: uf.toUpperCase() || null } : s));
    };

    return (
        <div className="space-y-3">
            <div className="relative">
                <div className="flex items-center gap-2 p-2 border border-gray-300 rounded-xl focus-within:ring-2 focus-within:ring-blue-500">
                    <FiSearch className="text-gray-400 ml-1" size={16} />
                    <input
                        type="text"
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        placeholder="Buscar por código CNES (ex: 2077) -- só prefixo, mín. 2 dígitos"
                        className="flex-1 outline-none text-sm"
                    />
                    {searching && <span className="text-xs text-gray-400">buscando...</span>}
                </div>

                {searchError && <p className="text-xs text-red-600 mt-1">{searchError}</p>}

                {query.replace(/\D/g, '').length >= 2 && !searching && (
                    <div className="mt-1 max-h-40 overflow-y-auto border border-gray-100 rounded-xl divide-y divide-gray-50">
                        {results.length === 0 ? (
                            <p className="text-xs text-gray-400 p-2">Nenhum estabelecimento real encontrado com esse prefixo.</p>
                        ) : (
                            results.map(uri => (
                                <button
                                    key={uri}
                                    type="button"
                                    onClick={() => add(uri)}
                                    disabled={isSelected(uri)}
                                    className={`w-full text-left px-3 py-1.5 text-xs font-mono flex items-center justify-between
                                        ${isSelected(uri) ? 'text-gray-300 cursor-not-allowed' : 'text-gray-600 hover:bg-blue-50'}`}
                                >
                                    {uri}
                                    {!isSelected(uri) && <FiPlus size={12} />}
                                </button>
                            ))
                        )}
                    </div>
                )}
            </div>

            {suggestions.length > 0 && (
                <div>
                    <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Sugestões (dado já verificado)</span>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                        {suggestions.map(s => (
                            <button
                                key={s.facility_uri}
                                type="button"
                                onClick={() => add(s.facility_uri, s.uf)}
                                disabled={isSelected(s.facility_uri)}
                                className={`px-2.5 py-1 rounded-full text-xs font-bold border transition
                                    ${isSelected(s.facility_uri)
                                        ? 'bg-blue-50 border-blue-200 text-blue-400 cursor-not-allowed'
                                        : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-blue-50 hover:border-blue-200'}`}
                            >
                                {s.label}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            <div>
                <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">
                    Selecionados ({selected.length})
                </span>
                {selected.length === 0 ? (
                    <p className="text-xs text-gray-400 mt-1">Nenhum estabelecimento selecionado ainda.</p>
                ) : (
                    <div className="mt-1 space-y-1 max-h-48 overflow-y-auto pr-1">
                        {selected.map(s => (
                            <div key={s.facility_uri} className="flex items-center gap-2 p-1.5 bg-gray-50 rounded-lg border border-gray-100">
                                <span className="flex-1 text-xs font-mono text-gray-600">{s.facility_uri}</span>
                                <input
                                    type="text"
                                    value={s.uf || ''}
                                    onChange={e => setUf(s.facility_uri, e.target.value)}
                                    placeholder="UF"
                                    maxLength={2}
                                    className="w-12 p-1 text-xs text-center border border-gray-200 rounded"
                                    title="UF (opcional -- sem ela, composição demográfica fica ausente)"
                                />
                                <button type="button" onClick={() => remove(s.facility_uri)} className="text-gray-400 hover:text-red-500">
                                    <FiX size={14} />
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
