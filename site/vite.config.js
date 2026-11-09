import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// The site reads ../level-*/results_*.json and the level READMEs at build time, so every number on the page is generated, never typed.
export default defineConfig({
  base: '/mcp-toolkit/',
  plugins: [react()],
  // Dev server may read only this site and the files it imports, not the whole repo.
  server: { fs: { allow: ['.', '../level-1-learn', '../level-2-build', '../level-3-deep', '../REPORT.md'] } },
});
