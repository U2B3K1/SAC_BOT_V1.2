import React, { useState } from 'react'
import { exportApi } from '../api/client'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import { Download, FileSpreadsheet, FileText } from 'lucide-react'

export default function ExportPage() {
    const [params, setParams] = useState({
        date_from: format(new Date(new Date() - 7 * 864e5), 'yyyy-MM-dd'),
        date_to: format(new Date(), 'yyyy-MM-dd'),
    })
    const [loading, setLoading] = useState(false)

    const download = async (type) => {
        setLoading(true)
        try {
            const fn = type === 'excel' ? exportApi.excel : exportApi.pdf
            const { data } = await fn(params)
            const url = URL.createObjectURL(new Blob([data]))
            const a = document.createElement('a')
            a.href = url
            a.download = `hisobot_${params.date_from}_${params.date_to}.${type === 'excel' ? 'xlsx' : 'pdf'}`
            a.click()
            URL.revokeObjectURL(url)
            toast.success(`${type.toUpperCase()} yuklab olindi ✅`)
        } catch { toast.error('Yuklab olishda xato') }
        finally { setLoading(false) }
    }

    return (
        <div className="page">
            <div className="page-header">
                <div className="page-title">📤 Export</div>
                <div className="page-subtitle">Hisobotni Excel yoki PDF sifatida yuklab oling</div>
            </div>
            <div className="card">
                <div className="card-title" style={{ marginBottom: '12px' }}>Davr Tanlash</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <div className="form-group"><label className="form-label">Boshidan</label><input type="date" className="form-input" value={params.date_from} onChange={e => setParams(p => ({ ...p, date_from: e.target.value }))} /></div>
                    <div className="form-group"><label className="form-label">Gacha</label><input type="date" className="form-input" value={params.date_to} onChange={e => setParams(p => ({ ...p, date_to: e.target.value }))} /></div>
                </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <button className="btn btn-success btn-full" onClick={() => download('excel')} disabled={loading} style={{ padding: '16px', fontSize: '15px' }}>
                    <FileSpreadsheet size={20} /> {loading ? 'Yuklanmoqda...' : 'Excel yuklab olish (.xlsx)'}
                </button>
                <button className="btn btn-primary btn-full" onClick={() => download('pdf')} disabled={loading} style={{ padding: '16px', fontSize: '15px' }}>
                    <FileText size={20} /> {loading ? 'Yuklanmoqda...' : 'PDF yuklab olish (.pdf)'}
                </button>
            </div>
            <div className="card" style={{ marginTop: '16px' }}>
                <div className="card-title" style={{ marginBottom: '8px' }}>📌 Export Ichida</div>
                <ul style={{ color: 'var(--text-muted)', fontSize: '13px', paddingLeft: '16px', lineHeight: '2' }}>
                    <li>Har bir bo'lim bo'yicha hisobot</li>
                    <li>Sotuvlar jadvali (mahsulot, miqdor, narx, tannarx, foyda)</li>
                    <li>Xarajatlar jadvali kategoriyalar bo'yicha</li>
                    <li>Daromad, xarajat, sof foyda yig'masi</li>
                    <li>Davr bo'yicha umumiy balans</li>
                </ul>
            </div>
        </div>
    )
}
