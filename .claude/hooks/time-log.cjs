#!/usr/bin/env node
// time-log: records how long Claude's work takes, so the user can see which kinds of work are slow.
// A temporary system (2026-10-19, about one week, then removed - see the time-log skill).
//
// Three ways, one log (.claude/time-log/<session>.jsonl, not committed):
//   hook        PreToolUse / PostToolUse time each tool call and put it in a category;
//               UserPromptSubmit / Stop split Claude's working time from time waiting for the user.
//   mark        `node .claude/hooks/time-log.cjs mark <phase>` - Claude stamps the start of a phase
//               (계획, 테스트 작성, 구현, 게이트, ...). A phase runs until the next mark.
//   report      `node .claude/hooks/time-log.cjs report [file]` - a markdown summary of a log
//               (the latest one by default), for the issue comment written after each task.
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

function classify(tool, input) {
  if (["Edit", "Write", "NotebookEdit"].includes(tool)) return "편집";
  if (["Read", "Grep", "Glob"].includes(tool)) return "조사";
  if (tool === "Bash") {
    const cmd = String((input && input.command) || "");
    if (/time-log\.cjs/.test(cmd)) return "시간 기록";
    if (/ui_smoke/.test(cmd)) return "화면 확인";
    if (/check\.py|pytest|ruff|node --test/.test(cmd)) return "게이트";
    if (/(^|[\s;&|])git\s/.test(cmd)) return "깃";
    return "명령";
  }
  if (tool.startsWith("mcp__github__")) return "깃허브";
  if (tool === "Agent") return "하위 에이전트";
  if (tool === "Skill") return "스킬";
  return "기타";
}

// One log line for a hook event, or null for events this log does not keep.
function record(input, now) {
  const ev = input.hook_event_name;
  if (ev === "PreToolUse" || ev === "PostToolUse") {
    const tool = String(input.tool_name || "");
    return { t: now, ev, tool, cat: classify(tool, input.tool_input), id: input.tool_use_id };
  }
  if (ev === "UserPromptSubmit" || ev === "Stop") return { t: now, ev };
  return null;
}

function secs(from, to) {
  return Math.max(0, Math.round((Date.parse(to) - Date.parse(from)) / 1000));
}

// Seconds of [from, to) that fall inside the working intervals.
function overlap(intervals, from, to) {
  const a = Date.parse(from);
  const b = Date.parse(to);
  let ms = 0;
  for (const [s, e] of intervals) ms += Math.max(0, Math.min(b, e) - Math.max(a, s));
  return Math.round(ms / 1000);
}

function summarize(events) {
  const categories = {};
  const open = {};
  const working = [];
  let promptAt = null;
  let stopAt = null;
  let waiting = 0;
  const marks = [];

  for (const e of events) {
    if (e.ev === "PreToolUse") open[e.id] = e;
    else if (e.ev === "PostToolUse" && open[e.id]) {
      const c = (categories[open[e.id].cat] ||= { sec: 0, count: 0 });
      c.sec += secs(open[e.id].t, e.t);
      c.count += 1;
      delete open[e.id];
    } else if (e.ev === "UserPromptSubmit") {
      if (promptAt) working.push([Date.parse(promptAt), Date.parse(e.t)]); // a turn without Stop
      if (stopAt) waiting += secs(stopAt, e.t);
      promptAt = e.t;
      stopAt = null;
    } else if (e.ev === "Stop" && promptAt) {
      working.push([Date.parse(promptAt), Date.parse(e.t)]);
      promptAt = null;
      stopAt = e.t;
    } else if (e.ev === "Mark") marks.push(e);
  }

  const end = events.length ? events[events.length - 1].t : null;
  if (promptAt) working.push([Date.parse(promptAt), Date.parse(end)]);
  const phases = marks.map((m, i) => ({
    phase: m.phase,
    sec: overlap(working, m.t, i + 1 < marks.length ? marks[i + 1].t : end),
  }));

  return {
    start: events.length ? events[0].t : null,
    end,
    working: working.reduce((sum, [s, e]) => sum + Math.round((e - s) / 1000), 0),
    waiting,
    categories,
    phases,
  };
}

function dur(sec) {
  return sec >= 60 ? `${Math.floor(sec / 60)}분 ${sec % 60}초` : `${sec}초`;
}

function format(s) {
  const rows = Object.entries(s.categories).sort((a, b) => b[1].sec - a[1].sec);
  const out = [
    `기간: ${s.start} ~ ${s.end} (UTC)`,
    `Claude 작업: ${dur(s.working)} / 사용자 대기: ${dur(s.waiting)}`,
    "",
    "| 분류 | 횟수 | 도구 시간 |",
    "|---|---|---|",
    ...rows.map(([cat, c]) => `| ${cat} | ${c.count} | ${dur(c.sec)} |`),
  ];
  if (s.phases.length) {
    out.push("", "| 단계 | 작업 시간 |", "|---|---|", ...s.phases.map((p) => `| ${p.phase} | ${dur(p.sec)} |`));
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

function main(argv, env) {
  const dir = logDir(env);
  if (argv[0] === "mark") {
    const phase = argv.slice(1).join(" ").trim() || "이름 없음";
    append(latestLog(dir) || logFile(dir, "manual"), { t: new Date().toISOString(), ev: "Mark", phase });
    return;
  }
  if (argv[0] === "report") {
    const file = argv[1] || latestLog(dir);
    if (!file) {
      process.stdout.write("기록 없음\n");
      return;
    }
    process.stdout.write(format(summarize(readLog(file))));
    return;
  }
  let raw = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => (raw += chunk));
  process.stdin.on("end", () => {
    try {
      const input = JSON.parse(raw || "{}");
      const line = record(input, new Date().toISOString());
      if (line) append(logFile(dir, input.session_id), line);
    } catch {
      /* never block a tool call or a prompt because of this hook */
    }
  });
}

if (require.main === module) main(process.argv.slice(2), process.env);

module.exports = { classify, record, summarize, format, logFile, latestLog };
