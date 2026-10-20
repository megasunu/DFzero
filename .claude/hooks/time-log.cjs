#!/usr/bin/env node
// time-log: records how long Claude's work takes, to find what to make faster. A temporary system
// (2026-10-19, #236/#239): it stays until the user orders it removed - the list is in #237.
//
// One log per session (.claude/time-log/<session>.jsonl, not committed), three sources:
//   hook   PreToolUse / PostToolUse / PostToolUseFailure time each tool call, in a detailed category
//          (git by subcommand, gate, game tests, smoke, editing, GitHub ...) and whether it failed.
//          UserPromptSubmit / Stop bound each turn - from the user's message to the end of the answer -
//          and Stop adds the turn's output tokens and context size, read from the transcript.
//   mark   `node .claude/hooks/time-log.cjs mark 작업 <유형> <이름>` starts a task;
//          `mark <단계>` starts a phase. tools/check.py adds one GateStep line per gate step.
//   report `node .claude/hooks/time-log.cjs report [file]` - markdown tables of a log (the latest by default).
//
// The hook never blocks a tool call or a prompt: on any error it prints nothing and exits 0.

"use strict";

const fs = require("fs");
const path = require("path");

function logDir(env) {
  return path.join(env.CLAUDE_PROJECT_DIR || process.cwd(), ".claude", "time-log");
}

function logFile(dir, sessionId) {
  const safe = String(sessionId || "unknown").replace(/[^A-Za-z0-9_-]/g, "_");
  return path.join(dir, `${safe}.jsonl`);
}

// The most recently written log, or null when there is none yet.
function latestLog(dir) {
  let names;
  try {
    names = fs.readdirSync(dir).filter((n) => n.endsWith(".jsonl"));
  } catch {
    return null;
  }
  const files = names.map((n) => path.join(dir, n));
  files.sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  return files[0] || null;
}

const git = (sub) => new RegExp(`\\bgit\\s+(?:-[cC]\\s+\\S+\\s+)*(?:${sub})\\b`);
// A repository script run by python - reading or searching the file is not running it (#271).
const pyRun = (script) => new RegExp(`\\bpython[\\d.]*\\s+(?:-\\S+\\s+)*\\S*\\b${script}\\.py\\b`);

// Shell categories, heaviest first: a mixed command is timed under the first that matches.
const BASH = [
  ["저장소 저장 - 올리기", git("push")],
  ["저장소 저장 - 커밋", git("commit")],
  ["깃 - 병합", git("merge")],
  ["화면 확인", pyRun("ui_smoke")],
  ["전체 게이트", pyRun("check")],
  ["골든 갱신", /UPDATE_GOLDEN=1/],
  ["게임 테스트", /(?<!install\b[^\n;&|]*)\bpytest\b/],
  ["서식 자동 수정", /ruff\s+format(?![^\n;&|]*--check)/],
  ["서식·문법 검사", /ruff\s+(check|format)/],
  ["훅 테스트", /node\s+--test/],
  ["환경 준비", /pip3?\s+install|git\s+config/],
  ["깃 - 작업 복사본", git("worktree")],
  ["깃 - 가져오기", git("fetch|pull")],
  ["깃 - 커밋 준비", git("add")],
  ["깃 - 브랜치 전환", git("checkout|switch|branch|reset|stash")],
  ["파일 편집 - 셸", /python3?\s+-\s*<<|\bcat\s*>|\bsed\s+-i|\b(cp|mv|rm|tee)\s/],
  ["라이브러리 코드 조사", /python3?(\.\d+)?\s+-c\b/],
  ["깃 - 조회", git("status|log|diff|show|rev-parse|ls-remote|merge-base|blame")],
  ["코드 검색", /\b(grep|rg|find)\s/],
  ["파일 읽기", /\b(cat|head|tail|wc)\s|\bsed\s+-n/],
  ["환경 확인", /\b(ls|which|pwd|df|du|date)\b|--version/],
  ["시간 기록", /time-log\.cjs\s+(mark|report)\b/], // last: `mark x && <real work>` is timed as the work
];

const GROUPS = {
  "시간 기록": "기타",
  "화면 확인": "검사·실행",
  "전체 게이트": "검사·실행",
  "골든 갱신": "검사·실행",
  "게임 테스트": "검사·실행",
  "서식 자동 수정": "편집",
  "서식·문법 검사": "검사·실행",
  "훅 테스트": "검사·실행",
  "환경 준비": "환경 준비",
  "라이브러리 코드 조사": "조사",
  "코드 검색": "조사",
  "파일 읽기": "조사",
  "이미지 확인": "조사",
  "환경 확인": "조사",
  "하위 에이전트": "기타",
  스킬: "기타",
  웹: "조사",
};

function group(cat) {
  if (GROUPS[cat]) return GROUPS[cat];
  const head = cat.split(" - ")[0];
  return ["깃", "저장소 저장", "파일 편집", "깃허브", "세션"].includes(head) ? (head === "파일 편집" ? "편집" : head) : "기타";
}

function githubCategory(name, input) {
  if (/rerun/.test(String((input && input.method) || "") + name)) return "깃허브 - 자동 검사 다시 돌리기";
  if (/review|pull_request_comment/.test(name)) return "깃허브 - 병합 요청 댓글·리뷰";
  if (/pull_request/.test(name)) return "깃허브 - 병합 요청";
  if (/issue/.test(name)) return "깃허브 - 이슈";
  if (/actions|check_run|job_logs|workflow/.test(name)) return "깃허브 - 자동 검사 조회";
  return "깃허브 - 기타";
}

// Every category a tool call touches, heaviest first (only shell commands can have more than one).
function categories(tool, input) {
  if (tool === "Bash") {
    const cmd = String((input && input.command) || "");
    const hits = BASH.filter(([, re]) => re.test(cmd)).map(([cat]) => cat);
    return hits.length ? hits : ["기타 명령"];
  }
  if (["Edit", "Write", "NotebookEdit"].includes(tool)) return ["파일 편집 - 도구"];
  if (tool === "Read") {
    return [/\.(png|jpe?g|gif|webp|bmp)$/i.test(String((input && input.file_path) || "")) ? "이미지 확인" : "파일 읽기"];
  }
  if (tool === "Grep" || tool === "Glob") return ["코드 검색"];
  if (tool.startsWith("mcp__github__")) return [githubCategory(tool.slice(13), input)];
  if (tool.startsWith("mcp__claude-code-remote__")) {
    const name = tool.slice(25);
    if (/pr_activity/.test(name)) return ["깃허브 - 알림 설정"];
    if (/send_later|trigger/.test(name)) return ["세션 - 예약"];
    return ["세션 - 기타"];
  }
  if (tool === "ReadNotifications") return ["세션 - 알림 읽기"];
  if (tool === "ToolSearch") return ["세션 - 도구 불러오기"];
  if (tool === "Agent") return ["하위 에이전트"];
  if (tool === "Skill") return ["스킬"];
  if (tool === "WebFetch" || tool === "WebSearch") return ["웹"];
  return ["기타 도구"];
}

function classify(tool, input) {
  return categories(tool, input)[0];
}

// Output tokens of a transcript slice (one turn) and the context size at its last request.
function turnTokens(text) {
  const seen = new Map();
  for (const line of text.split("\n")) {
    if (!line.trim().startsWith("{")) continue;
    let e;
    try {
      e = JSON.parse(line);
    } catch {
      continue;
    }
    const usage = e.message && e.message.usage;
    if (e.isSidechain || !usage) continue;
    seen.set(e.message.id || seen.size, usage); // one message can span several lines
  }
  let output = 0;
  let context = 0;
  for (const u of seen.values()) {
    output += u.output_tokens || 0;
    context = (u.input_tokens || 0) + (u.cache_creation_input_tokens || 0) + (u.cache_read_input_tokens || 0);
  }
  return { output, context };
}

// One log line for a hook event, or null for events this log does not keep.
function record(input, now) {
  const ev = input.hook_event_name;
  if (ev === "PreToolUse") {
    const tool = String(input.tool_name || "");
    const [cat, ...also] = categories(tool, input.tool_input);
    return { t: now, ev, tool, cat, ...(also.length ? { also } : {}), id: input.tool_use_id };
  }
  if (ev === "PostToolUse" || ev === "PostToolUseFailure") {
    const line = { t: now, ev: "PostToolUse", id: input.tool_use_id, ok: ev === "PostToolUse" };
    // how much the call put into the context - to see whether long thinking follows big outputs
    if (input.tool_response !== undefined) line.size = JSON.stringify(input.tool_response).length;
    return line;
  }
  if (ev === "UserPromptSubmit") return { t: now, ev, kind: promptKind(input.prompt) };
  if (ev === "Stop") return { t: now, ev };
  return null;
}

// What started a turn: a person's message, a background task's notification, or a hook's feedback.
// Only the kind is kept - the log never holds message text (the repository is public).
function promptKind(prompt) {
  const p = String(prompt || "").trimStart();
  if (p.startsWith("<task-notification>")) return "알림";
  if (/^\w+ hook feedback:/i.test(p)) return "훅피드백";
  return "사람";
}

const BG_STATUS = ["completed", "failed", "killed"];

// The task id and status of each notification in a prompt - nothing else of it.
function notifications(prompt) {
  return String(prompt || "")
    .split("<task-notification>")
    .slice(1)
    .flatMap((part) => {
      const id = (part.match(/<task-id>([A-Za-z0-9_-]{1,64})<\/task-id>/) || [])[1];
      const status = (part.match(/<status>(\w+)<\/status>/) || [])[1];
      return id ? [{ id, status: BG_STATUS.includes(status) ? status : "기타" }] : [];
    });
}

// Extra log lines for background tasks: a start when a call answers with a background task id, an end
// when its notification comes in or when TaskStop stops it (a stopped task sends no notification).
function backgroundLines(input, now) {
  const ev = input.hook_event_name;
  if (ev === "UserPromptSubmit") {
    if (promptKind(input.prompt) !== "알림") return [];
    return notifications(input.prompt).map((n) => ({ t: now, ev: "BgEnd", ...n }));
  }
  if (ev !== "PostToolUse") return [];
  const response = input.tool_response;
  const id = response && typeof response === "object" && response.backgroundTaskId;
  if (id) return [{ t: now, ev: "BgStart", id: String(id), call: input.tool_use_id }];
  const stop = input.tool_name === "TaskStop" && (input.tool_input || {});
  const stopped = stop && (stop.task_id || stop.shell_id);
  return stopped ? [{ t: now, ev: "BgEnd", id: String(stopped), status: "stopped" }] : [];
}

function parseMark(args) {
  if (args[0] === "작업") return { ev: "Task", kind: args[1] || "기타", name: args.slice(2).join(" ") || "이름 없음" };
  return { ev: "Mark", phase: args.join(" ").trim() || "이름 없음" };
}

const ms = (iso) => Date.parse(iso);
const r1 = (sec) => Math.round(sec * 10) / 10;

// A set of [start, end] intervals merged where they overlap, in order.
function merge(intervals) {
  const merged = [];
  for (const [s, e] of [...intervals].sort((a, b) => a[0] - b[0])) {
    const cur = merged[merged.length - 1];
    if (cur && s <= cur[1]) cur[1] = Math.max(cur[1], e);
    else merged.push([s, e]);
  }
  return merged;
}

// Total length of a set of [start, end] intervals, overlaps counted once.
function unionMs(intervals) {
  return merge(intervals).reduce((sum, [s, e]) => sum + e - s, 0);
}

function overlapMs(intervals, a, b) {
  return intervals.reduce((sum, [s, e]) => sum + Math.max(0, Math.min(b, e) - Math.max(a, s)), 0);
}

function summarize(events) {
  const pre = {};
  const calls = []; // finished tool calls: {s, e, cat, ok}
  const turns = [];
  const working = [];
  const marks = [];
  const tasks = [];
  const gate = {};
  const steps = [];
  const bgStarts = [];
  const bgEnds = {};
  let open = null;
  let openKind = null;
  let stopAt = null;
  let waiting = 0;
  let bgWaiting = 0;

  const closeTurn = (end, stop, cut) => {
    turns.push({
      s: ms(open),
      e: ms(end),
      start: open,
      output: stop.output || 0,
      context: stop.context || 0,
      cut,
      kind: openKind,
    });
    working.push([ms(open), ms(end)]);
    open = null;
  };

  for (const e of events) {
    if (e.ev === "PreToolUse") pre[e.id] = e;
    else if (e.ev === "PostToolUse" && pre[e.id]) {
      const p = pre[e.id];
      calls.push({ id: e.id, s: ms(p.t), e: ms(e.t), cat: p.cat, also: p.also || [], ok: e.ok !== false, size: e.size || 0 });
      delete pre[e.id];
    } else if (e.ev === "UserPromptSubmit") {
      const kind = e.kind || "사람"; // lines written before kinds were kept are people's messages
      if (open) closeTurn(e.t, e.prev || {}, true); // a message sent while Claude was still answering
      // A gap ended by a person is waiting on the user, one ended by a notification is waiting on a
      // background task; hook feedback follows the turn at once.
      if (stopAt && kind === "사람") waiting += (ms(e.t) - ms(stopAt)) / 1000;
      if (stopAt && kind === "알림") bgWaiting += (ms(e.t) - ms(stopAt)) / 1000;
      open = e.t;
      openKind = kind;
      stopAt = null;
    } else if (e.ev === "Stop" && open) {
      closeTurn(e.t, e, false);
      stopAt = e.t;
    } else if (e.ev === "Mark") marks.push(e);
    else if (e.ev === "Task") tasks.push(e);
    else if (e.ev === "BgStart") bgStarts.push(e);
    else if (e.ev === "BgEnd") bgEnds[e.id] ||= e;
    else if (e.ev === "GateStep") {
      steps.push(e);
      const g = (gate[e.step] ||= { count: 0, fails: 0, sec: 0 });
      g.count += 1;
      g.fails += e.ok === false ? 1 : 0;
      g.sec = r1(g.sec + e.sec);
    }
  }
  const end = events.length ? events[events.length - 1].t : null;
  if (open) closeTurn(end, {}, false);
  const endMs = end ? ms(end) : 0;

  // A mark before any other work in its turn counts from the turn's start, as the turn table does for tasks.
  const snap = (x) => {
    const turn = turns.find((u) => x >= u.s && x <= u.e);
    if (!turn) return x;
    return calls.some((c) => c.s >= turn.s && c.e <= x && c.cat !== "시간 기록") ? x : turn.s;
  };
  const taskStarts = tasks.map((task) => ({ name: task.name, at: snap(ms(task.t)) }));
  const taskOf = (x) => {
    const last = taskStarts.filter((task) => task.at <= x).pop();
    return last ? last.name : "작업 없음";
  };
  const catsIn = (a, b) => {
    const cats = {};
    for (const c of calls.filter((c) => c.s >= a && c.s < b)) cats[c.cat] = r1((cats[c.cat] || 0) + (c.e - c.s) / 1000);
    return cats;
  };

  const taskAt = (t) => {
    const last = tasks.filter((k) => ms(k.t) <= t).pop();
    return last ? last.name : "작업 없음";
  };

  const turnRows = [];
  const gaps = {};
  const addGap = (label, sec, size) => {
    const g = (gaps[label] ||= { count: 0, sec: 0, max: 0, sizeSum: 0 });
    g.count += 1;
    g.sec = r1(g.sec + sec);
    g.max = Math.max(g.max, r1(sec));
    g.sizeSum += size;
  };
  turns.forEach((turn, i) => {
    const inTurn = calls.filter((c) => c.s >= turn.s && c.s <= turn.e);
    const clip = (a, b) => inTurn.map((c) => [Math.max(c.s, a), Math.min(c.e, b)]).filter(([s, e]) => e > s);
    // A task mark splits the turn only once other work in the turn has finished before it -
    // a mark at the start of a turn just names the turn's task.
    const work = inTurn.filter((c) => c.cat !== "시간 기록");
    const cuts = tasks
      .map((k) => ms(k.t))
      .filter((x) => x > turn.s && x < turn.e && work.some((c) => c.e <= x));
    const bounds = [turn.s, ...cuts, turn.e];
    for (let j = 0; j + 1 < bounds.length; j++) {
      const [a, b] = [bounds[j], bounds[j + 1]];
      const last = j + 2 === bounds.length;
      const mine = inTurn.filter((c) => c.s >= a && (last ? c.s <= b : c.s < b));
      const cats = {};
      for (const c of mine) cats[c.cat] = r1((cats[c.cat] || 0) + (c.e - c.s) / 1000);
      const sec = r1((b - a) / 1000);
      const tools = r1(unionMs(clip(a, b)) / 1000);
      turnRows.push({
        n: bounds.length > 2 ? `${i + 1}-${j + 1}` : i + 1,
        start: new Date(a).toISOString(),
        sec,
        tools,
        think: r1(sec - tools),
        output: last ? turn.output : 0,
        context: last ? turn.context : 0,
        task: taskAt(last ? b : b - 1),
        fails: mine.filter((c) => !c.ok).length,
        cats,
        cut: last && turn.cut,
        kind: turn.kind,
      });
    }
    // Thinking and answering time, by what came just before it: the user's message, a tool's result, or
    // (after the last tool) the final answer.
    let cursor = turn.s;
    const holes = [];
    for (const [s, e] of merge(clip(turn.s, turn.e))) {
      if (s > cursor) holes.push([cursor, s]);
      cursor = Math.max(cursor, e);
    }
    if (turn.e > cursor) holes.push([cursor, turn.e]);
    for (const [s, e] of holes) {
      const before = inTurn.filter((c) => c.e <= s).sort((x, y) => x.e - y.e).pop();
      const label = !before ? (e === turn.e ? "도구 없는 턴" : "턴 시작") : e === turn.e ? "마지막 답변" : `${before.cat} 뒤`;
      addGap(label, (e - s) / 1000, before ? before.size : 0);
    }
  });
  for (const g of Object.values(gaps)) {
    g.size = Math.round(g.sizeSum / g.count);
    delete g.sizeSum;
  }

  const categoryRows = {};
  for (const c of calls) {
    const row = (categoryRows[c.cat] ||= { count: 0, fails: 0, sec: 0 });
    row.count += 1;
    row.fails += c.ok ? 0 : 1;
    row.sec = r1(row.sec + (c.e - c.s) / 1000);
  }

  const taskRows = [];
  for (const turn of turnRows) {
    let row = taskRows.find((r) => r.name === turn.task);
    if (!row) {
      const k = tasks.find((x) => x.name === turn.task);
      row = { name: turn.task, kind: k ? k.kind : "-", turns: 0, sec: 0, think: 0, tools: 0, fails: 0 };
      taskRows.push(row);
    }
    row.turns += 1;
    row.sec = r1(row.sec + turn.sec);
    row.think = r1(row.think + turn.think);
    row.tools = r1(row.tools + turn.tools);
    row.fails += turn.fails;
  }

  // Phases per task: a task mark starts its phases over, and its time before the first phase mark is
  // "단계 없음". Only working time counts, as everywhere else.
  const phases = [];
  const spans = [{ name: "작업 없음", at: events.length ? ms(events[0].t) : 0 }, ...taskStarts];
  spans.forEach((span, i) => {
    const b = i + 1 < spans.length ? spans[i + 1].at : endMs;
    const own = marks.map((m) => ({ phase: m.phase, at: snap(ms(m.t)) })).filter((m) => m.at >= span.at && m.at < b);
    const points = [{ phase: "단계 없음", at: span.at }, ...own];
    points.forEach((p, j) => {
      const q = j + 1 < points.length ? points[j + 1].at : b;
      const sec = r1(overlapMs(working, p.at, q) / 1000);
      if (j === 0 && sec === 0) return;
      phases.push({ task: span.name, phase: p.phase, sec, cats: catsIn(p.at, q) });
    });
  });

  // Background tasks run from their call until their notification (or TaskStop, or the end of the log).
  const bgRange = (b) => {
    const call = calls.find((c) => c.id === b.call);
    return [call ? call.s : ms(b.t), bgEnds[b.id] ? ms(bgEnds[b.id].t) : endMs];
  };
  const background = {};
  for (const b of bgStarts) {
    const [a, z] = bgRange(b);
    const busy = overlapMs(working, a, z) / 1000;
    const row = (background[b.cat || "기타 명령"] ||= { count: 0, sec: 0, busy: 0, idle: 0 });
    row.count += 1;
    row.sec = r1(row.sec + (z - a) / 1000);
    row.busy = r1(row.busy + busy);
    row.idle = r1(row.idle + (z - a) / 1000 - busy);
  }

  // Gate runs: each gate call (until its background task ends, if it ran in the background) with the
  // steps check.py wrote meanwhile; steps outside any call are grouped into runs of their own.
  const bgEndOf = {};
  for (const b of bgStarts) bgEndOf[b.call] = bgRange(b)[1];
  const callRuns = calls
    .filter((c) => c.cat === "전체 게이트")
    .map((c) => ({ s: c.s, e: Math.max(c.e, bgEndOf[c.id] || 0), ok: c.ok, call: c, steps: [] }));
  const runs = [...callRuns];
  let loose = null;
  for (const st of steps) {
    const x = ms(st.t);
    const run = callRuns.find((r) => x >= r.s && x <= r.e);
    if (run) {
      run.steps.push(st);
      continue;
    }
    const from = x - st.sec * 1000;
    if (!loose || loose.steps.some((p) => p.step === st.step) || from - loose.e > 120000) {
      loose = { s: from, e: x, ok: true, call: null, steps: [] };
      runs.push(loose);
    }
    loose.steps.push(st);
    loose.e = x;
  }
  // check.py always writes its steps, so a "gate" call without any never got to run it.
  const realRuns = runs.filter((run) => run.steps.length).sort((a, b) => a.s - b.s);

  const SINCE = ["골든 갱신", "서식 자동 수정", "편집"];
  const sinceLabels = (cats) =>
    new Set(cats.map((cat) => (SINCE.includes(cat) ? cat : group(cat) === "편집" ? "편집" : null)).filter(Boolean));
  const result = (run) => {
    const failed = run.steps.filter((st) => st.ok === false).map((st) => st.step);
    const ok = run.steps.length ? !failed.length : run.ok;
    const text = ok ? "통과" : failed.length ? `실패(${failed.join(", ")})` : "실패";
    return run.kind === "빠른" ? `빠른 ${text}` : text;
  };
  const gateRuns = [];
  const seen = {};
  realRuns.forEach((run, i) => {
    run.kind = run.steps.some((st) => st.step === "pytest(빠른)") ? "빠른" : "전체";
    run.task = taskOf(run.s);
    const prev = realRuns.slice(0, i).filter((r) => r.task === run.task).pop();
    let since = "-";
    if (prev) {
      const counts = {};
      const between = calls.filter((c) => c.s >= prev.e && c.s < run.s && c !== run.call);
      const lists = [...between.map((c) => [c.cat, ...c.also]), run.call ? run.call.also : []];
      for (const cats of lists) for (const label of sinceLabels(cats)) counts[label] = (counts[label] || 0) + 1;
      since = SINCE.filter((label) => counts[label]).map((label) => `${label} ${counts[label]}`).join(", ") || "없음";
    }
    const key = `${run.task}\n${run.kind}`;
    seen[key] = (seen[key] || 0) + 1;
    gateRuns.push({ task: run.task, kind: run.kind, n: seen[key], sec: r1((run.e - run.s) / 1000), prev: prev ? result(prev) : "-", since });
  });

  return {
    start: events.length ? events[0].t : null,
    end,
    waiting: r1(waiting),
    bgWaiting: r1(bgWaiting),
    background,
    gateRuns,
    unfinished: Object.keys(pre).length,
    turns: turnRows,
    tasks: taskRows,
    categories: categoryRows,
    gate,
    phases,
    gaps,
  };
}

function dur(sec) {
  const whole = Math.round(sec);
  if (whole >= 60) return `${Math.floor(whole / 60)}분 ${whole % 60}초`;
  return Number.isInteger(sec) ? `${sec}초` : `${sec.toFixed(1)}초`;
}

const k = (n) => (n >= 1000 ? `${Math.round(n / 1000)}k` : String(n));

const top = (cats) =>
  Object.entries(cats)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([cat, sec]) => `${cat} ${dur(sec)}`)
    .join(", ") || "-";

const STARTED_BY = { 알림: " (알림)", 훅피드백: " (훅)" };

function format(s) {
  const out = [
    `기간: ${s.start} ~ ${s.end} (UTC)`,
    `사용자 대기: ${dur(s.waiting)} / 백그라운드 대기: ${dur(s.bgWaiting || 0)} / ` +
      `끝나지 않은 도구 호출(거부·중단): ${s.unfinished}`,
    "",
    "**작업별**",
    "",
    "| 작업 | 유형 | 턴 | 걸린 시간 | 생각·답변 | 도구 | 실패 |",
    "|---|---|---|---|---|---|---|",
    ...s.tasks.map(
      (r) => `| ${r.name} | ${r.kind} | ${r.turns} | ${dur(r.sec)} | ${dur(r.think)} | ${dur(r.tools)} | ${r.fails} |`,
    ),
  ];
  if (s.phases.length) {
    out.push(
      "",
      '**작업별 단계** (사용자 대기 제외, 작업의 첫 단계 표시 전은 "단계 없음")',
      "",
      "| 작업 | 단계 | 시간 | 주요 도구 |",
      "|---|---|---|---|",
      ...s.phases.map((p) => `| ${p.task} | ${p.phase} | ${dur(p.sec)} | ${top(p.cats)} |`),
    );
  }
  out.push(
    "",
    "**턴별** (사용자 메시지부터 답을 마칠 때까지, `+`는 답하는 도중 새 메시지가 와서 나뉜 턴, " +
      "(알림)은 백그라운드 작업의 알림으로 시작한 턴)",
    "",
    "| 턴 | 작업 | 시작(UTC) | 걸린 시간 | 생각·답변 | 도구 | 실패 | 맥락 | 출력 토큰 | 주요 도구 |",
    "|---|---|---|---|---|---|---|---|---|---|",
    ...s.turns.map(
      (r) =>
        `| ${r.n}${r.cut ? "+" : ""}${STARTED_BY[r.kind] || ""} | ${r.task} | ${r.start.slice(11, 19)} | ${dur(r.sec)} | ` +
        `${dur(r.think)} | ${dur(r.tools)} | ${r.fails} | ${k(r.context)} | ${r.output} | ${top(r.cats)} |`,
    ),
    "",
    "**분류별**",
    "",
    "| 묶음 | 분류 | 횟수 | 실패 | 합계 | 평균 |",
    "|---|---|---|---|---|---|",
    ...Object.entries(s.categories)
      .sort((a, b) => b[1].sec - a[1].sec)
      .map(([cat, c]) => `| ${group(cat)} | ${cat} | ${c.count} | ${c.fails} | ${dur(c.sec)} | ${dur(r1(c.sec / c.count))} |`),
  );
  const gaps = Object.entries(s.gaps || {});
  if (gaps.length) {
    out.push(
      "",
      "**생각·답변 나눔** (도구가 돌지 않은 시간을 바로 앞의 일로 묶는다, 앞 출력 = 그 도구가 돌려준 글자 수 평균)",
      "",
      "| 바로 앞 | 횟수 | 합계 | 평균 | 가장 긴 | 앞 출력 |",
      "|---|---|---|---|---|---|",
      ...gaps
        .sort((a, b) => b[1].sec - a[1].sec)
        .map(([label, g]) => `| ${label} | ${g.count} | ${dur(g.sec)} | ${dur(r1(g.sec / g.count))} | ${dur(g.max)} | ${g.size} |`),
    );
  }
  const gate = Object.entries(s.gate);
  if (gate.length) {
    out.push("", "**게이트 단계별**", "", "| 단계 | 횟수 | 실패 | 합계 | 평균 |", "|---|---|---|---|---|");
    out.push(...gate.map(([step, g]) => `| ${step} | ${g.count} | ${g.fails} | ${dur(g.sec)} | ${dur(r1(g.sec / g.count))} |`));
  }
  const runs = s.gateRuns || [];
  if (runs.length) {
    out.push(
      "",
      "**게이트 회차** (회차는 그 작업 안에서 전체/빠른 따로, 그 사이 = 직전 게이트가 끝난 뒤 이 게이트까지)",
      "",
      "| 작업 | 회차 | 시간 | 직전 결과 | 그 사이 있었던 일 |",
      "|---|---|---|---|---|",
      ...runs.map((g) => `| ${g.task} | ${g.kind} ${g.n} | ${dur(g.sec)} | ${g.prev} | ${g.since} |`),
    );
  }
  const bg = Object.entries(s.background || {});
  if (bg.length) {
    out.push(
      "",
      "**백그라운드** (호출부터 알림·멈춤까지, 다른 일 = 그동안 Claude가 턴 안에 있던 시간)",
      "",
      "| 분류 | 횟수 | 실제로 돈 시간 | 그동안 다른 일 | 기다리기만 |",
      "|---|---|---|---|---|",
      ...bg.map(([cat, b]) => `| ${cat} | ${b.count} | ${dur(b.sec)} | ${dur(b.busy)} | ${dur(b.idle)} |`),
    );
  }
  return out.join("\n") + "\n";
}

function readLog(file) {
  return fs
    .readFileSync(file, "utf8")
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => {
      try {
        return JSON.parse(l);
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}

function append(file, line) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.appendFileSync(file, JSON.stringify(line) + "\n");
}

function readFrom(file, offset) {
  const size = fs.statSync(file).size;
  const fd = fs.openSync(file, "r");
  try {
    const buf = Buffer.alloc(Math.max(0, size - offset));
    fs.readSync(fd, buf, 0, buf.length, offset);
    return buf.toString("utf8");
  } finally {
    fs.closeSync(fd);
  }
}

const REMINDER =
  "작업시간 기록: 작업 표시 없이 편집을 시작했다. 새 작업이면 먼저 " +
  '`node .claude/hooks/time-log.cjs mark 작업 <유형> "#이슈 제목"`을 찍는다(time-log 스킬). 이어지는 작업이면 무시한다.';

// After an edit: a reminder (once) when no task is open - none was marked yet, or the last one ended with
// its merge request. Without it the time lands on "작업 없음" or on the previous task.
function reminder(input, file) {
  if (input.hook_event_name !== "PostToolUse" || group(classify(String(input.tool_name || ""), input.tool_input)) !== "편집")
    return null;
  const events = fs.existsSync(file) ? readLog(file) : [];
  const lastIndex = (pred) => events.reduce((found, e, i) => (pred(e) ? i : found), -1);
  const task = lastIndex((e) => e.ev === "Task");
  const ended = lastIndex((e) => e.ev === "Mark" && e.phase === "병합요청");
  const reminded = lastIndex((e) => e.ev === "Reminder");
  if ((task >= 0 && ended < task) || reminded > Math.max(task, ended)) return null;
  append(file, { t: new Date().toISOString(), ev: "Reminder" });
  return { hookSpecificOutput: { hookEventName: "PostToolUse", additionalContext: REMINDER } };
}

function hook(input, dir) {
  const line = record(input, new Date().toISOString());
  if (!line) return null;
  const file = logFile(dir, input.session_id);
  const transcript = input.transcript_path;
  if (line.ev === "UserPromptSubmit" && transcript && fs.existsSync(transcript)) {
    line.off = fs.statSync(transcript).size;
    // A prompt while the last turn has no Stop yet: that turn is cut here, keep its tokens on this line.
    const events = fs.existsSync(file) ? readLog(file) : [];
    const last = events.filter((e) => e.ev === "UserPromptSubmit" || e.ev === "Stop").pop();
    if (last && last.ev === "UserPromptSubmit" && typeof last.off === "number") {
      line.prev = turnTokens(readFrom(transcript, last.off));
    }
  }
  if (line.ev === "Stop" && transcript && fs.existsSync(transcript) && fs.existsSync(file)) {
    const prompt = readLog(file)
      .filter((e) => e.ev === "UserPromptSubmit")
      .pop();
    if (prompt && typeof prompt.off === "number") Object.assign(line, turnTokens(readFrom(transcript, prompt.off)));
  }
  append(file, line);
  for (const extra of backgroundLines(input, line.t)) {
    if (extra.ev === "BgStart") {
      const call = readLog(file).find((e) => e.ev === "PreToolUse" && e.id === extra.call);
      extra.cat = call ? call.cat : "기타 명령";
    }
    append(file, extra);
  }
  return reminder(input, file);
}

function main(argv, env) {
  const dir = logDir(env);
  if (argv[0] === "mark") {
    append(latestLog(dir) || logFile(dir, "manual"), { t: new Date().toISOString(), ...parseMark(argv.slice(1)) });
    return;
  }
  if (argv[0] === "report") {
    const file = argv[1] || latestLog(dir);
    process.stdout.write(file ? format(summarize(readLog(file))) : "기록 없음\n");
    return;
  }
  let raw = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => (raw += chunk));
  process.stdin.on("end", () => {
    try {
      const output = hook(JSON.parse(raw || "{}"), dir);
      if (output) process.stdout.write(JSON.stringify(output));
    } catch {
      /* never block a tool call or a prompt because of this hook */
    }
  });
}

if (require.main === module) main(process.argv.slice(2), process.env);

module.exports = {
  categories,
  classify,
  group,
  turnTokens,
  record,
  promptKind,
  backgroundLines,
  parseMark,
  summarize,
  format,
  dur,
  logFile,
  latestLog,
};
