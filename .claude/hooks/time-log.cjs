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

// Shell categories, heaviest first: a mixed command is timed under the first that matches.
const BASH = [
  ["저장소 저장 - 올리기", git("push")],
  ["저장소 저장 - 커밋", git("commit")],
  ["깃 - 병합", git("merge")],
  ["화면 확인", /ui_smoke/],
  ["전체 게이트", /check\.py/],
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
    return { t: now, ev: "PostToolUse", id: input.tool_use_id, ok: ev === "PostToolUse" };
  }
  if (ev === "UserPromptSubmit" || ev === "Stop") return { t: now, ev };
  return null;
}

function parseMark(args) {
  if (args[0] === "작업") return { ev: "Task", kind: args[1] || "기타", name: args.slice(2).join(" ") || "이름 없음" };
  return { ev: "Mark", phase: args.join(" ").trim() || "이름 없음" };
}

const ms = (iso) => Date.parse(iso);
const r1 = (sec) => Math.round(sec * 10) / 10;

// Total length of a set of [start, end] intervals, overlaps counted once.
function unionMs(intervals) {
  const sorted = [...intervals].sort((a, b) => a[0] - b[0]);
  let total = 0;
  let cur = null;
  for (const [s, e] of sorted) {
    if (!cur || s > cur[1]) {
      if (cur) total += cur[1] - cur[0];
      cur = [s, e];
    } else cur[1] = Math.max(cur[1], e);
  }
  return cur ? total + cur[1] - cur[0] : total;
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
  let open = null;
  let stopAt = null;
  let waiting = 0;

  const closeTurn = (end, stop, cut) => {
    turns.push({ s: ms(open), e: ms(end), start: open, output: stop.output || 0, context: stop.context || 0, cut });
    working.push([ms(open), ms(end)]);
    open = null;
  };

  for (const e of events) {
    if (e.ev === "PreToolUse") pre[e.id] = e;
    else if (e.ev === "PostToolUse" && pre[e.id]) {
      calls.push({ s: ms(pre[e.id].t), e: ms(e.t), cat: pre[e.id].cat, ok: e.ok !== false });
      delete pre[e.id];
    } else if (e.ev === "UserPromptSubmit") {
      if (open) closeTurn(e.t, e.prev || {}, true); // a message sent while Claude was still answering
      if (stopAt) waiting += (ms(e.t) - ms(stopAt)) / 1000;
      open = e.t;
      stopAt = null;
    } else if (e.ev === "Stop" && open) {
      closeTurn(e.t, e, false);
      stopAt = e.t;
    } else if (e.ev === "Mark") marks.push(e);
    else if (e.ev === "Task") tasks.push(e);
    else if (e.ev === "GateStep") {
      const g = (gate[e.step] ||= { count: 0, fails: 0, sec: 0 });
      g.count += 1;
      g.fails += e.ok === false ? 1 : 0;
      g.sec = r1(g.sec + e.sec);
    }
  }
  const end = events.length ? events[events.length - 1].t : null;
  if (open) closeTurn(end, {}, false);

  const taskAt = (t) => {
    const last = tasks.filter((k) => ms(k.t) <= t).pop();
    return last ? last.name : "작업 없음";
  };

  const turnRows = turns.map((turn, i) => {
    const mine = calls.filter((c) => c.s >= turn.s && c.s <= turn.e);
    const cats = {};
    for (const c of mine) cats[c.cat] = r1((cats[c.cat] || 0) + (c.e - c.s) / 1000);
    const sec = r1((turn.e - turn.s) / 1000);
    const tools = r1(unionMs(mine.map((c) => [c.s, Math.min(c.e, turn.e)])) / 1000);
    return {
      n: i + 1,
      start: turn.start,
      sec,
      tools,
      think: r1(sec - tools),
      output: turn.output,
      context: turn.context,
      task: taskAt(turn.e),
      fails: mine.filter((c) => !c.ok).length,
      cats,
      cut: turn.cut,
    };
  });

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

  const phases = marks.map((m, i) => ({
    phase: m.phase,
    sec: r1(overlapMs(working, ms(m.t), ms(i + 1 < marks.length ? marks[i + 1].t : end)) / 1000),
  }));

  return {
    start: events.length ? events[0].t : null,
    end,
    waiting: r1(waiting),
    unfinished: Object.keys(pre).length,
    turns: turnRows,
    tasks: taskRows,
    categories: categoryRows,
    gate,
    phases,
  };
}

function dur(sec) {
  const whole = Math.round(sec);
  if (whole >= 60) return `${Math.floor(whole / 60)}분 ${whole % 60}초`;
  return Number.isInteger(sec) ? `${sec}초` : `${sec.toFixed(1)}초`;
}

const k = (n) => (n >= 1000 ? `${Math.round(n / 1000)}k` : String(n));

function format(s) {
  const out = [
    `기간: ${s.start} ~ ${s.end} (UTC)`,
    `사용자 대기: ${dur(s.waiting)} / 끝나지 않은 도구 호출(거부·중단): ${s.unfinished}`,
    "",
    "**작업별**",
    "",
    "| 작업 | 유형 | 턴 | 걸린 시간 | 생각·답변 | 도구 | 실패 |",
    "|---|---|---|---|---|---|---|",
    ...s.tasks.map(
      (r) => `| ${r.name} | ${r.kind} | ${r.turns} | ${dur(r.sec)} | ${dur(r.think)} | ${dur(r.tools)} | ${r.fails} |`,
    ),
    "",
    "**턴별** (사용자 메시지부터 답을 마칠 때까지, `+`는 답하는 도중 새 메시지가 와서 나뉜 턴)",
    "",
    "| 턴 | 작업 | 시작(UTC) | 걸린 시간 | 생각·답변 | 도구 | 실패 | 맥락 | 출력 토큰 | 주요 도구 |",
    "|---|---|---|---|---|---|---|---|---|---|",
    ...s.turns.map((r) => {
      const top = Object.entries(r.cats)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([cat, sec]) => `${cat} ${dur(sec)}`)
        .join(", ");
      return (
        `| ${r.n}${r.cut ? "+" : ""} | ${r.task} | ${r.start.slice(11, 19)} | ${dur(r.sec)} | ${dur(r.think)} | ${dur(r.tools)} | ` +
        `${r.fails} | ${k(r.context)} | ${r.output} | ${top || "-"} |`
      );
    }),
    "",
    "**분류별**",
    "",
    "| 묶음 | 분류 | 횟수 | 실패 | 합계 | 평균 |",
    "|---|---|---|---|---|---|",
    ...Object.entries(s.categories)
      .sort((a, b) => b[1].sec - a[1].sec)
      .map(([cat, c]) => `| ${group(cat)} | ${cat} | ${c.count} | ${c.fails} | ${dur(c.sec)} | ${dur(r1(c.sec / c.count))} |`),
  ];
  const gate = Object.entries(s.gate);
  if (gate.length) {
    out.push("", "**게이트 단계별**", "", "| 단계 | 횟수 | 실패 | 합계 | 평균 |", "|---|---|---|---|---|");
    out.push(...gate.map(([step, g]) => `| ${step} | ${g.count} | ${g.fails} | ${dur(g.sec)} | ${dur(r1(g.sec / g.count))} |`));
  }
  if (s.phases.length) {
    out.push("", "**단계별** (사용자 대기 제외)", "", "| 단계 | 작업 시간 |", "|---|---|");
    out.push(...s.phases.map((p) => `| ${p.phase} | ${dur(p.sec)} |`));
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

function hook(input, dir) {
  const line = record(input, new Date().toISOString());
  if (!line) return;
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
      hook(JSON.parse(raw || "{}"), dir);
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
  parseMark,
  summarize,
  format,
  dur,
  logFile,
  latestLog,
};
