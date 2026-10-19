"""완료 기준(DoD) 게이트 - 커밋 전에 이것 하나만 돌린다.

    python tools/check.py

1. compileall  : 모든 .py 파일 문법 검사
2. ruff check  : 정의 안 된 이름, 안 쓰는 import 등 (pyproject.toml 설정)
   ruff format --check : 서식 검사 - 어긋나면 `python -m ruff format .`로 고친다
3. pytest      : tests/ (kivy 없이 gameflow 이하 로직만 헤드리스로 검사)
                pytest-cov가 설치돼 있으면 game/system + game/controller + gameflow.py 커버리지가
                COVERAGE_FLOOR(%) 아래로 떨어져도 실패한다(CI는 항상 설치).
4. node --test : .claude/hooks/의 훅(context-guard 맥락 크기, time-log 작업시간)의 테스트. node가 없으면 건너뛰고
                NOT VERIFIED라고 찍는다(CI 러너에는 node가 있다).

하나라도 실패하면 0이 아닌 코드로 끝난다. Windows/리눅스 어디서나 돈다.
필요한 도구: pip install pytest pytest-cov ruff==0.16.9 (CI와 같은 버전 - 서식 결과가 버전마다 다르다)
"""

import importlib.util
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2026-10-14 측정 94.57%(품질 계획 P7에서 90 -> 92). 떨어뜨리지 말고, 올리면 이 값도 올린다.
COVERAGE_FLOOR = 92

PYTEST = [sys.executable, "-m", "pytest"]
if importlib.util.find_spec("pytest_cov") is not None:
    PYTEST += [
        "--cov=game.system",
        "--cov=game.controller",
        "--cov=gameflow",
        "--cov-branch",
        "--cov-report=term:skip-covered",
        f"--cov-fail-under={COVERAGE_FLOOR}",
    ]

STEPS = [
    (
        "compileall",
        [
            sys.executable,
            "-m",
            "compileall",
            "-q",
            "-x",
            r"[\\/](\.buildozer|bin|\.git)[\\/]",
            ".",
        ],
    ),
    ("ruff check", [sys.executable, "-m", "ruff", "check", "."]),
    ("ruff format", [sys.executable, "-m", "ruff", "format", "--check", "."]),
    ("pytest", PYTEST),
    (
        "node --test",
        [
            "node",
            "--test",
            ".claude/hooks/context-guard.test.cjs",
            ".claude/hooks/time-log.test.cjs",
        ],
    ),
]


def main():
    # Windows에서 리디렉션된 출력은 cp1252라 한글 print가 죽는다(#200) - 콘솔 인코딩과 상관없이 UTF-8로.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    failed = []
    for name, cmd in STEPS:
        if name == "pytest" and not os.path.isdir(os.path.join(ROOT, "tests")):
            print(f"== {name}: tests/ 없음, 건너뜀")
            continue
        if name == "node --test" and shutil.which("node") is None:
            print(
                f"== {name}: node 없음, 건너뜀 - NOT VERIFIED: context-guard·time-log 훅 테스트"
            )
            continue
        print(f"== {name}")
        if name == "pytest" and "--cov-branch" not in cmd:
            print(
                "   (pytest-cov 없음 - 커버리지 하한 검사를 건너뜀: pip install pytest-cov)"
            )
        result = subprocess.run(cmd, cwd=ROOT)
        if result.returncode != 0:
            failed.append(name)
    print()
    if failed:
        print("FAIL: " + ", ".join(failed))
        return 1
    print("PASS: 모든 검사 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
