<script>
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import '$lib/site.css';
	let { children } = $props();
	const links = [
		{ href: resolve('/'), label: 'Overview', number: '01' },
		{ href: resolve('/members'), label: 'Members', number: '02' },
		{ href: resolve('/timeline'), label: 'Timeline', number: '03' },
		{ href: resolve('/map'), label: 'Map', number: '04' },
		{ href: resolve('/gallery'), label: 'Gallery', number: '05' }
	];
</script>

<a class="skip-link" href="#content">Skip to content</a>
<div class="site-frame">
	<header class="site-header">
		<a class="wordmark" href={resolve('/')} aria-label="YIW home">YIW</a>
		<div class="site-caption">
			youtube is whack<br /><span>just a silly lil server of friends (˶ˆᗜˆ˵)</span>
		</div>
		<span class="header-stamp">YIW / ONLINE</span>
	</header>
	<nav class="site-nav" aria-label="Main navigation">
		{#each links as link (link.href)}
			<!-- eslint-disable svelte/no-navigation-without-resolve -- Navigation URLs are resolved above. -->
			<a href={link.href} aria-current={page.url.pathname === link.href ? 'page' : undefined}>
				<span>{link.number}</span>{link.label}
			</a>
		{/each}
	</nav>
	<div id="content" class="site-content" tabindex="-1">{@render children()}</div>
	<footer class="site-footer">
		<a href={resolve('/')}>YIW</a><span>Overview / Members / Timeline / Map / Gallery</span>
	</footer>
</div>

<p class="background-credit">
	Background art by <a
		href="https://linktr.ee/that.pixel.artistt"
		target="_blank"
		rel="noopener noreferrer">Fatbeard</a
	>
</p>
