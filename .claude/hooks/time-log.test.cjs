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

const bash = (command) => t.classify("Bash", { command });

test("classify: git commands by what they do", () => {
  assert.strictEqual(bash("git status -sb"), "깃 - 조회");
  assert.strictEqual(bash("git show HEAD:a.py > /tmp/a"), "깃 - 조회");
  assert.strictEqual(bash("git fetch -q origin main-branch"), "깃 - 가져오기");
  assert.strictEqual(bash("git merge --abort"), "깃 - 병합");
  assert.strictEqual(bash("git checkout -q -B b origin/main-branch"), "깃 - 브랜치 전환");
  assert.strictEqual(bash("git worktree add ../base main-branch"), "깃 - 작업 복사본");
  assert.strictEqual(bash("git add -A"), "깃 - 커밋 준비");
  assert.strictEqual(bash("git -c user.name=Claude -c user.email=x commit -q -F -"), "저장소 저장 - 커밋");
  assert.strictEqual(bash("git push -u origin b 2>&1 | tail -2"), "저장소 저장 - 올리기");
  assert.strictEqual(bash("git config core.hooksPath .githooks"), "환경 준비");
});

test("classify: checks and runs", () => {
  assert.strictEqual(bash("python tools/check.py 2>&1 | tail -3"), "전체 게이트");
  assert.strictEqual(bash("python -m pytest tests/x.py -q"), "게임 테스트");
  assert.strictEqual(bash("UPDATE_GOLDEN=1 python -m pytest"), "골든 갱신");
  assert.strictEqual(bash("python -m ruff check ."), "서식·문법 검사");
  assert.strictEqual(bash("python -m ruff format --check ."), "서식·문법 검사");
  assert.strictEqual(bash("python -m ruff format ."), "서식 자동 수정");
  assert.strictEqual(bash("node --test .claude/hooks/a.test.cjs"), "훅 테스트");
  assert.strictEqual(bash('xvfb-run -a -s "-screen 0 1x1x24" python3.13 tools/ui_smoke.py'), "화면 확인");
  assert.strictEqual(bash("pip install -q pytest"), "환경 준비");
  assert.strictEqual(bash("node .claude/hooks/time-log.cjs mark 구현"), "시간 기록");
  assert.strictEqual(bash("node .claude/hooks/time-log.cjs report"), "시간 기록");
  assert.strictEqual(bash("sed -n 1,9p .claude/hooks/time-log.cjs"), "파일 읽기"); // only mark/report
});

test("classify: reading, searching and editing from the shell", () => {
  assert.strictEqual(bash("cat a.py"), "파일 읽기");
  assert.strictEqual(bash("sed -n 1,80p a.py"), "파일 읽기");
  assert.strictEqual(bash("grep -rn foo game"), "코드 검색");
  assert.strictEqual(bash("find . -name '*.py'"), "코드 검색");
  assert.strictEqual(bash('python -c "import kivy; print(kivy.__file__)"'), "라이브러리 코드 조사");
  assert.strictEqual(bash("ls -la && which python3.11"), "환경 확인");
  assert.strictEqual(bash("python3 - <<'EOF'\nprint(1)\nEOF"), "파일 편집 - 셸");
  assert.strictEqual(bash("cat >> .gitignore <<'EOF'\nx\nEOF"), "파일 편집 - 셸");
  assert.strictEqual(bash("sed -i 's/a/b/' x.py"), "파일 편집 - 셸");
  assert.strictEqual(bash("cp a.py /tmp/a.py"), "파일 편집 - 셸");
  assert.strictEqual(bash("echo hi"), "기타 명령");
});

test("classify: a mixed command goes to its heaviest part, all parts are kept", () => {
  const cmd = "cd /x && git add -A && git commit -m m && git push";
  assert.strictEqual(bash(cmd), "저장소 저장 - 올리기");
  assert.deepStrictEqual(t.categories("Bash", { command: cmd }), [
    "저장소 저장 - 올리기",
    "저장소 저장 - 커밋",
    "깃 - 커밋 준비",
  ]);
});

test("classify: other tools", () => {
  assert.strictEqual(t.classify("Edit", {}), "파일 편집 - 도구");
  assert.strictEqual(t.classify("Write", {}), "파일 편집 - 도구");
  assert.strictEqual(t.classify("Read", { file_path: "/a/b.py" }), "파일 읽기");
  assert.strictEqual(t.classify("Read", { file_path: "/shots/01.PNG" }), "이미지 확인");
  assert.strictEqual(t.classify("Grep", {}), "코드 검색");
  assert.strictEqual(t.classify("mcp__github__create_pull_request", {}), "깃허브 - 병합 요청");
  assert.strictEqual(t.classify("mcp__github__pull_request_read", {}), "깃허브 - 병합 요청");
  assert.strictEqual(t.classify("mcp__github__add_reply_to_pull_request_comment", {}), "깃허브 - 병합 요청 댓글·리뷰");
  assert.strictEqual(t.classify("mcp__github__pull_request_review_write", {}), "깃허브 - 병합 요청 댓글·리뷰");
  assert.strictEqual(t.classify("mcp__github__issue_write", {}), "깃허브 - 이슈");
  assert.strictEqual(t.classify("mcp__github__search_issues", {}), "깃허브 - 이슈");
  assert.strictEqual(t.classify("mcp__github__get_job_logs", {}), "깃허브 - 자동 검사 조회");
  assert.strictEqual(t.classify("mcp__github__actions_list", {}), "깃허브 - 자동 검사 조회");
  assert.strictEqual(
    t.classify("mcp__github__actions_run_trigger", { method: "rerun_failed_jobs" }),
    "깃허브 - 자동 검사 다시 돌리기",
  );
  assert.strictEqual(t.classify("mcp__claude-code-remote__subscribe_pr_activity", {}), "깃허브 - 알림 설정");
  assert.strictEqual(t.classify("mcp__claude-code-remote__send_later", {}), "세션 - 예약");
  assert.strictEqual(t.classify("mcp__claude-code-remote__delete_trigger", {}), "세션 - 예약");
  assert.strictEqual(t.classify("ReadNotifications", {}), "세션 - 알림 읽기");
  assert.strictEqual(t.classify("ToolSearch", {}), "세션 - 도구 불러오기");
  assert.strictEqual(t.classify("Agent", {}), "하위 에이전트");
  assert.strictEqual(t.classify("Skill", {}), "스킬");
  assert.strictEqual(t.classify("WebFetch", {}), "웹");
  assert.strictEqual(t.classify("SomethingNew", {}), "기타 도구");
});

test("group: every category belongs to a group", () => {
  assert.strictEqual(t.group("깃 - 병합"), "깃");
  assert.strictEqual(t.group("저장소 저장 - 커밋"), "저장소 저장");
  assert.strictEqual(t.group("게임 테스트"), "검사·실행");
  assert.strictEqual(t.group("이미지 확인"), "조사");
  assert.strictEqual(t.group("파일 편집 - 셸"), "편집");
  assert.strictEqual(t.group("세션 - 예약"), "세션");
  assert.strictEqual(t.group("기타 명령"), "기타");
});

test("turnTokens: output tokens of the turn and the context at its end", () => {
  const a = (id, out, cache, extra = {}) =>
    JSON.stringify({
      type: "assistant",
      message: { id, usage: { input_tokens: 5, cache_read_input_tokens: cache, output_tokens: out } },
      ...extra,
    });
  const text = [
    '{"cut',
    a("m1", 100, 1000),
    a("m1", 100, 1000), // one message split over several lines
    a("s1", 900, 9, { isSidechain: true }),
    a("m2", 40, 2000),
  ].join("\n");
  assert.deepStrictEqual(t.turnTokens(text), { output: 140, context: 2005 });
});

test("record: hook input becomes one log line", () => {
  const input = { tool_name: "Bash", tool_use_id: "u1", tool_input: { command: "git add -A && git commit" } };
  assert.deepStrictEqual(t.record({ ...input, hook_event_name: "PreToolUse" }, at(0)), {
    t: at(0),
    ev: "PreToolUse",
    tool: "Bash",
    cat: "저장소 저장 - 커밋",
    also: ["깃 - 커밋 준비"],
    id: "u1",
  });
  assert.deepStrictEqual(t.record({ ...input, hook_event_name: "PostToolUse" }, at(3)), {
    t: at(3),
    ev: "PostToolUse",
    id: "u1",
    ok: true,
  });
  assert.deepStrictEqual(t.record({ ...input, hook_event_name: "PostToolUseFailure" }, at(3)), {
    t: at(3),
    ev: "PostToolUse",
    id: "u1",
    ok: false,
  });
  assert.deepStrictEqual(t.record({ hook_event_name: "Stop" }, at(5)), { t: at(5), ev: "Stop" });
  assert.strictEqual(t.record({ hook_event_name: "Notification" }, at(5)), null);
});

test("parseMark: tasks carry a kind, other marks are phases", () => {
  assert.deepStrictEqual(t.parseMark(["작업", "버그", "#12", "전투", "버그"]), {
    ev: "Task",
    kind: "버그",
    name: "#12 전투 버그",
  });
  assert.deepStrictEqual(t.parseMark(["게이트"]), { ev: "Mark", phase: "게이트" });
  assert.deepStrictEqual(t.parseMark([]), { ev: "Mark", phase: "이름 없음" });
});

const EVENTS = [
  { t: at(0), ev: "UserPromptSubmit" },
  { t: at(1), ev: "Task", kind: "기능", name: "#1 상점" },
  { t: at(1), ev: "Mark", phase: "조사" },
  { t: at(2), ev: "PreToolUse", tool: "Read", cat: "파일 읽기", id: "a" },
  { t: at(2), ev: "PreToolUse", tool: "Grep", cat: "코드 검색", id: "p" }, // parallel with a
  { t: at(5), ev: "PostToolUse", id: "a", ok: true },
  { t: at(6), ev: "PostToolUse", id: "p", ok: true },
  { t: at(10), ev: "Mark", phase: "게이트" },
  { t: at(10), ev: "PreToolUse", tool: "Bash", cat: "전체 게이트", id: "g" },
  { t: at(20), ev: "GateStep", step: "pytest", sec: 7.5, ok: false },
  { t: at(30), ev: "PostToolUse", id: "g", ok: false },
  { t: at(31), ev: "PreToolUse", tool: "Bash", cat: "전체 게이트", id: "lost" }, // denied: no end
  { t: at(40), ev: "Stop", output: 300, context: 50000 },
  { t: at(100), ev: "UserPromptSubmit" },
  { t: at(101), ev: "Task", kind: "버그", name: "#2 전투" },
  { t: at(102), ev: "PreToolUse", tool: "Bash", cat: "저장소 저장 - 커밋", id: "c" },
  { t: at(104), ev: "PostToolUse", id: "c", ok: true },
  { t: at(110), ev: "Stop", output: 20, context: 60000 },
];

test("summarize: turns with their task, tool time and thinking time", () => {
  const s = t.summarize(EVENTS);
  assert.deepStrictEqual(s.turns, [
    {
      n: 1,
      start: at(0),
      sec: 40,
      tools: 4 + 20, // 2..6 counted once although two calls ran at once, then 10..30
      think: 16,
      output: 300,
      context: 50000,
      task: "#1 상점",
      fails: 1,
      cats: { "파일 읽기": 3, "코드 검색": 4, "전체 게이트": 20 },
    },
    {
      n: 2,
      start: at(100),
      sec: 10,
      tools: 2,
      think: 8,
      output: 20,
      context: 60000,
      task: "#2 전투",
      fails: 0,
      cats: { "저장소 저장 - 커밋": 2 },
    },
  ]);
  assert.strictEqual(s.waiting, 60);
  assert.strictEqual(s.unfinished, 1);
});

test("summarize: categories, tasks, gate steps and phases", () => {
  const s = t.summarize(EVENTS);
  assert.deepStrictEqual(s.categories["전체 게이트"], { count: 1, fails: 1, sec: 20 });
  assert.deepStrictEqual(s.tasks, [
    { name: "#1 상점", kind: "기능", turns: 1, sec: 40, think: 16, tools: 24, fails: 1 },
    { name: "#2 전투", kind: "버그", turns: 1, sec: 10, think: 8, tools: 2, fails: 0 },
  ]);
  assert.deepStrictEqual(s.gate, { pytest: { count: 1, fails: 1, sec: 7.5 } });
  assert.deepStrictEqual(s.phases, [
    { phase: "조사", sec: 9 },
    { phase: "게이트", sec: 30 + 10 },
  ]);
});

test("format: markdown tables in seconds", () => {
  const text = t.format(t.summarize(EVENTS));
  assert.match(text, /\| 1 \| #1 상점 \| 00:00:00 \| 40초 \| 16초 \| 24초 \| 1 \| 50k \| 300 \| 전체 게이트 20초, 코드 검색 4초, 파일 읽기 3초 \|/);
  assert.match(text, /\| #1 상점 \| 기능 \| 1 \| 40초 \| 16초 \| 24초 \| 1 \|/);
  assert.match(text, /\| 검사·실행 \| 전체 게이트 \| 1 \| 1 \| 20초 \| 20초 \|/);
  assert.match(text, /\| pytest \| 1 \| 1 \| 7\.5초 \|/);
  assert.match(text, /사용자 대기: 1분 0초/);
  assert.match(text, /끝나지 않은 도구 호출\(거부·중단\): 1/);
});

test("format: a turn of minutes shows minutes and seconds", () => {
  assert.strictEqual(t.dur(75), "1분 15초");
  assert.strictEqual(t.dur(7.26), "7.3초");
  assert.strictEqual(t.dur(0), "0초");
});

test("end to end: hook writes the session log with tokens, mark and report read it", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "time-log-"));
  const transcript = path.join(dir, "t.jsonl");
  fs.writeFileSync(transcript, '{"type":"user"}\n');
  const env = { ...process.env, CLAUDE_PROJECT_DIR: dir };
  const run = (args, input) =>
    execFileSync("node", [HOOK, ...args], { env, input: input ? JSON.stringify(input) : "" }).toString();
  const base = { session_id: "s/1", transcript_path: transcript };

  assert.strictEqual(run([], { ...base, hook_event_name: "UserPromptSubmit" }), "");
  run(["mark", "작업", "기능", "#3", "상점"]);
  run([], { ...base, hook_event_name: "PreToolUse", tool_name: "Edit", tool_use_id: "x" });
  run([], { ...base, hook_event_name: "PostToolUse", tool_name: "Edit", tool_use_id: "x" });
  fs.appendFileSync(
    transcript,
    JSON.stringify({ type: "assistant", message: { id: "m", usage: { input_tokens: 7, output_tokens: 11 } } }) + "\n",
  );
  run([], { ...base, hook_event_name: "Stop" });

  const file = path.join(dir, ".claude", "time-log", "s_1.jsonl");
  const lines = fs.readFileSync(file, "utf8").trim().split("\n").map((l) => JSON.parse(l));
  assert.deepStrictEqual(
    lines.map((l) => l.ev),
    ["UserPromptSubmit", "Task", "PreToolUse", "PostToolUse", "Stop"],
  );
  assert.strictEqual(lines[0].off, 16);
  assert.deepStrictEqual([lines[4].output, lines[4].context], [11, 7]);
  assert.match(run(["report"]), /\| #3 상점 \| 기능 \| 1 \|/);
});

test("the hook never fails a tool call: bad input prints nothing and exits 0", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "time-log-"));
  const out = execFileSync("node", [HOOK], {
    env: { ...process.env, CLAUDE_PROJECT_DIR: dir },
    input: "{not json",
  }).toString();
  assert.strictEqual(out, "");
});
