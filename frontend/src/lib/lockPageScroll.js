let locks = 0;
/** @type {(() => void) | undefined} */
let restore;

export function lockPageScroll() {
	if (locks++ === 0) {
		const { scrollX, scrollY } = window;
		const body = document.body;
		const root = document.documentElement;
		const properties = ['position', 'top', 'left', 'width'];
		const previous = properties.map((name) => [
			name,
			body.style.getPropertyValue(name),
			body.style.getPropertyPriority(name)
		]);
		const overflow = root.style.overflow;
		root.style.overflow = 'hidden';
		body.style.position = 'fixed';
		body.style.top = `${-scrollY}px`;
		body.style.left = `${-scrollX}px`;
		body.style.width = '100%';
		restore = () => {
			for (const [name, value, priority] of previous) {
				if (value) body.style.setProperty(name, value, priority);
				else body.style.removeProperty(name);
			}
			root.style.overflow = overflow;
			window.scrollTo({ left: scrollX, top: scrollY, behavior: 'instant' });
		};
	}
	let released = false;
	return () => {
		if (released) return;
		released = true;
		if (--locks === 0) {
			restore?.();
			restore = undefined;
		}
	};
}
