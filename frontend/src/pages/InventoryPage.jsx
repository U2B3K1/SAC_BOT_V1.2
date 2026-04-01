import React, { useEffect, useState } from 'react'
import { inventoryApi, adminApi } from '../api/client'
import { useAppStore } from '../store'
import toast from 'react-hot-toast'
import { Plus, RefreshCw } from 'lucide-react'

function fmt(n) { return Number(n || 0).toFixed(2) }

export default function InventoryPage() {
    const { inventory, inventoryLoaded, setInventoryCache } = useAppStore()
    const stock = inventory.stock || []
    const variance = inventory.variance || []
    const ingredients = inventory.ingredients || []

    const [tab, setTab] = useState('stock') // 'stock' | 'receipt' | 'variance'
    const [actual, setActual] = useState({}) // id -> qty
    const [loading, setLoading] = useState(false)
    const [receiptForm, setReceiptForm] = useState({ receipt_date: new Date().toISOString().slice(0, 10), supplier: '', items: [] })
    const [newItem, setNewItem] = useState({ ingredient_id: '', quantity: 0, unit: 'kg', unit_cost: 0 })

    useEffect(() => { 
        if (!inventoryLoaded) {
            loadAll() 
        } else {
            const init = {}
            ;(inventory.stock || []).forEach(i => { init[i.ingredient_id] = i.quantity })
            setActual(init)
        }
    }, [])

    const loadAll = async () => {
        if (!inventoryLoaded) setLoading(true)
        try {
            const [s, ing, v] = await Promise.all([inventoryApi.stock(), adminApi.ingredients(), inventoryApi.variance()])
            setInventoryCache({ stock: s.data, ingredients: ing.data, variance: v.data.adjustments || [] })
            
            const init = {}
            s.data.forEach(i => { init[i.ingredient_id] = i.quantity })
            setActual(init)
        } finally { setLoading(false) }
    }

    const saveActual = async () => {
        const updates = Object.entries(actual).map(([ingredient_id, actual_qty]) => ({ ingredient_id, actual_qty: +actual_qty }))
        try { await inventoryApi.updateStock(updates); toast.success('Qoldiqlar yangilandi ✅'); loadAll() } catch (e) { toast.error('Xato') }
    }

    const addReceiptItem = () => {
        if (!newItem.ingredient_id || !newItem.quantity) return toast.error("Ingredient va miqdor kerak")
        setReceiptForm(p => ({ ...p, items: [...p.items, { ...newItem }] }))
        setNewItem({ ingredient_id: '', quantity: 0, unit: 'kg', unit_cost: 0 })
    }

    const saveReceipt = async () => {
        if (!receiptForm.items.length) return toast.error("Kamida bitta ingredient qo'shing")
        try {
            await inventoryApi.createReceipt({ ...receiptForm, items: receiptForm.items.map(i => ({ ...i, quantity: +i.quantity, unit_cost: +i.unit_cost })) })
            toast.success('Kirimi saqlandi ✅')
            setReceiptForm({ receipt_date: new Date().toISOString().slice(0, 10), supplier: '', items: [] })
            loadAll()
        } catch (e) { toast.error(e.response?.data?.detail || 'Xato') }
    }

    const getIngName = (id) => ingredients.find(i => i.id === id)?.name || id

    return (
        <div className="page">
            <div className="page-header">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div className="page-title">📦 Ombor</div>
                    <button className="btn btn-ghost" style={{ padding: '8px' }} onClick={loadAll}><RefreshCw size={16} /></button>
                </div>
                <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                    {['stock', 'receipt', 'variance'].map(t => (
                        <button key={t} className={`btn ${tab === t ? 'btn-primary' : 'btn-ghost'}`} style={{ padding: '8px 14px', fontSize: '12px' }} onClick={() => setTab(t)}>
                            {t === 'stock' ? '📋 Qoldiq' : t === 'receipt' ? '➕ Kirimi' : '📊 Farq'}
                        </button>
                    ))}
                </div>
            </div>

            {loading && <div className="loader"><div className="spinner" /></div>}

            {/* STOCK TAB */}
            {tab === 'stock' && !loading && (
                <div>
                    <div className="table-wrap">
                        <table>
                            <thead><tr><th>Ingredient</th><th>Birlik</th><th>Faktik</th></tr></thead>
                            <tbody>
                                {stock.map(s => (
                                    <tr key={s.id}>
                                        <td>{s.ingredients?.name}</td>
                                        <td>{s.ingredients?.unit}</td>
                                        <td>
                                            <input type="number" step="0.01" style={{ width: '80px', background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: '6px', color: 'var(--text)', padding: '4px 8px', fontSize: '13px' }}
                                                value={actual[s.ingredient_id] ?? s.quantity}
                                                onChange={e => setActual(p => ({ ...p, [s.ingredient_id]: e.target.value }))} />
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    <button className="btn btn-success btn-full" style={{ marginTop: '12px' }} onClick={saveActual}>💾 Saqlash</button>
                </div>
            )}

            {/* RECEIPT TAB */}
            {tab === 'receipt' && (
                <div>
                    <div className="card">
                        <div className="card-title" style={{ marginBottom: '12px' }}>Yangi Kirimi</div>
                        <div className="form-group"><label className="form-label">Sana</label><input type="date" className="form-input" value={receiptForm.receipt_date} onChange={e => setReceiptForm(p => ({ ...p, receipt_date: e.target.value }))} /></div>
                        <div className="form-group"><label className="form-label">Ta'minotchi</label><input type="text" className="form-input" value={receiptForm.supplier} placeholder="Ixtiyoriy" onChange={e => setReceiptForm(p => ({ ...p, supplier: e.target.value }))} /></div>
                    </div>

                    <div className="card">
                        <div className="card-title" style={{ marginBottom: '12px' }}>Ingredient Qo'shish</div>
                        <div className="form-group">
                            <label className="form-label">Ingredient</label>
                            <select className="form-select" value={newItem.ingredient_id} onChange={e => setNewItem(p => ({ ...p, ingredient_id: e.target.value, unit: ingredients.find(i => i.id === e.target.value)?.unit || 'kg' }))}>
                                <option value="">Tanlang...</option>
                                {ingredients.map(i => <option key={i.id} value={i.id}>{i.name} ({i.unit})</option>)}
                            </select>
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                            <div className="form-group"><label className="form-label">Miqdor</label><input type="number" className="form-input" value={newItem.quantity} onChange={e => setNewItem(p => ({ ...p, quantity: e.target.value }))} /></div>
                            <div className="form-group"><label className="form-label">Narx/birligi</label><input type="number" className="form-input" value={newItem.unit_cost} onChange={e => setNewItem(p => ({ ...p, unit_cost: e.target.value }))} /></div>
                        </div>
                        <button className="btn btn-primary btn-full" onClick={addReceiptItem}><Plus size={14} /> Qo'shish</button>
                    </div>

                    {receiptForm.items.length > 0 && (
                        <div className="card">
                            <div className="card-title" style={{ marginBottom: '8px' }}>Qo'shilganlar ({receiptForm.items.length})</div>
                            {receiptForm.items.map((item, i) => (
                                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                                    <div>{getIngName(item.ingredient_id)}</div>
                                    <div className="text-muted">{item.quantity} {item.unit} × {Number(item.unit_cost).toLocaleString()} = <span className="text-blue">{(item.quantity * item.unit_cost).toLocaleString()}</span></div>
                                </div>
                            ))}
                            <button className="btn btn-success btn-full" style={{ marginTop: '12px' }} onClick={saveReceipt}>💾 Kirimi Saqlash</button>
                        </div>
                    )}
                </div>
            )}

            {/* VARIANCE TAB */}
            {tab === 'variance' && (
                <div>
                    <div className="card">
                        <div className="card-title" style={{ marginBottom: '12px' }}>Real vs Teorik Farq</div>
                        {variance.length === 0 ? <div className="empty-state">Farq ma'lumotlari yo'q</div> : (
                            <div className="table-wrap">
                                <table>
                                    <thead><tr><th>Ingredient</th><th>Teorik</th><th>Faktik</th><th>Farq</th></tr></thead>
                                    <tbody>
                                        {variance.map(a => (
                                            <tr key={a.id}>
                                                <td>{a.ingredients?.name}</td>
                                                <td>{fmt(a.theoretical_qty)}</td>
                                                <td>{fmt(a.actual_qty)}</td>
                                                <td className={a.difference < 0 ? 'text-red font-bold' : 'text-green'}>{fmt(a.difference)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
