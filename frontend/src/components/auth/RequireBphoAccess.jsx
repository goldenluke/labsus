import React from 'react';
import { Link } from 'react-router-dom';
import { FiLock } from 'react-icons/fi';
import { useAuth } from '../../context/AuthContext';

const RequireBphoAccess = ({ children }) => {
  const { hasBphoAccess, authLoading } = useAuth();

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <p className="text-gray-600">Verificando permissões...</p>
      </div>
    );
  }

  if (!hasBphoAccess) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
        <FiLock size={40} className="text-gray-400 mb-4" />
        <h1 className="text-xl font-semibold text-gray-800 mb-2">Acesso restrito</h1>
        <p className="text-gray-600 max-w-md mb-6">
          Este recurso faz parte da BPHO/PopulationSpace e exige alto custo computacional,
          por isso está disponível apenas para usuários com acesso liberado.
          Fale com um administrador se precisar dele.
        </p>
        <Link to="/inicio" className="text-blue-600 hover:underline font-medium">
          Voltar para o início
        </Link>
      </div>
    );
  }

  return children;
};

export default RequireBphoAccess;
