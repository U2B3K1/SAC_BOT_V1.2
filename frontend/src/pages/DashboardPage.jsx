import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { reportsApi, adminApi } from '../api/client'
import { useAuthStore, useAppStore } from '../store'
import { format } from 'date-fns'
import { uz } from 'date-fns/locale'
import toast from 'react-hot-toast'
import { Plus, TrendingUp, TrendingDown, Wallet, DollarSign } from 'lucide-react'

function fmt(n) { return Number(n || 0).toLocaleString('uz-UZ') }

export default function DashboardPage() {
    const { user } = useAuthStore()
    const { masterDataLoaded, setMasterData } = useAppStore()
    const navigate = useNavigate()
    const [summary, setSummary] = useState(null)
    const [reports, setReports] = useState([])
    const [loading, setLoading] = useState(true)

    const today = format(new Date(), 'yyyy-MM-dd')

    useEffect(() => {
        loadData()
        // Master data faqat birinchi marta yuklanadi
        if (!masterDataLoaded) {
            loadMasterData()
        }
    }, [])

    const loadMasterData = async () => {
        try {
            const [depts, prods, cats] = await Promise.all([
                adminApi.departments(),
                adminApi.products(),
                adminApi.expenseCategories(),
            ])
            setMasterData(depts.data, prods.data, cats.data)
        } catch { }
    }

    const loadData = async () => {
        try {
            const [sum, reps] = await Promise.all([
                reportsApi.summary(3),
                reportsApi.list({ limit: 5 }),
            ])
            setSummary(sum.data)
            setReports(reps.data)
        } catch (e) {
            toast.error("Ma'lumotlarni yuklashda xato")
        } finally {
            setLoading(false)
        }
    }

    if (loading) return <div className="page"><div className="loader"><div className="spinner" /></div></div>

    const isSuperUser = user?.role === 'super_user'

    return (
        <div className="page">
            {/* Header */}
            <div className="page-header">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                        <div className="page-title">Salom, {user?.full_name?.split(' ')[0]} 👋</div>
                        <div className="page-subtitle">{format(new Date(), 'dd MMMM yyyy', { locale: uz })}</div>
                    </div>
                    <span className={`badge ${isSuperUser ? 'badge-approved' : 'badge-submitted'}`}>
                        {isSuperUser ? '👑 Super User' : '👤 Manager'}
                    </span>
                </div>
            </div>

            {/* 3 kunlik yig'ma */}
            {summary && (
                <>
                    <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginBottom: '8px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        So'nggi 3 kun
                    </div>
                    <div className="stat-grid">
                        <div className="stat-card">
                            <div className="stat-label">💰 Daromad</div>
                            <div className="stat-value blue">{fmt(summary.total_revenue)}</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-label">✅ Sof Foyda</div>
                            <div className="stat-value green">{fmt(summary.net_profit)}</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-label">📦 Tannarx</div>
                            <div className="stat-value yellow">{fmt(summary.total_cost)}</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-label">💸 Xarajat</div>
                            <div className="stat-value red">{fmt(summary.total_expenses)}</div>
                        </div>
                    </div>
                </>
            )}

            {/* Tezkor harakatlar */}
            <div className="card">
                <div className="card-header">
                    <span className="card-title">⚡ Tezkor Harakatlar</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <button className="btn btn-primary" onClick={() => navigate('/reports')}>
                        <Plus size={16} /> Hisobot
                    </button>
                    <button className="btn btn-success" onClick={() => navigate('/ai')}>
                        ✨ AI Yuklash
                    </button>
                    <button className="btn btn-ghost" onClick={() => navigate('/inventory')}>
                        📦 Ombor
                    </button>
                    <button className="btn btn-ghost" onClick={() => navigate('/export')}>
                        📤 Export
                    </button>
                </div>
            </div>

            {/* Oxirgi hisobotlar */}
            <div className="card">
                <div className="card-header">
                    <span className="card-title">📋 Oxirgi Hisobotlar</span>
                    <button className="btn btn-ghost" style={{ padding: '6px 12px', fontSize: '12px' }} onClick={() => navigate('/reports')}>
                        Hammasi
                    </button>
                </div>
                {reports.length === 0 ? (
                    <div className="empty-state" style={{ padding: '24px' }}>
                        Hali hisobot yo'q
                    </div>
                ) : (
                    <div>
                        {reports.map(r => (
                            <div key={r.id} style={{
                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                padding: '12px 0', borderBottom: '1px solid var(--border)'
                            }}>
                                <div>
                                    <div style={{ fontWeight: 600, fontSize: '14px' }}>{r.report_date}</div>
                                    <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                                        {r.departments?.name}
                                    </div>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    <div style={{ color: 'var(--accent)', fontWeight: 700 }}>
                                        {fmt(r.total_revenue)} so'm
                                    </div>
                                    <span className={`badge badge-${r.status}`}>{
                                        r.status === 'draft' ? 'Qoralama' :
                                            r.status === 'submitted' ? 'Yuborildi' : 'Tasdiqlandi'
                                    }</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
