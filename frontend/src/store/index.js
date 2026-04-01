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
    departments: [],
    products: [],
    expenseCategories: [],
    masterDataLoaded: false, // ← Cache flag

    setDepartments: (d) => set({ departments: d }),
    setProducts: (p) => set({ products: p }),
    setExpenseCategories: (c) => set({ expenseCategories: c }),

    // Master data ni bir martalik yuklash
    setMasterData: (depts, prods, cats) => set({
        departments: depts,
        products: prods,
        expenseCategories: cats,
        masterDataLoaded: true,
    }),

    // Logout da cache tozalash
    clearMasterData: () => set({
        departments: [],
        products: [],
        expenseCategories: [],
        masterDataLoaded: false,
    }),
}))
