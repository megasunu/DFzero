"""완료 기준(DoD) 게이트 - CI가 모든 push/PR에서 전체를 돌려 커버리지 하한까지 판정한다. push 전 로컬 확인은 --빠른 한 번(#285).

    python tools/check.py                            # 전체: 커버리지 하한 포함 - CI의 판정
    python tools/check.py --빠른 [테스트 파일 ...]   # 커버리지 없음 - 파일 없이 주면 push 전 로컬 확인
    python tools/check.py --골든                     # 서식 고침 + 골든 갱신(직렬) + 차이 요약, 출력은 요약만

1. compileall  : 모든 .py 파일 문법 검사
2. ruff check  : 정의 안 된 이름, 안 쓰는 import 등 (pyproject.toml 설정)
   ruff format --check : 서식 검사 - 어긋나면 `python -m ruff format .`로 고친다
3. pytest      : tests/ (kivy 없이 gameflow 이하 로직만 헤드리스로 검사)
                pytest-cov가 설치돼 있으면 game/system + game/controller + gameflow.py 커버리지가
                COVERAGE_FLOOR(%) 아래로 떨어져도 실패한다(CI는 항상 설치).
4. node --test : .claude/hooks/의 훅(context-guard 맥락 크기, time-log 작업시간)의 테스트. node가 없으면 건너뛰고
                NOT VERIFIED라고 찍는다(CI 러너에는 node가 있다).

앞의 싼 검사(1, 2)가 실패하면 테스트로 넘어가지 않고 멈춘다 - 고친 뒤 어차피 다시 돌린다.
`--빠른`은 커버리지 없이 테스트(파일을 주면 그 파일만)를 돌린다. 파일 없이 주면 push 전 로컬 확인이고, 하한은 CI가 판정한다.
`--골든`은 골든이 바뀐 작업의 마무리 한 줄이다: pytest 출력 전체는 임시 폴더 로그에 쓰고 FAILED/ERROR 줄과 끝 줄만 찍는다.
하나라도 실패하면 0이 아닌 코드로 끝난다. Windows/리눅스 어디서나 돈다.
필요한 도구: pip install pytest pytest-cov pytest-xdist==3.8.0 ruff==0.16.9 (CI와 같은 버전 - 서식 결과가 버전마다 다르다)
"""

import datetime
import glob
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2026-10-14 측정 94.57%(품질 계획 P7에서 90 -> 92). 떨어뜨리지 말고, 올리면 이 값도 올린다.
COVERAGE_FLOOR = 92

PYTEST_BASE = [sys.executable, "-m", "pytest"]
커버리지_있음 = importlib.util.find_spec("pytest_cov") is not None
병렬_있음 = importlib.util.find_spec("xdist") is not None  # pytest-xdist


def pytest_명령(빠른, 파일, 병렬, 커버리지):
    """게이트의 pytest 명령. 병렬이면 -n auto(4코어에서 약 124초 -> 57초) - 빠른 확인에서 파일을 고르면
    직렬이다(작업자를 띄우는 데 더 걸린다). 커버리지 하한은 전체 게이트에만 붙는다."""
    명령 = list(PYTEST_BASE)
    if 병렬 and not (빠른 and 파일):
        명령 += ["-n", "auto"]
    if 커버리지 and not 빠른:
        명령 += [
            "--cov=game.system",
            "--cov=game.controller",
            "--cov=gameflow",
            "--cov-branch",
            "--cov-report=term:skip-covered",
            f"--cov-fail-under={COVERAGE_FLOOR}",
        ]
    return 명령 + list(파일)


PYTEST = pytest_명령(빠른=False, 파일=[], 병렬=병렬_있음, 커버리지=커버리지_있음)

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
            ".claude/hooks/output-guard.test.cjs",
        ],
    ),
]

# 싼 검사 - 실패하면 비싼 단계(pytest, node --test)로 넘어가지 않는다.
앞_단계 = ("compileall", "ruff check", "ruff format")
빠른_플래그 = "--빠른"
골든_플래그 = "--골든"
게이트_로그_폴더 = tempfile.gettempdir()
골든_로그 = os.path.join(게이트_로그_폴더, "dfzero-golden-update.log")
# 로컬에서는 출력을 요약하는 단계 - 전체는 게이트_로그_폴더에 남는다. CI(환경변수 CI)는 그대로 찍는다.
요약_단계 = ("pytest", "pytest(빠른)", "node --test")

# 작업시간 기록(임시, #239 - 지울 때 #237 목록대로): 단계마다 걸린 시간을 .claude/hooks/time-log.cjs의 세션 기록에 남긴다.
TIME_LOG = os.path.join(ROOT, ".claude", "time-log")


def 시간_기록(폴더, 단계, 초, 성공):
    """가장 최근 세션 기록에 GateStep 한 줄을 더한다. 기록이 없으면(CI) 아무것도 안 한다."""
    기록들 = glob.glob(os.path.join(폴더, "*.jsonl"))
    if not 기록들:
        return
    줄 = {
        "t": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "ev": "GateStep",
        "step": 단계,
        "sec": round(초, 1),
        "ok": 성공,
    }
    with open(max(기록들, key=os.path.getmtime), "a", encoding="utf-8") as f:
        f.write(json.dumps(줄, ensure_ascii=False) + "\n")


def 출력_요약(출력):
    """긴 테스트 출력에서 실패 줄(pytest FAILED/ERROR, node --test `not ok`), 개수 줄(`# pass`/`# fail`),
    끝 줄만 남긴다 - 통째로 찍으면 맥락에 수천 자가 쌓인다."""
    줄들 = [줄 for 줄 in 출력.splitlines() if 줄.strip()]
    핵심 = [
        줄
        for 줄 in 줄들[:-1]
        if 줄.startswith(("FAILED", "ERROR", "not ok", "# pass ", "# fail "))
    ]
    return 핵심 + 줄들[-1:]


def 요약_실행(name, cmd):
    """출력을 받아 로그 파일에 쓰고 요약만 찍는다."""
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    출력 = (result.stdout or "") + (result.stderr or "")
    로그 = os.path.join(
        게이트_로그_폴더, f"dfzero-gate-{name.split('(')[0].replace(' ', '-')}.log"
    )
    with open(로그, "w", encoding="utf-8", newline="\n") as f:
        f.write(출력)
    print("\n".join(출력_요약(출력)))
    print(f"   (전체 출력: {로그})")
    return result


def 골든_갱신():
    """서식 고침 -> UPDATE_GOLDEN=1 테스트 전체(직렬 - 병렬이면 쓰는 도중의 골든을 다른 테스트가 읽는다) -> 차이 요약.
    갱신 실행은 골든 비교 말고는 모두 단언하므로 마지막 테스트를 겸한다."""
    for cmd in (
        [sys.executable, "-m", "ruff", "format", "."],
        [sys.executable, "-m", "ruff", "check", "--fix", "."],
    ):
        result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            print("\n".join(출력_요약(result.stdout + result.stderr)))
            print(f"FAIL: {' '.join(cmd[2:])}")
            return 1
    result = subprocess.run(
        PYTEST_BASE + ["-p", "no:cacheprovider"],
        cwd=ROOT,
        env=dict(os.environ, UPDATE_GOLDEN="1"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    출력 = result.stdout + result.stderr
    with open(골든_로그, "w", encoding="utf-8", newline="\n") as f:
        f.write(출력)
    print("\n".join(출력_요약(출력)))
    print(f"   (전체 출력: {골든_로그})")
    if result.returncode != 0:
        print("FAIL: 골든 갱신 실행")
        return 1
    return subprocess.run([sys.executable, "tools/golden_diff.py"], cwd=ROOT).returncode


def main(argv=None):
    # Windows에서 리디렉션된 출력은 cp1252라 한글 print가 죽는다(#200) - 콘솔 인코딩과 상관없이 UTF-8로.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    인자 = sys.argv[1:] if argv is None else argv
    if 골든_플래그 in 인자:
        return 골든_갱신()
    빠른 = 빠른_플래그 in 인자
    테스트_파일 = [a for a in 인자 if a != 빠른_플래그]
    if 테스트_파일 and not 빠른:
        print(
            f"테스트 파일은 {빠른_플래그}와 같이 준다 - 전체 게이트는 커버리지 하한 때문에 전부 돌아야 한다"
        )
        return 2
    failed = []
    for name, cmd in STEPS:
        if failed and name not in 앞_단계:
            print(f"== {name}: 앞 단계 실패({', '.join(failed)}), 건너뜀")
            continue
        if name == "pytest" and not os.path.isdir(os.path.join(ROOT, "tests")):
            print(f"== {name}: tests/ 없음, 건너뜀")
            continue
        if name == "pytest" and 빠른:
            name, cmd = (
                "pytest(빠른)",
                pytest_명령(True, 테스트_파일, 병렬_있음, 커버리지_있음),
            )
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
        if name == "pytest" and "-n" not in cmd:
            print("   (pytest-xdist 없음 - 직렬로 돈다: pip install pytest-xdist)")
        시작 = time.monotonic()
        if name in 요약_단계 and not os.environ.get("CI"):
            result = 요약_실행(name, cmd)
        else:
            result = subprocess.run(cmd, cwd=ROOT)
        초 = time.monotonic() - 시작
        print(f"   ({초:.1f}초)")
        시간_기록(TIME_LOG, name, 초, result.returncode == 0)
        if result.returncode != 0:
            failed.append(name)
    print()
    if failed:
        print("FAIL: " + ", ".join(failed))
        return 1
    if 빠른:
        print(
            "PASS: 빠른 확인 통과 - 커버리지 하한은 CI(check)가 판정한다(전체: python tools/check.py)"
        )
        return 0
    print("PASS: 모든 검사 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
