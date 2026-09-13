import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

// Exercise the actual TypeScript resolver without adding a frontend test runtime.
const source = await readFile(
  new URL("../src/features/story/assets/storyAssetManifest.ts", import.meta.url),
  "utf8",
);
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
});
const { resolveStoryAsset, STORY_ASSET_MANIFEST } = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`
);
const languages = ["zh-CN", "zh-TW", "en", "pt"];
const stories = await Promise.all(
  ["lotus_city_double_map", "taipa_letters", "coloane_after_tide"].map(async (id) => {
    const json = await readFile(new URL(`../../data/stories/${id}.json`, import.meta.url), "utf8");
    return { id, assetIds: new Set(json.match(/(?:V4|TAI|CAT)-[A-Z0-9-]+/g)) };
  }),
);
const coloaneAssets = stories[2].assetIds;
const otherStoryAssets = new Set(stories.slice(0, 2).flatMap(({ assetIds }) => [...assetIds]));
const coloaneExclusiveAssets = new Set([...coloaneAssets].filter((id) => !otherStoryAssets.has(id)));
const localizedAssets = [...STORY_ASSET_MANIFEST.values()].filter(
  ({ id }) => /^(V4|TAI)-/.test(id),
);

test("Lotus, Taipa and shared portrait labels support four languages", () => {
  assert.ok(localizedAssets.length >= 68);
  for (const item of localizedAssets) {
    assert.strictEqual(resolveStoryAsset(item.id), item);
    for (const language of languages) {
      const localized = resolveStoryAsset(item.id, language);
      assert.ok(localized.fallbackLabel.trim(), `${item.id}: ${language}`);
      if (language === "en" || language === "pt") {
        assert.doesNotMatch(localized.fallbackLabel, /[\u3400-\u9fff]/, item.id);
        assert.notEqual(localized.fallbackLabel, item.fallbackLabel, item.id);
      }
      // Localization must not change image URLs, ratios, positions or attribution.
      assert.deepEqual({ ...localized, fallbackLabel: item.fallbackLabel }, item);
    }
    assert.strictEqual(resolveStoryAsset(item.id, "zh-CN"), item);
  }
});

test("all referenced assets are registered; only Coloane-exclusive labels are untouched", () => {
  for (const story of stories) {
    for (const id of story.assetIds) assert.ok(resolveStoryAsset(id), `${story.id}: ${id}`);
  }
  const excluded = [...STORY_ASSET_MANIFEST.keys()].filter(
    (id) => coloaneExclusiveAssets.has(id) || id.startsWith("CAT-"),
  );
  for (const id of excluded) {
    for (const language of languages) {
      assert.strictEqual(resolveStoryAsset(id, language), STORY_ASSET_MANIFEST.get(id));
    }
  }
});

test("portraits shared with Coloane use the same localization as the other routes", () => {
  const sharedIds = [...coloaneAssets].filter((id) => otherStoryAssets.has(id));
  assert.ok(sharedIds.length > 0);
  for (const id of sharedIds) {
    for (const language of ["en", "pt"]) {
      assert.doesNotMatch(resolveStoryAsset(id, language).fallbackLabel, /[\u3400-\u9fff]/);
    }
  }
  const expected = {
    "zh-CN": "阿莲正在查找资料",
    "zh-TW": "阿蓮正在查找資料",
    en: "A Lin is checking the sources",
    pt: "A Lin está a consultar fontes",
  };
  for (const language of languages) {
    assert.equal(resolveStoryAsset("V4-CHAR-02", language).fallbackLabel, expected[language]);
  }
});

test("map collection captions follow locale changes without mutating the manifest", () => {
  const expected = {
    "V4-PROP-03": ["兩張澳門舊圖", "Two old maps of Macau", "Dois mapas antigos de Macau"],
    "V4-PROP-04": ["六組地點局部圖", "Six pairs of local maps", "Seis pares de mapas locais"],
    "V4-PROP-05": [
      "迎光重合的五張紙條",
      "Five notes held together against the light",
      "Cinco bilhetes sobrepostos à luz",
    ],
    "TAI-COVER-01": [
      "氹仔舊城與龍環葡韻景觀",
      "Taipa’s old town and the Taipa Houses",
      "O centro antigo da Taipa e as Casas da Taipa",
    ],
    "TAI-PROP-01": [
      "退信盒劇情道具",
      "The returned-letter box — a story prop",
      "A caixa de cartas devolvidas — um objeto da história",
    ],
  };
  for (const [id, labels] of Object.entries(expected)) {
    for (const [index, language] of ["zh-TW", "en", "pt"].entries()) {
      assert.equal(resolveStoryAsset(id, language).fallbackLabel, labels[index]);
    }
    assert.strictEqual(resolveStoryAsset(id), STORY_ASSET_MANIFEST.get(id));
  }
});

test("unknown assets and unsupported locales retain the existing fallback", () => {
  assert.equal(resolveStoryAsset("MISSING", "en"), undefined);
  assert.strictEqual(resolveStoryAsset("TAI-COVER-01", "invalid"), resolveStoryAsset("TAI-COVER-01"));
});
