<script>
	import photos from '$lib/smp.json';
	import { dismissOnBackdrop } from '$lib/dismissOnBackdrop.js';
	/** @typedef {{id: string, src: string, title: string, alt: string, credit?: string}} Photo */
	/** @type {Photo[]} */
	const gallery = photos;
	/** @type {HTMLDialogElement} */
	let dialog;
	let selected = $state(0);
	let active = $derived(gallery[selected]);
	let failed = $state(/** @type {string[]} */ ([]));
	function open(index = 0) {
		selected = index;
		dialog.showModal();
	}
	/** @param {number} step */
	function move(step) {
		selected = (selected + step + gallery.length) % gallery.length;
	}
	/** @param {KeyboardEvent} event */
	function navigate(event) {
		if (gallery.length < 2 || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
		event.preventDefault();
		move(event.key === 'ArrowLeft' ? -1 : 1);
	}
</script>

{#snippet picture(index = 0, large = false)}
	{@const photo = gallery[index]}
	{#if failed.includes(photo.id)}
		<span class="unavailable">Image unavailable</span>
	{:else}
		<img
			src={photo.src}
			alt={photo.alt}
			loading="lazy"
			class:large
			onerror={() => (failed = [...failed, photo.id])}
		/>
	{/if}
{/snippet}

{#snippet emptyScene()}
	<div class="empty-scene">
		<div class="landscape" aria-hidden="true"><span></span><i></i><b></b></div>
		<p>Screenshots coming soon</p>
	</div>
{/snippet}

<section class="smp" aria-labelledby="smp-heading">
	<div class="intro">
		<h2 id="smp-heading">YIW SMP</h2>
		<button class="text-button" aria-haspopup="dialog" onclick={() => open()}>See all &rarr;</button
		>
	</div>
	{#if gallery.length}
		<div class="highlights" class:single={gallery.length === 1}>
			{#each gallery.slice(0, 3) as photo, index (photo.id)}
				<button
					class="highlight"
					class:hero={index === 0}
					onclick={() => open(index)}
					aria-haspopup="dialog"
					aria-label={`View ${photo.title}`}
				>
					{@render picture(index)}
					<span class="photo-label"
						><span>{photo.title}</span><span aria-hidden="true">↗</span></span
					>
				</button>
			{/each}
		</div>
	{:else}
		<button
			class="empty-preview"
			onclick={() => open()}
			aria-haspopup="dialog"
			aria-label="Open YIW SMP gallery"
		>
			{@render emptyScene()}
		</button>
	{/if}
	<div class="section-foot">
		<span>Our shared world.</span><span>January 2025 - Present</span>
	</div>
</section>

<dialog
	bind:this={dialog}
	use:dismissOnBackdrop={() => dialog.close()}
	aria-labelledby="smp-gallery-title"
	onkeydown={navigate}
>
	<header class="gallery-header">
		<div>
			<p class="eyebrow">THE WORLD ALBUM</p>
			<h2 id="smp-gallery-title">YIW SMP</h2>
		</div>
		<button class="close" onclick={() => dialog.close()} aria-label="Close SMP gallery"
			>Close &times;</button
		>
	</header>
	<div class="gallery-body">
		{#if active}
			<div class="viewer">
				{#key active.id}<div class="full-photo">{@render picture(selected, true)}</div>{/key}
			</div>
			<div class="viewer-info">
				<div>
					<h3>{active.title}</h3>
					{#if active.credit}<p>{active.credit}</p>{/if}
				</div>
				<div class="navigation">
					<button
						onclick={() => move(-1)}
						disabled={gallery.length < 2}
						aria-label="Previous screenshot">&larr;</button
					>
					<span aria-live="polite">{selected + 1} / {gallery.length}</span>
					<button onclick={() => move(1)} disabled={gallery.length < 2} aria-label="Next screenshot"
						>&rarr;</button
					>
				</div>
			</div>
			<div class="photo-grid" aria-label="All SMP screenshots">
				{#each gallery as photo, index (photo.id)}
					<button
						class:selected={selected === index}
						aria-pressed={selected === index}
						onclick={() => (selected = index)}
					>
						<span class="thumbnail">{@render picture(index)}</span><span class="thumbnail-title"
							>{photo.title}</span
						>
					</button>
				{/each}
			</div>
		{:else}
			{@render emptyScene()}
			<p class="empty-note">A place for our builds, landscapes, and moments from the SMP.</p>
		{/if}
	</div>
</dialog>

<style>
	.smp {
		margin-top: 48px;
		border-top: 1px solid var(--line);
		padding-top: 30px;
	}
	.intro,
	.section-foot,
	.gallery-header,
	.viewer-info,
	.navigation {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 20px;
	}
	.intro {
		align-items: center;
		margin-bottom: 22px;
	}
	.text-button {
		background: transparent;
		border: 0;
		padding: 10px 0;
		color: var(--green);
		min-height: 44px;
	}
	.text-button:hover {
		background: transparent;
		text-decoration: underline;
	}
	.eyebrow {
		font-size: 0.6rem;
		letter-spacing: 0.16em;
		color: var(--muted);
		margin: 0 0 10px;
	}
	h2 {
		margin: 0;
		font-size: 1.8rem;
	}
	.intro h2 {
		font-size: clamp(2rem, 4vw, 2.4rem);
	}
	.highlights {
		display: grid;
		grid-template-columns: 1.7fr 1fr;
		grid-auto-rows: 150px;
		gap: 12px;
	}
	.highlights.single {
		grid-template-columns: 1fr;
	}
	.highlight {
		position: relative;
		padding: 0;
		border: 0;
		overflow: hidden;
		background: #273c30;
		min-width: 0;
	}
	.hero {
		grid-row: span 2;
	}
	img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
	}
	.highlight img {
		transition: transform 450ms ease;
	}
	.highlight:hover img {
		transform: scale(1.035);
	}
	.photo-label {
		position: absolute;
		inset: auto 0 0;
		display: flex;
		justify-content: space-between;
		gap: 14px;
		color: #fff;
		padding: 40px 20px 18px;
		background: linear-gradient(transparent, #13251cbb);
		text-align: left;
	}
	.empty-preview {
		display: block;
		width: 100%;
		padding: 0;
		border: 0;
		background: transparent;
	}
	.empty-scene {
		position: relative;
		height: 250px;
		overflow: hidden;
		background: #e1e8d9;
		display: grid;
		place-items: center;
	}
	.empty-scene p {
		position: relative;
		z-index: 1;
		font-size: 0.75rem;
		padding: 10px 16px;
		background: #f7f3ebe8;
		color: var(--ink);
	}
	.landscape {
		position: absolute;
		inset: 0;
		background-image:
			linear-gradient(#ffffff26 1px, transparent 1px),
			linear-gradient(90deg, #ffffff26 1px, transparent 1px);
		background-size: 32px 32px;
	}
	.landscape span {
		position: absolute;
		width: 48px;
		height: 48px;
		background: #f0e4ad;
		right: 18%;
		top: 32px;
	}
	.landscape i,
	.landscape b {
		position: absolute;
		inset: 35% 0 0;
		background: #b7c9a7;
		clip-path: polygon(
			0 50%,
			15% 50%,
			15% 22%,
			32% 22%,
			32% 45%,
			54% 45%,
			54% 10%,
			76% 10%,
			76% 38%,
			100% 38%,
			100% 100%,
			0 100%
		);
	}
	.landscape b {
		inset: 60% 0 0;
		background: #839c77;
		transform: scaleX(-1);
	}
	.section-foot {
		margin-top: 12px;
		color: var(--muted);
		font-size: 0.6rem;
		line-height: 1.6;
	}
	dialog {
		width: min(1080px, calc(100% - 28px));
		max-width: none;
		max-height: 90dvh;
		padding: 0;
		border: 1px solid var(--line);
		border-radius: 8px;
		background: var(--paper);
		color: var(--ink);
		box-shadow: 0 24px 80px #0007;
	}
	dialog::backdrop {
		background: #18281ecc;
		backdrop-filter: blur(5px);
	}
	dialog[open] {
		animation: arrive 260ms ease-out;
	}
	.gallery-header {
		padding: 24px 28px;
		background: #e1e8d9;
		border-bottom: 1px solid #bdc9b4;
	}
	.close {
		background: transparent;
		flex-shrink: 0;
	}
	.gallery-body {
		padding: 24px 28px 28px;
	}
	.viewer {
		background: #202e26;
	}
	.full-photo {
		height: clamp(220px, 48dvh, 520px);
		animation: reveal 220ms ease-out;
	}
	img.large {
		object-fit: contain;
	}
	.viewer-info {
		padding: 20px 0;
		align-items: flex-start;
	}
	h3 {
		font-size: 0.95rem;
		margin: 0;
		overflow-wrap: anywhere;
	}
	.viewer-info p {
		font-size: 0.7rem;
		margin: 8px 0 0;
		color: var(--muted);
	}
	.navigation {
		gap: 12px;
		flex-shrink: 0;
		font-size: 0.7rem;
	}
	.navigation button {
		padding: 10px 14px;
	}
	.photo-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
		gap: 16px;
		border-top: 1px solid var(--line);
		padding-top: 20px;
	}
	.photo-grid button {
		background: transparent;
		border: 0;
		padding: 0 0 8px;
		text-align: left;
	}
	.photo-grid button.selected {
		box-shadow: 0 2px var(--green);
	}
	.thumbnail {
		display: block;
		aspect-ratio: 16 / 10;
		background: #e1e8d9;
		overflow: hidden;
	}
	.thumbnail-title {
		display: block;
		font-size: 0.65rem;
		margin-top: 10px;
		overflow-wrap: anywhere;
	}
	.unavailable {
		display: grid;
		place-items: center;
		height: 100%;
		min-height: 80px;
		padding: 16px;
		color: var(--muted);
		background: #e1e8d9;
		font-size: 0.75rem;
	}
	.empty-note {
		font-size: 0.75rem;
		line-height: 1.7;
		color: var(--muted);
		text-align: center;
	}
	@keyframes arrive {
		from {
			opacity: 0;
			transform: translateY(14px) scale(0.98);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	@keyframes reveal {
		from {
			opacity: 0.3;
		}
		to {
			opacity: 1;
		}
	}
	@media (max-width: 600px) {
		.intro,
		.viewer-info {
			align-items: flex-start;
			flex-direction: column;
			gap: 16px;
		}
		.highlights {
			grid-template-columns: 1fr 1fr;
			grid-auto-rows: 120px;
		}
		.hero {
			grid-column: 1 / -1;
			grid-row: span 2;
		}
		.highlights.single .hero {
			grid-column: auto;
		}
		.gallery-header,
		.gallery-body {
			padding: 20px 16px;
		}
		.photo-grid {
			grid-template-columns: repeat(2, minmax(0, 1fr));
			gap: 12px;
		}
		.navigation {
			width: 100%;
		}
		.section-foot {
			align-items: flex-start;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		dialog[open],
		.full-photo {
			animation: none;
		}
		.highlight img {
			transition: none;
		}
	}
</style>
