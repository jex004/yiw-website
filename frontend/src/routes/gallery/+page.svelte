<script>
	import { resolve } from '$app/paths';
</script>

<main>
	<header class="page-heading">
		<div>
			<p class="section-number">05 / Gallery</p>
			<h1>Community gallery</h1>
			<p>Photos and screenshots from the server.</p>
		</div>
	</header>
	<section class="gallery-placeholder" aria-label="Gallery coming soon">
		<span class="placeholder-icon" aria-hidden="true">[ + ]</span>
		<h2>Nothing here yet</h2>
		<p>The gallery is still being built. Check back later.</p>
		<a href={resolve('/members')}>Back to the directory &rarr;</a>
	</section>
</main>

<style>
	.gallery-placeholder {
		border: 1px dashed var(--line);
		background: #f7f3ebba;
		text-align: center;
		padding: 80px 20px;
	}
	.placeholder-icon {
		color: var(--green);
		font-size: 2rem;
	}
	.gallery-placeholder p,
	.gallery-placeholder a {
		font-size: 0.8rem;
	}
</style>
