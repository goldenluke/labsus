// src/index.js

import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';

// --- ADICIONE ESTA LINHA ---
import 'tippy.js/dist/tippy.css'; // Importa os estilos padrão do Tippy.js

const root = ReactDOM.createRoot(document.getElementById('root'));
// ... (resto do arquivo)
root.render(
  <React.StrictMode>

  <BrowserRouter>
  <AuthProvider>
  <App />
  </AuthProvider>
  </BrowserRouter>

  </React.StrictMode>
);

reportWebVitals();
