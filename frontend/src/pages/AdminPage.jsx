import React, { useEffect, useState } from 'react'
import { adminApi } from '../api/client'
import { useAuthStore } from '../store'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Plus, LogOut } from 'lucide-react'

export default function AdminPage() {
    const { user, logout } = useAuthStore()
    const navigate = useNavigate()
    const [tab, setTab] = useState('users')
    const [users, setUsers] = useState([])
    const [products, setProducts] = useState([])
    const [ingredients, setIngredients] = useState([])
    const [loading, setLoading] = useState(false)
    const [newUser, setNewUser] = useState({ telegram_id: '', full_name: '', phone: '', role: 'manager' })
    const [newProd, setNewProd] = useState({ name: '', sale_price: 0, department_id: '' })
    const [newIng, setNewIng] = useState({ name: '', unit: '', cost_per_unit: 0 })
    const [departments, setDepartments] = useState([])

    useEffect(() => {
        if (user?.role !== 'super_user') { navigate('/'); return }
        loadData()
    }, [tab])

    const loadData = async () => {
        setLoading(true)
        try {
            const [u, p, i, d] = await Promise.all([adminApi.users(), adminApi.products(), adminApi.ingredients(), adminApi.departments()])
            setUsers(u.data); setProducts(p.data); setIngredients(i.data); setDepartments(d.data)
        } finally { setLoading(false) }
    }

    const createUser = async () => {
        if (!newUser.telegram_id || !newUser.full_name) return toast.error("TG ID va ism kerak")
        try { await adminApi.createUser({ ...newUser, telegram_id: +newUser.telegram_id }); toast.success('Foydalanuvchi qo\'shildi'); setNewUser({ telegram_id: '', full_name: '', phone: '', role: 'manager' }); loadData() }
        catch (e) { toast.error(e.response?.data?.detail || 'Xato') }
    }

    const toggleActive = async (u) => {
        await adminApi.updateUser(u.id, { is_active: !u.is_active })
        toast.success(u.is_active ? 'O\'chirildi' : 'Faollashtirildi')
        loadData()
    }

    const createProduct = async () => {
        if (!newProd.name || !newProd.department_id) return toast.error("Ism va bo'lim kerak")
        try { await adminApi.createProduct({ ...newProd, sale_price: +newProd.sale_price }); toast.success('Mahsulot qo\'shildi'); setNewProd({ name: '', sale_price: 0, department_id: '' }); loadData() }
        catch (e) { toast.error(e.response?.data?.detail || 'Xato') }
    }

    const createIngredient = async () => {
        if (!newIng.name || !newIng.unit) return toast.error("Nomi va o'lchov birligi kerak")
        try { await adminApi.createIngredient({ ...newIng, cost_per_unit: +newIng.cost_per_unit }); toast.success('Ingredient qo\'shildi'); setNewIng({ name: '', unit: '', cost_per_unit: 0 }); loadData() }
        catch (e) { toast.error(e.response?.data?.detail || 'Xato') }
    }

    return (
        <div className="page">
            <div className="page-header">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div className="page-title">⚙️ Admin Panel</div>
                    <button className="btn btn-danger" style={{ padding: '8px 12px', fontSize: '12px' }} onClick={() => { logout(); navigate('/login') }}><LogOut size={14} /> Chiqish</button>
                </div>
                <div style={{ display: 'flex', gap: '6px', marginTop: '12px', flexWrap: 'wrap' }}>
                    {['users', 'products', 'ingredients'].map(t => (
                        <button key={t} className={`btn ${tab === t ? 'btn-primary' : 'btn-ghost'}`} style={{ padding: '8px 12px', fontSize: '12px' }} onClick={() => setTab(t)}>
                            {t === 'users' ? '👥 Users' : t === 'products' ? '🍽️ Mahsulotlar' : '🥩 Ingredientlar'}
                        </button>
                    ))}
                </div>
            </div>

            {loading && <div className="loader"><div className="spinner" /></div>}

            {/* USERS */}
            {tab === 'users' && !loading && (
                <div>
                    <div className="card">
                        <div className="card-title" style={{ marginBottom: '12px' }}>Yangi Foydalanuvchi</div>
                        <div className="form-group"><label className="form-label">Telegram ID</label><input type="number" className="form-input" value={newUser.telegram_id} onChange={e => setNewUser(p => ({ ...p, telegram_id: e.target.value }))} /></div>
                        <div className="form-group"><label className="form-label">Ism Familya</label><input type="text" className="form-input" value={newUser.full_name} onChange={e => setNewUser(p => ({ ...p, full_name: e.target.value }))} /></div>
                        <div className="form-group"><label className="form-label">Telefon</label><input type="tel" className="form-input" value={newUser.phone} onChange={e => setNewUser(p => ({ ...p, phone: e.target.value }))} /></div>
                        <div className="form-group"><label className="form-label">Rol</label><select className="form-select" value={newUser.role} onChange={e => setNewUser(p => ({ ...p, role: e.target.value }))}><option value="manager">Manager</option><option value="super_user">Super User</option></select></div>
                        <button className="btn btn-primary btn-full" onClick={createUser}><Plus size={14} /> Qo'shish</button>
                    </div>
                    {users.map(u => (
                        <div key={u.id} className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <div style={{ fontWeight: 700 }}>{u.full_name}</div>
                                <div className="text-muted" style={{ fontSize: '12px' }}>ID: {u.telegram_id} · {u.role}</div>
                            </div>
                            <button className={`btn ${u.is_active ? 'btn-danger' : 'btn-success'}`} style={{ padding: '6px 12px', fontSize: '12px' }} onClick={() => toggleActive(u)}>
                                {u.is_active ? 'O\'chirish' : 'Faollashtirish'}
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* PRODUCTS */}
            {tab === 'products' && !loading && (
                <div>
                    <div className="card">
                        <div className="card-title" style={{ marginBottom: '12px' }}>Yangi Mahsulot</div>
                        <div className="form-group"><label className="form-label">Nomi</label><input type="text" className="form-input" value={newProd.name} onChange={e => setNewProd(p => ({ ...p, name: e.target.value }))} /></div>
                        <div className="form-group"><label className="form-label">Bo'lim</label><select className="form-select" value={newProd.department_id} onChange={e => setNewProd(p => ({ ...p, department_id: e.target.value }))}><option value="">Tanlang...</option>{departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></div>
                        <div className="form-group"><label className="form-label">Sotuv narxi (so'm)</label><input type="number" className="form-input" value={newProd.sale_price} onChange={e => setNewProd(p => ({ ...p, sale_price: e.target.value }))} /></div>
                        <button className="btn btn-primary btn-full" onClick={createProduct}><Plus size={14} /> Qo'shish</button>
                    </div>
                    {products.map(p => (
                        <div key={p.id} className="card" style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <div><div style={{ fontWeight: 600 }}>{p.name}</div><div className="text-muted" style={{ fontSize: '12px' }}>{p.departments?.name}</div></div>
                            <div className="text-blue font-bold">{Number(p.sale_price).toLocaleString()} so'm</div>
                        </div>
                    ))}
                </div>
            )}

            {/* INGREDIENTS */}
            {tab === 'ingredients' && !loading && (
                <div>
                    <div className="card">
                        <div className="card-title" style={{ marginBottom: '12px' }}>Yangi Ingredient</div>
                        <div className="form-group"><label className="form-label">Nomi</label><input type="text" className="form-input" value={newIng.name} onChange={e => setNewIng(p => ({ ...p, name: e.target.value }))} /></div>
                        <div className="form-group"><label className="form-label">O'lchov birligi</label><input type="text" className="form-input" placeholder="masalan: kg, litr, dona" value={newIng.unit} onChange={e => setNewIng(p => ({ ...p, unit: e.target.value }))} /></div>
                        <div className="form-group"><label className="form-label">1 {newIng.unit || 'birlik'} narxi (so'm)</label><input type="number" className="form-input" value={newIng.cost_per_unit} onChange={e => setNewIng(p => ({ ...p, cost_per_unit: e.target.value }))} /></div>
                        <button className="btn btn-primary btn-full" onClick={createIngredient}><Plus size={14} /> Qo'shish</button>
                    </div>
                    {ingredients.map(i => (
                        <div key={i.id} className="card" style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <div><div style={{ fontWeight: 600 }}>{i.name}</div><div className="text-muted" style={{ fontSize: '12px' }}>{i.unit} · {Number(i.cost_per_unit).toLocaleString()} so'm/{i.unit}</div></div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
