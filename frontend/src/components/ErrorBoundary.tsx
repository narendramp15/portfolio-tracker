import React from 'react'

type State = { hasError: boolean; error?: Error }

export class ErrorBoundary extends React.Component<React.PropsWithChildren<{}>, State> {
    constructor(props: React.PropsWithChildren<{}>) {
        super(props)
        this.state = { hasError: false }
    }

    static getDerivedStateFromError() {
        return { hasError: true }
    }

    componentDidCatch(error: Error, info: React.ErrorInfo) {
        // Log to console (or send to monitoring)
        // eslint-disable-next-line no-console
        console.error('Uncaught error in React tree:', error, info)
        this.setState({ error })
    }

    render() {
        if (this.state.hasError) {
            return (
                <div style={{ padding: 24, fontFamily: 'Inter, system-ui, sans-serif' }}>
                    <h1 style={{ color: '#e11d48' }}>Something went wrong</h1>
                    <p>Open the browser console for the error details.</p>
                    <pre style={{ whiteSpace: 'pre-wrap', marginTop: 12 }}>{this.state.error?.message}</pre>
                </div>
            )
        }

        return this.props.children
    }
}

export default ErrorBoundary
