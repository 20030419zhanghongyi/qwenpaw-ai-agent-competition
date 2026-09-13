import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ts from "typescript";

// Load the real TypeScript modules, including their relative imports, without a new runtime.
async function typeScriptModuleUrl(fileUrl) {
  const source = await readFile(fileUrl, "utf8");
  let { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
  });
  for (const [statement, quote, specifier] of outputText.matchAll(/from (["'])(\.[^"']+)\1/g)) {
    const dependencyUrl = await typeScriptModuleUrl(new URL(`${specifier}.ts`, fileUrl));
    outputText = outputText.replace(statement, `from ${quote}${dependencyUrl}${quote}`);
  }
  return `data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`;
}

const [imageTextModule, manifestModule] = await Promise.all(
  ["storyImageText", "storyAssetManifest"].map(async (name) =>
    import(await typeScriptModuleUrl(
      new URL(`../src/features/story/assets/${name}.ts`, import.meta.url),
    )),
  ),
);
const { STORY_IMAGE_TEXT, resolveStoryImageText } = imageTextModule;
const { STORY_ASSET_MANIFEST } = manifestModule;
const languages = ["zh-CN", "zh-TW", "en", "pt"];

test("transcribed assets exist in the manifest and have matching nonempty paragraphs in four languages", () => {
  // These visually checked notes and maps must not disappear during later content edits.
  for (const id of [
    "V4-PROP-02", "V4-PROP-03", "V4-PROP-05", "V4-PRO-03",
    "V4-AMA-03", "V4-AMA-04", "V4-MAN-04", "V4-MAN-05", "V4-SEN-04",
    "V4-SAM-02", "V4-SAM-03", "V4-SAM-04", "V4-SAM-05",
    "V4-LOU-03", "V4-LOU-04", "V4-LOU-06", "V4-FOR-03", "V4-FOR-05", "V4-FOR-06",
  ]) {
    assert.ok(STORY_IMAGE_TEXT[id], `${id}: missing image text`);
  }
  for (const [id, localized] of Object.entries(STORY_IMAGE_TEXT)) {
    assert.ok(STORY_ASSET_MANIFEST.has(id), `${id}: unregistered asset`);
    assert.deepEqual(Object.keys(localized).sort(), [...languages].sort(), id);
    const paragraphCount = localized["zh-CN"].length;
    assert.ok(paragraphCount > 0, `${id}: no paragraphs`);
    for (const language of languages) {
      const paragraphs = resolveStoryImageText(id, language);
      assert.ok(Array.isArray(paragraphs), `${id}: ${language}`);
      assert.equal(paragraphs.length, paragraphCount, `${id}: ${language} paragraph count`);
      for (const paragraph of paragraphs) {
        assert.equal(typeof paragraph, "string", `${id}: ${language}`);
        assert.ok(paragraph.trim(), `${id}: ${language} empty paragraph`);
      }
    }
  }
});

test("English and Portuguese image text contains no untranslated Chinese lettering", () => {
  for (const id of Object.keys(STORY_IMAGE_TEXT)) {
    for (const language of ["en", "pt"]) {
      for (const paragraph of resolveStoryImageText(id, language)) {
        assert.doesNotMatch(paragraph, /\p{Script=Han}/u, `${id}: ${language}`);
      }
    }
  }
});

test("unknown assets, text-free illustrations and other routes have no added image text", () => {
  const otherRouteIds = [...STORY_ASSET_MANIFEST.keys()].filter((id) => /^(TAI|CAT)-/.test(id));
  assert.ok(otherRouteIds.length > 0);
  const excludedIds = [
    "V4-DOES-NOT-EXIST", "V4-AMA-05", "V4-MAN-01", "V4-MAN-02",
    "V4-MAN-03", "V4-MAN-06", "V4-SEN-02", "V4-SEN-05", ...otherRouteIds,
  ];
  for (const id of excludedIds) {
    for (const language of languages) {
      assert.equal(resolveStoryImageText(id, language), undefined, `${id}: ${language}`);
    }
  }
});

test("identical Chinese passages retain the same translations wherever the images repeat them", () => {
  const seen = new Map();
  let duplicates = 0;
  for (const [id, localized] of Object.entries(STORY_IMAGE_TEXT)) {
    for (const [index, chinese] of localized["zh-CN"].entries()) {
      const translations = languages.map((language) => localized[language][index]);
      const previous = seen.get(chinese);
      if (previous) {
        assert.deepEqual(translations, previous.translations, `${id} / ${previous.id}: ${chinese}`);
        duplicates += 1;
      } else {
        seen.set(chinese, { id, translations });
      }
    }
  }
  assert.ok(duplicates > 0, "expected repeated passages across the story images");
});
