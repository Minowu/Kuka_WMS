import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface NotificationState {
  readIds: string[]
  markAsRead: (id: string) => void
  markAllAsRead: (ids: string[]) => void
  isRead: (id: string) => boolean
}

export const useNotificationStore = create<NotificationState>()(
  persist(
    (set, get) => ({
      readIds: [],
      markAsRead: (id) =>
        set((state) =>
          state.readIds.includes(id)
            ? state
            : { readIds: [...state.readIds, id] },
        ),
      markAllAsRead: (ids) =>
        set((state) => ({
          readIds: Array.from(new Set([...state.readIds, ...ids])),
        })),
      isRead: (id) => get().readIds.includes(id),
    }),
    {
      name: 'notification-store',
      partialize: (state) => ({ readIds: state.readIds }),
    },
  ),
)
