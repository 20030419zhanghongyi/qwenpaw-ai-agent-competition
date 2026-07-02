import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 本地开发：把 /api 请求代理到后端 8000，避免跨域；前端因此可用相对路径调用。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
