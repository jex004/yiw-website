<script>
	import { onMount, tick } from 'svelte';
	import { dismissOnBackdrop } from '$lib/dismissOnBackdrop.js';
	import MemberJoinChart from '$lib/MemberJoinChart.svelte';
	/** @typedef {{id: string, username: string, avatar_url: string, date_joined: string, minecraft_username: string, preferred_name?: string, bio: string, detailed_bio?: string}} Member */
	/** @type {{discord_id: string, username: string} | null} */
	let currentUser = $state(null);
	/** @type {Member[]} */
	let members = $state([]);
	/** @type {Member | null} */
	let selected = $state(null);
	/** @type {HTMLDialogElement} */
	let dialog;
	/** @type {HTMLDivElement | undefined} */
	let flipper = $state();
	/** @type {HTMLButtonElement | null} */
	let source = null;
	let loading = $state(true),
		error = $state('');
	let editing = $state(false),
		saving = $state(false),
		animating = $state(false);
	let editingBio = $state(''),
		editingMcName = $state(''),
		editingDetailedBio = $state('');
	let saveMessage = $state('');
	let editingPreferredName = $state('');
	let search = $state('');
	let filteredMembers = $derived(
		members.filter((member) =>
			[
				member.username,
				member.preferred_name,
				member.minecraft_username === 'Not set' ? '' : member.minecraft_username
			].some((name) => name?.toLowerCase().includes(search.trim().toLowerCase()))
		)
	);
	let ownsProfile = $derived.by(() => !!selected && currentUser?.discord_id === selected.id);

	async function load() {
		loading = true;
		error = '';
		try {
			const [authRes, dirRes] = await Promise.all([
				fetch('/api/me', { credentials: 'include' }),
				fetch('/api/members')
			]);
			if (!authRes.ok || !dirRes.ok) throw new Error('Could not load members. Please try again.');
			const auth = await authRes.json();
			currentUser = auth.authenticated ? auth.user : null;
			members = (await dirRes.json()).members;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Could not load members.';
		} finally {
			loading = false;
		}
	}
	/** @param {Member} member @param {MouseEvent} event */
	async function openProfile(member, event) {
		if (animating || dialog.open) return;
		source = /** @type {HTMLButtonElement} */ (event.currentTarget);
		selected = member;
		editing = false;
		saveMessage = '';
		await tick();
		dialog.showModal();
		await animateCard(false);
	}
	/** @param {boolean} closing */
	async function animateCard(closing) {
		if (
			!source?.isConnected ||
			!flipper ||
			window.matchMedia('(prefers-reduced-motion: reduce)').matches
		)
			return;
		animating = true;
		const from = source.getBoundingClientRect(),
			to = dialog.getBoundingClientRect();
		const dx = from.x + from.width / 2 - to.x - to.width / 2;
		const dy = from.y + from.height / 2 - to.y - to.height / 2;
		const small = `translate(${dx}px, ${dy}px) scale(${from.width / to.width}, ${from.height / to.height}) rotateY(0deg)`;
		const frames = [
			{ transform: small, offset: 0 },
			{
				transform: `translate(${dx * 0.35}px, ${dy * 0.35}px) scale(.8) rotateY(90deg)`,
				offset: 0.45
			},
			{ transform: 'translate(0, 0) scale(1) rotateY(180deg)', offset: 1 }
		];
		const animation = flipper.animate(frames, {
			duration: closing ? 300 : 480,
			easing: 'cubic-bezier(.22,.7,.3,1)',
			direction: closing ? 'reverse' : 'normal'
		});
		try {
			await animation.finished;
		} catch {
			/* The element can unmount during navigation. */
		}
		animating = false;
	}
	async function closeProfile() {
		if (animating || saving) return;
		editing = false;
		await tick();
		await animateCard(true);
		dialog.close();
	}
	function startEditing() {
		if (!selected || animating) return;
		editingPreferredName = selected.preferred_name || '';
		editingBio = selected.bio || '';
		editingMcName = selected.minecraft_username === 'Not set' ? '' : selected.minecraft_username;
		editingDetailedBio = selected.detailed_bio || '';
		saveMessage = '';
		editing = true;
	}
	async function saveProfile() {
		if (!selected || saving) return;
		saving = true;
		saveMessage = '';
		try {
			const res = await fetch('/api/profile/update', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
				body: JSON.stringify({
					preferred_name: editingPreferredName.trim(),
					bio: editingBio,
					mc_name: editingMcName,
					detailed_bio: editingDetailedBio
				})
			});
			if (!res.ok || (await res.json()).status !== 'success')
				throw new Error('Could not save your profile. Please try again.');
			const updated = {
				...selected,
				preferred_name: editingPreferredName.trim(),
				bio: editingBio,
				minecraft_username: editingMcName || 'Not set',
				detailed_bio: editingDetailedBio
			};
			members = members.map((member) => (member.id === updated.id ? updated : member));
			selected = updated;
			editing = false;
			saveMessage = 'Profile saved.';
		} catch (err) {
			saveMessage = err instanceof Error ? err.message : 'Could not save your profile.';
		} finally {
			saving = false;
		}
	}
	onMount(() => {
		void load();
	});
</script>

<main>
	<header class="page-heading">
		<div>
			<p class="section-number">02 / Members</p>
			<h1>Community roster</h1>
			<p>The people in the server. ૮₍ ˶ᵔ ᵕ ᵔ˶ ₎ა</p>
		</div>
		{#if !currentUser}<!-- eslint-disable svelte/no-navigation-without-resolve -- Login is a backend endpoint. -->
			<a class="button-link" href="/login" data-sveltekit-reload>Log in with Discord &rarr;</a
			>{:else}<p class="signed-in">
				Logged in as <strong>{currentUser.username}</strong>
			</p>{/if}
	</header>
	<MemberJoinChart />
	<div class="roster-label">
		<span>MEMBER DIRECTORY</span><span
			>{loading ? 'LOADING' : `${filteredMembers.length} / ${members.length} MEMBERS`}</span
		>
	</div>
	<div class="directory-search">
		<input
			id="member-search"
			type="search"
			bind:value={search}
			placeholder="⌕ Search for a member"
		/>
	</div>
	{#if loading}<p role="status">Loading members...</p>
	{:else if error}<p role="alert">{error}</p>
		<button onclick={load}>Try again</button>
	{:else if !members.length}<p>No members to show yet.</p>
	{:else if !filteredMembers.length}<p role="status">No members match your search.</p>
	{:else}
		<div class="roster">
			{#each filteredMembers as member (member.id)}
				<button
					class="member-card"
					class:opened={selected?.id === member.id}
					aria-label={`View ${member.username}'s profile`}
					aria-haspopup="dialog"
					onclick={(event) => openProfile(member, event)}
				>
					<span class="member-heading"
						><img src={member.avatar_url} alt="" width="56" height="56" /><span
							><strong>{member.username}</strong><small>Joined {member.date_joined}</small></span
						></span
					>
					<span class="member-names">
						<span class="member-name"
							><small>PREFERRED NAME</small>{member.preferred_name || 'Not set'}</span
						>
						<span class="member-name"
							><small>MINECRAFT USERNAME</small>{member.minecraft_username}</span
						>
					</span>
					<span class="bio-preview">{member.bio || 'No short bio added yet.'}</span>
					<span class="card-footer"
						><span>{currentUser?.discord_id === member.id ? 'Your profile' : ''}</span><span
							>View &rarr;</span
						></span
					>
				</button>
			{/each}
		</div>
	{/if}
</main>

<dialog
	use:dismissOnBackdrop={closeProfile}
	bind:this={dialog}
	aria-labelledby="profile-title"
	oncancel={(event) => {
		event.preventDefault();
		void closeProfile();
	}}
	onclose={async () => {
		selected = null;
		editing = false;
		await tick();
		if (source?.isConnected) source.focus();
		else document.getElementById('member-search')?.focus();
	}}
>
	{#if selected}
		<div class="flipper" bind:this={flipper}>
			<div class="card-front" aria-hidden="true">
				<img src={selected.avatar_url} alt="" width="80" height="80" /><strong
					>{selected.username}</strong
				>
				<p>{selected.bio || 'Member profile'}</p>
			</div>
			<div class="card-back">
				<div class="profile-top">
					<span>YIW / MEMBER PROFILE</span><button
						class="close"
						aria-label="Close profile"
						disabled={animating || saving}
						onclick={closeProfile}>Close &times;</button
					>
				</div>
				<div class="profile-heading">
					<img src={selected.avatar_url} alt="" width="80" height="80" />
					<div>
						<h2 id="profile-title">{selected.username}</h2>
						<p>Joined {selected.date_joined}</p>
					</div>
				</div>
				{#if editing && ownsProfile}
					<form
						onsubmit={(event) => {
							event.preventDefault();
							void saveProfile();
						}}
					>
						<label for="preferred-name">Preferred name</label>
						<input
							id="preferred-name"
							bind:value={editingPreferredName}
							maxlength="20"
							disabled={saving}
							placeholder="What should people call you?"
						/>
						<label for="mc-name">Minecraft username</label><input
							id="mc-name"
							bind:value={editingMcName}
							maxlength="20"
							disabled={saving}
						/>
						<label for="bio"
							>Short bio <small>Up to two lines shown on your member card</small></label
						><textarea id="bio" bind:value={editingBio} rows="3" disabled={saving}></textarea>
						<label for="detailed-bio">About you <small>Shown in your full profile</small></label
						><textarea
							id="detailed-bio"
							bind:value={editingDetailedBio}
							rows="8"
							maxlength="10000"
							disabled={saving}></textarea>
						<div class="edit-actions">
							<button disabled={saving}>{saving ? 'Saving...' : 'Save profile'}</button><button
								type="button"
								disabled={saving}
								onclick={() => (editing = false)}>Cancel</button
							>
						</div>
					</form>
				{:else}
					<dl>
						<dt>Preferred name</dt>
						<dd>{selected.preferred_name || 'Not set'}</dd>
						<dt>Minecraft username</dt>
						<dd>{selected.minecraft_username}</dd>
					</dl>
					<h3>Short bio</h3>
					<p class="intro">
						{selected.bio?.trim() ? selected.bio : 'This member has not added a bio yet.'}
					</p>
					<h3>About</h3>
					<p class="full-bio">
						{selected.detailed_bio?.trim()
							? selected.detailed_bio
							: `Unfortunately, who ${selected.username} is remains a mystery.`}
					</p>
					{#if ownsProfile}<button disabled={animating} onclick={startEditing}>Edit profile</button
						>{/if}
				{/if}
				{#if saveMessage}<p class="save-message" role="status">{saveMessage}</p>{/if}
			</div>
		</div>
	{/if}
</dialog>

<style>
	.directory-search {
		display: grid;
		gap: 8px;
		margin-top: 20px;
		font-size: 0.75rem;
		color: var(--green);
	}
	.directory-search input {
		width: 100%;
		min-width: 0;
	}
	.member-names {
		border-bottom: 1px solid #c0c8b4;
		padding-bottom: 16px;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
		gap: 16px;
		width: 100%;
	}
	dd + dt {
		margin-top: 16px;
	}
	.roster-label {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		border-block: 1px solid var(--line);
		padding: 13px 0;
		font-size: 0.7rem;
		color: var(--green);
	}
	.roster {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));
		gap: 24px;
		margin-top: 24px;
	}
	.member-card {
		display: flex;
		flex-direction: column;
		text-align: left;
		background: #f7f3ebdd;
		border: 1px solid var(--line);
		padding: 22px;
		min-width: 0;
		color: var(--ink);
		transition:
			transform 160ms,
			box-shadow 160ms;
	}
	.member-card:hover {
		background: var(--paper);
		transform: translateY(-4px);
		box-shadow: 4px 5px 0 #416d4820;
	}
	.member-card.opened {
		visibility: hidden;
	}
	.member-heading {
		display: flex;
		align-items: center;
		gap: 14px;
		margin-bottom: 20px;
	}
	.member-heading > span {
		min-width: 0;
	}
	.member-heading strong {
		display: block;
		font-family: 'Arial Narrow', 'Trebuchet MS', sans-serif;
		font-weight: 400;
		text-transform: uppercase;
		font-size: 1.2rem;
		overflow-wrap: anywhere;
		margin-bottom: 6px;
	}
	img {
		border: 1px solid var(--line);
		object-fit: cover;
		flex-shrink: 0;
		filter: saturate(0.8);
	}
	small,
	.signed-in {
		font-size: 0.7rem;
		color: var(--muted);
	}
	.member-name {
		font-size: 0.75rem;
		overflow-wrap: anywhere;
	}
	.member-name small {
		display: block;
		color: var(--green);
		font-size: 0.6rem;
		margin-bottom: 5px;
	}
	.bio-preview {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		font-size: 0.8rem;
		line-height: 1.6;
		height: 3.2em;
		flex-shrink: 0;
		overflow-wrap: anywhere;
		white-space: pre-wrap;
		margin: 16px 0 20px;
	}
	.card-footer {
		display: flex;
		justify-content: space-between;
		gap: 12px;
		padding-top: 12px;
		margin-top: auto;
		font-size: 0.65rem;
		color: var(--green);
		width: 100%;
	}
	dialog {
		width: min(680px, calc(100% - 32px));
		max-width: none;
		padding: 0;
		border: 0;
		background: transparent;
		color: var(--ink);
		overflow: visible;
		perspective: 1400px;
	}
	dialog::backdrop {
		background: #163a42a6;
	}
	.flipper {
		position: relative;
		transform-style: preserve-3d;
		transform: rotateY(180deg);
	}
	.card-front,
	.card-back {
		backface-visibility: hidden;
		border: 1px solid var(--green);
		background-color: var(--paper);
		background-image:
			linear-gradient(var(--grid) 1px, transparent 1px),
			linear-gradient(90deg, var(--grid) 1px, transparent 1px);
		background-size: 40px 40px;
		padding: 28px;
	}
	.card-front {
		position: absolute;
		inset: 0;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		gap: 16px;
	}
	.card-front strong {
		font-size: 1.5rem;
		overflow-wrap: anywhere;
	}
	.card-front img {
		align-self: flex-start;
	}
	.card-back {
		transform: rotateY(180deg);
		max-height: 85dvh;
		overflow: auto;
	}
	.profile-top {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 12px;
		border-bottom: 1px solid var(--line);
		padding-bottom: 16px;
		margin-bottom: 24px;
		font-size: 0.65rem;
	}
	.profile-heading {
		display: flex;
		align-items: center;
		gap: 20px;
	}
	.profile-heading div {
		min-width: 0;
	}
	h2 {
		font-size: clamp(1.4rem, 4vw, 2rem);
		margin: 0;
		overflow-wrap: anywhere;
	}
	.profile-heading p {
		font-size: 0.7rem;
		color: var(--muted);
	}
	dl {
		border-block: 1px solid var(--line);
		padding: 16px 0;
		margin: 24px 0;
	}
	dt {
		font-size: 0.65rem;
		text-transform: uppercase;
		color: var(--green);
		margin-bottom: 6px;
	}
	dd {
		margin: 0;
		overflow-wrap: anywhere;
		font-size: 0.85rem;
	}
	.intro,
	.full-bio {
		white-space: pre-wrap;
		overflow-wrap: anywhere;
		font-size: 0.85rem;
		line-height: 1.8;
	}
	.intro {
		color: var(--muted);
	}
	.full-bio {
		margin-bottom: 24px;
	}
	h3 {
		font-size: 1rem;
	}
	form {
		display: grid;
		gap: 10px;
		margin-top: 24px;
		font-size: 0.8rem;
	}
	label small {
		display: block;
		margin-top: 4px;
	}
	.edit-actions {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
	}
	.save-message {
		font-size: 0.75rem;
		color: var(--green);
	}
	@media (max-width: 650px) {
		.card-front,
		.card-back {
			padding: 18px;
		}
		.profile-heading {
			gap: 12px;
		}
		.profile-heading img {
			width: 64px;
			height: 64px;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.member-card {
			transition: none;
		}
		.member-card:hover {
			transform: none;
		}
	}
</style>
