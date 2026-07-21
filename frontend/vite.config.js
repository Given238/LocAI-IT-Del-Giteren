import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Default `host: "localhost"` was resolving to the IPv6 loopback only
    // on this machine, so http://127.0.0.1:5173 (IPv4) got connection
    // refused while http://localhost:5173 worked -- bind everything so
    // both forms (and the LAN IP, if ever needed) reach the dev server.
    host: true,
  },
})
