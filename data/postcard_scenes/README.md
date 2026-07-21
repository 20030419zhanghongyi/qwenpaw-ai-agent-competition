# Postcard scene library

Reference photos + (later) time-of-day SVG illustrations for no-photo postcards.

## Current roadmap (phase 1 — NOW)

**Only collect real-world reference images from the web.**  
Do **not** batch-generate SVGs for now.

Reference photos are stored under:

```text
harness/datasets/photos/poi_refs/{poi_id}.jpg
```

Landmark briefs stay under `data/postcard_scenes/{poi_id}/_brief.json`.

```bash
# From backend/ — no QwenPaw required
python scripts/generate_postcard_scenes.py --research-only

# Only route / port POIs
python scripts/generate_postcard_scenes.py --only-routed --research-only

# Re-fetch refs even if _brief.json already exists
python scripts/generate_postcard_scenes.py --research-only --force-research
```

Checkpoint: `data/postcard_scenes/_checkpoint.json`.

## Later phase (phase 2 — not now)

Multimodal QwenPaw `scene` agent draws `morning|midday|dusk|night.svg` from each
`harness/datasets/photos/poi_refs/{poi_id}.*` (same landmark, lighting only).

| Slot | Macau local hours | 含义 |
|------|-------------------|------|
| `morning` | 05:00–11:00 | 早 |
| `midday` | 11:00–15:00 | 中 |
| `dusk` | 15:00–19:00 | 傍晚 |
| `night` | 19:00–05:00 | 晚 |
