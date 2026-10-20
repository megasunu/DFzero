"""바뀐 골든을 짧게 요약한다 - 큰 diff를 읽지 않고 "의도한 만큼만 바뀌었나"를 본다.

    python tools/golden_diff.py            # 작업 트리의 tests/golden/ 을 HEAD와 비교
    python tools/golden_diff.py main-branch

파일마다 한 줄: 바뀐 곳 수, 많이 바뀐 키, 전투 로그가 몇 번째 항목부터 갈렸는지.
로그가 앞에서부터 다 갈렸으면 굴림 순서가 밀린 것이고, 끝 근처만 갈렸으면 그 지점의 변경이다.
"""

import glob
import json
import os
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = "tests/golden"
_없음 = object()


def _훑기(옛, 새, 경로, 키, 결과):
    """옛/새를 같이 내려가며 다른 잎을 (경로, 키)로 모으고, "로그" 목록의 첫 갈림을 적는다."""
    if isinstance(옛, dict) and isinstance(새, dict):
        for k in sorted(set(옛) | set(새)):
            _훑기(
                옛.get(k, _없음),
                새.get(k, _없음),
                f"{경로}.{k}" if 경로 else k,
                k,
                결과,
            )
    elif isinstance(옛, list) and isinstance(새, list):
        for i in range(max(len(옛), len(새))):
            _훑기(
                옛[i] if i < len(옛) else _없음,
                새[i] if i < len(새) else _없음,
                f"{경로}[{i}]",
                키,
                결과,
            )
        if 키 == "로그" and 옛 != 새:
            첫 = next(
                i
                for i in range(max(len(옛), len(새)))
                if i >= min(len(옛), len(새)) or 옛[i] != 새[i]
            )
            결과["로그_갈림"][경로] = (첫, len(옛), len(새))
    elif 옛 != 새 or type(옛) is not type(새):
        결과["곳"].append((경로, 키))


def 차이_요약(옛, 새):
    결과 = {"곳": [], "로그_갈림": {}}
    _훑기(옛, 새, "", "", 결과)
    return {
        "바뀐_곳": len(결과["곳"]),
        "키별": dict(Counter(키 for _, 키 in 결과["곳"])),
        "첫_갈림": 결과["곳"][0][0] if 결과["곳"] else None,
        "로그_갈림": 결과["로그_갈림"],
    }


def _한_줄(이름, 요약):
    키들 = ", ".join(f"{k} {n}" for k, n in Counter(요약["키별"]).most_common(5))
    줄 = f"{이름}: {요약['바뀐_곳']}곳 ({키들})"
    갈림 = [
        f"{경로} {첫 + 1}번째 항목부터(옛 {옛n}개, 새 {새n}개)"
        for 경로, (첫, 옛n, 새n) in list(요약["로그_갈림"].items())[:3]
    ]
    if 갈림:
        줄 += " / 로그 갈림: " + "; ".join(갈림)
    return 줄


def 요약_줄들(폴더, 옛_읽기, 옛_이름들):
    """폴더의 골든과 옛_읽기(이름)->값|None 을 비교해 바뀐 파일만 한 줄씩, 끝에 합계 한 줄."""
    지금 = {
        os.path.splitext(os.path.basename(p))[0]: p
        for p in glob.glob(os.path.join(폴더, "*.json"))
    }
    변경, 새_파일, 지워짐, 합계 = [], [], [], 0
    for 이름 in sorted(set(지금) | set(옛_이름들)):
        옛 = 옛_읽기(이름) if 이름 in 옛_이름들 else None
        if 이름 not in 지금:
            지워짐.append(f"{이름}: 지워짐")
            continue
        if 옛 is None:
            새_파일.append(f"{이름}: 새 파일")
            continue
        with open(지금[이름], encoding="utf-8") as f:
            요약 = 차이_요약(옛, json.load(f))
        if 요약["바뀐_곳"]:
            합계 += 요약["바뀐_곳"]
            변경.append(_한_줄(이름, 요약))
    개수 = len(변경) + len(새_파일) + len(지워짐)
    끝 = f"골든 {개수}개 바뀜(변경 {len(변경)}, 새 파일 {len(새_파일)}, 지워짐 {len(지워짐)}), 바뀐 곳 {합계}"
    return 변경 + 새_파일 + 지워짐 + [끝]


def _git(*인자):
    return subprocess.run(
        ["git", *인자], cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):  # Windows 콘솔에서도 한글(#200)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    인자 = sys.argv[1:] if argv is None else argv
    기준 = 인자[0] if 인자 else "HEAD"
    # -z: 한글 경로를 따옴표·8진수로 바꾸지 않고 그대로, NUL로 나눠 찍는다
    목록 = _git("ls-tree", "-z", "--name-only", 기준, f"{GOLDEN}/")
    if 목록.returncode != 0:
        print(f"기준 {기준!r}을 읽지 못했다: {목록.stderr.strip()}")
        return 2
    옛_이름들 = [
        os.path.splitext(os.path.basename(p))[0]
        for p in 목록.stdout.split("\0")
        if p.endswith(".json")
    ]

    def 옛_읽기(이름):
        결과 = _git("show", f"{기준}:{GOLDEN}/{이름}.json")
        return json.loads(결과.stdout) if 결과.returncode == 0 else None

    for 줄 in 요약_줄들(os.path.join(ROOT, GOLDEN), 옛_읽기, 옛_이름들):
        print(줄)
    return 0


if __name__ == "__main__":
    sys.exit(main())
