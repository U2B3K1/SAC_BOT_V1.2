import React from 'react'
import { NavLink } from 'react-router-dom'
import { useAuthStore } from '../store'
import { LayoutDashboard, FileText, Sparkles, Package, CreditCard, Download, Settings } from 'lucide-react'

export default function NavBar() {
    const { user } = useAuthStore()
    const isSuperUser = user?.role === 'super_user'

    const navItems = [
        { to: '/', icon: LayoutDashboard, label: 'Bosh' },
        { to: '/reports', icon: FileText, label: 'Hisobot' },
        { to: '/ai', icon: Sparkles, label: 'AI' },
        { to: '/inventory', icon: Package, label: 'Ombor' },
        { to: '/debts', icon: CreditCard, label: 'Qarzlar' },
        { to: '/export', icon: Download, label: 'Export' },
        ...(isSuperUser ? [{ to: '/admin', icon: Settings, label: 'Admin' }] : []),
    ]

    return (
        <nav className="nav-bar">
            {navItems.map(({ to, icon: Icon, label }) => (
                <NavLink
                    key={to}
                    to={to}
                    className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                    end={to === '/'}
                >
                    <Icon size={22} />
                    <span>{label}</span>
                </NavLink>
            ))}
        </nav>
    )
}
