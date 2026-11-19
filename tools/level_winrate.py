"""레벨별 등록 파티 승률 - 레벨마다 등록한 파티로 그 레벨 던전의 인카운트·보스·원정 승률을 잰다.

    python tools/level_winrate.py --판 100                  # 등록 파일의 모든 레벨
    python tools/level_winrate.py --레벨 2 --판 50 --표 결과.md --출력 결과.json

등록 파일(docs/balance/레벨별_파티.json)의 "레벨" 아래에 레벨마다
  던전  재는 던전 코드 목록(D01 ...)
  종류  "인카운트" / "보스" / "원정" 중 잴 것
  준비  "초기" = 새 게임 그대로(레벨 1, 시작 장비, 스킬 없음)
        "성장" = 그 레벨까지 결정적으로 레벨업(tests/support.성장, 스킬은 배우지 않음), 장비는 시작 장비
  파티  [{"이름", "직업": 1차 직업 4개, "봉인": {"직업", "아이템"}(없어도 됨)}]
        봉인 = 그 직업 캐릭터가 무기 칸에 레어 마법봉인 무기를 봉인된 채로 낀다.
전투는 tools/dungeon_sim.py와 같다 - 아군 전원 자동전투 "전력전투", 판마다 쉬고, 판 i의 시드는 시작시드+i라
파티끼리 같은 시드를 쓴다(공통 난수). 깃허브 액션 "Level winrate"(버튼 실행)가 이 도구를 돌려 표를 실행 요약에 남긴다.
"""

import argparse
import concurrent.futures
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _경로 in (ROOT, os.path.join(ROOT, "tests")):
    if _경로 not in sys.path:
        sys.path.insert(0, _경로)

from tools import dungeon_sim as ds  # noqa: E402

등록경로 = os.path.join(ROOT, "docs", "balance", "레벨별_파티.json")
종류들 = ("인카운트", "보스", "원정")
준비들 = ("초기", "성장")
파티인원 = 4


# ------------------------------------------------------------------ 등록 파일


def 등록_읽기(경로=등록경로):
    with open(경로, encoding="utf-8") as f:
        return json.load(f)


def 등록_검사(등록):
    """등록 내용의 문제 목록(비었으면 정상). 게임 데이터와 대조한다 - 직업, 던전, 봉인 아이템."""
    import gameflow as gf
    from game.data.character.job_info import 직업정보

    문제 = []
    무기 = _무기목록()
    for 레벨, 항목 in 등록.get("레벨", {}).items():
        머리 = f"레벨 {레벨}"
        if not 레벨.isdigit() or int(레벨) < 1:
            문제.append(f"{머리}: 레벨은 1 이상의 정수")
        if 항목.get("준비") not in 준비들:
            문제.append(f"{머리}: 준비는 {'/'.join(준비들)} 중 하나")
        elif 항목["준비"] == "초기" and 레벨 != "1":
            문제.append(f"{머리}: 준비 '초기'는 레벨 1만")
        for d in 항목.get("던전") or []:
            try:
                ds.던전_찾기(d, gf.던전_레지스트리)
            except SystemExit:
                문제.append(f"{머리}: 없는 던전 {d}")
        if not 항목.get("던전"):
            문제.append(f"{머리}: 던전이 없다")
        if not 항목.get("종류") or set(항목["종류"]) - set(종류들):
            문제.append(f"{머리}: 종류는 {'/'.join(종류들)} 중에서")
        이름들 = [p.get("이름") for p in 항목.get("파티") or []]
        if not 이름들:
            문제.append(f"{머리}: 파티가 없다")
        if len(set(이름들)) != len(이름들):
            문제.append(f"{머리}: 파티 이름이 겹친다")
        for p in 항목.get("파티") or []:
            곳 = f"{머리} {p.get('이름')}"
            직업들 = p.get("직업") or []
            if len(직업들) != 파티인원:
                문제.append(f"{곳}: 직업은 {파티인원}개")
            if len(set(직업들)) != len(직업들):
                문제.append(f"{곳}: 같은 직업이 둘")
            for j in 직업들:
                if j not in 직업정보:
                    문제.append(f"{곳}: 없는 1차 직업 {j}")
            봉인 = p.get("봉인")
            if 봉인 is None:
                continue
            if 봉인.get("직업") not in 직업들:
                문제.append(f"{곳}: 봉인 직업 {봉인.get('직업')}이 파티에 없다")
            템 = 무기.get(봉인.get("아이템"))
            if 템 is None:
                문제.append(f"{곳}: 없는 무기 {봉인.get('아이템')}")
            elif 템.get("레어도") != "레어" or "마법봉인" not in 템.get("타입", []):
                문제.append(f"{곳}: {봉인['아이템']}은 레어 마법봉인 무기가 아니다")
    return 문제


def _무기목록():
    import support

    return support.새게임([("", "귀검사")])["상점카탈로그"]["장비"]["무기"]


# ------------------------------------------------------------------ 파티 준비와 판


def 파티_상태(레벨, 준비, 파티):
    """등록 파티 하나 -> 준비를 마친 새 게임 상태. 봉인 무기는 끼고 나서 정말 끼었는지 확인한다."""
    import gameflow as gf
    import support
    from game.system import rng

    rng.시드(1)
    상태 = support.새게임([("", j) for j in 파티["직업"]])
    if 준비 == "성장":
        for c in 상태["파티"]["파티원"]:
            support.성장(상태, c, 레벨)
    봉인 = 파티.get("봉인")
    if 봉인:
        c = next(c for c in 상태["파티"]["파티원"] if c["직업"] == 봉인["직업"])
        상태["소지품"]["장비"][봉인["아이템"]] = 1
        gf.장비_교체(상태, c, "무기", 봉인["아이템"])
        끼운것 = gf.캐릭터_장착아이템(상태, c, "무기")["이름"]
        if 끼운것 != 봉인["아이템"]:
            raise ValueError(f"{c['직업']}이 {봉인['아이템']}을 끼지 못했다")
    상태["진행도"]["플레이어레벨"] = max(상태["진행도"]["플레이어레벨"], 레벨)
    return 상태


class 등록판(ds.판):
    """dungeon_sim.판과 같은 전투(한판·원정·싸우기)를 등록 파티 상태로 돈다."""

    def __init__(self, 던전, 종류, 레벨, 준비, 파티):
        import gameflow as gf
        import scenario
        import support
        from game.controller.ctl_registry import 몬스터목록
        from game.system import dungeon_system, rng, town_system

        self.gf, self.scenario, self.support, self.rng = gf, scenario, support, rng
        self.dungeon_system, self.town_system = dungeon_system, town_system
        self.몬스터목록 = 몬스터목록
        self.던전 = ds.던전_찾기(던전, gf.던전_레지스트리)
        self.종류, self.조정 = 종류, {}
        self.맵정보 = gf.던전_레지스트리[self.던전]
        gf.자동전투_방식_설정("전력전투")
        self.상태 = 파티_상태(레벨, 준비, 파티)


def _조각(인수):
    조건, 시드들 = 인수
    m = 등록판(조건["던전"], 조건["종류"], 조건["레벨"], 조건["준비"], 조건["파티"])
    결과 = []
    for s in 시드들:
        r = m.한판(s)
        r["피해"] = {f"{a}|{b}": v for (a, b), v in r["피해"].items()}
        결과.append(r)
    return 결과


def 조건들(등록, 레벨들=None):
    """잴 조건 목록 - 레벨, 파티, 던전, 종류 순."""
    목록 = []
    for 레벨, 항목 in sorted(등록["레벨"].items(), key=lambda kv: int(kv[0])):
        if 레벨들 and int(레벨) not in 레벨들:
            continue
        for 파티 in 항목["파티"]:
            for 던전 in 항목["던전"]:
                for 종류 in 항목["종류"]:
                    목록.append(
                        {
                            "레벨": int(레벨),
                            "준비": 항목["준비"],
                            "파티": 파티,
                            "던전": 던전,
                            "종류": 종류,
                        }
                    )
    return 목록


def 재기(목록, 판수, 시작시드=1000, 일꾼=1):
    """조건마다 판수만큼 -> [조건 + 요약]. 일꾼 수와 상관없이 결과가 같다(판 i의 시드 = 시작시드 + i)."""
    시드 = list(range(시작시드, 시작시드 + 판수))
    작업 = [(조건, 시드[i::일꾼]) for 조건 in 목록 for i in range(일꾼)]
    if 일꾼 <= 1:
        조각결과 = [_조각(w) for w in 작업]
    else:
        with concurrent.futures.ProcessPoolExecutor(일꾼) as ex:
            조각결과 = list(ex.map(_조각, 작업))
    결과 = []
    for k, 조건 in enumerate(목록):
        판들 = [r for 묶음 in 조각결과[k * 일꾼 : (k + 1) * 일꾼] for r in 묶음]
        결과.append({**조건, **ds.요약(판들)})
    return 결과


# ------------------------------------------------------------------ 표


def 윌슨_구간(승, 판, z=1.96):
    """승률의 95% 윌슨 구간 (아래, 위)."""
    if 판 == 0:
        return 0.0, 0.0
    p = 승 / 판
    분모 = 1 + z * z / 판
    가운데 = (p + z * z / (2 * 판)) / 분모
    폭 = z * math.sqrt(p * (1 - p) / 판 + z * z / (4 * 판 * 판)) / 분모
    return max(0.0, 가운데 - 폭), min(1.0, 가운데 + 폭)


def _퍼센트(x):
    return f"{x * 100:.1f}%"


def _봉인칸(파티):
    봉인 = 파티.get("봉인")
    return f"{봉인['직업']}: {봉인['아이템']}" if 봉인 else "-"


def 표(결과, 판수, 시작시드):
    """결과 -> 마크다운. 레벨마다 파티 x (던전 종류) 승률표와 자세한 표."""
    줄 = [
        "# 레벨별 등록 파티 승률",
        "",
        f"판 {판수}개씩(시드 {시작시드}~{시작시드 + 판수 - 1}, 파티끼리 같은 시드), 아군 전원 자동전투 전력전투. "
        "구간은 95% 윌슨 구간이다.",
    ]
    for 레벨 in sorted({r["레벨"] for r in 결과}):
        행들 = [r for r in 결과 if r["레벨"] == 레벨]
        열 = list(dict.fromkeys(f"{r['던전']} {r['종류']}" for r in 행들))
        파티들 = list(dict.fromkeys(r["파티"]["이름"] for r in 행들))
        줄 += ["", f"## 레벨 {레벨} (준비: {행들[0]['준비']})", ""]
        줄.append("| 파티 | 직업 | 봉인 무기 | " + " | ".join(열) + " | 평균 |")
        줄.append("|---" * (len(열) + 4) + "|")
        for 이름 in 파티들:
            내것 = [r for r in 행들 if r["파티"]["이름"] == 이름]
            칸 = {f"{r['던전']} {r['종류']}": r["승률"] for r in 내것}
            평균 = sum(칸.values()) / len(칸)
            파티 = 내것[0]["파티"]
            줄.append(
                f"| {이름} | {' · '.join(파티['직업'])} | {_봉인칸(파티)} | "
                + " | ".join(_퍼센트(칸[c]) for c in 열)
                + f" | {_퍼센트(평균)} |"
            )
        줄 += [
            "",
            "<details><summary>자세히</summary>",
            "",
            "| 파티 | 던전 | 종류 | 승/판 | 승률 | 95% 구간 | 평균 라운드 | 가장 아픈 몬스터 |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for r in 행들:
            아래, 위 = 윌슨_구간(r["승"], r["판"])
            아픔 = r["피해상위"][0][0].split("|")[0] if r["피해상위"] else "-"
            줄.append(
                f"| {r['파티']['이름']} | {r['던전']} | {r['종류']} | {r['승']}/{r['판']} | "
                f"{_퍼센트(r['승률'])} | {_퍼센트(아래)}~{_퍼센트(위)} | {r['평균라운드']} | {아픔} |"
            )
        줄 += ["", "</details>"]
    return "\n".join(줄) + "\n"


# ------------------------------------------------------------------ 명령


def main(argv=None):
    p = argparse.ArgumentParser(description="레벨별 등록 파티 던전 승률")
    p.add_argument("--등록", default=등록경로, help="등록 파일 경로")
    p.add_argument("--레벨", type=int, nargs="*", help="잴 레벨(없으면 전부)")
    p.add_argument("--판", type=int, default=100, help="조건마다 판 수")
    p.add_argument("--시드", type=int, default=1000, help="시작 시드")
    p.add_argument("--일꾼", type=int, default=os.cpu_count() or 1)
    p.add_argument("--표", help="마크다운 표를 쓸 경로(없으면 화면에만)")
    p.add_argument("--출력", help="결과 JSON 경로")
    a = p.parse_args(argv)

    등록 = 등록_읽기(a.등록)
    문제 = 등록_검사(등록)
    if 문제:
        print("등록 파일 문제:\n- " + "\n- ".join(문제), file=sys.stderr)
        return 2
    목록 = 조건들(등록, a.레벨)
    if not 목록:
        print("잴 조건이 없다(레벨을 확인)", file=sys.stderr)
        return 2
    결과 = 재기(목록, a.판, a.시드, max(1, a.일꾼))
    글 = 표(결과, a.판, a.시드)
    print(글)
    if a.표:
        with open(a.표, "w", encoding="utf-8") as f:
            f.write(글)
    if a.출력:
        with open(a.출력, "w", encoding="utf-8") as f:
            json.dump(
                {"판": a.판, "시드": a.시드, "결과": 결과},
                f,
                ensure_ascii=False,
                indent=1,
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
