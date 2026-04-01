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
        const initTelegram = () => {
            const tg = window.Telegram?.WebApp;
            if (tg) {
                tg.ready();
                tg.expand();

                const updateHeight = () => {
                    const height = tg.viewportStableHeight || tg.viewportHeight || window.innerHeight;
                    document.documentElement.style.setProperty('--tg-viewport-height', `${height}px`);
                };

                updateHeight();
                tg.onEvent('viewportChanged', updateHeight);

                // Telefon qulflanib ochilganda yoki fondan qaytganda muzlashni oldini olish
                document.addEventListener('visibilitychange', () => {
                    if (document.visibilityState === 'visible') {
                        tg.expand();
                        updateHeight();
                    }
                });
            }
        };

        initTelegram();
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
