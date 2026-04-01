import { create } from 'zustand'

export const useAuthStore = create((set) => ({
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    isAuthenticated: !!localStorage.getItem('access_token'),

    login: (userData, accessToken, refreshToken) => {
        localStorage.setItem('access_token', accessToken)
        localStorage.setItem('refresh_token', refreshToken)
        localStorage.setItem('user', JSON.stringify(userData))
        set({ user: userData, isAuthenticated: true })
    },

    logout: () => {
        localStorage.clear()
        set({ user: null, isAuthenticated: false })
    },
}))

export const useAppStore = create((set, get) => ({
    // Master data
    departments: [],
    products: [],
    expenseCategories: [],
    masterDataLoaded: false, 

    // O'zgaruvchan List ma'lumotlari (Caching for fast navigation)
    reports: [],
    debts: [],
    inventory: [],
    
    // Status flags
    reportsLoaded: false,
    debtsLoaded: false,
    inventoryLoaded: false,

    setDepartments: (d) => set({ departments: d }),
    setProducts: (p) => set({ products: p }),
    setExpenseCategories: (c) => set({ expenseCategories: c }),

    setMasterData: (depts, prods, cats) => set({
        departments: depts,
        products: prods,
        expenseCategories: cats,
        masterDataLoaded: true,
    }),

    setReportsCache: (vals) => set({ reports: vals, reportsLoaded: true }),
    setDebtsCache: (vals) => set({ debts: vals, debtsLoaded: true }),
    setInventoryCache: (vals) => set({ inventory: vals, inventoryLoaded: true }),

    clearMasterData: () => set({
        departments: [], products: [], expenseCategories: [],
        reports: [], debts: [], inventory: [],
        masterDataLoaded: false, reportsLoaded: false, debtsLoaded: false, inventoryLoaded: false
    }),
}))
