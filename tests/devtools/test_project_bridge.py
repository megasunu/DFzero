"""tools/project_bridge.py - 이슈와 megasunu 작업 보드(Project)를 잇는 브리지.

칸·옵션·명령 라벨이 한국어다(`명령:상태-지금`). 조직의 기본 자동화(닫힘 -> 완료 등)는 API로 켤 수 없어서
브리지가 대신한다 - 새 이슈 -> 백로그, 닫힘 -> 완료, 다시 열림 -> 백로그.
"""

import datetime as dt
import json
import os
from unittest import mock

import pytest

from tools import project_bridge as pb

# ---------------------------------------------------------------- 명령 라벨


def test_명령_라벨을_칸과_옵션으로_읽는다():
    assert pb.parse_command("명령:상태-지금") == ("상태", "지금")
    assert pb.parse_command("명령:상태-검토중") == ("상태", "검토 중")
    assert pb.parse_command("명령:단계-레벨12~20") == ("단계", "레벨 12~20")
    assert pb.parse_command("명령:단계-품질구조") == ("단계", "품질·구조")
    assert pb.parse_command("명령:검증-실기기필요") == ("검증", "실기기 필요")
    assert pb.parse_command("명령:우선순위-1") == ("우선순위", "1순위")


def test_명령_라벨의_띄어쓰기는_무시한다():
    assert pb.parse_command(" 명령: 상태-검토 중 ") == ("상태", "검토 중")


def test_모르는_명령과_보통_라벨은_None():
    assert pb.parse_command("명령:상태-나중에") is None
    assert pb.parse_command("버그") is None
    # 옛 영어 명령은 이 저장소의 것이 아니다
    assert pb.parse_command("cmd:status-now") is None


def test_모든_명령이_실제_옵션을_가리킨다():
    options = {
        pb.FIELD_STATUS: pb.STATUS_OPTIONS,
        pb.FIELD_PHASE: pb.PHASE_OPTIONS,
        pb.FIELD_VERIFICATION: pb.VERIFICATION_OPTIONS,
        pb.FIELD_PRIORITY: pb.PRIORITY_OPTIONS,
    }
    for suffix, (field, option) in pb.COMMANDS.items():
        assert option in options[field], suffix
    # 옵션마다 명령이 하나씩 있다
    assert len(pb.COMMANDS) == sum(len(v) for v in options.values())


def test_명령_라벨_이름_목록():
    names = pb.command_labels()
    assert "명령:상태-지금" in names and "명령:우선순위-3" in names
    assert all(pb.parse_command(n) for n in names)


# ---------------------------------------------------------------- 라벨 계획


def test_쓰기권한자가_연_이슈는_명령을_모두_적용한다():
    plan = pb.plan_labels(
        "opened", "", ["버그", "명령:상태-지금", "명령:우선순위-1"], True
    )
    assert plan.apply == ["명령:상태-지금", "명령:우선순위-1"]
    assert plan.strip == []


def test_권한_없는_사람의_명령은_지운다():
    plan = pb.plan_labels("opened", "", ["명령:상태-지금", "질문"], False)
    assert (plan.apply, plan.strip) == ([], ["명령:상태-지금"])


def test_labeled는_방금_단_라벨만_본다():
    plan = pb.plan_labels(
        "labeled", "명령:검증-확인됨", ["명령:상태-지금", "명령:검증-확인됨"], True
    )
    assert plan.apply == ["명령:검증-확인됨"]


def test_보통_라벨을_달면_아무것도_안_한다():
    plan = pb.plan_labels("labeled", "버그", ["버그"], True)
    assert (plan.apply, plan.strip, plan.unknown) == ([], [], [])


def test_모르는_명령은_남겨_두고_알린다():
    plan = pb.plan_labels("labeled", "명령:상태-언젠가", [], True)
    assert (plan.apply, plan.unknown) == ([], ["명령:상태-언젠가"])


def test_닫힘_사건은_명령을_보지_않는다():
    assert pb.plan_labels("closed", "", ["명령:상태-지금"], True).apply == []


def test_같은_칸은_마지막_명령이_이긴다():
    assert pb.last_wins(["명령:상태-다음", "명령:우선순위-2", "명령:상태-지금"]) == {
        "상태": "지금",
        "우선순위": "2순위",
    }


# ---------------------------------------------------------------- 기본 자동화 대신


@pytest.mark.parametrize(
    "action, expected",
    [
        ("opened", "백로그"),
        ("reopened", "백로그"),
        ("closed", "완료"),
        ("labeled", None),
        ("edited", None),
    ],
)
def test_사건별_기본_상태(action, expected):
    assert pb.status_on_event(action) == expected


# ---------------------------------------------------------------- 보드 칸


PROJECT_DATA = {
    "organization": {
        "projectV2": {
            "id": "PVT_1",
            "fields": {
                "nodes": [
                    # GitHub 기본 칸은 API로 이름을 못 바꿔 "Status"로 남아 있을 수 있다
                    {
                        "id": "F_status",
                        "name": "Status",
                        "options": [{"id": "o_now", "name": "지금"}],
                    },
                    {"id": "F_target", "name": "목표"},
                    {},
                ]
            },
        }
    }
}


def test_Status_칸을_상태로_찾는다():
    project = pb.parse_project(PROJECT_DATA)
    assert project.option("상태", "지금") == ("F_status", "o_now")


def test_상태_칸이_있으면_그것을_쓴다():
    data = json.loads(json.dumps(PROJECT_DATA))
    data["organization"]["projectV2"]["fields"]["nodes"][0]["name"] = "상태"
    assert pb.parse_project(data).option("상태", "지금") == ("F_status", "o_now")


def test_없는_칸이나_옵션은_오류():
    project = pb.parse_project(PROJECT_DATA)
    with pytest.raises(pb.GitHubError):
        project.option("단계", "1차수")
    with pytest.raises(pb.GitHubError):
        project.option("상태", "백로그")


def test_보드가_없으면_오류():
    with pytest.raises(pb.GitHubError):
        pb.parse_project({"organization": {"projectV2": None}})


# ---------------------------------------------------------------- STATUS.md


def node(kind, number, title, state, values, archived=False, assignees=()):
    content = {"__typename": kind, "title": title}
    if kind != "DraftIssue":
        content.update(
            number=number,
            url=f"https://github.com/megasunu/DFzero/issues/{number}",
            state=state,
            repository={"name": "DFzero"},
            assignees={"nodes": [{"login": login} for login in assignees]},
        )
    field_nodes = []
    for name, value in values.items():
        if name in ("시작", "목표"):
            field_nodes.append({"date": value, "field": {"name": name}})
        else:
            field_nodes.append({"name": value, "field": {"name": name}})
    field_nodes.append({})  # 글자/숫자 칸 값은 빈 객체로 온다
    return {
        "id": f"PVTI_{number or 'draft'}",
        "isArchived": archived,
        "fieldValues": {"nodes": field_nodes},
        "content": content,
    }


def page(*nodes):
    return {
        "organization": {
            "projectV2": {
                "title": "던전앤파이터 모바일",
                "items": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": list(nodes),
                },
            }
        }
    }


@pytest.fixture
def items():
    return pb.parse_items(
        [
            page(
                node(
                    "Issue",
                    1,
                    "업적 보상",
                    "OPEN",
                    {
                        "Status": "지금",
                        "단계": "1차수",
                        "우선순위": "1순위",
                        "목표": "2026-10-20",
                    },
                ),
                node(
                    "Issue",
                    2,
                    "창고 | 기능",
                    "OPEN",
                    {"Status": "다음", "단계": "2차수"},
                ),
                node(
                    "Issue",
                    3,
                    "세이브 실기기",
                    "CLOSED",
                    {"Status": "완료", "단계": "1차수", "검증": "실기기 필요"},
                    assignees=["kirnata77"],
                ),
                node(
                    "PullRequest",
                    4,
                    "브리지",
                    "MERGED",
                    {"Status": "완료", "검증": "미확인"},
                ),
                node("DraftIssue", None, "나중에 볼 것", None, {}),
                node("Issue", 5, "옛 일", "CLOSED", {"Status": "완료"}, archived=True),
                node(
                    "Issue",
                    6,
                    "D06 밸런스",
                    "OPEN",
                    {"Status": "다음"},
                    assignees=["kirnata77"],
                ),
                node("Issue", 7, "검토 중인 일", "OPEN", {"상태": "검토 중"}),
            )
        ]
    )


def test_보관된_항목은_뺀다(items):
    assert len(items) == 7


def test_Status_값을_상태로_읽는다(items):
    assert {i.number: i.status for i in items if i.number} == {
        1: "지금",
        2: "다음",
        3: "완료",
        4: "완료",
        6: "다음",
        7: "검토 중",
    }


def test_열린_항목은_열렸거나_초안이고_완료가_아니다(items):
    assert sorted(i.ref() for i in items if i.is_open) == [
        "DFzero#1",
        "DFzero#2",
        "DFzero#6",
        "DFzero#7",
        "초안",
    ]


def test_담당자를_읽는다(items):
    by_ref = {i.ref(): i.assignees for i in items}
    assert by_ref["DFzero#6"] == ["kirnata77"]
    assert by_ref["초안"] == []
    assert "assignees" in pb.ITEMS_QUERY


def _절(text, 제목):
    return text.split(f"## {제목}")[1].split("\n## ")[0]


def test_STATUS_md(items):
    when = dt.datetime(2026, 10, 8, 0, 17, tzinfo=dt.timezone.utc)
    text = pb.render_status(
        items,
        "던전앤파이터 모바일",
        when,
        "https://github.com/orgs/megasunu/projects/1",
    )
    assert "2026-10-08 09:17 KST (00:17 UTC)" in text
    assert "## 지금 (1)" in text
    assert (
        "- [DFzero#1](https://github.com/megasunu/DFzero/issues/1) 업적 보상 · 1순위 · 1차수 · 목표 2026-10-20"
        in text
    )
    assert "## 검토 중 (1)" in text and "DFzero#7" in _절(text, "검토 중")
    # 주인 결정 = 주인이 담당인 열린 항목. 닫힌 #3은 기다리지 않는다
    assert "## 주인 결정 대기 (1)" in text
    assert "DFzero#6" in _절(text, "주인 결정 대기")
    # 닫혔어도 실기기 확인이 남았으면 보인다
    assert "## 실기기 필요 (1)" in text
    assert "DFzero#3" in _절(text, "실기기 필요") and "닫힘" in _절(text, "실기기 필요")
    assert "## 미확인 (1)" in text and "병합됨" in _절(text, "미확인")
    assert "## 다음 (2)" in text
    # 로드맵은 닫힌 것을 끝난 것으로 센다
    assert "### 1차수: 1/2 끝남, 목표 2026-10-20" in text
    assert "### 2차수: 0/1 끝남" in text
    # 제목의 | 는 목록을 깨지 않게 바꾼다
    assert "창고 / 기능" in text
    # 상태 없는 초안은 백로그
    assert "## 백로그 (1)" in text and "- 초안 나중에 볼 것" in text


def test_빈_보드도_그린다():
    text = pb.render_status(
        [], "던전앤파이터 모바일", dt.datetime(2026, 10, 8, tzinfo=dt.timezone.utc)
    )
    assert "## 지금 (0)" in text and "## 주인 결정 대기 (0)" in text
    assert "- 없음" in text


def test_긴_목록은_자른다():
    many = pb.parse_items(
        [
            page(
                *[
                    node("Issue", n, f"일 {n}", "OPEN", {"Status": "백로그"})
                    for n in range(1, 46)
                ]
            )
        ]
    )
    text = pb.render_status(
        many, "보드", dt.datetime(2026, 10, 8, tzinfo=dt.timezone.utc)
    )
    assert "## 백로그 (45)" in text
    assert "- … 그 밖 5개는 보드에서" in text


# ---------------------------------------------------------------- sync 전체


def run_sync(env, writer=True):
    calls = []

    class FakeGitHub:
        def __init__(self, token):
            self.token = token

        def graphql(self, query, variables):
            calls.append(("graphql", variables))
            if "addProjectV2ItemById" in query:
                return {"addProjectV2ItemById": {"item": {"id": "ITEM_1"}}}
            if "updateProjectV2ItemFieldValue" in query:
                return {
                    "updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "ITEM_1"}}
                }
            return {
                "organization": {
                    "projectV2": {
                        "id": "PVT_1",
                        "fields": {
                            "nodes": [
                                {
                                    "id": "F_s",
                                    "name": "Status",
                                    "options": [
                                        {"id": "o_backlog", "name": "백로그"},
                                        {"id": "o_now", "name": "지금"},
                                        {"id": "o_done", "name": "완료"},
                                    ],
                                },
                                {
                                    "id": "F_p",
                                    "name": "우선순위",
                                    "options": [{"id": "o_p1", "name": "1순위"}],
                                },
                            ]
                        },
                    }
                }
            }

        def rest(self, method, path, body=None):
            calls.append((method, path))
            if path.endswith("/permission"):
                role = "write" if writer else "read"
                return {"permission": role, "role_name": role}
            return None

    base = {
        "REPO": "megasunu/DFzero",
        "ISSUE_NUMBER": "7",
        "ISSUE_NODE_ID": "I_7",
        "ORG": "megasunu",
        "PROJECT_NUMBER": "1",
        "PROJECT_TOKEN": "p",
        "GITHUB_TOKEN": "g",
        "SENDER": "enjay27",
    }
    base.update(env)
    with (
        mock.patch.object(pb, "GitHub", FakeGitHub),
        mock.patch.dict(os.environ, base, clear=True),
        mock.patch("builtins.print"),
    ):
        code = pb.cmd_sync(None)
    return code, calls


def _설정한_옵션(calls):
    return [c[1]["option"] for c in calls if c[0] == "graphql" and "option" in c[1]]


def test_명령을_적용한_뒤에_라벨을_지운다():
    code, calls = run_sync(
        {
            "EVENT_ACTION": "opened",
            "ISSUE_LABELS": json.dumps(["명령:상태-지금", "명령:우선순위-1", "버그"]),
        }
    )
    assert code == 0
    assert sorted(_설정한_옵션(calls)) == ["o_now", "o_p1"]
    deletes = [c[1] for c in calls if c[0] == "DELETE"]
    assert deletes == [
        "/repos/megasunu/DFzero/issues/7/labels/%EB%AA%85%EB%A0%B9%3A%EC%83%81%ED%83%9C-%EC%A7%80%EA%B8%88",
        "/repos/megasunu/DFzero/issues/7/labels/%EB%AA%85%EB%A0%B9%3A%EC%9A%B0%EC%84%A0%EC%88%9C%EC%9C%84-1",
    ]
    first_delete = next(i for i, c in enumerate(calls) if c[0] == "DELETE")
    last_set = max(
        i for i, c in enumerate(calls) if c[0] == "graphql" and "option" in c[1]
    )
    assert last_set < first_delete


def test_명령_없는_새_이슈는_백로그():
    code, calls = run_sync(
        {"EVENT_ACTION": "opened", "ISSUE_LABELS": json.dumps(["버그"])}
    )
    assert code == 0
    assert _설정한_옵션(calls) == ["o_backlog"]


def test_닫힌_이슈는_완료():
    code, calls = run_sync(
        {"EVENT_ACTION": "closed", "ISSUE_LABELS": json.dumps(["명령:상태-지금"])}
    )
    assert code == 0
    assert _설정한_옵션(calls) == ["o_done"]
    assert not [c for c in calls if c[0] == "DELETE"]


def test_권한_없는_사람의_이슈도_넣지만_명령은_지운다():
    code, calls = run_sync(
        {"EVENT_ACTION": "opened", "ISSUE_LABELS": json.dumps(["명령:상태-지금"])},
        writer=False,
    )
    assert code == 0
    assert _설정한_옵션(calls) == ["o_backlog"]
    assert [c for c in calls if c[0] == "graphql" and c[1].get("content") == "I_7"]
    assert [c[1] for c in calls if c[0] == "DELETE"] == [
        "/repos/megasunu/DFzero/issues/7/labels/%EB%AA%85%EB%A0%B9%3A%EC%83%81%ED%83%9C-%EC%A7%80%EA%B8%88"
    ]


def test_워크플로가_보낸_명령은_라벨_없이_적용한다():
    """check.yml의 main-status: 보낸 사람이 없어(SENDER="") 라벨 명령은 못 쓰므로 APPLY_COMMANDS로 넘긴다.
    이슈의 라벨은 건드리지 않고, 권한도 묻지 않는다."""
    code, calls = run_sync(
        {
            "EVENT_ACTION": "opened",
            "SENDER": "",
            "APPLY_COMMANDS": "명령:상태-지금 명령:우선순위-1",
        }
    )
    assert code == 0
    assert sorted(_설정한_옵션(calls)) == ["o_now", "o_p1"]
    assert not [c for c in calls if c[0] in ("DELETE", "GET")]


def test_워크플로가_보낸_모르는_명령은_무시한다():
    code, calls = run_sync(
        {
            "EVENT_ACTION": "opened",
            "SENDER": "",
            "APPLY_COMMANDS": "명령:상태-없는값 버그",
        }
    )
    assert code == 0
    assert _설정한_옵션(calls) == ["o_backlog"]


def test_main_snapshot은_보드_번호가_필요하다():
    with mock.patch.dict(os.environ, {}, clear=True), pytest.raises(SystemExit):
        pb.main(["snapshot"])


# ---------------------------------------------------------------- 닫힌 이슈 맞추기
# auto-merge.yml은 GITHUB_TOKEN으로 이슈를 닫아 issues: closed 사건이 project-sync를 깨우지 않는다.
# 그래서 snapshot --reconcile이 내보내기 전에 닫혔는데 완료가 아닌 이슈를 완료로 맞춘다.


def 맞출_보드():
    return pb.parse_items(
        [
            page(
                node("Issue", 11, "자동 병합이 닫음", "CLOSED", {"Status": "지금"}),
                node("Issue", 12, "검토하다 닫힘", "CLOSED", {"상태": "검토 중"}),
                node("Issue", 13, "상태 없이 닫힘", "CLOSED", {}),
                node("Issue", 14, "이미 완료", "CLOSED", {"Status": "완료"}),
                node("Issue", 15, "열린 일", "OPEN", {"Status": "지금"}),
                node("PullRequest", 16, "병합된 PR", "MERGED", {"Status": "지금"}),
                node("DraftIssue", None, "초안", None, {"Status": "지금"}),
                node(
                    "Issue", 17, "보관됨", "CLOSED", {"Status": "지금"}, archived=True
                ),
            )
        ]
    )


def test_항목_id를_읽는다():
    assert [i.item_id for i in 맞출_보드()][:2] == ["PVTI_11", "PVTI_12"]


def test_닫혔는데_완료가_아닌_이슈만_고른다():
    assert [i.ref() for i in pb.stale_closed(맞출_보드())] == [
        "DFzero#11",
        "DFzero#12",
        "DFzero#13",
    ]


class 가짜_보드:
    """보드 칸을 읽고 칸 값 쓰기를 적어 두는 가짜 GitHub. 보드 항목은 pages로 준다."""

    def __init__(self, pages=(), field_name="Status"):
        self.pages = list(pages)
        self.field_name = field_name
        self.calls = []

    def __call__(self, token):  # pb.GitHub 자리에 클래스처럼 꽂는다
        return self

    def graphql(self, query, variables):
        self.calls.append((query, variables))
        if "updateProjectV2ItemFieldValue" in query:
            return {"updateProjectV2ItemFieldValue": {"projectV2Item": {"id": "x"}}}
        if "items(first" in query:
            return self.pages.pop(0)
        return {
            "organization": {
                "projectV2": {
                    "id": "PVT_1",
                    "fields": {
                        "nodes": [
                            {
                                "id": "F_s",
                                "name": self.field_name,
                                "options": [
                                    {"id": "o_now", "name": "지금"},
                                    {"id": "o_done", "name": "완료"},
                                ],
                            }
                        ]
                    },
                }
            }
        }

    def writes(self):
        return [v for q, v in self.calls if "updateProjectV2ItemFieldValue" in q]


@pytest.mark.parametrize("field_name", ["Status", "상태"])
def test_닫힌_이슈를_완료로_맞춘다(field_name, capsys):
    gh = 가짜_보드(field_name=field_name)
    items = 맞출_보드()
    changed = pb.reconcile(gh, "megasunu", 1, items)
    assert [i.ref() for i in changed] == ["DFzero#11", "DFzero#12", "DFzero#13"]
    assert gh.writes() == [
        {"project": "PVT_1", "item": f"PVTI_{n}", "field": "F_s", "option": "o_done"}
        for n in (11, 12, 13)
    ]
    # 내보낼 내용도 보드와 같아진다
    assert all(i.status == "완료" for i in changed)
    assert {i.number: i.status for i in items if i.number in (15, 16)} == {
        15: "지금",
        16: "지금",
    }
    # 공개 로그에는 번호만 - 제목은 찍지 않는다
    out = capsys.readouterr().out
    assert "DFzero#11" in out and "자동 병합이 닫음" not in out


def test_맞출_것이_없으면_보드에_쓰지_않는다(capsys):
    gh = 가짜_보드()
    items = [i for i in 맞출_보드() if i.number in (14, 15)]
    assert pb.reconcile(gh, "megasunu", 1, items) == []
    assert gh.calls == []


def _snapshot(tmp_path, *extra):
    gh = 가짜_보드(
        pages=[
            page(
                node("Issue", 11, "자동 병합이 닫음", "CLOSED", {"Status": "지금"}),
                node("Issue", 15, "열린 일", "OPEN", {"Status": "지금"}),
            )
        ]
    )
    out = tmp_path / "STATUS.md"
    argv = ["snapshot", "--org", "megasunu", "--project", "1", "--out", str(out)]
    with (
        mock.patch.object(pb, "GitHub", gh),
        mock.patch.dict(os.environ, {"GH_TOKEN": "t"}, clear=True),
    ):
        code = pb.main(argv + list(extra))
    return code, gh, out.read_text(encoding="utf-8")


def test_snapshot_reconcile은_맞춘_뒤에_내보낸다(tmp_path, capsys):
    code, gh, text = _snapshot(tmp_path, "--reconcile")
    assert code == 0
    assert [w["item"] for w in gh.writes()] == ["PVTI_11"]
    assert "## 지금 (1)" in text and "DFzero#15" in text


def test_snapshot은_reconcile_없이는_보드에_쓰지_않는다(tmp_path, capsys):
    code, gh, text = _snapshot(tmp_path)
    assert code == 0
    assert gh.writes() == []
    assert "## 지금 (1)" in text
