"""컨트롤러 구조 규칙 - gameflow.py는 창구, 구현은 game/controller/ctl_*.py (구조 점검 R-1, N5).

gameflow.py(2,296줄/함수 148개)를 주제별 모듈 15개로 나눴다. 화면과 테스트는 그대로 `import gameflow as gf`로
쓴다. 이 파일은 그 분할이 다시 무너지지 않게 지킨다: 창구에는 구현을 두지 않고, 컨트롤러 모듈끼리 순환하지
않고, 창구가 화면/테스트가 쓰는 이름을 빠뜨리지 않는다.
"""

import ast
import pathlib

import gameflow
from tests.test_architecture import _강연결_묶음

루트 = pathlib.Path(__file__).resolve().parents[1]
컨트롤러_폴더 = 루트 / "game" / "controller"
모듈들 = sorted(p.stem for p in 컨트롤러_폴더.glob("ctl_*.py"))


def _트리(경로):
    return ast.parse(경로.read_text(encoding="utf-8"))


def _정의한_이름(트리):
    이름들 = []
    for 노드 in 트리.body:
        if isinstance(노드, (ast.FunctionDef, ast.ClassDef)):
            이름들.append(노드.name)
        elif isinstance(노드, ast.Assign):
            이름들 += [
                x.id
                for x in 노드.targets
                if isinstance(x, ast.Name) and x.id != "__all__"
            ]
    return 이름들


def test_창구에는_구현을_두지_않는다():
    """gameflow.py는 머리말 주석과 재수출(import)만 둔다 - 함수/변수 정의가 생기면 컨트롤러 모듈로 옮긴다."""
    트리 = _트리(루트 / "gameflow.py")
    구현 = [
        f"{노드.lineno}: {type(노드).__name__}"
        for 노드 in 트리.body
        if not isinstance(노드, (ast.Import, ast.ImportFrom))
    ]
    assert not 구현, (
        "gameflow.py에 구현이 있다(game/controller/ctl_*.py로):\n" + "\n".join(구현)
    )


def test_컨트롤러_모듈은_정의한_이름을_전부_all에_넣는다():
    """창구가 `import *`로 다시 내보내므로 __all__에 빠진 함수는 화면/테스트에서 안 보인다."""
    문제 = []
    for 모듈 in 모듈들:
        트리 = _트리(컨트롤러_폴더 / f"{모듈}.py")
        정의 = set(_정의한_이름(트리))
        all_노드 = next(
            (
                n
                for n in 트리.body
                if isinstance(n, ast.Assign)
                and any(getattr(t, "id", "") == "__all__" for t in n.targets)
            ),
            None,
        )
        if all_노드 is None:
            문제.append(f"{모듈}: __all__이 없다")
            continue
        목록 = {e.value for e in all_노드.value.elts}
        if 정의 - 목록:
            문제.append(f"{모듈}: __all__에 빠짐 {sorted(정의 - 목록)}")
        if 목록 - 정의:
            문제.append(f"{모듈}: __all__에 있는데 정의가 없다 {sorted(목록 - 정의)}")
    assert not 문제, "\n".join(문제)


def test_컨트롤러_모듈끼리_순환하지_않고_위로_부르지_않는다():
    그래프 = {m: set() for m in 모듈들}
    위반 = []
    for 모듈 in 모듈들:
        for 노드 in ast.walk(_트리(컨트롤러_폴더 / f"{모듈}.py")):
            if isinstance(노드, ast.ImportFrom) and 노드.module:
                if 노드.module.startswith("game.controller.ctl_"):
                    대상 = 노드.module.rsplit(".", 1)[1]
                    그래프[모듈].add(대상)
                    # 다른 컨트롤러 모듈의 밑줄 이름을 가져오지 않는다(공개 이름만)
                    위반 += [
                        f"{모듈}: {대상}의 {a.name}"
                        for a in 노드.names
                        if a.name.startswith("_")
                    ]
                if 노드.module == "gameflow":
                    위반.append(f"{모듈}: gameflow(창구)를 import한다")
    assert not 위반, "컨트롤러 모듈 경계 위반:\n" + "\n".join(위반)
    assert _강연결_묶음(그래프) == [], f"컨트롤러 모듈 순환: {_강연결_묶음(그래프)}"


def test_창구는_화면_테스트_도구가_쓰는_이름을_빠짐없이_내보낸다():
    쓰는 = {}
    대상 = [
        *(루트 / "game" / "screens").glob("*.py"),
        *(루트 / "tests").glob("*.py"),
        *(루트 / "tools").glob("*.py"),
        루트 / "main.py",
    ]
    for 경로 in 대상:
        for 노드 in ast.walk(_트리(경로)):
            if (
                isinstance(노드, ast.Attribute)
                and isinstance(노드.value, ast.Name)
                and 노드.value.id in ("gf", "gameflow")
            ):
                쓰는.setdefault(노드.attr, f"{경로.relative_to(루트)}:{노드.lineno}")
    없는 = {이름: 곳 for 이름, 곳 in 쓰는.items() if not hasattr(gameflow, 이름)}
    assert not 없는, f"gameflow 창구에 없는 이름을 쓴다: {없는}"
    assert len(쓰는) > 120  # 수집이 비는 일을 막는다


def test_창구에서_이름이_겹치지_않는다():
    """같은 이름을 두 컨트롤러 모듈이 정의하면 import * 순서에 따라 한쪽이 가려진다."""
    주인 = {}
    겹침 = []
    for 모듈 in 모듈들:
        for 이름 in _정의한_이름(_트리(컨트롤러_폴더 / f"{모듈}.py")):
            if 이름 in 주인:
                겹침.append(f"{이름}: {주인[이름]}, {모듈}")
            주인[이름] = 모듈
    assert not 겹침, "\n".join(겹침)
