// Run: node --test .claude/hooks/time-log.test.cjs (python tools/check.py runs it)
"use strict";

const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");
const t = require("./time-log.cjs");

const HOOK = path.join(__dirname, "time-log.cjs");

function at(sec) {
  return new Date(Date.UTC(2026, 9, 19, 0, 0, sec)).toISOString();
}

test("classify: tools and bash commands fall into categories", () => {
  assert.strictEqual(t.classify("Edit", {}), "편집");
  assert.strictEqual(t.classify("Write", {}), "편집");
  assert.strictEqual(t.classify("Read", {}), "조사");
  assert.strictEqual(t.classify("Grep", {}), "조사");
  assert.strictEqual(t.classify("Bash", { command: "python tools/check.py | tail -3" }), "게이트");
  assert.strictEqual(t.classify("Bash", { command: "python -m pytest tests/x.py" }), "게이트");
  assert.strictEqual(t.classify("Bash", { command: "xvfb-run -a python tools/ui_smoke.py" }), "화면 확인");
  assert.strictEqual(t.classify("Bash", { command: "cd /x && git push -u origin b" }), "깃");
  assert.strictEqual(t.classify("Bash", { command: "node .claude/hooks/time-log.cjs mark 구현" }), "시간 기록");
  assert.strictEqual(t.classify("Bash", { command: "ls -la" }), "명령");
  assert.strictEqual(t.classify("mcp__github__create_pull_request", {}), "깃허브");
  assert.strictEqual(t.classify("Agent", {}), "하위 에이전트");
  assert.strictEqual(t.classify("Skill", {}), "스킬");
  assert.strictEqual(t.classify("WebFetch", {}), "기타");
});

test("record: hook input becomes one log line, unknown events give none", () => {
  const pre = t.record(
    { hook_event_name: "PreToolUse", tool_name: "Edit", tool_use_id: "u1", tool_input: { file_path: "a" } },
    at(0),
  );
  assert.deepStrictEqual(pre, { t: at(0), ev: "PreToolUse", tool: "Edit", cat: "편집", id: "u1" });
  assert.deepStrictEqual(t.record({ hook_event_name: "Stop" }, at(5)), { t: at(5), ev: "Stop" });
  assert.strictEqual(t.record({ hook_event_name: "Notification" }, at(5)), null);
});

test("summarize: tool time by category, working and waiting time, phases", () => {
  const events = [
    { t: at(0), ev: "UserPromptSubmit" },
    { t: at(1), ev: "Mark", phase: "계획" },
    { t: at(2), ev: "PreToolUse", tool: "Read", cat: "조사", id: "a" },
    { t: at(5), ev: "PostToolUse", tool: "Read", cat: "조사", id: "a" },
    { t: at(11), ev: "Mark", phase: "게이트" },
    { t: at(12), ev: "PreToolUse", tool: "Bash", cat: "게이트", id: "b" },
    { t: at(40), ev: "PostToolUse", tool: "Bash", cat: "게이트", id: "b" },
    { t: at(41), ev: "PreToolUse", tool: "Bash", cat: "게이트", id: "lost" }, // no Post: not counted
    { t: at(50), ev: "Stop" },
    { t: at(110), ev: "UserPromptSubmit" },
    { t: at(120), ev: "Stop" },
  ];
  const s = t.summarize(events);
  assert.deepStrictEqual(s.categories, { 조사: { sec: 3, count: 1 }, 게이트: { sec: 28, count: 1 } });
  assert.strictEqual(s.working, 50 + 10);
  assert.strictEqual(s.waiting, 60);
  assert.deepStrictEqual(s.phases, [
    { phase: "계획", sec: 10 },
    { phase: "게이트", sec: 39 + 10 },
  ]);
  assert.strictEqual(s.start, at(0));
  assert.strictEqual(s.end, at(120));
});

test("summarize: a phase does not count the time spent waiting for the user", () => {
  const s = t.summarize([
    { t: at(0), ev: "UserPromptSubmit" },
    { t: at(0), ev: "Mark", phase: "구현" },
    { t: at(30), ev: "Stop" },
    { t: at(90), ev: "UserPromptSubmit" },
    { t: at(100), ev: "Stop" },
  ]);
  assert.deepStrictEqual(s.phases, [{ phase: "구현", sec: 40 }]);
});

test("format: a markdown report with minutes and seconds", () => {
  const text = t.format({
    start: at(0),
    end: at(120),
    working: 75,
    waiting: 3600,
    categories: { 게이트: { sec: 28, count: 2 } },
    phases: [{ phase: "계획", sec: 10 }],
  });
  assert.match(text, /\| 게이트 \| 2 \| 28초 \|/);
  assert.match(text, /\| 계획 \| 10초 \|/);
  assert.match(text, /Claude 작업: 1분 15초/);
  assert.match(text, /사용자 대기: 60분 0초/);
});

test("end to end: hook writes the session log, mark and report read it", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "time-log-"));
  const env = { ...process.env, CLAUDE_PROJECT_DIR: dir };
  const run = (args, input) =>
    execFileSync("node", [HOOK, ...args], { env, input: input ? JSON.stringify(input) : "" }).toString();

  assert.strictEqual(run([], { hook_event_name: "UserPromptSubmit", session_id: "s/1" }), "");
  run([], { hook_event_name: "PreToolUse", session_id: "s/1", tool_name: "Edit", tool_use_id: "x" });
  run([], { hook_event_name: "PostToolUse", session_id: "s/1", tool_name: "Edit", tool_use_id: "x" });
  run(["mark", "구현"]);
  run([], { hook_event_name: "Stop", session_id: "s/1" });

  const file = path.join(dir, ".claude", "time-log", "s_1.jsonl");
  const lines = fs.readFileSync(file, "utf8").trim().split("\n").map((l) => JSON.parse(l));
  assert.deepStrictEqual(
    lines.map((l) => l.ev),
    ["UserPromptSubmit", "PreToolUse", "PostToolUse", "Mark", "Stop"],
  );
  assert.strictEqual(lines[3].phase, "구현");
  assert.match(run(["report"]), /\| 편집 \| 1 \|/);
});

test("the hook never fails a tool call: bad input prints nothing and exits 0", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "time-log-"));
  const out = execFileSync("node", [HOOK], {
    env: { ...process.env, CLAUDE_PROJECT_DIR: dir },
    input: "{not json",
  }).toString();
  assert.strictEqual(out, "");
});
