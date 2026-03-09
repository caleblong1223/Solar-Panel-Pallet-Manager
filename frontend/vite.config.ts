import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist/web",
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules")) {
            const segments = id.split("node_modules/");
            if (segments.length > 1) {
              return segments[1].split("/")[0];
            }
            return "vendor";
          }
        },
      },
    },
  },
  server: {
    port: 1420,
    strictPort: true,
  },
});
