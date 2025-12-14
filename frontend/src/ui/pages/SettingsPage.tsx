import { useTheme } from '../../providers/theme/ThemeProvider'
import { Card } from '../components/Card'

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

      <Card>
        <div className="text-sm font-semibold">Roadmap</div>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
          <li>Portfolio value chart with date ranges</li>
          <li>Allocation charts (sector, asset class)</li>
          <li>Add/edit transactions (API endpoint needed)</li>
        </ul>
      </Card>
    </div>
  )
}

