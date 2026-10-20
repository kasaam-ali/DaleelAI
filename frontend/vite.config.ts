/** Dev server and the production build for the React app. */

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { fbrLawDate } from './src/lib/lawDate.ts'

// The Home trust row says how current the FBR laws are; the catalog is the source of truth.
const catalog = readFileSync(fileURLToPath(new URL('../backend/pipeline/catalog.csv', import.meta.url)), 'utf8')

export default defineConfig({
  plugins: [react(), tailwindcss()],
  define: {
    __FBR_LAW_DATE__: JSON.stringify(fbrLawDate(catalog)),
  },
})
