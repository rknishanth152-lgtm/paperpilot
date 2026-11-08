// Vite dev server, build and Vitest configuration.
//
// The browser calls `/api/...` on the dev server, which forwards to the
// backend at API_PROXY_TARGET (frontend/.env). Same origin, so the backend
// needs no CORS settings, and no backend URL is written into the code.
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, import.meta.dirname, "");
  const target = env.API_PROXY_TARGET;
  // Only the dev server forwards requests; builds and tests do not need it.
  if (command === "serve" && mode !== "test" && !target) {
    throw new Error(
      "API_PROXY_TARGET is not set. Copy frontend/.env.example to frontend/.env.",
    );
  }
  return {
    plugins: [react()],
    server: {
      // Local machine only (NFR-SEC-006).
      host: "127.0.0.1",
      port: 5173,
      strictPort: true,
      proxy: target
        ? { "/api": { target, rewrite: (path: string) => path.replace(/^\/api/, "") } }
        : undefined,
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/test/setup.ts"],
    },
  };
});
