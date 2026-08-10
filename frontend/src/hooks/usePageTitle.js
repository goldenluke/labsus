// === Início do arquivo: src/hooks/usePageTitle.js (NOVO ARQUIVO) ===

import { useEffect } from 'react';

const usePageTitle = (title) => {
    useEffect(() => {
        const baseTitle = 'LabSUS';
        if (title) {
            document.title = `${baseTitle} - ${title}`;
        } else {
            document.title = baseTitle;
        }

        // Opcional: Retornar a uma função de limpeza para redefinir o título
        // quando o componente for desmontado.
        return () => {
            document.title = baseTitle;
        };
    }, [title]); // O efeito será executado novamente sempre que o 'title' mudar
};

export default usePageTitle;
