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
		if (lane === -1) lane = ends.length;
		ends[lane] = left + labelWidth;
		const below = lane % 2 === 1;
		const distance = 32 + Math.floor(lane / 2) * rowHeight;
		return { left, below, distance, offset: below ? distance : -distance - labelHeight };
	});
	const axis = Math.max(1, Math.ceil(ends.length / 2)) * rowHeight + 32;
	const height = axis + Math.max(1, Math.floor(ends.length / 2)) * rowHeight + 64;
	return { placed, axis, height };
}
