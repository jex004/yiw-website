import { day } from './dates.js';

const labelSpacing = 168;
const maxLanes = 4;
export const timelinePadding = 186;

/** @param {number[]} dates @param {number} viewportWidth */
export function minimumTimelineWidth(dates, viewportWidth) {
	let width = Math.max(320, viewportWidth);
	const span = Math.max(day, (dates.at(-1) ?? 0) - (dates[0] ?? 0));
	for (let index = maxLanes; index < dates.length; index++) {
		const interval = dates[index] - dates[index - maxLanes];
		if (interval > 0) width = Math.max(width, timelinePadding + (labelSpacing * span) / interval);
	}
	return Math.ceil(width);
}

/** @param {{x: number}[]} markers @param {number} width */
export function layoutMarkers(markers, width) {
	const labelWidth = 150;
	const labelHeight = 76;
	const rowHeight = 92;
	/** @type {number[]} */
	const ends = [];
	const placed = markers.map(({ x }) => {
		const left = Math.max(8, Math.min(x - 20, width - labelWidth - 8));
		let lane = ends.findIndex((end) => left >= end + 16);
		const hidden = lane === -1 && ends.length >= maxLanes;
		if (lane === -1) lane = hidden ? 0 : ends.length;
		if (!hidden) ends[lane] = left + labelWidth;
		const below = lane % 2 === 1;
		const distance = 32 + Math.floor(lane / 2) * rowHeight;
		return { left, below, distance, hidden, offset: below ? distance : -distance - labelHeight };
	});
	const axis = Math.max(1, Math.ceil(ends.length / 2)) * rowHeight + 32;
	const height = axis + Math.max(1, Math.floor(ends.length / 2)) * rowHeight + 64;
	return { placed, axis, height };
}
