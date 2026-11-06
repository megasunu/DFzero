"""던전 밸런스 모의전투 - 던전의 인카운트·전투이벤트(보스)·원정을 시드 여럿으로 싸워 승률을 잰다(#491).

    python tools/dungeon_sim.py D11 D13 --판 300            # 인카운트·보스 각 300판, 진입 레벨, 측정 장비
    python tools/dungeon_sim.py D11 --종류 원정 --판 100 --레벨 8
    python tools/dungeon_sim.py D11 --차수 1 --마리 2 3     # 조정안을 임시로 바꿔 끼워 잰다(데이터 파일은 그대로)
    python tools/dungeon_sim.py --표 하늘성 --판 300 --출력 결과.json   # 보고서(docs/balance/하늘성.md)의 표 전부

전투 종류
  인카운트  던전 데이터의 출현그룹·출현마리수·레벨·차수로 게임과 같은 함수(dungeon_system.인카운트_판정,
            챔피언_부여)가 뽑은 무리와 한 번 싸운다. 판마다 쉰다(판끼리 독립).
  보스      그 던전의 보스전투 오브젝트(전투이벤트)의 몬스터·레벨·차수와 한 번 싸운다. 판마다 쉰다.
  원정      입구(위층은 아래층에서 넘어오는 칸)에서 쉬지 않고 걸어 인카운트를 다 싸우고 보스까지 이기면 승리.
            포션·휴식 없음 - 가장 엄한 조건이다.

아군은 모두 자동전투 "전력전투"로 싸운다(플레이어 정책 없이 같은 조건 비교용). 판 i의 시드는 시작시드+i라
조정안끼리 같은 시드를 쓴다(공통 난수). 파티는 tests/의 결정적 성장 도우미로 키운다(tests/scenario.py
측정_파티_준비 - 언커먼 무기, 레벨 6부터 언커먼 방어구, 7부터 한 명 레어).
"""

import argparse
import collections
import concurrent.futures
import contextlib
import copy
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _경로 in (ROOT, os.path.join(ROOT, "tests")):
    if _경로 not in sys.path:
        sys.path.insert(0, _경로)

판당_최대턴 = 600
기본_구성 = [  # S7의 기본 4인 파티(tests/support.py 구현된_전직)
    ["귀검사", "웨펀마스터"],
    ["격투가", "스트라이커"],
    ["거너", "레인저"],
    ["프리스트", "크루세이더"],
]


# ------------------------------------------------------------------ 조건 (게임 없이)


def 던전_찾기(코드, 레지스트리):
    """ "D11" 또는 파일명 -> 던전 파일명."""
    if 코드 in 레지스트리:
        return 코드
    맞음 = [f for f in 레지스트리 if f"_{코드}_" in f]
    if len(맞음) != 1:
        raise SystemExit(f"던전 {코드!r}를 하나로 찾지 못함: {맞음}")
    return 맞음[0]


def 보스_오브젝트(맵정보):
    """(좌표, 오브젝트) - 던전의 보스전투 오브젝트(전투이벤트)."""
    return next(
        (p, o) for p, o in 맵정보["오브젝트"].items() if o.get("타입") == "보스전투"
    )


def 조정_인카운트(인카운트, 조정):
    """인카운트 정의의 사본에 조정(레벨+·차수·마리)을 적용한다. 원본은 바꾸지 않는다."""
    새 = copy.deepcopy(인카운트)
    새["레벨"] = 새.get("레벨", 1) + 조정.get("레벨+", 0)
    if 조정.get("차수") is not None:
        새["차수"] = 조정["차수"]
    if 조정.get("마리") is not None:
        새["출현마리수"] = tuple(조정["마리"])
    return 새


def 조정_보스(오브젝트, 조정):
    """보스 오브젝트의 (몬스터 항목들, 레벨, 차수) - 조정 "보스마리"가 있으면 앞에서 그만큼만(보스 포함)."""
    항목 = list(오브젝트["전투몬스터"])
    if 조정.get("보스마리") is not None:
        항목 = 항목[: 조정["보스마리"]]
    레벨 = 오브젝트.get("레벨", 1) + 조정.get("레벨+", 0)
    차수 = 조정["차수"] if 조정.get("차수") is not None else 오브젝트.get("차수")
    return 항목, 레벨, 차수


def 피해_집계(로그, 적이름):
    """전투 로그에서 적이 아군에게 준 피해를 (몬스터명, 패턴)마다 더한다. 적이름: 참가자 이름 -> 몬스터명.
    일반공격은 "피해", 패턴 공격은 "총피해"를 쓴다(지속 피해·반사 등 로그의 다른 줄은 세지 않는다)."""
    합 = collections.Counter()
    for e in 로그:
        몹 = 적이름.get(e.get("공격자"))
        if 몹 is None:
            continue
        피해 = e.get("총피해", e.get("피해"))
        if not isinstance(피해, (int, float)) or 피해 <= 0:
            continue
        합[(몹, e.get("패턴") or e.get("종류"))] += 피해
    return 합


def 요약(결과들):
    """판 결과 목록 -> {판, 승, 승률, 평균라운드, 몬스터별 피해 상위}."""
    판 = len(결과들)
    승 = sum(r["승"] for r in 결과들)
    피해 = collections.Counter()
    for r in 결과들:
        for k, v in r["피해"].items():
            피해[k] += v
    전체 = sum(피해.values()) or 1
    return {
        "판": 판,
        "승": 승,
        "승률": round(승 / 판, 3) if 판 else 0.0,
        "평균라운드": round(sum(r["라운드"] for r in 결과들) / 판, 1) if 판 else 0,
        "평균인카운트": round(sum(r.get("인카운트", 0) for r in 결과들) / 판, 1)
        if 판
        else 0,
        "피해상위": [
            [k, round(v / 판, 1), round(v / 전체, 3)] for k, v in 피해.most_common(6)
        ],
    }


def 몬스터별_피해(피해상위):
    """피해상위 [["몬스터|패턴", 판당, 비율], ...] -> 몬스터명마다 비율 합."""
    합 = collections.Counter()
    for k, _, 비율 in 피해상위:
        합[k.split("|")[0]] += 비율
    return 합


# ------------------------------------------------------------------ 게임 (판 하나)


class 판:
    """한 조건(던전·종류·파티·조정)의 전투 환경. 파티는 한 번 키워 두고 판마다 쉬고 싸운다."""

    def __init__(self, 던전, 종류, 레벨, 구성=None, 장비="측정", 조정=None):
        import gameflow as gf
        import scenario
        import support
        from game.controller.ctl_registry import 몬스터목록
        from game.system import dungeon_system, rng, town_system

        self.gf, self.scenario, self.support, self.rng = gf, scenario, support, rng
        self.dungeon_system, self.town_system = dungeon_system, town_system
        self.몬스터목록 = 몬스터목록
        self.던전 = 던전_찾기(던전, gf.던전_레지스트리)
        self.종류, self.조정 = 종류, dict(조정 or {})
        self.맵정보 = gf.던전_레지스트리[self.던전]
        gf.자동전투_방식_설정("전력전투")
        구성 = 구성 or 기본_구성
        rng.시드(1)
        상태 = support.새게임([("", 직업) for 직업, _ in 구성])
        if 장비 == "측정":
            scenario.측정_파티_준비(상태, 레벨, 전직={j: 전 for j, 전 in 구성})
        else:  # "시작": 시작 장비 그대로, 스킬만 배운다
            for c, (_, 전직) in zip(상태["파티"]["파티원"], 구성):
                support.성장(상태, c, 레벨, 전직=전직, 스킬습득=True)
        상태["진행도"]["플레이어레벨"] = 레벨
        self.상태 = 상태

    @contextlib.contextmanager
    def _챔피언(self):
        이전 = self.dungeon_system.챔피언_확률
        if self.조정.get("챔피언") is False:
            self.dungeon_system.챔피언_확률 = 0.0
        try:
            yield
        finally:
            self.dungeon_system.챔피언_확률 = 이전

    def _싸우기(self):
        """열린 전투를 끝까지 자동으로 싸우고 정리한다 -> (승, 라운드, 피해)."""
        결과 = self._싸우기_열린채()
        self.gf.전투_결과_정리(self.상태)
        return 결과

    def 한판(self, 시드):
        gf, 상태 = self.gf, self.상태
        gf.휴식(상태)
        상태["던전상태"] = None
        self.rng.시드(시드)
        with self._챔피언():
            if self.종류 == "인카운트":
                인카운트 = 조정_인카운트(self.맵정보["인카운트"], self.조정)
                인카운트["인카운트확률"] = {"안전걸음": 0, "걸음당증가율": 1.0}
                뽑음 = self.dungeon_system.인카운트_판정(
                    {"맵정보": {"인카운트": 인카운트}, "걸음수": 1}
                )
                몹 = self.dungeon_system.챔피언_부여(
                    뽑음["등장몬스터"], self.몬스터목록
                )
                gf.전투_시작(상태, 몹, 레벨=인카운트["레벨"], 차수=인카운트["차수"])
                승, 라운드, 피해 = self._싸우기()
                return {"승": 승, "라운드": 라운드, "피해": 피해}
            if self.종류 == "보스":
                _, 오브젝트 = 보스_오브젝트(self.맵정보)
                항목, 레벨, 차수 = 조정_보스(오브젝트, self.조정)
                gf.전투_시작(상태, 항목, 레벨=레벨, 차수=차수)
                승, 라운드, 피해 = self._싸우기()
                return {"승": 승, "라운드": 라운드, "피해": 피해}
            return self._원정()

    def _원정(self):
        gf, 상태, support = self.gf, self.상태, self.support
        맵 = copy.deepcopy(self.맵정보)
        if 맵.get("인카운트"):
            맵["인카운트"] = 조정_인카운트(맵["인카운트"], self.조정)
        _, 오브젝트 = 보스_오브젝트(맵)
        항목, 레벨, 차수 = 조정_보스(오브젝트, self.조정)
        오브젝트.update(전투몬스터=항목, 레벨=레벨, 차수=차수)
        시작 = (
            next(
                (
                    c["진입좌표"]
                    for 다른 in gf.던전_레지스트리.values()
                    for c in 다른.get("연결지역", {}).values()
                    if c.get("연결맵") == self.던전 and c.get("진입좌표")
                ),
                None,
            )
            if 맵.get("입장좌표") is None
            else None
        )
        상태["던전상태"] = self.dungeon_system.던전_시작(
            맵, self.던전, 시작좌표=시작, 진행도=상태["진행도"]
        )
        합 = {"승": False, "라운드": 0, "피해": collections.Counter(), "인카운트": 0}

        class _짐(Exception):
            pass

        def 처리(_상태):
            승, 라운드, 피해 = self._싸우기_열린채()
            합["라운드"] += 라운드
            합["피해"].update(피해)
            합["인카운트"] += 1
            if not 승:
                raise _짐()

        try:
            결과, _ = support.보스_처치(상태, 전투처리=처리)
        except _짐:
            상태["전투상태"] = None
            상태["던전상태"] = None
            return 합
        합["인카운트"] -= 1  # 마지막은 보스
        합["승"] = 결과 == "아군승리"
        상태["던전상태"] = None
        return 합

    def _싸우기_열린채(self):
        """열린 전투를 끝까지 자동으로 -> (승, 라운드, 피해). 정리는 부르는 쪽(원정은 support)이 한다.
        적이름은 끝난 뒤에 모아 전투 중 들어온 적(소환수)도 넣는다."""
        gf, 상태 = self.gf, self.상태
        self.support.반응_처리(상태)
        for _ in range(판당_최대턴):
            if gf.전투_종료됨(상태):
                break
            p = gf.현재_턴_참가자(상태)
            if p["진영"] == "아군" and p["생존"]:
                gf.자동전투_한_턴(상태)
            else:
                gf.턴_넘기기(상태)
        전투 = 상태["전투상태"]
        적이름 = {
            p["이름"]: p["원본"].get("몬스터명", p["이름"])
            for p in 전투["참가자"]
            if p["진영"] == "적"
        }
        return (
            전투.get("종료") == "아군승리",
            전투.get("라운드", 0),
            피해_집계(전투["로그"], 적이름),
        )


# ------------------------------------------------------------------ 측정


def _조각(인수):
    조건, 시드들 = 인수
    m = 판(
        조건["던전"],
        조건["종류"],
        조건["레벨"],
        조건.get("구성"),
        조건.get("장비", "측정"),
        조건.get("조정"),
    )
    결과 = []
    for s in 시드들:
        r = m.한판(s)
        r["피해"] = {f"{a}|{b}": v for (a, b), v in r["피해"].items()}
        결과.append(r)
    return 결과


def 재기(조건, 판수, 시작시드=1000, 일꾼=1):
    """조건 하나를 판수만큼 -> 요약. 일꾼이 2 이상이면 시드를 나눠 프로세스로 돌린다(결과는 같다)."""
    시드 = list(range(시작시드, 시작시드 + 판수))
    if 일꾼 <= 1:
        결과 = _조각((조건, 시드))
    else:
        조각들 = [(조건, 시드[i::일꾼]) for i in range(일꾼)]
        with concurrent.futures.ProcessPoolExecutor(일꾼) as ex:
            결과 = [r for 묶음 in ex.map(_조각, 조각들) for r in 묶음]
    return 요약(결과)


# 보고서(docs/balance/하늘성.md)의 표. 진입 레벨 = 그 던전 몬스터 레벨 = 앞 던전 보스로 오르는 플레이어 레벨
# (ctl_registry.플레이어레벨업_트리거: D10->6, D12->7, D14->8).
하늘성 = ["D11", "D12", "D13", "D14", "D15", "D16"]
진입레벨 = {
    "D08": 4,
    "D09": 5,
    "D10": 5,
    "D11": 6,
    "D12": 6,
    "D13": 7,
    "D14": 7,
    "D15": 8,
    "D16": 8,
}
다른_구성 = {
    "기본(웨·스·레·크)": 기본_구성,
    "마법사(웨·스·엘·크)": [
        ["귀검사", "웨펀마스터"],
        ["격투가", "스트라이커"],
        ["마법사", "엘리멘탈마스터"],
        ["프리스트", "크루세이더"],
    ],
    "딜러(버·넨·레·엘)": [
        ["귀검사", "버서커"],
        ["격투가", "넨마스터"],
        ["거너", "레인저"],
        ["마법사", "엘리멘탈마스터"],
    ],
}
조정안 = {
    "현재": {},
    "A 차수1": {"차수": 1},
    "B 마리-1": {"마리": None, "마리-": 1, "보스마리": 3},
    "C 레벨-2": {"레벨+": -2},
}


def 조정_풀기(이름, 던전정보):
    """조정안 이름 -> 그 던전에 맞춘 조정 dict("마리-"는 출현마리수 양끝에서 1씩 뺀다, 최소 1)."""
    조정 = dict(조정안[이름])
    if "마리-" in 조정:
        a, b = 던전정보["인카운트"]["출현마리수"]
        d = 조정.pop("마리-")
        조정["마리"] = [max(1, a - d), max(1, b - d)]
    return 조정


def 표_조건들(판수):
    """보고서 표의 (표이름, 행이름, 조건) 목록."""
    import gameflow as gf

    out = []
    for d in 하늘성 + ["D08", "D09", "D10"]:
        for 종류 in ("인카운트", "보스"):
            out.append(
                ("기준", f"{d} {종류}", {"던전": d, "종류": 종류, "레벨": 진입레벨[d]})
            )
    for d in 하늘성:
        out.append(
            ("기준", f"{d} 원정", {"던전": d, "종류": "원정", "레벨": 진입레벨[d]})
        )
    for d in ("D08", "D10"):
        out.append(
            ("기준", f"{d} 원정", {"던전": d, "종류": "원정", "레벨": 진입레벨[d]})
        )
    for d in 하늘성:
        for 레벨 in (진입레벨[d] + 2, 10, 12, 15):
            for 종류 in ("인카운트", "보스"):
                out.append(
                    (
                        "레벨",
                        f"{d} {종류} L{레벨}",
                        {"던전": d, "종류": 종류, "레벨": 레벨},
                    )
                )
    for d in ("D11", "D13", "D15"):
        for 이름, 구성 in 다른_구성.items():
            for 종류 in ("인카운트", "보스"):
                out.append(
                    (
                        "구성",
                        f"{d} {종류} {이름}",
                        {"던전": d, "종류": 종류, "레벨": 진입레벨[d], "구성": 구성},
                    )
                )
    for d in ("D11", "D13", "D15"):
        for 종류 in ("인카운트", "보스"):
            out.append(
                (
                    "장비",
                    f"{d} {종류} 시작장비",
                    {"던전": d, "종류": 종류, "레벨": 진입레벨[d], "장비": "시작"},
                )
            )
        out.append(
            (
                "원인",
                f"{d} 인카운트 챔피언없음",
                {
                    "던전": d,
                    "종류": "인카운트",
                    "레벨": 진입레벨[d],
                    "조정": {"챔피언": False},
                },
            )
        )
    for d in 하늘성:
        정보 = gf.던전_레지스트리[던전_찾기(d, gf.던전_레지스트리)]
        for 이름 in 조정안:
            if 이름 == "현재":
                continue
            for 종류 in ("인카운트", "보스", "원정"):
                out.append(
                    (
                        "조정안",
                        f"{d} {종류} {이름}",
                        {
                            "던전": d,
                            "종류": 종류,
                            "레벨": 진입레벨[d],
                            "조정": 조정_풀기(이름, 정보),
                        },
                    )
                )
    return out


def _커밋():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "?"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("던전", nargs="*", help="D11 같은 던전 코드")
    p.add_argument(
        "--종류",
        nargs="+",
        default=["인카운트", "보스"],
        choices=["인카운트", "보스", "원정"],
    )
    p.add_argument("--판", type=int, default=300)
    p.add_argument("--레벨", type=int, help="파티 레벨(없으면 진입 레벨)")
    p.add_argument("--장비", default="측정", choices=["측정", "시작"])
    p.add_argument("--차수", type=int)
    p.add_argument("--레벨더하기", type=int, default=0, help="몬스터 레벨 조정")
    p.add_argument("--마리", type=int, nargs=2)
    p.add_argument("--보스마리", type=int)
    p.add_argument("--챔피언없음", action="store_true")
    p.add_argument("--시드", type=int, default=1000, help="시작 시드")
    p.add_argument("--일꾼", type=int, default=os.cpu_count() or 1)
    p.add_argument("--표", choices=["하늘성"], help="보고서 표 전부를 잰다")
    p.add_argument("--원정판", type=int, help="--표에서 원정 판수(없으면 --판의 1/3)")
    p.add_argument("--출력", help="결과 JSON 경로")
    a = p.parse_args(argv)

    if a.표:
        조건들 = 표_조건들(a.판)
    else:
        조정 = {"레벨+": a.레벨더하기}
        if a.차수 is not None:
            조정["차수"] = a.차수
        if a.마리:
            조정["마리"] = a.마리
        if a.보스마리:
            조정["보스마리"] = a.보스마리
        if a.챔피언없음:
            조정["챔피언"] = False
        조건들 = [
            (
                "직접",
                f"{d} {종류}",
                {
                    "던전": d,
                    "종류": 종류,
                    "레벨": a.레벨 or 진입레벨.get(d, 6),
                    "장비": a.장비,
                    "조정": 조정,
                },
            )
            for d in a.던전
            for 종류 in a.종류
        ]
    결과 = {"커밋": _커밋(), "시작시드": a.시드, "판": a.판, "행": []}
    for 표, 행, 조건 in 조건들:
        판수 = (
            (a.원정판 or max(1, a.판 // 3)) if 조건["종류"] == "원정" and a.표 else a.판
        )
        r = 재기(조건, 판수, a.시드, a.일꾼)
        결과["행"].append({"표": 표, "행": 행, "조건": 조건, **r})
        상위 = ", ".join(f"{k} {비율:.0%}" for k, _, 비율 in r["피해상위"][:3])
        print(
            f"{표}\t{행}\t{r['승']}/{r['판']}\t{r['승률']:.0%}\t라운드 {r['평균라운드']}\t{상위}",
            flush=True,
        )
        if a.출력:
            with open(a.출력, "w", encoding="utf-8") as f:
                json.dump(결과, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
