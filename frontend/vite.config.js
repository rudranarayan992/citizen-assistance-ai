import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      '.ngrok-free.dev'   // allows all ngrok subdomains
    ]
  }
})