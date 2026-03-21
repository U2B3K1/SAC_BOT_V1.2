import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store'
import { authApi } from '../api/client'
import toast from 'react-hot-toast'

export default function LoginPage() {
    const { login, isAuthenticated } = useAuthStore()
    const navigate = useNavigate()
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        if (isAuthenticated) navigate('/', { replace: true })
    }, [isAuthenticated, navigate])

    useEffect(() => {
        // Telegram WebApp mavjud bo'lsa avtomatik login
        const tg = window.Telegram?.WebApp
        if (tg?.initData) {
            handleTelegramLogin(tg.initData)
        }
    }, [])

    const handleTelegramLogin = async (initData) => {
        setLoading(true)
        try {
            const { data } = await authApi.login(initData)
            login(data.user, data.access_token, data.refresh_token)
            toast.success(`Xush kelibsiz, ${data.user.full_name}!`)
            navigate('/')
        } catch (err) {
            const msg = err.response?.data?.detail || "Tizimga kirib bo'lmadi"
            toast.error(msg)
        } finally {
            setLoading(false)
        }
    }

    const handleDevLogin = async () => {
        // Development uchun — test initData
        await handleTelegramLogin('user=%7B%22id%22%3A123456789%7D&auth_date=9999999999&hash=devhash')
    }

    return (
        <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', minHeight: '100vh', padding: '32px 24px',
            background: 'linear-gradient(135deg, #0A1628 0%, #1A2744 100%)'
        }}>
            {/* Logo */}
            <div style={{ fontSize: '64px', marginBottom: '24px' }}>🍽️</div>

            <h1 style={{ fontSize: '24px', fontWeight: 800, marginBottom: '8px', textAlign: 'center' }}>
                Restoran Boshqaruv
            </h1>
            <p style={{ color: 'var(--text-muted)', marginBottom: '48px', textAlign: 'center', fontSize: '14px' }}>
                Hisobot • Ombor • Qarzlar
            </p>

            {loading ? (
                <div className="loader"><div className="spinner" /></div>
            ) : (
                <div style={{ width: '100%', maxWidth: '320px' }}>
                    {window.Telegram?.WebApp?.initData ? (
                        <button
                            className="btn btn-primary btn-full"
                            onClick={() => handleTelegramLogin(window.Telegram.WebApp.initData)}
                            style={{ padding: '16px', fontSize: '16px' }}
                        >
                            🔐 Telegram orqali kirish
                        </button>
                    ) : (
                        <div style={{ textAlign: 'center' }}>
                            <p style={{ color: 'var(--text-muted)', marginBottom: '16px', fontSize: '13px' }}>
                                Iltimos, bu ilovani Telegram orqali oching
                            </p>
                            {import.meta.env.DEV && (
                                <button className="btn btn-ghost btn-full" onClick={handleDevLogin}>
                                    🛠️ Dev Login (Test)
                                </button>
                            )}
                        </div>
                    )}
                </div>
            )}

            <div style={{ marginTop: '48px', color: 'var(--text-muted)', fontSize: '12px', textAlign: 'center' }}>
                Kirish uchun Telegram hisobingiz<br />tizimga qo'shilgan bo'lishi kerak
            </div>
        </div>
    )
}
