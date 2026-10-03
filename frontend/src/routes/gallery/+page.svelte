<script>
	import VideoLibrary from '$lib/VideoLibrary.svelte';
	/** @type {{open: () => void} | undefined} */
	let library = $state();
	import VideoCarousel from '$lib/VideoCarousel.svelte';
	import videoData from '$lib/videos.json';
	const featured = [...videoData].sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
</script>

<main>
	<header class="page-heading">
		<div>
			<p class="section-number">05 / Gallery</p>
			<h1>Community gallery</h1>
			<p>Videos, photos, and screenshots from the server. ദ്ദി ˉ͈̀꒳ˉ͈́ )✧</p>
		</div>
	</header>
	<div class="section-heading">
		<h2>Pure Cinema</h2>
		<button class="text-button" aria-haspopup="dialog" onclick={() => library?.open()}
			>See all &rarr;</button
		>
	</div>
	{#if featured.length}<VideoCarousel videos={featured} />
	{:else}<p>No videos added yet.</p>{/if}
	<section class="photos-placeholder" aria-label="Photos coming soon">
		<h2>Photos &amp; screenshots</h2>
		<p>More from the server, coming soon.</p>
	</section>
</main>
<VideoLibrary bind:this={library} />

<style>
	.section-heading {
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 16px;
		margin: 24px 0 16px;
	}
	.section-heading h2 {
		margin: 0;
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
	.photos-placeholder {
		margin-top: 36px;
		border: 1px dashed var(--line);
		padding: 28px;
		text-align: center;
	}
	.photos-placeholder p {
		color: var(--muted);
		font-size: 0.75rem;
	}
</style>
