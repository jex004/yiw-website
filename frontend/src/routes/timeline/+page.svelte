<script>
	import { onMount, tick } from 'svelte';
	import { day, dateFormat, timestamp } from '$lib/dates.js';
	/** @typedef {{id: string, date: string, title: string, summary: string, description: string, images: {url: string, alt: string}[]}} ServerEvent */
	/** @type {ServerEvent[]} */
	let events = $state([]);
	let loading = $state(true);
	let error = $state('');
	let zoom = $state(1);
	let width = $state(800);
	let dragging = $state(false);
	let visibleCount = $state(12);
	/** @type {HTMLDivElement | undefined} */
	let viewport = $state();
	/** @type {HTMLDialogElement} */
	let dialog;
	/** @type {ServerEvent | null} */
	let selected = $state(null);
	/** @type {ServerEvent[]} */
	let group = $state([]);
	/** @param {string} value */
	const dateLabel = (value) => dateFormat.format(timestamp(value));
	let chronological = $derived([...events].reverse());
	let first = $derived(events.length ? timestamp(chronological[0].date) : 0);
	let last = $derived(
		events.length ? timestamp(chronological[chronological.length - 1].date) : day
	);
	let padding = $derived(Math.max((last - first) * 0.08, day * 7));
	let start = $derived(first - padding);
	let span = $derived(Math.max(day, last - first + padding * 2));
	let trackWidth = $derived(Math.max(width, 320) * zoom);
	/** @param {string} value */
	const position = (value) => ((timestamp(value) - start) / span) * trackWidth;
	let markers = $derived.by(() => {
		/** @type {{x: number, events: ServerEvent[]}[]} */
		const result = [];
		for (const event of chronological) {
			const x = position(event.date);
			const previous = result[result.length - 1];
			if (previous && x - previous.x < 170) previous.events.push(event);
			else result.push({ x, events: [event] });
		}
		return result;
	});
	let ticks = $derived(
		Array.from({ length: Math.ceil(trackWidth / 180) + 1 }, (_, i) => {
			const fraction = i / Math.ceil(trackWidth / 180);
			return { x: fraction * (trackWidth - 1), label: dateFormat.format(start + span * fraction) };
		})
	);
	let selectedIndex = $derived(
		selected ? events.findIndex((event) => event.id === selected?.id) : -1
	);

	async function load() {
		loading = true;
		error = '';
		try {
			const response = await fetch('/api/events');
			if (!response.ok) throw new Error('Could not load the events. Please try again.');
			const data = await response.json();
			events = data.events;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Could not load events.';
		} finally {
			loading = false;
		}
	}
	/** @param {ServerEvent} event */
	function openEvent(event) {
		selected = event;
		group = [];
		if (!dialog.open) dialog.showModal();
		dialog.scrollTop = 0;
	}
	/** @param {ServerEvent[]} items */
	function openMarker(items) {
		if (items.length === 1) return openEvent(items[0]);
		selected = null;
		group = items;
		dialog.showModal();
	}
	/** @param {number} next @param {number} [anchor] */
	async function setZoom(next, anchor = width / 2) {
		if (!viewport) return;
		const ratio = (viewport.scrollLeft + anchor) / trackWidth;
		zoom = Math.max(1, Math.min(16, next));
		await tick();
		viewport.scrollLeft = ratio * trackWidth - anchor;
	}
	async function resetView() {
		zoom = 1;
		await tick();
		if (viewport) viewport.scrollLeft = 0;
	}
	/** @param {HTMLDivElement} node */
	function draggable(node) {
		let active = false,
			origin = 0,
			initialScroll = 0;
		/** @param {PointerEvent} event */
		const down = (event) => {
			if (
				event.pointerType !== 'mouse' ||
				event.button !== 0 ||
				/** @type {Element} */ (event.target).closest('button')
			)
				return;
			active = true;
			dragging = true;
			origin = event.clientX;
			initialScroll = node.scrollLeft;
			node.setPointerCapture(event.pointerId);
		};
		/** @param {PointerEvent} event */
		const move = (event) => {
			if (active) node.scrollLeft = initialScroll + origin - event.clientX;
		};
		const up = () => {
			active = false;
			dragging = false;
		};
		/** @param {WheelEvent} event */
		const wheel = (event) => {
			if (!event.ctrlKey && !event.metaKey) return;
			event.preventDefault();
			void setZoom(
				zoom * Math.exp(-event.deltaY * 0.005),
				event.clientX - node.getBoundingClientRect().left
			);
		};
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
			}
		};
	}
	/** @param {KeyboardEvent} event */
	function keyboard(event) {
		if (event.target !== event.currentTarget) return;
		if (event.key === '+' || event.key === '=') {
			event.preventDefault();
			void setZoom(zoom * 1.5);
		}
		if (event.key === '-') {
			event.preventDefault();
			void setZoom(zoom / 1.5);
		}
		if (event.key === 'Home') {
			event.preventDefault();
			void resetView();
		}
	}
	onMount(() => {
		void load();
	});
</script>

<main>
	<header class="page-heading">
		<div>
			<p class="section-number">03 / Timeline</p>
			<h1>Server history</h1>
			<p>Events, milestones, and other things worth keeping.</p>
		</div>
	</header>
	{#if loading}<p role="status">Loading events...</p>
	{:else if error}<p role="alert">{error}</p>
		<button onclick={load}>Try again</button>
	{:else}
		<section class="timeline-panel" aria-labelledby="timeline-heading">
			<div class="panel-heading">
				<h2 id="timeline-heading">Timeline</h2>
				<div class="controls" aria-label="Timeline controls">
					<button
						aria-label="Zoom out timeline"
						disabled={!events.length || zoom <= 1}
						onclick={() => setZoom(zoom / 1.5)}>&minus;</button
					>
					<span>{zoom.toFixed(1)}&times;</span>
					<button
						aria-label="Zoom in timeline"
						disabled={!events.length || zoom >= 16}
						onclick={() => setZoom(zoom * 1.5)}>+</button
					>
					<button disabled={!events.length} onclick={resetView}>Reset</button>
				</div>
			</div>
			{#if events.length}
				<!-- The focusable scroll region supports native arrow-key scrolling plus zoom shortcuts. -->
				<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
				<div
					class="timeline-viewport"
					class:dragging
					bind:this={viewport}
					bind:clientWidth={width}
					use:draggable
					tabindex="0"
					role="region"
					aria-label="Event timeline. Scroll or drag horizontally. Plus and minus zoom; Home resets."
					onkeydown={keyboard}
				>
					<div class="timeline-track" style:width={`${trackWidth}px`}>
						<div class="axis"></div>
						{#each ticks as mark (mark)}<div
								class="tick"
								class:last={mark === ticks[ticks.length - 1]}
								style:left={`${mark.x}px`}
							>
								<span>{mark.label}</span>
							</div>{/each}
						{#each markers as marker, i (marker)}
							<button
								class="event-marker"
								class:lower={i % 2 === 1}
								style:left={`${marker.x}px`}
								aria-label={marker.events.length === 1
									? `${marker.events[0].title}, ${dateLabel(marker.events[0].date)}`
									: `${marker.events.length} nearby events, starting ${dateLabel(marker.events[0].date)}`}
								onclick={() => openMarker(marker.events)}
							>
								<span class="pin"></span><span
									class="marker-label"
									style:left={marker.x > trackWidth - 160 ? '-126px' : '-6px'}
									><time>{dateLabel(marker.events[0].date)}</time>
									<strong
										>{marker.events.length === 1
											? marker.events[0].title
											: `${marker.events.length} events`}</strong
									></span
								>
							</button>
						{/each}
					</div>
				</div>
				<p class="timeline-hint">
					Drag or swipe to move. Use + / &minus; to zoom. Click an event to read more.
				</p>
			{:else}<p class="empty">No events added yet.</p>{/if}
		</section>
		<div class="feed-heading">
			<h2>Event archive</h2>
			<span>Newest first / {events.length} {events.length === 1 ? 'event' : 'events'}</span>
		</div>
		{#if events.length}
			<div class="event-feed">
				{#each events.slice(0, visibleCount) as event (event.id)}
					<article class="event-card">
						{#if event.images[0]}<button
								class="cover"
								onclick={() => openEvent(event)}
								aria-label={`Read ${event.title}`}
								><img src={event.images[0].url} alt={event.images[0].alt} loading="lazy" /></button
							>{/if}
						<div class="event-copy">
							<time datetime={event.date}>{dateLabel(event.date)}</time>
							<h3><button onclick={() => openEvent(event)}>{event.title}</button></h3>
							<p>
								{event.summary ||
									event.description.slice(0, 220) + (event.description.length > 220 ? '...' : '')}
							</p>
							<button class="read-more" onclick={() => openEvent(event)}
								>Read overview &rarr;</button
							>
						</div>
					</article>
				{/each}
			</div>
			{#if events.length > visibleCount}<button onclick={() => (visibleCount += 12)}
					>Show more events</button
				>{/if}
		{:else}<p class="archive-empty">Event overviews and photos will appear here.</p>{/if}
	{/if}
</main>

<dialog
	bind:this={dialog}
	aria-labelledby="event-title"
	onclose={() => {
		selected = null;
		group = [];
	}}
>
	<div class="dialog-top">
		<span>YIW / EVENTS</span><button onclick={() => dialog.close()} aria-label="Close event"
			>Close &times;</button
		>
	</div>
	{#if selected}
		<time datetime={selected.date}>{dateLabel(selected.date)}</time>
		<h2 id="event-title">{selected.title}</h2>
		{#if selected.summary}<p class="event-summary">{selected.summary}</p>{/if}
		{#if selected.description}<p class="event-description">{selected.description}</p>{/if}
		{#if selected.images.length}<div class="event-photos">
				{#each selected.images as photo (photo)}<figure>
						<img src={photo.url} alt={photo.alt} />{#if photo.alt}<figcaption>
								{photo.alt}
							</figcaption>{/if}
					</figure>{/each}
			</div>{/if}
		<div class="event-pagination">
			<button
				disabled={selectedIndex >= events.length - 1}
				onclick={() => openEvent(events[selectedIndex + 1])}>&larr; Older event</button
			><button disabled={selectedIndex <= 0} onclick={() => openEvent(events[selectedIndex - 1])}
				>Newer event &rarr;</button
			>
		</div>
	{:else}
		<h2 id="event-title">Events in this period</h2>
		<p class="group-note">
			Choose an event below. Zoom in on the timeline to spread out nearby dates.
		</p>
		<div class="group-list">
			{#each group as event (event.id)}<button onclick={() => openEvent(event)}
					><time>{dateLabel(event.date)}</time><strong>{event.title}</strong></button
				>{/each}
		</div>
	{/if}
</dialog>

<style>
	.timeline-panel {
		border: 1px solid var(--line);
		background: #f7f3ebdf;
		margin-bottom: 36px;
	}
	.panel-heading,
	.feed-heading,
	.dialog-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 12px;
	}
	.panel-heading {
		border-bottom: 1px solid var(--line);
		padding: 12px 18px;
	}
	.panel-heading h2 {
		margin: 0;
	}
	.controls {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 0.7rem;
	}
	.controls button {
		padding: 7px 11px;
	}
	.timeline-viewport {
		overflow-x: auto;
		overflow-y: hidden;
		cursor: grab;
		scrollbar-color: var(--line) var(--paper);
	}
	.timeline-viewport:focus-visible {
		outline: 2px solid var(--green);
		outline-offset: -3px;
	}
	.timeline-viewport.dragging {
		cursor: grabbing;
		user-select: none;
	}
	.timeline-track {
		position: relative;
		height: 290px;
		min-width: 100%;
	}
	.axis {
		position: absolute;
		top: 145px;
		left: 0;
		right: 0;
		height: 1px;
		background: var(--green);
	}
	.tick {
		position: absolute;
		top: 145px;
		height: 115px;
		border-left: 1px solid #a5bac070;
	}
	.tick span {
		position: absolute;
		top: 118px;
		left: 4px;
		white-space: nowrap;
		font-size: 0.6rem;
		color: var(--muted);
	}
	.tick.last span {
		left: -4px;
		transform: translateX(-100%);
	}
	.event-marker {
		position: absolute;
		top: 145px;
		width: 28px;
		height: 28px;
		margin-left: -14px;
		margin-top: -14px;
		padding: 0;
		border: 0;
		background: none;
		color: var(--ink);
	}
	.pin {
		position: absolute;
		left: 14px;
		top: 14px;
		width: 12px;
		height: 12px;
		background: var(--green);
		border: 2px solid var(--paper);
		outline: 1px solid var(--green);
		border-radius: 50%;
		transform: translate(-50%, -50%);
	}
	.marker-label {
		position: absolute;
		width: 150px;
		bottom: 34px;
		left: -6px;
		text-align: left;
		border-left: 2px solid var(--green);
		padding: 8px 10px;
		background: var(--paper);
	}
	.lower .marker-label {
		top: 34px;
		bottom: auto;
	}
	.marker-label strong {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		font-size: 0.75rem;
		margin-top: 6px;
		font-weight: normal;
	}
	time {
		font-size: 0.65rem;
		color: var(--muted);
	}
	.event-marker:hover .marker-label,
	.event-marker:focus-visible .marker-label {
		background: #dce8ce;
		outline: 1px solid var(--green);
	}
	.event-marker:hover .pin,
	.event-marker:focus-visible .pin {
		background: #b65c3e;
		outline: 3px solid #b65c3e55;
	}
	.timeline-hint {
		border-top: 1px solid var(--line);
		margin: 0;
		padding: 12px 18px;
		color: var(--muted);
		font-size: 0.65rem;
	}
	.empty {
		text-align: center;
		padding: 70px 16px;
		font-size: 0.8rem;
	}
	.feed-heading {
		border-bottom: 1px solid var(--line);
		margin-bottom: 24px;
	}
	.feed-heading span,
	.archive-empty {
		font-size: 0.7rem;
		color: var(--muted);
	}
	.event-feed {
		display: grid;
		gap: 24px;
		margin-bottom: 24px;
	}
	.event-card {
		display: flex;
		border-bottom: 1px solid #a5bac0;
		padding-bottom: 24px;
		gap: 24px;
	}
	.cover {
		flex: 0 0 220px;
		padding: 0;
		border: 1px solid var(--line);
		background: var(--paper);
		align-self: flex-start;
	}
	.cover img {
		width: 100%;
		height: 160px;
		object-fit: cover;
		display: block;
	}
	.event-copy {
		min-width: 0;
	}
	h3 {
		margin: 10px 0;
	}
	h3 button {
		font: inherit;
		font-size: 1.4rem;
		text-transform: uppercase;
		background: none;
		border: 0;
		padding: 0;
		text-align: left;
		overflow-wrap: anywhere;
	}
	.event-copy p {
		font-size: 0.8rem;
		overflow-wrap: anywhere;
	}
	.read-more {
		padding: 0;
		background: none;
		border: 0;
		text-decoration: underline;
		text-underline-offset: 4px;
		font-size: 0.7rem;
		color: var(--green);
	}
	dialog {
		width: min(780px, calc(100% - 32px));
		max-height: 85vh;
		border: 1px solid var(--green);
		background: var(--paper);
		color: var(--ink);
		padding: 28px;
	}
	dialog::backdrop {
		background: #24322599;
	}
	.dialog-top {
		border-bottom: 1px solid var(--line);
		padding-bottom: 16px;
		margin-bottom: 24px;
		font-size: 0.65rem;
	}
	dialog h2 {
		font-size: clamp(1.5rem, 4vw, 2.2rem);
		overflow-wrap: anywhere;
	}
	.event-summary {
		font-size: 0.95rem;
	}
	.event-description {
		white-space: pre-wrap;
		font-size: 0.85rem;
		overflow-wrap: anywhere;
	}
	.event-photos {
		display: grid;
		gap: 20px;
		margin: 24px 0;
	}
	figure {
		margin: 0;
	}
	figure img {
		display: block;
		max-width: 100%;
		max-height: 480px;
		object-fit: contain;
		margin: auto;
		border: 1px solid var(--line);
	}
	figcaption {
		font-size: 0.65rem;
		color: var(--muted);
		margin-top: 8px;
	}
	.event-pagination {
		border-top: 1px solid var(--line);
		padding-top: 20px;
		display: flex;
		justify-content: space-between;
		gap: 12px;
		margin-top: 24px;
	}
	.group-note {
		font-size: 0.8rem;
	}
	.group-list {
		display: grid;
		gap: 10px;
	}
	.group-list button {
		text-align: left;
		background: #f7f3eb;
	}
	.group-list time {
		display: block;
		margin-bottom: 8px;
	}
	@media (max-width: 650px) {
		.panel-heading {
			padding: 12px;
		}
		.event-card {
			flex-direction: column;
			gap: 16px;
		}
		.cover {
			flex-basis: auto;
			width: 100%;
		}
		.cover img {
			height: 190px;
		}
		dialog {
			padding: 18px;
		}
		.event-pagination button {
			font-size: 0.65rem;
			padding: 8px;
		}
	}
</style>
