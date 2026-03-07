/// <reference types="vite/client" />

interface ImportMetaEnv {
    /** Anthropic API key for the Nifty Options Analyzer. Set in frontend/.env */
    readonly VITE_ANTHROPIC_API_KEY?: string
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}
