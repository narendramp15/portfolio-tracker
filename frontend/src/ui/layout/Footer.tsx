export function Footer() {
    const currentYear = new Date().getFullYear()

    return (
        <footer className="border-t border-border bg-surface/30 backdrop-blur-sm mt-auto">
            <div className="px-6 py-6 sm:px-8">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-2 text-sm text-muted">
                        <span>© {currentYear}</span>
                        <span className="font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                            Quatleap
                        </span>
                        <span>• All rights reserved</span>
                    </div>
                    <div className="flex items-center gap-6 text-xs text-muted">
                        <a href="#" className="hover:text-indigo-400 transition-colors">Privacy Policy</a>
                        <a href="#" className="hover:text-indigo-400 transition-colors">Terms of Service</a>
                        <a href="#" className="hover:text-indigo-400 transition-colors">Contact</a>
                    </div>
                </div>
            </div>
        </footer>
    )
}
