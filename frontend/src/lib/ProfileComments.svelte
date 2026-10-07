<script>
	import { onMount } from 'svelte';
	/** @typedef {{id: string, author_id: string, username: string, body: string, created_at: string, updated_at: string | null}} Comment */
	/** @type {{profileId: string, currentUser: {discord_id: string, username: string} | null}} */
	let { profileId, currentUser } = $props();
	/** @type {Comment[]} */
	let comments = $state([]);
	let loading = $state(true);
	let loadError = $state('');
	let error = $state('');
	let busy = $state(false);
	let draft = $state('');
	let editingId = $state('');
	let editDraft = $state('');
	let deletingId = $state('');
	let ownCount = $derived(
		comments.filter((comment) => comment.author_id === currentUser?.discord_id).length
	);
	let endpoint = $derived(`/api/members/${encodeURIComponent(profileId)}/comments`);

	/** @param {string} url @param {RequestInit} [options] */
	async function request(url, options) {
		const response = await fetch(url, { credentials: 'include', ...options });
		const data = response.status === 204 ? null : await response.json();
		if (!response.ok)
			throw new Error(
				typeof data?.detail === 'string'
					? data.detail
					: 'Could not save your comment. Please try again.'
			);
		return data;
	}
	async function load() {
		loading = true;
		loadError = '';
		try {
			comments = (await request(endpoint)).comments;
		} catch {
			loadError = 'Could not load comments. Please try again.';
		} finally {
			loading = false;
		}
	}
	/** @param {'POST' | 'PATCH' | 'DELETE'} method @param {string} [id] */
	async function save(method, id = '') {
		if (busy) return;
		busy = true;
		error = '';
		try {
			const result = await request(
				method === 'POST' ? endpoint : `/api/comments/${encodeURIComponent(id)}`,
				{
					method,
					headers: { 'Content-Type': 'application/json' },
					body:
						method === 'DELETE'
							? undefined
							: JSON.stringify({ body: method === 'POST' ? draft : editDraft })
				}
			);
			if (method === 'POST') {
				comments = [...comments, result];
				draft = '';
			} else if (method === 'PATCH') {
				comments = comments.map((comment) => (comment.id === id ? result : comment));
				editingId = '';
			} else {
				comments = comments.filter((comment) => comment.id !== id);
				deletingId = '';
				if (editingId === id) editingId = '';
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'Could not save your comment.';
		} finally {
			busy = false;
		}
	}
	onMount(() => {
		void load();
	});
</script>

<section class="comments" aria-label="Profile comments">
	<h3>Comments</h3>
	{#if loading}<p role="status">Loading comments...</p>
	{:else if loadError}<p role="alert">{loadError}</p>
		<button onclick={load}>Try again</button>
	{:else}
		{#each comments as comment (comment.id)}
			<article>
				<header>
					<strong>{comment.username}</strong>{#if comment.updated_at}<small>edited</small>{/if}
				</header>
				{#if editingId === comment.id}
					<form
						onsubmit={(event) => {
							event.preventDefault();
							void save('PATCH', comment.id);
						}}
					>
						<label for={`edit-comment-${comment.id}`}>Edit comment</label>
						<textarea
							id={`edit-comment-${comment.id}`}
							bind:value={editDraft}
							maxlength="200"
							rows="3"
							required
							disabled={busy}></textarea>
						<small>{editDraft.length}/200</small>
						<div class="actions">
							<button disabled={busy || !editDraft.trim()}>Save</button><button
								type="button"
								disabled={busy}
								onclick={() => (editingId = '')}>Cancel</button
							>
						</div>
					</form>
				{:else}<p class="body">{comment.body}</p>{/if}
				{#if comment.author_id === currentUser?.discord_id}
					<div class="actions">
						{#if deletingId === comment.id}<span>Delete this comment?</span><button
								disabled={busy}
								onclick={() => save('DELETE', comment.id)}>Delete</button
							><button disabled={busy} onclick={() => (deletingId = '')}>Cancel</button>
						{:else}
							{#if editingId !== comment.id}<button
									disabled={busy}
									onclick={() => {
										editingId = comment.id;
										editDraft = comment.body;
										error = '';
									}}>Edit</button
								>{/if}
							<button disabled={busy} onclick={() => (deletingId = comment.id)}>Delete</button>
						{/if}
					</div>
				{/if}
			</article>
		{:else}<p>No comments yet.</p>{/each}
		{#if !currentUser}
			<!-- eslint-disable svelte/no-navigation-without-resolve -- Backend login endpoint. -->
			<p>
				<a href="/login" data-sveltekit-reload>Sign in with Discord</a> to leave a comment. You don't
				need to be in the server.
			</p>
		{:else if ownCount >= 2}<p>
				You've left two comments on this profile. You can edit or delete them above.
			</p>
		{:else}
			<form
				onsubmit={(event) => {
					event.preventDefault();
					void save('POST');
				}}
			>
				<label for="new-profile-comment">Leave a comment</label>
				<textarea
					id="new-profile-comment"
					bind:value={draft}
					maxlength="200"
					rows="3"
					required
					disabled={busy}></textarea>
				<div class="counter">
					<small>{draft.length}/200 characters</small><small>{ownCount}/2 comments used</small>
				</div>
				<button disabled={busy || !draft.trim()}>{busy ? 'Saving...' : 'Post comment'}</button>
			</form>
		{/if}
	{/if}
	{#if error}<p role="alert">{error}</p>{/if}
</section>

<style>
	.comments {
		margin-top: 28px;
		padding-top: 20px;
		border-top: 1px solid var(--line);
		font-size: 0.8rem;
	}
	article {
		padding: 14px 0;
		border-bottom: 1px solid var(--line);
	}
	header,
	.actions,
	.counter {
		display: flex;
		gap: 12px;
		align-items: center;
		flex-wrap: wrap;
	}
	header strong {
		color: var(--green);
		overflow-wrap: anywhere;
	}
	.body {
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}
	small {
		color: var(--muted);
		font-size: 0.65rem;
	}
	form {
		display: grid;
		gap: 8px;
		margin-top: 16px;
	}
	textarea {
		width: 100%;
		min-width: 0;
		resize: vertical;
	}
	.counter {
		justify-content: space-between;
	}
	button {
		width: fit-content;
		font-size: 0.7rem;
		padding: 6px 10px;
	}
</style>
