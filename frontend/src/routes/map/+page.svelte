<script>
	import { onMount } from 'svelte';
	import { geoEqualEarth, geoPath } from 'd3-geo';
	import { feature } from 'topojson-client';

	/** @typedef {{code: string, name: string, coords: [number, number], count: number}} Country */
	/** @type {any[]} */
	let countries = $state([]);
	/** @type {Country[]} */
	let locations = $state([]);
	let loading = $state(true);
	let error = $state('');
	let selected = $state('');
	/** @type {Country | null} */
	let hovered = $state(null);
	let tooltipX = $state(0);
	let tooltipY = $state(0);
	let tooltipWidth = $state(220);
	let tooltipBelow = $state(false);

	function hideTooltip() {
		hovered = null;
	}

	/** @param {Event} event @param {Country} country */
	function showTooltip(event, country) {
		if (dragging) return;
		const dot = /** @type {SVGCircleElement} */ (event.currentTarget);
		const container = dot.closest('.map');
		if (!container) return;
		const bounds = container.getBoundingClientRect();
		const rect = dot.getBoundingClientRect();
		tooltipWidth = Math.min(220, bounds.width - 16);
		tooltipX = Math.max(
			8,
			Math.min(
				bounds.width - tooltipWidth - 8,
				rect.left + rect.width / 2 - bounds.left - tooltipWidth / 2
			)
		);
		tooltipBelow = rect.top - bounds.top < 110;
		tooltipY = tooltipBelow ? rect.bottom - bounds.top + 12 : rect.top - bounds.top - 12;
		hovered = country;
	}

	/** @param {KeyboardEvent} event @param {Country} country */
	function dotKey(event, country) {
		if (event.key === 'Escape') {
			hideTooltip();
			event.stopPropagation();
		}
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			showTooltip(event, country);
		}
	}
	const projection = geoEqualEarth().fitExtent(
		[
			[20, 20],
			[940, 490]
		],
		{ type: 'Sphere' }
	);
	const path = geoPath(projection);
	let maximum = $derived(Math.max(1, ...locations.map((d) => d.count)));
	let total = $derived(locations.reduce((sum, d) => sum + d.count, 0));
	// A common multiplier keeps circle area proportional to member count.
	let unitRadius = $derived(Math.min(7, 36 / Math.sqrt(maximum)));

	/** @param {string} url */
	async function get(url) {
		const res = await fetch(url, {
			credentials: url.startsWith('/api/') ? 'include' : 'omit'
		});
		if (!res.ok) throw new Error('Could not load the map. Please try again.');
		return res.json();
	}

	async function load() {
		loading = true;
		error = '';
		try {
			const [world, data] = await Promise.all([
				get('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'),
				get('/api/locations')
			]);
			countries = /** @type {any} */ (feature(world, world.objects.countries)).features;
			locations = data;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Could not load the map.';
		} finally {
			loading = false;
		}
	}

	let zoom = $state(1);
	let offsetX = $state(0);
	let offsetY = $state(0);
	let dragging = $state(false);

	/** @param {number} scale @param {number} x @param {number} y */
	function setView(scale, x, y) {
		hideTooltip();
		zoom = Math.max(1, Math.min(8, scale));
		offsetX = Math.max(960 * (1 - zoom), Math.min(0, x));
		offsetY = Math.max(510 * (1 - zoom), Math.min(0, y));
	}

	/** @param {number} factor @param {number} [x] @param {number} [y] */
	function zoomBy(factor, x = 480, y = 255) {
		const next = Math.max(1, Math.min(8, zoom * factor));
		setView(next, x - ((x - offsetX) * next) / zoom, y - ((y - offsetY) * next) / zoom);
	}

	function resetView() {
		setView(1, 0, 0);
		selected = '';
	}

	/** @param {Country} country */
	function visit(country) {
		selected = country.code;
		const point = projection(country.coords);
		if (point) setView(3, 480 - point[0] * 3, 255 - point[1] * 3);
	}

	/** @param {KeyboardEvent} event */
	function keyboard(event) {
		if (event.target !== event.currentTarget) return;
		switch (event.key) {
			case '+':
			case '=':
				zoomBy(1.4);
				break;
			case '-':
				zoomBy(1 / 1.4);
				break;
			case '0':
			case 'Home':
				resetView();
				break;
			case 'ArrowLeft':
				setView(zoom, offsetX + 60, offsetY);
				break;
			case 'ArrowRight':
				setView(zoom, offsetX - 60, offsetY);
				break;
			case 'ArrowUp':
				setView(zoom, offsetX, offsetY + 60);
				break;
			case 'ArrowDown':
				setView(zoom, offsetX, offsetY - 60);
				break;
			default:
				return;
		}
		event.preventDefault();
	}

	/** @param {SVGSVGElement} node */
	function explore(node) {
		/** @type {Map<number, {x: number, y: number}>} */
		// eslint-disable-next-line svelte/prefer-svelte-reactivity -- Pointer tracking does not render UI.
		const pointers = new Map();
		/** @param {MouseEvent} event */
		function point(event) {
			const matrix = node.getScreenCTM();
			return matrix
				? new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse())
				: new DOMPoint();
		}
		function gesture() {
			const values = [...pointers.values()];
			const a = values[0];
			const b = values[1] ?? a;
			return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, distance: Math.hypot(a.x - b.x, a.y - b.y) };
		}
		/** @param {PointerEvent} event */
		function down(event) {
			if (event.button !== 0) return;
			pointers.set(event.pointerId, point(event));
			node.setPointerCapture(event.pointerId);
			dragging = true;
			hideTooltip();
		}
		/** @param {PointerEvent} event */
		function move(event) {
			if (!pointers.has(event.pointerId)) return;
			const before = gesture();
			pointers.set(event.pointerId, point(event));
			const after = gesture();
			const ratio = before.distance > 0 ? after.distance / before.distance : 1;
			const next = Math.max(1, Math.min(8, zoom * ratio));
			setView(
				next,
				after.x - ((before.x - offsetX) * next) / zoom,
				after.y - ((before.y - offsetY) * next) / zoom
			);
		}
		/** @param {PointerEvent} event */
		function up(event) {
			pointers.delete(event.pointerId);
			dragging = pointers.size > 0;
		}
		/** @param {WheelEvent} event */
		function wheel(event) {
			event.preventDefault();
			const anchor = point(event);
			const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 510 : 1);
			zoomBy(Math.exp(-Math.max(-300, Math.min(300, delta)) * 0.002), anchor.x, anchor.y);
		}
		node.addEventListener('pointerdown', down);
		node.addEventListener('pointermove', move);
		node.addEventListener('pointerup', up);
		node.addEventListener('pointercancel', up);
		node.addEventListener('lostpointercapture', up);
		node.addEventListener('wheel', wheel, { passive: false });
		return {
			destroy() {
				node.removeEventListener('pointerdown', down);
				node.removeEventListener('pointermove', move);
				node.removeEventListener('pointerup', up);
				node.removeEventListener('pointercancel', up);
				node.removeEventListener('lostpointercapture', up);
				node.removeEventListener('wheel', wheel);
				pointers.clear();
			}
		};
	}

	onMount(() => {
		void load();
		window.addEventListener('resize', hideTooltip);
		/** @param {KeyboardEvent} event */
		const dismiss = (event) => {
			if (event.key === 'Escape') hideTooltip();
		};
		window.addEventListener('keydown', dismiss);
		return () => {
			window.removeEventListener('resize', hideTooltip);
			window.removeEventListener('keydown', dismiss);
		};
	});
</script>

<main>
	<header class="page-heading">
		<div>
			<p class="section-number">04 / Map</p>
			<h1>Member map</h1>
			<p>Where people in the server are from.</p>
		</div>
	</header>
	{#if loading}
		<p role="status">Loading map...</p>
	{:else if error}
		<p role="alert">{error}</p>
		<button onclick={load}>Try again</button>
	{:else}
		<div class="postcard">
			<div class="map-top">
				<span>{total} members · {locations.length} countries</span>
			</div>
			<!-- The map is a keyboard-controlled application with its own pan and zoom shortcuts. -->
			<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
			<div
				role="application"
				class="map"
				class:dragging
				tabindex="0"
				aria-label="Explore the map. Use plus and minus to zoom, arrow keys to move, and zero to reset."
				onkeydown={keyboard}
			>
				<svg
					use:explore
					viewBox="0 0 960 510"
					role="group"
					aria-labelledby="map-title map-description"
				>
					<title id="map-title">Member countries</title>
					<desc id="map-description"
						>Bigger dots mean more members from that country. Drag to explore, scroll or pinch to
						zoom. Country buttons are below.</desc
					>
					<g transform={`translate(${offsetX}, ${offsetY}) scale(${zoom})`}>
						<path d={path({ type: 'Sphere' })} fill="#edf0e6" />
						<g fill="#bac9a4" stroke="#f7f3eb" stroke-width="0.7">
							{#each countries as shape (shape.id)}<path d={path(shape)} />{/each}
						</g>
						{#each [...locations].sort((a, b) => b.count - a.count) as location (location.code)}
							{@const point = projection(location.coords)}
							{#if point}
								{#if hovered?.code === location.code}
									<circle
										class="dot-halo"
										cx={point[0]}
										cy={point[1]}
										r={(Math.sqrt(location.count) * unitRadius) / Math.sqrt(zoom) + 5 / zoom}
										fill="none"
										stroke="#416d48"
										stroke-opacity="0.5"
										stroke-width={2 / zoom}
										pointer-events="none"
										aria-hidden="true"
									/>
								{/if}
								<circle
									class="member-dot"
									class:highlighted={hovered?.code === location.code}
									data-country={location.code}
									role="button"
									tabindex="0"
									aria-label={`${location.name}: ${location.count} ${location.count === 1 ? 'member' : 'members'}`}
									aria-describedby={hovered?.code === location.code ? 'country-tooltip' : undefined}
									onpointerenter={(event) => showTooltip(event, location)}
									onpointerleave={hideTooltip}
									onfocus={(event) => showTooltip(event, location)}
									onblur={hideTooltip}
									onclick={(event) => showTooltip(event, location)}
									onkeydown={(event) => dotKey(event, location)}
									cx={point[0]}
									cy={point[1]}
									r={(Math.sqrt(location.count) * unitRadius) / Math.sqrt(zoom)}
									fill={hovered?.code === location.code
										? '#284d30'
										: selected === location.code
											? '#c16342'
											: '#416d48'}
									fill-opacity={hovered?.code === location.code ? 1 : 0.85}
									stroke="#faf7ed"
									stroke-width={(hovered?.code === location.code ? 2.5 : 1.5) / zoom}
								/>
							{/if}
						{/each}
					</g>
				</svg>
				{#if hovered}
					<div
						id="country-tooltip"
						role="tooltip"
						class="country-tooltip"
						class:below={tooltipBelow}
						style:left={`${tooltipX}px`}
						style:top={`${tooltipY}px`}
						style:width={`${tooltipWidth}px`}
					>
						<strong>{hovered.name}</strong>
						<span><b>{hovered.count}</b> {hovered.count === 1 ? 'member' : 'members'}</span>
					</div>
				{/if}
				<div class="map-controls" aria-label="Map controls">
					<button aria-label="Zoom in" onclick={() => zoomBy(1.4)} disabled={zoom >= 8}>+</button>
					<button aria-label="Zoom out" onclick={() => zoomBy(1 / 1.4)} disabled={zoom <= 1}
						>−</button
					>
					<button class="reset" onclick={resetView}>Reset view</button>
				</div>
			</div>
			<div class="map-bottom">
				<span>Drag around · Scroll or pinch to zoom</span><span>Bigger dots = more members</span>
			</div>
		</div>
		{#if locations.length === 0}
			<p class="empty">No countries have been added yet.</p>
		{:else}
			<h2>Countries</h2>
			<p class="hint">Select a country to zoom in.</p>
			<div class="country-list">
				{#each locations as location (location.code)}
					<button
						class:active={selected === location.code}
						aria-pressed={selected === location.code}
						onclick={() => visit(location)}
					>
						<span>{location.name}</span><strong>{location.count}</strong>
					</button>
				{/each}
			</div>
		{/if}
		<p class="note">
			Country locations only. Some members may not be added yet.<br />Map: Natural Earth /
			world-atlas.
		</p>
	{/if}
</main>

<style>
	.member-dot {
		cursor: pointer;
		transition:
			fill 120ms,
			fill-opacity 120ms;
		outline: none;
	}
	.country-tooltip {
		position: absolute;
		z-index: 2;
		pointer-events: none;
		transform: translateY(-100%);
		padding: 12px 14px;
		border: 1px solid var(--green);
		border-top: 3px solid var(--green);
		background: var(--paper);
		color: var(--ink);
		box-shadow: 3px 4px 0 #416d4820;
	}
	.country-tooltip.below {
		transform: none;
	}
	.country-tooltip strong {
		display: block;
		font-size: 0.85rem;
		line-height: 1.35;
		overflow-wrap: anywhere;
	}
	.country-tooltip span {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-top: 8px;
		font-size: 0.7rem;
		color: var(--muted);
	}
	.country-tooltip b {
		background: #dce8ce;
		padding: 3px 7px;
		color: var(--green);
		font-size: 0.8rem;
	}
	@media (prefers-reduced-motion: reduce) {
		.member-dot {
			transition: none;
		}
	}

	.postcard {
		border: 1px solid var(--line);
		background: #f7f3ebde;
	}
	.map-top,
	.map-bottom {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: 8px;
		padding: 12px 16px;
		color: var(--green);
		font-size: 0.7rem;
	}
	.map-top {
		border-bottom: 1px solid var(--line);
		text-transform: uppercase;
	}
	.map-bottom {
		border-top: 1px solid var(--line);
	}
	.map {
		position: relative;
		background: #edf0e6;
		overflow: hidden;
	}
	.map:focus-visible {
		outline: 3px solid var(--green);
		outline-offset: -3px;
	}
	svg {
		display: block;
		width: 100%;
		height: auto;
		min-height: 280px;
		touch-action: none;
		cursor: grab;
		user-select: none;
	}
	.dragging svg {
		cursor: grabbing;
	}
	.map-controls {
		position: absolute;
		bottom: 12px;
		right: 12px;
		display: flex;
		gap: 6px;
	}
	.map-controls button {
		background: var(--paper);
		width: 36px;
		height: 36px;
		padding: 0;
		font-size: 1.2rem;
	}
	.map-controls button:hover {
		background: var(--green-light);
	}
	.map-controls .reset {
		width: auto;
		padding: 0 12px;
		font-size: 0.7rem;
	}
	h2 {
		margin: 28px 0 6px;
	}
	.hint {
		margin: 0 0 16px;
		font-size: 0.75rem;
		color: var(--muted);
	}
	.country-list {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
	}
	.country-list button {
		display: flex;
		align-items: center;
		gap: 16px;
		background: #f7f3ebdc;
		text-align: left;
		padding: 10px 12px;
	}
	.country-list button:hover,
	.country-list button.active {
		background: var(--green-light);
	}
	.country-list strong {
		font-size: 0.75rem;
		border-left: 1px solid var(--line);
		padding-left: 12px;
	}
	.note {
		margin-top: 28px;
		font-size: 0.65rem;
		color: var(--muted);
		line-height: 1.8;
	}
	.empty {
		text-align: center;
		padding: 16px;
		font-size: 0.8rem;
	}
	@media (max-width: 650px) {
		.map-top,
		.map-bottom {
			padding: 10px;
			font-size: 0.6rem;
		}
	}
</style>
