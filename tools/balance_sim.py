"""직업 밸런스 모의전투 - 시험 직업의 "승률패턴"을 찾고 판을 더할수록 다듬는다.

    python tools/balance_sim.py 검귀 --처음부터   # 다섯 단계 1000판 + 최종 200판
    python tools/balance_sim.py 검귀 --판 200     # 저장된 승률패턴에서 이어서(승률·랜덤·변형 1/3씩)
    python tools/balance_sim.py 검귀 --비교       # 같은 200판으로 일반공격만 / 스킬 하나씩 / 승률패턴

패턴 = 시험 직업의 차례 1~슬롯수마다 고를 행동(일반공격 또는 보유 스킬). 차례마다 슬롯의 스킬을 먼저
쓰고, 그 스킬이 일반행동을 쓰지 않았으면(보조행동·소모 없음) 같은 차례에 다음 슬롯도 쓴다(최대 3칸 -
원귀->합격, 류심->파생기). 못 쓰면 "일반공격"으로 기록한다. 남은 행동은 일반공격이고, 다른 파티원은
자동전투 "전력전투"다. 슬롯마다 실제로 나간 행동의 (승, 판)을 쌓아 승률패턴을 고른다.

기록은 docs/balance/patterns.json에 직업마다 쌓인다. 기록마다 "규칙지문"(game/data와 game/system의
내용 해시)이 있고, 지금 규칙과 같은 기록만 이어 쓴다. 규칙이 바뀌면 이전 기록은 남되 참고하지 않는다
(2026-10-21 사용자 결정). 결과 보고서는 docs/balance/*.md.
"""

import argparse
import collections
import datetime
import hashlib
import json
import os
import random
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
기록경로 = os.path.join(ROOT, "docs", "balance", "patterns.json")

슬롯수 = 10
판당_최대턴 = 400
# 측정 조건 - 무작위 패턴의 승률이 50% 안팎이 되게 맞춘 값(2026-10-21)
조건 = {
    "파티레벨": 9,
    "몬스터레벨": 20,
    "몬스터차수": 3,
    "마리": [4, 6],
    "몬스터": [
        "고블린",
        "고블린 투척병",
        "고블린 십장",
        "시가브",
        "힐가브",
        "루가루",
        "시로가루",
        "쿠로가루",
        "포레스트 좀비",
        "할로우 아이",
        "칼카자크",
    ],
    "기본파티": [
        ["격투가", "스트라이커"],
        ["거너", "레인저"],
        ["프리스트", "크루세이더"],
    ],
    # 단계 4와 비교에 쓰는 다른 파티 5개 - 시험 직업과 같은 전직은 소울브링어로 바꾼다
    "다른파티": [
        [["귀검사", "검귀"], ["마법사", "엘리멘탈마스터"], ["프리스트", "크루세이더"]],
        [["귀검사", "버서커"], ["격투가", "넨마스터"], ["거너", "레인저"]],
        [["귀검사", "아수라"], ["귀검사", "웨펀마스터"], ["마법사", "엘리멘탈마스터"]],
        [["격투가", "넨마스터"], ["격투가", "스트라이커"], ["프리스트", "크루세이더"]],
        [["귀검사", "웨펀마스터"], ["거너", "레인저"], ["마법사", "엘리멘탈마스터"]],
    ],
    "대신할전직": ["귀검사", "소울브링어"],
    # 전직 스킬에 필요한 무기 - 마도학자의 파우더는 빗자루를 들어야 쓴다
    "전직무기": {"검귀": "예리한 카타나", "마도학자": "낡은 빗자루"},
}


# ------------------------------------------------------------------ 패턴과 기록 (게임 없이)


def 승률패턴_계산(누적, 이전=None, 최소=5):
    """슬롯마다 (승+1)/(판+2)가 가장 높은 행동. 판이 `최소`보다 적은 행동은 후보에서 빼고,
    후보가 없는 슬롯은 이전 승률패턴의 행동(없으면 일반공격)을 그대로 둔다."""
    패턴 = []
    for k, 칸 in enumerate(누적):
        후보 = sorted(
            ((w + 1) / (n + 2), n, a) for a, (w, n) in 칸.items() if n >= 최소
        )
        if 후보:
            패턴.append(후보[-1][2])
        else:
            패턴.append(이전[k] if 이전 and k < len(이전) else "일반공격")
    return 패턴


def 랜덤패턴(행동목록, R):
    return [R.choice(행동목록) for _ in range(슬롯수)]


def 변형(패턴, 행동목록, R, 비율=0.25):
    """승률패턴에서 슬롯마다 `비율` 확률로 행동을 무작위로 바꾼다."""
    return [R.choice(행동목록) if R.random() < 비율 else a for a in 패턴]


def 누적_더하기(누적, 의도, 승):
    for k, a in enumerate(의도[: len(누적)]):
        칸 = 누적[k].setdefault(a, [0, 0])
        칸[0] += int(승)
        칸[1] += 1


def 규칙지문(루트=ROOT):
    """game/data와 game/system의 .py 내용 해시(앞 16자리) - 게임 규칙이 바뀌었는지 가린다."""
    h = hashlib.sha256()
    for 폴더 in ("game/data", "game/system"):
        for 위, 폴더들, 파일들 in os.walk(os.path.join(루트, 폴더)):
            폴더들[:] = sorted(d for d in 폴더들 if d != "__pycache__")
            for 이름 in sorted(파일들):
                if 이름.endswith(".py"):
                    경로 = os.path.join(위, 이름)
                    h.update(os.path.relpath(경로, 루트).replace(os.sep, "/").encode())
                    with open(경로, "rb") as f:
                        h.update(f.read().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


def 빈기록(직업, 지문):
    return {
        "규칙지문": 지문,
        "커밋": _커밋(),
        "만든날": _오늘(),
        "조건": 조건,
        "판수": 0,
        "승률패턴": ["일반공격"] * 슬롯수,
        "누적": [{} for _ in range(슬롯수)],
        "실행": [],
    }


def 현재기록(기록, 직업, 지문):
    """지금 규칙(지문)과 같은 기록. 없으면 None - 다른 규칙의 기록은 참고하지 않는다."""
    return next((r for r in 기록.get(직업, []) if r["규칙지문"] == 지문), None)


def 기록_넣기(기록, 직업, 새기록):
    """같은 규칙의 기록은 바꿔 끼우고, 다른 규칙의 기록은 뒤에 그대로 남긴다(최신이 맨 앞)."""
    남길것 = [r for r in 기록.get(직업, []) if r["규칙지문"] != 새기록["규칙지문"]]
    기록[직업] = [새기록] + 남길것


def 기록_읽기(경로):
    if not os.path.exists(경로):
        return {}
    with open(경로, encoding="utf-8") as f:
        return json.load(f)


def 기록_쓰기(경로, 기록):
    os.makedirs(os.path.dirname(경로), exist_ok=True)
    with open(경로, "w", encoding="utf-8", newline="\n") as f:
        json.dump(기록, f, ensure_ascii=False, indent=1)
        f.write("\n")


def _커밋():
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _오늘():
    return datetime.date.today().isoformat()


# ------------------------------------------------------------------ 전투


class 측정:
    """시험 직업 하나의 전투 환경. 파티 구성마다 캐릭터를 한 번 키워 두고 판마다 쉬고 싸운다."""

    def __init__(self, 직업):
        # tests/의 결정적 성장 도우미와 스킬 대상 고르기를 쓴다(tests/support.py, tests/scenario.py)
        for 경로 in (ROOT, os.path.join(ROOT, "tests")):
            if 경로 not in sys.path:
                sys.path.insert(0, 경로)
        import gameflow as gf
        import scenario
        import support
        from game.system import rng

        self.gf, self.scenario, self.support, self.rng = gf, scenario, support, rng
        self.직업 = 직업
        # 시험자는 전직의 1차 직업으로 만든다(배틀메이지면 마법사)
        self.기본직업 = next(
            j for j, 전직들 in gf.전직_레지스트리.items() if 직업 in 전직들
        )
        self.기본파티 = [tuple(x) for x in 조건["기본파티"]]
        대신 = tuple(조건["대신할전직"])
        self.다른파티 = [
            [대신 if 전 == 직업 else (j, 전) for j, 전 in 파티]
            for 파티 in 조건["다른파티"]
        ]
        self.상태모음 = {}
        gf.자동전투_방식_설정("전력전투")
        시험자 = self._상태(self.기본파티)["파티"]["파티원"][0]
        self.행동목록 = ["일반공격"] + list(시험자["보유스킬"])

    def _상태(self, 나머지):
        키 = tuple(나머지)
        if 키 not in self.상태모음:
            gf, support = self.gf, self.support
            self.rng.시드(1)
            상태 = support.새게임(
                [("", self.기본직업)] + [("", 직업) for 직업, _ in 나머지]
            )
            구성 = [(self.기본직업, self.직업)] + list(나머지)
            for c, (_, 전직) in zip(상태["파티"]["파티원"], 구성):
                support.성장(상태, c, 조건["파티레벨"], 전직=전직, 스킬습득=True)
                무기 = 조건["전직무기"].get(전직)
                if 무기:
                    상태["소지품"]["장비"][무기] = 1
                    gf.장비_교체(상태, c, "무기", 무기)
            self.상태모음[키] = 상태
        return self.상태모음[키]

    def 전투(self, 나머지, 패턴, 시드):
        """한 판 -> (승리, 실제 행동 횟수, 슬롯별 실제 행동)"""
        gf = self.gf
        상태 = self._상태(나머지)
        시험자 = 상태["파티"]["파티원"][0]
        gf.휴식(상태)  # 판마다 쉰다 - 판끼리 독립
        self.rng.시드(시드)
        rr = random.Random(시드)
        몹 = [rr.choice(조건["몬스터"]) for _ in range(rr.randint(*조건["마리"]))]
        gf.전투_시작(상태, 몹, 레벨=조건["몬스터레벨"], 차수=조건["몬스터차수"])
        self.support.반응_처리(상태)
        실제, 의도 = collections.Counter(), []
        for _ in range(판당_최대턴):
            if gf.전투_종료됨(상태):
                break
            p = gf.현재_턴_참가자(상태)
            if p["진영"] == "아군" and p["생존"] and p["원본"] is 시험자:
                self._시험자_차례(상태, p, 패턴, 실제, 의도)
            elif p["진영"] == "아군" and p["생존"]:
                gf.자동전투_한_턴(상태)
            else:
                gf.턴_넘기기(상태)
        승 = 상태["전투상태"]["종료"] == "아군승리"
        gf.전투_결과_정리(상태)
        return 승, 실제, 의도

    def _시험자_차례(self, 상태, p, 패턴, 실제, 의도):
        gf, 적 = self.gf, self.scenario._살아있는_적
        전투상태 = 상태["전투상태"]

        def 계속():
            return 전투상태["종료"] is None and p["생존"] and 적(상태)

        for _ in range(3):
            if not 계속():
                break
            k = len(의도)
            행동 = 패턴[k] if k < len(패턴) else "일반공격"
            한것 = "일반공격"
            if 행동 != "일반공격" and gf.스킬_사용_가능여부(상태, p, 행동)[0]:
                인수 = self.scenario._스킬_인수(상태, p, 행동)
                if 인수 is not None:
                    gf.아군_스킬사용(상태, 행동, **인수)
                    실제[행동] += 1
                    한것 = 행동
            의도.append(한것)
            if 한것 == "일반공격" or p["행동자원"].get("일반행동", 0) <= 0:
                break
        while 계속() and gf.일반공격_가능여부(상태, p):
            gf.아군_일반공격(상태, 적(상태)[0])
            실제["일반공격"] += 1
        if 전투상태["종료"] is None:
            gf.턴_넘기기(상태)


# ------------------------------------------------------------------ 실행 방식


def _단계(m, 기록, 이름, 판들, 시드):
    """판들: [(나머지, 종류, 패턴)]. 슬롯 기록을 쌓고 승률패턴을 다시 고른다."""
    종류별 = collections.defaultdict(lambda: [0, 0])
    for 나머지, 종류, 패턴 in 판들:
        승, _, 의도 = m.전투(나머지, 패턴, next(시드))
        누적_더하기(기록["누적"], 의도, 승)
        종류별[종류][0] += int(승)
        종류별[종류][1] += 1
        기록["판수"] += 1
    기록["승률패턴"] = 승률패턴_계산(기록["누적"], 기록["승률패턴"])
    실행 = {
        "이름": 이름,
        "날짜": _오늘(),
        "종류별": dict(종류별),
        "승률패턴": 기록["승률패턴"],
    }
    기록["실행"].append(실행)
    print(f"[{이름}] " + ", ".join(f"{k} {w}/{n}" for k, (w, n) in 종류별.items()))
    print("  승률패턴: " + " > ".join(기록["승률패턴"]))
    return 실행


def _셋중하나(m, 기록, R, 나머지):
    x = R.random()
    if x < 1 / 3:
        return (나머지, "승률", 기록["승률패턴"])
    if x < 2 / 3:
        return (나머지, "랜덤", 랜덤패턴(m.행동목록, R))
    return (나머지, "변형", 변형(기록["승률패턴"], m.행동목록, R))


def 처음부터(m, 기록, 판=200):
    """다섯 단계: 랜덤 -> 승률/랜덤 반반 -> 승률/랜덤/변형 -> 다른 파티 5개 -> 최종 패턴 판."""
    R = random.Random(7)
    시드 = iter(range(10000, 10**9))
    기본, 행동 = m.기본파티, m.행동목록
    _단계(
        m, 기록, "1 랜덤", [(기본, "랜덤", 랜덤패턴(행동, R)) for _ in range(판)], 시드
    )
    판들 = []
    for _ in range(판):
        반반 = (
            ("승률", 기록["승률패턴"])
            if R.random() < 0.5
            else ("랜덤", 랜덤패턴(행동, R))
        )
        판들.append((기본, *반반))
    _단계(m, 기록, "2 승률 반 랜덤 반", 판들, 시드)
    _단계(
        m,
        기록,
        "3 승률 랜덤 변형",
        [_셋중하나(m, 기록, R, 기본) for _ in range(판)],
        시드,
    )
    판들 = [_셋중하나(m, 기록, R, m.다른파티[i % 5]) for i in range(판)]
    _단계(m, 기록, "4 다른 파티 5개", 판들, 시드)
    기록["다음시드"] = next(시드)
    기록["최종"] = 최종판(m, 기록["승률패턴"], 판, R)


def 이어서(m, 기록, 판):
    """저장된 승률패턴에서 승률·랜덤·변형 1/3씩, 기본 파티 반 + 다른 파티 5개 반."""
    R = random.Random(f"{m.직업}-{기록['판수']}")
    시드 = iter(range(기록.get("다음시드", 10000), 10**9))
    판들 = [
        _셋중하나(m, 기록, R, m.기본파티 if i % 2 == 0 else m.다른파티[(i // 2) % 5])
        for i in range(판)
    ]
    _단계(m, 기록, f"이어서 {판}판", 판들, 시드)
    기록["다음시드"] = next(시드)


def _같은판(m, 패턴, 판, 시작=500000):
    """기본 파티 절반 + 다른 파티 5개로 시드 고정 판 -> (승수, 행동 횟수)"""
    승수, 횟수 = 0, collections.Counter()
    for i in range(판):
        나머지 = m.기본파티 if i < 판 // 2 else m.다른파티[i % 5]
        승, 실제, _ = m.전투(나머지, 패턴, 시작 + i)
        승수 += int(승)
        횟수 += 실제
    return 승수, dict(횟수.most_common())


def 최종판(m, 패턴, 판, R):
    승수, 횟수 = _같은판(m, 패턴, 판)
    일반, _ = _같은판(m, ["일반공격"] * 슬롯수, 판)
    print(f"[최종 {판}판] 승률패턴 {승수}승, 같은 판 일반공격만 {일반}승")
    print(f"  행동 횟수: {횟수}")
    return {"판": 판, "승": 승수, "일반공격만": 일반, "행동횟수": 횟수, "패턴": 패턴}


def 비교(m, 기록, 판=200):
    """같은 판으로 일반공격만 / 첫 차례에 스킬 하나 / 승률패턴을 맞댄다."""
    후보 = {"일반공격만": ["일반공격"] * 슬롯수}
    for 스킬 in m.행동목록[1:]:
        후보["첫차례 " + 스킬] = [스킬] + ["일반공격"] * (슬롯수 - 1)
    후보["승률패턴"] = 기록["승률패턴"]
    결과 = {}
    for 이름, 패턴 in 후보.items():
        승수, 횟수 = _같은판(m, 패턴, 판)
        결과[이름] = {"승": 승수, "행동횟수": 횟수}
        print(f"  {승수:4d}  {이름}")
    기록["비교"] = {"날짜": _오늘(), "판": 판, "결과": 결과}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):  # cp1252 콘솔에서도 한글(#200)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="직업 밸런스 모의전투(승률패턴)")
    p.add_argument("직업", help="시험할 전직 이름(예: 검귀)")
    p.add_argument("--처음부터", action="store_true", help="다섯 단계를 새로 돌린다")
    p.add_argument("--판", type=int, default=200, help="단계(또는 이어서)마다 판 수")
    p.add_argument("--비교", action="store_true", help="같은 판으로 스킬 하나씩 맞대기")
    p.add_argument(
        "--기록", default=기록경로, help="기록 파일(기본 docs/balance/patterns.json)"
    )
    a = p.parse_args(argv)

    기록 = 기록_읽기(a.기록)
    지문 = 규칙지문()
    지금 = 현재기록(기록, a.직업, 지문)
    m = 측정(a.직업)
    if a.처음부터 or 지금 is None:
        if 지금 is None and not a.처음부터:
            print(
                "지금 규칙의 기록이 없다 - 처음부터 돌린다(이전 규칙의 기록은 남기고 참고하지 않는다)"
            )
        지금 = 빈기록(a.직업, 지문)
        처음부터(m, 지금, a.판)
    elif not a.비교:
        이어서(m, 지금, a.판)
    if a.비교:
        비교(m, 지금, a.판)
    지금["커밋"] = _커밋()
    기록_넣기(기록, a.직업, 지금)
    기록_쓰기(a.기록, 기록)
    print(f"기록함: {a.기록} ({a.직업}, 누적 {지금['판수']}판)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
