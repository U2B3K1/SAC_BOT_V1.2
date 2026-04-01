import React, { useState, useEffect } from 'react'
import { reportsApi, salesApi, expensesApi, adminApi } from '../api/client'
import { useAppStore } from '../store'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import { Plus, Trash2 } from 'lucide-react'

function fmt(n) { return Number(n || 0).toLocaleString('uz-UZ') }

export default function ReportPage() {
    const { 
        departments, products, expenseCategories,
        reports, reportsLoaded, setReportsCache
    } = useAppStore()
    
    const [selected, setSelected] = useState(null) // tanlangan hisobot
    const [sales, setSales] = useState([])
    const [expenses, setExpenses] = useState([])
    const [loading, setLoading] = useState(false)
    const [creating, setCreating] = useState(false)
    const [form, setForm] = useState({ report_date: format(new Date(), 'yyyy-MM-dd'), department_id: '', opening_balance: 0 })
    const [saleForm, setSaleForm] = useState({ product_id: '', quantity: 1, unit_price: 0 })
    const [expForm, setExpForm] = useState({ category_id: '', amount: 0, description: '' })

    useEffect(() => { loadReports() }, [])
    useEffect(() => { if (selected) loadDetail(selected) }, [selected])

    const loadReports = async () => {
        // Faqat kesh bo'lmasa spinner chiqaramiz
        if (!reportsLoaded) setLoading(true)
        try {
            const { data } = await reportsApi.list({ limit: 20 })
            setReportsCache(data) // store ga joylaymiz
        } finally { setLoading(false) }
    }

    const loadDetail = async (id) => {
        const { data } = await reportsApi.get(id)
        setSales(data.sales || [])
        setExpenses(data.expenses || [])
    }

    const createReport = async () => {
        if (!form.department_id) return toast.error("Bo'lim tanlang")
        try {
            const { data } = await reportsApi.create(form)
            setReportsCache([data, ...reports]) // keshni ham yangilaymiz
            setSelected(data.id)
            setCreating(false)
            toast.success('Hisobot yaratildi')
        } catch (e) { toast.error(e.response?.data?.detail || 'Xato') }
    }

    const addSale = async () => {
        if (!saleForm.product_id || !saleForm.quantity || !saleForm.unit_price) return toast.error("Barcha maydonlarni to'ldiring")
        try {
            const { data } = await salesApi.create({ ...saleForm, daily_report_id: selected })
            setSales(prev => [...prev, data])
            setSaleForm({ product_id: '', quantity: 1, unit_price: 0 })
            toast.success('Sotuv qo\'shildi ✅')
            loadReports()
        } catch (e) { toast.error(e.response?.data?.detail || 'Xato') }
    }

    const addExpense = async () => {
        if (!expForm.category_id || !expForm.amount) return toast.error("Kategoriya va summani kiriting")
        try {
            const { data } = await expensesApi.create({ ...expForm, daily_report_id: selected })
            setExpenses(prev => [...prev, data])
            setExpForm({ category_id: '', amount: 0, description: '' })
            toast.success('Xarajat qo\'shildi')
            loadReports()
        } catch (e) { toast.error(e.response?.data?.detail || 'Xato') }
    }

    const submitReport = async () => {
        try {
            await reportsApi.submit(selected)
            toast.success('Hisobot yuborildi!')
            loadReports()
        } catch (e) { toast.error(e.response?.data?.detail || 'Xato') }
    }

    const deleteSale = async (id) => {
        await salesApi.delete(id)
        setSales(prev => prev.filter(s => s.id !== id))
        loadReports()
    }

    const rep = reports.find(r => r.id === selected)

    return (
        <div className="page">
            <div className="page-header">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div className="page-title">📋 Hisobotlar</div>
                    <button className="btn btn-primary" style={{ padding: '8px 14px', fontSize: '13px' }} onClick={() => setCreating(true)}>
                        <Plus size={16} /> Yangi
                    </button>
                </div>
            </div>

            {/* Yangi hisobot formasi */}
            {creating && (
                <div className="card">
                    <div className="card-title" style={{ marginBottom: '12px' }}>Yangi Hisobot</div>
                    <div className="form-group">
                        <label className="form-label">Sana</label>
                        <input type="date" className="form-input" value={form.report_date} onChange={e => setForm(p => ({ ...p, report_date: e.target.value }))} />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Bo'lim</label>
                        <select className="form-select" value={form.department_id} onChange={e => setForm(p => ({ ...p, department_id: e.target.value }))}>
                            <option value="">Tanlang...</option>
                            {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                        </select>
                    </div>
                    <div className="form-group">
                        <label className="form-label">Boshlanish balansi (so'm)</label>
                        <input type="number" className="form-input" value={form.opening_balance} onChange={e => setForm(p => ({ ...p, opening_balance: +e.target.value }))} />
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                        <button className="btn btn-primary btn-full" onClick={createReport}>Yaratish</button>
                        <button className="btn btn-ghost btn-full" onClick={() => setCreating(false)}>Bekor</button>
                    </div>
                </div>
            )}

            {/* Hisobotlar ro'yxati */}
            {!selected && (
                <div>
                    {loading ? <div className="loader"><div className="spinner" /></div> : reports.map(r => (
                        <div key={r.id} className="card" style={{ cursor: 'pointer' }} onClick={() => setSelected(r.id)}>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <div>
                                    <div style={{ fontWeight: 600 }}>{r.report_date} — {r.departments?.name}</div>
                                    <div style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '4px' }}>
                                        Daromad: {fmt(r.total_revenue)} • Foyda: {fmt(r.net_profit)}
                                    </div>
                                </div>
                                <span className={`badge badge-${r.status}`}>{r.status === 'draft' ? 'Qoralama' : r.status === 'submitted' ? 'Yuborildi' : 'Tasdiqlandi'}</span>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Tanlangan hisobot detali */}
            {selected && rep && (
                <div>
                    <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                        <button className="btn btn-ghost" onClick={() => setSelected(null)}>← Orqaga</button>
                        {rep.status === 'draft' && (
                            <button className="btn btn-success" onClick={submitReport}>✅ Yuborish</button>
                        )}
                    </div>

                    {/* Yig'ma */}
                    <div className="stat-grid">
                        <div className="stat-card"><div className="stat-label">Daromad</div><div className="stat-value blue">{fmt(rep.total_revenue)}</div></div>
                        <div className="stat-card"><div className="stat-label">Sof Foyda</div><div className="stat-value green">{fmt(rep.net_profit)}</div></div>
                        <div className="stat-card"><div className="stat-label">Tannarx</div><div className="stat-value yellow">{fmt(rep.total_cost)}</div></div>
                        <div className="stat-card"><div className="stat-label">Xarajatlar</div><div className="stat-value red">{fmt(rep.total_expenses)}</div></div>
                    </div>

                    {/* Sotuv qo'shish */}
                    {rep.status === 'draft' && (
                        <div className="card">
                            <div className="card-title" style={{ marginBottom: '12px' }}>➕ Sotuv Kiritish</div>
                            <div className="form-group">
                                <label className="form-label">Mahsulot</label>
                                <select className="form-select" value={saleForm.product_id} onChange={e => { const p = products.find(x => x.id === e.target.value); setSaleForm(f => ({ ...f, product_id: e.target.value, unit_price: p?.sale_price || 0 })) }}>
                                    <option value="">Tanlang...</option>
                                    {products.map(p => <option key={p.id} value={p.id}>{p.name} — {fmt(p.sale_price)} so'm</option>)}
                                </select>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                                <div className="form-group"><label className="form-label">Miqdor</label><input type="number" className="form-input" value={saleForm.quantity} onChange={e => setSaleForm(f => ({ ...f, quantity: +e.target.value }))} /></div>
                                <div className="form-group"><label className="form-label">Narx</label><input type="number" className="form-input" value={saleForm.unit_price} onChange={e => setSaleForm(f => ({ ...f, unit_price: +e.target.value }))} /></div>
                            </div>
                            <button className="btn btn-primary btn-full" onClick={addSale}>Qo'shish</button>
                        </div>
                    )}

                    {/* Sotuvlar ro'yxati */}
                    <div className="card">
                        <div className="card-title" style={{ marginBottom: '12px' }}>🛒 Sotuvlar ({sales.length})</div>
                        {sales.length === 0 ? <div className="text-muted" style={{ textAlign: 'center', padding: '16px' }}>Sotuv yo'q</div> : (
                            <div className="table-wrap">
                                <table>
                                    <thead><tr><th>Mahsulot</th><th>Miqdor</th><th>Narx</th><th>Jami</th><th></th></tr></thead>
                                    <tbody>
                                        {sales.map(s => (
                                            <tr key={s.id}>
                                                <td>{s.products?.name}</td>
                                                <td>{s.quantity}</td>
                                                <td>{fmt(s.unit_price)}</td>
                                                <td className="text-green font-bold">{fmt(s.total_amount)}</td>
                                                <td>{rep.status === 'draft' && <button className="btn btn-danger" style={{ padding: '4px 8px' }} onClick={() => deleteSale(s.id)}><Trash2 size={12} /></button>}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>

                    {/* Xarajat qo'shish */}
                    {rep.status === 'draft' && (
                        <div className="card">
                            <div className="card-title" style={{ marginBottom: '12px' }}>💸 Xarajat Kiritish</div>
                            <div className="form-group">
                                <label className="form-label">Kategoriya</label>
                                <select className="form-select" value={expForm.category_id} onChange={e => setExpForm(f => ({ ...f, category_id: e.target.value }))}>
                                    <option value="">Tanlang...</option>
                                    {expenseCategories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                                </select>
                            </div>
                            <div className="form-group"><label className="form-label">Summa (so'm)</label><input type="number" className="form-input" value={expForm.amount} onChange={e => setExpForm(f => ({ ...f, amount: +e.target.value }))} /></div>
                            <div className="form-group"><label className="form-label">Izoh</label><input type="text" className="form-input" value={expForm.description} onChange={e => setExpForm(f => ({ ...f, description: e.target.value }))} /></div>
                            <button className="btn btn-primary btn-full" onClick={addExpense}>Qo'shish</button>
                        </div>
                    )}

                    {/* Xarajatlar ro'yxati */}
                    <div className="card">
                        <div className="card-title" style={{ marginBottom: '12px' }}>💸 Xarajatlar ({expenses.length})</div>
                        {expenses.map(e => (
                            <div key={e.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
                                <div><div style={{ fontWeight: 600 }}>{e.expense_categories?.name}</div><div className="text-muted" style={{ fontSize: '12px' }}>{e.description}</div></div>
                                <div className="text-red font-bold">{fmt(e.amount)} so'm</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    )
}
