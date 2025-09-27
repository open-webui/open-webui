import { defineConfig } from 'vitest/config';
import { resolve } from 'path';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['tests/**/*.{test,spec}.?(c|m)[jt]s?(x)'],
    exclude: [
      'node_modules/**',
      'dist/**',
      '.svelte-kit/**',
      '**/.{idea,git,cache,output,temp}/**',
      '**/{karma,rollup,webpack,vite,vitest,jest,ava,babel,nyc,cypress,tsup,build,eslint,prettier}.config.*'
    ],
    setupFiles: ['./tests/setup.ts']
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@/agents': resolve(__dirname, 'src/agents'),
      '@/ai': resolve(__dirname, 'src/ai'),
      '@/auth': resolve(__dirname, 'src/auth'),
      '@/storage': resolve(__dirname, 'src/storage'),
      '@/types': resolve(__dirname, 'src/types'),
      '@/utils': resolve(__dirname, 'src/utils')
    }
  }
});
