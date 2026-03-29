import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Upload, FileText, Download, X, ExternalLink, Info } from 'lucide-react'

import { api } from '../../lib/api'
import { type Portfolio } from '../../types/domain'
import { useAppStore } from '../../store/appStore'

type ImportResult = {
    success: boolean
    detected_format: string
    total_rows: number
    imported: number
    skipped_duplicates: number
    skipped_invalid: number
    errors: string[]
}

type BrokerGuide = {
    label: string
    steps: string[]
    url: string
    urlLabel: string
    note?: string
}

const BROKER_GUIDES: Record<string, BrokerGuide> = {
    zerodha: {
        label: 'Zerodha',
        steps: [
            'Log in at console.zerodha.com',
            'Go to Reports → Tradebook',
            'Select the date range (up to 1 year at a time)',
            'Click the Download icon (↓) → choose CSV',
        ],
        url: 'https://console.zerodha.com/reports/tradebook',
        urlLabel: 'Open Zerodha Console',
        note: 'Zerodha limits each download to 1 year. Run multiple exports for longer history.',
    },
    groww: {
        label: 'Groww',
        steps: [
            'Log in at groww.in',
            'Go to Profile (top-right) → Reports',
            'Select Stocks → P&L Report',
            'Choose the financial year and click Download CSV',
        ],
        url: 'https://groww.in/stocks/profile/reports',
        urlLabel: 'Open Groww Reports',
        note: 'Download one financial year at a time. Repeat for each year.',
    },
    fivepaisa: {
        label: '5Paisa',
        steps: [
            'Log in at 5paisa.com',
            'Go to Reports → Trade Report',
            'Set the date range and click Search',
            'Click Export → CSV',
        ],
        url: 'https://trade.5paisa.com/trading-tool/trade-history',
        urlLabel: 'Open 5Paisa Trade History',
    },
    generic: {
        label: 'Manual / Generic',
        steps: [
            'Download the sample CSV template below',
            'Fill in your transactions (date, symbol, type, quantity, price, etc.)',
            'Save as UTF-8 CSV and upload',
        ],
        url: '#sample',
        urlLabel: 'Download sample template',
    },
}

function formatApiError(err: unknown): string {
    const detail = (err as any)?.response?.data?.detail
    if (!detail) return (err as Error)?.message ?? 'Import failed'
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
        return detail
            .map((d: any) => (typeof d === 'object' && d.msg ? String(d.msg) : JSON.stringify(d)))
            .join('; ')
    }
    return JSON.stringify(detail)
}

export function CSVImportUpload({ onDone }: { onDone?: () => void }) {
    const queryClient = useQueryClient()
    const fileRef = useRef<HTMLInputElement>(null)
    const [file, setFile] = useState<File | null>(null)
    const [broker, setBroker] = useState<string>('')
    const { selectedPortfolioId, setSelectedPortfolioId } = useAppStore()

    const portfoliosQuery = useQuery({
        queryKey: ['portfolios'],
        queryFn: async () => {
            const { data } = await api.get<Portfolio[]>('/portfolio/')
            return data
        },
    })
    const portfolios = portfoliosQuery.data ?? []

    const resolvedId = selectedPortfolioId
        ? Number(selectedPortfolioId)
        : portfolios.length === 1
            ? portfolios[0].id
            : null

    const importMutation = useMutation({
        mutationFn: async () => {
            if (!file || !resolvedId) return
            const form = new FormData()
            form.append('file', file)
            const params: Record<string, string> = { portfolio_id: String(resolvedId) }
            if (broker) params.broker = broker
            const { data } = await api.post<ImportResult>('/transactions/import-csv', form, {
                params,
                headers: { 'Content-Type': undefined },
            })
            return data
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ['transactions'] })
            await queryClient.invalidateQueries({ queryKey: ['portfolios'] })
            onDone?.()
        },
    })

    const result = importMutation.data

    const downloadSample = async () => {
        try {
            const res = await api.get('/transactions/import-csv/sample', { responseType: 'blob' })
            const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }))
            const a = document.createElement('a')
            a.href = url
            a.download = 'quantleap_import_template.csv'
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            window.URL.revokeObjectURL(url)
        } catch {
            /* ignore */
        }
    }

    return (
        <div className="space-y-4">
            {/* Portfolio + broker selectors */}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                <div className="flex-1">
                    <label className="mb-1 block text-xs font-semibold text-muted">Portfolio</label>
                    <select
                        className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm"
                        value={resolvedId ?? ''}
                        onChange={(e) => setSelectedPortfolioId(e.target.value ? Number(e.target.value) : null)}
                    >
                        <option value="" disabled>
                            {portfolios.length ? 'Select portfolio' : 'No portfolios'}
                        </option>
                        {portfolios.map((p) => (
                            <option key={p.id} value={p.id}>
                                {p.name}
                            </option>
                        ))}
                    </select>
                </div>
                <div className="flex-1">
                    <label className="mb-1 block text-xs font-semibold text-muted">Broker format</label>
                    <select
                        className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm"
                        value={broker}
                        onChange={(e) => setBroker(e.target.value)}
                    >
                        <option value="">Auto-detect</option>
                        <option value="zerodha">Zerodha</option>
                        <option value="groww">Groww</option>
                        <option value="fivepaisa">5Paisa</option>
                        <option value="generic">Manual / Generic</option>
                    </select>
                </div>
            </div>

            {/* Broker download guide */}
            {broker && BROKER_GUIDES[broker] && (
                <div className="rounded-xl border border-border bg-surface/60 p-4 text-sm">
                    <div className="mb-2 flex items-center gap-1.5 font-semibold">
                        <Info className="h-4 w-4 text-primary flex-shrink-0" />
                        How to download from {BROKER_GUIDES[broker].label}
                    </div>
                    <ol className="list-decimal space-y-1 pl-5 text-muted">
                        {BROKER_GUIDES[broker].steps.map((step, i) => (
                            <li key={i}>{step}</li>
                        ))}
                    </ol>
                    {BROKER_GUIDES[broker].note && (
                        <p className="mt-2 text-xs text-amber-500">{BROKER_GUIDES[broker].note}</p>
                    )}
                    {broker !== 'generic' && (
                        <a
                            href={BROKER_GUIDES[broker].url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                        >
                            <ExternalLink className="h-3 w-3" />
                            {BROKER_GUIDES[broker].urlLabel}
                        </a>
                    )}
                </div>
            )}

            {/* Drop zone */}
            <div
                className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border p-6 text-center transition hover:border-primary/50 hover:bg-surface"
                onClick={() => fileRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                    e.preventDefault()
                    const f = e.dataTransfer.files[0]
                    if (f) setFile(f)
                }}
            >
                <input
                    ref={fileRef}
                    type="file"
                    accept=".csv,text/csv"
                    className="hidden"
                    onChange={(e) => {
                        const f = e.target.files?.[0]
                        if (f) setFile(f)
                    }}
                />
                {file ? (
                    <div className="flex items-center gap-2">
                        <FileText className="h-5 w-5 text-primary" />
                        <span className="text-sm font-semibold">{file.name}</span>
                        <button
                            type="button"
                            className="rounded p-0.5 hover:bg-danger/10"
                            onClick={(e) => {
                                e.stopPropagation()
                                setFile(null)
                                if (fileRef.current) fileRef.current.value = ''
                            }}
                        >
                            <X className="h-4 w-4 text-danger" />
                        </button>
                    </div>
                ) : (
                    <>
                        <Upload className="h-8 w-8 text-muted" />
                        <p className="text-sm text-muted">
                            Drag & drop a CSV file here, or <span className="font-semibold text-primary">browse</span>
                        </p>
                        <p className="text-xs text-muted">Zerodha tradebook, Groww, 5Paisa, or manual format (max 5 MB)</p>
                    </>
                )}
            </div>

            {/* Actions */}
            <div className="flex flex-wrap items-center gap-3">
                <button
                    type="button"
                    disabled={!file || !resolvedId || importMutation.isPending}
                    className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2 text-sm font-semibold text-primary-fg shadow-soft disabled:opacity-60"
                    onClick={() => importMutation.mutate()}
                >
                    <Upload className="h-4 w-4" />
                    {importMutation.isPending ? 'Importing…' : 'Import'}
                </button>
                <button
                    type="button"
                    className="inline-flex items-center gap-2 rounded-xl border border-border bg-bg px-4 py-2 text-sm font-semibold hover:bg-surface"
                    onClick={downloadSample}
                >
                    <Download className="h-4 w-4" />
                    Download sample CSV
                </button>
            </div>

            {/* Result summary */}
            {result && (
                <div className="rounded-xl border border-border bg-surface p-4 text-sm space-y-1">
                    <div className="font-semibold text-success">
                        Import complete — {result.imported} transaction{result.imported !== 1 ? 's' : ''} added
                    </div>
                    <div className="text-muted">
                        Format detected: <span className="font-medium">{result.detected_format}</span> ·
                        Total rows: {result.total_rows} ·
                        Duplicates skipped: {result.skipped_duplicates} ·
                        Invalid skipped: {result.skipped_invalid}
                    </div>
                    {result.errors.length > 0 && (
                        <details className="mt-2">
                            <summary className="cursor-pointer text-xs text-danger">
                                {result.errors.length} warning{result.errors.length !== 1 ? 's' : ''}
                            </summary>
                            <ul className="mt-1 list-disc pl-4 text-xs text-danger">
                                {result.errors.map((e, i) => (
                                    <li key={i}>{e}</li>
                                ))}
                            </ul>
                        </details>
                    )}
                </div>
            )}

            {importMutation.isError && (
                <div className="rounded-xl border border-danger/30 bg-danger/5 p-3 text-sm text-danger">
                    {formatApiError(importMutation.error)}
                </div>
            )}
        </div>
    )
}
