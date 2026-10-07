let visitorDay = '';
let visitorId = '';

export function countPageView() {
	const today = new Date().toISOString().slice(0, 10);
	if (visitorDay !== today) {
		visitorDay = today;
		visitorId = crypto.randomUUID();
		try {
			const saved = JSON.parse(localStorage.getItem('yiw-visitor') || 'null');
			if (saved?.day === today && /^[\da-f]{8}(-[\da-f]{4}){3}-[\da-f]{12}$/i.test(saved.id)) {
				visitorId = saved.id;
			}
			localStorage.setItem('yiw-visitor', JSON.stringify({ day: today, id: visitorId }));
		} catch {
			// Keep an in-memory identifier when browser storage is unavailable.
		}
	}
	void fetch('/api/visits', {
		method: 'POST',
		credentials: 'omit',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ visitor: visitorId }),
		keepalive: true
	}).catch(() => {});
}
