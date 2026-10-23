// Run: node --test .claude/hooks/output-guard.test.cjs (python tools/check.py runs it)
"use strict";

const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync } = require("child_process");
const g = require("./output-guard.cjs");

// line counts of the files a call names, as decide() receives them
const lines = (table) => (file) => (file in table ? table[file] : null);

const bash = (command) => ({ hook_event_name: "PreToolUse", tool_name: "Bash", tool_input: { command } });
const read = (input) => ({ hook_event_name: "PreToolUse", tool_name: "Read", tool_input: input });

test("reading a big file whole warns, a range or a small file does not", () => {
  const n = lines({ "/r/big.py": 300, "/r/small.py": 40 });
  assert.match(g.decide(read({ file_path: "/r/big.py" }), n), /300줄/);
  assert.strictEqual(g.decide(read({ file_path: "/r/big.py", offset: 10, limit: 40 }), n), null);
  assert.strictEqual(g.decide(read({ file_path: "/r/small.py" }), n), null);
  assert.strictEqual(g.decide(read({ file_path: "/r/없음.py" }), n), null);
});

test("cat of a big file warns unless piped into a filter; heredocs and redirects are not reads", () => {
  const n = lines({ "game/data/a.py": 400, "b.txt": 10 });
  assert.match(g.decide(bash("cat game/data/a.py"), n), /400줄/);
  assert.match(g.decide(bash("cd /r && cat b.txt game/data/a.py"), n), /game\/data\/a.py/);
  assert.strictEqual(g.decide(bash("cat game/data/a.py | grep -n 레벨"), n), null);
  assert.strictEqual(g.decide(bash("cat b.txt"), n), null);
  assert.strictEqual(g.decide(bash("cat >> game/data/a.py <<'EOF'\nx\nEOF"), n), null);
  assert.strictEqual(g.decide(bash("cat <<'EOF' > b.txt\nx\nEOF"), n), null);
});

test("a wide sed -n range warns, a narrow one does not", () => {
  assert.match(g.decide(bash("sed -n '1,200p' a.py"), lines({})), /200줄/);
  assert.match(g.decide(bash("sed -n 10,300p a.py"), lines({})), /291줄/);
  assert.strictEqual(g.decide(bash("sed -n 120,160p a.py"), lines({})), null);
});

test("a recursive search without a length or count limit warns", () => {
  const none = lines({});
  assert.match(g.decide(bash("grep -rn 레벨 game/"), none), /검색/);
  assert.match(g.decide(bash("cd /r && rg 레벨 game"), none), /검색/);
  for (const ok of [
    "grep -rl 레벨 game/",
    "grep -rn 레벨 game/ | head -30",
    "grep -rn 레벨 game/ | cut -c1-200",
    "rg -c 레벨 game",
    "rg --max-columns 200 레벨 game",
    "grep -n 레벨 game/data/a.py",
    "git grep -n 레벨 | wc -l",
  ]) {
    assert.strictEqual(g.decide(bash(ok), none), null, ok);
  }
});

test("a long editing script warns; a commit message or a short script does not", () => {
  const body = "x = 1\n".repeat(400);
  assert.match(g.decide(bash(`python - <<'EOF'\n${body}EOF`), lines({})), /Edit/);
  assert.strictEqual(g.decide(bash(`git commit -F - <<'EOF'\n${body}EOF`), lines({})), null);
  assert.strictEqual(g.decide(bash("python - <<'EOF'\nprint(1)\nEOF"), lines({})), null);
});

test("other tools and events stay quiet", () => {
  assert.strictEqual(g.decide({ hook_event_name: "PreToolUse", tool_name: "Edit", tool_input: {} }, lines({})), null);
  assert.strictEqual(g.decide({ hook_event_name: "PostToolUse", tool_name: "Bash", tool_input: { command: "cat a" } }, lines({ a: 999 })), null);
});

test("the hook warns as context and never blocks: no permission decision, exit 0", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "output-guard-"));
  const big = path.join(dir, "big.py");
  fs.writeFileSync(big, "x\n".repeat(500));
  const run = (input) =>
    execFileSync("node", [path.join(__dirname, "output-guard.cjs")], { input: JSON.stringify(input), encoding: "utf8" });
  const out = JSON.parse(run({ ...read({ file_path: big }), cwd: dir }));
  assert.strictEqual(out.hookSpecificOutput.hookEventName, "PreToolUse");
  assert.match(out.hookSpecificOutput.additionalContext, /500줄/);
  assert.strictEqual(out.hookSpecificOutput.permissionDecision, undefined);
  assert.strictEqual(run({ ...bash("cat big.py | head -5"), cwd: dir }), "");
  assert.strictEqual(run({ ...bash("cat big.py"), cwd: dir }).length > 0, true); // relative to cwd
  assert.strictEqual(execFileSync("node", [path.join(__dirname, "output-guard.cjs")], { input: "깨진", encoding: "utf8" }), "");
});
