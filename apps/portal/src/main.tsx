import React from 'react';
import ReactDOM from 'react-dom/client';
import '@agepar/tokens';
import './index.css';
import { RouterProvider, createBrowserRouter } from 'react-router-dom';
import { AppRoutes } from './routes';

const router = createBrowserRouter(AppRoutes, { basename: "/" });

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><RouterProvider router={router} /></React.StrictMode>
);
