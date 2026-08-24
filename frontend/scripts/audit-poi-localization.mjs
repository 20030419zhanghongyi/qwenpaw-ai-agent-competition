import fs from "node:fs";
import path from "node:path";

const frontendRoot = path.resolve(import.meta.dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8"));
const pois = readJson(path.join(repoRoot, "data/pois.json")).pois;
const routes = readJson(path.join(repoRoot, "data/routes.json")).routes;
const ports = readJson(path.join(repoRoot, "data/ports.json")).ports;
const generated = readJson(
  path.join(frontendRoot, "src/data/poiNames.generated.json"),
).names;
const localizationSource = fs.readFileSync(
  path.join(frontendRoot, "src/lib/poiLocalization.ts"),
  "utf8",
);
const curatedIds = new Set(
  [...localizationSource.matchAll(/^  (poi_[A-Za-z0-9_]+): \{/gm)].map(
    (match) => match[1],
  ),
);
const legacyIds = new Map(
  [...localizationSource.matchAll(/(poi_[A-Za-z0-9_]+): "(poi_[A-Za-z0-9_]+)"/g)].map(
    (match) => [match[1], match[2]],
  ),
);
const knownIds = new Set(pois.map((poi) => poi.id));
const localizedIds = new Set([...curatedIds, ...Object.keys(generated)]);
const resolvedId = (id) => legacyIds.get(id) || id;
const routeIds = new Set(
  routes.flatMap((route) => route.nodes.map((node) => node.poi_id)),
);
const portIds = new Set(ports.map((port) => port.poi_id));

const unresolvedRouteIds = [...routeIds].filter(
  (id) => !knownIds.has(id) && !knownIds.has(resolvedId(id)) && !localizedIds.has(resolvedId(id)),
);
const untranslatedRouteIds = [...routeIds].filter(
  (id) => !localizedIds.has(id) && !localizedIds.has(resolvedId(id)),
);
const untranslatedPortIds = [...portIds].filter(
  (id) => !localizedIds.has(id) && !localizedIds.has(resolvedId(id)),
);
const invalidNames = pois.filter(
  (poi) => !poi.name_zh?.trim() || poi.name_zh.trim() === poi.id,
);
const generatedNamesWithHan = Object.entries(generated).filter(([, names]) =>
  /[\u3400-\u9fff]/.test(`${names.en || ""}${names.pt || ""}`),
);
const usesIdentifierFallback = /Macau place[^\n]+replace\(\/\^poi_\//.test(
  localizationSource,
);

const errors = [
  unresolvedRouteIds.length && `Route IDs missing from POI data: ${unresolvedRouteIds.join(", ")}`,
  untranslatedRouteIds.length &&
    `Route IDs missing foreign names: ${untranslatedRouteIds.join(", ")}`,
  untranslatedPortIds.length &&
    `Port IDs missing foreign names: ${untranslatedPortIds.join(", ")}`,
  invalidNames.length &&
    `POIs missing real source names: ${invalidNames.map((poi) => poi.id).join(", ")}`,
  generatedNamesWithHan.length &&
    `Generated foreign names still contain Han characters: ${generatedNamesWithHan
      .map(([id]) => id)
      .join(", ")}`,
  usesIdentifierFallback && "localizedPoiName still exposes an internal POI identifier fallback",
].filter(Boolean);

console.log(
  JSON.stringify(
    {
      poiCount: pois.length,
      localizedForeignNameCount: pois.filter((poi) => localizedIds.has(poi.id)).length,
      sourceNameFallbackCount: pois.filter((poi) => !localizedIds.has(poi.id)).length,
      routePoiCount: routeIds.size,
      portCount: portIds.size,
      errors,
    },
    null,
    2,
  ),
);

if (errors.length) process.exitCode = 1;
