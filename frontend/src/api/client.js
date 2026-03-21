import axios from 'axios'

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/api/v1',
    timeout: 30000,
})

// Token ni headerga qo'shish
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
})

// Token yangilash
api.interceptors.response.use(
    (res) => res,
    async (error) => {
        if (error.response?.status === 401) {
            const refresh = localStorage.getItem('refresh_token')
            if (refresh) {
                try {
                    const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refresh })
                    localStorage.setItem('access_token', data.access_token)
                    error.config.headers.Authorization = `Bearer ${data.access_token}`
                    return api(error.config)
                } catch {
                    localStorage.clear()
                    window.location.reload()
                }
            }
        }
        return Promise.reject(error)
    }
)

// AUTH
export const authApi = {
    login: (init_data) => api.post('/auth/telegram', { init_data }),
    refresh: (refresh_token) => api.post('/auth/refresh', { refresh_token }),
}

// REPORTS
export const reportsApi = {
    list: (params) => api.get('/reports/daily', { params }),
    create: (data) => api.post('/reports/daily', data),
    get: (id) => api.get(`/reports/daily/${id}`),
    update: (id, data) => api.patch(`/reports/daily/${id}`, data),
    submit: (id) => api.post(`/reports/daily/${id}/submit`),
    approve: (id) => api.post(`/reports/daily/${id}/approve`),
    range: (params) => api.get('/reports/range', { params }),
    summary: (days, params) => api.get(`/reports/summary/${days}`, { params }),
}

// SALES
export const salesApi = {
    list: (params) => api.get('/sales/', { params }),
    create: (data) => api.post('/sales/', data),
    bulk: (data) => api.post('/sales/bulk', data),
    delete: (id) => api.delete(`/sales/${id}`),
}

// EXPENSES
export const expensesApi = {
    list: (params) => api.get('/expenses/', { params }),
    create: (data) => api.post('/expenses/', data),
    delete: (id) => api.delete(`/expenses/${id}`),
}

// INVENTORY
export const inventoryApi = {
    stock: () => api.get('/inventory/stock'),
    updateStock: (data) => api.patch('/inventory/stock', data),
    createReceipt: (data) => api.post('/inventory/receipts', data),
    receipts: (params) => api.get('/inventory/receipts', { params }),
    variance: () => api.get('/inventory/variance'),
    theoretical: (params) => api.get('/inventory/theoretical', { params }),
}

// DEBTS
export const debtsApi = {
    list: (params) => api.get('/debts/', { params }),
    get: (id) => api.get(`/debts/${id}`),
    create: (data) => api.post('/debts/', data),
    addPayment: (id, data) => api.post(`/debts/${id}/payments`, data),
    sendSms: (id, data) => api.post(`/debts/${id}/sms`, data),
}

// AI
export const aiApi = {
    parseScreenshot: (file) => {
        const form = new FormData()
        form.append('file', file)
        return api.post('/ai/parse-screenshot', form, {
            headers: { 'Content-Type': 'multipart/form-data' },
            timeout: 60000,
        })
    },
    parseAudio: (file) => {
        const form = new FormData()
        form.append('file', file)
        return api.post('/ai/parse-audio', form, {
            headers: { 'Content-Type': 'multipart/form-data' },
            timeout: 60000,
        })
    },
    importExcel: (file) => {
        const form = new FormData()
        form.append('file', file)
        return api.post('/ai/import-excel', form, {
            headers: { 'Content-Type': 'multipart/form-data' },
        })
    },
    getSession: (id) => api.get(`/ai/sessions/${id}`),
    confirmSession: (id, data) => api.post(`/ai/sessions/${id}/confirm`, data),
    rejectSession: (id) => api.post(`/ai/sessions/${id}/reject`),
}

// ADMIN
export const adminApi = {
    // Users
    users: () => api.get('/admin/users'),
    createUser: (data) => api.post('/admin/users', data),
    updateUser: (id, data) => api.patch(`/admin/users/${id}`, data),
    // Departments
    departments: () => api.get('/admin/departments'),
    // Products
    products: (params) => api.get('/admin/products', { params }),
    createProduct: (data) => api.post('/admin/products', data),
    updateProduct: (id, data) => api.patch(`/admin/products/${id}`, data),
    // Ingredients
    ingredients: () => api.get('/admin/ingredients'),
    createIngredient: (data) => api.post('/admin/ingredients', data),
    // Recipes
    recipes: () => api.get('/admin/recipes'),
    createRecipe: (data) => api.post('/admin/recipes', data),
    updateRecipe: (id, data) => api.patch(`/admin/recipes/${id}`, data),
    // Expense categories
    expenseCategories: () => api.get('/admin/expense-categories'),
    // Audit
    auditLogs: (params) => api.get('/admin/audit-logs', { params }),
}

// EXPORT
export const exportApi = {
    excel: (params) => api.get('/export/excel', { params, responseType: 'blob' }),
    pdf: (params) => api.get('/export/pdf', { params, responseType: 'blob' }),
}

export default api
