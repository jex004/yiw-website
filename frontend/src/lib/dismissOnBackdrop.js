/** @param {HTMLDialogElement} node @param {() => void} close */
export function dismissOnBackdrop(node, close) {
	let startedOutside = false;
	/** @param {MouseEvent} event */
	function isOutside(event) {
		const bounds = node.getBoundingClientRect();
		return (
			event.target === node &&
			(event.clientX < bounds.left ||
				event.clientX > bounds.right ||
				event.clientY < bounds.top ||
				event.clientY > bounds.bottom)
		);
	}
	/** @param {PointerEvent} event */
	function pointerDown(event) {
		startedOutside = event.button === 0 && isOutside(event);
	}
	/** @param {MouseEvent} event */
	function click(event) {
		if (startedOutside && isOutside(event)) close();
		startedOutside = false;
	}
	node.addEventListener('pointerdown', pointerDown);
	node.addEventListener('click', click);
	return {
		destroy() {
			node.removeEventListener('pointerdown', pointerDown);
			node.removeEventListener('click', click);
		}
	};
}
