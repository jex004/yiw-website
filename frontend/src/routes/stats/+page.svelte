<script>
	/** @typedef {{date: string, views: number, visitors: number, signins: number, accounts: number}} Day */
	/** @type {Day[]} */
	let daily = $state([]);
	/** @type {{id: string, username: string, count: number, last_signin: string}[]} */
	let signedInUsers = $state([]);
	const signinDate = new Intl.DateTimeFormat('en', {
		dateStyle: 'medium',
		timeStyle: 'short',
		timeZone: 'UTC'
	});
	let days = $state(30);
	let loading = $state(true);
	let error = $state('');
	let needsLogin = $state(false);
	let refresh = $state(0);
	let views = $derived(daily.reduce((sum, day) => sum + day.views, 0));
	let signins = $derived(daily.reduce((sum, day) => sum + day.signins, 0));
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
				<dt>Page views</dt>
				<dd>{views.toLocaleString()}</dd>
			</div>
			<div>
				<dt>Successful sign-ins</dt>
				<dd>{signins.toLocaleString()}</dd>
			</div>
			<div>
				<dt>Visitors today (approx.)</dt>
				<dd>{(daily[0]?.visitors ?? 0).toLocaleString()}</dd>
			</div>
		</dl>
		<p>
			Visitors are counted per browser per day. Different devices or cleared storage can count
			someone again; blocked tracking can miss visits. Daily account counts come from successful
			Discord sign-ins, not login-button clicks. These are approximate activity metrics, not
			verified human counts.
		</p>
		<div class="table-wrap">
			<table>
				<caption>Daily activity — counts begin when this feature is deployed</caption><thead
					><tr
						><th scope="col">Date</th><th scope="col">Page views</th><th scope="col">Visitors</th
						><th scope="col">Sign-ins</th><th scope="col">Accounts signing in</th></tr
					></thead
				><tbody
					>{#each daily as day (day.date)}<tr
							><th scope="row">{day.date}</th><td>{day.views}</td><td>{day.visitors}</td><td
								>{day.signins}</td
							><td>{day.accounts}</td></tr
						>{/each}</tbody
				>
			</table>
		</div>
		<h2>Discord sign-ins</h2>
		<p>
			Accounts that signed in during the selected period, most recent first. Username records begin
			with this update; earlier aggregate counts remain in the daily table.
		</p>
		{#if signedInUsers.length}
			<div class="table-wrap">
				<table>
					<caption>Signed-in users — visible only to the server owner</caption><thead
						><tr
							><th scope="col">Discord username</th><th scope="col">Sign-ins</th><th scope="col"
								>Latest sign-in (UTC)</th
							></tr
						></thead
					><tbody
						>{#each signedInUsers as user (user.id)}<tr
								><th scope="row">{user.username}</th><td>{user.count}</td><td
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
