import { defineConfig } from 'vitest/config'

export default defineConfig({
    test: {
        environment: 'jsdom',
        globals: true,
        setupFiles: './src/setupTests.ts',
        include: ['tests/**/*.test.{js,ts,tsx}', 'src/**/__tests__/**/*.test.{js,ts,tsx}'],
    },
})
