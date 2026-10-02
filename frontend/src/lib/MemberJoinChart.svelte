<script>
	import { onMount } from 'svelte';
	import { day, dateFormat, timestamp } from '$lib/dates.js';
	import { Line } from 'svelte-chartjs';
	import {
		Chart as ChartJS,
		Tooltip,
		Legend,
		LineElement,
		LinearScale,
		PointElement,
		Filler
	} from 'chart.js';
	ChartJS.register(Tooltip, Legend, LineElement, LinearScale, PointElement, Filler);

	/** @type {import('chart.js').ChartData<'line', {x: number, y: number}[]>} */
	let chartData = $state({ datasets: [] });
	let loading = $state(true);
	let error = $state('');
	let currentMembers = $state(0);
	let missingDates = $state(0);
	let hasChart = $state(false);
	/** @type {import('chart.js').ChartOptions<'line'>} */
	const options = {
		responsive: true,
		maintainAspectRatio: false,
		interaction: { intersect: false, mode: 'nearest' },
		plugins: {
			legend: { display: false },
			tooltip: {
				callbacks: {
					title: (items) =>
						items[0]?.parsed.x != null ? dateFormat.format(items[0].parsed.x) : '',
					label: (item) => `${item.parsed.y} current members joined by this date`
				}
			}
		},
		scales: {
			x: {
				type: 'linear',
				title: { display: true, text: 'Join date (UTC)' },
				ticks: { maxTicksLimit: 7, callback: (value) => dateFormat.format(Number(value)) },
				grid: { display: false }
			},
			y: {
				beginAtZero: true,
				title: { display: true, text: 'Current members joined by date' },
				ticks: { precision: 0 }
			}
		}
	};

	async function load() {
		loading = true;
		error = '';
		try {
			const res = await fetch('/api/timeline');
			if (!res.ok) throw new Error('Could not load the member graph. Please try again.');
			const data = await res.json();
			currentMembers = data.current_members;
			missingDates = data.missing_join_dates;
			/** @type {{x: number, y: number}[]} */
			const points = data.chart_data.map(
				/** @param {{date: string, total_members: number}} point */ (point) => ({
					x: timestamp(point.date),
					y: point.total_members
				})
			);
			hasChart = points.length > 0;
			// A zero baseline makes the first day's joins visible, including single-day datasets.
			if (points.length) points.unshift({ x: points[0].x - day, y: 0 });
			chartData = {
				datasets: [
					{
						label: 'Current members joined by date',
						data: points,
						borderColor: '#416d48',
						backgroundColor: 'rgba(107, 151, 88, 0.15)',
						fill: true,
						stepped: 'before',
						pointRadius: 0,
						pointHitRadius: 12,
						pointHoverRadius: 5,
						borderWidth: 2
					}
				]
			};
		} catch (err) {
			error = err instanceof Error ? err.message : 'Could not load the member graph.';
		} finally {
			loading = false;
		}
	}
	onMount(() => {
		void load();
	});
</script>

<section class="chart-card" aria-label="Member join graph">
	{#if loading}<p role="status">Loading member graph...</p>
	{:else if error}<p role="alert">{error}</p>
		<button onclick={load}>Try again</button>
	{:else}
		<div class="chart-heading">
			<h2>When our current members joined</h2>
			<strong>{currentMembers} current members</strong>
		</div>
		<p>
			This chartcounts people who are in the server, using their latest join date. The chart does
			not explicitly show if a member left then rejoined. It excludes bots and people who left, so
			it is not a record of past server size.
		</p>
		{#if hasChart}
			<div class="chart"><Line data={chartData} {options} /></div>
			<p class="note">
				Each step groups one day's joins. Horizontal distance represents elapsed time; the line
				continues to today.
			</p>
		{:else}
			<p>No member join dates available yet.</p>
		{/if}
		{#if missingDates}<p class="note">
				{missingDates} current members have no usable join date and are excluded from the curve.
			</p>{/if}
	{/if}
</section>

<style>
	.chart-card {
		padding: 24px;
		border: 1px solid var(--line);
		background: #f7f3ebeb;
		margin: 0 0 32px;
	}
	.chart-heading {
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 12px;
	}
	.chart-heading strong {
		font-size: 0.7rem;
		color: var(--green);
		border: 1px solid var(--line);
		padding: 8px;
	}
	.chart-card > p {
		font-size: 0.75rem;
		color: var(--muted);
	}
	.chart {
		height: 340px;
	}
	.note {
		font-size: 0.65rem;
		color: var(--muted);
	}
	@media (max-width: 650px) {
		.chart-card {
			padding: 12px;
		}
		.chart {
			height: 270px;
		}
	}
</style>
