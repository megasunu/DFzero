"""아키텍처 규칙 - combat 패키지의 의존 방향과 모듈 경계 (구조 점검 R-3).

R4가 combat_system을 12개 모듈로 나눈 뒤에도 모듈끼리 서로 import하는 순환이 있었고, 다른 모듈에서
"비공개"(밑줄) 이름을 쓰는 곳이 77곳이었다. 순환은 다 없앨 수 없다(피격이 특성을 발동시키고 특성이
다시 피해를 주는 도메인 재귀) - 대신 남은 순환을 허용 목록으로 고정해 더 커지지 못하게 한다.
"""

import ast
import pathlib

루트 = pathlib.Path(__file__).resolve().parents[1]
combat_폴더 = 루트 / "game" / "system" / "combat"
combat_모듈 = sorted(p.stem for p in combat_폴더.glob("*.py") if p.stem != "__init__")
검사_모듈 = combat_모듈 + ["skill_system"]  # 밑줄 이름 규칙은 skill_system도 지킨다

# 도메인 재귀로 남은 순환(피격 -> 반응/특성 발동 -> 피해, 능력치 <-> 특성). 새 순환이 생기거나 이 묶음이
# 커지면 실패하고, 작아지면 이 목록도 같이 줄이라고 알려 준다.
허용_순환 = [frozenset({"damage", "reactions", "stats", "traits"})]


def _combat_import_그래프():
    """모듈 맨 위의 `from game.system.combat import X, Y`로 만든 {모듈: {불러온 combat 모듈}}."""
    그래프 = {m: set() for m in combat_모듈}
    for 모듈 in combat_모듈:
        트리 = ast.parse((combat_폴더 / f"{모듈}.py").read_text(encoding="utf-8"))
        for 노드 in 트리.body:
            if isinstance(노드, ast.ImportFrom) and 노드.module == "game.system.combat":
                그래프[모듈] |= {a.name for a in 노드.names if a.name in 그래프}
    return 그래프


def _강연결_묶음(그래프):
    """크기 2 이상인 강연결 성분(= 순환에 든 모듈 묶음). Tarjan."""
    번호, 낮은번호, 스택, 스택안, 결과 = {}, {}, [], set(), []

    def 방문(v):
        번호[v] = 낮은번호[v] = len(번호)
        스택.append(v)
        스택안.add(v)
        for w in 그래프[v]:
            if w not in 번호:
                방문(w)
                낮은번호[v] = min(낮은번호[v], 낮은번호[w])
            elif w in 스택안:
                낮은번호[v] = min(낮은번호[v], 번호[w])
        if 낮은번호[v] == 번호[v]:
            묶음 = set()
            while True:
                w = 스택.pop()
                스택안.discard(w)
                묶음.add(w)
                if w == v:
                    break
            if len(묶음) > 1:
                결과.append(frozenset(묶음))

    for v in 그래프:
        if v not in 번호:
            방문(v)
    return 결과


def test_combat_모듈_순환은_허용된_묶음뿐이다():
    실제 = _강연결_묶음(_combat_import_그래프())
    assert sorted(map(sorted, 실제)) == sorted(map(sorted, 허용_순환)), (
        f"combat 모듈 순환이 허용 목록과 다르다: 실제 {[sorted(s) for s in 실제]}. "
        "새 순환이면 의존 방향을 고치고(아래 계층이 위 계층을 부르지 않게 함수를 아래로 옮긴다), "
        "순환이 줄었으면 허용_순환도 줄인다."
    )


def test_순환_검사기는_순환을_찾는다():
    assert _강연결_묶음({"a": {"b"}, "b": {"c"}, "c": {"a"}, "d": {"a"}}) == [
        frozenset({"a", "b", "c"})
    ]
    assert _강연결_묶음({"a": {"b"}, "b": set()}) == []


def test_combat_모듈은_skill_system을_부르지_않는다():
    """combat은 skill_system보다 아래 계층이다(skill_system이 combat을 쓴다)."""
    위반 = []
    for 모듈 in combat_모듈:
        트리 = ast.parse((combat_폴더 / f"{모듈}.py").read_text(encoding="utf-8"))
        for 노드 in ast.walk(트리):
            if isinstance(노드, ast.ImportFrom) and (
                (노드.module or "").endswith("skill_system")
                or (노드.module or "").startswith("game.system.skill")
                or any(a.name in ("skill_system", "skill") for a in 노드.names)
            ):
                위반.append(모듈)
            if isinstance(노드, ast.Import) and any(
                a.name.endswith("skill_system")
                or a.name.startswith("game.system.skill")
                for a in 노드.names
            ):
                위반.append(모듈)
    assert not 위반, f"combat이 skill_system을 import한다: {위반}"


skill_폴더 = 루트 / "game" / "system" / "skill"
# 스킬 엔진 패키지의 계층(위가 아래를 부른다). 같은 줄끼리는 서로 부르지 않는다.
skill_계층 = [
    ["skill_grant"],
    ["skill_usage", "skill_target"],
    ["skill_apply"],
    ["skill_attack"],
    ["skill_run"],
]


def test_skill_패키지는_아래로만_부르고_밑줄_이름을_가져오지_않는다():
    """skill_system.py를 나눈 game/system/skill/ - 모듈은 skill_계층의 앞 줄 모듈만 부르고,
    `from game.system.skill.X import _이름`처럼 다른 모듈의 밑줄 이름을 가져오지 않는다."""
    층 = {m: i for i, 줄 in enumerate(skill_계층) for m in 줄}
    실제 = sorted(p.stem for p in skill_폴더.glob("skill_*.py"))
    assert 실제 == sorted(층), f"skill_계층과 실제 모듈이 다르다: {실제}"
    위반 = []
    for 모듈 in 실제:
        트리 = ast.parse((skill_폴더 / f"{모듈}.py").read_text(encoding="utf-8"))
        for 노드 in ast.walk(트리):
            if not (
                isinstance(노드, ast.ImportFrom)
                and (노드.module or "").startswith("game.system.skill.")
            ):
                continue
            대상 = 노드.module.rsplit(".", 1)[1]
            if 층[대상] >= 층[모듈]:
                위반.append(f"{모듈} -> {대상} (위 계층이나 같은 줄)")
            위반 += [
                f"{모듈}: {대상}.{a.name}" for a in 노드.names if a.name.startswith("_")
            ]
    assert not 위반, "skill 패키지 규칙 위반:\n" + "\n".join(위반)


def _별칭표(트리):
    """{코드에서 쓰는 이름: 검사 대상 모듈 이름} - `from game.system(.combat) import X [as Y]`."""
    표 = {}
    for 노드 in ast.walk(트리):
        if isinstance(노드, ast.ImportFrom) and 노드.module in (
            "game.system.combat",
            "game.system",
        ):
            for a in 노드.names:
                if a.name in 검사_모듈 and (
                    (노드.module == "game.system.combat") == (a.name in combat_모듈)
                ):
                    표[a.asname or a.name] = a.name
    return 표


def test_다른_모듈의_밑줄_이름을_쓰지_않는다():
    """`flow._턴_시작_처리`처럼 다른 모듈에서 부르는 이름은 공개 이름이다. 밑줄은 그 모듈 안에서만 쓴다.
    (R4 분할 뒤 모듈 경계를 넘은 77곳을 공개 이름으로 바꿨다.)"""
    위반 = []
    대상 = [
        p
        for p in 루트.rglob("*.py")
        if not set(p.parts) & {".git", ".buildozer", "node_modules", "graft"}
    ]
    for 경로 in 대상:
        트리 = ast.parse(경로.read_text(encoding="utf-8"))
        별칭 = _별칭표(트리)
        자기모듈 = (
            경로.stem
            if 경로.parent in (combat_폴더, 루트 / "game" / "system")
            else None
        )
        for 노드 in ast.walk(트리):
            if (
                isinstance(노드, ast.Attribute)
                and isinstance(노드.value, ast.Name)
                and 노드.value.id in 별칭
                and 노드.attr.startswith("_")
                and not 노드.attr.startswith("__")
                and 별칭[노드.value.id] != 자기모듈
            ):
                위반.append(
                    f"{경로.relative_to(루트)}:{노드.lineno} {노드.value.id}.{노드.attr}"
                )
    assert not 위반, (
        "다른 모듈의 밑줄 이름을 쓴다(공개 이름으로 바꾼다):\n" + "\n".join(위반)
    )


def test_게임_코드는_eval_exec_compile을_쓰지_않는다():
    """수식은 formula.안전_평가(제한된 AST 평가기)로만 계산한다(구조 점검 W-2). 데이터가 문자열을
    실행하는 길을 열어 두지 않는다."""
    위반 = []
    대상 = [루트 / "gameflow.py", 루트 / "main.py", *(루트 / "game").rglob("*.py")]
    for 경로 in 대상:
        for 노드 in ast.walk(ast.parse(경로.read_text(encoding="utf-8"))):
            if (
                isinstance(노드, ast.Call)
                and isinstance(노드.func, ast.Name)
                and 노드.func.id in ("eval", "exec", "compile")
            ):
                위반.append(f"{경로.relative_to(루트)}:{노드.lineno} {노드.func.id}()")
    assert not 위반, "eval/exec/compile 사용:\n" + "\n".join(위반)


def test_게임_코드는_random을_rng로만_쓴다():
    """무작위는 game/system/rng.py의 용도별 흐름에서만 나온다 - 전역 random을 쓰면 흐름 분리가 깨져
    굴림 하나에 모든 골든이 다시 밀린다."""
    위반 = []
    대상 = [루트 / "gameflow.py", 루트 / "main.py", *(루트 / "game").rglob("*.py")]
    for 경로 in 대상:
        if 경로 == 루트 / "game" / "system" / "rng.py":
            continue
        for 노드 in ast.walk(ast.parse(경로.read_text(encoding="utf-8"))):
            이름들 = []
            if isinstance(노드, ast.Import):
                이름들 = [a.name for a in 노드.names]
            elif isinstance(노드, ast.ImportFrom):
                이름들 = [노드.module or ""]
            if any(n == "random" or n.startswith("random.") for n in 이름들):
                위반.append(f"{경로.relative_to(루트)}:{노드.lineno}")
    assert not 위반, "random을 직접 import:\n" + "\n".join(위반)
