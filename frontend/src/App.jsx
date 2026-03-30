import React, { useEffect, Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store'

import LoginPage from './pages/LoginPage'
import NavBar from './components/NavBar'

// Lazy load — sahifalar faqat kerak bo'lganda yuklanadi
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const ReportPage = lazy(() => import('./pages/ReportPage'))
const AiParsePage = lazy(() => import('./pages/AiParsePage'))
const InventoryPage = lazy(() => import('./pages/InventoryPage'))
const DebtsPage = lazy(() => import('./pages/DebtsPage'))
const ExportPage = lazy(() => import('./pages/ExportPage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))

function PrivateRoute({ children }) {
    const { isAuthenticated } = useAuthStore()
    return isAuthenticated ? children : <Navigate to="/login" replace />
}

const PageLoader = () => (
    <div className="page"><div className="loader"><div className="spinner" /></div></div>
)

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
            <Suspense fallback={<PageLoader />}>
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
            </Suspense>
            {isAuthenticated && <NavBar />}
        </>
    )
}
