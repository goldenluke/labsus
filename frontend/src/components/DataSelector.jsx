import React, { useState, useEffect } from 'react';
import axios from 'axios';
import LoadingSpinner from './common/LoadingSpinner';

/**
 * Componente DataSelector Flexível
 * Funciona de duas maneiras:
 * 1. MODO NÃO CONTROLADO (padrão): Busca a sua própria lista de ficheiros se a prop 'files' não for fornecida.
 * 2. MODO CONTROLADO: Usa a lista de ficheiros e o estado de loading passados via props.
 *
 * @param {Array} [files] - (Opcional) A lista de ficheiros para exibir. Se fornecida, ativa o modo controlado.
 * @param {string} selectedValue - O ID do ficheiro atualmente selecionado.
 * @param {function} onChange - A função a ser chamada quando um novo ficheiro é selecionado.
 * @param {boolean} [isLoading] - (Opcional) O estado de carregamento controlado externamente.
 * @param {string} [label] - O texto do rótulo para o seletor.
 * @param {string} [fileType] - (Opcional) Filtra os ficheiros por tipo no modo não controlado.
 */
const DataSelector = ({ files: externalFiles, selectedValue, onChange, isLoading: externalLoading, label, fileType }) => {

    // Estados internos para o modo não controlado
    const [internalFiles, setInternalFiles] = useState([]);
    const [internalLoading, setInternalLoading] = useState(false);
    const [error, setError] = useState('');

    // Efeito para buscar dados apenas se o componente estiver em modo não controlado
    useEffect(() => {
        // Se 'externalFiles' foi fornecido, o componente está em modo controlado e não deve buscar dados.
        if (externalFiles !== undefined) {
            return;
        }

        const fetchFileList = async () => {
            setInternalLoading(true);
            setError('');
            try {
                const token = localStorage.getItem('authToken');
                const params = fileType ? { file_type: fileType } : {};
                const response = await axios.get('/api/files/', {
                    headers: { 'Authorization': `Token ${token}` },
                    params: params
                });
                setInternalFiles(response.data.results || []);
            } catch (err) {
                console.error("Erro no DataSelector ao buscar a lista de ficheiros:", err);
                setError('Não foi possível carregar a lista de arquivos.');
            } finally {
                setInternalLoading(false);
            }
        };

        fetchFileList();
    }, [externalFiles, fileType]); // Executa se externalFiles for undefined

    // Determina quais dados e estado de loading usar
    const files = externalFiles !== undefined ? externalFiles : internalFiles;
    const isLoading = externalLoading !== undefined ? externalLoading : internalLoading;

    if (isLoading) {
        return (
            <div className="flex items-center space-x-2 text-gray-500">
            <LoadingSpinner size="sm" />
            <span>A carregar lista de arquivos...</span>
            </div>
        );
    }

    if (error) {
        return <p className="text-red-500 text-sm">{error}</p>;
    }

    if (!files || files.length === 0) {
        return <p className="text-gray-500">Nenhum arquivo disponível para seleção.</p>;
    }

    return (
        <label className="flex flex-col font-semibold w-full">
        {label || 'Selecione o arquivo de análise:'}
        <select
        value={selectedValue || ''}
        onChange={(e) => onChange(e.target.value)} // Chama a função passada via props
        className="p-2 border rounded-md mt-1 font-normal bg-white"
        >
        <option value="">-- Selecione um arquivo --</option>
        {files.map((file) => (
            <option key={file.id} value={file.id}>
            {file.filename}
            </option>
        ))}
        </select>
        </label>
    );
};

export default DataSelector;
