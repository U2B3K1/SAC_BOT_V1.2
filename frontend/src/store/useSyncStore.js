import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { salesApi, expensesApi } from '../api/client';

/**
 * useSyncStore - Offline-First State Management
 *
 * Internet uzilganda harakatlar navbatga olinadi (localStorage).
 * Internet tiklanganda avtomatik sinxronizatsiya amalga oshiriladi.
 *
 * Qo'llab-quvvatlanadigan action turlari:
 *   - 'CREATE_SALE'    → salesApi.create(payload)
 *   - 'CREATE_EXPENSE' → expensesApi.create(payload)
 */

const ACTION_HANDLERS = {
  CREATE_SALE: (payload) => salesApi.create(payload),
  CREATE_EXPENSE: (payload) => expensesApi.create(payload),
};

export const useSyncStore = create(
  persist(
    (set, get) => ({
      offlineQueue: [],
      isSyncing: false,
      lastSyncAt: null,
      failedCount: 0,

      // 1. Navbatga amal qo'shish
      enqueueAction: (actionType, payload) => {
        if (!ACTION_HANDLERS[actionType]) {
          console.error(`[SyncStore] Noma'lum action turi: ${actionType}`);
          return;
        }

        const newAction = {
          id: `${Date.now()}-${Math.random().toString(36).substr(2, 6)}`,
          actionType,
          payload,
          createdAt: new Date().toISOString(),
          retryCount: 0,
        };

        set((state) => ({
          offlineQueue: [...state.offlineQueue, newAction],
        }));

        console.log(`[SyncStore] Navbatga qo'shildi: ${actionType}`, payload);

        // Darhol sinxronlashga urinish
        if (navigator.onLine) {
          setTimeout(() => get().syncData(), 100);
        }
      },

      // 2. Server bilan sinxronizatsiya
      syncData: async () => {
        const { offlineQueue, isSyncing } = get();
        if (isSyncing || offlineQueue.length === 0 || !navigator.onLine) return;

        set({ isSyncing: true });
        console.log(`[SyncStore] Sinxronizatsiya boshlandi (${offlineQueue.length} ta amal)...`);

        const queue = [...offlineQueue];
        const successfulIds = [];
        let newFailedCount = 0;

        for (const action of queue) {
          const handler = ACTION_HANDLERS[action.actionType];
          if (!handler) {
            // Noma'lum amallarni o'chirib tashlash
            successfulIds.push(action.id);
            continue;
          }

          try {
            await handler(action.payload);
            successfulIds.push(action.id);
            console.log(`[SyncStore] ✅ Muvaffaqiyatli: ${action.actionType}`);
          } catch (error) {
            const status = error?.response?.status;

            // 4xx xatoliklar (noto'g'ri ma'lumot) — navbatdan o'chirish
            if (status && status >= 400 && status < 500) {
              console.warn(`[SyncStore] ⚠️ Client xatosi — o'chirilmoqda: ${action.actionType}`, status);
              successfulIds.push(action.id);
            } else {
              // 5xx yoki tarmoq xatoligi — navbatda qoladi
              newFailedCount++;
              console.error(`[SyncStore] ❌ Server xatosi — qayta urinamiz: ${action.actionType}`, error?.message);
              break;
            }
          }
        }

        set((state) => ({
          offlineQueue: state.offlineQueue.filter((a) => !successfulIds.includes(a.id)),
          isSyncing: false,
          lastSyncAt: successfulIds.length > 0 ? new Date().toISOString() : state.lastSyncAt,
          failedCount: newFailedCount,
        }));

        if (newFailedCount > 0) {
          // 30 soniyadan keyin qayta urinish
          setTimeout(() => {
            if (navigator.onLine) get().syncData();
          }, 30000);
        }
      },

      // 3. Navbatni tozalash (foydalanuvchi ixtiyori bilan)
      clearQueue: () => {
        set({ offlineQueue: [], failedCount: 0 });
        console.log('[SyncStore] Navbat tozalandi.');
      },

      // 4. Holat ko'rsatkichlari
      getQueueSize: () => get().offlineQueue.length,
      isOfflinePending: () => get().offlineQueue.length > 0,
    }),
    {
      name: 'sac-bot-offline-sync',
      storage: createJSONStorage(() => localStorage),
      // Faqat navbatni saqlash (isSyncing va boshqalar saqlanmaydi)
      partialize: (state) => ({ offlineQueue: state.offlineQueue }),
    }
  )
);

// Internet tiklanganda avtomatik trigger
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    console.log('[SyncStore] 🌐 Internet tiklandi — sinxronizatsiya boshlanmoqda...');
    useSyncStore.getState().syncData();
  });

  window.addEventListener('offline', () => {
    console.log('[SyncStore] 📴 Internet uzildi — ma\'lumotlar lokallashtiriladi.');
  });
}
