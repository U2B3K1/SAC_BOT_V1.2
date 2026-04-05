import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

/**
 * useSyncStore - Offline-First State Management
 * 
 * Bu do'kon barcha foydalanuvchi harakatlarini (sotuv, xarajat) navbatga oladi.
 * Internet uzilgan bo'lsa, ma'lumotlar localStorage'da qoladi.
 * Internet tiklanganda avtomatik sinxronizatsiya bo'ladi.
 */
export const useSyncStore = create(
  persist(
    (set, get) => ({
      offlineQueue: [],
      isSyncing: false,

      // 1. Navbatga amal qo'shish
      enqueueAction: (actionType, payload) => {
        const newAction = {
          id: Math.random().toString(36).substr(2, 9),
          actionType,
          payload,
          createdAt: new Date().toISOString(),
        };

        set((state) => ({
          offlineQueue: [...state.offlineQueue, newAction]
        }));

        // Darhol sinxronlashga urinish
        if (navigator.onLine) {
          get().syncData();
        }
      },

      // 2. Server bilan sinxronizatsiya (Background Sync)
      syncData: async () => {
        const { offlineQueue, isSyncing } = get();
        if (isSyncing || offlineQueue.length === 0 || !navigator.onLine) return;

        set({ isSyncing: true });

        const queue = [...offlineQueue];
        const successfulIds = [];

        for (const action of queue) {
          try {
            // API call - Bu yerda sizning axios instance'ingiz bo'ladi
            // await api.post('/sync', action);
            console.log("Syncing action:", action.actionType);
            successfulIds.push(action.id);
          } catch (error) {
            console.error("Sync failed:", error);
            break; // Birinchi xatodanoq to'xtaymiz (tartib buzilmasligi uchun)
          }
        }

        // Faqat muvaffaqiyatli yuborilganlarni navbatdan o'chirish
        set((state) => ({
          offlineQueue: state.offlineQueue.filter(a => !successfulIds.includes(a.id)),
          isSyncing: false
        }));
      },

      // 3. Navbat hajmi
      getQueueSize: () => get().offlineQueue.length
    }),
    {
      name: 'sac-bot-offline-sync',
      storage: createJSONStorage(() => localStorage),
    }
  )
);

// Window 'online' bo'lganda avtomatik trigger
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    useSyncStore.getState().syncData();
  });
}
