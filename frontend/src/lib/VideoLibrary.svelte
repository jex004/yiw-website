<script>
	import { dismissOnBackdrop } from '$lib/dismissOnBackdrop.js';
	/** @type {HTMLDialogElement} */
	let dialog;
	export function open() {
		dialog.showModal();
	}
	import videoData from '$lib/videos.json';
	import { dateFormat, timestamp } from '$lib/dates.js';
	let order = $state('newest');
	let failed = $state(/** @type {string[]} */ ([]));
	let videos = $derived(
		[...videoData].sort(
			(a, b) =>
				(order === 'oldest' ? 1 : -1) * a.publishedAt.localeCompare(b.publishedAt) ||
				a.title.localeCompare(b.title)
		)
	);
</script>

<dialog
	class="cinema"
	bind:this={dialog}
	use:dismissOnBackdrop={() => dialog.close()}
	aria-labelledby="cinema-title"
>
	<header class="marquee">
		<div>
			<p>YIW / PICTURE HOUSE</p>
			<h2 id="cinema-title">Pure Cinema</h2>
		</div>
		<button class="close" onclick={() => dialog.close()} aria-label="Close video collection"
			>Close &times;</button
		>
	</header>
	<div class="cinema-content">
		<div class="section-heading">
			<div>
				<h3>All videos</h3>
				<p class="count">
					{videos.length}
					{videos.length === 1 ? 'video' : 'videos'} / opens on YouTube
				</p>
			</div>
			<label for="video-order"
				>Sort by
				<select id="video-order" bind:value={order}>
					<option value="newest">Newest first</option>
					<option value="oldest">Oldest first</option>
				</select>
			</label>
		</div>
		<ul class="video-library">
			{#each videos as video, index (video.id)}
				<li>
					<!-- eslint-disable svelte/no-navigation-without-resolve -- Public YouTube video. -->
					<a
						href={`https://www.youtube.com/watch?v=${video.id}`}
						target="_blank"
						rel="noopener noreferrer"
						aria-label={`Watch ${video.title} on YouTube (opens in a new tab)`}
					>
						<div class="thumbnail">
							{#if !failed.includes(video.id)}
								<img
									src={video.thumbnail || `https://i.ytimg.com/vi/${video.id}/hqdefault.jpg`}
									alt=""
									loading="lazy"
									onerror={() => (failed = [...failed, video.id])}
								/>
							{:else}<span class="image-fallback">Preview unavailable</span>{/if}
							<span class="watch">Watch &nearr;</span>
						</div>
						<div class="video-info">
							<span class="catalog-number">{String(index + 1).padStart(2, '0')}</span>
							<div>
								<time datetime={video.publishedAt}
									>{dateFormat.format(timestamp(video.publishedAt))}</time
								>
								<h3>{video.title}</h3>
								<p>{video.creator}</p>
							</div>
						</div>
					</a>
				</li>
			{/each}
		</ul>
		{#if !videos.length}<p>No videos added yet.</p>{/if}
	</div>
</dialog>

<style>
	.cinema {
		width: min(960px, calc(100% - 28px));
		max-width: none;
		max-height: 88dvh;
		padding: 0;
		color: #f7f3eb;
		background: #202a24;
		border: 1px solid #c6b77b;
		border-radius: 14px;
		box-shadow: 0 24px 80px #0008;
	}
	.cinema::backdrop {
		background: #101b19bd;
		backdrop-filter: blur(3px);
	}
	.cinema[open] {
		animation: cinema-enter 220ms ease-out;
	}
	.marquee {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		padding: 28px;
		border-bottom: 1px solid #8a805b;
		background:
			radial-gradient(circle, #e5d59a 2px, transparent 3px) 8px 6px / 24px 12px repeat-x,
			radial-gradient(circle, #e5d59a 2px, transparent 3px) 8px calc(100% - 6px) / 24px 12px
				repeat-x,
			#303d31;
	}
	.marquee p {
		font-size: 0.6rem;
		letter-spacing: 0.15em;
		color: #dcca91;
		margin: 0 0 6px;
	}
	.marquee h2 {
		font-size: clamp(1.5rem, 5vw, 2.2rem);
		letter-spacing: 0.06em;
		margin: 0;
	}
	.close {
		background: transparent;
		border-color: #c6b77b;
		color: #f7f3eb;
		flex-shrink: 0;
	}
	.close:hover {
		background: #4b5844;
	}
	.cinema-content {
		padding: 0 24px 28px;
	}
	select {
		background: #303d31;
		color: #f7f3eb;
		border-color: #8a977c;
	}
	.cinema :global(:focus-visible) {
		outline-color: #e5d59a;
	}
	@keyframes cinema-enter {
		from {
			opacity: 0;
			transform: translateY(14px) scale(0.97);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.cinema[open] {
			animation: none;
		}
	}
	@media (max-width: 500px) {
		.marquee {
			padding: 24px 16px;
		}
		.cinema-content {
			padding: 0 16px 20px;
		}
	}

	.section-heading {
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 16px;
		margin: 24px 0 16px;
	}
	.section-heading h3 {
		margin: 0;
	}
	.count {
		color: #b9bfac;
		font-size: 0.75rem;
	}
	label {
		display: flex;
		align-items: center;
		gap: 10px;
		font-size: 0.7rem;
	}
	.video-library {
		list-style: none;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 250px), 1fr));
		gap: 24px;
		margin: 0;
	}
	.video-library li {
		min-width: 0;
		border: 1px solid #66745e;
		background: #2b352d;
		box-shadow: 3px 3px 0 #111b16;
		border-radius: 6px;
	}
	.video-library a {
		display: block;
		height: 100%;
		color: #f7f3eb;
		text-decoration: none;
	}
	.thumbnail {
		position: relative;
		aspect-ratio: 16 / 9;
		background: #dce8ce;
		margin: 0;
		overflow: hidden;
	}
	.thumbnail img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
		transition: transform 200ms;
	}
	.video-library a:hover img {
		transform: scale(1.04);
	}
	.watch {
		position: absolute;
		bottom: 8px;
		right: 8px;
		padding: 6px 8px;
		color: var(--paper);
		background: #303d31eb;
		font-size: 0.65rem;
	}
	.image-fallback {
		display: grid;
		place-items: center;
		height: 100%;
		font-size: 0.75rem;
	}
	.video-info {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 12px;
		padding: 14px;
	}
	.catalog-number {
		color: #dcca91;
		font-size: 1.5rem;
		border-right: 1px dashed #66745e;
		padding-right: 12px;
	}
	time,
	.video-info p {
		color: #b9bfac;
		font-size: 0.65rem;
	}
	.video-info h3 {
		font-size: 1.1rem;
		line-height: 1.3;
		margin: 8px 0;
		overflow-wrap: anywhere;
	}
	.video-info p {
		margin: 0 0 10px;
	}
	@media (prefers-reduced-motion: reduce) {
		.thumbnail img {
			transition: none;
		}
		.video-library a:hover img {
			transform: none;
		}
	}
</style>
