import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { reportsApi, adminApi, dashboardApi } from '../api/client'
import { useAuthStore, useAppStore } from '../store'
import { format } from 'date-fns'
import { uz } from 'date-fns/locale'
import toast from 'react-hot-toast'
import { Plus, Wallet, Package, Briefcase, FileText } from 'lucide-react'

function fmt(n) { return Number(n || 0).toLocaleString('uz-UZ') }

export default function DashboardPage() {
    const { user } = useAuthStore()
    const { masterDataLoaded, setMasterData, reports, setReportsCache, dashboardSummary, dashboardSummaryLoaded, setDashboardSummaryCache } = useAppStore()
    const navigate = useNavigate()
    const [loading, setLoading] = useState(false)

    const today = format(new Date(), 'yyyy-MM-dd')
    const [filterDate, setFilterDate] = useState(today)

    useEffect(() => {
        // Avval kirmagan bo'lsa zudlik bilan loader chiqaramiz, bo'lmasa eski xolat turadi
        if (!dashboardSummaryLoaded) setLoading(true)
        loadData()
        if (!masterDataLoaded) loadMasterData()
    }, [])

    useEffect(() => {
        if (dashboardSummaryLoaded) {
            dashboardApi.stats({ filter_date: filterDate }).then(res => setDashboardSummaryCache(res.data))
        }
    }, [filterDate])

    const loadMasterData = async () => {
        console.log("Loading Master Data...")
        try {
            const [depts, prods, cats] = await Promise.allSettled([
                adminApi.departments(),
                adminApi.products(),
                adminApi.expenseCategories(),
            ])
            const d = depts.status === 'fulfilled' ? depts.value.data : []
            const p = prods.status === 'fulfilled' ? prods.value.data : []
            const c = cats.status === 'fulfilled' ? cats.value.data : []
            setMasterData(d, p, c)
            console.log("Master Data loaded successfully")
        } catch (err) { 
            console.error("Master Data error:", err)
        }
    }

    const loadData = async () => {
        console.log("Loading Dashboard Data for:", filterDate)
        try {
            const [sum, reps] = await Promise.allSettled([
                dashboardApi.stats({ filter_date: filterDate }),
                reportsApi.list({ limit: 5 }),
            ])
            
            if (sum.status === 'fulfilled') {
                console.log("Stats received:", sum.value.data)
                setDashboardSummaryCache(sum.value.data)
            } else {
                console.error("Stats API error:", sum.reason)
                toast.error("Statistika yuklanmadi")
            }

            if (reps.status === 'fulfilled') {
                setReportsCache(reps.value.data)
            }
        } catch (e) {
            console.error("LoadData global error:", e)
            toast.error("Ma'lumotlarni yuklashda xato")
        } finally {
            setLoading(false)
        }
    }

    if (loading && !dashboardSummaryLoaded) return <div className="page"><div className="loader"><div className="spinner" /></div></div>

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

            {/* Dashboard Ko'rsatkichlari */}
            {dashboardSummary && (
                <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <div style={{ color: 'var(--text-muted)', fontSize: '13px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                            Asosiy Holat
                        </div>
                        <input 
                            type="date" 
                            className="form-input" 
                            style={{ width: 'auto', padding: '4px 8px', fontSize: '13px', border: 'none', background: 'var(--bg-secondary)', cursor: 'pointer' }}
                            value={filterDate}
                            onChange={(e) => setFilterDate(e.target.value)}
                        />
                    </div>
                    <div className="stat-grid">
                        <div className="stat-card">
                            <div className="stat-label">🤝 Jami qarz (Haqdorlik)</div>
                            <div className="stat-value green">{fmt(dashboardSummary.total_receive_debt)}</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-label">🏢 Bizning qarz</div>
                            <div className="stat-value red">{fmt(dashboardSummary.total_pay_debt)}</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-label">📦 Tovar qoldiq</div>
                            <div className="stat-value yellow">{fmt(dashboardSummary.total_inventory_value)}</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-label">💰 Daromad (Kunlik)</div>
                            <div className="stat-value blue">{fmt(dashboardSummary.total_revenue)}</div>
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
                        <FileText size={16} /> Hisobot
                    </button>
                    <button className="btn btn-success" onClick={() => navigate('/debts?tab=receive')}>
                        <Wallet size={16} /> Qarz
                    </button>
                    <button className="btn btn-ghost" onClick={() => navigate('/inventory')}>
                        <Package size={16} /> Ombor
                    </button>
                    <button className="btn btn-danger" style={{ background: 'rgba(192, 57, 43, 0.1)', color: 'var(--danger)' }} onClick={() => navigate('/debts?tab=pay')}>
                        <Briefcase size={16} /> Bizning qarz
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
