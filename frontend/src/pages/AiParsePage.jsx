import React, { useState, useRef } from 'react'
import { aiApi } from '../api/client'
import { useAppStore } from '../store'
import toast from 'react-hot-toast'
import { Camera, Mic, FileSpreadsheet, CheckCircle, XCircle } from 'lucide-react'

export default function AiParsePage() {
    const { products } = useAppStore()
    const [mode, setMode] = useState(null) // 'screenshot' | 'audio' | 'excel'
    const [loading, setLoading] = useState(false)
    const [session, setSession] = useState(null)
    const [parsedData, setParsedData] = useState(null)
    const [polling, setPolling] = useState(false)
    const fileRef = useRef()

    const poll = async (sessionId, attempts = 0) => {
        if (attempts > 30) { toast.error("Vaqt tugadi, qayta urinib ko'ring"); setPolling(false); return }
        try {
            const { data } = await aiApi.getSession(sessionId)
            if (data.parsed_data && Object.keys(data.parsed_data).length > 0) {
                setParsedData(data.parsed_data)
                setPolling(false)
            } else {
                setTimeout(() => poll(sessionId, attempts + 1), 2000)
            }
        } catch {
            setTimeout(() => poll(sessionId, attempts + 1), 2000)
        }
    }

    const handleUpload = async (file) => {
        if (!file) return
        setLoading(true); setParsedData(null); setSession(null)
        try {
            let res
            if (mode === 'screenshot') res = await aiApi.parseScreenshot(file)
            else if (mode === 'audio') res = await aiApi.parseAudio(file)
            else if (mode === 'excel') res = await aiApi.importExcel(file)
            setSession(res.data.session_id)
            toast.success('Fayl yuborildi, tahlil qilinmoqda...')
            setPolling(true)
            setTimeout(() => poll(res.data.session_id), 3000)
        } catch (e) { toast.error(e.response?.data?.detail || 'Yuklashda xato') }
        finally { setLoading(false) }
    }

    const confirm = async () => {
        try {
            await aiApi.confirmSession(session, { session_id: session, confirmed_data: parsedData })
            toast.success('Ma\'lumotlar saqlandi! ✅')
            setSession(null); setParsedData(null); setMode(null)
        } catch (e) { toast.error(e.response?.data?.detail || 'Xato') }
    }

    const reject = async () => {
        if (session) await aiApi.rejectSession(session)
        setSession(null); setParsedData(null); setMode(null)
        toast('Bekor qilindi')
    }

    const items = parsedData?.items || []
    const totalConfidence = items.length ? Math.round(items.reduce((s, i) => s + (i.confidence || 0), 0) / items.length) : 0

    return (
        <div className="page">
            <div className="page-header">
                <div className="page-title">✨ AI Parsing</div>
                <div className="page-subtitle">Screenshot, Audio yoki Excel bilan ma'lumot kiritish</div>
            </div>

            {!mode && !parsedData && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {[
                        { key: 'screenshot', icon: Camera, label: '📸 Screenshot Yuklash', sub: 'Kassa screenshotidan sotuv o\'qish' },
                        { key: 'audio', icon: Mic, label: '🎙️ Audio Kiritish', sub: 'Ovozli xabar yuborish — Whisper transkripsiya qiladi' },
                        { key: 'excel', icon: FileSpreadsheet, label: '📊 Excel Import', sub: '.xlsx yoki .xls fayl yuklash' },
                    ].map(({ key, label, sub }) => (
                        <button key={key} className="card" style={{ cursor: 'pointer', textAlign: 'left', border: '1px solid var(--border)' }}
                            onClick={() => { setMode(key); setTimeout(() => fileRef.current?.click(), 100) }}>
                            <div style={{ fontWeight: 700, fontSize: '15px', marginBottom: '4px' }}>{label}</div>
                            <div className="text-muted" style={{ fontSize: '12px' }}>{sub}</div>
                        </button>
                    ))}
                </div>
            )}

            {/* File input (hidden) */}
            <input
                ref={fileRef} type="file" style={{ display: 'none' }}
                accept={mode === 'screenshot' ? 'image/*' : mode === 'audio' ? 'audio/*' : '.xlsx,.xls'}
                onChange={e => { if (e.target.files[0]) handleUpload(e.target.files[0]); e.target.value = '' }}
            />

            {/* Loading */}
            {(loading || polling) && (
                <div style={{ textAlign: 'center', padding: '48px 24px' }}>
                    <div className="spinner" style={{ margin: '0 auto 16px' }} />
                    <div style={{ fontWeight: 600 }}>AI tahlil qilmoqda...</div>
                    <div className="text-muted" style={{ fontSize: '12px', marginTop: '8px' }}>Bu 10-30 soniya vaqt olishi mumkin</div>
                </div>
            )}

            {/* Natija */}
            {parsedData && !loading && !polling && (
                <div>
                    <div className="card">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                            <div className="card-title">🤖 AI Natijasi</div>
                            <span className={`badge ${totalConfidence >= 80 ? 'badge-approved' : 'badge-submitted'}`}>
                                {totalConfidence}% aniqlik
                            </span>
                        </div>

                        {/* Audio transkripsiya */}
                        {parsedData.transcript && (
                            <div style={{ background: 'var(--bg-input)', padding: '12px', borderRadius: '8px', marginBottom: '12px', fontSize: '13px', color: 'var(--text-muted)' }}>
                                🎙️ <em>"{parsedData.transcript}"</em>
                            </div>
                        )}

                        {/* Sotuvlar */}
                        {items.length > 0 && (
                            <div className="table-wrap">
                                <table>
                                    <thead><tr><th>Mahsulot</th><th>Miqdor</th><th>Narx</th><th>Aniqlik</th></tr></thead>
                                    <tbody>
                                        {items.map((item, i) => (
                                            <tr key={i}>
                                                <td>
                                                    <div style={{ fontWeight: 600 }}>{item.matched_name || item.product_name}</div>
                                                    {item.matched_name !== item.product_name && <div className="text-muted" style={{ fontSize: '11px' }}>Asl: {item.product_name}</div>}
                                                    {item.needs_review && <span className="badge badge-submitted" style={{ fontSize: '10px' }}>Tekshiring</span>}
                                                </td>
                                                <td>{item.quantity}</td>
                                                <td>{Number(item.unit_price).toLocaleString()}</td>
                                                <td><span className={`badge ${(item.confidence || 0) >= 80 ? 'badge-approved' : 'badge-active'}`}>{item.confidence || 0}%</span></td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}

                        {/* Xarajat */}
                        {parsedData.type === 'expense' && (
                            <div style={{ padding: '12px', background: 'rgba(192,57,43,0.1)', borderRadius: '8px' }}>
                                <div style={{ fontWeight: 700 }}>Xarajat: {Number(parsedData.amount || 0).toLocaleString()} so'm</div>
                                <div className="text-muted" style={{ fontSize: '12px' }}>Kategoriya: {parsedData.category} | {parsedData.description}</div>
                            </div>
                        )}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                        <button className="btn btn-success" onClick={confirm}><CheckCircle size={16} /> Tasdiqlash</button>
                        <button className="btn btn-danger" onClick={reject}><XCircle size={16} /> Rad etish</button>
                    </div>

                    <button className="btn btn-ghost btn-full" style={{ marginTop: '10px' }} onClick={() => { setMode(null); setParsedData(null); setSession(null) }}>
                        ← Orqaga
                    </button>
                </div>
            )}
        </div>
    )
}
