import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'

import { api } from '../../lib/api'
import { type Portfolio } from '../../types/domain'
import { Card } from '../components/Card'

type TransactionFormProps = {
    portfolios: Portfolio[]
    initialPortfolio?: Portfolio
    onClose: () => void
}

type TransactionData = {
    asset_id: number
    type: 'buy' | 'sell'
    quantity: number
    price: number
    notes?: string
}

async function createTransaction(portfolioId: number, data: TransactionData) {
    const { data: result } = await api.post(`/transactions/${portfolioId}`, data)
    return result
}

async function getAvailableQuantity(portfolioId: number, assetId: number) {
    const { data } = await api.get(`/transactions/available/${portfolioId}/${assetId}`)
    return data
}

export function TransactionForm({ portfolios, initialPortfolio, onClose }: TransactionFormProps) {
    const queryClient = useQueryClient()
    const [selectedPortfolioId, setSelectedPortfolioId] = useState<string>(
        initialPortfolio?.id.toString() || (portfolios.length > 0 ? portfolios[0].id.toString() : '')
    )
    const [formData, setFormData] = useState({
        asset_id: '',
        type: 'buy' as 'buy' | 'sell',
        quantity: '',
        price: '',
        notes: ''
    })
    const [quantityError, setQuantityError] = useState<string | null>(null)

    const selectedPortfolio = portfolios.find(p => p.id.toString() === selectedPortfolioId)

    // Query for available quantity when selling
    const availableQtyQuery = useQuery({
        queryKey: ['available-qty', selectedPortfolioId, formData.asset_id],
        queryFn: () => {
            if (formData.type === 'sell' && selectedPortfolioId && formData.asset_id) {
                return getAvailableQuantity(parseInt(selectedPortfolioId), parseInt(formData.asset_id))
            }
            return null
        },
        enabled: formData.type === 'sell' && !!selectedPortfolioId && !!formData.asset_id
    })

    const mutation = useMutation({
        mutationFn: (data: TransactionData) => {
            const portfolioId = parseInt(selectedPortfolioId)
            return createTransaction(portfolioId, data)
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['portfolios'] })
            queryClient.invalidateQueries({ queryKey: ['transactions'] })
            queryClient.invalidateQueries({ queryKey: ['available-qty'] })
            onClose()
        },
        onError: (error: any) => {
            console.error('Failed to create transaction:', error)
            const errorMessage = error.response?.data?.detail || 'Failed to create transaction. Please try again.'
            setQuantityError(errorMessage)
        }
    })

    // Validate quantity when selling
    useEffect(() => {
        if (formData.type === 'sell' && formData.quantity && availableQtyQuery.data) {
            const requestedQty = parseFloat(formData.quantity)
            const availableQty = availableQtyQuery.data.available_quantity

            if (requestedQty > availableQty) {
                setQuantityError(`Insufficient quantity. Available: ${availableQty.toFixed(4)}`)
            } else {
                setQuantityError(null)
            }
        } else {
            setQuantityError(null)
        }
    }, [formData.quantity, formData.type, availableQtyQuery.data])

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()

        if (!formData.asset_id || !formData.quantity || !formData.price) {
            alert('Please fill in all required fields')
            return
        }

        const quantity = parseFloat(formData.quantity)
        const price = parseFloat(formData.price)

        if (quantity <= 0 || price <= 0) {
            setQuantityError('Quantity and price must be positive numbers')
            return
        }

        // Additional sell validation
        if (formData.type === 'sell' && availableQtyQuery.data) {
            if (quantity > availableQtyQuery.data.available_quantity) {
                setQuantityError(`Insufficient quantity. Maximum sell: ${availableQtyQuery.data.available_quantity.toFixed(4)}`)
                return
            }
        }

        mutation.mutate({
            asset_id: parseInt(formData.asset_id),
            type: formData.type,
            quantity,
            price,
            notes: formData.notes || undefined
        })
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <Card className="w-full max-w-md">
                <div className="flex items-center justify-between border-b border-border pb-4">
                    <h2 className="text-lg font-semibold">Add Transaction</h2>
                    <button
                        onClick={onClose}
                        className="rounded-lg p-1 hover:bg-surface"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="mt-4 space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-foreground">
                            Portfolio *
                        </label>
                        <select
                            value={selectedPortfolioId}
                            onChange={(e) => {
                                setSelectedPortfolioId(e.target.value)
                                // Reset asset selection when portfolio changes
                                setFormData(prev => ({ ...prev, asset_id: '' }))
                            }}
                            className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm"
                            required
                        >
                            <option value="">Select a portfolio</option>
                            {portfolios.map((portfolio) => (
                                <option key={portfolio.id} value={portfolio.id.toString()}>
                                    {portfolio.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-foreground">
                            Asset *
                        </label>
                        <select
                            value={formData.asset_id}
                            onChange={(e) => setFormData(prev => ({ ...prev, asset_id: e.target.value }))}
                            className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm"
                            required
                            disabled={!selectedPortfolio}
                        >
                            <option value="">
                                {selectedPortfolio ? 'Select an asset' : 'Select a portfolio first'}
                            </option>
                            {selectedPortfolio?.assets.map((asset) => (
                                <option key={asset.id} value={asset.id}>
                                    {asset.symbol} - {asset.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-foreground">
                            Transaction Type *
                        </label>
                        <select
                            value={formData.type}
                            onChange={(e) => setFormData(prev => ({ ...prev, type: e.target.value as 'buy' | 'sell' }))}
                            className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm"
                        >
                            <option value="buy">Buy</option>
                            <option value="sell">Sell</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-foreground">
                            Quantity *
                        </label>
                        <div className="relative">
                            <input
                                type="number"
                                step="0.01"
                                min="0.01"
                                value={formData.quantity}
                                onChange={(e) => setFormData(prev => ({ ...prev, quantity: e.target.value }))}
                                className={`mt-1 w-full rounded-lg border bg-bg px-3 py-2 text-sm ${quantityError ? 'border-red-500 focus:ring-red-500' : 'border-border'
                                    }`}
                                placeholder="e.g., 10.5"
                                required
                            />
                            {/* Show available quantity for sell transactions */}
                            {formData.type === 'sell' && availableQtyQuery.data && (
                                <div className={`text-xs mt-1 ${quantityError ? 'text-red-400' : 'text-muted-foreground'
                                    }`}>
                                    Available: {availableQtyQuery.data.available_quantity.toFixed(4)}
                                    {availableQtyQuery.data.available_quantity !== availableQtyQuery.data.display_quantity && (
                                        <span className="ml-2 opacity-75">
                                            (Display: {availableQtyQuery.data.display_quantity.toFixed(4)})
                                        </span>
                                    )}
                                </div>
                            )}
                            {/* Show loading state */}
                            {formData.type === 'sell' && availableQtyQuery.isFetching && (
                                <div className="text-xs text-muted-foreground mt-1">
                                    Checking available quantity...
                                </div>
                            )}
                            {/* Show error message */}
                            {quantityError && (
                                <div className="text-xs text-red-400 mt-1">
                                    {quantityError}
                                </div>
                            )}
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-foreground">
                            Price per Unit (₹) *
                        </label>
                        <input
                            type="number"
                            step="0.01"
                            min="0.01"
                            value={formData.price}
                            onChange={(e) => setFormData(prev => ({ ...prev, price: e.target.value }))}
                            className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm"
                            placeholder="e.g., 150.25"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-foreground">
                            Notes
                        </label>
                        <textarea
                            value={formData.notes}
                            onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                            className="mt-1 w-full rounded-lg border border-border bg-bg px-3 py-2 text-sm"
                            placeholder="Optional notes..."
                            rows={3}
                        />
                    </div>

                    <div className="flex gap-3 pt-4">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 rounded-lg border border-border bg-bg py-2 text-sm font-semibold hover:bg-surface"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={mutation.isPending}
                            className="flex-1 rounded-lg bg-primary py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                        >
                            {mutation.isPending ? 'Adding...' : 'Add Transaction'}
                        </button>
                    </div>
                </form>
            </Card>
        </div>
    )
}