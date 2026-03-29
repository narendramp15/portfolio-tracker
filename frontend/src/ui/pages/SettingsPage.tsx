import { useTheme } from '../../providers/theme/ThemeProvider'
import { Card } from '../components/Card'
import { ExternalLink, MessageSquare } from 'lucide-react'

export function SettingsPage() {
  const { mode, setMode } = useTheme()

  return (
    <div className="space-y-6">
      <div>
        <div className="text-sm text-muted">Preferences</div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
      </div>

      <Card>
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-sm font-semibold">Theme</div>
            <div className="text-sm text-muted">Light and dark mode support.</div>
          </div>
          <select
            className="rounded-xl border border-border bg-bg px-3 py-2 text-sm"
            value={mode}
            onChange={(e) => setMode(e.target.value as any)}
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
          </select>
        </div>
      </Card>

      {/* Open a Broker Account */}
      <Card>
        <div className="text-sm font-semibold mb-3">Open a Broker Account</div>
        <p className="text-xs text-muted mb-4">
          Don't have a demat account yet? Open one for free with our partners.
        </p>
        <div className="space-y-2">
          <a
            href="https://angel-one.onelink.me/Wjgr/referral"
            target="_blank"
            rel="noopener noreferrer sponsored"
            className="flex items-center justify-between gap-2 rounded-lg border border-border px-4 py-3 text-sm hover:bg-surface transition-colors"
          >
            <span className="font-medium">Angel One — Free demat + ₹0 brokerage on delivery</span>
            <ExternalLink className="h-4 w-4 text-muted flex-shrink-0" />
          </a>
          <a
            href="https://upstox.com/open-account/"
            target="_blank"
            rel="noopener noreferrer sponsored"
            className="flex items-center justify-between gap-2 rounded-lg border border-border px-4 py-3 text-sm hover:bg-surface transition-colors"
          >
            <span className="font-medium">Upstox — Free demat + instant KYC</span>
            <ExternalLink className="h-4 w-4 text-muted flex-shrink-0" />
          </a>
        </div>
        <p className="text-xs text-muted mt-3 italic">
          Affiliate disclosure: We may earn a commission if you sign up through these links — at no extra cost to you.
        </p>
      </Card>

      {/* File your taxes */}
      <Card>
        <div className="text-sm font-semibold mb-3">File Your Taxes</div>
        <p className="text-xs text-muted mb-4">
          Export your STCG/LTCG report from the Tax Reports page, then file ITR with a partner.
        </p>
        <a
          href="https://cleartax.in/income-tax-efiling"
          target="_blank"
          rel="noopener noreferrer sponsored"
          className="flex items-center justify-between gap-2 rounded-lg border border-border px-4 py-3 text-sm hover:bg-surface transition-colors"
        >
          <span className="font-medium">ClearTax — File ITR in minutes</span>
          <ExternalLink className="h-4 w-4 text-muted flex-shrink-0" />
        </a>
        <p className="text-xs text-muted mt-3 italic">
          Affiliate disclosure: We may earn a commission if you sign up through this link.
        </p>
      </Card>

      {/* Feedback */}
      <Card>
        <div className="flex items-center gap-2 mb-2">
          <MessageSquare className="h-4 w-4 text-primary" />
          <div className="text-sm font-semibold">Feedback</div>
        </div>
        <p className="text-xs text-muted mb-3">
          Help us improve — it takes 30 seconds.
        </p>
        <a
          href="https://tally.so/r/feedback-quantleap"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-lg bg-primary text-white px-4 py-2 text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <MessageSquare className="h-4 w-4" />
          Share Feedback
        </a>
      </Card>

      <Card>
        <div className="text-sm font-semibold">Roadmap</div>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
          <li>Mutual fund tracking (CAS PDF import)</li>
          <li>Price alerts (email + push)</li>
          <li>Portfolio allocation charts</li>
        </ul>
      </Card>
    </div>
  )
}

