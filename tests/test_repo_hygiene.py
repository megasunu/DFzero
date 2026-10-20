"""저장소 규칙 검사 (코드 동작이 아니라 파일 자체)."""

import os
import re
import subprocess
import sys

from tools import fix_eol, scenario_registry


def test_모든_텍스트파일은_LF():
    위반 = fix_eol.crlf_files()
    assert not 위반, (
        "LF 규칙 위반(.claude/rules/eol.md) - `python tools/fix_eol.py`로 고친다:\n"
        + "\n".join(위반)
    )


def test_git_훅도_검사_대상이다():
    """훅(확장자 없음)은 sh가 실행하므로 CR이 섞이면 "/bin/sh^M" 오류가 난다."""
    훅들 = [p for p in fix_eol.text_files() if os.sep + ".githooks" + os.sep in p]
    assert any(p.endswith("pre-commit") for p in 훅들)


def test_gitattributes는_LF_정규화():
    결과 = subprocess.run(
        ["git", "check-attr", "text", "eol", "--", "main.py", ".githooks/pre-commit"],
        cwd=fix_eol.ROOT,
        capture_output=True,
        text=True,
    )
    if 결과.returncode != 0:  # git이 없는 환경(zip으로 받은 경우 등)은 건너뛴다
        return
    for 줄 in (
        "main.py: text: auto",
        "main.py: eol: lf",
        ".githooks/pre-commit: eol: lf",
    ):
        assert 줄 in 결과.stdout, 결과.stdout


# ------------------------------------------------------------ 할 일 기록


def test_할_일_기록은_작업_보드뿐이다():
    """2026-10-16부터 할 일과 상태는 megasunu 작업 보드(이슈)에만 둔다(CLAUDE.md "작업 보드").

    MEMORY.md/.memory/가 다시 생기면 보드와 두 곳이 어긋난다 - 할 일은 이슈로, 게임 규칙은 docs/game-rules.md로.
    """
    for 이름 in ("MEMORY.md", ".memory", os.path.join(".claude", "rules", "memory.md")):
        assert not os.path.exists(os.path.join(fix_eol.ROOT, 이름)), (
            f"{이름}가 다시 생겼다 - 할 일은 이슈(작업 보드)로, 게임 규칙은 docs/game-rules.md로"
        )


# ------------------------------------------------------------ 비밀값

# 공개 저장소다(CLAUDE.md "작업 방식") - 이슈와 Actions 로그까지 전부 공개다.
비밀값_확장자 = {".pem", ".key", ".keystore", ".jks", ".p12", ".pfx"}
비밀값_내용 = [
    ("개인 키", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("GitHub 토큰", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b|\bgithub_pat_\w{22,}")),
    ("AWS 액세스 키", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
]


def _비밀값_문제(경로, 내용):
    """커밋하면 안 되는 파일이나 내용이면 그 종류들(없으면 빈 목록). 경로는 `/`로 나눈 저장소 상대 경로."""
    이름 = 경로.rsplit("/", 1)[-1]
    if os.path.splitext(이름)[1].lower() in 비밀값_확장자 or (
        이름 == ".env"
        or (이름.startswith(".env.") and 이름 not in (".env.example", ".env.template"))
    ):
        return ["비밀값 파일"]
    return [종류 for 종류, 패턴 in 비밀값_내용 if 패턴.search(내용)]


def _커밋될_파일들():
    """git이 커밋할 파일: 추적 중인 것 + 무시되지 않은 새 파일. git이 없으면 None."""
    결과 = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=fix_eol.ROOT,
        capture_output=True,
    )
    if 결과.returncode != 0:
        return None
    return sorted({p for p in 결과.stdout.decode("utf-8").split("\0") if p})


def test_비밀값을_커밋하지_않는다():
    """키스토어, 토큰, `*.pem`, `.env`는 저장소에 두지 않는다 - CI 비밀은 GitHub Secrets로."""
    파일들 = _커밋될_파일들()
    if 파일들 is None:  # git이 없는 환경(zip으로 받은 경우 등)은 건너뛴다
        return
    위반 = []
    for 경로 in 파일들:
        전체 = os.path.join(fix_eol.ROOT, *경로.split("/"))
        if not os.path.isfile(전체):  # 지운 뒤 아직 커밋하지 않은 파일
            continue
        이름 = 경로.rsplit("/", 1)[-1]
        글 = (
            os.path.splitext(이름)[1].lower() in fix_eol.TEXT_EXTS
            or 이름 in fix_eol.TEXT_NAMES
            or "." not in 이름
        )
        with open(전체, "rb") as f:
            내용 = f.read().decode("utf-8", "replace") if 글 else ""
        위반 += [f"{경로}: {종류}" for 종류 in _비밀값_문제(경로, 내용)]
    assert not 위반, (
        "비밀값을 커밋하려 한다 - 지우고, 이미 push했으면 값을 바꾼다:\n"
        + "\n".join(위반)
    )


def test_비밀값_검사는_어긋남을_잡는다():
    # 패턴을 이어 붙여 만든다 - 이 파일 자체가 검사에 걸리지 않게.
    키 = "-----BEGIN " + "RSA PRIVATE KEY-----\nMIIE\n"
    토큰 = "gh" + "p_" + "a" * 36
    assert _비밀값_문제("release.keystore", "") == ["비밀값 파일"]
    assert _비밀값_문제("config/.env", "") == ["비밀값 파일"]
    assert _비밀값_문제("docs/key.md", 키) == ["개인 키"]
    assert _비밀값_문제("tools/x.py", f"TOKEN = '{토큰}'") == ["GitHub 토큰"]
    assert _비밀값_문제("tools/x.py", "AKIA" + "ABCDEFGHIJKLMNOP") == ["AWS 액세스 키"]
    assert _비밀값_문제(".env.example", "") == []
    assert _비밀값_문제("game/data/a.py", "ghp_ 접두사만 있는 글") == []


# ------------------------------------------------------------ CLAUDE.md / 규칙 파일 / 스킬

CLAUDE_최대_줄 = 100  # 매 세션 읽는다 - 길면 지시가 덜 지켜진다
규칙_최대_줄 = 80  # .claude/rules/*.md: 해당 파일을 건드릴 때만 읽힌다


def _머리말(텍스트):
    """첫 줄이 ---로 시작하는 머리말의 줄들. 없거나 닫히지 않았으면 None."""
    줄들 = 텍스트.splitlines()
    if not 줄들 or 줄들[0] != "---":
        return None
    for i, 줄 in enumerate(줄들[1:], start=1):
        if 줄 == "---":
            return 줄들[1:i]
    return None


def 규칙_파일_문제(이름, 텍스트):
    """.claude/rules/ 파일이 어기는 규칙들(없으면 빈 목록)."""
    문제 = []
    줄수 = len(텍스트.splitlines())
    if 줄수 > 규칙_최대_줄:
        문제.append(
            f"{이름}: {줄수}줄(상한 {규칙_최대_줄}) - 나누거나 절차는 스킬로 옮긴다"
        )
    머리말 = _머리말(텍스트)
    if 머리말 is None or not any(m.startswith("paths:") for m in 머리말):
        문제.append(
            f"{이름}: 머리말에 paths:가 없다 - 없으면 매 세션 읽힌다(---, paths: 목록, ---로 시작)"
        )
    return 문제


def 스킬_파일_문제(폴더이름, 텍스트):
    """.claude/skills/<폴더>/SKILL.md가 어기는 규칙들."""
    머리말 = _머리말(텍스트)
    if 머리말 is None:
        return [f"{폴더이름}: 머리말(---)이 없다"]
    값 = {}
    for 줄 in 머리말:
        if ":" in 줄 and not 줄.startswith(" "):
            키, _, 내용 = 줄.partition(":")
            값[키.strip()] = 내용.strip()
    문제 = []
    if 값.get("name") != 폴더이름:
        문제.append(f"{폴더이름}: name이 폴더 이름과 다르다({값.get('name')!r})")
    if not 값.get("description"):
        문제.append(f"{폴더이름}: description이 비었다 - 스킬은 이 글로 골라진다")
    설명 = 값.get("description", "")
    if ": " in 설명 or " #" in 설명:
        문제.append(
            f"{폴더이름}: description에 ': ' 또는 ' #'가 있어 YAML이 깨진다 - 풀어 쓰거나 따옴표로 감싼다"
        )
    return 문제


def _읽기(경로):
    with open(경로, encoding="utf-8") as f:
        return f.read()


def test_CLAUDE_md는_100줄_이하():
    """CLAUDE.md는 매 세션 읽힌다. 한 부분에만 해당하는 규칙은 .claude/rules/, 절차는 스킬로."""
    텍스트 = _읽기(os.path.join(fix_eol.ROOT, "CLAUDE.md"))
    줄수 = len(텍스트.splitlines())
    assert 줄수 <= CLAUDE_최대_줄, (
        f"CLAUDE.md가 {줄수}줄이다(상한 {CLAUDE_최대_줄}) - 한 부분에만 해당하는 규칙은 "
        ".claude/rules/<주제>.md(paths: 머리말)로, 절차는 .claude/skills/로 옮긴다"
    )


def test_CLAUDE_md는_전역_규칙의_예외를_이름으로_적는다():
    """Kade의 전역 규칙(~/.claude/AGENTS.md "Precedence"): 저장소가 바꾸는 전역 규칙은
    "Overrides of global rules" 섹션에 굵은 머리 불릿으로 하나씩 적는다. 적지 않은 것은 전역 규칙을 따른다."""
    텍스트 = _읽기(os.path.join(fix_eol.ROOT, "CLAUDE.md"))
    섹션 = re.search(
        r"^## Overrides of global rules\b.*\n((?:(?!## ).*\n?)*)", 텍스트, re.M
    )
    assert 섹션, 'CLAUDE.md에 "## Overrides of global rules" 섹션이 없다'
    본문 = 섹션.group(1)
    assert re.search(r"^- \*\*[^*]+\*\*", 본문, re.M) or "없음." in 본문, (
        '예외는 "- **이름.** 설명" 꼴로 적는다(없으면 "없음."이라고 쓴다)'
    )


def test_규칙_파일은_80줄_이하이고_paths를_가진다():
    폴더 = os.path.join(fix_eol.ROOT, ".claude", "rules")
    파일들 = (
        sorted(f for f in os.listdir(폴더) if f.endswith(".md"))
        if os.path.isdir(폴더)
        else []
    )
    문제 = []
    for 이름 in 파일들:
        문제 += 규칙_파일_문제(이름, _읽기(os.path.join(폴더, 이름)))
    assert not 문제, "\n".join(문제)


def test_스킬은_이름과_설명을_가진다():
    폴더 = os.path.join(fix_eol.ROOT, ".claude", "skills")
    이름들 = sorted(os.listdir(폴더)) if os.path.isdir(폴더) else []
    문제 = []
    for 이름 in 이름들:
        경로 = os.path.join(폴더, 이름, "SKILL.md")
        if not os.path.exists(경로):
            문제.append(f"{이름}: SKILL.md가 없다")
            continue
        문제 += 스킬_파일_문제(이름, _읽기(경로))
    assert not 문제, "\n".join(문제)


def test_규칙_파일_검사는_어긋남을_잡는다():
    좋음 = '---\npaths:\n  - "game/**"\n---\n\n# 제목\n'
    assert 규칙_파일_문제("a.md", 좋음) == []
    assert "paths:가 없다" in "\n".join(규칙_파일_문제("b.md", "# 머리말 없음\n"))
    assert "paths:가 없다" in "\n".join(규칙_파일_문제("c.md", "---\nname: x\n---\n"))
    assert "paths:가 없다" in "\n".join(
        규칙_파일_문제("d.md", "---\npaths:\n  - x\n")
    )  # 안 닫힘
    긴 = 좋음 + "줄\n" * 규칙_최대_줄
    assert "줄(상한 80)" in "\n".join(규칙_파일_문제("e.md", 긴))


def test_스킬_검사는_어긋남을_잡는다():
    좋음 = "---\nname: foo\ndescription: 무엇을 언제\n---\n본문\n"
    assert 스킬_파일_문제("foo", 좋음) == []
    assert "머리말(---)이 없다" in "\n".join(스킬_파일_문제("foo", "본문\n"))
    assert "name이 폴더 이름과 다르다" in "\n".join(스킬_파일_문제("bar", 좋음))
    assert "description이 비었다" in "\n".join(
        스킬_파일_문제("foo", "---\nname: foo\ndescription:\n---\n")
    )
    깨짐 = "---\nname: foo\ndescription: 언제 쓰나: 이런 때\n---\n"
    assert "YAML이 깨진다" in "\n".join(스킬_파일_문제("foo", 깨짐))
    assert "YAML이 깨진다" in "\n".join(
        스킬_파일_문제("foo", "---\nname: foo\ndescription: 이것 # 주석\n---\n")
    )


# ------------------------------------------------------------ 풀 시나리오 장부


def test_시나리오_문서와_테스트_마커가_일치한다():
    """docs/scenarios.md 표 <-> @pytest.mark.scenario("ID") (.claude/rules/scenarios.md)."""
    문제 = scenario_registry.점검()
    assert not 문제, "\n".join(문제)


def test_시나리오_대조는_어긋남을_잡는다():
    문서 = """## 시나리오
| ID | 상태 | 기능 | 방법 | 테스트 |
|---|---|---|---|---|
| S1 | 구현 | 전투 | 귀검사 | test_a.py::test_x |
| S2 | 계획 | 성장 | 5직업 | - |
| S2 | 계획 | 중복 | 중복 | - |
| S3 | 구현 | 장비 | 방어구 | test_a.py::test_y |
| s4 | 모름 | | | - |
## 다른 절
| S9 | 구현 | 무시 | 무시 | 무시 |
"""
    표시 = {
        "test_a.py::test_x": "S1",
        "test_a.py::test_z": "S7",
        "test_a.py::test_w": "S2",
    }
    문제 = "\n".join(scenario_registry.대조(scenario_registry.문서_행(문서), 표시))
    assert "ID S2가 중복" in 문제
    assert "ID 형식 오류 's4'" in 문제
    assert "s4: 상태는" in 문제 and "s4: 기능/방법 칸이 비었다" in 문제
    assert "test_z: 문서에 없는 시나리오 ID 'S7'" in 문제
    assert "test_w: 문서에서 S2의 상태가 '구현'이 아니다" in 문제
    assert "S3: 구현인데 마커를 단 테스트가 없다" in 문제
    assert "S3: 문서의 테스트 칸" in 문제
    assert "S2: 계획인데 테스트가 있다" in 문제
    assert "S9" not in 문제 and "S1:" not in 문제


def test_시나리오_마커는_소스에서_읽는다():
    소스 = (
        "import pytest\n"
        '@pytest.mark.scenario("S1")\n'
        "def test_a(): pass\n"
        '@pytest.mark.parametrize("x", [1])\n'
        "def test_b(x): pass\n"
    )
    assert scenario_registry.테스트_표시(소스, "t.py") == {"t.py::test_a": "S1"}


# ------------------------------------------------------------ APK 빌드 트리거


def _저장소_파일(상대경로):
    return _읽기(os.path.join(fix_eol.ROOT, 상대경로))


def test_APK_빌드는_v_태그_push로만_돈다():
    """CLAUDE.md "Git" - 큰 기능을 끝내면 사용자가 v<version> 태그를 push해 빌드한다. 다른 트리거를 되살리지 않는다."""
    워크플로 = _저장소_파일(".github/workflows/build-apk.yml")
    on = 워크플로.split("\npermissions:")[0]
    assert re.search(r"^  push:\n    tags:\n      - 'v\*'\n", on, re.M), on
    assert (
        "workflow_dispatch" not in on and "paths:" not in on and "branches:" not in on
    )
    assert "$GITHUB_REF_NAME" in 워크플로 or "github.ref_name" in 워크플로
    assert (
        "--notes-file CHANGELOG.md" in 워크플로
    )  # 릴리스 페이지에 이번 마이너의 변경 내역이 보인다


def test_APK_태그_검사가_읽는_spec_버전이_있다():
    """워크플로의 태그-버전 검사와 같은 정규식으로 buildozer.spec의 version을 읽을 수 있어야 한다."""
    워크플로 = _저장소_파일(".github/workflows/build-apk.yml")
    assert "buildozer.spec" in 워크플로 and "does not match" in 워크플로
    줄 = re.findall(r"^version *= *(\S+)\s*$", _저장소_파일("buildozer.spec"), re.M)
    assert len(줄) == 1 and re.fullmatch(r"\d+\.\d+\.\d+", 줄[0]), (
        줄
    )  # major.minor.patch


# ------------------------------------------------------------ CHANGELOG.md


def _spec_버전():
    return re.findall(r"^version *= *(\S+)\s*$", _저장소_파일("buildozer.spec"), re.M)[
        0
    ]


def _변경내역_제목들(본문):
    """`## ` 제목 줄의 이름 목록. 버전 제목은 `## 0.1.1 (날짜)` 꼴이다."""
    return [줄[3:].strip() for 줄 in 본문.splitlines() if 줄.startswith("## ")]


def _변경내역_문제(본문, 버전):
    """CHANGELOG 규칙을 어긴 곳(없으면 빈 목록). 마이너 버전을 릴리스하면 파일을 비우고 새로 시작한다."""
    제목들 = _변경내역_제목들(본문)
    문제 = []
    if not 제목들 or 제목들[0] != "미릴리스":
        문제.append("첫 제목이 `## 미릴리스`가 아니다")
    버전들 = [
        m.group(1)
        for t in 제목들[1:]
        if (m := re.match(r"(\d+\.\d+\.\d+)( \(\d{4}-\d{2}-\d{2}\))?$", t))
    ]
    if len(버전들) != len(제목들) - 1:
        문제.append("버전 제목이 `## x.y.z (YYYY-MM-DD)` 꼴이 아니다")
    if 버전 not in 버전들:
        문제.append(f"buildozer.spec 버전 {버전}의 제목이 없다")
    마이너 = ".".join(버전.split(".")[:2])
    for v in 버전들:
        if ".".join(v.split(".")[:2]) != 마이너:
            문제.append(f"{v}: 현재 마이너 {마이너}가 아니다(마이너 릴리스 때 비운다)")
    if 버전들 != sorted(
        버전들, key=lambda v: tuple(map(int, v.split("."))), reverse=True
    ):
        문제.append("버전 제목이 최신순이 아니다")
    return 문제


def test_CHANGELOG는_규칙을_지킨다():
    """.claude/rules/build-and-save.md - 이 파일이 변경 내역의 유일한 출처다."""
    문제 = _변경내역_문제(_저장소_파일("CHANGELOG.md"), _spec_버전())
    assert not 문제, "\n".join(문제)


def test_CHANGELOG_검사는_어긋남을_잡는다():
    좋음 = "# 변경 내역\n\n## 미릴리스\n- a\n\n## 0.1.2 (2026-10-11)\n- b\n\n## 0.1.1 (2026-10-10)\n- c\n"
    assert _변경내역_문제(좋음, "0.1.2") == []
    assert any(
        "미릴리스" in m for m in _변경내역_문제("## 0.1.1 (2026-10-10)\n", "0.1.1")
    )
    assert any("0.1.3" in m for m in _변경내역_문제(좋음, "0.1.3"))
    # 마이너를 올렸는데 옛 마이너 내용이 남아 있다
    남음 = "## 미릴리스\n\n## 0.2.0 (2026-11-01)\n\n## 0.1.1 (2026-10-10)\n"
    assert any("0.1.1" in m and "마이너" in m for m in _변경내역_문제(남음, "0.2.0"))
    assert any(
        "최신순" in m
        for m in _변경내역_문제("## 미릴리스\n\n## 0.1.1\n\n## 0.1.2\n", "0.1.2")
    )


# ------------------------------------------------------------ 워크플로 권한과 SDK/NDK 캐시

ANDROID_해시_명령 = "grep '^android\\.' buildozer.spec | sha256sum"


def _워크플로들():
    폴더 = os.path.join(fix_eol.ROOT, ".github", "workflows")
    return {
        n: _읽기(os.path.join(폴더, n))
        for n in sorted(os.listdir(폴더))
        if n.endswith(".yml")
    }


def test_워크플로는_권한을_비우고_checkout은_자격증명을_남기지_않는다():
    """CLAUDE.md "GitHub 워크플로" - 맨 위 `permissions: {}`와 잡별 권한, checkout마다 persist-credentials: false."""
    for 이름, 본문 in _워크플로들().items():
        assert re.search(r"^permissions: \{\}$", 본문, re.M), 이름
        assert 본문.count("uses: actions/checkout@") == 본문.count(
            "persist-credentials: false"
        ), 이름


def test_SDK_NDK_캐시_키는_android_줄만_해시한다():
    """version을 올려도(릴리스마다) 캐시가 유지되고, android.* 줄이 바뀔 때만 키가 바뀐다."""
    for 이름 in ("build-apk.yml", "warm-cache.yml"):
        본문 = _워크플로들()[이름]
        assert ANDROID_해시_명령 in 본문, 이름
        assert "hashFiles('buildozer.spec')" not in 본문, 이름
        assert "restore-keys" in 본문, 이름


def test_태그_빌드는_캐시를_불러오기만_한다():
    """태그 실행이 저장한 캐시는 다음 태그가 못 쓴다 - 저장은 main-branch의 warm-cache.yml만 한다."""
    태그 = _워크플로들()["build-apk.yml"]
    assert "actions/cache/restore@v4" in 태그
    assert "uses: actions/cache@" not in 태그 and "actions/cache/save" not in 태그


def test_캐시_채우기는_main_branch에서_spec이_바뀔_때만_돈다():
    본문 = _워크플로들()["warm-cache.yml"]
    on = 본문.split("\npermissions:")[0]
    assert re.search(
        r"^  push:\n    branches:\n      - main-branch\n    paths:\n      - buildozer\.spec\n",
        on,
        re.M,
    ), on
    assert "schedule" not in on and "tags:" not in on and "workflow_dispatch" not in on
    assert (
        "gh release" not in 본문 and "contents: write" not in 본문
    )  # 릴리스를 만들지 않는다


# ------------------------------------------------------------ 자동 병합(auto-merge.yml)


def _필수_검사(본문):
    """auto-merge.yml의 `REQUIRE: |` 블록에 적힌 check run 이름들."""
    블록 = re.search(r"^ +REQUIRE: \|\n((?: {12}\S.*\n)+)", 본문, re.M)
    assert 블록, "auto-merge.yml에 REQUIRE: | 블록이 없다"
    return [줄.strip() for 줄 in 블록.group(1).splitlines()]


def test_자동_병합의_필수_검사는_check_yml의_잡과_같다():
    """잡 이름이 바뀌었는데 REQUIRE가 그대로면 모든 PR이 영영 "wait"에 머문다."""
    워크플로들 = _워크플로들()
    병합, 검사 = 워크플로들["auto-merge.yml"], 워크플로들["check.yml"]
    검사_이름 = re.search(r"^name: (.+)$", 검사, re.M).group(1)
    assert f'workflows: ["{검사_이름}"]' in 병합
    잡들 = re.findall(r"^  ([\w-]+):\n", 검사.split("\njobs:\n", 1)[1], re.M)
    assert (
        "\n    name:" not in 검사
    )  # 잡에 name:이 붙으면 check run 이름이 잡 id가 아니게 된다
    # main-status는 main-branch 실행에서만 돈다(PR에서는 건너뜀) - 필수 검사가 아니다.
    assert sorted(_필수_검사(병합)) == sorted(j for j in 잡들 if j != "main-status")


def _잡(본문, 이름):
    """워크플로 본문에서 잡 하나의 줄들(다음 잡 전까지)."""
    잡들 = 본문.split("\njobs:\n", 1)[1]
    찾음 = re.search(rf"^  {re.escape(이름)}:\n((?:(?:    .*)?\n)*)", 잡들, re.M)
    assert 찾음, f"{이름} 잡이 없다"
    return 찾음.group(1)


def test_자동_병합_뒤와_매주_main_branch를_다시_검사한다():
    """GITHUB_TOKEN 병합은 main-branch에 push 실행을 만들지 않아 병합 커밋이 검사되지 않았다(#206).
    workflow_dispatch는 GITHUB_TOKEN으로도 실행이 생기므로, 병합한 뒤 auto-merge.yml이 Check를 부른다."""
    워크플로들 = _워크플로들()
    병합, 검사 = 워크플로들["auto-merge.yml"], 워크플로들["check.yml"]
    부르기 = '      gh workflow run check.yml --repo "$REPO" --ref main-branch'
    assert 부르기 in 병합
    assert 병합.index("gh pr merge") < 병합.index(부르기)
    assert re.search(r"^      actions: write\b", _잡(병합, "merge"), re.M)
    on = 검사.split("\npermissions:")[0]
    assert "\n  workflow_dispatch:" in on and re.search(
        r"^  schedule:\n    - cron: ", on, re.M
    )


def test_main_branch가_빨가면_이슈를_열고_보드에_올린다():
    """main-branch 실행이 실패하면 "main-branch가 빨갛다: Check" 이슈를 열고, 통과하면 닫는다.
    GITHUB_TOKEN이 연 이슈는 project-sync를 깨우지 않으므로 보드 브리지를 직접 부른다."""
    잡 = _잡(_워크플로들()["check.yml"], "main-status")
    assert "needs: [check, ui-smoke]" in 잡
    assert re.search(
        r"^    if: always\(\) && github\.ref == 'refs/heads/main-branch'$", 잡, re.M
    )
    assert "main-branch가 빨갛다: Check" in 잡
    assert "python3 tools/project_bridge.py sync" in 잡
    # 새로 연 이슈는 백로그가 아니라 지금·1순위로(보낸 사람이 없어 라벨 명령은 못 쓴다)
    assert (
        "APPLY_COMMANDS: ${{ steps.issue.outputs.action == 'opened' && "
        "'명령:상태-지금 명령:우선순위-1' || '' }}"
    ) in 잡
    assert "actions/create-github-app-token@" in 잡 and "contents: write" not in 잡


def test_자동_병합은_claude_브랜치에서_main_branch로만_병합한다():
    본문 = _워크플로들()["auto-merge.yml"]
    assert "startsWith(github.event.workflow_run.head_branch, 'claude/')" in 본문
    assert "--base main-branch" in 본문 and "--match-head-commit" in 본문
    assert "python3 tools/auto_merge_gate.py" in 본문


def test_자동_병합은_PR_코드를_체크아웃하지_않는다():
    """workflow_run은 쓰기 권한으로 돈다 - 기본 브랜치의 판정 스크립트만 실행하고 PR 코드는 받지 않는다."""
    본문 = _워크플로들()["auto-merge.yml"]
    assert 본문.count("uses: actions/checkout@") == 1
    assert "ref:" not in 본문 and "repository:" not in 본문


# ------------------------------------------------------------ context-guard 훅


def test_context_guard_훅이_등록되고_게이트가_그_테스트를_돌린다():
    """handoff-trigger 스킬은 이 훅의 메시지(맥락 크기)를 전제로 한다 - 등록이 빠지면 숫자를 모른다."""
    import json

    from tools import check

    with open(
        os.path.join(fix_eol.ROOT, ".claude", "settings.json"), encoding="utf-8"
    ) as f:
        훅 = json.load(f)["hooks"]
    명령 = 'node "$CLAUDE_PROJECT_DIR/.claude/hooks/context-guard.cjs"'
    assert 명령 in [
        h["command"] for 묶음 in 훅["UserPromptSubmit"] for h in 묶음["hooks"]
    ]
    assert [
        (묶음["matcher"], [h["command"] for h in 묶음["hooks"]])
        for 묶음 in 훅["SessionStart"]
    ] == [("compact", [명령])]
    assert os.path.isfile(
        os.path.join(fix_eol.ROOT, ".claude", "hooks", "context-guard.cjs")
    )
    assert any(이름 == "node --test" for 이름, _ in check.STEPS)
    assert ".cjs" in fix_eol.TEXT_EXTS


def test_time_log_훅이_모든_도구와_턴에_등록되고_게이트가_그_테스트를_돌린다():
    """작업시간 기록(임시, #236) - 등록이 빠지면 그 이벤트의 시간이 조용히 비어 버린다."""
    import json

    from tools import check

    with open(
        os.path.join(fix_eol.ROOT, ".claude", "settings.json"), encoding="utf-8"
    ) as f:
        훅 = json.load(f)["hooks"]
    명령 = 'node "$CLAUDE_PROJECT_DIR/.claude/hooks/time-log.cjs"'
    for 이벤트 in (
        "PreToolUse",
        "PostToolUse",
        "PostToolUseFailure",
        "UserPromptSubmit",
        "Stop",
    ):
        묶음들 = 훅[이벤트]
        assert any(
            묶음.get("matcher", "*") == "*"
            and 명령 in [h["command"] for h in 묶음["hooks"]]
            for 묶음 in 묶음들
        ), 이벤트
    단계 = dict(check.STEPS)["node --test"]
    assert ".claude/hooks/time-log.test.cjs" in 단계
    assert ".claude/time-log/" in _읽기(os.path.join(fix_eol.ROOT, ".gitignore"))


def test_게이트는_단계별_시간을_작업시간_기록에_남긴다(tmp_path):
    """작업시간 기록(임시, #239) - 가장 최근 세션 기록에 GateStep 한 줄. 기록 폴더가 없으면(CI) 아무것도 안 한다."""
    import json

    from tools import check

    check.시간_기록(str(tmp_path / "없음"), "pytest", 1.23, True)
    assert not (tmp_path / "없음").exists()

    (tmp_path / "옛.jsonl").write_text("", encoding="utf-8")
    최근 = tmp_path / "새.jsonl"
    최근.write_text("", encoding="utf-8")
    os.utime(tmp_path / "옛.jsonl", (0, 0))
    check.시간_기록(str(tmp_path), "pytest", 1.23, False)
    줄 = json.loads(최근.read_text(encoding="utf-8"))
    assert (줄["ev"], 줄["step"], 줄["sec"], 줄["ok"]) == (
        "GateStep",
        "pytest",
        1.2,
        False,
    )
    assert (tmp_path / "옛.jsonl").read_text(encoding="utf-8") == ""


def _게이트_실행(monkeypatch, tmp_path, 단계들, 인자=()):
    """check.main을 가짜 단계로 돌리고 (종료 코드, 실제로 돈 명령들)을 돌려준다."""
    import subprocess
    from types import SimpleNamespace

    from tools import check

    돈_명령 = []

    def 가짜_실행(cmd, cwd=None):
        돈_명령.append(cmd)
        return SimpleNamespace(returncode=1 if "실패" in cmd else 0)

    monkeypatch.setattr(check, "STEPS", 단계들)
    monkeypatch.setattr(check, "TIME_LOG", str(tmp_path))  # 세션 기록을 더럽히지 않는다
    monkeypatch.setattr(subprocess, "run", 가짜_실행)
    return check.main(list(인자)), 돈_명령


def test_게이트는_싼_검사가_실패하면_테스트로_넘어가지_않는다(monkeypatch, tmp_path):
    """서식 하나 틀려도 1분 넘는 테스트를 다 돌고 다시 돌리던 낭비를 막는다."""
    단계들 = [
        ("compileall", ["컴파일"]),
        ("ruff check", ["린트"]),
        ("ruff format", ["서식", "실패"]),
        ("pytest", ["테스트"]),
        ("node --test", ["훅"]),
    ]
    코드, 돈_명령 = _게이트_실행(monkeypatch, tmp_path, 단계들)
    assert 코드 == 1
    assert 돈_명령 == [["컴파일"], ["린트"], ["서식", "실패"]]


def test_게이트_빠른_확인은_커버리지_없이_고른_테스트만_돌린다(monkeypatch, tmp_path):
    from tools import check

    단계들 = [("ruff check", ["린트"]), ("pytest", check.PYTEST)]
    코드, 돈_명령 = _게이트_실행(
        monkeypatch, tmp_path, 단계들, ["--빠른", "tests/test_battle_log.py"]
    )
    assert 코드 == 0
    테스트_명령 = 돈_명령[-1]
    assert 테스트_명령[:3] == [sys.executable, "-m", "pytest"]
    assert not [a for a in 테스트_명령 if a.startswith("--cov")]
    assert 테스트_명령[-1] == "tests/test_battle_log.py"


def test_게이트는_빠른_확인_없이_테스트를_고르면_거절한다(monkeypatch, tmp_path):
    """전체 게이트에서 테스트 일부만 돌면 커버리지 하한이 거짓으로 깨진다."""
    코드, 돈_명령 = _게이트_실행(
        monkeypatch, tmp_path, [("pytest", ["테스트"])], ["tests/test_x.py"]
    )
    assert 코드 == 2
    assert 돈_명령 == []


def test_게이트는_병렬_도구가_있으면_테스트를_나눠_돌린다():
    """pytest-xdist가 있으면 -n auto(4코어에서 약 124초 -> 57초). 없으면 직렬로 돌고 그 사실을 알린다."""
    from tools import check

    전체 = check.pytest_명령(빠른=False, 파일=[], 병렬=True, 커버리지=True)
    assert "-n" in 전체 and 전체[전체.index("-n") + 1] == "auto"
    assert "--cov-branch" in 전체
    assert "-n" not in check.pytest_명령(빠른=False, 파일=[], 병렬=False, 커버리지=True)
    # 빠른 확인: 파일을 고르면 직렬(병렬 준비가 더 오래 걸린다), 전부면 병렬, 커버리지는 늘 없다
    고름 = check.pytest_명령(빠른=True, 파일=["tests/a.py"], 병렬=True, 커버리지=True)
    assert "-n" not in 고름 and 고름[-1] == "tests/a.py"
    assert not [a for a in 고름 if a.startswith("--cov")]
    assert "-n" in check.pytest_명령(빠른=True, 파일=[], 병렬=True, 커버리지=True)
