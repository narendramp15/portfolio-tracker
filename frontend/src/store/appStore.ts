import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type AppState = {
  selectedPortfolioId: number | null
  setSelectedPortfolioId: (id: number | null) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      selectedPortfolioId: null,
      setSelectedPortfolioId: (id) => set({ selectedPortfolioId: id }),
    }),
    { name: 'portfolio_tracker_app' },
  ),
)

