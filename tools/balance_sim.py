"""직업 밸런스 모의전투 - 시험 직업의 "승률패턴"을 찾고 판을 더할수록 다듬는다.

    python tools/balance_sim.py 검귀 --처음부터   # 다섯 단계 1000판 + 최종 200판
    python tools/balance_sim.py 검귀 --판 200     # 저장된 승률패턴에서 이어서(승률·랜덤·변형 1/3씩)
    python tools/balance_sim.py 검귀 --비교       # 같은 200판으로 일반공격만 / 스킬 하나씩 / 승률패턴
    python tools/balance_sim.py 전체 --딜 --판 200  # 24종 전원 자동전투 판당 딜(인형은 따로, 기록하지 않음)
    python tools/balance_sim.py 전체 --지표 --판 200  # 딜지분·승률(버퍼를 끈 판까지, #617). --전체지표면 다섯 가지
    python tools/balance_sim.py 크루세이더 --기대      # 전투 없이 수치만 본 기대값(일반공격·피격·버프별)
    python tools/balance_sim.py 전체 --분석 --묶음 10 --판 30  # 분석용 전투(#690, tools/balance_analysis.py)

패턴 = 시험 직업의 차례 1~슬롯수마다 고를 행동(일반공격 또는 보유 스킬). 차례마다 슬롯의 스킬을 먼저
쓰고, 그 스킬이 일반행동을 쓰지 않았으면(보조행동·소모 없음) 같은 차례에 다음 슬롯도 쓴다(최대 3칸 -
원귀->합격, 류심->파생기). 못 쓰면 "일반공격"으로 기록한다. 반응스킬(조건이 맞으면 저절로)과
연계스킬(앞 스킬에 이어 저절로)은 직접 쓸 수 없어 행동 후보에서 빼고, 실제로 나간 횟수만 전투 로그에서 센다(#593). 남은 행동은 일반공격이고, 다른 파티원은
자동전투 "전력전투"다. 슬롯마다 실제로 나간 행동의 (승, 판)을 쌓아 승률패턴을 고른다.

기록은 docs/balance/patterns.json에 직업마다 쌓인다. 기록마다 "규칙지문"(game/data와 game/system의
내용 해시)이 있고, 지금 규칙과 같은 기록만 이어 쓴다. 규칙이 바뀌면 이전 기록은 남되 참고하지 않는다
(2026-10-21 사용자 결정). 결과 보고서는 docs/balance/*.md.
"""

import argparse
import collections
import copy
import datetime
import hashlib
import json
import os
import random
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
기록경로 = os.path.join(ROOT, "docs", "balance", "patterns.json")
분석보고서경로 = os.path.join(ROOT, "docs", "balance", "분석.md")

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
    # 무기(11-02 사용자 지정, #520): 파티 전원이 전직 추천 종류(tests/scenario.py 전직_추천무기)의 언커먼
    # 무기를 들고, 레벨 2 무기 마스터리도 측정 조건과 같게 고른다(scenario.측정_파티_준비).
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


def 자동스킬_종류(정의):
    """저절로 나가는 스킬이면 "반응"(반응스킬) 또는 "연계"(연계스킬), 직접 쓰는 스킬이면 None."""
    if not 정의:
        return None
    if 정의.get("분류") == "반응스킬":
        return "반응"
    if "연계스킬" in (정의.get("타입") or []):
        return "연계"
    return None


def 자동_횟수(로그, 이름, 반응스킬, 연계스킬):
    """전투 로그에서 시험자(`이름`)의 반응스킬·연계스킬이 나간 횟수. 반응은 "반응" 로그 한 줄이 한 번이고,
    연계는 그 스킬의 "타격" 로그다(귀참드라이브는 "귀참 - 귀참드라이브"로 남는다)."""
    횟수 = collections.Counter()
    for 항목 in 로그:
        if 항목.get("공격자") != 이름:
            continue
        if 항목.get("종류") == "반응" and 항목.get("반응") in 반응스킬:
            횟수[항목["반응"]] += 1
        elif 항목.get("종류") == "타격":
            스킬 = str(항목.get("스킬") or "")
            for 연계 in 연계스킬:
                if 스킬 == 연계 or 스킬.endswith(" - " + 연계):
                    횟수[연계] += 1
    return dict(횟수)


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


def 게임():
    """(gameflow, scenario, support, rng) - tests/의 결정적 성장 도우미와 스킬 대상 고르기를 쓴다
    (tests/support.py, tests/scenario.py). game을 부르기 전에 sys.path를 맞춘다."""
    for 경로 in (ROOT, os.path.join(ROOT, "tests")):
        if 경로 not in sys.path:
            sys.path.insert(0, 경로)
    import gameflow as gf
    import scenario
    import support
    from game.system import rng

    return gf, scenario, support, rng


def 파티_상태(구성):
    """[(1차 직업, 전직), ...] -> 측정 조건(파티레벨, 전직 추천 무기, 무기 마스터리)으로 키운 새 게임 상태.
    구성 순서가 파티원 순서다. 시작 전에 난수를 1로 맞춰 같은 구성이면 언제나 같은 상태다."""
    gf, scenario, support, rng = 게임()
    rng.시드(1)
    상태 = support.새게임([("", 직업) for 직업, _ in 구성])
    for c, (_, 전직) in zip(상태["파티"]["파티원"], 구성):
        종류 = scenario.전직_추천무기[전직]
        시작종류 = gf.캐릭터_장착아이템(상태, c, "무기")["타입"]
        support.성장(
            상태,
            c,
            조건["파티레벨"],
            전직=전직,
            스킬습득=True,
            무기숙련=[f"{종류} 마스터리", f"{시작종류} 마스터리"],
        )
        무기 = scenario.측정_무기(상태, 종류)
        # 같은 종류를 드는 파티원이 있어도(레인저·패러메딕 리볼버) 한 자루씩
        상태["소지품"]["장비"][무기] = 상태["소지품"]["장비"].get(무기, 0) + 1
        gf.장비_교체(상태, c, "무기", 무기)
    return 상태


class 측정:
    """시험 직업 하나의 전투 환경. 파티 구성마다 캐릭터를 한 번 키워 두고 판마다 쉬고 싸운다."""

    def __init__(self, 직업):
        gf, self.scenario, self.support, self.rng = 게임()
        self.gf = gf
        self.직업 = 직업
        # 시험자는 전직의 1차 직업으로 만든다(배틀메이지면 마법사)
        self.기본직업 = next(
            j for j, 전직들 in gf.전직_레지스트리.items() if 직업 in 전직들
        )
        대신 = tuple(조건["대신할전직"])
        # 시험 직업과 같은 전직은 기본 파티에서도 대신할 전직으로 바꾼다(레인저 시험에 레인저 둘이 되지 않게)
        self.기본파티 = [대신 if 전 == 직업 else (j, 전) for j, 전 in 조건["기본파티"]]
        self.다른파티 = [
            [대신 if 전 == 직업 else (j, 전) for j, 전 in 파티]
            for 파티 in 조건["다른파티"]
        ]
        self.상태모음 = {}
        gf.자동전투_방식_설정("전력전투")
        상태 = self._상태(self.기본파티)
        시험자 = 상태["파티"]["파티원"][0]
        정의모음 = gf.스킬데이터모음_생성()
        종류 = {s: 자동스킬_종류(정의모음.get(s)) for s in 시험자["보유스킬"]}
        self.행동목록 = ["일반공격"] + [s for s, k in 종류.items() if k is None]
        self.반응스킬 = [s for s, k in 종류.items() if k == "반응"]
        self.연계스킬 = [s for s, k in 종류.items() if k == "연계"]

    def _상태(self, 나머지):
        키 = tuple(나머지)
        if 키 not in self.상태모음:
            self.상태모음[키] = 파티_상태([(self.기본직업, self.직업)] + list(나머지))
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
        실제.update(
            자동_횟수(
                상태["전투상태"]["로그"],
                시험자["캐릭터명"],
                self.반응스킬,
                self.연계스킬,
            )
        )
        gf.전투_결과_정리(상태)
        return 승, 실제, 의도

    def 자동전투(self, 시드, 끌사람=None):
        """기본 파티 전원 자동전투("전력전투") 한 판 -> (승리, {이름: 적에게 넣은 피해}, 인형 이름들).
        피해는 core.피해_집계(넘친 피해 빼고 흡수된 피해 포함, 인형은 따로, 지속 피해는 건 사람).
        끌사람(캐릭터명)을 주면 그가 남에게 건 버프·적에게 건 디버프의 효과만 끈 판이다(#617)."""
        r = self.자동전투_결과(시드, 끌사람)
        return r["승"], r["딜"], r["인형"]

    def 자동전투_결과(self, 시드, 끌사람=None):
        """자동전투 한 판 -> {"승", "딜": {이름: 적에게 넣은 피해}, "받음": {이름: 받은 피해}, "인형": 이름들}.
        판마다 같은 파티 상태(복사본)에서 시작한다 - 끈 판과 본 판이 같은 시드면 같은 구성으로 시작한다."""
        from game.system.combat import contribution, core

        gf = self.gf
        원본 = self._상태(self.기본파티)
        gf.휴식(원본)
        상태 = copy.deepcopy(원본)
        self.rng.시드(시드)
        rr = random.Random(시드)
        몹 = [rr.choice(조건["몬스터"]) for _ in range(rr.randint(*조건["마리"]))]
        gf.전투_시작(상태, 몹, 레벨=조건["몬스터레벨"], 차수=조건["몬스터차수"])
        전투상태 = 상태["전투상태"]
        if 끌사람 is not None:
            전투상태["기여끄기"] = next(
                p["id"]
                for p in 전투상태["참가자"]
                if p["진영"] == "아군" and p["원본"].get("캐릭터명") == 끌사람
            )
        self.support.반응_처리(상태)
        for _ in range(판당_최대턴):
            if gf.전투_종료됨(상태):
                break
            p = gf.현재_턴_참가자(상태)
            if p["진영"] == "아군" and p["생존"]:
                gf.자동전투_한_턴(상태)
            else:
                gf.턴_넘기기(상태)
        return {
            "승": 전투상태["종료"] == "아군승리",
            "딜": core.피해_집계(전투상태),
            "받음": contribution.받은피해_집계(전투상태),
            "인형": {p["이름"] for p in 전투상태["참가자"] if p.get("인형")},
        }

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


def 비교_후보패턴(승률패턴, 결과):
    """같은 판 비교에서 가장 많이 이긴 단일 스킬로 만든 패턴 둘 - 그 스킬 하나만, 그 스킬 + 승률패턴의 차례 2~(#593).
    학습은 슬롯마다 따로 보므로 스킬 하나보다 못한 패턴이 나올 수 있다."""
    단일 = [(v["승"], k) for k, v in 결과.items() if k.startswith("첫차례 ")]
    if not 단일:
        return {}
    스킬 = max(단일, key=lambda x: x[0])[1][len("첫차례 ") :]
    return {
        "최고 단일 스킬": [스킬] + ["일반공격"] * (슬롯수 - 1),
        "최고 단일 스킬 + 승률패턴": [스킬] + list(승률패턴[1:슬롯수]),
    }


def 채택_후보(결과):
    """승률패턴·최고 단일 스킬·둘을 섞은 것 중 같은 판 승수가 가장 많은 이름. 같으면 앞의 것(학습한 승률패턴)."""
    이름들 = ["승률패턴", "최고 단일 스킬", "최고 단일 스킬 + 승률패턴"]
    return max((n for n in 이름들 if n in 결과), key=lambda n: 결과[n]["승"])


def 비교(m, 기록, 판=200):
    """같은 판으로 일반공격만 / 첫 차례에 스킬 하나 / 승률패턴을 맞대고, 최고 단일 스킬로 만든 패턴 둘도
    돌려 가장 많이 이긴 것을 승률패턴으로 삼는다(#593 - 이어서 실행은 그 패턴에서 시작한다)."""
    후보 = {"일반공격만": ["일반공격"] * 슬롯수}
    for 스킬 in m.행동목록[1:]:
        후보["첫차례 " + 스킬] = [스킬] + ["일반공격"] * (슬롯수 - 1)
    후보["승률패턴"] = 기록["승률패턴"]
    결과 = {}
    for 이름, 패턴 in 후보.items():
        승수, 횟수 = _같은판(m, 패턴, 판)
        결과[이름] = {"승": 승수, "행동횟수": 횟수}
        print(f"  {승수:4d}  {이름}")
    for 이름, 패턴 in 비교_후보패턴(기록["승률패턴"], 결과).items():
        승수, 횟수 = _같은판(m, 패턴, 판)
        결과[이름] = {"승": 승수, "행동횟수": 횟수, "패턴": 패턴}
        print(f"  {승수:4d}  {이름}")
    결과["승률패턴"]["패턴"] = 기록["승률패턴"]
    채택 = 채택_후보(결과)
    기록["승률패턴"] = 결과[채택]["패턴"]
    print(f"  채택: {채택} - " + " > ".join(기록["승률패턴"]))
    기록["비교"] = {"날짜": _오늘(), "판": 판, "결과": 결과, "채택": 채택}


def 측정_전직표():
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import gameflow

    return gameflow.전직_레지스트리


def 판당_딜(m, 판=200):
    """시드 0..판-1로 전원 자동전투 -> {"승": 승수, "시험자": 판당 딜, "인형": {이름: 판당 딜}} - 시험자는 1번
    파티원, 인형은 그 판에 나온 인형마다 따로(누가 불렀든, 2026-11-09 사용자 결정)."""
    시험자 = m._상태(m.기본파티)["파티"]["파티원"][0]["캐릭터명"]
    승수, 딜, 인형딜 = 0, 0, collections.Counter()
    for 시드 in range(판):
        승, 집계, 인형 = m.자동전투(시드)
        승수 += 승
        딜 += 집계.get(시험자, 0)
        for 이름 in 인형:
            인형딜[이름] += 집계.get(이름, 0)
    return {
        "승": 승수,
        "시험자": round(딜 / 판, 1),
        "인형": {이름: round(v / 판, 1) for 이름, v in 인형딜.items()},
    }


def 판당_지표(m, 판=200):
    """시드 0..판-1로 전원 자동전투 본 판과, 파티원마다 그를 끈 판(#617)을 돌려 다섯 지표를 낸다 -> {"승", "판",
    "시험자", "지표": {이름: {"딜지분", "딜기여도", "탱지분", "탱기여도"}(백분율)}, "딜", "받음"(본 판 판당)}.
    판수는 (1 + 파티원 수)배로 돈다."""
    from game.system.combat import contribution

    파티 = [c["캐릭터명"] for c in m._상태(m.기본파티)["파티"]["파티원"]]
    본 = {"딜": collections.Counter(), "받음": collections.Counter()}
    끈 = {
        이름: {"딜": collections.Counter(), "받음": collections.Counter()}
        for 이름 in 파티
    }
    승수 = 0
    for 시드 in range(판):
        r = m.자동전투_결과(시드)
        승수 += r["승"]
        for 칸 in ("딜", "받음"):
            본[칸].update(r[칸])
        for 이름 in 파티:
            r = m.자동전투_결과(시드, 끌사람=이름)
            for 칸 in ("딜", "받음"):
                끈[이름][칸].update(r[칸])

    def 평균(c):
        return {k: v / 판 for k, v in c.items()}

    본 = {칸: 평균(c) for 칸, c in 본.items()}
    끈 = {이름: {칸: 평균(c) for 칸, c in d.items()} for 이름, d in 끈.items()}
    return {
        "승": 승수,
        "판": 판,
        "시험자": 파티[0],
        "지표": contribution.지표_계산(본, 끈),
        "딜": 본["딜"],
        "받음": 본["받음"],
    }


def _목록(값):
    return [값] if isinstance(값, str) else list(값 or [])


def 기대_표(직업):
    """수치만 보는 기대값(전투를 돌리지 않는다, #617) - 측정 파티(레벨 9)와 측정 몬스터 11종 각 한 마리로 전투만
    열어 두고 계산한다. {"일반공격": 시험자 일반공격 1회 기대 피해(몬스터 평균), "피격": 몬스터 공격 1회에 시험자가
    받을 기대 피해, "버프": {스킬: {"딜기여", "탱기여"}}} - 버프·디버프 스킬 한 번이 다른 아군의 일반공격 기대
    피해를 올리고 받을 피해를 줄이는 양 x 지속턴(받는 사람·걸린 적 수만큼, 단일 대상이면 한 명 평균)."""
    m = 측정(직업)  # sys.path를 맞춘다 - game을 부르기 전에
    from game.system.combat import contribution
    from game.system.skill import skill_grant

    gf = m.gf
    상태 = copy.deepcopy(m._상태(m.기본파티))
    gf.휴식(상태)
    m.rng.시드(0)
    gf.전투_시작(
        상태, list(조건["몬스터"]), 레벨=조건["몬스터레벨"], 차수=조건["몬스터차수"]
    )
    시험자원본 = 상태["파티"]["파티원"][0]
    정의모음 = 상태["스킬데이터모음"]

    def 편(전투상태):
        참가자 = 전투상태["참가자"]
        아군 = [p for p in 참가자 if p["진영"] == "아군"]
        나 = next(
            p
            for p in 아군
            if p["원본"] is 시험자원본
            or p["원본"].get("캐릭터명") == 시험자원본["캐릭터명"]
        )
        return (
            나,
            [p for p in 아군 if p is not 나],
            [p for p in 참가자 if p["진영"] == "적"],
        )

    def 딜(전투상태, p, 적):
        return sum(contribution.일반공격_기대피해(전투상태, p, e) for e in 적) / len(적)

    def 맞음(전투상태, p, 적):
        return sum(contribution.몬스터_기대피해(전투상태, e, p) for e in 적) / len(적)

    전투상태 = 상태["전투상태"]
    나, 남, 적 = 편(전투상태)
    표 = {"일반공격": 딜(전투상태, 나, 적), "피격": 맞음(전투상태, 나, 적), "버프": {}}
    for 스킬 in 시험자원본.get("보유스킬") or []:
        데이터 = 정의모음.get(스킬) or {}
        효과들 = [
            e
            for e in _목록(데이터.get("효과")) + _목록(데이터.get("조건부효과"))
            if isinstance(e, dict) and e.get("종류") in ("자동디버프", "내성디버프")
        ]
        버프 = 데이터.get("분류") == "버프스킬" and 데이터.get("타겟") != "자신"
        if not (버프 or 효과들):
            continue
        사본 = copy.deepcopy(전투상태)
        나2, 남2, 적2 = 편(사본)
        전딜 = [딜(사본, p, 적2) for p in 남2]
        전맞음 = [맞음(사본, p, 적2) for p in 남2]
        if 버프:
            받는이 = 남2
            for p in 받는이:
                for 이름 in _목록(데이터.get("버프획득")):
                    skill_grant.이름있는효과_부여(사본, p, 이름, 시전자=나2)
            지속 = 데이터.get("지속턴") or 1
            단일 = str(데이터.get("타겟")).endswith("단일")
        else:
            for e in 적2:
                for 효과 in 효과들:
                    skill_grant.이름있는효과_부여(사본, e, 효과["이름"], 시전자=나2)
            지속 = max((e.get("지속턴") or 1) for e in 효과들)
            단일 = not str(데이터.get("타겟", "")).startswith("적전체")
        후딜 = [딜(사본, p, 적2) for p in 남2]
        후맞음 = [맞음(사본, p, 적2) for p in 남2]
        딜차 = sum(b - a for a, b in zip(전딜, 후딜))
        탱차 = sum(a - b for a, b in zip(전맞음, 후맞음))
        if 단일:  # 한 명(한 마리)에게만 - 받는 사람 평균
            딜차, 탱차 = 딜차 / max(len(남2), 1), 탱차 / max(len(남2), 1)
            if not 버프:
                딜차, 탱차 = 딜차 / len(적2), 탱차 / len(적2)
        if 딜차 or 탱차:
            표["버프"][스킬] = {
                "딜기여": round(딜차 * 지속, 2),
                "탱기여": round(탱차 * 지속, 2),
            }
    표["일반공격"], 표["피격"] = round(표["일반공격"], 2), round(표["피격"], 2)
    return 표


def _분석_명령(a):
    """--분석: 고른 무작위 파티를 뽑아 분석 전투를 돌리고 보고서를 쓴다(#690)."""
    if a.직업 != "전체":
        print("--분석은 전직을 고르게 섞으므로 직업 자리에 '전체'를 쓴다")
        return 2
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    from tools import balance_analysis as ba

    판 = a.판 or 30
    파티들 = ba.고른_파티들(측정_전직표(), a.묶음, random.Random(a.분석시드))
    print(f"분석 전투: 파티 {len(파티들)}개 x {판}판, 일꾼 {a.일꾼}", flush=True)
    판들 = ba.분석_실행(파티들, 판, a.섞기, a.일꾼, 시작시드=a.분석시드 * 100000)
    요약 = ba.집계(판들)
    정보 = {
        "판": 판,
        "섞기": a.섞기,
        "파티": len(파티들),
        "규칙지문": 규칙지문(),
        "커밋": _커밋(),
    }
    with open(a.보고서, "w", encoding="utf-8", newline="\n") as f:
        f.write(ba.보고서(요약, 정보))
    print(f"판 {요약['판']}, 승률 {요약['승률'] * 100:.1f}% - 보고서: {a.보고서}")
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):  # cp1252 콘솔에서도 한글(#200)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="직업 밸런스 모의전투(승률패턴)")
    p.add_argument("직업", help="시험할 전직 이름(예: 검귀)")
    p.add_argument("--처음부터", action="store_true", help="다섯 단계를 새로 돌린다")
    p.add_argument(
        "--판",
        type=int,
        default=None,
        help="단계(또는 이어서)마다 판 수(기본 200), --분석이면 파티마다 판 수(기본 30)",
    )
    p.add_argument("--비교", action="store_true", help="같은 판으로 스킬 하나씩 맞대기")
    p.add_argument(
        "--기록", default=기록경로, help="기록 파일(기본 docs/balance/patterns.json)"
    )
    p.add_argument(
        "--딜",
        action="store_true",
        help="전원 자동전투 --판 판의 판당 딜만 잰다(기록하지 않는다). 직업 자리에 '전체'면 24종",
    )
    p.add_argument(
        "--지표",
        action="store_true",
        help="버퍼를 끈 판까지 돌려 딜지분·승률을 잰다(#617, 판수 x5). 직업 자리에 '전체'면 24종",
    )
    p.add_argument(
        "--전체지표",
        action="store_true",
        help="--지표와 함께: 딜기여도·탱지분·탱기여도까지 보인다",
    )
    p.add_argument(
        "--기대",
        action="store_true",
        help="전투 없이 수치만으로 일반공격·피격·버프별 기대값(#617)",
    )
    p.add_argument(
        "--분석",
        action="store_true",
        help="분석용 전투(#690): 고른 무작위 4인 파티가 무작위 행동으로 싸운다. 직업 자리는 '전체'",
    )
    p.add_argument(
        "--묶음", type=int, default=10, help="--분석: 묶음 수(묶음마다 파티 6개)"
    )
    p.add_argument(
        "--섞기", type=float, default=0.3, help="--분석: 아군 차례가 전력전투일 확률"
    )
    p.add_argument(
        "--분석시드", type=int, default=0, help="--분석: 파티 뽑기와 판 시드"
    )
    p.add_argument(
        "--일꾼", type=int, default=os.cpu_count() or 1, help="--분석: 프로세스 수"
    )
    p.add_argument(
        "--보고서",
        default=분석보고서경로,
        help="--분석: 보고서(기본 docs/balance/분석.md)",
    )
    a = p.parse_args(argv)
    if a.분석:
        return _분석_명령(a)
    if a.판 is None:
        a.판 = 200
    직업들 = (
        [j for 전직들 in 측정_전직표().values() for j in 전직들]
        if a.직업 == "전체"
        else [a.직업]
    )
    if a.지표:
        for 직업 in 직업들:
            r = 판당_지표(측정(직업), a.판)
            나 = r["지표"][r["시험자"]]
            줄 = f"{직업}\t딜지분 {나['딜지분']:.1f}%\t승 {r['승']}/{r['판']}"
            if a.전체지표:
                줄 += (
                    f"\t딜기여도 {나['딜기여도']:.1f}%\t탱지분 {나['탱지분']:.1f}%"
                    f"\t탱기여도 {나['탱기여도']:.1f}%"
                )
            print(줄, flush=True)
        return 0
    if a.기대:
        for 직업 in 직업들:
            print(직업, json.dumps(기대_표(직업), ensure_ascii=False), flush=True)
        return 0
    if a.딜:
        for 직업 in 직업들:
            r = 판당_딜(측정(직업), a.판)
            인형 = "".join(f"  인형 {n} {v}" for n, v in r["인형"].items())
            print(f"{직업}\t판당 {r['시험자']}\t승 {r['승']}/{a.판}{인형}", flush=True)
        return 0

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
