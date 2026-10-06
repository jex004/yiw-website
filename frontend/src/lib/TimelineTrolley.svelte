<script>
	/** @type {{moving: boolean, progress: number}} */
	let { moving, progress } = $props();
</script>

<div class="trolley-scene" class:moving>
	<div
		class="trolley"
		role="img"
		aria-label="Pixel-art YIW trolley"
		style:left={`${progress * 100}%`}
		style:transform={`translateX(${-progress * 100}%)`}
	>
		{#each [1, 2, 3, 4, 5, 6] as frame (frame)}
			<img
				src={`/timeline-animation/trolley-${frame}.png`}
				alt=""
				width="192"
				height="128"
				draggable="false"
				style:animation-delay={`${(frame - 1) * 200}ms`}
			/>
		{/each}
	</div>
</div>

<style>
	.trolley-scene {
		position: sticky;
		left: 0;
		width: 100%;
		padding-top: 96px;
		pointer-events: none;
		border-bottom: 1px solid var(--line);
	}
	.trolley {
		position: relative;
		width: min(192px, 100%);
		height: 128px;
		flex-shrink: 0;
	}
	img {
		position: absolute;
		inset: 0;
		image-rendering: pixelated;
		width: 100%;
		object-fit: contain;
		opacity: 0;
		animation: trolley-frame 1200ms step-end infinite;
		animation-play-state: paused;
	}
	.moving img {
		animation-play-state: running;
	}
	@keyframes trolley-frame {
		0% {
			opacity: 1;
		}
		16.666667%,
		100% {
			opacity: 0;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		img {
			animation: none;
		}
		img:first-child {
			opacity: 1;
		}
	}
</style>
