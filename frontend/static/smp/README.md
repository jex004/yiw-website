# SMP screenshots

Put screenshots in this folder, then add entries to `frontend/src/lib/smp.json`:

```json
[
  {
    "id": "spawn",
    "src": "/smp/spawn.png",
    "title": "Spawn",
    "alt": "Describe what is in the screenshot",
    "credit": "Built by / screenshot by (optional)"
  }
]
```

Use unique IDs and matching filenames (including capitalization). The first three entries are featured; all entries appear in the popup. Images display in file order. Omit `credit` if not needed. No image uploads or database changes are required; commit the images and JSON together to publish them.
