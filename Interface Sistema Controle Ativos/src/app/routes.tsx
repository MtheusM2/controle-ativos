import React from 'react'
import { createBrowserRouter, Navigate } from 'react-router'
import { MainLayout } from './layouts/MainLayout'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { AssetList } from './pages/AssetList'
import { AssetForm } from './pages/AssetForm'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Login />,
  },
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'assets', element: <AssetList /> },
      { path: 'assets/new', element: <AssetForm /> },
      { path: 'assets/edit/:id', element: <AssetForm /> },
    ]
  }
])
