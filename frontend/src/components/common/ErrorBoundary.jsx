// src/components/common/ErrorBoundary.jsx (Crie este arquivo)

import React from 'react';

class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        // Atualiza o estado para que a próxima renderização mostre a UI de fallback.
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        // Você também pode registrar o erro em um serviço de relatórios de erro
        console.error("ErrorBoundary caught an error:", error, errorInfo);
        this.setState({
            error: error,
            errorInfo: errorInfo
        });
    }

    render() {
        if (this.state.hasError) {
            // Você pode renderizar qualquer UI de fallback personalizada
            return (
                <div className="p-6 bg-red-100 text-red-800 rounded-lg shadow-md m-4">
                <h2 className="text-xl font-bold mb-2">Ops! Algo deu errado.</h2>
                <p className="mb-2">Por favor, tente recarregar a página ou contate o suporte se o problema persistir.</p>
                {this.props.debug && ( // Mostra detalhes do erro apenas em modo de depuração
                    <details className="mt-4 text-sm">
                    <summary>Detalhes do Erro (apenas em DEBUG)</summary>
                    <pre className="whitespace-pre-wrap break-words text-xs mt-2 p-2 bg-red-50 rounded-md">
                    {this.state.error && this.state.error.toString()}
                    <br />
                    {this.state.errorInfo && this.state.errorInfo.componentStack}
                    </pre>
                    </details>
                )}
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
