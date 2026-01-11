import { Outlet } from 'react-router-dom'

import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { Footer } from './Footer'

export function AppShell() {
  return (
    <div className="min-h-screen bg-bg text-text flex flex-col">
      <div className="mx-auto grid flex-1 w-full max-w-[1600px] grid-cols-1 md:grid-cols-[280px_1fr] gap-0">
        <Sidebar />
        <div className="min-w-0 flex flex-col">
          <TopBar />
          <main className="flex-1 px-6 py-6 sm:px-8">
            <Outlet />
          </main>
          <Footer />
        </div>
      </div>
    </div>
  )
}

