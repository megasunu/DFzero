"""풀 시나리오 장부(docs/scenarios.md)와 테스트(@pytest.mark.scenario("S1"))를 대조한다.

규칙은 .claude/rules/scenarios.md. tests/structure/test_repo_hygiene.py가 부른다.
"""

import ast
import glob
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs", "scenarios.md")
TESTS = os.path.join(ROOT, "tests")

상태들 = ("계획", "구현")
_ID = re.compile(r"^S\d+$")


def 문서_행(텍스트):
    """ "## 시나리오" 절의 표 행을 [{ID, 상태, 기능, 방법, 테스트}]로 읽는다."""
    행들 = []
    절 = False
    for 줄 in 텍스트.splitlines():
        if 줄.startswith("## "):
            절 = 줄.strip() == "## 시나리오"
            continue
        if not 절 or not 줄.startswith("|"):
            continue
        칸 = [c.strip() for c in 줄.strip().strip("|").split("|")]
        if 칸[0] == "ID" or set(칸[0]) <= {"-", ":", " "}:
            continue  # 머리글과 구분선
        행들.append(dict(zip(("ID", "상태", "기능", "방법", "테스트"), 칸)))
    return 행들


def 테스트_표시(소스, 파일명):
    """소스의 @pytest.mark.scenario("S1") 함수를 {"파일::함수": ID}로 모은다."""
    찾음 = {}
    for 노드 in ast.walk(ast.parse(소스)):
        if not isinstance(노드, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for 장식 in 노드.decorator_list:
            if (
                isinstance(장식, ast.Call)
                and isinstance(장식.func, ast.Attribute)
                and 장식.func.attr == "scenario"
                and 장식.args
                and isinstance(장식.args[0], ast.Constant)
            ):
                찾음[f"{파일명}::{노드.name}"] = 장식.args[0].value
    return 찾음


def 모든_테스트_표시(폴더=TESTS):
    표시 = {}
    for 경로 in sorted(
        glob.glob(os.path.join(폴더, "**", "test_*.py"), recursive=True)
    ):
        with open(경로, encoding="utf-8") as f:
            표시.update(테스트_표시(f.read(), os.path.basename(경로)))
    return 표시


def 대조(행들, 표시):
    """어긋나는 곳을 문장 목록으로 돌려준다(없으면 빈 목록)."""
    문제 = []
    ID들 = [행["ID"] for 행 in 행들]
    for id_ in sorted({i for i in ID들 if ID들.count(i) > 1}):
        문제.append(f"문서에 ID {id_}가 중복이다")
    문서 = {}
    for 행 in 행들:
        id_, 상태 = 행["ID"], 행["상태"]
        문서[id_] = 행
        if not _ID.match(id_):
            문제.append(f"ID 형식 오류 '{id_}' (S1, S2 ... 형식)")
        if 상태 not in 상태들:
            문제.append(f"{id_}: 상태는 {'/'.join(상태들)} 중 하나여야 한다 ('{상태}')")
        if not 행["기능"] or not 행["방법"]:
            문제.append(f"{id_}: 기능/방법 칸이 비었다")
    for 이름, id_ in sorted(표시.items()):
        if id_ not in 문서:
            문제.append(f"{이름}: 문서에 없는 시나리오 ID '{id_}'")
        elif 문서[id_]["상태"] != "구현":
            문제.append(f"{이름}: 문서에서 {id_}의 상태가 '구현'이 아니다")
    for id_, 행 in 문서.items():
        적힌 = [
            t.strip() for t in 행["테스트"].split(",") if t.strip() not in ("", "-")
        ]
        실제 = sorted(n for n, i in 표시.items() if i == id_)
        if 행["상태"] == "구현":
            if not 실제:
                문제.append(f"{id_}: 구현인데 마커를 단 테스트가 없다")
            if sorted(적힌) != 실제:
                문제.append(
                    f"{id_}: 문서의 테스트 칸 {sorted(적힌)}와 실제 마커 {실제}가 다르다"
                )
        elif 적힌 or 실제:
            문제.append(f"{id_}: 계획인데 테스트가 있다 - 상태를 '구현'으로 고친다")
    return 문제


def 점검():
    with open(DOC, encoding="utf-8") as f:
        행들 = 문서_행(f.read())
    return 대조(행들, 모든_테스트_표시())
