import { api } from './api'
import type { TradingJournalEntry, TradingJournalSummary, TradingJournalCreate, TradingJournalUpdate } from '../types/domain'

export const tradingJournalApi = {
    async getEntries(portfolioId: number, params?: { skip?: number; limit?: number; symbol?: string }) {
        const queryParams = new URLSearchParams()
        if (params?.skip) queryParams.set('skip', params.skip.toString())
        if (params?.limit) queryParams.set('limit', params.limit.toString())
        if (params?.symbol) queryParams.set('symbol', params.symbol)

        const query = queryParams.toString()
        const response = await api.get<TradingJournalEntry[]>(
            `/journal/${portfolioId}${query ? `?${query}` : ''}`
        )
        return response.data
    },

    async getStats(portfolioId: number) {
        const response = await api.get<TradingJournalSummary>(`/journal/${portfolioId}/stats`)
        return response.data
    },

    async getEntry(portfolioId: number, journalId: number) {
        const response = await api.get<TradingJournalEntry>(`/journal/${portfolioId}/${journalId}`)
        return response.data
    },

    async createEntry(portfolioId: number, data: TradingJournalCreate) {
        const response = await api.post<TradingJournalEntry>(`/journal/${portfolioId}`, data)
        return response.data
    },

    async updateEntry(portfolioId: number, journalId: number, data: TradingJournalUpdate) {
        const response = await api.patch<TradingJournalEntry>(`/journal/${portfolioId}/${journalId}`, data)
        return response.data
    },

    async deleteEntry(portfolioId: number, journalId: number) {
        await api.delete(`/journal/${portfolioId}/${journalId}`)
    }
}
