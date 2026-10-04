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
		<h2 id="cinema-title">All videos</h2>
		<button class="close" onclick={() => dialog.close()} aria-label="Close video collection"
			>Close &times;</button
		>
	</header>
	<div class="cinema-content">
		<div class="section-heading">
			<div>
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
			{#each videos as video (video.id)}
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
		color: var(--ink);
		background: var(--paper);
		border: 1px solid var(--line);
		border-radius: 10px;
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
		position: relative;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		padding: 32px 28px 24px;
		background: #e5e1eb;
		border-bottom: 1px dashed #9890a3;
	}
	.marquee::before {
		content: '';
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 12px;
		background: repeating-linear-gradient(90deg, #4e5550 0 12px, #e5e1eb 12px 22px);
		border-block: 3px solid #4e5550;
	}
	.marquee h2 {
		font-size: 1.4rem;
		margin: 0;
	}
	.close {
		background: transparent;
		border-color: var(--line);
		color: var(--ink);
		flex-shrink: 0;
	}
	.close:hover {
		background: var(--green-light);
	}
	.cinema-content {
		padding: 0 24px 28px;
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
	.count {
		color: var(--muted);
		font-size: 0.75rem;
		padding: 6px 10px;
		border-left: 3px solid #b8aac7;
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
	}
	.video-library a {
		display: block;
		height: 100%;
		color: var(--ink);
		text-decoration: none;
	}
	.thumbnail {
		position: relative;
		aspect-ratio: 16 / 9;
		background: #dce8ce;
		margin: 0;
		border-radius: 8px;
		box-shadow: 0 5px 14px #303d3118;
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
		padding: 14px 2px;
	}
	time,
	.video-info p {
		color: var(--muted);
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
