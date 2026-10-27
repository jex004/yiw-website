<script>
	/** @type {{moving: boolean, progress: number, reversed?: boolean}} */
	let { moving, progress, reversed = false } = $props();
	let currentFrame = $state(1);
	$effect(() => {
		if (!moving) return;
		const step = reversed ? -1 : 1;
		const timer = setInterval(() => {
			currentFrame = ((currentFrame - 1 + step + 6) % 6) + 1;
		}, 200);
		return () => clearInterval(timer);
	});
</script>

<div class="trolley-scene">
	<div
		class="trolley"
		role="img"
		aria-label="Pixel-art YIW trolley"
		style:left={`${progress * 100}%`}
		style:transform={`translateX(${-progress * 100}%)`}
	>
		{#each [1, 2, 3, 4, 5, 6] as frame (frame)}
			<img
				class:active={frame === currentFrame}
				src={`/timeline-animation/trolley-${frame}.png`}
				alt=""
				width="192"
				height="128"
				draggable="false"
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
	}
	img.active {
		opacity: 1;
	}
	@media (prefers-reduced-motion: reduce) {
		img.active {
			opacity: 0;
		}
		img:first-child {
			opacity: 1;
		}
	}
</style>
