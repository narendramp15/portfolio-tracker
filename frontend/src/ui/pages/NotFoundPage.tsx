import { Link } from 'react-router-dom'

import { Card } from '../components/Card'

export function NotFoundPage() {
  return (
    <div className="mx-auto flex max-w-xl items-center justify-center py-16">
      <Card className="w-full">
        <div className="text-lg font-semibold">Page not found</div>
        <div className="mt-1 text-sm text-muted">The page you’re looking for doesn’t exist.</div>
        <div className="mt-4">
          <Link className="text-sm font-semibold text-primary hover:underline" to="/app/dashboard">
            Go to dashboard
          </Link>
        </div>
      </Card>
    </div>
  )
}

