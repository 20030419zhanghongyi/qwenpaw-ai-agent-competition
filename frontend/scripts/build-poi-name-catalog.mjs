import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { pinyin } from "pinyin-pro";

const frontendRoot = path.resolve(import.meta.dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const officialPaths = process.argv.slice(2, 4);
const osmPath = process.argv[4];

if (officialPaths.length !== 2 || !osmPath) {
  throw new Error(
    "Usage: node scripts/build-poi-name-catalog.mjs <official-page-1.json> <official-page-2.json> <osm.json>",
  );
}

const readJson = (file) => JSON.parse(fs.readFileSync(file, "utf8"));
const pois = readJson(path.join(repoRoot, "data/pois.json")).pois;
const localizationSource = fs.readFileSync(
  path.join(frontendRoot, "src/lib/poiLocalization.ts"),
  "utf8",
);
const traditionalToSimplified = {};
for (const match of localizationSource.matchAll(
  /([\p{Script=Han}]): "([\p{Script=Han}])"/gu,
)) {
  traditionalToSimplified[match[2]] = match[1];
}

const simplify = (value) =>
  [...String(value || "")]
    .map((character) => traditionalToSimplified[character] || character)
    .join("");
const normalizeName = (value) =>
  simplify(String(value || "").normalize("NFKC"))
    .replace(/^澳门/, "")
    .replace(/\([^)]*\)|（[^）]*）/g, "")
    .replace(/[\s·/／\-—_.]/g, "")
    .replace(/[A-Za-zÀ-ž0-9'.,:;ºª]+/g, "")
    .toLowerCase();
const clean = (value) => String(value || "").replace(/\r?\n/g, " ").trim();
const romanize = (value) => {
  const prepared = String(value || "")
    .replace(/^澳门/, "Macao ")
    .replace(/^氹仔/, "Taipa ")
    .replace(/^路环/, "Coloane ");
  return pinyin(prepared, {
    toneType: "none",
    type: "array",
    nonZh: "consecutive",
  })
    .map((token) => token.trim())
    .filter((token) => /[A-Za-z0-9À-ž]/.test(token))
    .map((token) =>
      /^[a-zà-ž]+$/.test(token)
        ? `${token.charAt(0).toUpperCase()}${token.slice(1)}`
        : token,
    )
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
};

const officialRows = officialPaths.flatMap((file) => readJson(file).features || []);
const officialByName = new Map();
for (const feature of officialRows) {
  const attributes = feature.attributes || {};
  for (const sourceName of [attributes.CFULL, attributes.CNFULL]) {
    const key = normalizeName(sourceName);
    if (key) officialByName.set(key, attributes);
  }
}

const osmRows = (readJson(osmPath).elements || []).filter(
  (element) => element.tags && (element.tags["name:en"] || element.tags["name:pt"]),
);

function transformLatitude(x, y) {
  let result = -100 + 2 * x + 3 * y + 0.2 * y ** 2 + 0.1 * x * y;
  result += 0.2 * Math.sqrt(Math.abs(x));
  result += ((20 * Math.sin(6 * x * Math.PI) + 20 * Math.sin(2 * x * Math.PI)) * 2) / 3;
  result += ((20 * Math.sin(y * Math.PI) + 40 * Math.sin((y / 3) * Math.PI)) * 2) / 3;
  result += ((160 * Math.sin((y / 12) * Math.PI) + 320 * Math.sin((y * Math.PI) / 30)) * 2) / 3;
  return result;
}

function transformLongitude(x, y) {
  let result = 300 + x + 2 * y + 0.1 * x ** 2 + 0.1 * x * y;
  result += 0.1 * Math.sqrt(Math.abs(x));
  result += ((20 * Math.sin(6 * x * Math.PI) + 20 * Math.sin(2 * x * Math.PI)) * 2) / 3;
  result += ((20 * Math.sin(x * Math.PI) + 40 * Math.sin((x / 3) * Math.PI)) * 2) / 3;
  result += ((150 * Math.sin((x / 12) * Math.PI) + 300 * Math.sin((x / 30) * Math.PI)) * 2) / 3;
  return result;
}

function gcj02ToWgs84(latitude, longitude) {
  const earthRadius = 6378245;
  const eccentricity = 0.006693421622965943;
  const deltaLatitude = transformLatitude(longitude - 105, latitude - 35);
  const deltaLongitude = transformLongitude(longitude - 105, latitude - 35);
  const radians = (latitude / 180) * Math.PI;
  const magic = 1 - eccentricity * Math.sin(radians) ** 2;
  const squareRoot = Math.sqrt(magic);
  const adjustedLatitude =
    latitude +
    (deltaLatitude * 180) /
      (((earthRadius * (1 - eccentricity)) / (magic * squareRoot)) * Math.PI);
  const adjustedLongitude =
    longitude +
    (deltaLongitude * 180) /
      (((earthRadius / squareRoot) * Math.cos(radians)) * Math.PI);
  return [latitude * 2 - adjustedLatitude, longitude * 2 - adjustedLongitude];
}

function distanceMeters(latitudeA, longitudeA, latitudeB, longitudeB) {
  const radians = Math.PI / 180;
  const x =
    (longitudeB - longitudeA) *
    radians *
    Math.cos(((latitudeA + latitudeB) * radians) / 2);
  const y = (latitudeB - latitudeA) * radians;
  return 6371000 * Math.hypot(x, y);
}

function nearestExactOsmMatch(poi) {
  const key = normalizeName(poi.name_zh);
  if (!key) return null;
  const [latitude, longitude] = gcj02ToWgs84(
    poi.coordinates.lat,
    poi.coordinates.lng,
  );
  return osmRows
    .filter((element) =>
      [
        element.tags["name:zh"],
        element.tags["name:zh-Hans"],
        element.tags["name:zh-Hant"],
        element.tags.name,
      ].some((name) => normalizeName(name) === key),
    )
    .map((element) => ({
      element,
      distance: distanceMeters(
        latitude,
        longitude,
        element.lat || element.center?.lat,
        element.lon || element.center?.lon,
      ),
    }))
    .sort((left, right) => left.distance - right.distance)[0]?.element;
}

const portPortugueseNames = {
  poi_port_guanja: "Posto Fronteiriço das Portas do Cerco",
  poi_port_qingmao: "Posto Fronteiriço Qingmao",
  poi_port_hengqin: "Posto Fronteiriço de Hengqin",
  poi_port_hzmb: "Posto Fronteiriço da Ponte Hong Kong-Zhuhai-Macau",
  poi_port_outer_harbor: "Terminal Marítimo do Porto Exterior",
  poi_0071: "Terminal Marítimo do Porto Interior",
};

const names = {};
for (const poi of pois) {
  const official = officialByName.get(normalizeName(poi.name_zh));
  const osm = nearestExactOsmMatch(poi)?.tags || {};
  const officialEnglish = clean(official?.EFULL);
  const officialPortuguese = clean(official?.PFULL || official?.PFULL_Unicode);
  const english = clean(
    poi.name_en || osm["name:en"] || officialEnglish || osm["name:pt"] || romanize(poi.name_zh),
  );
  const portuguese = clean(
    portPortugueseNames[poi.id] ||
      poi.name_pt ||
      osm["name:pt"] ||
      officialPortuguese ||
      osm["name:en"] ||
      english,
  );
  if (english || portuguese) names[poi.id] = { en: english, pt: portuguese };
}

const output = {
  _meta: {
    generated: true,
    sources: [
      "data/pois.json",
      "Macao Statistics and Census Service ArcGIS street-name layer",
      "OpenStreetMap contributors",
    ],
    policy:
      "Exact normalized Chinese-name matches use official or OSM names; GCJ-02 coordinates resolve duplicates. Remaining proper names use tone-free Hanyu Pinyin rather than exposing internal IDs or inventing translations.",
  },
  names,
};
fs.mkdirSync(path.join(frontendRoot, "src/data"), { recursive: true });
fs.writeFileSync(
  path.join(frontendRoot, "src/data/poiNames.generated.json"),
  `${JSON.stringify(output, null, 2)}\n`,
);
console.log(`Generated ${Object.keys(names).length} localized POI entries.`);
