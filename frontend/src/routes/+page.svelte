<script>
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import ServerExpressions from '$lib/ServerExpressions.svelte';
	import GamesWePlay from '$lib/GamesWePlay.svelte';
	/** @type {{name: string, description: string | null, founded_at: string, owner_name: string | null, member_count: number, icon_url: string | null, emojis?: {id: string, name: string, animated: boolean, image_url: string, still_url: string}[], stickers?: {id: string, name: string, description: string, animated: boolean, image_url: string | null, discord_url: string}[]} | null} */
	let server = $state(null);
	let loading = $state(true);
	let error = $state('');
	const dates = new Intl.DateTimeFormat('en', {
		day: 'numeric',
		month: 'long',
		year: 'numeric',
		timeZone: 'UTC'
	});
	async function load() {
		loading = true;
		error = '';
		try {
			const response = await fetch('/api/server');
			if (!response.ok) throw new Error('Could not load the server details. Please try again.');
			server = await response.json();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Could not load the server details.';
		} finally {
			loading = false;
		}
	}
	onMount(() => {
		void load();
	});
</script>

<main>
	<header class="page-heading">
		<div>
			<p class="section-number">01 / Overview</p>
			<h1>{server?.name ?? 'Server overview'}</h1>
			<p>just the basics</p>
		</div>
		{#if server?.icon_url}<img
				class="server-icon"
				src={server.icon_url}
				alt="Server icon"
				width="80"
				height="80"
			/>{/if}
	</header>
	{#if loading}
		<p class="status" role="status">Loading server details...</p>
	{:else if error}
		<p class="status" role="alert">{error}</p>
		<button onclick={load}>Try again</button>
	{:else if server}
		<dl class="server-facts">
			<div>
				<dt>Created</dt>
				<dd>{dates.format(new Date(`${server.founded_at}T00:00:00Z`))}</dd>
				<dd class="fact-note">Discord server created</dd>
			</div>
			<div>
				<dt>Owner</dt>
				<dd>{server.owner_name ?? 'Not available'}</dd>
				<dd class="fact-note">Current server owner</dd>
			</div>
			<div>
				<dt>Members</dt>
				<dd>{server.member_count.toLocaleString()}</dd>
				<dd class="fact-note">Current members, excluding bots</dd>
			</div>
		</dl>
		<section class="about">
			<div class="about-copy">
				<h2>About</h2>
				<p>
					{server.description ||
						'This is the community website for our Discord server. Find member profiles, server history, and where everyone is from.'}
				</p>
				<a class="button-link" href={resolve('/members')}>View members &rarr;</a>
			</div>
		</section>
	{/if}
	<GamesWePlay />
	{#if server && !loading && !error}<ServerExpressions
			emojis={server.emojis}
			stickers={server.stickers}
		/>{/if}
	<section class="explore" aria-labelledby="explore-title">
		<h2 id="explore-title">Around the site</h2>
		<div class="site-links">
			<a href={resolve('/members')}
				><span>02 / Members</span><strong>Member directory &rarr;</strong>
				<p>Profiles, bios and Minecraft names.</p></a
			>
			<a href={resolve('/timeline')}
				><span>03 / Timeline</span><strong>Server history &rarr;</strong>
				<p>Server events and milestones.</p></a
			>
			<a href={resolve('/map')}
				><span>04 / Map</span><strong>Member map &rarr;</strong>
				<p>The countries our members are from.</p></a
			>
			<a href={resolve('/gallery')}
				><span>05 / Gallery</span><strong>Community gallery &rarr;</strong>
				<p>Photos and screenshots. Coming soon.</p></a
			>
		</div>
	</section>
</main>

<style>
	.server-icon {
		border: 1px solid var(--line);
		object-fit: cover;
	}
	h1 {
		overflow-wrap: anywhere;
	}
	.server-facts {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		border: 1px solid var(--line);
		margin: 0 0 32px;
		background: #f7f3ebdf;
	}
	.server-facts > div {
		padding: 24px;
		border-right: 1px solid var(--line);
	}
	.server-facts > div:last-child {
		border-right: 0;
	}
	dt {
		text-transform: uppercase;
		color: var(--green);
		font-size: 0.7rem;
		margin-bottom: 18px;
	}
	dd {
		margin: 0;
		font-family: 'Arial Narrow', 'Trebuchet MS', sans-serif;
		font-size: 1.65rem;
		overflow-wrap: anywhere;
	}
	.server-facts .fact-note {
		color: var(--muted);
		font-family: 'Courier New', monospace;
		font-size: 0.65rem;
		margin-top: 12px;
	}
	.about {
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 24px;
		margin-bottom: 36px;
	}
	.about-copy {
		flex: 1 1 280px;
		max-width: 720px;
		min-width: 0;
	}
	.about p {
		font-size: 0.85rem;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}
	.about .button-link {
		margin-top: 8px;
	}
	.explore {
		border-top: 1px solid var(--line);
		padding-top: 16px;
	}
	.site-links {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 16px;
	}
	.site-links a {
		display: block;
		border: 1px solid var(--line);
		background: #f7f3ebd9;
		padding: 22px;
		text-decoration: none;
	}
	.site-links a:hover {
		background: #e0e9d4;
	}
	.site-links span {
		display: block;
		font-size: 0.65rem;
		text-transform: uppercase;
		margin-bottom: 16px;
	}
	.site-links strong {
		font-weight: normal;
		font-size: 0.95rem;
	}
	.site-links p,
	.status {
		font-size: 0.75rem;
		color: var(--muted);
	}
	@media (max-width: 650px) {
		.server-facts,
		.site-links {
			grid-template-columns: 1fr;
		}
		.server-facts > div {
			border-right: 0;
			border-bottom: 1px solid var(--line);
			padding: 20px;
		}
		.server-facts > div:last-child {
			border-bottom: 0;
		}
	}
</style>
