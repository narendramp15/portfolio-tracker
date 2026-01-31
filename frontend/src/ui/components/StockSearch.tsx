import { useState, useEffect, useRef } from 'react'
import { Search, TrendingUp } from 'lucide-react'
import { api } from '../../lib/api'
import { formatCurrencyINR } from '../../lib/format'

interface StockResult {
    symbol: string
    name: string
    exchange: string
    current_price?: number | null
    currency?: string
}

interface StockSearchProps {
    onSelect: (stock: StockResult) => void
    market?: 'IN' | 'US'
    placeholder?: string
}

export function StockSearch({ onSelect, market = 'IN', placeholder = 'Search stocks...' }: StockSearchProps) {
    const [query, setQuery] = useState('')
    const [results, setResults] = useState<StockResult[]>([])
    const [isOpen, setIsOpen] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const [selectedIndex, setSelectedIndex] = useState(-1)
    const wrapperRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
                setIsOpen(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    // Search stocks with debounce
    useEffect(() => {
        if (query.length < 2) {
            setResults([])
            setIsOpen(false)
            return
        }

        const timeoutId = setTimeout(async () => {
            setIsLoading(true)
            try {
                const response = await api.get('/market/search', {
                    params: { q: query, market }
                })
                setResults(response.data.results || [])
                setIsOpen(true)
                setSelectedIndex(-1)
            } catch (error) {
                console.error('Stock search error:', error)
                setResults([])
            } finally {
                setIsLoading(false)
            }
        }, 300)

        return () => clearTimeout(timeoutId)
    }, [query, market])

    // Keyboard navigation
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (!isOpen || results.length === 0) return

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault()
                setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : prev))
                break
            case 'ArrowUp':
                e.preventDefault()
                setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1))
                break
            case 'Enter':
                e.preventDefault()
                if (selectedIndex >= 0 && selectedIndex < results.length) {
                    handleSelect(results[selectedIndex])
                }
                break
            case 'Escape':
                setIsOpen(false)
                setSelectedIndex(-1)
                break
        }
    }

    const handleSelect = (stock: StockResult) => {
        onSelect(stock)
        setQuery('')
        setResults([])
        setIsOpen(false)
        setSelectedIndex(-1)
    }

    return (
        <div ref={wrapperRef} className="relative">
            <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
                <input
                    ref={inputRef}
                    type="text"
                    className="w-full rounded-xl border border-border bg-bg px-9 py-2 text-sm outline-none ring-primary focus:ring-2"
                    placeholder={placeholder}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    onFocus={() => results.length > 0 && setIsOpen(true)}
                />
                {isLoading && (
                    <div className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                )}
            </div>

            {isOpen && results.length > 0 && (
                <div className="absolute z-50 mt-1 w-full rounded-xl border border-border bg-bg shadow-lg">
                    <div className="max-h-[300px] overflow-y-auto">
                        {results.map((stock, index) => (
                            <button
                                key={stock.symbol}
                                onClick={() => handleSelect(stock)}
                                onMouseEnter={() => setSelectedIndex(index)}
                                className={`flex w-full items-start gap-3 border-b border-border px-4 py-3 text-left transition-colors last:border-0 ${index === selectedIndex ? 'bg-primary/10' : 'hover:bg-surface'
                                    } focus:outline-none`}
                            >
                                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                                    <TrendingUp className="h-4 w-4 text-primary" />
                                </div>
                                <div className="min-w-0 flex-1">
                                    <div className="flex items-baseline justify-between gap-2">
                                        <div className="truncate font-semibold">{stock.symbol}</div>
                                        {stock.current_price !== null && stock.current_price !== undefined && (
                                            <div className="shrink-0 text-sm font-medium">
                                                {stock.currency === 'INR'
                                                    ? formatCurrencyINR(stock.current_price)
                                                    : `$${stock.current_price.toFixed(2)}`}
                                            </div>
                                        )}
                                    </div>
                                    <div className="mt-0.5 truncate text-xs text-muted">{stock.name}</div>
                                    <div className="mt-0.5 text-xs text-muted/70">{stock.exchange}</div>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {isOpen && query.length >= 2 && results.length === 0 && !isLoading && (
                <div className="absolute z-50 mt-1 w-full rounded-xl border border-border bg-bg px-4 py-3 text-sm text-muted shadow-lg">
                    No stocks found for "{query}"
                </div>
            )}
        </div>
    )
}

