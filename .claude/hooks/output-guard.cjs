#!/usr/bin/env node
// output-guard: warns before a tool call that would pour far more text into the context than the
// task needs (#388). Measured on the launcher/mechanic session: code search 106k chars, whole-file
// reads 82k, shell edits 65k - the three biggest tool-result groups, and the skill's "keep output
// short" rule alone did not hold them back.
//
// PreToolUse, Bash and Read. It warns as additionalContext and never blocks: no permission decision,
// and on any error it prints nothing and exits 0. Claude goes ahead if the whole output is needed.
//   Read      a file over READ_LINES lines without offset/limit
//   cat       a file over READ_LINES lines, not piped into a filter (heredocs/redirects are writes)
//   sed -n    a range wider than SED_LINES lines
//   search    recursive grep / rg / git grep with no length or count limit and no pipe
//   script    a heredoc command over SCRIPT_CHARS chars (git commands aside): the text sent stays in
//             the context, and a shell edit of a file read before also brings back the changed lines
// The limits are judgement (2026-10-23), not measured optima.

"use strict";

const fs = require("fs");
const path = require("path");

const READ_LINES = 150;
const SED_LINES = 80;
const SCRIPT_CHARS = 1500;
const MAX_BYTES = 20 * 1024 * 1024; // do not count lines of anything bigger

function lineCounter(cwd) {
  return (file) => {
    try {
      const full = path.resolve(cwd || process.cwd(), file);
      const stat = fs.statSync(full);
      if (!stat.isFile() || stat.size > MAX_BYTES) return null;
      const text = fs.readFileSync(full, "utf8");
      return text.split("\n").length - (text.endsWith("\n") ? 1 : 0);
    } catch {
      return null;
    }
  };
}

const words = (stage) => stage.trim().split(/\s+/).filter(Boolean);
const shortFlags = (ws) =>
  ws.filter((w) => /^-[A-Za-z]/.test(w)).map((w) => w.slice(1)).join("").replace(/[0-9]/g, "");

function readWhole(file, n) {
  return (
    `output-guard: ${file}는 ${n}줄이다 - 통째로 읽으면 그대로 맥락에 쌓인다. ` +
    "grep -n으로 위치를 찾고 범위(offset/limit, sed -n 'A,Bp')로 필요한 40줄 안팎만 읽는다. 전체가 꼭 필요하면 그대로 진행한다."
  );
}

function unlimitedSearch(ws) {
  const [cmd, sub] = ws;
  const flags = shortFlags(ws);
  const long = ws.filter((w) => w.startsWith("--"));
  if (cmd === "grep" || cmd === "egrep") {
    if (!/[rR]/.test(flags)) return false;
    return !/[lLcoqm]/.test(flags) && !long.some((w) => /^--(files-with|count|max-count)/.test(w));
  }
  if (cmd === "rg" || (cmd === "git" && sub === "grep")) {
    return !/[lLcoqmM]/.test(flags) && !long.some((w) => /^--(files-with|count|max-count|max-columns)/.test(w));
  }
  return false;
}

function checkBash(command, countLines) {
  const warnings = [];
  const first = command.split("\n")[0];
  for (const segment of first.split(/&&|\|\||;/)) {
    const stages = segment.split("|");
    if (stages.length > 1) continue; // piped into head/grep/cut/wc ...
    const ws = words(stages[0]);
    if (ws[0] === "cat" && !/[<>]/.test(segment)) {
      for (const file of ws.slice(1).filter((w) => !w.startsWith("-"))) {
        const n = countLines(file);
        if (n !== null && n > READ_LINES) warnings.push(readWhole(file, n));
      }
    }
    const sed = /\bsed\s+-n\s+['"]?(\d+),(\d+)p/.exec(segment);
    if (sed && Number(sed[2]) - Number(sed[1]) + 1 > SED_LINES) {
      const n = Number(sed[2]) - Number(sed[1]) + 1;
      warnings.push(
        `output-guard: sed -n 범위가 ${n}줄이다. 필요한 곳을 grep -n으로 찾아 ${SED_LINES}줄 안으로 좁힌다. 전체가 꼭 필요하면 그대로 진행한다.`
      );
    }
    if (unlimitedSearch(ws)) {
      warnings.push(
        "output-guard: 줄 길이·개수 제한 없는 재귀 검색이다(데이터 파일은 한 줄이 수백 자). " +
          "파일부터 찾거나(grep -rl, rg -l) `| cut -c1-200 | head -30`, rg --max-columns 200을 붙인다."
      );
    }
  }
  const gitOnly = /^\s*(cd\s+[^&;]*(&&|;)\s*)?git\b/.test(first);
  if (command.length > SCRIPT_CHARS && command.includes("<<") && !gitOnly) {
    warnings.push(
      `output-guard: ${command.length}자짜리 스크립트다 - 보낸 글이 그대로 맥락에 남는다. ` +
        "있는 파일의 몇 줄을 바꾸는 것이면 Edit 도구로 바뀌는 줄만 보낸다(셸 편집은 바뀐 줄이 알림으로 다시 붙는다). 새 파일 본문이면 무시한다."
    );
  }
  return warnings;
}

// Pure decision: the warning text for one hook input, or null. countLines(file) -> lines or null.
function decide(input, countLines) {
  if (!input || input.hook_event_name !== "PreToolUse") return null;
  const tool = input.tool_input || {};
  let warnings = [];
  if (input.tool_name === "Read" && tool.file_path && tool.offset == null && tool.limit == null) {
    const n = countLines(tool.file_path);
    if (n !== null && n > READ_LINES) warnings.push(readWhole(tool.file_path, n));
  } else if (input.tool_name === "Bash" && typeof tool.command === "string") {
    warnings = checkBash(tool.command, countLines);
  }
  return warnings.length ? warnings.join("\n") : null;
}

function main() {
  let raw = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => (raw += chunk));
  process.stdin.on("end", () => {
    try {
      const input = JSON.parse(raw || "{}");
      const warning = decide(input, lineCounter(input.cwd));
      if (!warning) return;
      process.stdout.write(
        JSON.stringify({ hookSpecificOutput: { hookEventName: "PreToolUse", additionalContext: warning } })
      );
    } catch {
      /* never stand in the way of a tool call */
    }
  });
}

if (require.main === module) main();

module.exports = { decide, lineCounter, READ_LINES, SED_LINES, SCRIPT_CHARS };
