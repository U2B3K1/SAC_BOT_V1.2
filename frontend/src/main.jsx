import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
    <BrowserRouter>
        <App />
        <Toaster
            position="top-center"
            toastOptions={{
                duration: 3000,
                style: {
                    background: '#1A2744',
                    color: '#E8EDF5',
                    border: '1px solid #2D4270',
                    borderRadius: '10px',
                    fontSize: '13px',
                },
                success: { iconTheme: { primary: '#27AE60', secondary: '#0A1628' } },
                error: { iconTheme: { primary: '#C0392B', secondary: '#0A1628' } },
            }}
        />
    </BrowserRouter>
)
