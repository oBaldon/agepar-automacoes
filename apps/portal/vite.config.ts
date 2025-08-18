import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
    server: {
    host: true,       // 0.0.0.0 (exposto na rede)
    port: 5173,
    strictPort: true
  }
})