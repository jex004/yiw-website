import entries from './videos.json';

/** @typedef {{id: string, title: string, creator: string, publishedAt: string, thumbnail: string, url: string}} Video */
const videos = entries.map((video) => ({
	...video,
	thumbnail: video.thumbnail || `https://i.ytimg.com/vi/${video.id}/hqdefault.jpg`,
	url: `https://www.youtube.com/watch?v=${video.id}`
}));

export default videos;
