import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const authProxyPort = process.env.GITHUB_AUTH_PROXY_PORT || 5174;

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api/auth': {
        target: `http://localhost:${authProxyPort}`,
        changeOrigin: true
      }
    }
  }
});
