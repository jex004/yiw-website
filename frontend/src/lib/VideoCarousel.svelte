<script>
	import { onDestroy } from 'svelte';
	/** @type {{videos: import('$lib/videos.js').Video[]}} */
	let { videos } = $props();
	let selected = $state(0);
	let rotation = $state(0);
	let width = $state(800);
	let frame = 0;
	let target = 0;
	let failed = $state(/** @type {string[]} */ ([]));
	let cardWidth = $derived(Math.min(360, width * 0.68));
	let spread = $derived(Math.min(290, width * 0.32));
	const mod = (/** @type {number} */ n) => (n + videos.length) % videos.length;
	/** @param {number} step */
	function turn(step) {
		if (videos.length < 2) return;
		cancelAnimationFrame(frame);
		target += step;
		selected = mod(selected + step);
		const from = rotation;
		if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
			rotation = target;
			return;
		}
		const start = performance.now();
		const animate = (/** @type {number} */ now) => {
			const progress = Math.min(1, (now - start) / 600);
			rotation = from + (target - from) * (1 - (1 - progress) ** 3);
			if (progress < 1) frame = requestAnimationFrame(animate);
		};
		frame = requestAnimationFrame(animate);
	}
	/** @param {number} index */
	function bringForward(index) {
		let step = mod(index - selected);
		if (step > videos.length / 2) step -= videos.length;
		turn(step);
	}
	onDestroy(() => cancelAnimationFrame(frame));
</script>

<section class="carousel" aria-label="Featured videos" aria-roledescription="carousel">
	<div class="stage" bind:clientWidth={width} style:height={`${cardWidth * 0.5625 + 72}px`}>
		{#each videos as video, index (video.id)}
			{@const angle = ((index - rotation) * Math.PI * 2) / videos.length}
			{@const depth = Math.cos(angle)}
			<!-- eslint-disable svelte/no-navigation-without-resolve -- Public YouTube video. -->
			<a
				class="video-slide"
				class:front={index === selected}
				href={video.url}
				target="_blank"
				rel="noopener noreferrer"
				aria-label={index === selected
					? `Watch ${video.title} on YouTube (opens in a new tab)`
					: `Bring ${video.title} to the front`}
				style:width={`${cardWidth}px`}
				style:transform={`translate(-50%, -50%) translateX(${Math.sin(angle) * spread}px) translateZ(${(depth - 1) * 180}px) rotateY(${-Math.sin(angle) * 32}deg)`}
				style:filter={`brightness(${0.65 + (depth + 1) * 0.175})`}
				style:z-index={Math.round((depth + 1) * 100)}
				onclick={(event) => {
					if (index !== selected) {
						event.preventDefault();
						bringForward(index);
					}
				}}
			>
				{#if !failed.includes(video.id)}
					<img
						src={video.thumbnail}
						alt={video.title}
						onerror={() => (failed = [...failed, video.id])}
						draggable="false"
					/>
				{:else}<span class="fallback">{video.title}</span>{/if}
				<span class="play" aria-hidden="true">▶</span>
			</a>
		{/each}
	</div>
	<div class="carousel-controls">
		<button onclick={() => turn(-1)} disabled={videos.length < 2} aria-label="Previous video"
			>&larr;</button
		>
		<div class="current" aria-live="polite" aria-atomic="true">
			<span>{String(selected + 1).padStart(2, '0')} / {String(videos.length).padStart(2, '0')}</span
			>
			<h3>{videos[selected]?.title}</h3>
			<p>{videos[selected]?.creator}</p>
		</div>
		<button onclick={() => turn(1)} disabled={videos.length < 2} aria-label="Next video"
			>&rarr;</button
		>
	</div>
</section>

<style>
	.carousel {
		overflow: hidden;
		border: 1px solid var(--line);
		background: #e7ecdf99;
	}
	.stage {
		position: relative;
		perspective: 1100px;
		margin: 16px 0 0;
	}
	.video-slide {
		position: absolute;
		left: 50%;
		top: 50%;
		aspect-ratio: 16 / 9;
		border-radius: 10px;
		overflow: hidden;
		background: #dce8ce;
		box-shadow: 0 12px 24px #303d3126;
		text-decoration: none;
	}
	.video-slide img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
	}
	.fallback {
		display: grid;
		place-items: center;
		height: 100%;
		padding: 20px;
		background: #dce8ce;
		font-size: 0.8rem;
		text-align: center;
	}
	.play {
		position: absolute;
		left: 50%;
		top: 50%;
		transform: translate(-50%, -50%);
		width: 44px;
		height: 44px;
		display: grid;
		place-items: center;
		background: #f7f3ebe8;
		color: var(--green);
		border: 1px solid var(--green);
		border-radius: 50%;
	}
	.video-slide:not(.front) .play {
		visibility: hidden;
	}
	.front:hover .play {
		background: var(--green-light);
	}
	.carousel-controls {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 16px;
		padding: 0 18px;
	}
	.carousel-controls button {
		min-width: 44px;
		min-height: 44px;
		padding: 8px;
		flex-shrink: 0;
	}
	.current {
		width: 440px;
		min-width: 0;
		text-align: center;
	}
	.current span,
	.current p {
		font-size: 0.65rem;
		color: var(--muted);
	}
	.current h3 {
		font-size: clamp(1rem, 3vw, 1.3rem);
		margin: 8px 0;
		min-height: 2.6em;
	}
	.current p {
		margin: 0 0 16px;
	}
</style>
