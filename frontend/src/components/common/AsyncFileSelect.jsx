import React, { useState, useEffect } from 'react';
import AsyncSelect from 'react-select/async';
import axios from 'axios';
import { FILE_TYPE_PLACEHOLDERS } from '../../config/fileTypes';

const AsyncFileSelect = ({ value, onChange, fileType, isClearable = false, placeholder: customPlaceholder }) => {
    // ⭐ NOVO ESTADO PARA GUARDAR A OPÇÃO INICIAL/ATUAL ⭐
    const [currentOption, setCurrentOption] = useState(null);

    // Efeito para carregar os detalhes do arquivo inicial se um ID for fornecido
    useEffect(() => {
        const fetchInitialOption = async () => {
            if (value && (!currentOption || currentOption.value !== value)) {
                try {
                    const token = localStorage.getItem('authToken');
                    const response = await axios.get(`/api/files/${value}/`, {
                        headers: { 'Authorization': `Token ${token}` },
                    });
                    const file = response.data;
                    setCurrentOption({
                        value: file.id,
                        label: `${file.filename} (Upload: ${new Date(file.uploaded_at).toLocaleDateString()})`,
                                     fileObject: file
                    });
                } catch (error) {
                    console.error("Erro ao carregar opção inicial:", error);
                    setCurrentOption(null);
                }
            } else if (!value) {
                setCurrentOption(null);
            }
        };
        fetchInitialOption();
    }, [value]);


    const loadOptions = async (inputValue) => {
        try {
            const token = localStorage.getItem('authToken');
            const response = await axios.get('/api/files/', {
                headers: { 'Authorization': `Token ${token}` },
                params: {
                    search: inputValue,
                    file_type: fileType,
                }
            });
            const options = response.data.results.map(file => ({
                value: file.id,
                label: `${file.filename} (Upload: ${new Date(file.uploaded_at).toLocaleDateString()})`,
                                                               fileObject: file
            }));
            return options;
        } catch (error) {
            console.error(`Erro ao carregar arquivos de ${fileType}:`, error);
            return [];
        }
    };

    const handleChange = (selectedOption) => {
        setCurrentOption(selectedOption); // Atualiza o estado interno
        onChange(selectedOption); // Passa o objeto completo para a página pai
    };

    const placeholderText = customPlaceholder || `Digite para buscar por ${FILE_TYPE_PLACEHOLDERS[fileType] || 'arquivos'}...`;

    return (
        <AsyncSelect
        cacheOptions
        defaultOptions
        loadOptions={loadOptions}
        value={currentOption} // Usa o estado interno
        onChange={handleChange}
        placeholder={placeholderText}
        isClearable={isClearable}
        noOptionsMessage={() => "Nenhum arquivo encontrado"}
        loadingMessage={() => "Buscando..."}
        />
    );
};

export default AsyncFileSelect;
