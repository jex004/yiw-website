<script>
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { afterNavigate } from '$app/navigation';
	import { countPageView } from '$lib/analytics.js';
	import '$lib/site.css';
	let { children } = $props();
	const links = [
		{ href: resolve('/'), label: 'Overview', number: '01' },
		{ href: resolve('/members'), label: 'Members', number: '02' },
		{ href: resolve('/timeline'), label: 'Timeline', number: '03' },
		{ href: resolve('/map'), label: 'Map', number: '04' },
		{ href: resolve('/gallery'), label: 'Gallery', number: '05' }
	];
	afterNavigate(({ from, to }) => {
		if (
			to?.url &&
			from?.url?.pathname !== to.url.pathname &&
			links.some((link) => link.href === to.url.pathname)
		) {
			countPageView();
		}
	});
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
	<details class="privacy-note">
		<summary>Privacy &amp; site statistics</summary>
		<p>
			We count page views and successful Discord sign-ins. A random browser identifier, renewed
			daily, helps estimate daily visitors. Statistics cover the last 90 days using daily counts and
			protected visitor identifiers, without storing IP addresses or browsing paths. The server
			owner can see Discord usernames, sign-in counts, and latest sign-in times. Sign-in records are
			separate from page views. Discord usernames are also used for profiles and comments.
		</p>
		<a href={resolve('/stats')}>Owner statistics</a>
	</details>
</div>

<p class="background-credit">
	Background art by <a
		href="https://linktr.ee/that.pixel.artistt"
		target="_blank"
		rel="noopener noreferrer">Fatbeard</a
	>
</p>

<style>
	.privacy-note {
		padding: 12px 32px;
		border-top: 1px solid var(--line);
		color: var(--muted);
		font-size: 0.65rem;
	}
	.privacy-note summary {
		cursor: pointer;
	}
	.privacy-note p {
		max-width: 80ch;
		line-height: 1.6;
	}
</style>
