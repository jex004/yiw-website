import { defineConfig } from 'vite';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';

export default defineConfig({
	// Docker bind mounts on Windows may not deliver filesystem change events.
	server: {
		watch: { usePolling: true, interval: 500 },
		proxy: Object.fromEntries(
			['/api', '/login', '/auth'].map((path) => [
				path,
				{ target: process.env.API_PROXY_TARGET || 'http://localhost:2000' }
			])
		)
	},
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			adapter: adapter({ fallback: 'index.html' })
		})
	]
});
