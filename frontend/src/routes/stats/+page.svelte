<script>
	/** @typedef {{date: string, views: number, visitors: number, accounts: number}} Day */
	/** @type {Day[]} */
	let daily = $state([]);
	let allTimeViews = $state(0);
	let allTimeAccounts = $state(0);
	/** @type {{id: string, username: string, last_signin: string}[]} */
	let signedInUsers = $state([]);
	const signinDate = new Intl.DateTimeFormat('en', {
		dateStyle: 'medium',
		timeStyle: 'short',
		timeZone: 'UTC'
	});
	let days = $state(7);
	let loading = $state(true);
	let error = $state('');
	let needsLogin = $state(false);
	let refresh = $state(0);
	let views = $derived(daily.reduce((sum, day) => sum + day.views, 0));
	let visitors = $derived(daily.reduce((sum, day) => sum + day.visitors, 0));
	$effect(() => {
		const period = days;
		void refresh;
		const controller = new AbortController();
		loading = true;
		error = '';
		needsLogin = false;
		void (async () => {
			try {
				const response = await fetch(`/api/stats?days=${period}`, { signal: controller.signal });
				const data = await response.json();
				if (!response.ok) {
					needsLogin = response.status === 401;
					throw new Error(
						typeof data.detail === 'string' ? data.detail : 'Could not load statistics.'
					);
				}
				daily = data.daily;
				allTimeViews = data.all_time_views;
				allTimeAccounts = data.all_time_accounts;
				signedInUsers = data.signed_in_users;
			} catch (err) {
				if (!controller.signal.aborted)
					error = err instanceof Error ? err.message : 'Could not load statistics.';
			} finally {
				if (!controller.signal.aborted) loading = false;
			}
		})();
		return () => controller.abort();
	});
</script>

<main>
	<header class="page-heading">
		<div>
			<p class="section-number">OWNER / STATISTICS</p>
			<h1>Site activity</h1>
			<p>Daily counts, using UTC dates.</p>
		</div>
	</header>
	{#if loading}<p role="status">Loading statistics...</p>
	{:else if error}<p role="alert">{error}</p>
		{#if needsLogin}
			<!-- eslint-disable svelte/no-navigation-without-resolve -- Backend login endpoint. -->
			<a class="button-link" href="/login" data-sveltekit-reload>Sign in with Discord</a>
			<p>After signing in, return to Owner statistics in the footer.</p>
		{:else}<button onclick={() => refresh++}>Try again</button>{/if}
	{:else}
		<label
			>Show <select bind:value={days}
				><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option
					value={90}>Last 90 days</option
				></select
			></label
		>
		<dl>
			<div>
				<dt>All-time page views</dt>
				<dd>{allTimeViews.toLocaleString()}</dd>
			</div>
			<div>
				<dt>Page views (last {days} days)</dt>
				<dd>{views.toLocaleString()}</dd>
			</div>
			<div>
				<dt title="Daily visitor counts added together; returning on another day counts again.">
					Visitors (last {days} days)
				</dt>
				<dd>{visitors.toLocaleString()}</dd>
			</div>
			<div>
				<dt>All-time unique Discord logins</dt>
				<dd>{allTimeAccounts.toLocaleString()}</dd>
			</div>
		</dl>
		<div class="table-wrap">
			<table>
				<caption>Daily activity — counts begin when this feature is deployed</caption><thead
					><tr
						><th scope="col">Date</th><th scope="col">Page views</th><th scope="col">Visitors</th
						><th scope="col">First-time Discord logins</th></tr
					></thead
				><tbody
					>{#each daily as day (day.date)}<tr
							><th scope="row">{day.date}</th><td>{day.views}</td><td>{day.visitors}</td><td
								>{day.accounts}</td
							></tr
						>{/each}</tbody
				>
			</table>
		</div>
		<h2>Discord accounts</h2>
		{#if signedInUsers.length}
			<div class="table-wrap">
				<table>
					<caption>Signed-in users — visible only to the server owner</caption><thead
						><tr><th scope="col">Discord username</th><th scope="col">Latest sign-in (UTC)</th></tr
						></thead
					><tbody
						>{#each signedInUsers as user (user.id)}<tr
								><th scope="row">{user.username}</th><td
									>{signinDate.format(new Date(user.last_signin))}</td
								></tr
							>{/each}</tbody
					>
				</table>
			</div>
		{:else}<p>No recorded Discord sign-ins in this period yet.</p>{/if}
	{/if}
</main>

<style>
	dl {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		gap: 16px;
		margin: 24px 0;
	}
	dl div {
		padding: 20px;
		border: 1px solid var(--line);
		background: var(--paper);
	}
	dt {
		font-size: 0.75rem;
		color: var(--muted);
	}
	dd {
		margin: 12px 0 0;
		font-size: 1.8rem;
	}
	.table-wrap {
		overflow-x: auto;
	}
	table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.75rem;
	}
	th,
	td {
		text-align: left;
		padding: 12px;
		border-bottom: 1px solid var(--line);
	}
	caption {
		text-align: left;
		padding: 12px 0;
		color: var(--muted);
	}
	p {
		font-size: 0.8rem;
		line-height: 1.6;
	}
</style>
