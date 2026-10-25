
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/ExoLens/',
  plugins: [react()],
  resolve: { preserveSymlinks: true },
  server: { port: 5173 },
  test: { environment: 'jsdom', setupFiles: './src/test-setup.ts' },
})
