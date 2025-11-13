import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "~": resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "../api/static/react",
    emptyOutDir: true,
    manifest: true,
    cssCodeSplit: false,
    rollupOptions: {
      input: {
        main: "./src/main.tsx",
      },
      output: {
        entryFileNames: "assets/main-react-app.js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: (assetInfo) => {
          if (assetInfo.name === "style.css") {
            return "assets/main-react-app.css";
          }
          // Keep SVG and other assets in assets folder with hash for cache busting
          if (assetInfo.name?.endsWith('.svg')) {
            return "assets/[name]-[hash][extname]";
          }
          return "assets/[name][extname]";
        },
      },
    },
  },
  // Ensure assets are properly handled
  assetsInclude: ['**/*.svg'],
});
