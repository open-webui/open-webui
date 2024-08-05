import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
    plugins: [sveltekit()],
    define: {
        APP_VERSION: JSON.stringify(process.env.npm_package_version),
        APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build')
    },
    build: {
        sourcemap: true
    },
    worker: {
        format: 'es'
    },
    server: {
        fs: {
            // Allow serving files from the /static directory
            allow: [
                // Adjust this path to match the actual location of your /static directory
                path.resolve(__dirname, 'static')
            ]
        }
    }
});