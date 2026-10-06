import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api to the FastAPI backend so the browser sees a single
// origin (no CORS in dev) and the session header round-trips cleanly.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8002",
        changeOrigin: true,
      },
    },
  },
});
