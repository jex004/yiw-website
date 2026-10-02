<script>
	import gameData from '$lib/games.json';
	/** @type {{name: string, category?: string, note?: string, image?: string, links?: (string | {label?: string, url: string})[]}[]} */
	const entries = gameData;
	const games = entries.map((game) => ({
		...game,
		links: (game.links || [])
			.map((link) => (typeof link === 'string' ? { url: link, label: 'Play online' } : link))
			.filter((link) => isWebLink(link.url))
	}));
	let expanded = $state(false);
	const previewCount = 4;
	let visibleGames = $derived(expanded ? games : games.slice(0, previewCount));
	const palettes = [
		{ accent: '#4f7042', tint: '#dce9b9' },
		{ accent: '#955239', tint: '#f0cfb8' },
		{ accent: '#596584', tint: '#dce2ef' },
		{ accent: '#487873', tint: '#cde7db' },
		{ accent: '#876334', tint: '#f4e3af' },
		{ accent: '#875a77', tint: '#ead5e3' }
	];
	/** @param {string} url */
	function isWebLink(url) {
		try {
			return ['https:', 'http:'].includes(new URL(url).protocol);
		} catch {
			return false;
		}
	}
</script>

<section class="games" aria-labelledby="games-title">
	<div class="section-heading">
		<h2 id="games-title">Games we play</h2>
		<span class="game-count">{games.length} games</span>
	</div>
	{#if games.length}
		<ul class="game-list" id="game-list">
			{#each visibleGames as game, index (index)}
				<li
					style={`--accent: ${palettes[index % palettes.length].accent}; --tint: ${palettes[index % palettes.length].tint}`}
				>
					<div class="cover">
						{#if game.image}
							<img src={game.image} alt="" loading="lazy" />
						{:else}
							<span class="art-placeholder">Game icons coming soon</span>
						{/if}
					</div>
					<div class="game-body">
						{#if game.category}<span class="category">{game.category}</span>{/if}
						<h3>{game.name}</h3>
						{#if game.note}<p>{game.note}</p>{/if}
						{#if game.links?.length}
							<div class="links">
								{#each game.links as link, linkIndex (linkIndex)}
									<!-- eslint-disable svelte/no-navigation-without-resolve -- External game websites. -->
									<a
										href={link.url}
										target="_blank"
										rel="noopener noreferrer"
										aria-label={`${link.label || 'Visit website'} for ${game.name} (opens in a new tab)`}
									>
										{link.label || 'Visit website'} <span aria-hidden="true">&#8599;</span>
									</a>
								{/each}
							</div>
						{/if}
					</div>
				</li>
			{/each}
		</ul>
		{#if games.length > previewCount}
			<button
				class="toggle-games"
				aria-expanded={expanded}
				aria-controls="game-list"
				onclick={() => (expanded = !expanded)}
			>
				{expanded ? 'Show fewer games' : `Show all ${games.length} games`}
			</button>
		{/if}
	{:else}
		<p class="empty">No games listed yet.</p>
	{/if}
</section>

<style>
	.games {
		border-top: 1px solid var(--line);
		padding-top: 16px;
		margin-bottom: 36px;
	}
	.section-heading {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
	}
	.game-count {
		font-size: 0.65rem;
		color: var(--muted);
		white-space: nowrap;
	}
	.game-list {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 230px), 1fr));
		gap: 20px;
		padding: 0;
		margin: 16px 0 0;
		list-style: none;
	}
	li {
		min-width: 0;
		display: flex;
		flex-direction: column;
		border: 1px solid var(--accent);
		background: var(--paper);
		box-shadow: 3px 3px 0 var(--tint);
		overflow-wrap: anywhere;
		transition:
			transform 160ms ease,
			box-shadow 160ms ease;
	}
	li:hover,
	li:focus-within {
		transform: translateY(-3px);
		box-shadow: 4px 7px 0 var(--tint);
	}
	.cover {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		height: 116px;
		border-bottom: 1px solid var(--accent);
		background-color: var(--tint);
		background-image:
			linear-gradient(#ffffff40 1px, transparent 1px),
			linear-gradient(90deg, #ffffff40 1px, transparent 1px);
		background-size: 16px 16px;
	}
	.cover img {
		width: 100%;
		height: 100%;
		object-fit: contain;
		image-rendering: pixelated;
	}
	.art-placeholder {
		padding: 16px;
		color: var(--accent);
		font-size: 0.7rem;
		text-align: center;
	}
	.toggle-games {
		margin-top: 20px;
		min-height: 44px;
	}
	.game-body {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		flex: 1;
		padding: 18px;
	}
	.category {
		color: var(--accent);
		background: var(--tint);
		border: 1px solid var(--accent);
		padding: 4px 7px;
		font-size: 0.6rem;
		text-transform: uppercase;
	}
	h3 {
		margin: 14px 0 8px;
		font-size: 1.2rem;
		line-height: 1.3;
	}
	p {
		font-size: 0.75rem;
		color: var(--muted);
		white-space: pre-wrap;
		margin: 0 0 12px;
	}
	.links {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-top: auto;
		padding-top: 12px;
		width: 100%;
	}
	a {
		display: inline-flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		min-height: 44px;
		padding: 8px 12px;
		border: 1px solid var(--accent);
		background: var(--tint);
		color: var(--accent);
		text-decoration: none;
		font-size: 0.75rem;
	}
	a:hover {
		background: var(--paper);
	}
	.empty {
		margin-top: 16px;
	}
	@media (prefers-reduced-motion: reduce) {
		li {
			transition: none;
		}
		li:hover,
		li:focus-within {
			transform: none;
		}
	}
</style>
