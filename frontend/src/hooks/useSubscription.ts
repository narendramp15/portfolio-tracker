import { useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '../lib/api'
import type { SubscriptionStatus, SubscriptionTier } from '../types/domain'

export function useSubscription() {
    const queryClient = useQueryClient()

    const query = useQuery<SubscriptionStatus>({
        queryKey: ['subscription'],
        queryFn: async () => {
            const { data } = await api.get<SubscriptionStatus>('/billing/subscription')
            return data
        },
        staleTime: 60_000, // 1 minute
    })

    const sub = query.data
    const tier: SubscriptionTier = sub?.tier ?? 'free'
    const isPro = tier === 'pro' || tier === 'teams'

    const maxExports = sub?.limits.exports_per_month ?? 3
    const usedExports = sub?.usage.exports_this_month ?? 0
    const exportsRemaining = isPro ? null : Math.max(0, maxExports - usedExports)

    const maxBrokers = sub?.limits.max_brokers ?? 2

    function invalidate() {
        queryClient.invalidateQueries({ queryKey: ['subscription'] })
    }

    return {
        subscription: sub,
        tier,
        isPro,
        maxBrokers,
        exportsRemaining,
        usedExports,
        maxExports: isPro ? null : maxExports,
        razorpayKeyId: sub?.razorpay_key_id ?? null,
        isLoading: query.isLoading,
        invalidate,
    }
}
