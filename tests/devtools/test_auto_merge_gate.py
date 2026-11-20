"""tools/auto_merge_gate.py - 자동 병합 워크플로(.github/workflows/auto-merge.yml)의 판정.

buildozer.spec도 기본 보호 경로다(CLAUDE.md "Git").
"""

import json

import pytest

from tools import auto_merge_gate as gate

상태_없음 = {"state": "pending", "total_count": 0, "statuses": []}


def run(name, status="completed", conclusion="success"):
    return {"name": name, "status": status, "conclusion": conclusion}


def pr(draft=False, changed_files=1):
    return {"draft": draft, "changed_files": changed_files}


def file(name, previous=None):
    return {"filename": name, "previous_filename": previous}


def ref(owner, name, number):
    return {"number": number, "repository": {"name": name, "owner": {"login": owner}}}


# ------------------------------------------------------------ check run


def test_모두_초록이면_병합():
    assert gate.decide([run("check"), run("ui-smoke")], 상태_없음) == "merge"


def test_skipped와_neutral은_초록으로_친다():
    runs = [
        run("check"),
        run("a", conclusion="skipped"),
        run("b", conclusion="neutral"),
    ]
    assert gate.decide(runs, 상태_없음) == "merge"


@pytest.mark.parametrize("status", ["in_progress", "queued"])
def test_아직_도는_검사가_있으면_기다린다(status):
    runs = [run("check"), run("ui-smoke", status=status, conclusion=None)]
    assert gate.decide(runs, 상태_없음) == "wait"


def test_실패한_검사가_있으면_멈춘다():
    assert (
        gate.decide([run("check"), run("ui-smoke", conclusion="failure")], 상태_없음)
        == "stop"
    )


def test_실패가_도는_검사보다_먼저다():
    runs = [
        run("a", conclusion="failure"),
        run("b", status="in_progress", conclusion=None),
    ]
    assert gate.decide(runs, 상태_없음) == "stop"


@pytest.mark.parametrize(
    "conclusion", ["cancelled", "timed_out", "action_required", "stale"]
)
def test_취소나_시간초과는_멈춘다(conclusion):
    assert gate.decide([run("a", conclusion=conclusion)], 상태_없음) == "stop"


def test_검사가_하나도_없으면_기다린다():
    assert gate.decide([], 상태_없음) == "wait"


def test_건너뛴_검사뿐이면_기다린다():
    assert gate.decide([run("a", conclusion="skipped")], 상태_없음) == "wait"


# ------------------------------------------------------------ commit status


def _상태(state):
    return {"state": state, "total_count": 1, "statuses": [{"state": state}]}


def test_대기중인_status는_기다린다():
    assert gate.decide([run("check")], _상태("pending")) == "wait"


@pytest.mark.parametrize("state", ["failure", "error"])
def test_실패한_status는_멈춘다(state):
    assert gate.decide([run("check")], _상태(state)) == "stop"


def test_초록_status는_병합():
    assert gate.decide([run("check")], _상태("success")) == "merge"


def test_status가_없을_때의_pending_기본값은_무시한다():
    # 커밋에 status가 하나도 없으면 GitHub는 "pending"이라고 답한다.
    assert gate.decide([run("check")], 상태_없음) == "merge"


# ------------------------------------------------------------ 필수 검사


def test_필수_검사가_아직_안_왔으면_기다린다():
    """push 실행이 먼저 끝나도 PR 실행의 ui-smoke가 시작 전이면 병합하지 않는다."""
    assert gate.decide([run("check")], 상태_없음, required=["ui-smoke"]) == "wait"


def test_필수_검사가_모두_성공하면_병합():
    runs = [run("check"), run("ui-smoke")]
    assert gate.decide(runs, 상태_없음, required=["check", "ui-smoke"]) == "merge"


def test_필수_검사가_빠져도_실패는_멈춘다():
    runs = [run("check", conclusion="failure")]
    assert gate.decide(runs, 상태_없음, required=["ui-smoke"]) == "stop"


def test_건너뛴_필수_검사는_성공이_아니다():
    runs = [run("check"), run("ui-smoke", conclusion="skipped")]
    assert gate.decide(runs, 상태_없음, required=["ui-smoke"]) == "wait"


def test_같은_이름의_검사가_둘이면_둘_다_끝나야_한다():
    """check.yml은 push와 pull_request 둘 다에서 돌아 같은 커밋에 `check`가 두 개 붙는다."""
    runs = [run("check"), run("check", status="in_progress", conclusion=None)]
    assert gate.decide(runs, 상태_없음, required=["check"]) == "wait"
    runs = [run("check"), run("check", conclusion="failure")]
    assert gate.decide(runs, 상태_없음, required=["check"]) == "stop"


# ------------------------------------------------------------ 초안과 보호 경로

초록 = [run("check"), run("ui-smoke")]


def _판정(pull, files, runs=초록, protected=()):
    return gate.decide(runs, 상태_없음, ["check", "ui-smoke"], pull, files, protected)


def test_보통_PR은_병합():
    assert _판정(pr(), [file("game/system/dice.py")]) == "merge"


def test_초안은_멈춘다():
    assert _판정(pr(draft=True), [file("README.md")]) == "stop"


def test_초안은_검사가_도는_중에도_멈춘다():
    runs = [run("check", status="in_progress", conclusion=None)]
    assert _판정(pr(draft=True), [file("README.md")], runs) == "stop"


@pytest.mark.parametrize(
    "path",
    [".github/workflows/auto-merge.yml", ".github/workflows/new.yml", "buildozer.spec"],
)
def test_워크플로와_buildozer_spec은_늘_보호된다(path):
    assert _판정(pr(), [file(path)]) == "stop"


@pytest.mark.parametrize(
    "path",
    [
        "tools/auto_merge_gate.py",
        "CLAUDE.md",
        ".claude/rules/eol.md",
        ".claude/rules/build-and-save.md",
        ".claude/rules/new.md",
    ],
)
def test_판정_스크립트와_에이전트_규칙은_늘_보호된다(path):
    """auto-merge.yml은 main-branch의 이 스크립트를 돌린다 - PR이 보호 목록을 줄이면 그 PR이 옛 규칙으로
    스스로 병합되고 다음 PR부터 보호가 풀린다. 에이전트 규칙도 에이전트가 스스로 병합하지 않는다(전역 G23)."""
    assert _판정(pr(), [file(path)]) == "stop"


@pytest.mark.parametrize("path", [".claude/rules/tests.md", ".claude/rules/layers.md"])
def test_테스트_지도와_모듈_배치는_기능_PR과_같이_병합된다(path):
    """기능 PR이 새 테스트 파일·모듈을 적는 곳이다 - 이것 때문에 기능 PR이 손 병합으로 멈추지 않게."""
    assert _판정(pr(), [file(path)]) == "merge"
    assert gate.protected_paths([file(path)]) == []


def test_예외_파일도_보호_파일과_같이_바꾸면_멈춘다():
    files = [file(".claude/rules/tests.md"), file("CLAUDE.md")]
    assert _판정(pr(changed_files=2), files) == "stop"
    assert gate.protected_paths(files) == ["CLAUDE.md"]


def test_예외_파일로_이름을_바꾸면_옛_이름으로_멈춘다():
    moved = file(".claude/rules/tests.md", previous=".claude/rules/eol.md")
    assert gate.protected_paths([moved]) == [".claude/rules/eol.md"]


@pytest.mark.parametrize(
    "path",
    [
        ".github/dependabot.yml",
        "tools/auto_merge_gate.py.orig",
        "docs/CLAUDE.md",
        ".claude/skills/repo-workflow/SKILL.md",
        "docs/github/workflows/x.md",
        "buildozer.spec.orig",
        "docs/buildozer.spec",
    ],
)
def test_다른_경로는_기본으로_보호되지_않는다(path):
    assert _판정(pr(), [file(path)]) == "merge"


@pytest.mark.parametrize("path", ["tools/check.py", ".github/scripts/x.sh"])
def test_호출자가_파일이나_폴더를_더_보호한다(path):
    assert (
        _판정(pr(), [file(path)], protected=["tools/check.py", ".github/scripts/"])
        == "stop"
    )


def test_보호_파일은_이름_전체로_맞춘다():
    files = [file("tools/check.py.orig"), file("tools/test_check.py")]
    assert _판정(pr(changed_files=2), files, protected=["tools/check.py"]) == "merge"


def test_이름을_바꾼_파일은_옛_이름으로도_본다():
    assert (
        _판정(pr(), [file("docs/old.yml", previous=".github/workflows/old.yml")])
        == "stop"
    )


def test_파일_목록을_다_못_읽었으면_멈춘다():
    assert _판정(pr(changed_files=2), [file("README.md")]) == "stop"


def test_파일_목록이_없으면_멈춘다():
    assert _판정(pr(), None) == "stop"


def test_보호_경로는_이름_바꾸기의_두_이름을_다_적는다():
    files = [
        file(".github/workflows/b.yml", previous=".github/workflows/a.yml"),
        file("README.md"),
    ]
    assert gate.protected_paths(files) == [
        ".github/workflows/a.yml",
        ".github/workflows/b.yml",
    ]


# ------------------------------------------------------------ 닫을 이슈


def test_같은_저장소의_이슈를_번호순으로_닫는다():
    refs = [ref("kirnata77", "asdf", 9), ref("kirnata77", "asdf", 4)]
    assert gate.issues_to_close(refs, "kirnata77/asdf") == [4, 9]


def test_다른_저장소의_이슈는_건드리지_않는다():
    refs = [ref("kirnata77", "other", 5), ref("kirnata77", "asdf", 4)]
    assert gate.issues_to_close(refs, "kirnata77/asdf") == [4]


def test_저장소_이름은_대소문자를_가리지_않는다():
    assert gate.issues_to_close([ref("Kirnata77", "ASDF", 4)], "kirnata77/asdf") == [4]


def test_같은_이슈는_한_번만_닫는다():
    refs = [ref("kirnata77", "asdf", 4), ref("kirnata77", "asdf", 4)]
    assert gate.issues_to_close(refs, "kirnata77/asdf") == [4]


def test_참조가_없으면_아무것도_닫지_않는다():
    assert gate.issues_to_close([], "kirnata77/asdf") == []


# ------------------------------------------------------------ 줄 목록과 명령줄


def test_줄_목록은_앞뒤_공백과_빈_줄을_뺀다():
    assert gate.name_list("  check \n\n ui-smoke\n") == ["check", "ui-smoke"]
    assert gate.name_list("") == []


def _main(tmp_path, capsys, *args, pull=None, files=None, runs=None):
    def 쓰기(name, data):
        path = tmp_path / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    extra = []
    if pull is not None:
        extra += ["--pr", 쓰기("pr.json", pull)]
    if files is not None:
        extra += ["--files", 쓰기("files.json", files)]
    runs_path = 쓰기("runs.json", runs if runs is not None else [run("check")])
    status_path = 쓰기("status.json", 상태_없음)
    code = gate.main(["auto_merge_gate.py", *args, *extra, runs_path, status_path])
    return code, capsys.readouterr().out.strip()


def test_옵션_없이_병합(tmp_path, capsys):
    assert _main(tmp_path, capsys) == (0, "merge")


def test_require는_줄_목록을_받는다(tmp_path, capsys):
    runs = [run("check"), run("ui-smoke")]
    assert _main(tmp_path, capsys, "--require", "check\nui-smoke\n", runs=runs) == (
        0,
        "merge",
    )
    assert _main(tmp_path, capsys, "--require", "check\nother", runs=runs) == (
        0,
        "wait",
    )


def test_빈_require와_protect는_아무것도_바꾸지_않는다(tmp_path, capsys):
    assert _main(tmp_path, capsys, "--require", "", "--protect", "") == (0, "merge")


def test_pr과_files로_보통_PR은_병합(tmp_path, capsys):
    assert _main(tmp_path, capsys, pull=pr(), files=[file("README.md")]) == (0, "merge")


def test_pr과_files로_초안은_멈춘다(tmp_path, capsys):
    assert _main(tmp_path, capsys, pull=pr(draft=True), files=[file("README.md")]) == (
        0,
        "stop",
    )


def test_files_없는_pr은_멈춘다(tmp_path, capsys):
    assert _main(tmp_path, capsys, pull=pr()) == (0, "stop")


def test_protect에_걸리면_멈춘다(tmp_path, capsys):
    결과 = _main(
        tmp_path,
        capsys,
        "--protect",
        "docs/\nREADME.md",
        pull=pr(),
        files=[file("README.md")],
    )
    assert 결과 == (0, "stop")


def test_pr_없는_files는_사용법_오류(tmp_path, capsys):
    assert _main(tmp_path, capsys, files=[file("README.md")]) == (2, "")


def test_issues_to_close_명령(tmp_path, capsys):
    path = tmp_path / "refs.json"
    path.write_text(json.dumps([ref("kirnata77", "asdf", 7)]), encoding="utf-8")
    code = gate.main(
        ["auto_merge_gate.py", "--issues-to-close", str(path), "kirnata77/asdf"]
    )
    assert (code, capsys.readouterr().out.strip()) == (0, "7")
