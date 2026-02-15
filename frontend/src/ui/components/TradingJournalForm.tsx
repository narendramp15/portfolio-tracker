import { useState } from 'react'

interface TradingJournalFormProps {
    initialData?: {
        symbol?: string
        entry_price?: number | string
        exit_price?: number | string | null
        quantity?: number | string
        entry_date?: string
        exit_date?: string | null
        notes?: string | null
    }
    onSubmit: (data: Record<string, unknown>) => Promise<void>
    onCancel: () => void
    isLoading?: boolean
    mode?: 'create' | 'update'
}

export function TradingJournalForm({ initialData, onSubmit, onCancel, isLoading, mode = 'create' }: TradingJournalFormProps) {
    const [formData, setFormData] = useState({
        symbol: initialData?.symbol || '',
        entry_price: initialData?.entry_price?.toString() || '',
        exit_price: initialData?.exit_price?.toString() || '',
        quantity: initialData?.quantity?.toString() || '',
        entry_date: initialData?.entry_date || new Date().toISOString().slice(0, 16),
        exit_date: initialData?.exit_date || '',
        notes: initialData?.notes || '',
    })

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target
        setFormData(prev => ({
            ...prev,
            [name]: value
        }))
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (mode === 'create') {
            const data = {
                symbol: formData.symbol,
                entry_price: parseFloat(formData.entry_price),
                exit_price: formData.exit_price ? parseFloat(formData.exit_price) : null,
                quantity: parseFloat(formData.quantity),
                entry_date: formData.entry_date,
                exit_date: formData.exit_date || null,
                notes: formData.notes || null,
            }
            await onSubmit(data)
        } else {
            const data = {
                exit_price: formData.exit_price ? parseFloat(formData.exit_price) : null,
                exit_date: formData.exit_date || null,
                notes: formData.notes || null,
            }
            await onSubmit(data)
        }
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
                {mode === 'create' && (
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Symbol *
                        </label>
                        <input
                            type="text"
                            name="symbol"
                            value={formData.symbol}
                            onChange={handleChange}
                            required
                            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                            placeholder="e.g., RELIANCE.NS"
                        />
                    </div>
                )}

                {mode === 'create' && (
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Quantity *
                        </label>
                        <input
                            type="number"
                            name="quantity"
                            value={formData.quantity}
                            onChange={handleChange}
                            required
                            min="0"
                            step="any"
                            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        />
                    </div>
                )}

                {mode === 'create' && (
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Entry Price *
                        </label>
                        <input
                            type="number"
                            name="entry_price"
                            value={formData.entry_price}
                            onChange={handleChange}
                            required
                            min="0"
                            step="any"
                            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        />
                    </div>
                )}

                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Exit Price
                    </label>
                    <input
                        type="number"
                        name="exit_price"
                        value={formData.exit_price}
                        onChange={handleChange}
                        min="0"
                        step="any"
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    />
                </div>

                {mode === 'create' && (
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Entry Date *
                        </label>
                        <input
                            type="datetime-local"
                            name="entry_date"
                            value={formData.entry_date}
                            onChange={handleChange}
                            required
                            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                        />
                    </div>
                )}

                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Exit Date
                    </label>
                    <input
                        type="datetime-local"
                        name="exit_date"
                        value={formData.exit_date}
                        onChange={handleChange}
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    />
                </div>
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Notes
                </label>
                <textarea
                    name="notes"
                    value={formData.notes}
                    onChange={handleChange}
                    rows={3}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    placeholder="Add any notes about this trade..."
                />
            </div>

            <div className="flex justify-end space-x-3 pt-4">
                <button
                    type="button"
                    onClick={onCancel}
                    className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
                >
                    Cancel
                </button>
                <button
                    type="submit"
                    disabled={isLoading}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                    {isLoading ? 'Saving...' : mode === 'create' ? 'Save Trade' : 'Update Trade'}
                </button>
            </div>
        </form>
    )
}
