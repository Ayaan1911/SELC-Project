import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server is bound to loopback only (this app is intentionally vulnerable).
export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173, strictPort: true },
});
