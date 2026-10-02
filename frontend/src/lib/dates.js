export const day = 86400000;

export const dateFormat = new Intl.DateTimeFormat('en', {
	day: 'numeric',
	month: 'short',
	year: 'numeric',
	timeZone: 'UTC'
});

/** @param {string} value */
export const timestamp = (value) => Date.parse(`${value}T00:00:00Z`);
