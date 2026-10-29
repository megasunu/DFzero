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
  assert.strictEqual(bash("node .claude/hooks/time-log.cjs mark 게이트 && python tools/check.py"), "전체 게이트");
  assert.strictEqual(bash("sed -n 1,9p .claude/hooks/time-log.cjs"), "파일 읽기"); // only mark/report
});

test("classify: the gate and the smoke only when they run, not when the file is read (#271)", () => {
  assert.strictEqual(bash("python3 -I tools/check.py --빠른 tests/test_a.py"), "전체 게이트");
  assert.strictEqual(bash("cd /x && python3.11 tools/check.py"), "전체 게이트");
  assert.strictEqual(bash("python tools/ui_smoke.py"), "화면 확인");
  assert.strictEqual(bash("sed -n 80,150p tools/check.py"), "파일 읽기");
  assert.strictEqual(bash("grep -n GateStep tools/check.py"), "코드 검색");
  assert.strictEqual(bash("cat tools/ui_smoke.py | head"), "파일 읽기");
  assert.strictEqual(bash("grep -n _단계_ tools/ui_smoke.py"), "코드 검색");
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
      cut: false,
      kind: "사람",
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
      cut: false,
      kind: "사람",
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
});

test("summarize: phases are counted per task, a task mark starts its phases over", () => {
  const s = t.summarize(EVENTS);
  // The task and 조사 marks come before any work in turn 1, so they start at the turn's start. 게이트 ends
  // where #2 starts, so the second turn is not 게이트 time; #2 has no phase mark at all.
  assert.deepStrictEqual(s.phases, [
    { task: "#1 상점", phase: "조사", sec: 10, cats: { "파일 읽기": 3, "코드 검색": 4 } },
    { task: "#1 상점", phase: "게이트", sec: 30, cats: { "전체 게이트": 20 } },
    { task: "#2 전투", phase: "단계 없음", sec: 10, cats: { "저장소 저장 - 커밋": 2 } },
  ]);
  const text = t.format(s);
  assert.match(text, /\*\*작업별 단계\*\*/);
  assert.match(text, /\| #1 상점 \| 게이트 \| 30초 \| 전체 게이트 20초 \|/);
  assert.match(text, /\| #2 전투 \| 단계 없음 \| 10초 \| 저장소 저장 - 커밋 2초 \|/);
});

test("summarize: time before a task's first phase mark is 단계 없음, an empty one is left out", () => {
  const s = t.summarize([
    { t: at(0), ev: "UserPromptSubmit" },
    { t: at(1), ev: "Task", kind: "기능", name: "#1" },
    { t: at(2), ev: "PreToolUse", tool: "Read", cat: "파일 읽기", id: "r" },
    { t: at(5), ev: "PostToolUse", id: "r", ok: true },
    { t: at(8), ev: "Mark", phase: "구현" },
    { t: at(20), ev: "Stop" },
  ]);
  assert.deepStrictEqual(
    s.phases.map((p) => [p.task, p.phase, p.sec]),
    [
      ["#1", "단계 없음", 8],
      ["#1", "구현", 12],
    ],
  );
});

// Gate runs: two full ones with fixes in between, a quick one, and steps written without a hook call
// (check.py run outside Claude's tools).
const GATES = [
  { t: at(0), ev: "UserPromptSubmit" },
  { t: at(0), ev: "Task", kind: "기능", name: "#1" },
  { t: at(1), ev: "PreToolUse", tool: "Bash", cat: "전체 게이트", id: "g1" },
  { t: at(2), ev: "GateStep", step: "compileall", sec: 1, ok: true },
  { t: at(3), ev: "GateStep", step: "ruff format", sec: 1, ok: false },
  { t: at(4), ev: "PostToolUse", id: "g1", ok: false },
  { t: at(5), ev: "PreToolUse", tool: "Bash", cat: "서식 자동 수정", id: "f" },
  { t: at(6), ev: "PostToolUse", id: "f", ok: true },
  { t: at(7), ev: "PreToolUse", tool: "Edit", cat: "파일 편집 - 도구", id: "e" },
  { t: at(8), ev: "PostToolUse", id: "e", ok: true },
  // `UPDATE_GOLDEN=1 python -m pytest && python tools/check.py`: the golden update rides on the gate call
  { t: at(9), ev: "PreToolUse", tool: "Bash", cat: "전체 게이트", also: ["골든 갱신", "게임 테스트"], id: "g2" },
  { t: at(20), ev: "GateStep", step: "pytest", sec: 10, ok: true },
  { t: at(21), ev: "PostToolUse", id: "g2", ok: true },
  { t: at(22), ev: "PreToolUse", tool: "Bash", cat: "전체 게이트", id: "q" },
  { t: at(25), ev: "GateStep", step: "pytest(빠른)", sec: 2, ok: true },
  { t: at(26), ev: "PostToolUse", id: "q", ok: true },
  { t: at(30), ev: "GateStep", step: "compileall", sec: 1, ok: true },
  { t: at(40), ev: "GateStep", step: "pytest", sec: 5, ok: false },
  // `sed -n 1,9p tools/check.py` is classified as a gate but writes no steps: not a gate run
  { t: at(41), ev: "PreToolUse", tool: "Bash", cat: "전체 게이트", id: "read" },
  { t: at(42), ev: "PostToolUse", id: "read", ok: true },
  { t: at(50), ev: "Stop" },
];

test("summarize: each gate run with its round in the task, the last result and what happened since", () => {
  const s = t.summarize(GATES);
  assert.deepStrictEqual(s.gateRuns, [
    { task: "#1", kind: "전체", n: 1, sec: 3, prev: "-", since: "-" },
    { task: "#1", kind: "전체", n: 2, sec: 12, prev: "실패(ruff format)", since: "골든 갱신 1, 서식 자동 수정 1, 편집 1" },
    { task: "#1", kind: "빠른", n: 1, sec: 4, prev: "통과", since: "없음" },
    { task: "#1", kind: "전체", n: 3, sec: 11, prev: "빠른 통과", since: "없음" },
  ]);
  const text = t.format(s);
  assert.match(text, /\*\*게이트 회차\*\*/);
  assert.match(text, /\| #1 \| 전체 2 \| 12초 \| 실패\(ruff format\) \| 골든 갱신 1, 서식 자동 수정 1, 편집 1 \|/);
  assert.match(text, /\| #1 \| 빠른 1 \| 4초 \| 통과 \| 없음 \|/);
});

test("prompt kinds: a person, a background task's notification, hook feedback", () => {
  assert.strictEqual(t.promptKind("고쳐줘"), "사람");
  assert.strictEqual(t.promptKind("  <task-notification>\n<task-id>b1</task-id>"), "알림");
  assert.strictEqual(t.promptKind("Stop hook feedback:\nx"), "훅피드백");
  assert.strictEqual(t.promptKind(undefined), "사람");
  const line = t.record({ hook_event_name: "UserPromptSubmit", prompt: "<task-notification>..." }, at(1));
  assert.deepStrictEqual(line, { t: at(1), ev: "UserPromptSubmit", kind: "알림" }); // no prompt text kept
});

// The queued notifications of PR activity and other sessions come in the same wrapper, with no task id (#276).
const REMOTE =
  "<task-notification>\n<task-type>queued-remote-notifications</task-type>\n<status>pending</status>\n" +
  "<summary>1 unread notification</summary>\n</task-notification>";

test("prompt kinds: a remote notification is not a background task's (#276)", () => {
  assert.strictEqual(t.promptKind(REMOTE), "원격알림");
  assert.deepStrictEqual(t.backgroundLines({ hook_event_name: "UserPromptSubmit", prompt: REMOTE }, at(1)), []);
});

test("summarize: a gap ended by a remote notification is its own wait, the turn shows (원격)", () => {
  const s = t.summarize([
    { t: at(0), ev: "UserPromptSubmit", kind: "사람" },
    { t: at(10), ev: "Stop" },
    { t: at(70), ev: "UserPromptSubmit", kind: "원격알림" },
    { t: at(75), ev: "Stop" },
    { t: at(95), ev: "UserPromptSubmit", kind: "알림" },
    { t: at(100), ev: "Stop" },
  ]);
  assert.deepStrictEqual([s.waiting, s.bgWaiting, s.remoteWaiting], [0, 20, 60]);
  const text = t.format(s);
  assert.match(text, /백그라운드 대기: 20초 \/ 원격 알림 대기: 1분 0초 \//);
  assert.match(text, /\| 2 \(원격\) \|/);
});

test("background lines: start from the tool's response, end from a notification or TaskStop", () => {
  const post = { hook_event_name: "PostToolUse", tool_name: "Bash", tool_use_id: "u1" };
  assert.deepStrictEqual(t.backgroundLines({ ...post, tool_response: { backgroundTaskId: "b7" } }, at(1)), [
    { t: at(1), ev: "BgStart", id: "b7", call: "u1" },
  ]);
  assert.deepStrictEqual(t.backgroundLines({ ...post, tool_response: { stdout: "x" } }, at(1)), []);
  assert.deepStrictEqual(
    t.backgroundLines({ ...post, tool_name: "TaskStop", tool_input: { task_id: "b7" }, tool_response: {} }, at(2)),
    [{ t: at(2), ev: "BgEnd", id: "b7", status: "stopped" }],
  );
  const prompt =
    "<task-notification>\n<task-id>b1</task-id>\n<status>completed</status>\n<summary>secret</summary>\n</task-notification>\n" +
    "<task-notification><task-id>b2</task-id><status>failed</status></task-notification>" +
    "<task-notification><task-id>bad id!</task-id><status>whatever</status></task-notification>";
  assert.deepStrictEqual(t.backgroundLines({ hook_event_name: "UserPromptSubmit", prompt }, at(3)), [
    { t: at(3), ev: "BgEnd", id: "b1", status: "completed" },
    { t: at(3), ev: "BgEnd", id: "b2", status: "failed" },
  ]);
  assert.deepStrictEqual(t.backgroundLines({ hook_event_name: "UserPromptSubmit", prompt: "hi" }, at(3)), []);
});

// A gate in the background: Claude reads meanwhile, then stops and waits for the notification.
const BG = [
  { t: at(0), ev: "UserPromptSubmit", kind: "사람" },
  { t: at(1), ev: "PreToolUse", tool: "Bash", cat: "전체 게이트", id: "b1" },
  { t: at(2), ev: "PostToolUse", id: "b1", ok: true },
  { t: at(2), ev: "BgStart", id: "x1", call: "b1", cat: "전체 게이트" },
  { t: at(3), ev: "PreToolUse", tool: "Read", cat: "파일 읽기", id: "r" },
  { t: at(13), ev: "PostToolUse", id: "r", ok: true },
  { t: at(20), ev: "Stop" },
  { t: at(30), ev: "GateStep", step: "pytest", sec: 25, ok: true },
  { t: at(60), ev: "UserPromptSubmit", kind: "알림" },
  { t: at(60), ev: "BgEnd", id: "x1", status: "completed" },
  { t: at(71), ev: "PreToolUse", tool: "Bash", cat: "게임 테스트", id: "b2" },
  { t: at(72), ev: "PostToolUse", id: "b2", ok: true },
  { t: at(72), ev: "BgStart", id: "x2", call: "b2", cat: "게임 테스트" },
  { t: at(80), ev: "PreToolUse", tool: "TaskStop", cat: "기타 도구", id: "s" },
  { t: at(81), ev: "PostToolUse", id: "s", ok: true },
  { t: at(81), ev: "BgEnd", id: "x2", status: "stopped" },
  { t: at(90), ev: "Stop" },
  { t: at(200), ev: "UserPromptSubmit" }, // an old log line: no kind is a person
  { t: at(210), ev: "Stop" },
];

test("summarize: background tasks, waiting on them apart from waiting on the user", () => {
  const s = t.summarize(BG);
  assert.strictEqual(s.waiting, 110);
  assert.strictEqual(s.bgWaiting, 40);
  assert.deepStrictEqual(s.background, {
    "전체 게이트": { count: 1, sec: 59, busy: 19, idle: 40 },
    "게임 테스트": { count: 1, sec: 10, busy: 10, idle: 0 },
  });
  assert.deepStrictEqual(
    s.turns.map((r) => [r.n, r.kind]),
    [
      [1, "사람"],
      [2, "알림"],
      [3, "사람"],
    ],
  );
  // the background gate runs until its notification, so its steps belong to that call
  assert.deepStrictEqual(
    s.gateRuns.map((g) => [g.n, g.sec]),
    [[1, 59]],
  );
  const text = t.format(s);
  assert.match(text, /사용자 대기: 1분 50초 \/ 백그라운드 대기: 40초/);
  assert.match(text, /\| 2 \(알림\) \|/);
  assert.match(text, /\*\*백그라운드\*\*/);
  assert.match(text, /\| 전체 게이트 \| 1 \| 59초 \| 19초 \| 40초 \|/);
});

test("format: markdown tables in seconds", () => {
  const text = t.format(t.summarize(EVENTS));
  assert.match(text, /\| 1 \| #1 상점 \| 09:00:00 \| 40초 \| 16초 \| 24초 \| 1 \| 50k \| 300 \| 전체 게이트 20초, 코드 검색 4초, 파일 읽기 3초 \|/);
  assert.match(text, /\| #1 상점 \| 기능 \| 1 \| 40초 \| 16초 \| 24초 \| 1 \|/);
  assert.match(text, /\| 검사·실행 \| 전체 게이트 \| 1 \| 1 \| 20초 \| 20초 \|/);
  assert.match(text, /\| pytest \| 1 \| 1 \| 7\.5초 \|/);
  assert.match(text, /사용자 대기: 1분 0초/);
  assert.match(text, /끝나지 않은 도구 호출\(거부·중단\): 1/);
});

test("summarize: a message sent mid-turn splits the turn and carries the tokens of the first part", () => {
  const s = t.summarize([
    { t: at(0), ev: "UserPromptSubmit" },
    { t: at(30), ev: "UserPromptSubmit", prev: { output: 70, context: 9000 } },
    { t: at(50), ev: "Stop", output: 5, context: 9500 },
  ]);
  assert.deepStrictEqual(
    s.turns.map((r) => [r.n, r.sec, r.output, r.context, r.cut]),
    [
      [1, 30, 70, 9000, true],
      [2, 20, 5, 9500, false],
    ],
  );
  assert.match(t.format(s), /\| 1\+ \|/);
});

// A Stop hook's feedback makes Claude go on without a new prompt: Stop, more work, Stop again (#272).
// The second Stop's tokens count from the same prompt, so they include the first part's.
const FEEDBACK = [
  { t: at(0), ev: "UserPromptSubmit", kind: "사람" },
  { t: at(1), ev: "Task", kind: "버그", name: "#9" },
  { t: at(30), ev: "Stop", output: 1000, context: 5000 },
  { t: at(32), ev: "PreToolUse", tool: "Bash", cat: "파일 읽기", id: "r" },
  { t: at(33), ev: "PostToolUse", id: "r", ok: true },
  { t: at(42), ev: "Stop", output: 1300, context: 5600 },
  { t: at(100), ev: "UserPromptSubmit", kind: "사람" },
  { t: at(110), ev: "Stop", output: 50, context: 6000 },
];

test("summarize: work after a Stop hook's feedback is a turn of its own, not waiting on the user", () => {
  const s = t.summarize(FEEDBACK);
  assert.deepStrictEqual(
    s.turns.map((r) => [r.n, r.kind, r.sec, r.tools, r.output, r.context, r.task]),
    [
      [1, "사람", 30, 0, 1000, 5000, "#9"],
      [2, "훅피드백", 12, 1, 300, 5600, "#9"],
      [3, "사람", 10, 0, 50, 6000, "#9"],
    ],
  );
  assert.strictEqual(s.waiting, 58); // from the second Stop, not the first
  assert.deepStrictEqual(s.categories["파일 읽기"], { count: 1, fails: 0, sec: 1 });
  assert.deepStrictEqual(
    s.phases.map((p) => [p.phase, p.sec]),
    [["단계 없음", 52]],
  );
  assert.match(t.format(s), /\| 2 \(훅\) \| #9 \|/);
});

test("format: a turn of minutes shows minutes and seconds", () => {
  assert.strictEqual(t.dur(75), "1분 15초");
  assert.strictEqual(t.dur(7.26), "7.3초");
  assert.strictEqual(t.dur(0), "0초");
  assert.strictEqual(t.dur(119.6), "2분 0초");
});

test("record: a finished call keeps the size of what it returned", () => {
  const input = { hook_event_name: "PostToolUse", tool_use_id: "u", tool_response: { stdout: "abcd" } };
  assert.strictEqual(t.record(input, at(1)).size, JSON.stringify(input.tool_response).length);
  assert.strictEqual("size" in t.record({ ...input, tool_response: undefined }, at(1)), false);
});

// a turn that moves to the next task after work on the first one: the turn is split at the task mark
const TWO_TASKS = [
  { t: at(0), ev: "UserPromptSubmit" },
  { t: at(1), ev: "Task", kind: "기능", name: "#1 가" },
  { t: at(2), ev: "PreToolUse", tool: "Bash", cat: "전체 게이트", id: "g" },
  { t: at(12), ev: "PostToolUse", id: "g", ok: true, size: 3000 },
  { t: at(20), ev: "Task", kind: "기능", name: "#2 나" },
  { t: at(22), ev: "PreToolUse", tool: "Read", cat: "파일 읽기", id: "r" },
  { t: at(23), ev: "PostToolUse", id: "r", ok: true, size: 100 },
  { t: at(30), ev: "Stop", output: 50, context: 1000 },
];

test("summarize: a task mark after work in the turn splits the turn between the tasks", () => {
  const s = t.summarize(TWO_TASKS);
  assert.deepStrictEqual(
    s.turns.map((r) => [r.n, r.task, r.sec, r.tools, r.think, r.output]),
    [
      ["1-1", "#1 가", 20, 10, 10, 0],
      ["1-2", "#2 나", 10, 1, 9, 50],
    ],
  );
  assert.deepStrictEqual(
    s.tasks.map((r) => [r.name, r.turns, r.sec]),
    [
      ["#1 가", 1, 20],
      ["#2 나", 1, 10],
    ],
  );
});

test("summarize: thinking time is split by what came just before it", () => {
  const s = t.summarize(TWO_TASKS);
  assert.deepStrictEqual(s.gaps, {
    "턴 시작": { count: 1, sec: 2, max: 2, size: 0 },
    "전체 게이트 뒤": { count: 1, sec: 10, max: 10, size: 3000 },
    "마지막 답변": { count: 1, sec: 7, max: 7, size: 100 },
  });
  const text = t.format(s);
  assert.match(text, /\*\*생각·답변 나눔\*\*/);
  assert.match(text, /\| 전체 게이트 뒤 \| 1 \| 10초 \| 10초 \| 10초 \| 3000 \|/);
});

test("hook: editing without a task mark reminds once, until the next task or after a merge request", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "time-log-"));
  const env = { ...process.env, CLAUDE_PROJECT_DIR: dir };
  const run = (args, input) =>
    execFileSync("node", [HOOK, ...args], { env, input: input ? JSON.stringify(input) : "" }).toString();
  const edit = { session_id: "r", hook_event_name: "PostToolUse", tool_name: "Edit", tool_use_id: "e" };
  const read = { ...edit, tool_name: "Read" };

  run([], { session_id: "r", hook_event_name: "UserPromptSubmit" });
  assert.strictEqual(run([], read), ""); // reading is not work on a task yet
  const out = JSON.parse(run([], edit));
  assert.strictEqual(out.hookSpecificOutput.hookEventName, "PostToolUse");
  assert.match(out.hookSpecificOutput.additionalContext, /mark 작업/);
  assert.strictEqual(run([], edit), ""); // once
  run(["mark", "작업", "기능", "#1"]);
  assert.strictEqual(run([], edit), "");
  run(["mark", "병합요청"]);
  assert.match(run([], edit), /mark 작업/); // the task ended with its merge request
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

  // a message sent while Claude is still answering: the turn so far gets its tokens on the new prompt line
  run([], { ...base, hook_event_name: "UserPromptSubmit" });
  fs.appendFileSync(
    transcript,
    JSON.stringify({ type: "assistant", message: { id: "n", usage: { input_tokens: 9, output_tokens: 4 } } }) + "\n",
  );
  run([], { ...base, hook_event_name: "UserPromptSubmit" });
  const last = JSON.parse(fs.readFileSync(file, "utf8").trim().split("\n").pop());
  assert.deepStrictEqual(last.prev, { output: 4, context: 9 });
});

test("end to end: the hook records the prompt kind and background starts and ends, never the prompt text", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "time-log-"));
  const env = { ...process.env, CLAUDE_PROJECT_DIR: dir };
  const run = (input) => execFileSync("node", [HOOK], { env, input: JSON.stringify(input) }).toString();
  const base = { session_id: "bg" };
  const bash = { ...base, tool_name: "Bash", tool_use_id: "u", tool_input: { command: "python tools/check.py" } };

  run({ ...base, hook_event_name: "UserPromptSubmit", prompt: "비밀 메시지" });
  run({ ...bash, hook_event_name: "PreToolUse" });
  run({ ...bash, hook_event_name: "PostToolUse", tool_response: { backgroundTaskId: "bx" } });
  run({ ...base, hook_event_name: "Stop" });
  run({
    ...base,
    hook_event_name: "UserPromptSubmit",
    prompt: "<task-notification><task-id>bx</task-id><status>completed</status><summary>비밀</summary></task-notification>",
  });

  const text = fs.readFileSync(path.join(dir, ".claude", "time-log", "bg.jsonl"), "utf8");
  assert.doesNotMatch(text, /비밀/);
  const lines = text.trim().split("\n").map((l) => JSON.parse(l));
  assert.deepStrictEqual(
    lines.map((l) => [l.ev, l.kind || l.cat || l.status || ""]),
    [
      ["UserPromptSubmit", "사람"],
      ["PreToolUse", "전체 게이트"],
      ["PostToolUse", ""],
      ["BgStart", "전체 게이트"],
      ["Stop", ""],
      ["UserPromptSubmit", "알림"],
      ["BgEnd", "completed"],
    ],
  );
  assert.deepStrictEqual([lines[3].id, lines[3].call, lines[6].id], ["bx", "u", "bx"]);
});

test("the hook never fails a tool call: bad input prints nothing and exits 0", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "time-log-"));
  const out = execFileSync("node", [HOOK], {
    env: { ...process.env, CLAUDE_PROJECT_DIR: dir },
    input: "{not json",
  }).toString();
  assert.strictEqual(out, "");
});

// Expected green: a task's kind gives its usual length, then CI (#287).
test("eta: the kind's usual length plus CI, none for an investigation", () => {
  assert.deepStrictEqual(t.eta("기능", at(0)), { sec: 720 + 190, green: at(910) });
  assert.deepStrictEqual(t.eta("버그", at(0)), { sec: 240 + 190, green: at(430) });
  assert.strictEqual(t.eta("모르는유형", at(0)).sec, 720 + 190);
  assert.strictEqual(t.eta("조사", at(0)), null);
});

test("parseMark: CI marks the result and when it ended", () => {
  assert.deepStrictEqual(t.parseMark(["CI", "초록"]), { ev: "CI", result: "초록" });
  assert.deepStrictEqual(t.parseMark(["CI", "빨강", at(5)]), { ev: "CI", result: "빨강", at: at(5) });
  assert.deepStrictEqual(t.parseMark(["CI"]), { ev: "Mark", phase: "CI" });
});

test("summarize/format: expected green against the CI result that followed the task", () => {
  const s = t.summarize([
    { t: at(0), ev: "Task", kind: "버그", name: "#1 버그", eta: at(430) },
    { t: at(600), ev: "CI", result: "초록", at: at(500) },
    { t: at(700), ev: "Task", kind: "조사", name: "#2 조사" },
  ]);
  assert.deepStrictEqual(s.etas, [{ task: "#1 버그", kind: "버그", eta: at(430), actual: at(500), diff: 70, result: "초록" }]);
  assert.match(t.format(s), /\| #1 버그 \| 버그 \| 09:07:10 \| 09:08:20 \| \+1분 10초 \| 초록 \|/);
});

test("kst: shows a UTC time as Korean time, crossing midnight", () => {
  assert.strictEqual(t.kst("2026-10-19T00:07:10.000Z"), "2026-10-19 09:07:10");
  assert.strictEqual(t.kst("2026-10-19T15:30:00.000Z"), "2026-10-20 00:30:00");
});

test("format shows the period and turn starts in Korean time", () => {
  const text = t.format(t.summarize(EVENTS));
  assert.match(text, /^기간: 2026-10-19 09:00:00 ~ 2026-10-19 09:\d\d:\d\d \(KST\)\n/);
  assert.match(text, /\| 턴 \| 작업 \| 시작\(KST\) \|/);
});

test("mark 작업 prints and keeps the expected green", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "time-log-eta-"));
  const env = { ...process.env, CLAUDE_PROJECT_DIR: dir };
  const out = execFileSync("node", [HOOK, "mark", "작업", "기능", "#3 상점"], { env }).toString();
  assert.match(out, /^예상 초록 \d\d:\d\d:\d\d KST \(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ, 작업 12분 0초 \+ CI 3분 10초\)\n$/);
  const [line] = fs.readdirSync(path.join(dir, ".claude", "time-log")).map((f) =>
    JSON.parse(fs.readFileSync(path.join(dir, ".claude", "time-log", f), "utf8")),
  );
  assert.strictEqual(Date.parse(line.eta) - Date.parse(line.t), 910 * 1000);
});
