# YIW frontend

Run `npm install`, then `npm run dev` to start the site. The backend runs on port 2000.

- `npm run check`: Svelte and JavaScript checks.
- `npm run lint`: formatting and lint checks.
- `npm run format`: format with Prettier.
- `npm run build`: production build.

See [community content](../backend/COMMUNITY.md) for editing countries and events.

## Games we play

Edit `src/lib/games.json` to manage the Overview game list. Each entry has a `name`, optional `category` and `note`, and a `links` array of plain website URLs or `{ "label": "Play online", "url": "https://example.com" }` objects. Use `[]` for games without links. Entries appear in file order. Links open in a new tab; only HTTP(S) URLs are accepted. All entries are public. Save for local updates; commit and push for Railway.

The first four games are shown initially; visitors can expand or collapse the rest. To add pixel art, place an image in `static/art/games/` and add `"image": "/art/games/minecraft.png"` to that game in `games.json`. Omit `image` to keep the coloured header blank. Images are fitted without cropping.
