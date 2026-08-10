import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate, Link } from 'react-router-dom';
import { FiUser, FiLock, FiMail, FiUserPlus, FiArrowRight, FiShield, FiAlertTriangle } from 'react-icons/fi';
import LabSUSLogo from '../assets/lab_icon.png';
import LoadingSpinner from '../components/common/LoadingSpinner';
import usePageTitle from '../hooks/usePageTitle';

const RegisterPage = () => {
    usePageTitle('Criar Conta');

    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [password2, setPassword2] = useState('');

    const [errors, setErrors] = useState({});
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setErrors({});

        // Validação básica de igualdade no cliente
        if (password !== password2) {
            setErrors({ password: 'As senhas digitadas não coincidem.' });
            setLoading(false);
            return;
        }

        try {
            // CORREÇÃO CRÍTICA: O Django espera 'password1' e 'password2'
            await axios.post('/api/auth/registration/', {
                username,
                email,
                password1: password,
                password2: password2,
            });

            // Redireciona para o login com mensagem de sucesso
            navigate('/login', {
                state: { message: 'Conta criada com sucesso! Entre com suas credenciais.' }
            });

        } catch (err) {
            if (err.response && err.response.data) {
                const backendErrors = err.response.data;
                const formattedErrors = {};

                // Mapeia os erros do Django para o nosso estado local. Erros
                // que não têm um campo próprio no formulário (non_field_errors,
                // como "a senha é parecida demais com o usuário", ou qualquer
                // chave inesperada) caem em `general` — sem isso, o back-end
                // responde 400 mas a tela não mostra nada, como se o clique
                // não tivesse feito nada.
                for (const key in backendErrors) {
                    const message = Array.isArray(backendErrors[key])
                        ? backendErrors[key].join(' ')
                        : backendErrors[key];

                    if (key === 'password1' || key === 'password2') {
                        formattedErrors.password = formattedErrors.password
                            ? `${formattedErrors.password} ${message}`
                            : message;
                    } else if (key === 'username' || key === 'email') {
                        formattedErrors[key] = message;
                    } else {
                        formattedErrors.general = formattedErrors.general
                            ? `${formattedErrors.general} ${message}`
                            : message;
                    }
                }
                setErrors(formattedErrors);
            } else {
                setErrors({ general: 'Não foi possível conectar ao servidor.' });
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-5xl w-full bg-white rounded-[40px] shadow-2xl overflow-hidden flex flex-col md:flex-row-reverse border border-gray-100">

        {/* COLUNA DA DIREITA (FORMULÁRIO) */}
        <div className="w-full md:w-1/2 p-10 md:p-16 flex flex-col justify-center">
        <div className="mb-10 text-center md:text-left">
        <img src={LabSUSLogo} alt="LabSUS" className="h-12 w-12 mb-6 mx-auto md:mx-0" />
        <h1 className="text-3xl font-black text-gray-900 tracking-tighter uppercase">
        Nova <span className="text-blue-600">Conta</span>
        </h1>
        <p className="text-gray-400 text-xs font-bold uppercase tracking-widest mt-2">
        Acesso ao Sistema de Inteligência
        </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
        <div className="relative group">
        <label className="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2 ml-1">Usuário</label>
        <div className="relative">
        <FiUser className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
        <input
        type="text"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="ex: gestor_saude"
        className="w-full pl-12 pr-4 py-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 transition outline-none text-gray-700 font-medium"
        required
        />
        </div>
        {errors.username && <p className="text-red-500 text-[10px] font-bold mt-1 ml-1">{errors.username}</p>}
        </div>

        <div className="relative group">
        <label className="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2 ml-1">E-mail</label>
        <div className="relative">
        <FiMail className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
        <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="email@instituicao.gov.br"
        className="w-full pl-12 pr-4 py-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 transition outline-none text-gray-700 font-medium"
        required
        />
        </div>
        {errors.email && <p className="text-red-500 text-[10px] font-bold mt-1 ml-1">{errors.email}</p>}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="relative group">
        <label className="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2 ml-1">Senha</label>
        <div className="relative">
        <FiLock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
        <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="••••••••"
        className="w-full pl-11 pr-4 py-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 transition outline-none text-gray-700 font-medium"
        required
        />
        </div>
        </div>
        <div className="relative group">
        <label className="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2 ml-1">Confirmar</label>
        <div className="relative">
        <FiLock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
        <input
        type="password"
        value={password2}
        onChange={(e) => setPassword2(e.target.value)}
        placeholder="••••••••"
        className="w-full pl-11 pr-4 py-3.5 bg-gray-50 border-none rounded-2xl focus:ring-2 focus:ring-blue-500 transition outline-none text-gray-700 font-medium"
        required
        />
        </div>
        </div>
        </div>

        {(errors.password || errors.general) && (
            <p className="text-red-500 text-[10px] font-bold bg-red-50 p-3 rounded-xl border border-red-100 flex items-center gap-2">
            <FiAlertTriangle className="shrink-0" /> {errors.password || errors.general}
            </p>
        )}

        <button
        type="submit"
        disabled={loading}
        className="w-full bg-gray-900 hover:bg-blue-600 text-white font-black py-4 rounded-2xl shadow-xl transition-all duration-300 flex items-center justify-center gap-3 group disabled:bg-gray-300 active:scale-[0.98] mt-4"
        >
        {loading ? (
            <LoadingSpinner size="sm" color="white" />
        ) : (
            <>
            CRIAR CONTA DE ACESSO <FiArrowRight className="group-hover:translate-x-1 transition-transform" />
            </>
        )}
        </button>
        </form>

        <div className="mt-10 pt-8 border-t border-gray-50 text-center">
        <p className="text-sm text-gray-500 font-medium">
        Já possui credenciais? <br className="md:hidden" />
        <Link to="/login" className="text-blue-600 font-black uppercase text-xs tracking-widest hover:underline ml-2">
        Fazer Login
        </Link>
        </p>
        </div>
        </div>

        {/* COLUNA DA ESQUERDA: IDENTIDADE VISUAL */}
        <div className="hidden md:flex w-1/2 bg-gradient-to-br from-blue-700 via-indigo-700 to-slate-900 p-16 flex-col justify-between relative overflow-hidden">
        <div className="absolute top-0 left-0 p-20 opacity-10">
        <FiUserPlus size={300} className="text-white" />
        </div>
        <div className="absolute top-1/2 right-[-100px] w-80 h-80 bg-blue-400/20 rounded-full blur-3xl"></div>

        <div className="relative z-10">
        <div className="bg-white/10 backdrop-blur-md p-6 rounded-[32px] border border-white/20 inline-block mb-10 shadow-xl">
        <img src={LabSUSLogo} alt="LabSUS" className="h-16 w-16 brightness-0 invert" />
        </div>
        <h2 className="text-5xl font-black text-white leading-tight tracking-tighter mb-4">
        Expanda sua <br /> capacidade de <br /> <span className="text-indigo-300">análise.</span>
        </h2>
        <p className="text-blue-100 text-lg leading-relaxed max-w-sm font-medium">
        Cadastre-se para processar indicadores, treinar modelos de risco e monitorar a dinâmica da saúde.
        </p>
        </div>

        <div className="relative z-10">
        <div className="flex gap-4 mb-4">
        <div className="h-1 w-4 bg-white/30 rounded-full"></div>
        <div className="h-1 w-8 bg-blue-400 rounded-full"></div>
        <div className="h-1 w-4 bg-white/30 rounded-full"></div>
        </div>
        <p className="text-blue-200 text-[10px] font-black uppercase tracking-[0.4em] flex items-center gap-2">
        <FiShield /> Acesso Institucional Seguro
        </p>
        </div>
        </div>
        </div>
        </div>
    );
};

export default RegisterPage;
