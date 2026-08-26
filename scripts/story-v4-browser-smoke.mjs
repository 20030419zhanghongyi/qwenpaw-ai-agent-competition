#!/usr/bin/env node

/**
 * Real-browser smoke test for the StoryWalk V4 happy path.
 *
 * This script intentionally uses only Node.js built-in modules. It launches an
 * installed Chrome, Edge, or Chromium instance and drives it through the Chrome
 * DevTools Protocol (CDP).
 *
 * Required environment variables:
 *   STORY_TEST_EMAIL
 *   STORY_TEST_PASSWORD
 *   STORY_SCREENSHOT_DIR
 *
 * Optional environment variables:
 *   STORY_BASE_URL       Defaults to http://localhost:5173
 *   STORY_BROWSER_PATH   Explicit Chrome/Edge/Chromium executable
 *   STORY_TIMEOUT_MS     Per-step timeout, defaults to 20000
 */

import { createHash, randomBytes } from "node:crypto";
import { existsSync } from "node:fs";
import {
  mkdir,
  mkdtemp,
  readFile,
  rm,
  writeFile,
} from "node:fs/promises";
import http from "node:http";
import https from "node:https";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import { once } from "node:events";

const STORY_ID = "lotus_city_double_map";
const EXPECTED_NODES = [
  { id: "chapter_ama", name: "妈阁庙" },
  { id: "chapter_mandarin_house", name: "郑家大屋" },
  { id: "chapter_senado", name: "议事亭前地" },
  { id: "chapter_sam_kai", name: "三街会馆" },
  { id: "chapter_lou_kau", name: "卢家大屋" },
  { id: "chapter_mount_fortress", name: "大炮台" },
];
const SESSION_STORAGE_KEY = "macau-storywalk-story-session-id";
const AUTH_TOKEN_KEY = "macau-storywalk-auth-token";
const INVITATION_STORAGE_PREFIX = "macau-storywalk-invitation-";
const DEFAULT_BASE_URL = "http://localhost:5173";
const DEFAULT_TIMEOUT_MS = 20_000;
const POLL_INTERVAL_MS = 150;

const email = requiredEnv("STORY_TEST_EMAIL");
const password = requiredEnv("STORY_TEST_PASSWORD");
const [emailLocalPart, emailDomain = "example.test"] = email.split("@");
const switchedAccountEmail =
  `${emailLocalPart}.switch.${Date.now()}@${emailDomain}`;
const screenshotDir = path.resolve(requiredEnv("STORY_SCREENSHOT_DIR"));
const baseUrl = normalizeBaseUrl(
  process.env.STORY_BASE_URL?.trim() || DEFAULT_BASE_URL,
);
const timeoutMs = positiveInteger(
  process.env.STORY_TIMEOUT_MS,
  DEFAULT_TIMEOUT_MS,
  "STORY_TIMEOUT_MS",
);
const skipPreferenceEntry =
  process.env.STORY_SKIP_PREFERENCE_ENTRY?.trim() === "1";

let browserProcess = null;
let browserProfileDir = null;
let cdp = null;
let cleanupStarted = false;
let interrupted = false;

function requiredEnv(name) {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(`缺少必需环境变量 ${name}`);
  }
  return value;
}

function normalizeBaseUrl(value) {
  const url = new URL(value);
  if (!["http:", "https:"].includes(url.protocol)) {
    throw new Error("STORY_BASE_URL 必须使用 http:// 或 https://");
  }
  url.pathname = url.pathname.replace(/\/+$/, "");
  url.search = "";
  url.hash = "";
  return url.toString().replace(/\/$/, "");
}

function positiveInteger(rawValue, fallback, name) {
  if (!rawValue) return fallback;
  const value = Number(rawValue);
  if (!Number.isSafeInteger(value) || value <= 0) {
    throw new Error(`${name} 必须是正整数`);
  }
  return value;
}

function sleep(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function log(message) {
  process.stdout.write(`[story-v4-smoke] ${message}\n`);
}

function normalizeText(value) {
  return String(value ?? "")
    .replace(/\s+/g, " ")
    .trim();
}

function executableNames() {
  if (process.platform === "win32") {
    return ["chrome.exe", "msedge.exe", "chromium.exe"];
  }
  return [
    "google-chrome",
    "google-chrome-stable",
    "microsoft-edge",
    "microsoft-edge-stable",
    "chromium",
    "chromium-browser",
  ];
}

function pathCandidates() {
  const candidates = [];
  const explicit = process.env.STORY_BROWSER_PATH?.trim();
  if (explicit) candidates.push(explicit);

  if (process.platform === "win32") {
    const roots = [
      process.env.PROGRAMFILES,
      process.env["PROGRAMFILES(X86)"],
      process.env.LOCALAPPDATA,
    ].filter(Boolean);
    for (const root of roots) {
      candidates.push(
        path.join(root, "Google", "Chrome", "Application", "chrome.exe"),
        path.join(root, "Microsoft", "Edge", "Application", "msedge.exe"),
        path.join(root, "Chromium", "Application", "chrome.exe"),
      );
    }
  } else if (process.platform === "darwin") {
    const applicationRoots = [
      "/Applications",
      path.join(os.homedir(), "Applications"),
    ];
    for (const root of applicationRoots) {
      candidates.push(
        path.join(
          root,
          "Google Chrome.app",
          "Contents",
          "MacOS",
          "Google Chrome",
        ),
        path.join(
          root,
          "Microsoft Edge.app",
          "Contents",
          "MacOS",
          "Microsoft Edge",
        ),
        path.join(root, "Chromium.app", "Contents", "MacOS", "Chromium"),
      );
    }
  }

  const pathEntries = (process.env.PATH ?? "")
    .split(path.delimiter)
    .filter(Boolean);
  for (const directory of pathEntries) {
    for (const name of executableNames()) {
      candidates.push(path.join(directory, name));
    }
  }
  return [...new Set(candidates.map((candidate) => path.resolve(candidate)))];
}

function findBrowserExecutable() {
  const found = pathCandidates().find((candidate) => existsSync(candidate));
  if (!found) {
    throw new Error(
      "未找到 Chrome、Edge 或 Chromium。可通过 STORY_BROWSER_PATH 指定浏览器可执行文件。",
    );
  }
  return found;
}

function safeTemporaryProfilePath(candidate) {
  const root = path.resolve(os.tmpdir());
  const resolved = path.resolve(candidate);
  const relative = path.relative(root, resolved);
  if (
    !relative ||
    relative === ".." ||
    relative.startsWith(`..${path.sep}`) ||
    path.isAbsolute(relative)
  ) {
    throw new Error(`拒绝清理系统临时目录之外的浏览器 profile：${resolved}`);
  }
  return resolved;
}

async function launchBrowser(executable) {
  browserProfileDir = await mkdtemp(
    path.join(os.tmpdir(), "story-v4-browser-smoke-"),
  );
  safeTemporaryProfilePath(browserProfileDir);

  const args = [
    "--headless=new",
    "--remote-debugging-port=0",
    `--user-data-dir=${browserProfileDir}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-default-apps",
    "--disable-extensions",
    "--disable-features=Translate,MediaRouter,OptimizationHints",
    "--disable-popup-blocking",
    "--disable-sync",
    "--hide-scrollbars",
    "--mute-audio",
    "--window-size=390,844",
    "about:blank",
  ];
  if (process.platform === "linux" && process.getuid?.() === 0) {
    args.push("--no-sandbox");
  }

  const stderrChunks = [];
  browserProcess = spawn(executable, args, {
    stdio: ["ignore", "ignore", "pipe"],
    windowsHide: true,
  });
  browserProcess.stderr?.on("data", (chunk) => {
    stderrChunks.push(String(chunk));
    if (stderrChunks.length > 20) stderrChunks.shift();
  });

  const activePortFile = path.join(browserProfileDir, "DevToolsActivePort");
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (
      browserProcess.exitCode !== null ||
      browserProcess.signalCode !== null
    ) {
      throw new Error(
        `浏览器提前退出（${browserProcess.exitCode}）\n${stderrChunks.join("")}`,
      );
    }
    try {
      const [portLine] = (await readFile(activePortFile, "utf8"))
        .trim()
        .split(/\r?\n/);
      const port = Number(portLine);
      if (Number.isInteger(port) && port > 0) {
        return port;
      }
    } catch {
      // Chrome writes DevToolsActivePort after its profile is initialized.
    }
    await sleep(POLL_INTERVAL_MS);
  }
  throw new Error(
    `等待浏览器 CDP 端口超时\n${stderrChunks.join("")}`,
  );
}

function httpRequestJson(url, method = "GET") {
  return new Promise((resolve, reject) => {
    const transport = new URL(url).protocol === "https:" ? https : http;
    const request = transport.request(url, { method }, (response) => {
      const chunks = [];
      response.on("data", (chunk) => chunks.push(chunk));
      response.on("end", () => {
        const body = Buffer.concat(chunks).toString("utf8");
        if (
          response.statusCode === undefined ||
          response.statusCode < 200 ||
          response.statusCode >= 300
        ) {
          reject(
            new Error(
              `${method} ${url} 返回 ${response.statusCode ?? "未知状态"}：${body}`,
            ),
          );
          return;
        }
        try {
          resolve(JSON.parse(body));
        } catch (error) {
          reject(new Error(`无法解析 ${url} 的 JSON：${error.message}`));
        }
      });
    });
    request.once("error", reject);
    request.end();
  });
}

function httpStatus(url) {
  return new Promise((resolve, reject) => {
    const transport = new URL(url).protocol === "https:" ? https : http;
    const request = transport.get(url, (response) => {
      response.resume();
      response.once("end", () => resolve(response.statusCode ?? 0));
    });
    request.once("error", reject);
  });
}

async function waitForFrontend() {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const status = await httpStatus(baseUrl);
      if (status >= 200 && status < 500) return;
      lastError = new Error(`${baseUrl} 返回 HTTP ${status}`);
    } catch (error) {
      lastError = error;
    }
    await sleep(300);
  }
  throw new Error(
    `前端在 ${baseUrl} 不可访问：${lastError?.message ?? "连接超时"}`,
  );
}

async function findPageWebSocket(port) {
  const endpoint = `http://127.0.0.1:${port}`;
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const targets = await httpRequestJson(`${endpoint}/json/list`);
      const page = targets.find(
        (target) => target.type === "page" && target.webSocketDebuggerUrl,
      );
      if (page) return page.webSocketDebuggerUrl;
    } catch {
      // CDP HTTP endpoint may need a short moment after the port file appears.
    }
    await sleep(POLL_INTERVAL_MS);
  }
  throw new Error("浏览器没有提供可用的 CDP page target");
}

class RawWebSocket {
  constructor(url) {
    this.url = new URL(url);
    this.socket = null;
    this.buffer = Buffer.alloc(0);
    this.fragments = [];
    this.fragmentOpcode = null;
    this.open = false;
    this.messageHandlers = new Set();
    this.closeHandlers = new Set();
  }

  async connect() {
    if (this.url.protocol !== "ws:") {
      throw new Error(`只支持本地 ws:// CDP 地址，收到 ${this.url.protocol}`);
    }
    const host = this.url.hostname;
    const port = Number(this.url.port || 80);
    const key = randomBytes(16).toString("base64");
    const expectedAccept = createHash("sha1")
      .update(`${key}258EAFA5-E914-47DA-95CA-C5AB0DC85B11`)
      .digest("base64");

    this.socket = net.createConnection({ host, port });
    await once(this.socket, "connect");
    const requestPath = `${this.url.pathname}${this.url.search}`;
    this.socket.write(
      [
        `GET ${requestPath} HTTP/1.1`,
        `Host: ${host}:${port}`,
        "Upgrade: websocket",
        "Connection: Upgrade",
        `Sec-WebSocket-Key: ${key}`,
        "Sec-WebSocket-Version: 13",
        "\r\n",
      ].join("\r\n"),
    );

    const handshake = await new Promise((resolve, reject) => {
      let received = Buffer.alloc(0);
      const onError = (error) => {
        cleanup();
        reject(error);
      };
      const onData = (chunk) => {
        received = Buffer.concat([received, chunk]);
        const boundary = received.indexOf("\r\n\r\n");
        if (boundary === -1) return;
        cleanup();
        resolve({
          headers: received.subarray(0, boundary).toString("utf8"),
          remaining: received.subarray(boundary + 4),
        });
      };
      const cleanup = () => {
        this.socket.off("error", onError);
        this.socket.off("data", onData);
      };
      this.socket.on("error", onError);
      this.socket.on("data", onData);
    });

    const statusLine = handshake.headers.split(/\r?\n/, 1)[0];
    const acceptHeader = handshake.headers
      .split(/\r?\n/)
      .find((line) => /^sec-websocket-accept:/i.test(line))
      ?.split(":")
      .slice(1)
      .join(":")
      .trim();
    if (!statusLine.includes("101") || acceptHeader !== expectedAccept) {
      throw new Error(`CDP WebSocket 握手失败：${statusLine}`);
    }

    this.open = true;
    this.socket.on("data", (chunk) => this.consume(chunk));
    this.socket.on("error", (error) => this.emitClose(error));
    this.socket.on("close", () => this.emitClose(new Error("CDP WebSocket 已关闭")));
    if (handshake.remaining.length > 0) this.consume(handshake.remaining);
  }

  onMessage(handler) {
    this.messageHandlers.add(handler);
  }

  onClose(handler) {
    this.closeHandlers.add(handler);
  }

  sendText(text) {
    this.sendFrame(0x1, Buffer.from(text, "utf8"));
  }

  sendFrame(opcode, payload = Buffer.alloc(0)) {
    if (!this.open || !this.socket) {
      throw new Error("CDP WebSocket 尚未连接");
    }
    const mask = randomBytes(4);
    let lengthBytes;
    if (payload.length < 126) {
      lengthBytes = Buffer.from([0x80 | payload.length]);
    } else if (payload.length <= 0xffff) {
      lengthBytes = Buffer.alloc(3);
      lengthBytes[0] = 0x80 | 126;
      lengthBytes.writeUInt16BE(payload.length, 1);
    } else {
      lengthBytes = Buffer.alloc(9);
      lengthBytes[0] = 0x80 | 127;
      lengthBytes.writeBigUInt64BE(BigInt(payload.length), 1);
    }
    const masked = Buffer.alloc(payload.length);
    for (let index = 0; index < payload.length; index += 1) {
      masked[index] = payload[index] ^ mask[index % 4];
    }
    this.socket.write(
      Buffer.concat([Buffer.from([0x80 | opcode]), lengthBytes, mask, masked]),
    );
  }

  consume(chunk) {
    this.buffer = Buffer.concat([this.buffer, chunk]);
    while (this.buffer.length >= 2) {
      const first = this.buffer[0];
      const second = this.buffer[1];
      const fin = Boolean(first & 0x80);
      const opcode = first & 0x0f;
      const masked = Boolean(second & 0x80);
      let payloadLength = second & 0x7f;
      let offset = 2;

      if (payloadLength === 126) {
        if (this.buffer.length < offset + 2) return;
        payloadLength = this.buffer.readUInt16BE(offset);
        offset += 2;
      } else if (payloadLength === 127) {
        if (this.buffer.length < offset + 8) return;
        const bigLength = this.buffer.readBigUInt64BE(offset);
        if (bigLength > BigInt(Number.MAX_SAFE_INTEGER)) {
          this.emitClose(new Error("CDP WebSocket 帧过大"));
          return;
        }
        payloadLength = Number(bigLength);
        offset += 8;
      }

      let mask = null;
      if (masked) {
        if (this.buffer.length < offset + 4) return;
        mask = this.buffer.subarray(offset, offset + 4);
        offset += 4;
      }
      if (this.buffer.length < offset + payloadLength) return;

      const payload = Buffer.from(
        this.buffer.subarray(offset, offset + payloadLength),
      );
      this.buffer = this.buffer.subarray(offset + payloadLength);
      if (mask) {
        for (let index = 0; index < payload.length; index += 1) {
          payload[index] ^= mask[index % 4];
        }
      }
      this.handleFrame(opcode, fin, payload);
    }
  }

  handleFrame(opcode, fin, payload) {
    if (opcode === 0x8) {
      this.close();
      return;
    }
    if (opcode === 0x9) {
      this.sendFrame(0x0a, payload);
      return;
    }
    if (opcode === 0x0a) return;

    if (opcode === 0x1 || opcode === 0x2) {
      this.fragmentOpcode = opcode;
      this.fragments = [payload];
    } else if (opcode === 0x0 && this.fragmentOpcode !== null) {
      this.fragments.push(payload);
    } else {
      return;
    }

    if (!fin) return;
    const complete = Buffer.concat(this.fragments);
    const completeOpcode = this.fragmentOpcode;
    this.fragments = [];
    this.fragmentOpcode = null;
    if (completeOpcode === 0x1) {
      const text = complete.toString("utf8");
      for (const handler of this.messageHandlers) handler(text);
    }
  }

  emitClose(error) {
    if (!this.open) return;
    this.open = false;
    for (const handler of this.closeHandlers) handler(error);
  }

  close() {
    if (!this.socket) return;
    if (this.open) {
      try {
        this.sendFrame(0x8);
      } catch {
        // The browser may already have closed the socket.
      }
    }
    this.open = false;
    this.socket.destroy();
  }
}

class CdpClient {
  constructor(webSocketUrl) {
    this.webSocket = new RawWebSocket(webSocketUrl);
    this.nextId = 1;
    this.pending = new Map();
    this.eventHandlers = new Map();
  }

  async connect() {
    await this.webSocket.connect();
    this.webSocket.onMessage((text) => this.handleMessage(text));
    this.webSocket.onClose((error) => this.rejectAll(error));
  }

  on(method, handler) {
    const handlers = this.eventHandlers.get(method) ?? new Set();
    handlers.add(handler);
    this.eventHandlers.set(method, handlers);
    return () => handlers.delete(handler);
  }

  send(method, params = {}, commandTimeoutMs = timeoutMs) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`CDP 命令超时：${method}`));
      }, commandTimeoutMs);
      this.pending.set(id, { resolve, reject, timer, method });
      this.webSocket.sendText(JSON.stringify({ id, method, params }));
    });
  }

  handleMessage(text) {
    let message;
    try {
      message = JSON.parse(text);
    } catch {
      return;
    }
    if (message.id !== undefined) {
      const pending = this.pending.get(message.id);
      if (!pending) return;
      clearTimeout(pending.timer);
      this.pending.delete(message.id);
      if (message.error) {
        pending.reject(
          new Error(
            `${pending.method} 失败：${message.error.message ?? JSON.stringify(message.error)}`,
          ),
        );
      } else {
        pending.resolve(message.result ?? {});
      }
      return;
    }
    const handlers = this.eventHandlers.get(message.method);
    if (!handlers) return;
    for (const handler of handlers) {
      Promise.resolve(handler(message.params ?? {})).catch((error) => {
        log(`处理 CDP 事件 ${message.method} 失败：${error.message}`);
      });
    }
  }

  rejectAll(error) {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
  }

  close() {
    this.webSocket.close();
  }
}

async function evaluate(expression) {
  const response = await cdp.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
    userGesture: true,
  });
  if (response.exceptionDetails) {
    const description =
      response.exceptionDetails.exception?.description ??
      response.exceptionDetails.text ??
      "未知 JavaScript 异常";
    throw new Error(`页面脚本执行失败：${description}`);
  }
  return response.result?.value;
}

async function currentUrl() {
  return evaluate("location.href");
}

async function bodyText() {
  return evaluate("document.body?.innerText ?? ''");
}

async function waitFor(description, probe, waitMs = timeoutMs) {
  const deadline = Date.now() + waitMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const result = await probe();
      if (result) return result;
    } catch (error) {
      lastError = error;
    }
    await sleep(POLL_INTERVAL_MS);
  }
  const url = await currentUrl().catch(() => "无法读取");
  const text = normalizeText(await bodyText().catch(() => "")).slice(-800);
  throw new Error(
    `等待“${description}”超时。当前 URL：${url}` +
      `${lastError ? `；最后错误：${lastError.message}` : ""}` +
      `${text ? `；页面末尾：${text}` : ""}`,
  );
}

async function waitForReady() {
  await waitFor("页面加载完成", async () => {
    const state = await evaluate("document.readyState");
    return state === "interactive" || state === "complete";
  });
}

async function navigate(url) {
  await cdp.send("Page.navigate", { url });
  await waitForReady();
}

async function reload() {
  await cdp.send("Page.reload", { ignoreCache: true });
  await waitForReady();
}

function visibleElementsExpression(selector) {
  return `
    [...document.querySelectorAll(${JSON.stringify(selector)})].filter((element) => {
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      return rect.width > 0 && rect.height > 0 &&
        style.visibility !== "hidden" && style.display !== "none";
    })
  `;
}

async function hasAnyText(labels) {
  return evaluate(`(() => {
    const labels = ${JSON.stringify(labels)}.map((value) =>
      String(value).replace(/\\s+/g, " ").trim()
    );
    const elements = ${visibleElementsExpression(
      "button, a, summary, [role='button'], input[type='submit'], input[type='button']",
    )};
    return elements.some((element) => {
      const text = [
        element.innerText,
        element.value,
        element.getAttribute("aria-label"),
        element.title,
      ].filter(Boolean).join(" ").replace(/\\s+/g, " ").trim();
      return labels.some((label) => text === label || text.includes(label));
    });
  })()`);
}

async function clickAny(labels, { optional = false } = {}) {
  const expression = `(() => {
    const labels = ${JSON.stringify(labels)}.map((value) =>
      String(value).replace(/\\s+/g, " ").trim()
    );
    const elements = ${visibleElementsExpression(
      "button, a, summary, [role='button'], input[type='submit'], input[type='button']",
    )}.filter((element) =>
      !element.disabled && element.getAttribute("aria-disabled") !== "true"
    );
    const textOf = (element) => [
      element.innerText,
      element.value,
      element.getAttribute("aria-label"),
      element.title,
    ].filter(Boolean).join(" ").replace(/\\s+/g, " ").trim();
    let found = null;
    for (const label of labels) {
      found = elements.find((element) => textOf(element) === label);
      if (found) break;
    }
    if (!found) {
      for (const label of labels) {
        found = elements.find((element) => textOf(element).includes(label));
        if (found) break;
      }
    }
    if (!found) return null;
    found.scrollIntoView({ block: "center", inline: "center" });
    found.click();
    return textOf(found);
  })()`;
  const clicked = await evaluate(expression);
  if (!clicked && !optional) {
    throw new Error(`找不到可点击控件：${labels.join(" / ")}`);
  }
  if (clicked) log(`点击：${clicked}`);
  return clicked;
}

async function waitAndClick(labels, description = labels.join(" / ")) {
  return waitFor(description, () => clickAny(labels, { optional: true }));
}

async function fillInput(selector, value, description, index = 0) {
  const filled = await evaluate(`(() => {
    const element = document.querySelectorAll(
      ${JSON.stringify(selector)}
    )[${JSON.stringify(index)}];
    if (!element) return false;
    const setter = Object.getOwnPropertyDescriptor(
      element instanceof HTMLTextAreaElement
        ? HTMLTextAreaElement.prototype
        : HTMLInputElement.prototype,
      "value"
    )?.set;
    if (setter) setter.call(element, ${JSON.stringify(value)});
    else element.value = ${JSON.stringify(value)};
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  })()`);
  if (!filled) throw new Error(`找不到${description}`);
}

async function submitFirstForm() {
  const submitted = await evaluate(`(() => {
    const form = document.querySelector("form");
    if (!form) return false;
    form.requestSubmit();
    return true;
  })()`);
  if (!submitted) throw new Error("登录页不存在可提交表单");
}

async function screenshot(name) {
  const safeName = name.replace(/[^a-zA-Z0-9._-]+/g, "-");
  const result = await cdp.send(
    "Page.captureScreenshot",
    {
      format: "png",
      fromSurface: true,
      captureBeyondViewport: true,
    },
    Math.max(timeoutMs, 30_000),
  );
  const destination = path.join(screenshotDir, `${safeName}.png`);
  await writeFile(destination, Buffer.from(result.data, "base64"));
  log(`截图：${destination}`);
}

async function setMobileViewport(width, height) {
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: true,
    screenWidth: width,
    screenHeight: height,
  });
  await cdp.send("Emulation.setTouchEmulationEnabled", {
    enabled: true,
    maxTouchPoints: 5,
  });
  await sleep(150);
}

async function touchDrag(
  sourceSelector,
  targetSelector,
  description,
  scrollAnchorSelector = sourceSelector,
) {
  const points = await evaluate(`(() => {
    const source = document.querySelector(${JSON.stringify(sourceSelector)});
    const target = document.querySelector(${JSON.stringify(targetSelector)});
    const anchor = document.querySelector(
      ${JSON.stringify(scrollAnchorSelector)}
    );
    if (!source || !target || !anchor) return null;
    anchor.scrollIntoView({ block: "start", inline: "nearest" });
    const sourceRect = source.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    return {
      viewportHeight: window.innerHeight,
      source: {
        x: sourceRect.left + sourceRect.width / 2,
        y: sourceRect.top + sourceRect.height / 2,
      },
      target: {
        x: targetRect.left + targetRect.width / 2,
        y: Math.min(
          window.innerHeight - 56,
          targetRect.top + Math.min(70, targetRect.height / 2)
        ),
      },
    };
  })()`);
  if (!points) throw new Error(`拖动元素不存在：${description}`);
  if (
    points.source.y < 0 ||
    points.source.y > points.viewportHeight ||
    points.target.y < 0 ||
    points.target.y > points.viewportHeight
  ) {
    throw new Error(`拖动元素不在视口内：${description} ${JSON.stringify(points)}`);
  }

  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [{ ...points.source, id: 1, radiusX: 2, radiusY: 2 }],
  });
  await sleep(220);
  for (let step = 1; step <= 8; step += 1) {
    const ratio = step / 8;
    await cdp.send("Input.dispatchTouchEvent", {
      type: "touchMove",
      touchPoints: [
        {
          x: points.source.x + (points.target.x - points.source.x) * ratio,
          y: points.source.y + (points.target.y - points.source.y) * ratio,
          id: 1,
          radiusX: 2,
          radiusY: 2,
        },
      ],
    });
    await sleep(35);
  }
  await cdp.send("Input.dispatchTouchEvent", {
    type: "touchEnd",
    touchPoints: [],
  });
  await sleep(300);
  log(`触控拖动：${description}`);
}

async function testEvidenceChainInteraction() {
  const body = normalizeText(await bodyText());
  for (const expected of [
    "来源类型：交货方记录",
    "来源类型：收货方账簿",
    "来源类型：经手人存条",
  ]) {
    if (!body.includes(expected)) {
      throw new Error(`证据卡缺少来源信息：${expected}`);
    }
  }

  await clickAny(["查看大图：梁掌柜交货单对应材料"]);
  await waitFor(
    "证据图片放大层",
    () => evaluate('Boolean(document.querySelector("[aria-modal=true]"))'),
  );
  await clickAny(["关闭大图"]);

  await clickAny(["加入证据链"]);
  await clickAny(["加入证据链"]);
  const before = await evaluate(
    `[...document.querySelectorAll("[data-evidence-id]")]
      .map((element) => element.getAttribute("data-evidence-id"))`,
  );
  await touchDrag(
    '[aria-label="长按拖动梁掌柜交货单"]',
    '[data-evidence-id="store_ledger"]',
    "证据卡在 iOS 风格触控下排序",
  );
  const after = await evaluate(
    `[...document.querySelectorAll("[data-evidence-id]")]
      .map((element) => element.getAttribute("data-evidence-id"))`,
  );
  if (
    before.join(",") === after.join(",") ||
    after[0] !== "store_ledger" ||
    after[1] !== "delivery_order"
  ) {
    throw new Error(
      `证据链触控排序未生效：${before.join(",")} -> ${after.join(",")}`,
    );
  }
  await clickAny(["加入证据链"]);
  await screenshot("06-04-evidence-chain-enhanced");
}

async function testAssemblyInteraction() {
  await clickAny(["上部窗框"]);
  await clickAny(["空槽位 1"]);
  await touchDrag(
    '[aria-label="按住拖动下部窗框"]',
    '[data-assembly-slot="1"]',
    "窗框构件拖入第二槽位",
    '[data-assembly-slot="0"]',
  );
  const state = await evaluate(`(() => {
    const first = document.querySelector('[data-assembly-slot="0"]');
    const second = document.querySelector('[data-assembly-slot="1"]');
    return {
      first: first?.getAttribute("aria-label") ?? "",
      second: second?.getAttribute("aria-label") ?? "",
    };
  })()`);
  if (
    !state.first.includes("上部窗框") ||
    !state.second.includes("下部窗框")
  ) {
    throw new Error(`窗框点按/拖动放置未生效：${JSON.stringify(state)}`);
  }
  await screenshot("06-05-window-assembly-drag");
}

async function assertNoHorizontalOverflow(width) {
  const layout = await evaluate(`(() => ({
    viewportWidth: window.innerWidth,
    documentWidth: document.documentElement.scrollWidth,
    bodyWidth: document.body.scrollWidth
  }))()`);
  if (
    layout.viewportWidth !== width ||
    layout.documentWidth > layout.viewportWidth ||
    layout.bodyWidth > layout.viewportWidth
  ) {
    throw new Error(
      `${width}px 视口存在横向溢出：${JSON.stringify(layout)}`,
    );
  }
}

async function assertStoryMapContained() {
  const layout = await evaluate(`(() => {
    const map = document.querySelector(".map-route-view");
    const pane = map?.parentElement;
    if (!map || !pane) return null;
    const mapRect = map.getBoundingClientRect();
    const paneRect = pane.getBoundingClientRect();
    const paneStyle = getComputedStyle(pane);
    return {
      mapTop: mapRect.top,
      mapBottom: mapRect.bottom,
      paneTop: paneRect.top,
      paneBottom: paneRect.bottom,
      panePosition: paneStyle.position,
      paneOverflow: paneStyle.overflow
    };
  })()`);
  if (!layout) throw new Error("六站地图没有渲染 MapRouteView");
  if (
    layout.panePosition === "static" ||
    layout.paneOverflow !== "hidden" ||
    layout.mapTop < layout.paneTop - 1 ||
    layout.mapBottom > layout.paneBottom + 1
  ) {
    throw new Error(`六站地图图层逃出面板：${JSON.stringify(layout)}`);
  }
}

async function waitForPath(predicate, description) {
  return waitFor(description, async () => {
    const url = new URL(await currentUrl());
    return predicate(url) ? url : null;
  });
}

async function advanceWithButtons({
  until,
  description,
  labels,
  maximumClicks = 40,
}) {
  const deadline = Date.now() + timeoutMs;
  let clickCount = 0;
  while (Date.now() < deadline) {
    if (await until()) return;
    const clicked = await clickAny(labels, { optional: true });
    if (!clicked) {
      await sleep(250);
      continue;
    }
    clickCount += 1;
    if (clickCount >= maximumClicks) break;
    await sleep(250);
  }
  const text = normalizeText(await bodyText()).slice(-600);
  throw new Error(
    `推进“${description}”失败（已点击 ${clickCount} 次）：${text}`,
  );
}

async function dismissRewardAndReturnToMap(sessionId, index) {
  if (
    await hasAnyText([
      "收下并查看下一站",
      "收下",
      "查看下一站",
      "下一站",
      "返回故事地图",
    ])
  ) {
    await screenshot(`08-${String(index).padStart(2, "0")}-reward`);
  }

  if (index === 5) {
    await setMobileViewport(390, 480);
    await waitFor(
      "第五瓣奖励与完整市花分步展示",
      async () => {
        const state = await evaluate(`(() => {
          const dialog = document.querySelector('[role="dialog"]');
          const scroll = document.querySelector("[data-reward-scroll]");
          const button = [...document.querySelectorAll("button")].find(
            (element) => element.textContent?.includes("收下第五瓣")
          );
          return {
            hasPetalDetail: dialog?.textContent?.includes("窗格花瓣"),
            hasFlowerAnimation: Boolean(
              document.querySelector(".story-flower-petal-group")
            ),
            buttonVisible: Boolean(
              button &&
                button.getBoundingClientRect().top >= 0 &&
                button.getBoundingClientRect().bottom <= innerHeight
            ),
            scrollable: Boolean(
              scroll && scroll.scrollHeight > scroll.clientHeight
            ),
          };
        })()`);
        return state.hasPetalDetail &&
          !state.hasFlowerAnimation &&
          state.buttonVisible &&
          state.scrollable
          ? state
          : null;
      },
    );
    await sleep(350);
    await screenshot("08-05-fifth-petal");
    const scrolledState = await evaluate(`(() => {
      const scroll = document.querySelector("[data-reward-scroll]");
      const button = [...document.querySelectorAll("button")].find(
        (element) => element.textContent?.includes("收下第五瓣")
      );
      if (!scroll || !button) return null;
      scroll.scrollTop = scroll.scrollHeight;
      const buttonRect = button.getBoundingClientRect();
      return {
        scrollTop: scroll.scrollTop,
        buttonVisible:
          buttonRect.top >= 0 && buttonRect.bottom <= innerHeight,
      };
    })()`);
    if (!scrolledState?.scrollTop || !scrolledState.buttonVisible) {
      throw new Error("第五瓣奖励弹层滚动后未保持操作按钮可见");
    }
    await sleep(100);
    await screenshot("08-05-fifth-petal-scroll");
    await waitAndClick(
      ["收下第五瓣密笺", "收下第五瓣，查看完整市花"],
      "确认收下第五瓣并进入完整市花展示",
    );
    await setMobileViewport(390, 844);
    await waitFor(
      "第五瓣完整市花动画",
      () =>
        evaluate(
          `Boolean(document.querySelector(".story-flower-petal-group") &&
            document.querySelector(".story-flower-final"))`,
        ),
    );
    await sleep(1650);
    await screenshot("08-05-reward-animation");
    const normalMotion = await evaluate(`(() => {
      const petals = document.querySelector(".story-flower-petal-group");
      const flower = document.querySelector(".story-flower-final");
      return {
        petalAnimation: getComputedStyle(petals).animationName,
        flowerAnimation: getComputedStyle(flower).animationName,
      };
    })()`);
    if (
      normalMotion.petalAnimation === "none" ||
      normalMotion.flowerAnimation === "none"
    ) {
      throw new Error("第五瓣奖励缺少组合完整市花动画");
    }

    await cdp.send("Emulation.setEmulatedMedia", {
      media: "",
      features: [{ name: "prefers-reduced-motion", value: "reduce" }],
    });
    await waitFor(
      "减少动态效果直接显示完整市花",
      async () => {
        const state = await evaluate(`(() => {
          const petals = document.querySelector(
            ".story-flower-petal-group"
          );
          const flower = document.querySelector(".story-flower-final");
          return {
            petalsDisplay: getComputedStyle(petals).display,
            flowerOpacity: getComputedStyle(flower).opacity,
          };
        })()`);
        return state.petalsDisplay === "none" &&
          state.flowerOpacity === "1"
          ? state
          : null;
      },
    );
    await screenshot("08-05-reward-reduced-motion");
    await cdp.send("Emulation.setEmulatedMedia", {
      media: "",
      features: [
        { name: "prefers-reduced-motion", value: "no-preference" },
      ],
    });
  }

  await advanceWithButtons({
    description: "奖励与下一站",
    until: async () => {
      const url = new URL(await currentUrl());
      return url.pathname === `/story-sessions/${sessionId}/map`;
    },
    labels: [
      "收下并查看下一站",
      "收下第五瓣，查看完整市花",
      "收下",
      "查看下一站",
      "下一站",
      "返回故事地图",
      "继续",
    ],
    maximumClicks: 10,
  });
}

async function confirmSkip(screenshotName) {
  let nativeDialogSeen = false;
  const removeDialogHandler = cdp.on(
    "Page.javascriptDialogOpening",
    async (event) => {
      nativeDialogSeen = true;
      if (!normalizeText(event.message).includes("跳过")) {
        throw new Error(`出现了非跳过确认对话框：${event.message}`);
      }
      await cdp.send("Page.handleJavaScriptDialog", { accept: true });
    },
  );

  try {
    await waitAndClick(["跳过谜题", "跳过本关", "跳过"], "跳过谜题按钮");
    const confirmationLabels = ["确认跳过", "仍然跳过", "确认"];
    const outcome = await waitFor(
      "跳过确认层",
      async () => {
        if (nativeDialogSeen) return "native";
        if (await hasAnyText(confirmationLabels)) return "custom";
        const url = new URL(await currentUrl());
        const text = normalizeText(await bodyText());
        if (
          url.pathname.endsWith("/map") ||
          text.includes("已跳过此章节") ||
          text.includes("谜题已跳过")
        ) {
          return "advanced-without-confirmation";
        }
        return null;
      },
      4_000,
    );
    if (outcome === "advanced-without-confirmation") {
      throw new Error("点击跳过后未显示确认层，故事已经直接推进");
    }
    if (outcome === "custom") {
      await screenshot(screenshotName);
      await clickAny(confirmationLabels);
    }
  } finally {
    removeDialogHandler();
  }
}

async function runStoryFlow() {
  await mkdir(screenshotDir, { recursive: true });
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await setMobileViewport(390, 844);

  const browserErrors = [];
  cdp.on("Runtime.exceptionThrown", (event) => {
    const message =
      event.exceptionDetails?.exception?.description ??
      event.exceptionDetails?.text ??
      "页面 JavaScript 异常";
    browserErrors.push(message);
  });
  const coverPath = `/stories/${STORY_ID}`;
  if (skipPreferenceEntry) {
    log("按 STORY_SKIP_PREFERENCE_ENTRY=1 跳过偏好 Agent 与故事选择入口");
    await navigate(`${baseUrl}${coverPath}`);
  } else {
    await navigate(`${baseUrl}/preferences`);
    await waitAndClick(
      ["跳过对话，直接微调偏好 →", "直接微调偏好", "跳过"],
      "偏好微调入口",
    );
    await waitAndClick(["历史"], "历史兴趣标签");
    await waitFor(
      "偏好页故事选择",
      async () =>
        normalizeText(await bodyText()).includes(
          "莲城双图：未尽之图",
        ),
    );
    await waitAndClick(["选择这条故事线"], "莲城双图选择按钮");
    await waitFor("莲城双图已选中", () =>
      evaluate(`(() => {
        const button = [...document.querySelectorAll("button")].find(
          (element) => element.textContent?.trim() === "选择这条故事线"
        );
        return button?.closest("article")?.className.includes("ring-2") ?? false;
      })()`)
    );
    await screenshot("00-preference-story-selection");
    await navigate(`${baseUrl}${coverPath}`);
  }
  await waitFor(
    "故事封面",
    async () => normalizeText(await bodyText()).includes("莲城双图"),
  );
  await screenshot("01-cover-logged-out");

  await waitAndClick(
    ["登录并开始", "登录 / 注册", "登录或注册"],
    "故事封面登录入口",
  );
  await waitForPath((url) => url.pathname === "/auth", "登录页");
  await fillInput(
    "input[type='email'], input[name='email']",
    email,
    "邮箱输入框",
  );
  await fillInput(
    "input[type='password'], input[name='password']",
    password,
    "密码输入框",
  );
  await submitFirstForm();
  await waitForPath(
    (url) => url.pathname === coverPath,
    "登录后返回故事封面",
  );
  await waitFor(
    "登录后的故事封面",
    async () =>
      hasAnyText([
        "开始故事",
        "开始探索",
        "继续上次进度",
        "继续探索",
      ]),
  );
  await screenshot("02-login-returned-to-cover");

  await clickAny([
    "开始故事",
    "开始探索",
    "继续上次进度",
    "继续探索",
  ]);
  const sessionUrl = await waitForPath(
    (url) => /^\/story-sessions\/[^/]+\/(?:map|nodes\/[^/]+)$/.test(url.pathname),
    "使用真实 session_id 进入故事",
  );
  const match = sessionUrl.pathname.match(/^\/story-sessions\/([^/]+)\//);
  const sessionId = match?.[1];
  if (!sessionId || sessionId === STORY_ID) {
    throw new Error(`故事 URL 未使用真实 session_id：${sessionUrl.pathname}`);
  }
  const persistedSession = await evaluate(`(() => {
    const token = localStorage.getItem(${JSON.stringify(AUTH_TOKEN_KEY)});
    if (!token) return { userId: null, storedSessionId: null, legacy: null };
    try {
      const encoded = token.split(".")[1]
        .replace(/-/g, "+")
        .replace(/_/g, "/");
      const padded = encoded.padEnd(
        encoded.length + ((4 - encoded.length % 4) % 4),
        "="
      );
      const userId = JSON.parse(atob(padded)).sub;
      const key = ${JSON.stringify(SESSION_STORAGE_KEY)} + ":" +
        encodeURIComponent(userId);
      return {
        userId,
        storedSessionId: localStorage.getItem(key),
        legacy: localStorage.getItem(${JSON.stringify(SESSION_STORAGE_KEY)}),
      };
    } catch {
      return { userId: null, storedSessionId: null, legacy: null };
    }
  })()`);
  if (persistedSession?.storedSessionId !== sessionId) {
    throw new Error(
      `URL session_id（${sessionId}）与账号级持久化值` +
        `（${persistedSession?.storedSessionId ?? "null"}）不一致`,
    );
  }
  if (persistedSession.legacy !== null) {
    throw new Error("仍写入了未区分账号的旧故事 session_id");
  }
  log(`真实会话已创建或恢复：${sessionId}`);

  if (
    sessionUrl.pathname ===
    `/story-sessions/${sessionId}/nodes/prologue_old_book`
  ) {
    await screenshot("03-prologue");
    await waitAndClick(["问阿莲"], "序章问阿莲入口");
    await waitFor(
      "序章 Agent 建议问题",
      async () =>
        normalizeText(await bodyText()).includes("这本古书是什么") &&
        normalizeText(await bodyText()).includes("为什么第一站要去妈阁庙"),
    );
    await screenshot("03a-prologue-agent");
    await clickAny(["关闭问答"]);

    await waitAndClick(["查看大图"], "缺图占位图放大入口");
    await waitFor(
      "图片放大层",
      () => evaluate('Boolean(document.querySelector("[aria-modal=true]"))'),
    );
    await screenshot("03b-placeholder-image-viewer");
    await clickAny(["关闭大图"]);

    await clickAny(["阅读下一格"]);
    await waitFor(
      "漫画向前从右侧滑入",
      () =>
        evaluate(
          'document.querySelector("[data-comic-direction]")?.getAttribute("data-comic-direction") === "forward"',
        ),
    );
    await clickAny(["上一格"]);
    await waitFor(
      "漫画返回时从左侧滑入",
      () =>
        evaluate(
          'document.querySelector("[data-comic-direction]")?.getAttribute("data-comic-direction") === "backward"',
        ),
    );
    await screenshot("03b2-comic-backward-transition");

    await advanceWithButtons({
      description: "序章漫画",
      until: () =>
        evaluate(
          'Boolean(document.querySelector("[data-story-dialogue-bubble=current]"))',
        ),
      labels: ["阅读下一格", "进入对话"],
      maximumClicks: 6,
    });
    const firstTurn = await evaluate(`(() => ({
      current: document.querySelectorAll(
        "[data-story-dialogue-bubble=current]"
      ).length,
      history: document.querySelectorAll(
        "[data-story-dialogue-bubble=history]"
      ).length,
    }))()`);
    if (firstTurn.current !== 1 || firstTurn.history !== 0) {
      throw new Error(`首次对话未保持单气泡：${JSON.stringify(firstTurn)}`);
    }

    await clickAny(["轻触继续"]);
    const portraitLayout = await waitFor(
      "阿莲立绘位于当前气泡左下侧",
      async () => {
        const layout = await evaluate(`(() => {
          const portrait = document.querySelector(
            '[aria-label="阿莲立绘"]'
          );
          const bubble = document.querySelector(
            "[data-story-dialogue-bubble=current]"
          );
          if (!portrait || !bubble) return null;
          const portraitRect = portrait.getBoundingClientRect();
          const bubbleRect = bubble.getBoundingClientRect();
          return {
            current: document.querySelectorAll(
              "[data-story-dialogue-bubble=current]"
            ).length,
            portraitLeft: portraitRect.left,
            portraitBottom: portraitRect.bottom,
            bubbleLeft: bubbleRect.left,
            bubbleBottom: bubbleRect.bottom,
          };
        })()`);
        if (
          layout &&
          layout.current === 1 &&
          layout.portraitLeft < layout.bubbleLeft &&
          Math.abs(layout.portraitBottom - layout.bubbleBottom) <= 8
        ) {
          return layout;
        }
        return null;
      },
    );
    log(`阿莲立绘与气泡底部对齐：${JSON.stringify(portraitLayout)}`);
    await screenshot("03c-single-dialogue-with-portrait");

    await clickAny(["轻触继续"]);
    await waitFor(
      "第三句对话出现",
      () =>
        evaluate(`document.querySelector(
          "[data-story-dialogue-bubble=current]"
        )?.textContent?.includes("第一张纸条")`),
    );
    await waitAndClick(["查看历史对话"], "历史对话入口");
    const historyLayout = await evaluate(`(() => ({
      current: document.querySelectorAll(
        "[data-story-dialogue-bubble=current]"
      ).length,
      history: document.querySelectorAll(
        "[data-story-dialogue-bubble=history]"
      ).length,
    }))()`);
    if (historyLayout.current !== 1 || historyLayout.history !== 2) {
      throw new Error(
        `历史对话展开数量不正确：${JSON.stringify(historyLayout)}`,
      );
    }
    await sleep(300);
    await screenshot("03d-dialogue-history");
    await clickAny(["收起历史"]);

    await advanceWithButtons({
      description: "序章",
      until: async () => {
        const url = new URL(await currentUrl());
        return url.pathname === `/story-sessions/${sessionId}/map`;
      },
      labels: [
        "打开古书",
        "继续",
        "下一句",
        "展开城市测绘图",
        "展开莲城脉图",
        "呼叫阿莲",
        "查看第一张密笺",
        "开始路线",
        "进入莲城路线",
        "查看路线",
        "返回故事地图",
        "阅读下一格",
        "进入对话",
        "继续观察",
        "去第一站：妈阁庙",
        "收下并查看下一站",
      ],
    });
  } else {
    log("会话已完成序章，从服务端当前路线继续");
  }
  await screenshot("04-route-after-prologue");
  await waitAndClick(["查看六站地图"], "六站地图折叠入口");
  await waitFor(
    "六站地图面板",
    async () =>
      await evaluate('Boolean(document.querySelector(".map-route-view"))'),
  );
  await assertStoryMapContained();
  await screenshot("04b-six-stop-map-contained");

  const currentStationText = await evaluate(`(() => {
    const controls = [...document.querySelectorAll("a, button, [role=button]")];
    return controls.find((element) =>
      element.textContent?.includes("当前站")
    )?.textContent ?? "";
  })()`);
  const resumedIndex = EXPECTED_NODES.findIndex((node) =>
    normalizeText(currentStationText).includes(node.name),
  );
  let startIndex = resumedIndex >= 0 ? resumedIndex : 0;
  let currentChapterAlreadyOpen = false;
  if (resumedIndex < 0) {
    await waitAndClick(
      ["进入章节", "前往当前站", "进入当前章节", "继续当前章节"],
      "探测服务端当前章节",
    );
    const activePath = new URL(await currentUrl()).pathname;
    const pathIndex = EXPECTED_NODES.findIndex((node) =>
      activePath.endsWith(`/nodes/${node.id}`),
    );
    if (pathIndex >= 0) {
      startIndex = pathIndex;
      currentChapterAlreadyOpen = true;
    }
  }
  if (startIndex > 0) {
    log(`从服务端当前第 ${startIndex + 1} 站继续`);
  }

  for (let index = startIndex; index < EXPECTED_NODES.length; index += 1) {
    const node = EXPECTED_NODES[index];
    const nodeNumber = index + 1;
    if (!currentChapterAlreadyOpen) {
      await waitAndClick(
        ["进入章节", "前往当前站", "进入当前章节", "继续当前章节"],
        `进入第 ${nodeNumber} 站 ${node.name}`,
      );
    }
    currentChapterAlreadyOpen = false;
    await waitForPath(
      (url) =>
        url.pathname ===
        `/story-sessions/${sessionId}/nodes/${node.id}`,
      `第 ${nodeNumber} 站 URL`,
    );
    await waitFor(
      `${node.name}章节`,
      async () => normalizeText(await bodyText()).includes(node.name),
    );
    await screenshot(
      `05-${String(nodeNumber).padStart(2, "0")}-${node.id}-arrival`,
    );

    if (await hasAnyText(["我已到达", "确认到达"])) {
      await clickAny(["我已到达", "确认到达"]);
    }

    if (index < EXPECTED_NODES.length - 1) {
      await advanceWithButtons({
        description: `${node.name}谜题前内容`,
        until: () =>
          hasAnyText(["跳过谜题", "跳过本关", "跳过"]),
        labels: [
          "继续",
          "下一句",
          "查看现场",
          "开始观察",
          "查看线索",
          "查看纸条",
          "开始解谜",
          "进入谜题",
          "阅读下一格",
          "进入对话",
          "继续观察",
          "完成回顾",
        ],
      });
      await screenshot(
        `06-${String(nodeNumber).padStart(2, "0")}-${node.id}-puzzle`,
      );
      if (index === 3) await testEvidenceChainInteraction();
      if (index === 4) await testAssemblyInteraction();
      await confirmSkip(
        `07-${String(nodeNumber).padStart(2, "0")}-${node.id}-skip-confirmation`,
      );
      await dismissRewardAndReturnToMap(sessionId, nodeNumber);
      await screenshot(
        `09-${String(nodeNumber).padStart(2, "0")}-${node.id}-map`,
      );
    } else {
      await advanceWithButtons({
        description: "大炮台终章",
        until: async () => {
          const url = new URL(await currentUrl());
          return (
            url.pathname === `/story-sessions/${sessionId}/ending` ||
            (await hasAnyText([
              "写下今日补记",
              "完成今日补记",
              "进入今日补记",
              "选择结局",
            ]))
          );
        },
        labels: [
          "继续",
          "下一句",
          "查看双图",
          "重合双图",
          "完成重合",
          "阅读下一格",
          "进入对话",
          "继续观察",
          "完成回顾",
        ],
      });
      const latestUrl = new URL(await currentUrl());
      if (
        latestUrl.pathname !== `/story-sessions/${sessionId}/ending`
      ) {
        await clickAny([
          "写下今日补记",
          "进入今日补记",
          "完成今日补记",
          "选择结局",
        ]);
      }
      await waitForPath(
        (url) => url.pathname === `/story-sessions/${sessionId}/ending`,
        "今日补记页面",
      );
    }
  }

  await waitFor(
    "今日补记输入框",
    () => evaluate("Boolean(document.querySelector('textarea'))"),
  );
  const reflection =
    "今日补记：澳门的城市记忆由不同年代的人共同书写，也应注明所见与来源。";
  await fillInput("textarea", reflection, "今日补记输入框");

  const todayNoteActions = await evaluate(`(() => {
    const elements = ${visibleElementsExpression(
      "button, [role='button'], input[type='submit']",
    )}.filter((element) =>
      !element.disabled &&
      element.getAttribute("aria-disabled") !== "true" &&
      !element.getAttribute("aria-label")?.startsWith("查看大图")
    );
    const textOf = (element) => String(
      element.innerText || element.value ||
      element.getAttribute("aria-label") || ""
    ).replace(/\\s+/g, " ").trim();
    return elements
      .map(textOf)
      .filter((text) =>
        text.includes("今日补记") || text.includes("留给后来人")
      );
  })()`);
  if (todayNoteActions.length !== 1) {
    throw new Error(
      `终章必须只有一个“今日补记”结局动作，当前找到 ${todayNoteActions.length} 个：` +
        todayNoteActions.join(" / "),
    );
  }
  await screenshot("10-today-note");
  await clickAny([todayNoteActions[0]]);

  if (
    !(await waitFor(
      "完成今日补记或确认动作",
      async () => {
        const text = normalizeText(await bodyText());
        if (
          text.includes("故事完成") ||
          text.includes("旅程完成") ||
          text.includes("今日补记已保存")
        ) {
          return "completed";
        }
        if (
          await hasAnyText([
            "确认完成",
            "确认选择",
            "保存今日补记",
            "完成今日补记",
          ])
        ) {
          return "confirm";
        }
        return null;
      },
    ) === "completed")
  ) {
    await clickAny([
      "确认完成",
      "确认选择",
      "保存今日补记",
      "完成今日补记",
    ]);
  }

  await waitFor("故事完成", async () => {
    const text = normalizeText(await bodyText());
    return (
      text.includes("故事完成") ||
      text.includes("旅程完成") ||
      text.includes("今日补记已保存")
    );
  });
  await waitFor("今日补记回显", async () =>
    normalizeText(await bodyText()).includes(reflection),
  );
  await screenshot("11-completed");

  await reload();
  await waitFor("刷新后仍为完成状态", async () => {
    const url = new URL(await currentUrl());
    const text = normalizeText(await bodyText());
    return (
      url.pathname === `/story-sessions/${sessionId}/ending` &&
      (text.includes("故事完成") ||
        text.includes("旅程完成") ||
        text.includes("今日补记已保存")) &&
      text.includes(reflection)
    );
  });
  await screenshot("12-completed-after-refresh");

  for (const [width, height] of [
    [360, 800],
    [430, 932],
  ]) {
    await setMobileViewport(width, height);
    await assertNoHorizontalOverflow(width);
    await screenshot(`13-completed-${width}px`);
  }

  await setMobileViewport(390, 844);
  await navigate(`${baseUrl}/profile`);
  await waitAndClick(["退出登录", "登出"], "退出当前测试账号");
  await waitFor(
    "退出后清理认证与邀请会话",
    async () =>
      evaluate(`(() => {
        const invitationKeys = Object.keys(sessionStorage).filter((key) =>
          key.startsWith(${JSON.stringify(INVITATION_STORAGE_PREFIX)})
        );
        return (
          localStorage.getItem(${JSON.stringify(AUTH_TOKEN_KEY)}) === null &&
          invitationKeys.length === 0 &&
          Boolean(document.querySelector('a[href^="/auth"]'))
        );
      })()`),
  );

  await navigate(
    `${baseUrl}/auth?mode=register&returnTo=${encodeURIComponent("/preferences")}`,
  );
  await waitFor(
    "切换账号注册表单",
    () => evaluate("Boolean(document.querySelector(\"input[type='email']\"))"),
  );
  await fillInput(
    "input[type='email']",
    switchedAccountEmail,
    "切换账号注册邮箱",
  );
  await fillInput(
    "input[type='password']",
    password,
    "切换账号注册密码",
  );
  await fillInput(
    "input[type='password']",
    password,
    "切换账号确认密码",
    1,
  );
  await fillInput(
    "input[autocomplete='name']",
    "Story Account Switch",
    "切换账号昵称",
  );
  await submitFirstForm();
  await waitForPath(
    (url) => url.pathname === "/preferences",
    "新账号注册后返回偏好页",
  );
  await waitAndClick(
    ["跳过对话，直接微调偏好 →", "直接微调偏好", "跳过"],
    "新账号偏好微调入口",
  );
  await waitAndClick(["历史"], "新账号历史兴趣标签");
  await waitFor("新账号收到独立故事选择", async () =>
    normalizeText(await bodyText()).includes("莲城双图：未尽之图")
  );
  await waitAndClick(["选择这条故事线"], "新账号莲城双图选择按钮");
  await waitFor("新账号莲城双图已选中", () =>
    evaluate(`(() => {
      const button = [...document.querySelectorAll("button")].find(
        (element) => element.textContent?.trim() === "选择这条故事线"
      );
      return button?.closest("article")?.className.includes("ring-2") ?? false;
    })()`)
  );
  await screenshot("14-story-selection-after-account-switch");
  await navigate(`${baseUrl}${coverPath}`);
  await waitFor("新账号不继承旧故事进度", async () => {
    const text = normalizeText(await bodyText());
    if (text.includes("继续上次进度") || text.includes("查看完成记录")) {
      throw new Error("新账号继承了旧账号的故事进度");
    }
    return text.includes("开始故事") || text.includes("开始探索");
  });

  if (browserErrors.length > 0) {
    throw new Error(
      `浏览器记录到 ${browserErrors.length} 个错误：\n${browserErrors.join("\n")}`,
    );
  }
  log(
    `PASS：${
      skipPreferenceEntry ? "已按配置跳过偏好故事选择，" : "偏好故事选择、"
    }登录回跳、真实会话、序章 Agent、单气泡对话、图片放大、` +
      "第五瓣动画、地图图层、六站跳关、今日补记、刷新恢复及账号隔离全部通过",
  );
}

async function cleanup() {
  if (cleanupStarted) return;
  cleanupStarted = true;

  if (cdp) {
    try {
      await cdp.send("Browser.close", {}, 2_000);
    } catch {
      // Fall back to terminating the process below.
    }
    cdp.close();
    cdp = null;
  }

  if (
    browserProcess &&
    browserProcess.exitCode === null &&
    browserProcess.signalCode === null
  ) {
    browserProcess.kill("SIGTERM");
    await Promise.race([once(browserProcess, "exit"), sleep(2_000)]).catch(
      () => {},
    );
    if (
      browserProcess.exitCode === null &&
      browserProcess.signalCode === null
    ) {
      browserProcess.kill("SIGKILL");
      await Promise.race([once(browserProcess, "exit"), sleep(2_000)]).catch(
        () => {},
      );
    }
  }
  browserProcess = null;

  if (browserProfileDir) {
    const safePath = safeTemporaryProfilePath(browserProfileDir);
    const removal = rm(safePath, {
      recursive: true,
      force: true,
      maxRetries: 2,
      retryDelay: 100,
    })
      .then(() => true)
      .catch((error) => {
        process.stderr.write(
          `[story-v4-smoke] 临时 profile 清理失败，可稍后删除 ${safePath}：${error.message}\n`,
        );
        return false;
      });
    const removed = await Promise.race([
      removal,
      sleep(3_000).then(() => false),
    ]);
    if (!removed) {
      process.stderr.write(
        `[story-v4-smoke] 临时 profile 清理超时，可稍后删除 ${safePath}\n`,
      );
    }
    browserProfileDir = null;
  }
}

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.once(signal, () => {
    interrupted = true;
    cleanup()
      .catch((error) => {
        process.stderr.write(`清理失败：${error.message}\n`);
      })
      .finally(() => process.exit(signal === "SIGINT" ? 130 : 143));
  });
}

async function main() {
  await waitForFrontend();
  const executable = findBrowserExecutable();
  log(`浏览器：${executable}`);
  log(`前端：${baseUrl}`);
  log(`截图目录：${screenshotDir}`);

  const port = await launchBrowser(executable);
  const pageWebSocketUrl = await findPageWebSocket(port);
  cdp = new CdpClient(pageWebSocketUrl);
  await cdp.connect();
  await runStoryFlow();
}

try {
  await main();
} catch (error) {
  if (!interrupted) {
    process.stderr.write(
      `[story-v4-smoke] FAIL：${error?.stack ?? error}\n`,
    );
    process.exitCode = 1;
  }
} finally {
  await cleanup().catch((error) => {
    process.stderr.write(`[story-v4-smoke] 清理失败：${error.message}\n`);
    process.exitCode = 1;
  });
}

process.exit(process.exitCode ?? 0);
