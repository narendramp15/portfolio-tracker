import { Outlet } from 'react-router-dom'

import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'

export function AppShell() {
  return (
    <div className="min-h-full bg-bg text-text">
      <div className="mx-auto grid h-full max-w-[1440px] grid-cols-1 md:grid-cols-[280px_1fr]">
        <Sidebar />
        <div className="min-w-0">
          <TopBar />
          <main className="px-4 py-5 sm:px-6">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}

