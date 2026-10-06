export const timelinePadding = 186;

/** @param {{x: number}[]} markers @param {number} width @param {number} [labelWidth] */
export function layoutMarkers(markers, width, labelWidth = 150) {
	const axis = 124;
	/** @type {number[]} */
	const ends = [];
	const placed = markers.map(({ x }) => {
		const left = Math.max(8, Math.min(x - 20, width - labelWidth - 8));
		let lane = ends.findIndex((end) => left >= end + 16);
		const hidden = lane === -1 && ends.length === 2;
		if (lane === -1) lane = hidden ? 0 : ends.length;
		if (!hidden) ends[lane] = left + labelWidth;
		return { left, below: lane === 1, distance: 32, hidden };
	});
	return { placed, axis, height: 280 };
}
