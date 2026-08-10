import "./api/axiosConfig";
import MapaRiscoTO from "./pages/mapa/MapaRiscoTO";
import React, { useEffect, useState } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import Cookies from 'js-cookie';
import { FiMenu, FiX } from 'react-icons/fi';

// Importar suas páginas
import CsvManagerPage from './pages/CsvManagerPage';
import AnalisePorEstadoPage from './pages/Dashboards/AnalisePorEstadoPage';
import AnalisePorMunicipioPage from './pages/Dashboards/AnalisePorMunicipioPage';
import VisaoGeralPage from './pages/Dashboards/VisaoGeralPage';
import KMeansPerfisSaudePage from './pages/Dashboards/KMeansPerfisSaudePage';
import PredictionInternacoesViewerPage from './pages/Dashboards/PredictionInternacoesViewerPage';
import TaskHistoryPage from './pages/TaskHistoryPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import PipelineIndicadoresPage from './pages/Pipelines/PipelineIndicadoresPage';
import KMeansOrchestrationPage from './pages/Pipelines/KMeansOrchestrationPage';
import ArchetypeCreatorPage from './pages/Pipelines/ArchetypeCreatorPage';
import PipelinePredicaoInternacoesPage from './pages/Pipelines/PipelinePredicaoInternacoesPage';
import HomePage from './pages/HomePage';
import LandingPage from './pages/LandingPage';
import PipelineRegressaoObitosPage from './pages/Pipelines/PipelineRegressaoObitosPage';
import RegressaoObitosViewerPage from './pages/Dashboards/RegressaoObitosViewerPage';
import PipelineFluxoPacientesPage from './pages/Pipelines/PipelineFluxoPacientesPage';
import FluxoPacientesViewerPage from './pages/Dashboards/FluxoPacientesViewerPage';
import PipelineRiscoReadmissaoPage from './pages/Pipelines/PipelineRiscoReadmissaoPage';
import ReadmissaoViewerPage from './pages/Dashboards/ReadmissaoViewerPage';
import PipelineCustoInternacaoPage from './pages/Pipelines/PipelineCustoInternacaoPage';
import CustoInternacaoViewerPage from './pages/Dashboards/CustoInternacaoViewerPage';
import PipelineDeteccaoSurtosPage from './pages/Pipelines/PipelineDeteccaoSurtosPage';
import DeteccaoSurtosViewerPage from './pages/Dashboards/DeteccaoSurtosViewerPage';
import ModelagemAvancadaTriggerPage from './pages/Pipelines/ModelagemAvancadaTriggerPage';
import ModelagemAvancadaViewerPage from './pages/Dashboards/ModelagemAvancadaViewerPage';
import IndiceCompostoDashboardPage from './pages/Dashboards/IndiceCompostoDashboardPage';
import PipelineLosHibridoPage from './pages/Pipelines/PipelineLosHibridoPage';
import LosHibridoViewerPage from './pages/Dashboards/LosHibridoViewerPage';
import PipelineRiscoPerinatalPage from './pages/Pipelines/PipelineRiscoPerinatalPage';
import RiscoPerinatalViewerPage from './pages/Dashboards/RiscoPerinatalViewerPage';
import PipelineSobrevidaInfantilPage from './pages/Pipelines/PipelineSobrevidaInfantilPage';
import SobrevidaInfantilViewerPage from './pages/Dashboards/SobrevidaInfantilViewerPage';
import PipelineDoencasCronicasPage from './pages/Pipelines/PipelineDoencasCronicasPage';
import DoencasCronicasViewerPage from './pages/Dashboards/DoencasCronicasViewerPage';
import RequireBphoAccess from './components/auth/RequireBphoAccess';
import PipelineHospitalizacaoRdfPage from './pages/Pipelines/PipelineHospitalizacaoRdfPage';
import HospitalizacaoRdfViewerPage from './pages/Dashboards/HospitalizacaoRdfViewerPage';
import ChatBphoPage from './pages/Pipelines/ChatBphoPage';
import PipelinePopulationSpacePage from './pages/Pipelines/PipelinePopulationSpacePage';
import PopulationSpaceViewerPage from './pages/Dashboards/PopulationSpaceViewerPage';
import PipelinePopulationComparePage from './pages/Pipelines/PipelinePopulationComparePage';
import PopulationCompareViewerPage from './pages/Dashboards/PopulationCompareViewerPage';
import PipelinePopulationCausalPage from './pages/Pipelines/PipelinePopulationCausalPage';
import PopulationCausalViewerPage from './pages/Dashboards/PopulationCausalViewerPage';
import PipelinePopulationAnomalyPage from './pages/Pipelines/PipelinePopulationAnomalyPage';
import PopulationAnomalyViewerPage from './pages/Dashboards/PopulationAnomalyViewerPage';
import PipelinePopulationRiskPage from './pages/Pipelines/PipelinePopulationRiskPage';
import PopulationRiskViewerPage from './pages/Dashboards/PopulationRiskViewerPage';
import PipelinePopulationUncertaintyPage from './pages/Pipelines/PipelinePopulationUncertaintyPage';
import PopulationUncertaintyViewerPage from './pages/Dashboards/PopulationUncertaintyViewerPage';
import PipelinePopulationClassifyPage from './pages/Pipelines/PipelinePopulationClassifyPage';
import PopulationClassifyViewerPage from './pages/Dashboards/PopulationClassifyViewerPage';
import PipelinePopulationTransitionsPage from './pages/Pipelines/PipelinePopulationTransitionsPage';
import PopulationTransitionsViewerPage from './pages/Dashboards/PopulationTransitionsViewerPage';
import PipelinePopulationSurvivalPage from './pages/Pipelines/PipelinePopulationSurvivalPage';
import PopulationSurvivalViewerPage from './pages/Dashboards/PopulationSurvivalViewerPage';
import PipelinePopulationIntervenePage from './pages/Pipelines/PipelinePopulationIntervenePage';
import PopulationInterveneViewerPage from './pages/Dashboards/PopulationInterveneViewerPage';
import PipelinePopulationGraphPage from './pages/Pipelines/PipelinePopulationGraphPage';
import PopulationGraphViewerPage from './pages/Dashboards/PopulationGraphViewerPage';
import PipelinePopulationFactorPage from './pages/Pipelines/PipelinePopulationFactorPage';
import PopulationFactorViewerPage from './pages/Dashboards/PopulationFactorViewerPage';
import PipelinePopulationTopologyPage from './pages/Pipelines/PipelinePopulationTopologyPage';
import PopulationTopologyViewerPage from './pages/Dashboards/PopulationTopologyViewerPage';
import PipelinePopulationEarlyWarningPage from './pages/Pipelines/PipelinePopulationEarlyWarningPage';
import PopulationEarlyWarningViewerPage from './pages/Dashboards/PopulationEarlyWarningViewerPage';
import PipelinePopulationGnnPage from './pages/Pipelines/PipelinePopulationGnnPage';
import PopulationGnnViewerPage from './pages/Dashboards/PopulationGnnViewerPage';
import PipelinePopulationDynamicsPage from './pages/Pipelines/PipelinePopulationDynamicsPage';
import PopulationDynamicsViewerPage from './pages/Dashboards/PopulationDynamicsViewerPage';
import PipelinePopulationPerCapitaPage from './pages/Pipelines/PipelinePopulationPerCapitaPage';
import PopulationPerCapitaViewerPage from './pages/Dashboards/PopulationPerCapitaViewerPage';
import PipelinePopulationMunicipioPage from './pages/Pipelines/PipelinePopulationMunicipioPage';
import PopulationMunicipioViewerPage from './pages/Dashboards/PopulationMunicipioViewerPage';
import PipelinePopulationNotificacaoPage from './pages/Pipelines/PipelinePopulationNotificacaoPage';
import PopulationNotificacaoViewerPage from './pages/Dashboards/PopulationNotificacaoViewerPage';
import PipelinePopulationFamiliaPage from './pages/Pipelines/PipelinePopulationFamiliaPage';
import PopulationFamiliaViewerPage from './pages/Dashboards/PopulationFamiliaViewerPage';
import CnesValidityPage from './pages/Pipelines/CnesValidityPage';
import RegistrosVitaisPage from './pages/Pipelines/RegistrosVitaisPage';
import SinanVigilanciaPage from './pages/Pipelines/SinanVigilanciaPage';

// Importar componentes comuns
import ErrorBoundary from './components/common/ErrorBoundary';
import Sidebar from './components/layout/Sidebar';

// Configuração Global do Axios
// src/App.js
const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || 'https://labsus-api.ngrok-free.app';
axios.defaults.baseURL = API_BASE_URL;
axios.defaults.withCredentials = true; // Permite envio de cookies/sessão
axios.defaults.headers.common['ngrok-skip-browser-warning'] = 'true'; // Pula tela de aviso do Ngrok

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeCategory, setActiveCategory] = useState(null);

  useEffect(() => {
    const setupCsrfToken = async () => {
      try {
        // Busca o token usando a URL completa do backend
        await axios.get(`${API_BASE_URL}/api/csrf/`);

        const csrfToken = Cookies.get('csrftoken');
        if (csrfToken) {
          axios.defaults.headers.common['X-CSRFToken'] = csrfToken;
          console.log("✅ Token CSRF configurado.");
        }
      } catch (error) {
        console.error("❌ Falha ao configurar o token CSRF:", error.message);
      }
    };
    setupCsrfToken();
  }, []);

  // Interceptor para garantir que o Token de Autenticação vá em todas as chamadas
  useEffect(() => {
    const token = localStorage.getItem('authToken');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Token ${token}`;
    }
  }, []);

  // Interceptor global de 401: sem isso, uma sessão expirada (por
  // inatividade, reinício do backend, etc.) só produz erros 401 silenciosos
  // em cada chamada, página após página, sem nunca deslogar de fato — o
  // `isAuthenticated` abaixo só olha se existe uma string de token no
  // localStorage, não se ela ainda é válida no servidor.
  useEffect(() => {
    const interceptorId = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        const isLoginAttempt = error.config?.url?.includes('/api/auth/login');
        if (error.response?.status === 401 && !isLoginAttempt) {
          localStorage.removeItem('authToken');
          delete axios.defaults.headers.common['Authorization'];
          const publicPaths = ['/login', '/register'];
          if (!publicPaths.includes(window.location.pathname)) {
            navigate('/login');
          }
        }
        return Promise.reject(error);
      }
    );
    return () => axios.interceptors.response.eject(interceptorId);
  }, [navigate]);

  const getNavLinkClass = ({ isActive }) =>
  `flex items-center px-4 py-2 rounded-md text-sm font-medium transition-colors duration-200 ${
    isActive ? 'bg-blue-600 text-white shadow-md' : 'hover:bg-gray-700 text-gray-300'
  }`;

  const handleLogout = async () => {
    try {
      await axios.post('/api/auth/logout/');
    } catch (error) {
      console.error("Erro ao fazer logout:", error.response?.data || error.message);
    } finally {
      localStorage.removeItem('authToken');
      delete axios.defaults.headers.common['Authorization'];
      navigate('/login');
    }
  };

  const handleLinkClick = () => {
    if (window.innerWidth < 768) {
      setIsSidebarOpen(false);
    }
    setActiveCategory(null);
  };

  const isAuthenticated = !!localStorage.getItem('authToken');
  const publicRoutes = ['/', '/login', '/register'];
  const isPublicPage = publicRoutes.includes(location.pathname);

  useEffect(() => {
    if (!isAuthenticated && !isPublicPage) {
      navigate('/login');
    } else if (isAuthenticated && location.pathname === '/') {
      // "/" é a landing page pública (SEO); quem já está logado vai direto
      // para o catálogo autenticado em vez de ver a página de marketing.
      navigate('/inicio');
    }
  }, [isAuthenticated, isPublicPage, location.pathname, navigate]);

  if (!isAuthenticated && !isPublicPage) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <p className="text-gray-700">Redirecionando para a página de login...</p>
      </div>
    );
  }

  const showSidebarAndButton = isAuthenticated && !isPublicPage;

  return (
    <div className="flex min-h-screen bg-gray-100">
    {showSidebarAndButton && (
      <>
      <button
      className="md:hidden fixed top-4 left-4 z-50 p-2 bg-blue-600 text-white rounded-md shadow-lg"
      onClick={() => setIsSidebarOpen(!isSidebarOpen)}
      >
      {isSidebarOpen ? <FiX size={24} /> : <FiMenu size={24} />}
      </button>
      {isSidebarOpen && (
        <div
        className="fixed inset-0 bg-black bg-opacity-50 z-30 md:hidden"
        onClick={() => setIsSidebarOpen(false)}
        ></div>
      )}
      <Sidebar
      getNavLinkClass={getNavLinkClass}
      handleLogout={handleLogout}
      isOpen={isSidebarOpen}
      onLinkClick={handleLinkClick}
      activeCategory={activeCategory}
      setActiveCategory={setActiveCategory}
      />
      </>
    )}

    <main className="flex-1 bg-gray-50 p-6 transition-all duration-300 ease-in-out">
    <Routes>
<Route path="/mapa-risco" element={<MapaRiscoTO />} />
<Route path="/mapa-risco" element={<MapaRiscoTO />} />
    <Route path="/tasks-history" element={<ErrorBoundary><TaskHistoryPage /></ErrorBoundary>} />
    <Route path="/csv-manager" element={<ErrorBoundary><CsvManagerPage /></ErrorBoundary>} />
    <Route path="/dashboards/analise-estado" element={<ErrorBoundary><AnalisePorEstadoPage /></ErrorBoundary>} />
    <Route path="/dashboards/analise-estado/:uf" element={<ErrorBoundary><AnalisePorEstadoPage /></ErrorBoundary>} />
    <Route path="/dashboards/analise-municipio" element={<ErrorBoundary><AnalisePorMunicipioPage /></ErrorBoundary>} />
    <Route path="/dashboards/visao-geral" element={<ErrorBoundary><VisaoGeralPage /></ErrorBoundary>} />
    <Route path="/dashboards/predicao-internacoes" element={<ErrorBoundary><PredictionInternacoesViewerPage /></ErrorBoundary>} />
    <Route path="/dashboards/kmeans-perfis-saude" element={<ErrorBoundary><KMeansPerfisSaudePage /></ErrorBoundary>} />
    <Route path="/dashboards/regressao-obitos" element={<ErrorBoundary><RegressaoObitosViewerPage /></ErrorBoundary>} />
    <Route path="/pipelines/indicadores" element={<ErrorBoundary><PipelineIndicadoresPage /></ErrorBoundary>} />
    <Route path="/pipelines/predicao-internacoes" element={<ErrorBoundary><PipelinePredicaoInternacoesPage /></ErrorBoundary>} />
    <Route path="/pipelines/kmeans" element={<ErrorBoundary><KMeansOrchestrationPage /></ErrorBoundary>} />
    <Route path="/pipelines/arquetipos" element={<ErrorBoundary><ArchetypeCreatorPage /></ErrorBoundary>} />
    <Route path="/pipelines/regressao-obitos" element={<ErrorBoundary><PipelineRegressaoObitosPage /></ErrorBoundary>} />
    <Route path="/pipelines/fluxo-pacientes" element={<ErrorBoundary><PipelineFluxoPacientesPage /></ErrorBoundary>} />
    <Route path="/dashboards/fluxo-pacientes" element={<ErrorBoundary><FluxoPacientesViewerPage /></ErrorBoundary>} />
    <Route path="/pipelines/risco-readmissao" element={<ErrorBoundary><PipelineRiscoReadmissaoPage /></ErrorBoundary>} />
    <Route path="/dashboards/risco-readmissao/viewer" element={<ErrorBoundary><ReadmissaoViewerPage /></ErrorBoundary>} />
    <Route path="/pipelines/custo-internacao" element={<ErrorBoundary><PipelineCustoInternacaoPage /></ErrorBoundary>} />
    <Route path="/dashboards/custo-internacao/viewer" element={<ErrorBoundary><CustoInternacaoViewerPage /></ErrorBoundary>} />
    <Route path="/pipelines/deteccao-surtos" element={<ErrorBoundary><PipelineDeteccaoSurtosPage /></ErrorBoundary>} />
    <Route path="/dashboards/deteccao-surtos/viewer" element={<ErrorBoundary><DeteccaoSurtosViewerPage /></ErrorBoundary>} />
    <Route path="/pipelines/modelagem/:slug" element={<ErrorBoundary><ModelagemAvancadaTriggerPage /></ErrorBoundary>} />
    <Route path="/dashboards/modelagem/:slug" element={<ErrorBoundary><ModelagemAvancadaViewerPage /></ErrorBoundary>} />
    <Route path="/dashboards/indices/:key" element={<ErrorBoundary><IndiceCompostoDashboardPage /></ErrorBoundary>} />
    <Route path="/pipelines/los-hibrido" element={<ErrorBoundary><PipelineLosHibridoPage /></ErrorBoundary>} />
    <Route path="/dashboards/los-hibrido/viewer" element={<ErrorBoundary><LosHibridoViewerPage /></ErrorBoundary>} />
    <Route path="/pipelines/risco-perinatal" element={<ErrorBoundary><PipelineRiscoPerinatalPage /></ErrorBoundary>} />
    <Route path="/dashboards/risco-perinatal/viewer" element={<ErrorBoundary><RiscoPerinatalViewerPage /></ErrorBoundary>} />
    <Route path="/pipelines/sobrevida-infantil" element={<ErrorBoundary><PipelineSobrevidaInfantilPage /></ErrorBoundary>} />
    <Route path="/dashboards/sobrevida-infantil/viewer" element={<ErrorBoundary><SobrevidaInfantilViewerPage /></ErrorBoundary>} />
    <Route path="/pipelines/doencas-cronicas" element={<ErrorBoundary><PipelineDoencasCronicasPage /></ErrorBoundary>} />
    <Route path="/dashboards/doencas-cronicas/viewer" element={<ErrorBoundary><DoencasCronicasViewerPage /></ErrorBoundary>} />
    <Route path="/pipelines/hospitalizacao-rdf" element={<RequireBphoAccess><ErrorBoundary><PipelineHospitalizacaoRdfPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/hospitalizacao-rdf/viewer" element={<RequireBphoAccess><ErrorBoundary><HospitalizacaoRdfViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/chat-bpho" element={<RequireBphoAccess><ErrorBoundary><ChatBphoPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-space" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationSpacePage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-space/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationSpaceViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-compare" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationComparePage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-compare/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationCompareViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-causal" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationCausalPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-causal/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationCausalViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-anomaly" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationAnomalyPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-anomaly/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationAnomalyViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-risk" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationRiskPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-risk/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationRiskViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-uncertainty" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationUncertaintyPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-uncertainty/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationUncertaintyViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-classify" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationClassifyPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-classify/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationClassifyViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-transitions" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationTransitionsPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-transitions/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationTransitionsViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-survival" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationSurvivalPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-survival/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationSurvivalViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-intervene" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationIntervenePage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-intervene/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationInterveneViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-graph" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationGraphPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-graph/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationGraphViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-factor" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationFactorPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-factor/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationFactorViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-topology" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationTopologyPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-topology/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationTopologyViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-early-warning" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationEarlyWarningPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-early-warning/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationEarlyWarningViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-gnn" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationGnnPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-gnn/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationGnnViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-dynamics" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationDynamicsPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-dynamics/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationDynamicsViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-per-capita" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationPerCapitaPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-per-capita/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationPerCapitaViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-municipio" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationMunicipioPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-municipio/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationMunicipioViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-notificacao" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationNotificacaoPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-notificacao/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationNotificacaoViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/population-familia" element={<RequireBphoAccess><ErrorBoundary><PipelinePopulationFamiliaPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/dashboards/population-familia/viewer" element={<RequireBphoAccess><ErrorBoundary><PopulationFamiliaViewerPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/cnes-validity" element={<RequireBphoAccess><ErrorBoundary><CnesValidityPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/registros-vitais" element={<RequireBphoAccess><ErrorBoundary><RegistrosVitaisPage /></ErrorBoundary></RequireBphoAccess>} />
    <Route path="/pipelines/sinan-vigilancia" element={<RequireBphoAccess><ErrorBoundary><SinanVigilanciaPage /></ErrorBoundary></RequireBphoAccess>} />

    <Route path="/login" element={<ErrorBoundary><LoginPage /></ErrorBoundary>} />
    <Route path="/register" element={<ErrorBoundary><RegisterPage /></ErrorBoundary>} />
    <Route path="/" element={<ErrorBoundary><LandingPage /></ErrorBoundary>} />
    <Route path="/inicio" element={<ErrorBoundary><HomePage /></ErrorBoundary>} />
    </Routes>
    </main>
    </div>
  );
}

export default App;
