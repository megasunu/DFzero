#!/usr/bin/env python3
"""이슈와 megasunu 작업 보드(조직 Project)를 잇는 브리지.

칸·옵션·명령 라벨이 한국어,
조직의 기본 자동화(새 이슈/닫힘/다시 열림)는 API로 켤 수 없어 sync가 대신 상태를 맞춘다.
설정과 클릭 순서는 docs/setup/project-board.md.

명령:

  sync      project-sync 워크플로가 이슈 사건마다 부른다. 이슈를 보드에 넣고, 사건에 맞는 기본 상태
            (새 이슈/다시 열림 -> 백로그, 닫힘 -> 완료)를 두고, 명령 라벨(명령:<칸>-<값>)을 칸에 반영한 뒤
            그 라벨을 지운다. 라벨은 요청이지 상태가 아니다. APPLY_COMMANDS(공백으로 나눈 명령)는 워크플로가
            직접 보내는 명령이다 - 이슈 라벨이 아니어서 지우지 않고 권한도 묻지 않는다(check.yml의 main-status).
  snapshot  보드를 STATUS.md로 내보낸다. 클라우드 세션은 보드 API에 닿지 못해 이 파일을 읽는다.
            --reconcile이면 먼저 닫혔는데 완료가 아닌 이슈를 완료로 맞춘다(GITHUB_TOKEN이 닫은 이슈는
            sync를 깨우지 않는다 - auto-merge.yml). 이것만 보드에 쓰고, 없으면 읽기만 한다.

둘 다 표준 라이브러리 HTTPS만 써서 Actions와 개발 PC에서 같은 파일이 돈다:

  GH_TOKEN=$(gh auth token) python3 tools/project_bridge.py snapshot --org megasunu --project 1 --out STATUS.md

공개 저장소의 Actions 로그는 공개라서 이슈 제목을 로그에 찍지 않는다.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

API = "https://api.github.com"
PREFIX = "명령:"
WRITE_ROLES = {"admin", "maintain", "write"}

# 칸과 옵션 이름은 보드와 글자까지 같아야 한다.
FIELD_STATUS = "상태"
FIELD_PHASE = "단계"
FIELD_VERIFICATION = "검증"
FIELD_PRIORITY = "우선순위"
FIELD_START = "시작"
FIELD_TARGET = "목표"
# GitHub이 만든 기본 칸 "Status"는 웹에서도 API로도 이름을 바꿀 수 없다 - 이 칸을 "상태"로 읽는다.
FIELD_ALIASES = {"Status": FIELD_STATUS}

STATUS_OPTIONS = ["백로그", "다음", "지금", "검토 중", "완료"]
PHASE_OPTIONS = ["1차수", "2차수", "레벨 12~20", "품질·구조"]
VERIFICATION_NEEDS_DEVICE = "실기기 필요"
VERIFICATION_OPTIONS = ["확인됨", "미확인", VERIFICATION_NEEDS_DEVICE]
PRIORITY_OPTIONS = ["1순위", "2순위", "3순위"]
# 주인이 정할 일은 검증 값이 아니라 담당자다: 주인이 담당인 열린 이슈 = 결정 대기.
MAINTAINERS = {"kirnata77"}

# 사건 -> 기본 상태 (조직 보드의 기본 자동화 대신). 명령 라벨이 상태를 정하면 그것이 이긴다.
STATUS_ON_EVENT = {"opened": "백로그", "reopened": "백로그", "closed": "완료"}


def _key(text: str) -> str:
    """명령 라벨 비교용: 띄어쓰기와 가운뎃점을 빼고 소문자로."""
    return "".join(text.split()).replace("·", "").lower()


# 명령:<칸>-<값> -> (칸, 옵션). 우선순위는 숫자만(명령:우선순위-1).
COMMANDS: dict[str, tuple[str, str]] = {}
for _field, _options in (
    (FIELD_STATUS, STATUS_OPTIONS),
    (FIELD_PHASE, PHASE_OPTIONS),
    (FIELD_VERIFICATION, VERIFICATION_OPTIONS),
):
    for _option in _options:
        COMMANDS[_key(f"{_field}-{_option}")] = (_field, _option)
for _option in PRIORITY_OPTIONS:
    COMMANDS[_key(f"{FIELD_PRIORITY}-{_option.removesuffix('순위')}")] = (
        FIELD_PRIORITY,
        _option,
    )


def command_labels() -> list[str]:
    """저장소에 만들 명령 라벨 이름(띄어쓰기·가운뎃점 없는 표준형)."""
    return [PREFIX + suffix for suffix in COMMANDS]


# --------------------------------------------------------------------------- 판정


def parse_command(label: str) -> tuple[str, str] | None:
    """아는 명령 라벨이면 (칸, 옵션), 아니면 None."""
    text = label.strip()
    if not text.startswith(PREFIX):
        return None
    return COMMANDS.get(_key(text[len(PREFIX) :]))


def is_command(label: str) -> bool:
    return label.strip().startswith(PREFIX)


def status_on_event(action: str) -> str | None:
    return STATUS_ON_EVENT.get(action)


@dataclass
class Plan:
    """사건 하나의 라벨로 sync가 할 일."""

    apply: list[str] = field(default_factory=list)  # 쓰기 권한자가 단 아는 명령
    strip: list[str] = field(default_factory=list)  # 권한 없는 사람이 단 명령 - 지운다
    unknown: list[str] = field(
        default_factory=list
    )  # 뜻이 없는 명령 - 남겨 두고 알린다


def plan_labels(
    action: str, event_label: str, issue_labels: list[str], sender_can_write: bool
) -> Plan:
    """적용하거나 지우거나 알릴 명령 라벨을 정한다.

    - opened / reopened: 이슈의 명령 라벨 전부(세션은 이슈와 라벨을 한 번에 만든다). 쓰기 권한이 없는
      사람의 것은 지운다 - 이슈 양식은 누구에게나 라벨을 미리 달 수 있다.
    - labeled: 방금 단 라벨만.
    - 그 밖(closed 포함): 없음.
    """
    if action in ("opened", "reopened"):
        candidates = [label for label in issue_labels if is_command(label)]
    elif action == "labeled":
        candidates = [event_label] if event_label and is_command(event_label) else []
    else:
        candidates = []

    plan = Plan()
    for label in candidates:
        if not sender_can_write:
            plan.strip.append(label)
        elif parse_command(label):
            plan.apply.append(label)
        else:
            plan.unknown.append(label)
    return plan


def last_wins(labels: list[str]) -> dict[str, str]:
    """칸마다 옵션 하나로 - 뒤의 라벨이 이긴다."""
    result: dict[str, str] = {}
    for label in labels:
        parsed = parse_command(label)
        if parsed:
            result[parsed[0]] = parsed[1]
    return result


# --------------------------------------------------------------------------- GitHub 입출력


class GitHubError(RuntimeError):
    pass


class GitHub:  # pragma: no cover - 실제 네트워크, 테스트는 가짜로 바꾼다
    def __init__(self, token: str):
        if not token:
            raise GitHubError(
                "토큰 없음: PROJECT_TOKEN, GH_TOKEN, GITHUB_TOKEN 중 하나를 둔다"
            )
        self.token = token

    def _request(self, method: str, url: str, body: dict | None = None) -> dict | None:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as err:
            if err.code == 404 and method == "DELETE":
                return None  # 라벨이 이미 없다
            raise GitHubError(
                f"{method} {url.split('?')[0]} -> HTTP {err.code}"
            ) from None
        return json.loads(raw) if raw else None

    def graphql(self, query: str, variables: dict) -> dict:
        out = self._request(
            "POST", f"{API}/graphql", {"query": query, "variables": variables}
        )
        if not out or out.get("errors"):
            messages = "; ".join(
                e.get("message", "?") for e in (out or {}).get("errors", [])
            )
            raise GitHubError(f"GraphQL 오류: {messages or '빈 응답'}")
        return out["data"]

    def rest(self, method: str, path: str, body: dict | None = None) -> dict | None:
        return self._request(method, f"{API}{path}", body)


PROJECT_QUERY = """
query($org: String!, $number: Int!) {
  organization(login: $org) {
    projectV2(number: $number) {
      id
      fields(first: 50) {
        nodes {
          ... on ProjectV2SingleSelectField { id name options { id name } }
          ... on ProjectV2Field { id name }
        }
      }
    }
  }
}
"""

ADD_ITEM = """
mutation($project: ID!, $content: ID!) {
  addProjectV2ItemById(input: {projectId: $project, contentId: $content}) { item { id } }
}
"""

SET_OPTION = """
mutation($project: ID!, $item: ID!, $field: ID!, $option: String!) {
  updateProjectV2ItemFieldValue(input: {
    projectId: $project, itemId: $item, fieldId: $field,
    value: {singleSelectOptionId: $option}
  }) { projectV2Item { id } }
}
"""

ITEMS_QUERY = """
query($org: String!, $number: Int!, $cursor: String) {
  organization(login: $org) {
    projectV2(number: $number) {
      title
      items(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isArchived
          fieldValues(first: 30) {
            nodes {
              ... on ProjectV2ItemFieldSingleSelectValue {
                name
                field { ... on ProjectV2FieldCommon { name } }
              }
              ... on ProjectV2ItemFieldDateValue {
                date
                field { ... on ProjectV2FieldCommon { name } }
              }
            }
          }
          content {
            __typename
            ... on Issue { number title url state repository { name } assignees(first: 5) { nodes { login } } }
            ... on PullRequest { number title url state repository { name } assignees(first: 5) { nodes { login } } }
            ... on DraftIssue { title }
          }
        }
      }
    }
  }
}
"""


def _field_name(name: str) -> str:
    return FIELD_ALIASES.get(name, name)


@dataclass
class Project:
    id: str
    fields: dict[str, dict]  # 이름 -> {"id": ..., "options": {이름: id}}

    def option(self, field_name: str, option_name: str) -> tuple[str, str]:
        f = self.fields.get(field_name)
        if not f:
            raise GitHubError(f"보드에 {field_name!r} 칸이 없다")
        opt = f["options"].get(option_name)
        if not opt:
            raise GitHubError(f"{field_name!r} 칸에 {option_name!r} 옵션이 없다")
        return f["id"], opt


def parse_project(data: dict) -> Project:
    node = (data.get("organization") or {}).get("projectV2")
    if not node:
        raise GitHubError("보드가 없거나 토큰으로 읽을 수 없다")
    fields: dict[str, dict] = {}
    for f in node["fields"]["nodes"]:
        if not f or "name" not in f:
            continue
        entry = {
            "id": f["id"],
            "options": {o["name"]: o["id"] for o in f.get("options", [])},
        }
        name = _field_name(f["name"])
        # 이름이 진짜 "상태"인 칸이 있으면 별칭("Status")보다 그것을 쓴다.
        if name not in fields or f["name"] == name:
            fields[name] = entry
    return Project(id=node["id"], fields=fields)


# --------------------------------------------------------------------------- sync


def can_write(gh: GitHub, repo: str, user: str) -> bool:
    if not user:
        return False
    out = (
        gh.rest(
            "GET", f"/repos/{repo}/collaborators/{urllib.parse.quote(user)}/permission"
        )
        or {}
    )
    return out.get("role_name") in WRITE_ROLES or out.get("permission") in WRITE_ROLES


def summary(lines: list[str]) -> None:
    text = "\n".join(lines)
    print(text)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")


def cmd_sync(args: argparse.Namespace | None) -> int:
    env = os.environ
    repo = env["REPO"]
    number = env["ISSUE_NUMBER"]
    action = env.get("EVENT_ACTION", "")
    event_label = env.get("EVENT_LABEL", "")
    issue_labels = json.loads(env.get("ISSUE_LABELS") or "[]") or []

    project_gh = GitHub(env.get("PROJECT_TOKEN", ""))
    repo_gh = GitHub(env.get("GITHUB_TOKEN", ""))

    writer = can_write(repo_gh, repo, env.get("SENDER", ""))
    plan = plan_labels(action, event_label, issue_labels, writer)

    project = parse_project(
        project_gh.graphql(
            PROJECT_QUERY, {"org": env["ORG"], "number": int(env["PROJECT_NUMBER"])}
        )
    )
    item = project_gh.graphql(
        ADD_ITEM, {"project": project.id, "content": env["ISSUE_NODE_ID"]}
    )
    item_id = item["addProjectV2ItemById"]["item"]["id"]

    # 워크플로가 보낸 명령: 보낸 사람이 없어(SENDER="") 라벨 명령을 쓸 수 없는 check.yml의 main-status가 쓴다.
    sent = env.get("APPLY_COMMANDS", "").split()
    unknown_sent = [c for c in sent if not parse_command(c)]
    values = last_wins(plan.apply + sent)  # last_wins는 모르는 것을 건너뛴다
    default_status = status_on_event(action)
    if default_status and FIELD_STATUS not in values:
        values[FIELD_STATUS] = default_status

    lines = [f"### 보드 동기화: {repo}#{number} ({action})", "- 보드에 있음"]
    for field_name, option_name in values.items():
        field_id, option_id = project.option(field_name, option_name)
        project_gh.graphql(
            SET_OPTION,
            {
                "project": project.id,
                "item": item_id,
                "field": field_id,
                "option": option_id,
            },
        )
        lines.append(f"- {field_name} = {option_name}")

    for label in plan.apply + plan.strip:
        repo_gh.rest(
            "DELETE",
            f"/repos/{repo}/issues/{number}/labels/{urllib.parse.quote(label, safe='')}",
        )
    if plan.strip:
        lines.append(
            f"- 쓰기 권한 없는 사람의 명령 라벨 {len(plan.strip)}개를 무시하고 지움"
        )
    if plan.unknown:
        lines.append(f"- 모르는 명령 라벨(그대로 둠): {', '.join(plan.unknown)}")
    if unknown_sent:
        lines.append(f"- 워크플로가 보낸 모르는 명령(무시): {', '.join(unknown_sent)}")
    summary(lines)
    return 0


# --------------------------------------------------------------------------- snapshot


@dataclass
class Item:
    kind: str  # Issue, PullRequest, DraftIssue
    repo: str
    number: int | None
    title: str
    url: str
    state: str  # OPEN, CLOSED, MERGED, 초안은 DRAFT
    values: dict[str, str]
    assignees: list[str] = field(default_factory=list)
    item_id: str = ""  # 보드 항목 id (칸 값을 쓸 때)

    @property
    def status(self) -> str:
        return self.values.get(FIELD_STATUS, "")

    @property
    def is_open(self) -> bool:
        return self.state in ("OPEN", "DRAFT") and self.status != "완료"

    @property
    def waits_on_maintainer(self) -> bool:
        """주인이 담당인 열린 항목은 주인의 결정을 기다린다."""
        return self.is_open and any(login in MAINTAINERS for login in self.assignees)

    def ref(self) -> str:
        if self.kind == "DraftIssue":
            return "초안"
        return f"{self.repo}#{self.number}"


def _values(nodes: list[dict]) -> dict[str, str]:
    values = {}
    for v in nodes:
        if not v or not v.get("field"):
            continue
        name = _field_name(v["field"].get("name"))
        if v.get("name") is not None:
            values[name] = v["name"]
        elif v.get("date"):
            values[name] = v["date"]
    return values


def parse_items(pages: list[dict]) -> list[Item]:
    items: list[Item] = []
    for page in pages:
        for node in page["organization"]["projectV2"]["items"]["nodes"]:
            if not node or node.get("isArchived"):
                continue
            content = node.get("content") or {}
            kind = content.get("__typename", "")
            if kind not in ("Issue", "PullRequest", "DraftIssue"):
                continue
            items.append(
                Item(
                    kind=kind,
                    repo=(content.get("repository") or {}).get("name", ""),
                    number=content.get("number"),
                    title=content.get("title", ""),
                    url=content.get("url", ""),
                    state=content.get("state") or "DRAFT",
                    values=_values(node["fieldValues"]["nodes"]),
                    assignees=[
                        a["login"]
                        for a in (content.get("assignees") or {}).get("nodes", [])
                        if a
                    ],
                    item_id=node.get("id", ""),
                )
            )
    return items


def fetch_pages(gh: GitHub, org: str, number: int) -> list[dict]:
    pages, cursor = [], None
    while True:
        data = gh.graphql(ITEMS_QUERY, {"org": org, "number": number, "cursor": cursor})
        node = (data.get("organization") or {}).get("projectV2")
        if not node:
            raise GitHubError("보드가 없거나 토큰으로 읽을 수 없다")
        pages.append(data)
        info = node["items"]["pageInfo"]
        if not info["hasNextPage"]:
            return pages
        cursor = info["endCursor"]


DONE = "완료"


def stale_closed(items: list[Item]) -> list[Item]:
    """닫혔는데 상태가 완료가 아닌 이슈. PR과 초안은 보지 않는다."""
    return [
        i
        for i in items
        if i.kind == "Issue" and i.state == "CLOSED" and i.status != DONE
    ]


def reconcile(gh: GitHub, org: str, number: int, items: list[Item]) -> list[Item]:
    """stale_closed 항목의 상태를 보드에서 완료로 바꾸고 items의 값도 맞춘다. 바꾼 항목을 돌려준다."""
    stale = stale_closed(items)
    if not stale:
        return []
    project = parse_project(gh.graphql(PROJECT_QUERY, {"org": org, "number": number}))
    field_id, option_id = project.option(FIELD_STATUS, DONE)
    for item in stale:
        gh.graphql(
            SET_OPTION,
            {
                "project": project.id,
                "item": item.item_id,
                "field": field_id,
                "option": option_id,
            },
        )
        item.values[FIELD_STATUS] = DONE
    # 공개 로그라 번호만 찍는다
    summary(
        [
            f"### 닫힌 이슈 {len(stale)}개를 {DONE}로 맞춤",
            *(f"- {i.ref()}" for i in stale),
        ]
    )
    return stale


STATE_TAGS = {"CLOSED": "닫힘", "MERGED": "병합됨"}


def _clean(text: str) -> str:
    return " ".join(text.split()).replace("|", "/")


def _sort_key(item: Item):
    return (
        item.values.get(FIELD_PRIORITY, "9"),
        item.repo,
        item.number or 0,
        item.title,
    )


def _line(item: Item, show_phase: bool = True) -> str:
    ref = f"[{item.ref()}]({item.url})" if item.url else item.ref()
    tags = []
    if item.values.get(FIELD_PRIORITY):
        tags.append(item.values[FIELD_PRIORITY])
    if show_phase and item.values.get(FIELD_PHASE):
        tags.append(item.values[FIELD_PHASE])
    if item.values.get(FIELD_TARGET):
        tags.append(f"목표 {item.values[FIELD_TARGET]}")
    if item.state in STATE_TAGS:
        tags.append(STATE_TAGS[item.state])
    suffix = f" · {' · '.join(tags)}" if tags else ""
    return f"- {ref} {_clean(item.title)}{suffix}"


def _section(
    title: str, items: list[Item], limit: int | None = None, show_phase: bool = True
) -> list[str]:
    items = sorted(items, key=_sort_key)
    out = [f"## {title} ({len(items)})", ""]
    if not items:
        out.append("- 없음")
    shown = items if limit is None else items[:limit]
    out += [_line(i, show_phase) for i in shown]
    if limit is not None and len(items) > limit:
        out.append(f"- … 그 밖 {len(items) - limit}개는 보드에서")
    out.append("")
    return out


def _roadmap(items: list[Item], open_items: list[Item]) -> list[str]:
    lines = ["## 로드맵 (단계)", ""]
    for phase in PHASE_OPTIONS:
        in_phase = [i for i in items if i.values.get(FIELD_PHASE) == phase]
        if not in_phase:
            continue
        done = sum(1 for i in in_phase if not i.is_open)
        targets = sorted(
            i.values[FIELD_TARGET] for i in in_phase if i.values.get(FIELD_TARGET)
        )
        when = f", 목표 {targets[-1]}" if targets else ""
        lines += [f"### {phase}: {done}/{len(in_phase)} 끝남{when}", ""]
        lines += [
            _line(i, show_phase=False)
            for i in sorted([i for i in in_phase if i.is_open], key=_sort_key)
        ]
        lines.append("")
    unphased = [i for i in open_items if not i.values.get(FIELD_PHASE)]
    if unphased:
        lines += [f"단계 없는 열린 항목: {len(unphased)}개", ""]
    return lines


def render_status(
    items: list[Item], project_title: str, generated: dt.datetime, project_url: str = ""
) -> str:
    open_items = [i for i in items if i.is_open]
    utc = generated.astimezone(dt.timezone.utc).strftime("%H:%M UTC")
    kst = generated.astimezone(dt.timezone(dt.timedelta(hours=9))).strftime(
        "%Y-%m-%d %H:%M KST"
    )
    where = f"[{project_title}]({project_url})" if project_url else project_title
    lines = [
        f"# 작업 상태: {project_title}",
        "",
        f"{kst} ({utc}) 기준. 조직 보드 {where}를 `project-snapshot` 워크플로가 내보냈다.",
        "이 파일은 고치지 않는다: 보드를 고치거나 이슈에 `명령:` 라벨을 단다(docs/setup/project-board.md).",
        "",
    ]
    lines += _section("지금", [i for i in open_items if i.status == "지금"])
    lines += _section("검토 중", [i for i in open_items if i.status == "검토 중"])
    lines += _section("주인 결정 대기", [i for i in items if i.waits_on_maintainer])
    # 검증은 상태와 따로다: 이슈가 닫혀 완료가 돼도 폰에서 확인하고 "확인됨"이 될 때까지 여기 남는다.
    lines += _section(
        VERIFICATION_NEEDS_DEVICE,
        [
            i
            for i in items
            if i.values.get(FIELD_VERIFICATION) == VERIFICATION_NEEDS_DEVICE
        ],
    )
    lines += _section(
        "미확인",
        [i for i in items if i.values.get(FIELD_VERIFICATION) == "미확인"],
        limit=30,
    )
    lines += _section("다음", [i for i in open_items if i.status == "다음"])
    lines += _roadmap(items, open_items)
    lines += _section(
        "백로그", [i for i in open_items if i.status in ("백로그", "")], limit=40
    )
    return "\n".join(lines).rstrip() + "\n"


def cmd_snapshot(args: argparse.Namespace) -> int:
    token = (
        os.environ.get("PROJECT_TOKEN")
        or os.environ.get("GH_TOKEN")
        or os.environ.get("GITHUB_TOKEN", "")
    )
    gh = GitHub(token)
    pages = fetch_pages(gh, args.org, args.project)
    title = pages[0]["organization"]["projectV2"]["title"]
    url = f"https://github.com/orgs/{args.org}/projects/{args.project}"
    items = parse_items(pages)
    if args.reconcile:
        reconcile(gh, args.org, args.project, items)
    text = render_status(items, title, dt.datetime.now(dt.timezone.utc), url)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"{args.out}: {len(text.splitlines())}줄")
    return 0


# --------------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    # Windows에서 리디렉션된 출력은 cp1252라 한글 print가 죽는다 - 콘솔 인코딩과 상관없이 UTF-8로.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sync", help="이슈 사건 하나를 반영한다(입력은 환경 변수)")
    snap = sub.add_parser("snapshot", help="보드를 Markdown 파일로 내보낸다")
    snap.add_argument("--org", default=os.environ.get("ORG", "megasunu"))
    snap.add_argument(
        "--project", type=int, default=int(os.environ.get("PROJECT_NUMBER") or 0)
    )
    snap.add_argument("--out", default="STATUS.md")
    snap.add_argument(
        "--reconcile",
        action="store_true",
        help="내보내기 전에 닫혔는데 완료가 아닌 이슈를 보드에서 완료로 맞춘다(보드 쓰기 권한)",
    )
    sub.add_parser(
        "labels", help="저장소에 만들 명령 라벨 이름을 한 줄에 하나씩 찍는다"
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "sync":
            return cmd_sync(args)
        if args.command == "labels":
            print("\n".join(command_labels()))
            return 0
        if not args.project:
            parser.error("--project(또는 PROJECT_NUMBER)가 필요하다")
        return cmd_snapshot(args)
    except GitHubError as err:
        print(f"오류: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
