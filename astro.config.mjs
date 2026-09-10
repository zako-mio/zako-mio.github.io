import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://zako-mio.github.io',
  output: 'static',
  build: {
    format: 'directory',
  },
  compressHTML: true,
});
