import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import ErrorBoundary from './components/ErrorBoundary'

// Quick mount log to detect whether main bundle runs
// eslint-disable-next-line no-console
console.log('main.tsx running — mounting React app')

const root = document.getElementById('root')
if (!root) {
  // eslint-disable-next-line no-console
  console.error('Root element not found: #root')
} else {
  createRoot(root).render(
    <StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </StrictMode>,
  )
}
