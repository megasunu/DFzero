"""측정용 전투 정책 두 가지와 비교 실행(#675) - 게이트 밖에서 직접 돌린다.

- 분석용(무작위정책): 파티원 전원이 매 행동마다 합법 행동(일반공격, 쓸 수 있는 스킬, 표적) 중 무작위로 고른다.
  행동을 먼저 고르게(행동마다 같은 확률) 고른 뒤 표적을 고른다 - 스킬마다 고르게 나와야 기여를 잴 수 있다.
  쓸모없는 행동(다친 아군이 없는데 회복, 아직 켜진 버프 갱신 등 - scenario._쓸_가치가_있나)은 거르고 걸러진 수를 센다.
- 승률용(탐색정책): 몬테카를로 탐색. 후보 행동마다 전투 상태를 복사해 다른 시드로 몇 라운드 전력전투로 굴려 보고
  점수(승패 + 남은 아군 HP 비율 - 남은 적 HP 비율)의 평균이 가장 높은 행동을 고른다.

정책 난수는 게임 난수 흐름(game/system/rng.py)과 따로 둔다. 탐색은 굴려 보기 전에 게임 난수 상태를 저장하고 끝나면 되돌린다 -
굴려 볼 때는 정책 난수로 만든 다른 시드를 쓴다(실제 전투의 미래 주사위를 미리 보지 않게).

    python tools/policy_sim.py --파티 48 --판 5 --정책 전력전투 분석용 승률용 --병렬 4 --출력 결과.json
    python tools/policy_sim.py --파티 300 --판 40 --정책 전력전투 분석용 --지표
"""

import argparse
import collections
import copy
import json
import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _경로 in (ROOT, os.path.join(ROOT, "tests"), os.path.join(ROOT, "tools")):
    if _경로 not in sys.path:
        sys.path.insert(0, _경로)

import gameflow as gf  # noqa: E402
import scenario  # noqa: E402
import support  # noqa: E402
from game.system import rng  # noqa: E402
from game.system.combat import contribution, core  # noqa: E402

import balance_sim  # noqa: E402

조건 = balance_sim.조건
# 테스트에서 무작위가 지기도 하는 싸움(승률용과 차이가 보이게)
어려운_조건 = dict(조건, 몬스터레벨=22, 마리=[6, 6])
판당_최대턴 = balance_sim.판당_최대턴
# 한 차례에 이보다 많이 행동하면 행동이 줄지 않는 버그다
_차례당_최대행동 = 20
# 전투가 끝날 때까지 복사하지 않고 같이 쓰는 정의(전투 중에 바뀌지 않는다) - 복사 시간이 10분의 1로 준다
_공유_게임상태 = ("스킬데이터모음", "상점카탈로그")
_공유_전투상태 = ("특성정의", "캐릭터특성정의", "스킬정의", "몬스터정의")


# ------------------------------------------------------------------ 파티와 전투 준비


def 전직_목록():
    """[(1차 직업, 전직)] - 전직 24종."""
    return [
        (직업, 전직) for 직업, 전직들 in gf.전직_레지스트리.items() for 전직 in 전직들
    ]


def 균등_파티(개수, 시드=0):
    """전직이 고르게 들어가는 무작위 4인 파티 개수만큼. 전직 목록을 섞어 넷씩 끊기를 되풀이한다 -
    한 파티에 같은 전직이 없고, 개수가 6의 배수면 전직마다 같은 횟수로 나온다."""
    R = random.Random(시드)
    모두 = 전직_목록()
    파티들 = []
    while len(파티들) < 개수:
        섞음 = 모두[:]
        R.shuffle(섞음)
        파티들 += [tuple(섞음[i : i + 4]) for i in range(0, len(섞음) - 3, 4)]
    return 파티들[:개수]


_파티_상태 = {}


def 파티_상태(구성):
    """구성 [(1차 직업, 전직)]의 레벨 9 파티(측정 조건 - 추천 언커먼 무기·마스터리). 구성마다 한 번 만든다."""
    키 = tuple(tuple(x) for x in 구성)
    if 키 not in _파티_상태:
        rng.시드(1)
        상태 = support.새게임([("", 직업) for 직업, _ in 키])
        for c, (_, 전직) in zip(상태["파티"]["파티원"], 키):
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
            상태["소지품"]["장비"][무기] = 상태["소지품"]["장비"].get(무기, 0) + 1
            gf.장비_교체(상태, c, "무기", 무기)
        _파티_상태[키] = 상태
    return _파티_상태[키]


def 몬스터(시드, 조건=조건):
    rr = random.Random(시드)
    return [rr.choice(조건["몬스터"]) for _ in range(rr.randint(*조건["마리"]))]


def 전투_준비(구성, 시드, 조건=조건, 끌사람=None):
    """쉰 파티의 복사본으로 시드의 전투를 시작한 상태. 끌사람(캐릭터명)이면 그의 버프·디버프를 끈 판(#617)."""
    gf.자동전투_방식_설정("전력전투")
    원본 = 파티_상태(구성)
    gf.휴식(원본)
    상태 = copy.deepcopy(원본)
    rng.시드(시드)
    gf.전투_시작(
        상태, 몬스터(시드, 조건), 레벨=조건["몬스터레벨"], 차수=조건["몬스터차수"]
    )
    if 끌사람 is not None:
        상태["전투상태"]["기여끄기"] = next(
            p["id"]
            for p in 상태["전투상태"]["참가자"]
            if p["진영"] == "아군" and p["원본"].get("캐릭터명") == 끌사람
        )
    support.반응_처리(상태)
    return 상태


def 상태_복사(상태):
    """전투 중 상태의 복사본 - 바뀌지 않는 정의는 같이 쓴다."""
    전투 = 상태["전투상태"]
    memo = {id(상태[k]): 상태[k] for k in _공유_게임상태 if k in 상태}
    memo.update({id(전투[k]): 전투[k] for k in _공유_전투상태 if k in 전투})
    return copy.deepcopy(상태, memo)


def 참가자_찾기(상태, 참가자id):
    return next(p for p in 상태["전투상태"]["참가자"] if p["id"] == 참가자id)


# ------------------------------------------------------------------ 후보 행동


def _표적들(상태, 이름=None):
    """행동이 노릴 수 있는 적(과 감옥)의 id - HP 낮은 순. 이름이 스킬이면 그 스킬로 지정할 수 없는 적은 뺀다."""
    적들 = scenario._살아있는_적(상태)
    감옥 = [p for p in gf.공격대상_목록(상태) if p["진영"] == "감옥"]
    if 이름 is not None:
        데이터 = 상태["스킬데이터모음"][이름]
        적들 = [e for e in 적들 if not gf.스킬_지정불가인가(상태, 데이터, e)]
        감옥 = [e for e in 감옥 if not gf.스킬_지정불가인가(상태, 데이터, e)]
    return [e["id"] for e in 적들 + 감옥]


class _정책:
    """두 정책이 같이 쓰는 것 - 후보 만들기, 행동 실행, 한 차례."""

    이름 = ""

    def __init__(self, 시드):
        self.R = random.Random(f"정책:{시드}")
        self.걸러짐 = collections.Counter()
        self.사용기록 = []  # scenario._쓸_가치가_있나가 보는 이번 전투의 스킬 사용 [{"라운드", "스킬", "시전자"}]

    def 전투_시작(self):
        self.사용기록 = []

    def 후보(self, 상태, 참가자):
        """지금 할 수 있는 행동 [(행동, 대상id|None)] - 행동은 "일반공격"이나 스킬 이름.
        적을 노리는 행동은 노릴 수 있는 적마다 하나씩, 아군·자신 대상은 대상 없이 하나."""
        후보 = []
        for 이름 in 참가자["원본"]["보유스킬"]:
            if not gf.스킬_사용_가능여부(상태, 참가자, 이름)[0]:
                continue
            타겟 = gf.스킬_실제_타겟(상태, 상태["스킬데이터모음"][이름])
            if 타겟 in scenario._정책_제외_타겟:
                continue
            if not scenario._쓸_가치가_있나(상태, 참가자, 이름, self.사용기록):
                self.걸러짐[(참가자["원본"].get("전직"), 이름)] += 1
                continue
            if 타겟 and 타겟.startswith("적"):
                후보 += [(이름, i) for i in _표적들(상태, 이름)]
            elif scenario._스킬_인수(상태, 참가자, 이름) is not None:
                후보.append((이름, None))
            else:
                self.걸러짐[(참가자["원본"].get("전직"), 이름)] += 1
        if gf.일반공격_가능여부(상태, 참가자):
            후보 += [("일반공격", i) for i in _표적들(상태)]
        return 후보

    @staticmethod
    def 실행(상태, 참가자, 행동, 대상id):
        if 행동 == "일반공격":
            gf.아군_일반공격(상태, 참가자_찾기(상태, 대상id))
        elif 대상id is not None:
            gf.아군_스킬사용(상태, 행동, 중심대상=참가자_찾기(상태, 대상id))
        else:
            gf.아군_스킬사용(상태, 행동, **scenario._스킬_인수(상태, 참가자, 행동))

    def 고르기(self, 상태, 참가자, 후보):
        raise NotImplementedError

    def 차례(self, 상태, 기록=None):
        """아군 한 차례 - 할 수 있는 행동이 없을 때까지 고르고 실행한 뒤 턴을 넘긴다.
        기록(list)이 있으면 행동마다 {"이름", "전직", "행동", "표적", "피해", "라운드"}를 더한다."""
        전투상태 = 상태["전투상태"]
        참가자 = gf.현재_턴_참가자(상태)
        if 전투상태["라운드"] > gf.자동전투_최대라운드:
            gf.자동전투_한_턴(상태)  # 자동전투와 같은 시간 초과 패배
            return
        for _ in range(_차례당_최대행동):
            if 전투상태["종료"] is not None or not 참가자["생존"]:
                return
            후보 = self.후보(상태, 참가자)
            if not 후보:
                break
            행동, 대상id = 후보[self.고르기(상태, 참가자, 후보)]
            전HP = _적HP(상태)
            표적 = _표적_종류(상태, 대상id)
            self.실행(상태, 참가자, 행동, 대상id)
            if 행동 != "일반공격":
                self.사용기록.append(
                    {
                        "라운드": 전투상태["라운드"],
                        "스킬": 행동,
                        "시전자": 참가자["이름"],
                    }
                )
            if 기록 is not None:
                기록.append(
                    {
                        "이름": 참가자["원본"]["캐릭터명"],
                        "전직": 참가자["원본"].get("전직"),
                        "행동": 행동,
                        "표적": 표적,
                        "피해": max(0, 전HP - _적HP(상태)),
                        "라운드": 전투상태["라운드"],
                    }
                )
        else:
            raise AssertionError("한 차례에 20번 넘게 행동했다 - 행동이 줄지 않는다")
        if 전투상태["종료"] is None:
            gf.턴_넘기기(상태)


def _적HP(상태):
    return sum(e["현재HP"] for e in gf.적_목록(상태) if e["생존"])


def _표적_종류(상태, 대상id):
    """기록용 표적 이름 - 없음/HP최저/보스/감옥/기타."""
    if 대상id is None:
        return "없음"
    대상 = 참가자_찾기(상태, 대상id)
    if 대상["진영"] == "감옥":
        return "감옥"
    if 대상["원본"].get("칭호") == "보스":
        return "보스"
    적들 = scenario._살아있는_적(상태)
    return "HP최저" if 적들 and 적들[0] is 대상 else "기타"


class 무작위정책(_정책):
    """분석용 - 행동을 고르게 고른 뒤 그 행동의 표적을 고르게 고른다."""

    이름 = "분석용"

    def 고르기(self, 상태, 참가자, 후보):
        행동들 = list(dict.fromkeys(a for a, _ in 후보))
        행동 = self.R.choice(행동들)
        return self.R.choice([i for i, (a, _) in enumerate(후보) if a == 행동])


class 탐색정책(_정책):
    """승률용 - 몬테카를로 탐색. 후보수를 넘으면 행동마다 HP 최저 표적을 먼저 남기고 나머지는 무작위로 줄인다.
    후보마다 같은 시드 횟수개로(공통 난수 - 후보끼리 운이 같게) 라운드만큼 전력전투로 굴려 점수를 평균한다."""

    이름 = "승률용"

    def __init__(self, 시드, 후보수=8, 횟수=3, 라운드=2):
        super().__init__(시드)
        self.후보수, self.횟수, self.라운드 = 후보수, 횟수, 라운드

    def _줄이기(self, 후보):
        if len(후보) <= self.후보수:
            return list(range(len(후보)))
        먼저, 나머지, 본행동 = [], [], set()
        for i, (a, _) in enumerate(후보):
            (나머지 if a in 본행동 else 먼저).append(i)
            본행동.add(a)
        if len(먼저) > self.후보수:
            return sorted(self.R.sample(먼저, self.후보수))
        return sorted(먼저 + self.R.sample(나머지, self.후보수 - len(먼저)))

    def 고르기(self, 상태, 참가자, 후보):
        남김 = self._줄이기(후보)
        if len(남김) == 1:
            return 남김[0]
        시드들 = [self.R.getrandbits(32) for _ in range(self.횟수)]
        저장 = rng.상태()
        try:
            점수 = {
                i: sum(self._굴려보기(상태, 참가자, 후보[i], s) for s in 시드들)
                for i in 남김
            }
        finally:
            rng.상태_복원(저장)
        최고 = max(점수.values())
        return self.R.choice([i for i in 남김 if 점수[i] == 최고])

    def _굴려보기(self, 상태, 참가자, 후보, 시드):
        사본 = 상태_복사(상태)
        rng.시드(시드)
        전투상태 = 사본["전투상태"]
        나 = 참가자_찾기(사본, 참가자["id"])
        self.실행(사본, 나, *후보)
        끝라운드 = 전투상태["라운드"] + self.라운드
        # 이 차례의 남은 행동과 그 뒤는 전력전투로
        for _ in range(판당_최대턴):
            if 전투상태["종료"] is not None or 전투상태["라운드"] >= 끝라운드:
                break
            p = gf.현재_턴_참가자(사본)
            if p["진영"] == "아군" and p["생존"]:
                gf.자동전투_한_턴(사본)
            else:
                gf.턴_넘기기(사본)
        return 상태_점수(사본)


class 전력전투정책:
    """비교 기준 - 자동전투 "전력전투"(ctl_autobattle) 그대로."""

    이름 = "전력전투"

    def __init__(self, 시드=0):
        self.걸러짐 = collections.Counter()

    def 전투_시작(self):
        pass

    def 차례(self, 상태, 기록=None):
        gf.자동전투_한_턴(상태)


정책들 = {"전력전투": 전력전투정책, "분석용": 무작위정책, "승률용": 탐색정책}


# ------------------------------------------------------------------ 점수와 한 판


def _아군들(상태):
    return [p for p in gf.아군_목록(상태) if not p.get("인형")]


def HP_비율(상태):
    """(아군 HP 합 ÷ 최대 HP 합, 적 HP 합 ÷ 시작 HP 합)."""
    아군 = _아군들(상태)
    최대 = sum(gf.캐릭터_최대HP(상태, p["원본"]) for p in 아군) or 1
    적시작 = 상태["전투상태"].get("_적시작HP") or 1
    return (
        sum(p["현재HP"] for p in 아군 if p["생존"]) / 최대,
        _적HP(상태) / 적시작,
    )


def 상태_점수(상태):
    """이기면 +2, 지면 -2에 남은 아군 HP 비율을 더하고 남은 적 HP 비율을 뺀다."""
    종료 = 상태["전투상태"]["종료"]
    아군, 적 = HP_비율(상태)
    보너스 = 2 if 종료 == "아군승리" else -2 if 종료 is not None else 0
    return 보너스 + 아군 - 적


def 판_점수(결과):
    return (2 if 결과["승"] else -2) + 결과["아군HP"] - 결과["적HP"]


def 한판(구성, 정책, 시드, 조건=조건, 끌사람=None):
    """한 판 -> {"승", "라운드", "아군HP", "적HP"(끝난 때 비율), "파티원": {이름: {"전직", "딜", "받음", "생존"}},
    "인형딜": {이름: 피해}, "행동": [행동 기록]}. 정책 시드는 정책이 갖고, 전투 시드는 시드다."""
    상태 = 전투_준비(구성, 시드, 조건, 끌사람)
    전투상태 = 상태["전투상태"]
    전투상태["_적시작HP"] = _적HP(상태)
    정책.전투_시작()
    기록 = []
    for _ in range(판당_최대턴):
        if gf.전투_종료됨(상태):
            break
        p = gf.현재_턴_참가자(상태)
        if p["진영"] == "아군" and p["생존"]:
            정책.차례(상태, 기록)
        else:
            gf.턴_넘기기(상태)
    딜 = core.피해_집계(전투상태)
    받음 = contribution.받은피해_집계(전투상태)
    아군HP, 적HP = HP_비율(상태)
    파티원 = {
        p["원본"]["캐릭터명"]: {
            "전직": p["원본"].get("전직"),
            "딜": 딜.get(p["이름"], 0),
            "받음": 받음.get(p["이름"], 0),
            "생존": p["생존"],
        }
        for p in _아군들(상태)
    }
    인형 = {p["이름"] for p in 전투상태["참가자"] if p.get("인형")}
    return {
        "승": 전투상태["종료"] == "아군승리",
        "라운드": 전투상태["라운드"],
        "아군HP": round(아군HP, 4),
        "적HP": round(적HP, 4),
        "파티원": 파티원,
        "인형딜": {이름: 딜.get(이름, 0) for 이름 in sorted(인형)},
        "행동": 기록,
    }


# ------------------------------------------------------------------ 요약


def 행동_요약(판들):
    """{(전직, 행동): {"횟수", "판"(쓴 판 수), "평균피해"(한 번에), "쓴판승률", "안쓴판승률"}}.
    안 쓴 판은 그 전직이 파티에 있었는데 그 행동을 안 쓴 판이다 - 두 승률의 차이가 그 행동의 승리 기여를 가늠한다."""
    횟수, 피해, 쓴판 = (
        collections.Counter(),
        collections.Counter(),
        collections.defaultdict(list),
    )
    전직판 = collections.defaultdict(list)
    for 번, r in enumerate(판들):
        for 칸 in r["파티원"].values():
            전직판[칸["전직"]].append(번)
        본 = set()
        for a in r["행동"]:
            키 = (a["전직"], a["행동"])
            횟수[키] += 1
            피해[키] += a["피해"]
            본.add(키)
        for 키 in 본:
            쓴판[키].append(번)

    def 승률(번들):
        return sum(판들[i]["승"] for i in 번들) / len(번들) if 번들 else None

    요약 = {}
    for 키, n in 횟수.items():
        쓴 = set(쓴판[키])
        안쓴 = [i for i in dict.fromkeys(전직판[키[0]]) if i not in 쓴]
        요약[키] = {
            "횟수": n,
            "판": len(쓴),
            "평균피해": round(피해[키] / n, 1),
            "쓴판승률": 승률(sorted(쓴)),
            "안쓴판승률": 승률(안쓴),
        }
    return 요약


def 파티원_요약(판들, 키="전직"):
    """{전직(또는 1차 직업): {"판", "생존율", "판당딜", "판당받음", "딜지분"(판마다 파티 딜 중 몫의 평균)}}."""
    칸 = collections.defaultdict(lambda: collections.Counter())
    for r in 판들:
        합 = sum(c["딜"] for c in r["파티원"].values()) or 1
        for c in r["파티원"].values():
            k = c[키]
            칸[k]["판"] += 1
            칸[k]["생존"] += c["생존"]
            칸[k]["딜"] += c["딜"]
            칸[k]["받음"] += c["받음"]
            칸[k]["지분"] += c["딜"] / 합
    return {
        k: {
            "판": v["판"],
            "생존율": round(v["생존"] / v["판"], 3),
            "판당딜": round(v["딜"] / v["판"], 1),
            "판당받음": round(v["받음"] / v["판"], 1),
            "딜지분": round(v["지분"] / v["판"], 3),
        }
        for k, v in sorted(칸.items())
    }


# ------------------------------------------------------------------ 비교 실행


def 파티_측정(구성, 정책이름, 판, 시드=0, 지표=False):
    """파티 하나를 전투 시드 시드..시드+판-1로 잰다 -> {"판들": [...], "지표": {이름: {...}}|None}.
    정책 시드는 전투 시드와 같다(같은 판끼리 비교). 지표면 파티원마다 그를 끈 판도 돌려 딜기여도를 낸다."""
    클래스 = 정책들[정책이름]
    판들 = [한판(구성, 클래스(s), s) for s in range(시드, 시드 + 판)]
    결과 = {
        "구성": [list(x) for x in 구성],
        "정책": 정책이름,
        "판들": 판들,
        "지표": None,
    }
    if 지표:
        이름들 = list(판들[0]["파티원"])
        본 = _평균(판들)
        끈 = {
            이름: _평균(
                [한판(구성, 클래스(s), s, 끌사람=이름) for s in range(시드, 시드 + 판)]
            )
            for 이름 in 이름들
        }
        결과["지표"] = contribution.지표_계산(본, 끈)
    return 결과


def _평균(판들):
    딜, 받음 = collections.Counter(), collections.Counter()
    for r in 판들:
        for 이름, c in r["파티원"].items():
            딜[이름] += c["딜"]
            받음[이름] += c["받음"]
    n = len(판들)
    return {
        "딜": {k: v / n for k, v in 딜.items()},
        "받음": {k: v / n for k, v in 받음.items()},
    }


def _작업(인수):
    return 파티_측정(*인수)


def 비교(파티수, 판, 정책이름들, 시드=0, 지표=False, 병렬=1):
    """균등 파티 파티수개 x 판을 정책마다 같은 파티·같은 시드로 -> {정책: [파티_측정 결과]}."""
    파티들 = 균등_파티(파티수, 시드)
    작업 = [(구성, 정책, 판, 시드, 지표) for 정책 in 정책이름들 for 구성 in 파티들]
    if 병렬 > 1:
        import multiprocessing

        with multiprocessing.Pool(병렬) as pool:
            결과들 = pool.map(_작업, 작업, chunksize=1)
    else:
        결과들 = [_작업(a) for a in 작업]
    묶음 = {정책: [] for 정책 in 정책이름들}
    for r in 결과들:
        묶음[r["정책"]].append(r)
    return 묶음


def 보고(묶음):
    """정책마다 승률, 1차 직업별 생존율, (지표가 있으면) 전직별 딜기여도 평균을 글로."""
    줄 = []
    for 정책, 결과들 in 묶음.items():
        판들 = [r for 결과 in 결과들 for r in 결과["판들"]]
        승 = sum(r["승"] for r in 판들)
        줄.append(f"## {정책}: 승률 {승 / len(판들):.1%} ({승}/{len(판들)}판)")
        for r in 판들:
            for c in r["파티원"].values():
                c["직업"] = _1차[c["전직"]]
        생존 = 파티원_요약(판들, "직업")
        줄.append(
            "생존율 " + ", ".join(f"{k} {v['생존율']:.0%}" for k, v in 생존.items())
        )
        if 결과들[0]["지표"] is not None:
            기여 = collections.defaultdict(list)
            for 결과 in 결과들:
                전직 = {
                    이름: c["전직"] for 이름, c in 결과["판들"][0]["파티원"].items()
                }
                for 이름, v in 결과["지표"].items():
                    if 이름 in 전직:
                        기여[전직[이름]].append(v["딜기여도"])
            줄.append(
                "딜기여도 "
                + ", ".join(
                    f"{k} {sum(v) / len(v):+.1f}%"
                    for k, v in sorted(
                        기여.items(), key=lambda x: -sum(x[1]) / len(x[1])
                    )
                )
            )
    return "\n".join(줄)


_1차 = {전직: 직업 for 직업, 전직 in 전직_목록()}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--파티", type=int, default=24)
    p.add_argument("--판", type=int, default=10)
    p.add_argument("--시드", type=int, default=0)
    p.add_argument("--정책", nargs="+", default=list(정책들), choices=list(정책들))
    p.add_argument(
        "--지표", action="store_true", help="딜기여도(파티원마다 끈 판, 판수가 5배)"
    )
    p.add_argument("--병렬", type=int, default=1)
    p.add_argument("--출력", help="판별 결과 전체를 JSON으로")
    a = p.parse_args(argv)
    시작 = time.time()
    묶음 = 비교(a.파티, a.판, a.정책, a.시드, a.지표, a.병렬)
    print(보고(묶음))
    분석 = [r for 결과 in 묶음.get("분석용", []) for r in 결과["판들"]]
    if 분석:
        요약 = 행동_요약(분석)
        차이 = sorted(
            (
                (v["쓴판승률"] - v["안쓴판승률"], k, v)
                for k, v in 요약.items()
                if v["안쓴판승률"] is not None and v["판"] >= 10
            ),
            key=lambda x: x[0],
        )
        print("## 분석용 - 쓴 판 승률 - 안 쓴 판 승률 (아래 5, 위 5)")
        for d, k, v in 차이[:5] + 차이[-5:]:
            print(f"{k[0]} {k[1]}: {d:+.1%} ({v['판']}판, 한 번에 {v['평균피해']})")
    if a.출력:
        with open(a.출력, "w", encoding="utf-8") as f:
            json.dump(
                {정책: 결과들 for 정책, 결과들 in 묶음.items()}, f, ensure_ascii=False
            )
    print(f"{time.time() - 시작:.0f}초")


if __name__ == "__main__":
    main()
