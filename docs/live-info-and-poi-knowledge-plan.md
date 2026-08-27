# POI Knowledge Graph and Live Information Plan

Last reviewed: 2026-08-22

This document turns the POI and real-time consultation roadmap into implementable data and API work. It should be read together with `data/poi_expansion_candidates.json`, `data/pois.json`, and `backend/app/features/routes/live_context.py`.

## Current Baseline

- `data/pois.json` currently contains 344 POIs across Macau Peninsula, Taipa, Cotai, and Coloane.
- Each canonical POI already has multilingual names, district, theme tags, coordinates, intro/history/architecture/story/observation tips, and verification metadata.
- The main gap is not raw count; it is verified provenance, finer-grained relationship modelling, opening-hours metadata, media assets, and dynamic travel constraints.

## POI Expansion Scope

Use `data/poi_expansion_candidates.json` as the review queue. Do not blindly merge candidates into `data/pois.json`; first check whether a POI already exists and enrich instead of duplicating.

Priority categories:

- Historic buildings: World Heritage components, historic residences, theatres, civic buildings.
- Museums and cultural venues: Macao Museum, Taipa Houses, small neighbourhood museums, archives, libraries.
- Food and local shops: long-running food shops, market stalls, Portuguese/Macanese restaurants, souvenir bakeries.
- Characteristic neighbourhoods: Senado/Ruins cluster, St. Lazarus, Taipa Village, Lai Chi Vun, Coloane Village.
- Geo nodes: entrances, lift/elevator links, slope/stair segments, shaded arcades, bus stops, ferry/border ports, toilets, wheelchair constraints.

Recommended canonical POI extensions:

```json
{
  "opening_hours": {
    "status": "unknown|official|estimated",
    "regular": [],
    "holiday_note": "",
    "source_id": ""
  },
  "media": {
    "images": [],
    "audio": [],
    "license": ""
  },
  "geo_detail": {
    "entrances": [],
    "stairs": [],
    "shade_level": "low|medium|high",
    "indoor_ratio": 0.0,
    "accessibility_notes": []
  },
  "relations": [
    {
      "type": "near|same_story_cluster|historical_period|religious_context|food_nearby|rainy_day_backup",
      "target_poi_id": "",
      "weight": 0.0,
      "evidence": ""
    }
  ]
}
```

## Source Strategy

Use official and licensed public sources first:

- Macau Government Tourism Office sightseeing and World Heritage pages for attraction names, clusters, descriptions, and visitor-facing context.
- Cultural Affairs Bureau / Macao World Heritage pages for conservation and heritage facts.
- Macao museums portal for museum lists and venue information.
- OpenStreetMap or AMap only for geocoding and route geometry, not historical claims.
- Internal AI-generated enrichment remains `source_type=ai` and `verify_status=AI生成·待核验` until manually checked.

## Live Information Sources

The first implemented backend bundle is `GET /api/v1/routes/live-advice`.

It returns:

- `weather`: Open-Meteo daily forecast for Macau, converted into umbrella/sunscreen/indoor-backup advice.
- `crowd`: estimated crowd level from mainland China holidays, weekends, and Macao official event calendar excerpts.
- `transport`: live DSAT route changes, suspended stops, and vehicle fields, with a 25-second cache and explicit fallback state.
- `opening_hours`: verified per-POI schedules, closure days, last-entry times, verification dates, and official sources.

Source entry points:

- Macau weather / forecast fallback: `https://api.open-meteo.com/v1/forecast`
- Macao Meteorological and Geophysical Bureau current weather: `https://www.smg.gov.mo/webdiss/c_actualweather_xml.php`
- MGTO event calendar: `https://www.macaotourism.gov.mo/en/events/calendar`
- DSAT bus information: `https://www.dsat.gov.mo/bus`
- MGTO sightseeing: `https://www.macaotourism.gov.mo/en/sightseeing`
- Mainland China public holiday notices: `https://www.gov.cn/zhengce/xxgk/`

## Crowd Prediction Rules

Crowd output is labelled `status=estimated`, never as a hard fact.

Current factors:

- Mainland China public holidays:
  - New Year: high
  - Spring Festival: very high
  - Qingming: high
  - Labour Day: very high
  - Dragon Boat Festival: high
  - Mid-Autumn Festival: high
  - National Day Golden Week: very high
- Weekends: medium
- Official Macao event calendar hit: medium by default; high if event excerpts include concert, fireworks, Grand Prix, or marathon terms.
- Weather pressure: handled in `weather.flags`; heavy rain or storm recommends indoor backup. A future route matcher should convert this into indoor/shaded POI preference.

Examples:

- Mainland Golden Week plus weekend -> `very_high`, recommend avoiding afternoon at Ruins of St. Paul's, Senado Square, Rua do Cunha, and Cotai venues.
- Concert/event near Cotai -> `high`, recommend buffer time around Galaxy Arena, Venetian Arena, Hengqin Port, and HZMB Port.
- No holiday and no event -> `low`, still warn that on-site queues and official notices take priority.

## Next Implementation Steps

1. Extend verified opening hours beyond the first five priority venues.
2. Enrich the remaining candidates from `data/poi_expansion_candidates.json`, one batch per district, with provenance.
3. Add nearest bus-stop identifiers to route nodes so live vehicle data can be filtered to the exact boarding stop.
4. Migrate graph edges to a relational table only after route algorithms need graph traversal queries.
5. Feed `crowd.level` and `weather.flags.indoor_backup` into route candidate scoring so rainy or crowded dates down-rank exposed and high-crowd nodes.

## Implemented 2026-08-27

- Added the DSAT public-web adapter for route changes, suspended stops, and official vehicle data.
- Added `bus_routes` and `poi_ids` filters to `GET /api/v1/routes/live-advice`.
- Added `data/poi_knowledge_graph.json` with ten priority cultural nodes across the peninsula, Taipa, and Coloane.
- Added source-attributed schedules for the Ruins of St. Paul's, Macao Museum, A-Ma Temple, Taipa Houses, and Guia Fortress.
- Added route-page display for the current POI's verified official opening schedule.

## Guardrails

- Do not scrape social media accounts or comments for crowd prediction.
- Do not store personal location traces for crowd inference.
- Label dynamic information as an estimate and provide the official source.
- Opening hours, traffic controls, severe weather, and border queues must defer to official channels and on-site notices.
