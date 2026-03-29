import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
    Upload,
    FileText,
    Trash2,
    TrendingUp,
    TrendingDown,
    PieChart,
    ChevronDown,
    ChevronUp,
    Info,
} from 'lucide-react'

import { api } from '../../lib/api'
import { formatCurrencyINR } from '../../lib/format'
import { Card } from '../components/Card'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type MFHolding = {
    id: number
    folio_number: string
    scheme_name: string
    amc: string
    isin: string | null
    units: number
    nav: number | null
    cost_value: number
    current_value: number
    gain_loss: number
    gain_loss_pct: number
    category: string | null
    registrar: string | null
    updated_at: string | null
}

type MFSummary = {
    total_invested: number
    total_current: number
    total_gain_loss: number
    total_gain_loss_pct: number
    fund_count: number
}

type MFListResponse = {
    holdings: MFHolding[]
    summary: MFSummary
}

type CASImportResult = {
    success: boolean
    registrar_detected: string
    statement_period: { from: string | null; to: string | null }
    folios_created: number
    folios_updated: number
    transactions_imported: number
    transactions_skipped: number
    total_folios_in_cas: number
    warnings: string[]
}

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

async function fetchMFHoldings(): Promise<MFListResponse> {
    const { data } = await api.get<MFListResponse>('/mutual-funds/')
    return data
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

function formatApiError(err: unknown): string {
    const detail = (err as any)?.response?.data?.detail
    if (!detail) return (err as Error)?.message ?? 'Request failed'
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail))
        return detail.map((d: any) => (typeof d === 'object' && d.msg ? String(d.msg) : JSON.stringify(d))).join('; ')
    return JSON.stringify(detail)
}

export function MutualFundsPage() {
    const queryClient = useQueryClient()
    const fileRef = useRef<HTMLInputElement>(null)
    const [file, setFile] = useState<File | null>(null)
    const [password, setPassword] = useState('')
    const [expandedId, setExpandedId] = useState<number | null>(null)

    const query = useQuery({ queryKey: ['mf-holdings'], queryFn: fetchMFHoldings })
    const holdings = query.data?.holdings ?? []
    const summary = query.data?.summary

    // CAS upload mutation
    const importCAS = useMutation({
        mutationFn: async () => {
            if (!file) throw new Error('Select a PDF file')
            const form = new FormData()
            form.append('file', file)
            const params: Record<string, string> = {}
            if (password) params.password = password
            const { data } = await api.post<CASImportResult>('/mutual-funds/import-cas', form, {
                params,
                headers: { 'Content-Type': undefined },
            })
            return data
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ['mf-holdings'] })
            setFile(null)
            setPassword('')
            if (fileRef.current) fileRef.current.value = ''
        },
    })

    // Delete mutation
    const deleteMF = useMutation({
        mutationFn: async (id: number) => {
            await api.delete(`/mutual-funds/${id}`)
        },
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['mf-holdings'] }),
    })

    const casResult = importCAS.data

    // Group by AMC
    const byAmc = holdings.reduce<Record<string, MFHolding[]>>((acc, h) => {
        const key = h.amc || 'Other'
            ; (acc[key] ??= []).push(h)
        return acc
    }, {})

    return (
        <div className="space-y-6">
            {/* Page header */}
            <div>
                <div className="text-sm text-muted">Investments</div>
                <h1 className="text-2xl font-semibold tracking-tight">Mutual Funds</h1>
            </div>

            {/* Summary cards */}
            {summary && summary.fund_count > 0 && (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                    <Card className="p-4">
                        <div className="text-xs font-semibold text-muted uppercase">Invested</div>
                        <div className="mt-1 text-lg font-bold">{formatCurrencyINR(summary.total_invested)}</div>
                    </Card>
                    <Card className="p-4">
                        <div className="text-xs font-semibold text-muted uppercase">Current</div>
                        <div className="mt-1 text-lg font-bold">{formatCurrencyINR(summary.total_current)}</div>
                    </Card>
                    <Card className="p-4">
                        <div className="text-xs font-semibold text-muted uppercase">Gain / Loss</div>
                        <div
                            className={`mt-1 text-lg font-bold ${summary.total_gain_loss >= 0 ? 'text-success' : 'text-danger'
                                }`}
                        >
                            {summary.total_gain_loss >= 0 ? '+' : ''}
                            {formatCurrencyINR(summary.total_gain_loss)}
                        </div>
                    </Card>
                    <Card className="p-4">
                        <div className="text-xs font-semibold text-muted uppercase">Returns</div>
                        <div
                            className={`mt-1 flex items-center gap-1 text-lg font-bold ${summary.total_gain_loss_pct >= 0 ? 'text-success' : 'text-danger'
                                }`}
                        >
                            {summary.total_gain_loss_pct >= 0 ? (
                                <TrendingUp className="h-4 w-4" />
                            ) : (
                                <TrendingDown className="h-4 w-4" />
                            )}
                            {summary.total_gain_loss_pct.toFixed(2)}%
                        </div>
                    </Card>
                </div>
            )}

            {/* CAS Import section */}
            <Card>
                <div className="mb-3 flex items-center gap-2">
                    <PieChart className="h-5 w-5 text-primary" />
                    <h2 className="text-sm font-semibold">Import CAS Statement</h2>
                </div>
                <p className="mb-4 text-xs text-muted">
                    Download your Consolidated Account Statement (CAS) from{' '}
                    <a
                        href="https://www.camsonline.com/Investors/Statements/Consolidated-Account-Statement"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold text-primary hover:underline"
                    >
                        CAMS
                    </a>{' '}
                    or{' '}
                    <a
                        href="https://mfs.kfintech.com/investor/General/ConsolidatedAccountStatement"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold text-primary hover:underline"
                    >
                        KFintech
                    </a>
                    , then upload the PDF here. Existing folios will be updated with the latest data.
                </p>

                <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
                    {/* File drop zone */}
                    <div
                        className="flex flex-1 cursor-pointer items-center gap-3 rounded-xl border-2 border-dashed border-border p-4 transition hover:border-primary/50 hover:bg-surface"
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
                            accept=".pdf,application/pdf"
                            className="hidden"
                            onChange={(e) => {
                                const f = e.target.files?.[0]
                                if (f) setFile(f)
                            }}
                        />
                        {file ? (
                            <div className="flex items-center gap-2 text-sm">
                                <FileText className="h-5 w-5 text-primary" />
                                <span className="font-semibold">{file.name}</span>
                            </div>
                        ) : (
                            <div className="flex items-center gap-2 text-sm text-muted">
                                <Upload className="h-5 w-5" />
                                Drop CAS PDF here, or click to browse
                            </div>
                        )}
                    </div>

                    {/* Password (optional) */}
                    <div>
                        <label className="mb-1 block text-xs font-semibold text-muted">PDF Password</label>
                        <input
                            type="password"
                            className="w-full rounded-xl border border-border bg-bg px-3 py-2 text-sm sm:w-48"
                            placeholder="PAN+DOB (if locked)"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                    </div>

                    <button
                        type="button"
                        disabled={!file || importCAS.isPending}
                        className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2 text-sm font-semibold text-primary-fg shadow-soft disabled:opacity-60"
                        onClick={() => importCAS.mutate()}
                    >
                        <Upload className="h-4 w-4" />
                        {importCAS.isPending ? 'Importing…' : 'Import'}
                    </button>
                </div>

                {/* Password hint */}
                <div className="mt-2 flex items-start gap-1.5 text-xs text-muted">
                    <Info className="mt-0.5 h-3 w-3 flex-shrink-0" />
                    <span>
                        CAS PDFs are usually password-protected with your PAN + Date of Birth (e.g., ABCDE1234F01011990).
                    </span>
                </div>

                {/* Import result */}
                {casResult && (
                    <div className="mt-4 rounded-xl border border-border bg-surface p-4 text-sm space-y-1">
                        <div className="font-semibold text-success">
                            Import complete — {casResult.folios_created} new fund{casResult.folios_created !== 1 ? 's' : ''},{' '}
                            {casResult.folios_updated} updated
                        </div>
                        <div className="text-muted">
                            Registrar: <span className="font-medium">{casResult.registrar_detected}</span> ·
                            Transactions imported: {casResult.transactions_imported} ·
                            Skipped: {casResult.transactions_skipped}
                            {casResult.statement_period.from && (
                                <> · Period: {casResult.statement_period.from?.slice(0, 10)} to{' '}
                                    {casResult.statement_period.to?.slice(0, 10)}</>
                            )}
                        </div>
                        {casResult.warnings.length > 0 && (
                            <details className="mt-2">
                                <summary className="cursor-pointer text-xs text-amber-500">
                                    {casResult.warnings.length} warning{casResult.warnings.length !== 1 ? 's' : ''}
                                </summary>
                                <ul className="mt-1 list-disc pl-4 text-xs text-amber-500">
                                    {casResult.warnings.map((w, i) => (
                                        <li key={i}>{w}</li>
                                    ))}
                                </ul>
                            </details>
                        )}
                    </div>
                )}

                {importCAS.isError && (
                    <div className="mt-3 rounded-xl border border-danger/30 bg-danger/5 p-3 text-sm text-danger">
                        {formatApiError(importCAS.error)}
                    </div>
                )}
            </Card>

            {/* Holdings list */}
            {query.isLoading ? (
                <div className="h-48 animate-pulse rounded-xl border border-border bg-surface" />
            ) : holdings.length === 0 ? (
                <Card>
                    <div className="text-sm font-semibold">No mutual funds yet</div>
                    <div className="mt-1 text-sm text-muted">
                        Upload a CAS statement above to import your MF holdings, or add them manually via the API.
                    </div>
                </Card>
            ) : (
                Object.entries(byAmc).map(([amc, funds]) => (
                    <Card key={amc} className="p-0">
                        <div className="border-b border-border bg-surface px-4 py-3">
                            <div className="text-xs font-semibold uppercase tracking-wide text-muted">{amc}</div>
                        </div>
                        <div className="divide-y divide-border">
                            {funds.map((h) => (
                                <div key={h.id}>
                                    <div
                                        className="flex cursor-pointer items-center gap-4 px-4 py-3 transition hover:bg-bg"
                                        onClick={() => setExpandedId(expandedId === h.id ? null : h.id)}
                                    >
                                        <div className="min-w-0 flex-1">
                                            <div className="truncate text-sm font-semibold">{h.scheme_name}</div>
                                            <div className="mt-0.5 flex gap-3 text-xs text-muted">
                                                <span>Folio: {h.folio_number}</span>
                                                {h.category && <span>· {h.category}</span>}
                                                <span>· {h.units.toFixed(3)} units</span>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <div className="text-sm font-semibold">{formatCurrencyINR(h.current_value)}</div>
                                            <div
                                                className={`text-xs font-semibold ${h.gain_loss >= 0 ? 'text-success' : 'text-danger'
                                                    }`}
                                            >
                                                {h.gain_loss >= 0 ? '+' : ''}
                                                {formatCurrencyINR(h.gain_loss)} ({h.gain_loss_pct.toFixed(1)}%)
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                type="button"
                                                className="rounded p-1 text-muted hover:bg-danger/10 hover:text-danger"
                                                title="Delete"
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    if (confirm(`Delete "${h.scheme_name}"?`)) deleteMF.mutate(h.id)
                                                }}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </button>
                                            {expandedId === h.id ? (
                                                <ChevronUp className="h-4 w-4 text-muted" />
                                            ) : (
                                                <ChevronDown className="h-4 w-4 text-muted" />
                                            )}
                                        </div>
                                    </div>

                                    {/* Expanded detail row */}
                                    {expandedId === h.id && (
                                        <div className="border-t border-border bg-bg/50 px-4 py-3">
                                            <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-xs sm:grid-cols-4">
                                                <div>
                                                    <span className="text-muted">NAV:</span>{' '}
                                                    <span className="font-semibold">{h.nav ? `₹${h.nav.toFixed(2)}` : '—'}</span>
                                                </div>
                                                <div>
                                                    <span className="text-muted">Invested:</span>{' '}
                                                    <span className="font-semibold">{formatCurrencyINR(h.cost_value)}</span>
                                                </div>
                                                <div>
                                                    <span className="text-muted">ISIN:</span>{' '}
                                                    <span className="font-semibold">{h.isin || '—'}</span>
                                                </div>
                                                <div>
                                                    <span className="text-muted">Registrar:</span>{' '}
                                                    <span className="font-semibold">{h.registrar || '—'}</span>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </Card>
                ))
            )}
        </div>
    )
}

export default MutualFundsPage
