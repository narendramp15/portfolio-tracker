import { AlertTriangle, X } from 'lucide-react'
import { useState } from 'react'

/**
 * Tax-season urgency banner shown across the app between January and July.
 * Dismissible per session.
 */
export function TaxSeasonBanner() {
    const [dismissed, setDismissed] = useState(false)

    // Show only Jan–Jul
    const month = new Date().getMonth() + 1
    if (month < 1 || month > 7 || dismissed) return null

    return (
        <div className="relative bg-gradient-to-r from-amber-500/90 to-orange-500/90 text-white px-4 py-2.5 text-center text-sm font-medium flex items-center justify-center gap-2">
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
            <span>
                📅 ITR filing deadline: <strong>July 31, 2026</strong> — Export your STCG/LTCG report now and
                file stress-free.
            </span>
            <a
                href="/app/tax-reports"
                className="ml-2 underline underline-offset-2 font-semibold hover:text-white/90 transition"
            >
                Go to Tax Reports →
            </a>
            <button
                onClick={() => setDismissed(true)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-white/20 transition"
                aria-label="Dismiss"
            >
                <X className="h-4 w-4" />
            </button>
        </div>
    )
}
