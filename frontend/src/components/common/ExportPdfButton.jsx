// src/components/common/ExportPdfButton.jsx

import React, { useCallback } from 'react';
import { FiFileText } from 'react-icons/fi'; // Ícone para o PDF
import html2canvas from 'html2canvas';      // Para capturar o DOM
import { jsPDF } from 'jspdf';               // Para gerar o PDF

/**
 * Componente de botão para exportar o conteúdo de um elemento para PDF.
 * @param {object} props - As propriedades do componente.
 * @param {React.RefObject} contentRef - Uma ref para o elemento DOM que contém o conteúdo a ser exportado.
 * @param {string} filename - O nome do arquivo PDF a ser gerado (ex: "relatorio_indicadores.pdf").
 * @param {string} title - Título que aparecerá no cabeçalho do PDF (se a captura começar do <h1>, pode ser opcional).
 */
const ExportPdfButton = ({ contentRef, filename = 'relatorio.pdf', title = 'Relatório' }) => {

    const downloadPdf = useCallback(() => {
        if (!contentRef.current) {
            console.error("Elemento de referência para captura de PDF não encontrado.");
            alert("Não foi possível gerar o PDF. Conteúdo não encontrado.");
            return;
        }

        const input = contentRef.current;
        const pdfFileName = `${filename.replace(/\.pdf$/, '')}.pdf`; // Garante extensão .pdf

        // Opcional: Adicionar um spinner ou feedback visual aqui
        // setGeneratingPdf(true);

        html2canvas(input, {
            useCORS: true, // Importante se houver imagens ou SVGs de outras origens
            scale: 2,     // Aumenta a resolução da captura (2x para melhor qualidade)
        logging: false, // Desativar logs do html2canvas para produção
        // Você pode adicionar um onclone para manipular o DOM antes da captura,
        // por exemplo, ocultar elementos não desejados no PDF.
        onclone: (clonedDocument) => {
            // Exemplo: se houver um botão de download que você não quer no PDF
            // const btn = clonedDocument.getElementById('download-button-id');
            // if (btn) btn.style.display = 'none';
        }
        })
        .then(canvas => {
            const imgData = canvas.toDataURL('image/png');
            const pdf = new jsPDF('p', 'mm', 'a4'); // 'p' retrato, 'mm' unidades, 'a4' tamanho
            const imgWidth = pdf.internal.pageSize.getWidth(); // Largura da página PDF
            const pageHeight = pdf.internal.pageSize.getHeight(); // Altura da página PDF
            const imgHeight = canvas.height * imgWidth / canvas.width; // Altura da imagem no PDF

            let heightLeft = imgHeight;
            let position = 0;

            // Adiciona a primeira imagem
            pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
            heightLeft -= pageHeight;

            // Se o conteúdo for maior que uma página, adiciona páginas extras
            while (heightLeft > 0) {
                position = -heightLeft; // Move a imagem para a posição correta na nova página
                pdf.addPage();
                pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
                heightLeft -= pageHeight;
            }

            pdf.save(pdfFileName);
            // setGeneratingPdf(false); // Esconde spinner
            // Opcional: feedback de sucesso
            // alert("PDF gerado com sucesso!");

        }).catch(err => {
            console.error("Erro ao gerar PDF:", err);
            // setGeneratingPdf(false); // Esconde spinner
            alert("Ocorreu um erro ao gerar o PDF. Por favor, tente novamente. Detalhes no console.");
        });
    }, [contentRef, filename, title]); // Dependências do useCallback

    return (
        <button
        onClick={downloadPdf}
        className="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded inline-flex items-center flex-shrink-0"
        title={`Baixar ${filename}`}
        >
        <FiFileText className="mr-2" /> Baixar PDF
        </button>
    );
};

export default ExportPdfButton;
