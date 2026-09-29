<script>
	/** @typedef {{id: string, name: string, animated: boolean, image_url: string, still_url: string}} Emoji */
	/** @typedef {{id: string, name: string, description: string, animated: boolean, image_url: string | null, discord_url: string}} Sticker */
	/** @type {{emojis?: Emoji[], stickers?: Sticker[]}} */
	let { emojis = [], stickers = [] } = $props();
	let emojiLimit = $state(24),
		stickerLimit = $state(8);
	/** @type {Set<string>} */
	let failed = $state(new Set());
	/** @param {string} key */
	function imageFailed(key) {
		failed = new Set([...failed, key]);
	}
</script>

<section class="expressions" aria-labelledby="expressions-title">
	<div class="heading">
		<h2 id="expressions-title">Server emojis &amp; stickers</h2>
	</div>
	<h3>Emojis <span>{emojis.length}</span></h3>
	{#if emojis.length}
		<div class="emoji-grid">
			{#each emojis.slice(0, emojiLimit) as emoji (emoji.id)}
				<!-- eslint-disable svelte/no-navigation-without-resolve -- External Discord media URL. -->
				<a
					class="emoji"
					href={emoji.image_url}
					target="_blank"
					rel="noopener noreferrer"
					title={`:${emoji.name}:`}
					aria-label={`Open emoji ${emoji.name}`}
				>
					{#if failed.has(`emoji-${emoji.id}`)}<span class="fallback">Preview unavailable</span>
					{:else}<img
							src={emoji.image_url}
							alt=""
							width="40"
							height="40"
							loading="lazy"
							onerror={() => imageFailed(`emoji-${emoji.id}`)}
						/>{/if}
					<span class="name">:{emoji.name}:</span>
				</a>
			{/each}
		</div>
		{#if emojis.length > emojiLimit}<button class="more" onclick={() => (emojiLimit += 24)}
				>Show more emojis</button
			>{/if}
	{:else}<p class="empty">No custom emojis yet.</p>{/if}
	<h3>Stickers <span>{stickers.length}</span></h3>
	{#if stickers.length}
		<div class="sticker-grid">
			{#each stickers.slice(0, stickerLimit) as sticker (sticker.id)}
				<!-- eslint-disable svelte/no-navigation-without-resolve -- External Discord media URL. -->
				<a
					class="sticker"
					href={sticker.image_url || sticker.discord_url}
					target="_blank"
					rel="noopener noreferrer"
					aria-label={`Open sticker ${sticker.name}`}
				>
					<div class="sticker-preview">
						{#if !sticker.image_url}<span class="fallback">View in Discord &rarr;</span>
						{:else if failed.has(`sticker-${sticker.id}`)}<span class="fallback"
								>Preview unavailable</span
							>
						{:else}<img
								src={sticker.image_url}
								alt={sticker.description || ''}
								width="120"
								height="120"
								loading="lazy"
								onerror={() => imageFailed(`sticker-${sticker.id}`)}
							/>{/if}
					</div>
					<span class="name">{sticker.name}</span>
				</a>
			{/each}
		</div>
		{#if stickers.length > stickerLimit}<button class="more" onclick={() => (stickerLimit += 8)}
				>Show more stickers</button
			>{/if}
	{:else}<p class="empty">No custom stickers yet.</p>{/if}
</section>

<style>
	.expressions {
		border-top: 1px solid var(--line);
		padding-top: 16px;
		margin-bottom: 36px;
	}
	.heading {
		display: flex;
		justify-content: space-between;
		align-items: center;
		flex-wrap: wrap;
		gap: 12px;
	}
	h3 {
		font-size: 1rem;
		margin: 24px 0 16px;
	}
	h3 span {
		font:
			0.7rem 'Courier New',
			monospace;
		color: var(--muted);
		margin-left: 8px;
	}
	.emoji-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
		gap: 10px;
	}
	.emoji,
	.sticker {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 12px;
		border: 1px solid var(--line);
		background: #f7f3ebdd;
		padding: 14px 8px;
		text-decoration: none;
		min-width: 0;
	}
	.emoji:hover,
	.sticker:hover {
		background: #e0e9d4;
	}
	img {
		object-fit: contain;
		max-width: 100%;
	}
	.name {
		font-size: 0.65rem;
		text-align: center;
		overflow-wrap: anywhere;
		max-width: 100%;
	}
	.sticker-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
		gap: 14px;
	}
	.sticker-preview {
		min-height: 120px;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	.fallback {
		font-size: 0.65rem;
		color: var(--muted);
		text-align: center;
		line-height: 1.5;
	}
	.more {
		margin-top: 16px;
	}
	.empty {
		font-size: 0.75rem;
		color: var(--muted);
	}
	@media (max-width: 400px) {
		.sticker-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
	}
</style>
