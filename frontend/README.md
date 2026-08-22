# Portfolio Tracker — Frontend

React 19 + TypeScript + Vite SPA for [Portfolio Tracker](../README.md). Start with the root README; this file covers only what is specific to the frontend.

## Development

```bash
npm install
npm run dev
```

Runs on **http://localhost:5173** and proxies `/api` to `http://localhost:8000`, so start the backend first:

```bash
cd .. && uv run uvicorn portfolio_tracker.main:app --reload
```

## Scripts

| Command | Does |
| --- | --- |
| `npm run dev` | Vite dev server with HMR |
| `npm run build` | `tsc -b` then production build into `dist/` |
| `npm run preview` | Serve the built bundle locally |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run lint` | ESLint |
| `npm test` | Vitest — **no component tests exist yet** |

## Environment

| Variable | Purpose |
| --- | --- |
| `VITE_API_URL` | API base URL. Defaults to `/api`, which the dev proxy and the FastAPI-served build both handle. Set it explicitly when the frontend is hosted separately (e.g. Vercel → Render). |

Only `VITE_`-prefixed variables reach the browser. Never put a secret in one.

## Layout

```
src/
├── lib/
│   ├── api.ts        # axios instance: request + response interceptors
│   └── format.ts     # INR and percentage formatting
├── providers/        # auth and theme context
├── router/           # route table — every route is React.lazy
├── hooks/            # data-fetching hooks over TanStack Query
├── store/            # Zustand client state
├── types/            # shared domain types
└── ui/
    ├── pages/        # one component per route
    ├── components/   # shared widgets
    └── layout/       # AppShell, navigation
```

## Conventions

**Never call `axios` directly — import `api` from `lib/api`.** The instance attaches the bearer token and normalises every error into a `userMessage`: a 401 clears the session and redirects, a 402 surfaces the plan-limit message, a 5xx becomes something readable. Bypassing it means an error renders as an empty state — a failed request showing a portfolio worth ₹0, which the user cannot tell apart from an actually empty portfolio.

```ts
import { api, apiErrorMessage } from '../../lib/api'

try {
  const { data } = await api.get('/dashboard/stats')
} catch (err) {
  setError(apiErrorMessage(err))
}
```

**Credentials go in the request body, never in `params`.** Query strings are written to server access logs.

**Money needs the right precision.** `formatCurrencyINR(value)` shows whole rupees, which is right for totals but wrong for per-unit prices — use `formatPriceINR(value)` there, or anything under ₹1 renders as ₹0.

**New routes are lazy.** Add them to `router/router.tsx` via `lazy()` and wrap with the local `page()` helper so they get a Suspense boundary.

## Known gaps

- No component or E2E tests.
- No design system — pages carry their own Tailwind class strings, and `DashboardPage` holds a large inline theme object.
- The dashboard chunk is ~355 kB (recharts). It is code-split, so only dashboard visitors pay for it.
