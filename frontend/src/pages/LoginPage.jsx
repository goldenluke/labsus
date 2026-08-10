import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { FiUser, FiLock, FiLogIn, FiArrowRight, FiShield } from 'react-icons/fi';
import LabSUSLogo from '../assets/lab_icon.png';
import LoadingSpinner from '../components/common/LoadingSpinner';
import usePageTitle from '../hooks/usePageTitle';

const LoginPage = () => {
    usePageTitle('Login');

    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [loading, setLoading] = useState(false);

    const navigate = useNavigate();
    const location = useLocation();

    useEffect(() => {
        if (location.state?.message) {
            setSuccessMessage(location.state.message);
        }
    }, [location.state]);

    const handleLoginSuccess = (token) => {
        localStorage.setItem('authToken', token);
        axios.defaults.headers.common['Authorization'] = `Token ${token}`;
        navigate('/inicio');
        window.location.reload();
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            const response = await axios.post('/api/auth/login/', {
                username, password,
            });
            handleLoginSuccess(response.data.key);
        } catch (err) {
            setError('Credenciais inválidas. Verifique seu usuário e senha.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-5xl w-full bg-white rounded-[40px] shadow-2xl overflow-hidden flex flex-col md:flex-row border border-gray-100">

        {/* COLUNA DA ESQUERDA: FORMULÁRIO */}
        <div className="w-full md:w-1/2 p-10 md:p-16 flex flex-col justify-center">
        <div className="mb-10 text-center md:text-left">
        <img src={LabSUSLogo} alt="LabSUS" className="h-12 w-12 mb-6 mx-auto md:mx-0" />
        <h1 className="text-3xl font-black text-gray-900 tracking-tighter uppercase">
        Acesso ao <span className="text-blue-600">Hub</span>
        </h1>
        <p className="text-gray-400 text-xs font-bold uppercase tracking-widest mt-2">
        Analytical Decision Support System
        </p>
        </div>

        {successMessage && (
            <div className="mb-6 p-4 bg-emerald-50 border border-emerald-100 rounded-2xl text-emerald-700 text-sm font-medium flex items-center gap-3">
            <FiShield className="shrink-0" /> {successMessage}
            </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
        <div className="relative group">
        <label className="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2 ml-1">Usuário / Identificador</label>
        <div className="relative">
        <FiUser className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
        <input
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="ex: gestor_saude"
        className="w-full pl-12 pr-4 py-4 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 transition outline-none text-gray-700 font-medium"
        required
        />
        </div>
        </div>

        <div className="relative group">
        <label className="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2 ml-1">Senha de Acesso</label>
        <div className="relative">
        <FiLock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
        <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="••••••••"
        className="w-full pl-12 pr-4 py-4 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 transition outline-none text-gray-700 font-medium"
        required
        />
        </div>
        </div>

        {error && (
            <p className="text-red-500 text-xs font-bold bg-red-50 p-3 rounded-xl border border-red-100 flex items-center gap-2">
            <FiAlertTriangle /> {error}
            </p>
        )}

        <button
        type="submit"
        disabled={loading}
        className="w-full bg-gray-900 hover:bg-blue-600 text-white font-black py-4 rounded-2xl shadow-xl transition-all duration-300 flex items-center justify-center gap-3 group disabled:bg-gray-300 active:scale-[0.98]"
        >
        {loading ? (
            <LoadingSpinner size="sm" color="white" />
        ) : (
            <>
            AUTENTICAR NO SISTEMA <FiArrowRight className="group-hover:translate-x-1 transition-transform" />
            </>
        )}
        </button>
        </form>

        <div className="mt-12 pt-8 border-t border-gray-50 text-center">
        <p className="text-sm text-gray-500 font-medium">
        Ainda não possui credenciais? <br className="md:hidden" />
        <Link to="/register" className="text-blue-600 font-black uppercase text-xs tracking-widest hover:underline ml-2">
        Criar Conta de Acesso
        </Link>
        </p>
        </div>
        </div>

        {/* COLUNA DA DIREITA: IDENTIDADE VISUAL (SALA DE SITUAÇÃO) */}
        <div className="hidden md:flex w-1/2 bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-900 p-16 flex-col justify-between relative overflow-hidden">
        {/* Elementos Decorativos de UI */}
        <div className="absolute top-0 right-0 p-20 opacity-10">
        <FiLogIn size={300} className="text-white" />
        </div>
        <div className="absolute bottom-[-50px] left-[-50px] w-64 h-64 bg-white/10 rounded-full blur-3xl"></div>

        <div className="relative z-10">
        <div className="bg-white/10 backdrop-blur-md p-6 rounded-[32px] border border-white/20 inline-block mb-10 shadow-xl">
        <img src={LabSUSLogo} alt="LabSUS" className="h-16 w-16 brightness-0 invert" />
        </div>
        <h2 className="text-5xl font-black text-white leading-tight tracking-tighter mb-4">
        Inteligência <br /> que salva <br /> <span className="text-blue-300">vidas.</span>
        </h2>
        <p className="text-blue-100 text-lg leading-relaxed max-w-sm font-medium">
        Transformando Big Data em ações estratégicas para o Sistema Único de Saúde.
        </p>
        </div>

        <div className="relative z-10 mt-20">
        <div className="flex gap-4 mb-4">
        <div className="h-1 w-8 bg-blue-400 rounded-full"></div>
        <div className="h-1 w-4 bg-white/30 rounded-full"></div>
        <div className="h-1 w-4 bg-white/30 rounded-full"></div>
        </div>
        <p className="text-blue-200 text-[10px] font-black uppercase tracking-[0.4em]">
        LabSUS Platform • v2.5.0
        </p>
        </div>
        </div>
        </div>
        </div>
    );
};

// Ícone de alerta interno para o form
const FiAlertTriangle = () => (
    <svg stroke="currentColor" fill="none" strokeWidth="2" viewBox="0 0 24 24" strokeLinecap="round" strokeLinejoin="round" height="14" width="14" xmlns="http://www.w3.org/2000/svg">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
    <line x1="12" y1="9" x2="12" y2="13"></line>
    <line x1="12" y1="17" x2="12.01" y2="17"></line>
    </svg>
);

export default LoginPage;
