import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Frontend dev-server na :5173, proxy /api -> backend FastAPI na :8000.
// Dzięki temu w produkcji i dev używamy tych samych ścieżek względnych.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
