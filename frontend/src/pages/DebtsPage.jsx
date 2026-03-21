import React, { useEffect, useState } from 'react'
import { debtsApi } from '../api/client'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import { Plus, MessageSquare } from 'lucide-react'

function fmt(n) { return Number(n || 0).toLocaleString('uz-UZ') }

export default function DebtsPage() {
    const [debts, setDebts] = useState([])
    const [selected, setSelected] = useState(null)
    const [creating, setCreating] = useState(false)
    const [addingPayment, setAddingPayment] = useState(false)
    const [loading, setLoading] = useState(true)
    const [search, setSearch] = useState('')
    const [form, setForm] = useState({ debtor_name: '', organization: '', phone: '', initial_amount: 0, description: '', debt_date: format(new Date(), 'yyyy-MM-dd'), due_date: '' })
    const [payForm, setPayForm] = useState({ amount: 0, payment_date: format(new Date(), 'yyyy-MM-dd'), notes: '' })

    useEffect(() => { loadDebts() }, [])

    const loadDebts = async () => {
        setLoading(true)
        try { const { data } = await debtsApi.list(); setDebts(data) } finally { setLoading(false) }
    }

    const loadDetail = async (id) => {
        const { data } = await debtsApi.get(id)
        setSelected(data)
    }

    const createDebt = async () => {
        if (!form.debtor_name || !form.initial_amount) return toast.error("Ism va summani kiriting")
        try {
            await debtsApi.create({ ...form, initial_amount: +form.initial_amount })
            toast.success('Qarz yozildi')
            setCreating(false)
            setForm({ debtor_name: '', organization: '', phone: '', initial_amount: 0, description: '', debt_date: format(new Date(), 'yyyy-MM-dd'), due_date: '' })
            loadDebts()
        } catch (e) { toast.error(e.response?.data?.detail || 'Xato') }
    }

    const addPayment = async () => {
        try {
            await debtsApi.addPayment(selected.id, { ...payForm, amount: +payForm.amount })
            toast.success('To\'lov kiritildi ✅')
            setAddingPayment(false)
            loadDetail(selected.id)
            loadDebts()
        } catch (e) { toast.error(e.response?.data?.detail || 'Xato') }
    }

    const sendSms = async () => {
        try {
            await debtsApi.sendSms(selected.id, { debt_id: selected.id })
            toast.success('SMS yuborildi 📱')
        } catch (e) { toast.error(e.response?.data?.detail || 'SMS yuborishda xato') }
    }

    const filtered = debts.filter(d =>
        d.debtor_name?.toLowerCase().includes(search.toLowerCase()) ||
        d.phone?.includes(search) ||
        d.organization?.toLowerCase().includes(search.toLowerCase())
    )

    const totalDebt = debts.filter(d => d.status !== 'paid').reduce((s, d) => s + (d.remaining_amount || 0), 0)

    if (selected) return (
        <div className="page">
            <button className="btn btn-ghost" style={{ marginBottom: '16px' }} onClick={() => setSelected(null)}>← Orqaga</button>
            <div className="card">
                <div className="card-title" style={{ marginBottom: '8px' }}>{selected.debtor_name}</div>
                {selected.organization && <div className="text-muted mb-8">🏢 {selected.organization}</div>}
                {selected.phone && <div className="text-muted mb-8">📱 {selected.phone}</div>}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '12px' }}>
                    <div style={{ background: 'rgba(192,57,43,0.1)', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
                        <div className="stat-label">Boshlang'ich</div>
                        <div className="stat-value red">{fmt(selected.initial_amount)}</div>
                    </div>
                    <div style={{ background: 'rgba(39,174,96,0.1)', padding: '12px', borderRadius: '8px', textAlign: 'center' }}>
                        <div className="stat-label">Qoldiq</div>
                        <div className="stat-value green">{fmt(selected.remaining_amount)}</div>
                    </div>
                </div>
                <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    <button className="btn btn-success" onClick={() => setAddingPayment(true)}><Plus size={14} /> To'lov</button>
                    {selected.phone && <button className="btn btn-primary" onClick={sendSms}><MessageSquare size={14} /> SMS</button>}
                </div>
            </div>
            {addingPayment && (
                <div className="card">
                    <div className="card-title" style={{ marginBottom: '12px' }}>To'lov Kiritish</div>
                    <div className="form-group"><label className="form-label">Summa (so'm)</label><input type="number" className="form-input" value={payForm.amount} onChange={e => setPayForm(p => ({ ...p, amount: e.target.value }))} /></div>
                    <div className="form-group"><label className="form-label">Sana</label><input type="date" className="form-input" value={payForm.payment_date} onChange={e => setPayForm(p => ({ ...p, payment_date: e.target.value }))} /></div>
                    <div className="form-group"><label className="form-label">Izoh</label><input type="text" className="form-input" value={payForm.notes} onChange={e => setPayForm(p => ({ ...p, notes: e.target.value }))} /></div>
                    <div style={{ display: 'flex', gap: '8px' }}><button className="btn btn-success btn-full" onClick={addPayment}>Saqlash</button><button className="btn btn-ghost btn-full" onClick={() => setAddingPayment(false)}>Bekor</button></div>
                </div>
            )}
            <div className="card">
                <div className="card-title" style={{ marginBottom: '12px' }}>To'lovlar tarixi</div>
                {(selected.debt_payments || []).length === 0 ? <div className="text-muted" style={{ textAlign: 'center', padding: '16px' }}>To'lov yo'q</div> :
                    selected.debt_payments.map((p, i) => (
                        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
                            <div><div style={{ fontWeight: 600 }}>{fmt(p.amount)} so'm</div><div className="text-muted" style={{ fontSize: '12px' }}>{p.payment_date}</div></div>
                            <div className="text-muted" style={{ fontSize: '12px' }}>{p.notes}</div>
                        </div>
                    ))}
            </div>
        </div>
    )

    return (
        <div className="page">
            <div className="page-header">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div className="page-title">💳 Qarzlar</div>
                    <button className="btn btn-primary" style={{ padding: '8px 14px', fontSize: '13px' }} onClick={() => setCreating(true)}><Plus size={16} /> Yangi</button>
                </div>
            </div>

            <div className="card"><div className="stat-label">Jami qoldiq qarzdorlik</div><div className="stat-value red">{fmt(totalDebt)} so'm</div></div>

            <input className="form-input" placeholder="Qidirish (ism, telefon, tashkilot)..." value={search} onChange={e => setSearch(e.target.value)} style={{ marginBottom: '12px' }} />

            {creating && (
                <div className="card">
                    <div className="card-title" style={{ marginBottom: '12px' }}>Yangi Qarz</div>
                    {[{ key: 'debtor_name', label: 'Ism Familya', type: 'text' }, { key: 'organization', label: 'Tashkilot', type: 'text' }, { key: 'phone', label: 'Telefon (+998...)', type: 'tel' }, { key: 'initial_amount', label: 'Summa (so\'m)', type: 'number' }, { key: 'debt_date', label: 'Sana', type: 'date' }, { key: 'due_date', label: 'To\'lov muddati', type: 'date' }].map(f => (
                        <div key={f.key} className="form-group">
                            <label className="form-label">{f.label}</label>
                            <input type={f.type} className="form-input" value={form[f.key]} onChange={e => setForm(p => ({ ...p, [f.key]: e.target.value }))} />
                        </div>
                    ))}
                    <div className="form-group"><label className="form-label">Izoh</label><textarea className="form-textarea" value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} /></div>
                    <div style={{ display: 'flex', gap: '8px' }}><button className="btn btn-primary btn-full" onClick={createDebt}>Saqlash</button><button className="btn btn-ghost btn-full" onClick={() => setCreating(false)}>Bekor</button></div>
                </div>
            )}

            {loading ? <div className="loader"><div className="spinner" /></div> : filtered.map(d => (
                <div key={d.id} className="card" style={{ cursor: 'pointer' }} onClick={() => loadDetail(d.id)}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <div>
                            <div style={{ fontWeight: 700 }}>{d.debtor_name}</div>
                            <div className="text-muted" style={{ fontSize: '12px' }}>{d.phone} {d.organization && `· ${d.organization}`}</div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                            <div className="text-red font-bold">{fmt(d.remaining_amount)} so'm</div>
                            <span className={`badge badge-${d.status}`}>{d.status === 'active' ? 'Faol' : d.status === 'partially_paid' ? "Qisman" : "To'liq"}</span>
                        </div>
                    </div>
                </div>
            ))}
        </div>
    )
}
