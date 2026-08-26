import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "..",
);
const repositoryRoot = path.resolve(frontendRoot, "..");
const publicAssetRoot = path.join(frontendRoot, "public", "story", "v4");
const manifestPath = path.join(
  frontendRoot,
  "src",
  "features",
  "story",
  "assets",
  "storyAssetManifest.ts",
);
const specificationPath = path.join(
  repositoryRoot,
  "docs",
  "story-v4",
  "03-竖屏生图编号与提示词清单.md",
);

async function collectImagePaths(directory, relativeDirectory = "") {
  const entries = await readdir(directory, { withFileTypes: true });
  const paths = [];

  for (const entry of entries) {
    const relativePath = path.posix.join(relativeDirectory, entry.name);
    const absolutePath = path.join(directory, entry.name);

    if (entry.isDirectory()) {
      paths.push(...(await collectImagePaths(absolutePath, relativePath)));
      continue;
    }

    if (
      /\.(?:png|webp)$/i.test(entry.name) &&
      !entry.name.startsWith("_placeholder")
    ) {
      paths.push(relativePath);
    }
  }

  return paths;
}

function duplicateValues(values) {
  const seen = new Set();
  const duplicates = new Set();

  for (const value of values) {
    if (seen.has(value)) duplicates.add(value);
    seen.add(value);
  }

  return [...duplicates].sort();
}

function readImageSize(buffer, file) {
  if (
    buffer.length >= 24 &&
    buffer.subarray(0, 8).equals(
      Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    )
  ) {
    return {
      width: buffer.readUInt32BE(16),
      height: buffer.readUInt32BE(20),
    };
  }

  if (
    buffer.length >= 30 &&
    buffer.toString("ascii", 0, 4) === "RIFF" &&
    buffer.toString("ascii", 8, 12) === "WEBP"
  ) {
    const format = buffer.toString("ascii", 12, 16);

    if (format === "VP8X") {
      return {
        width: buffer.readUIntLE(24, 3) + 1,
        height: buffer.readUIntLE(27, 3) + 1,
      };
    }

    if (format === "VP8L") {
      const bits = buffer.readUInt32LE(21);
      return {
        width: (bits & 0x3fff) + 1,
        height: ((bits >> 14) & 0x3fff) + 1,
      };
    }

    if (format === "VP8 ") {
      const frameMarker = buffer.indexOf(
        Buffer.from([0x9d, 0x01, 0x2a]),
        20,
      );
      if (frameMarker >= 0 && buffer.length >= frameMarker + 7) {
        return {
          width: buffer.readUInt16LE(frameMarker + 3) & 0x3fff,
          height: buffer.readUInt16LE(frameMarker + 5) & 0x3fff,
        };
      }
    }
  }

  throw new Error(`无法读取图片尺寸：${file}`);
}

const [manifestSource, specificationSource, deliveredPaths] = await Promise.all([
  readFile(manifestPath, "utf8"),
  readFile(specificationPath, "utf8"),
  collectImagePaths(publicAssetRoot),
]);

const manifestEntries = [
  ...manifestSource.matchAll(
    /asset\(\s*"(?<id>V4-[A-Z0-9-]+)"\s*,\s*"(?<file>[^"]+)"\s*,\s*"(?<ratio>\d+\/\d+)"/g,
  ),
].map(({ groups }) => ({
  id: groups.id,
  file: groups.file,
  ratio: groups.ratio,
}));

const requiredIds = new Set(
  [
    ...specificationSource.matchAll(
      /`(?<id>V4-[A-Z0-9-]+)(?:_[^`]*)?`/g,
    ),
  ].map(({ groups }) => groups.id),
);
const manifestIds = manifestEntries.map(({ id }) => id);
const manifestFiles = manifestEntries.map(({ file }) => file);
const deliveredSet = new Set(deliveredPaths);
const manifestFileSet = new Set(manifestFiles);

const duplicateIds = duplicateValues(manifestIds);
const duplicateFiles = duplicateValues(manifestFiles);
const missingFiles = manifestEntries.filter(
  ({ file }) => !deliveredSet.has(file),
);
const unregisteredFiles = deliveredPaths
  .filter((file) => !manifestFileSet.has(file))
  .sort();
const missingRequiredIds = [...requiredIds]
  .filter((id) => !manifestIds.includes(id))
  .sort();
const filenameConflicts = manifestEntries.filter(({ id, file }) => {
  const filename = path.posix.basename(file);
  return !filename.startsWith(`${id}_`);
});
const dimensionChecks = await Promise.all(
  manifestEntries
    .filter(({ file }) => deliveredSet.has(file))
    .map(async ({ id, file, ratio }) => {
      const buffer = await readFile(path.join(publicAssetRoot, ...file.split("/")));
      const { width, height } = readImageSize(buffer, file);
      const [ratioWidth, ratioHeight] = ratio.split("/").map(Number);
      const expected = ratioWidth / ratioHeight;
      const actual = width / height;

      return {
        id,
        file,
        ratio,
        width,
        height,
        differs: Math.abs(actual - expected) / expected > 0.02,
      };
    }),
);
const ratioConflicts = dimensionChecks.filter(({ differs }) => differs);

const problems = [];
if (duplicateIds.length > 0) {
  problems.push(`重复资产编号：${duplicateIds.join(", ")}`);
}
if (duplicateFiles.length > 0) {
  problems.push(`重复文件映射：${duplicateFiles.join(", ")}`);
}
if (missingFiles.length > 0) {
  problems.push(
    `manifest 文件不存在：${missingFiles
      .map(({ id, file }) => `${id} -> ${file}`)
      .join(", ")}`,
  );
}
if (unregisteredFiles.length > 0) {
  problems.push(`未登记的正式素材：${unregisteredFiles.join(", ")}`);
}
if (missingRequiredIds.length > 0) {
  problems.push(`素材清单要求但未登记：${missingRequiredIds.join(", ")}`);
}
if (filenameConflicts.length > 0) {
  problems.push(
    `文件名与资产编号冲突：${filenameConflicts
      .map(({ id, file }) => `${id} -> ${file}`)
      .join(", ")}`,
  );
}
if (ratioConflicts.length > 0) {
  problems.push(
    `图片比例与 manifest 冲突：${ratioConflicts
      .map(
        ({ id, ratio, width, height }) =>
          `${id} 标记 ${ratio}，实际 ${width}x${height}`,
      )
      .join(", ")}`,
  );
}

if (problems.length > 0) {
  console.error("[story-v4-assets] FAIL");
  for (const problem of problems) console.error(`- ${problem}`);
  process.exitCode = 1;
} else {
  console.log(
    `[story-v4-assets] PASS：${manifestEntries.length} 个 manifest 条目、` +
      `${deliveredPaths.length} 个正式素材均已对应，文件比例正确，` +
      "未发现编号冲突或遗漏。",
  );
}
