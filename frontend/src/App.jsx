import React, { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store'

import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ReportPage from './pages/ReportPage'
import AiParsePage from './pages/AiParsePage'
import InventoryPage from './pages/InventoryPage'
import DebtsPage from './pages/DebtsPage'
import ExportPage from './pages/ExportPage'
import AdminPage from './pages/AdminPage'
import NavBar from './components/NavBar'

function PrivateRoute({ children }) {
    const { isAuthenticated } = useAuthStore()
    return isAuthenticated ? children : <Navigate to="/login" replace />
}

export default function App() {
    const { isAuthenticated } = useAuthStore()

    useEffect(() => {
        // Telegram WebApp initialization
        if (window.Telegram?.WebApp) {
            window.Telegram.WebApp.ready()
            window.Telegram.WebApp.expand()
            document.documentElement.style.setProperty(
                '--tg-viewport-height',
                window.Telegram.WebApp.viewportHeight + 'px'
            )
        }
    }, [])

    return (
        <>
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/" element={<PrivateRoute><DashboardPage /></PrivateRoute>} />
                <Route path="/reports" element={<PrivateRoute><ReportPage /></PrivateRoute>} />
                <Route path="/ai" element={<PrivateRoute><AiParsePage /></PrivateRoute>} />
                <Route path="/inventory" element={<PrivateRoute><InventoryPage /></PrivateRoute>} />
                <Route path="/debts" element={<PrivateRoute><DebtsPage /></PrivateRoute>} />
                <Route path="/export" element={<PrivateRoute><ExportPage /></PrivateRoute>} />
                <Route path="/admin" element={<PrivateRoute><AdminPage /></PrivateRoute>} />
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
            {isAuthenticated && <NavBar />}
        </>
    )
}
