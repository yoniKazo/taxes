import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// GitHub Pages serves a project site at <user>.github.io/<repo>/, not the
// domain root -- without this, built asset URLs resolve to the wrong path.
export default defineConfig({
  base: '/taxes/',
  plugins: [react()],
})
