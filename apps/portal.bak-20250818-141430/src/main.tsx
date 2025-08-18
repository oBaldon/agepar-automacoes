import React from 'react';
import ReactDOM from 'react-dom/client';
import '@agepar/tokens';
import './index.css';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';
import { AppRoutes } from './routes';
import ThemeProvider from './theme/ThemeProvider';
import ThemeToggle from './components/ThemeToggle';

const router = createBrowserRouter(AppRoutes, { basename: "/" });

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <RouterProvider router={router} />
      <ThemeToggle />
    </ThemeProvider>
  </React.StrictMode>
);
