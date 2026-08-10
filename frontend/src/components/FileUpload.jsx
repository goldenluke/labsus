// src/components/FileUpload.jsx
import React, { useState } from 'react';
import axios from 'axios';

// O componente recebe uma função 'onUploadSuccess' como prop.
// Ele irá chamar esta função depois de um upload bem-sucedido
// para que a página principal (DashboardPage) possa atualizar a lista de ficheiros.
const FileUpload = ({ onUploadSuccess }) => {
    const [file, setFile] = useState(null);
    const [filename, setFilename] = useState('');
    const [description, setDescription] = useState('');
    const [error, setError] = useState('');
    const [uploading, setUploading] = useState(false);

    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setFile(selectedFile);
            // Preenche o nome do ficheiro automaticamente, removendo a extensão .csv se existir
            setFilename(selectedFile.name.replace(/\.csv$/, ''));
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!file) {
            setError('Por favor, selecione um ficheiro.');
            return;
        }

        setUploading(true);
        setError('');

        // Usamos FormData para enviar ficheiros via HTTP
        const formData = new FormData();
        formData.append('file', file);
        formData.append('filename', filename);
        formData.append('description', description);

        const token = localStorage.getItem('authToken');

        try {
            // Faz a requisição POST para o nosso endpoint /api/files/
            await axios.post('http://127.0.0.1:8000/api/files/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                    'Authorization': `Token ${token}`,
                },
            });

            // Limpa o formulário após o sucesso
            e.target.reset(); // Reseta o input de ficheiro
            setFile(null);
            setFilename('');
            setDescription('');

            // Chama a função de callback para informar a página principal que a lista precisa de ser atualizada
            onUploadSuccess();

        } catch (err) {
            setError('Ocorreu um erro ao fazer o upload. Verifique o ficheiro e tente novamente.');
            console.error('Erro de upload:', err);
        } finally {
            setUploading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="bg-gray-50 p-6 rounded-lg border">
        <h3 className="text-lg font-semibold mb-4 text-gray-700">Novo Upload</h3>
        {error && <p className="text-red-500 text-sm mb-4">{error}</p>}

        <div className="mb-4">
        <label className="block text-gray-700 mb-2" htmlFor="file-input">Ficheiro CSV</label>
        <input
        id="file-input"
        type="file"
        onChange={handleFileChange}
        className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
        accept=".csv"
        required
        />
        </div>

        <div className="mb-4">
        <label className="block text-gray-700 mb-2" htmlFor="filename">Nome do Ficheiro</label>
        <input
        id="filename"
        type="text"
        value={filename}
        onChange={(e) => setFilename(e.target.value)}
        className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        placeholder="Ex: indicadores_2024.csv"
        required
        />
        </div>

        <div className="mb-6">
        <label className="block text-gray-700 mb-2" htmlFor="description">Descrição (Opcional)</label>
        <textarea
        id="description"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        rows="2"
        />
        </div>

        <button
        type="submit"
        className="w-full bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700 transition duration-300 disabled:bg-gray-400"
        disabled={uploading}
        >
        {uploading ? 'A enviar...' : 'Enviar Ficheiro'}
        </button>
        </form>
    );
};

export default FileUpload;
