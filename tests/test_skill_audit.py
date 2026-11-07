"""스킬 전수 점검(작업 14) - 직접 쓰는 스킬 모두를 사용 조건을 갖춘 실제 전투에서 쓴다.

test_combat_skills는 그냥 쓴 결과를 골든에 박는다(조건이 안 맞으면 "사용 불가"도 그대로). 여기서는
조건(자원·무기·소환수·체이서·특수행동)을 갖춘 뒤 불변식만 단언한다 - 결과표는 docs/skill_audit.md.
- 쓸 수 있고 예외 없이 끝나며, 그 스킬(연계스킬은 앞 스킬에 이어)이 로그에 남는다.
- 전투 기록 문장에 dict·None·TODO가 그대로 보이지 않는다(뒤 3라운드 포함).
- 데이터의 MP소모만큼 MP가 줄고(조건부효과가 없을 때), 버프획득·지속턴이 실제로 붙는다.
- 레벨 12 스킬강화(최종피해 x1.5, MP x2)가 그 스킬의 모든 타격과 비용에 걸린다.
- 스킬 데이터의 키는 엔진이 읽는다(설명용 키는 이유와 함께 허용 목록에).
"""

import glob
import json
import math
import re

import pytest

import gameflow as gf
from game.controller import ctl_battle, ctl_battle_log
from game.system import equipment_system, rng
from game.system import skill_system as ss
from game.system.combat import flow
from tests import support

스킬데이터 = gf.스킬데이터모음_생성()
기본전직 = {직업: next(iter(전직들)) for 직업, 전직들 in gf.전직_레지스트리.items()}
적_구성 = ["타우 아미", "고블린", "고블린 투척병", "고블린"]


def _소유표():
    결과 = {}
    for 직업, 정보 in gf.직업_레지스트리.items():
        for 이름 in 정보["스킬목록"]:
            결과[이름] = (직업, None)
    for 직업, 전직들 in gf.전직_레지스트리.items():
        for 전직명, 정보 in 전직들.items():
            for 이름 in 정보["스킬목록"]:
                결과[이름] = (직업, 전직명)
    return 결과


소유표 = _소유표()
직접쓰는스킬 = [
    n for n, d in 스킬데이터.items() if d["분류"] not in ("반응스킬", "던전스킬")
]
무기카탈로그 = {
    k: v for 정보 in gf.직업_레지스트리.values() for k, v in 정보["무기목록"].items()
}
# 연계스킬이 이어 붙는 스킬(수플렉스 -> 수플렉스 썬더) - 쓰면 연계스킬 MP도 같이 든다
연계되는스킬 = {d["연계"] for d in 스킬데이터.values() if d.get("연계")}
나쁜문장 = re.compile(r"\{'|TODO|None|<function|\{\}")


def _전장(스킬):
    직업, 전직명 = 소유표.get(스킬, ("귀검사", None))  # 공용 스킬은 귀검사가 쓴다
    rng.시드(11)
    나머지 = [j for j in gf.직업_레지스트리 if j != 직업][:3]
    상태 = support.새게임([("", 직업)] + [("", j) for j in 나머지])
    for i, c in enumerate(상태["파티"]["파티원"]):
        전직 = 전직명 if i == 0 and 전직명 else 기본전직[c["직업"]]
        support.성장(상태, c, 10, 전직=전직, 스킬습득=True)
    gf.파티_최대치로_회복(상태)
    gf.전투_시작(상태, 적_구성, 레벨=6, 차수=2)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    시전자 = next(
        p for p in 전투상태["참가자"] if p["원본"] is 상태["파티"]["파티원"][0]
    )
    if 스킬 not in 시전자["원본"]["보유스킬"]:
        시전자["원본"]["보유스킬"].append(스킬)
    전투상태["현재턴"] = 전투상태["참가자"].index(시전자)
    flow.턴_시작_처리(전투상태, 시전자)
    시전자["현재MP"] = max(시전자["현재MP"], 100)
    return 상태, 시전자


def _조건_갖추기(상태, 시전자, 스킬):
    """사용 불가 사유를 보고 조건을 하나씩 채운다. 채운 것을 돌려준다."""
    전투상태 = 상태["전투상태"]
    한일 = []
    for _ in range(4):
        가능, 사유 = ctl_battle.스킬_사용_가능여부(상태, 시전자, 스킬)
        if 가능:
            break
        if m := re.search(r"'(.+?)' 자원이 부족", 사유):
            ss.이름있는효과_부여(전투상태, 시전자, m.group(1), 3)
        elif m := re.search(r"무기 '(.+?)'를 들어야", 사유):
            시전자["장비데이터"]["무기"] = dict(
                next(
                    v
                    for v in 무기카탈로그.values()
                    if equipment_system.무기_종류(v) == m.group(1)
                )
            )
        elif "체이서가 없다" in 사유:
            ss.이름있는효과_부여(전투상태, 시전자, "체이서 : 화", 3)
        elif (m := re.search(r"하급정령 '(.+?)'", 사유)) or "돌려보낼" in 사유:
            # 정령계약이면 하급정령 대신 중급정령이 나온다(#586) - 하급정령을 부르려고 뺀다
            if "정령계약" in 시전자["원본"]["보유특성"]:
                시전자["원본"]["보유특성"].remove("정령계약")
            소환 = f"정령소환 : {m.group(1) if m else '아도르'}"
            if 소환 not in 시전자["원본"]["보유스킬"]:
                시전자["원본"]["보유스킬"].append(소환)
            gf.아군_스킬사용(상태, 소환)
            for k in 시전자["행동자원"]:
                시전자["행동자원"][k] = max(시전자["행동자원"][k], 1)
            시전자["현재MP"] = 100
        elif m := re.search(r"'(.+?)'이\(가\) 남아있지 않다", 사유):
            시전자["기타행동"][m.group(1)] = 1
        else:
            pytest.fail(f"{스킬}: 갖출 수 없는 사용 조건 - {사유}")
        한일.append(사유)
    return 한일


def _요약(p):
    return {
        "HP": p["현재HP"],
        "MP": p.get("현재MP"),
        "버프": {b["이름"]: b.get("지속턴") for b in p["버프"] + p["디버프"]},
        "상태이상": {s["이름"] for s in p["상태이상"] if isinstance(s, dict)},
    }


def _나쁜_문장들(로그):
    return [
        str(줄)
        for 항목 in 로그
        for 줄 in ctl_battle_log.로그_문장들(항목)
        if 나쁜문장.search(str(줄))
    ]


def _이_스킬의_로그(로그스킬, 스킬):
    """그 스킬 자신의 타격(분할공격 "스킬 (1단계)", 패턴 "스킬 : 패턴")만 - 연계스킬은 뺀다."""
    로그스킬 = str(로그스킬 or "")
    return 로그스킬 == 스킬 or 로그스킬.startswith((f"{스킬} (", f"{스킬} : "))


def 스킬_실행(스킬, 강화=False):
    """조건을 갖춰 스킬을 한 번 쓰고 3라운드 더 진행한다. 측정값을 돌려준다."""
    데이터 = 스킬데이터[스킬]
    상태, 시전자 = _전장(스킬)
    전투상태 = 상태["전투상태"]
    if 강화:
        시전자["원본"]["스킬강화"] = {
            "스킬": 스킬,
            "최종피해배율": 1.5,
            "MP소모배율": 2,
        }
    쓸것 = 데이터["연계"] if "연계스킬" in (데이터.get("타입") or []) else 스킬
    if 쓸것 not in 시전자["원본"]["보유스킬"]:
        시전자["원본"]["보유스킬"].append(쓸것)
    _조건_갖추기(상태, 시전자, 쓸것)
    적들 = [p for p in 전투상태["참가자"] if p["진영"] == "적" and p["생존"]]
    아군들 = [p for p in 전투상태["참가자"] if p["진영"] == "아군"]
    타겟 = str(
        데이터.get("타겟")
        or (데이터.get("공격단계1") or {}).get("타겟")
        or (데이터.get("지속공격") or {}).get("타겟")
    )
    if 타겟.startswith("적"):
        중심 = 적들[1]
    elif 타겟 == "아군단일":
        중심 = next(p for p in 아군들 if p is not 시전자)
    else:
        중심 = 시전자
    지정 = [적들[0], 적들[1], 적들[0]] if 타겟 == "적반복지정" else None
    assert ctl_battle.스킬_사용_가능여부(상태, 시전자, 쓸것)[0], 스킬
    전 = {p["이름"]: _요약(p) for p in 전투상태["참가자"]}
    시작 = len(전투상태["로그"])
    gf.아군_스킬사용(상태, 쓸것, 중심대상=중심, 지정대상목록=지정)
    로그 = 전투상태["로그"][시작:]
    후 = {p["이름"]: _요약(p) for p in 전투상태["참가자"]}
    타격 = [
        t.get("피해")
        for x in 로그
        if _이_스킬의_로그(x.get("스킬"), 스킬)
        for t in x.get("타격") or []
    ]
    새버프 = {}
    for 이름, 요약 in 후.items():
        for b, 턴 in 요약["버프"].items():
            if b not in 전.get(이름, {"버프": {}})["버프"]:
                새버프.setdefault(b, set()).add(턴)
    측정 = {
        "시전자전": 전[시전자["이름"]],
        "시전자후": 후[시전자["이름"]],
        "타격": 타격,
        "새버프": 새버프,
        "로그에스킬": 스킬 in json.dumps(로그, ensure_ascii=False, default=str),
        "나쁜문장": _나쁜_문장들(로그),
    }
    for _ in range(3 * len(전투상태["참가자"])):
        if gf.전투_종료됨(상태):
            break
        gf.턴_넘기기(상태)
    측정["나쁜문장"] += _나쁜_문장들(전투상태["로그"][시작 + len(로그) :])
    return 측정


@pytest.mark.parametrize("스킬", 직접쓰는스킬)
def test_스킬은_조건을_갖추면_쓰이고_데이터대로_비용과_버프가_든다(스킬):
    데이터 = 스킬데이터[스킬]
    측정 = 스킬_실행(스킬)
    assert 측정["로그에스킬"], 스킬
    assert 측정["나쁜문장"] == [], 스킬
    MP = 데이터.get("MP소모")
    전, 후 = 측정["시전자전"], 측정["시전자후"]
    if (
        isinstance(MP, int)
        and not 데이터.get("조건부효과")
        and "연계스킬" not in (데이터.get("타입") or [])
        and 스킬 not in 연계되는스킬
    ):
        # 혈기왕성(버서커)은 MP 대신 HP 절반(올림)을 낸다
        assert 전["MP"] - 후["MP"] == MP or 전["HP"] - 후["HP"] >= math.ceil(MP / 2)
    버프 = 데이터.get("버프획득")
    for 이름 in [버프] if isinstance(버프, str) else 버프 or []:
        if 데이터["분류"] == "소환스킬" or 이름 not in _버프_이름들():
            continue  # 소환(정령계약이면 중급정령)·상태이상형 버프("살의의 파동")는 따로 본다
        assert 이름 in 측정["새버프"], (스킬, 이름)
        if isinstance(데이터.get("지속턴"), int):
            # 사슬 해제(소울브링어)는 귀신 스킬 지속턴 +2
            보너스 = (
                2 if "귀신" in 데이터["타입"] and 소유표[스킬][1] == "소울브링어" else 0
            )
            assert 측정["새버프"][이름] == {데이터["지속턴"] + 보너스}, 스킬


def _버프_이름들():
    from game.system.combat import resources

    return {
        n
        for n in {
            b
            for d in 스킬데이터.values()
            for b in (
                [d["버프획득"]]
                if isinstance(d.get("버프획득"), str)
                else d.get("버프획득") or []
            )
        }
        if resources.효과정의_조회(n)[0] is not None
    }


@pytest.mark.parametrize(
    "스킬",
    [n for n in 직접쓰는스킬 if "연계스킬" not in (스킬데이터[n].get("타입") or [])],
)
def test_스킬강화는_그_스킬의_피해를_1점5배_MP를_2배로_한다(스킬):
    기본, 강화 = 스킬_실행(스킬), 스킬_실행(스킬, 강화=True)
    MP기본 = 기본["시전자전"]["MP"] - 기본["시전자후"]["MP"]
    MP강화 = 강화["시전자전"]["MP"] - 강화["시전자후"]["MP"]
    if (
        MP기본 and not 스킬데이터[스킬].get("켤때MP") and 스킬 not in 연계되는스킬
    ):  # 나선의 넨: 켤 때 MP는 배율 밖
        assert MP강화 == 2 * MP기본, 스킬
    # 같은 시드라 굴림이 같다 - 대상이 먼저 쓰러져 타격 수가 줄면 거기까지만 비교한다
    for a, b in zip(기본["타격"], 강화["타격"]):
        if a:
            assert b in (math.floor(a * 1.5), math.ceil(a * 1.5)), (스킬, a, b)


# 엔진이 읽지 않아도 되는 키 - 이유와 함께. 새 키를 데이터에 넣으면 엔진이 읽거나 여기에 이유를 적는다.
설명용_키 = {
    "습득퍽": "어느 퍽으로 얻는지 적는 표식(퍽 데이터의 획득스킬이 실제로 준다)",
    "발동조건_변수설명": "반응스킬 발동조건식의 변수 설명",
    "발동조건_주체": "반응스킬 발동조건 설명",
    "발동조건_상황": "반응스킬 발동조건 설명",
    "적명중결과": "발동조건_변수설명 안의 변수 이름",
}


def _값으로_쓰는_키(데이터):
    """dict의 키가 이름(패턴·자원·형태 이름)인 칸 - 키가 데이터 값이다."""
    키 = set()
    for d in 데이터.values():
        for 칸 in ("패턴", "자원소모", "장판별", "형태순서"):
            if isinstance(d.get(칸), dict):
                키 |= set(d[칸])
        선택 = (d.get("패턴분기") or {}).get("선택")
        if isinstance(선택, dict):
            키 |= set(선택)
    return 키


def test_스킬_데이터의_키는_엔진이_읽는다():
    소스 = "".join(
        open(f, encoding="utf-8").read()
        for f in glob.glob("game/**/*.py", recursive=True) + ["gameflow.py"]
        if "/data/" not in f.replace("\\", "/")
    )
    키들 = set()

    def 모으기(v):
        if isinstance(v, dict):
            for k, x in v.items():
                키들.add(k)
                모으기(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                모으기(x)

    for d in 스킬데이터.values():
        모으기(d)
    안읽힘 = {
        k
        for k in 키들 - set(설명용_키) - _값으로_쓰는_키(스킬데이터)
        if f'"{k}"' not in 소스 and f"'{k}'" not in 소스
    }
    assert 안읽힘 == set()
    # 허용 목록이 낡지 않게 - 실제로 데이터에 있고 엔진이 안 읽는 키만
    for k in 설명용_키:
        assert k in 키들 and f'"{k}"' not in 소스, k
