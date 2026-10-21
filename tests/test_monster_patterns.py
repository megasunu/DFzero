"""몬스터 패턴·특성 단위 테스트 - 전격의 키놀, 공중에뜸 -> 넘어짐, 펜릴/루가루/좀비, 타우·샤우타,
몬스터 공격의 능력치 보정치, 거대화, 차수만큼 패턴 반복, 케라하·비노슈 주문영창과 감옥, 명중 굴림 없는 공격의 연출.

패턴 데이터 값은 전수 골든(test_combat_monsters)이 본다. 여기는 패턴이 일으키는 규칙을 정확한 값으로 본다.
"""

import random

import pytest

from game.system import rng
import gameflow as gf
from game.system.combat import (
    attacks,
    core,
    damage,
    flow,
    monster_actions,
    stats,
    status,
    traits,
)
from game.system import dice_utils
from game.system.skill import skill_target
from tests import support


# ------------------------------------------------------------- 전격의 키놀 (사용자 지정 2026-10-13)


@pytest.fixture
def 키놀전장(monkeypatch):
    """키놀 1마리 대 4인 파티. 모두 HP를 넉넉히 두고, 키놀 원본(지능 12, 보정 +1)을 돌려준다."""
    rng.시드(5)
    상태 = support.새게임(
        [("", "귀검사"), ("", "격투가"), ("", "거너"), ("", "마법사")]
    )
    gf.전투_시작(상태, ["전격의 키놀"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    키놀 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
    아군 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "아군"),
        key=lambda p: p["대형위치"],
    )
    for p in 전투상태["참가자"]:
        p["현재HP"] = 999
    return 전투상태, 키놀, 아군


def test_초전자포는_한_번_굴려_주대상은_전부_양옆은_절반_민첩내성_성공시_다시_절반(
    키놀전장, monkeypatch
):
    전투상태, 키놀, 아군 = 키놀전장
    from game.system import monster_ai

    support.주사위고정(monkeypatch, 4)  # 2d4 = 8
    # 내성굴림 순서: 대상마다(대형위치 왼쪽부터) 민첩 내성, 피해가 들어가면 알비노 고블린의
    # 감전 건강 내성. 오른쪽 옆만 민첩 내성 성공, 감전 내성은 모두 성공(감전 없음)
    결과들 = [False, True, False, True, True, True]
    monkeypatch.setattr(
        dice_utils, "내성_굴림", lambda 보정치, 난이도, **kw: (결과들.pop(0), 난이도)
    )
    monkeypatch.setattr(
        monster_ai, "행동_선택", lambda p: gf.몬스터목록["전격의 키놀"]["패턴"][6]
    )
    monkeypatch.setattr(monster_ai, "타겟_선택", lambda *a, **k: 아군[1])
    HP전 = {p["이름"]: p["현재HP"] for p in 아군}
    결과 = monster_actions.몬스터_턴_실행(전투상태, 키놀)

    # 2d4(8) + 지능보정치(1) + 몬스터 공통 데미지보너스
    원래피해 = 8 + 1 + monster_actions.몬스터_데미지보너스(전투상태, 키놀)

    def 기대(값, p):
        return damage.최종피해_계산(
            값, stats.유효_방어력(전투상태, p), stats.유효_보호률(전투상태, p)
        )

    assert [t["대상"] for t in 결과["타격"]] == [p["이름"] for p in 아군[:3]]
    assert HP전[아군[1]["이름"]] - 아군[1]["현재HP"] == 기대(원래피해, 아군[1])
    assert HP전[아군[0]["이름"]] - 아군[0]["현재HP"] == 기대(원래피해 * 0.5, 아군[0])
    assert HP전[아군[2]["이름"]] - 아군[2]["현재HP"] == 기대(원래피해 * 0.25, 아군[2])
    assert 아군[3]["현재HP"] == HP전[아군[3]["이름"]]
    assert 결과["난이도"] == 9 + 1


def _키놀_턴(전투상태, 키놀, monkeypatch, 패턴):
    """키놀이 이 패턴으로 한 턴을 하고 턴을 끝낸다(턴 종료 시 소환수 행동 포함)."""
    from game.system import monster_ai

    monkeypatch.setattr(monster_ai, "행동_선택", lambda p: 패턴)
    전투상태["현재턴"] = 전투상태["참가자"].index(키놀)
    flow.턴_시작_처리(전투상태, 키놀)
    monster_actions.몬스터_턴_실행(전투상태, 키놀)
    flow.턴_종료_처리(전투상태, 키놀)


def _연쇄번개_공격수(전투상태, 시작):
    return sum(
        len(x["타격"])
        for x in 전투상태["로그"][시작:]
        if x.get("패턴") == "연쇄 번개" and x.get("비고") == "소환수 행동"
    )


def test_연쇄_번개는_3턴간_턴_끝마다_무작위_적을_치고_겹쳐_쓰면_그만큼_더_친다(
    키놀전장, monkeypatch
):
    전투상태, 키놀, 아군 = 키놀전장
    연쇄 = gf.몬스터목록["전격의 키놀"]["패턴"][4]
    무행동 = {"이름": "쉬기", "타입": "무행동"}
    공격수 = []
    for 패턴 in [연쇄, 무행동, 무행동]:
        시작 = len(전투상태["로그"])
        _키놀_턴(전투상태, 키놀, monkeypatch, 패턴)
        공격수.append(_연쇄번개_공격수(전투상태, 시작))
    assert 공격수 == [1, 1, 0]  # 건 턴을 포함해 2턴(2026-10-13 3 -> 2)
    assert not any(b["이름"] == "소환:연쇄 번개" for b in 키놀["버프"])

    공격수 = []
    for 패턴 in [연쇄, 연쇄, 무행동, 무행동]:
        시작 = len(전투상태["로그"])
        _키놀_턴(전투상태, 키놀, monkeypatch, 패턴)
        공격수.append(_연쇄번개_공격수(전투상태, 시작))
    assert 공격수 == [1, 2, 1, 0]  # 시전마다 따로 2턴
    기록 = [x for x in 전투상태["로그"] if x.get("패턴") == "연쇄 번개" and "타격" in x]
    assert all(
        t["판정"].get("명중결과") is not None for x in 기록 for t in x["타격"]
    )  # 매번 명중굴림(지능판정)


def test_연쇄_번개는_1d4_지능보정치_데미지보너스_마이너스1(키놀전장, monkeypatch):
    # 사용자 지정(2026-10-13): 1d8 -> 1d6, 데미지보너스 -1, 지속턴 3 -> 2. 2026-10-15 1d6 -> 1d4
    전투상태, 키놀, 아군 = 키놀전장
    support.주사위고정(monkeypatch, 15)  # 명중, 1d4 = 4
    monkeypatch.setattr(
        dice_utils, "내성_굴림", lambda 보정치, 난이도, **kw: (True, 난이도)
    )
    monkeypatch.setattr(rng.대상, "choice", lambda 목록: 목록[0])
    시작 = len(전투상태["로그"])
    _키놀_턴(전투상태, 키놀, monkeypatch, gf.몬스터목록["전격의 키놀"]["패턴"][4])
    [기록] = [
        x
        for x in 전투상태["로그"][시작:]
        if x.get("패턴") == "연쇄 번개" and x.get("비고") == "소환수 행동"
    ]
    [타격] = 기록["타격"]
    대상 = next(p for p in 아군 if p["이름"] == 타격["대상"])
    기대 = damage.최종피해_계산(
        4 + 1 - 1, stats.유효_방어력(전투상태, 대상), stats.유효_보호률(전투상태, 대상)
    )
    assert 타격["피해"] == 기대


def test_알비노_고블린은_명속성_피해를_주면_건강내성_실패시_3턴_감전(
    키놀전장, monkeypatch
):
    전투상태, 키놀, 아군 = 키놀전장
    support.주사위고정(monkeypatch, 15)  # 명중
    monkeypatch.setattr(
        dice_utils, "내성_굴림", lambda 보정치, 난이도, **kw: (False, 난이도)
    )
    번개 = gf.몬스터목록["전격의 키놀"]["패턴"][2]
    반월도 = gf.몬스터목록["전격의 키놀"]["패턴"][1]
    from game.system import monster_ai

    monkeypatch.setattr(monster_ai, "타겟_선택", lambda *a, **k: 아군[0])
    _키놀_턴(전투상태, 키놀, monkeypatch, 반월도)  # 무속성 - 감전 없음
    assert all(i["이름"] != "감전" for i in 아군[0]["상태이상"])
    _키놀_턴(전투상태, 키놀, monkeypatch, 번개)
    감전 = [i for i in 아군[0]["상태이상"] if i["이름"] == "감전"]
    # 건 턴의 끝에 지속턴이 1 줄 수 있다(감전도 지속피해형) - 3턴짜리로 걸렸는지 본다
    assert len(감전) == 1 and 감전[0]["지속턴"] in (2, 3)
    비고 = [x for x in 전투상태["로그"] if "'알비노 고블린' 특성" in str(x.get("비고"))]
    assert 비고 and "감전" in 비고[-1]["비고"]


def _기상번개_준비(전투상태, 키놀, monkeypatch, 내성성공):
    """키놀을 넘어짐(2턴 - 턴 시작에 1 줄어도 남는다)으로 두고, 모든 내성을 내성성공으로 고정한다.
    1~6번 패턴을 고르면 실패하게 해 대체행동만 쓰는지 본다."""
    from game.system import monster_ai

    support.주사위고정(monkeypatch, 6)  # 1d8 = 6
    monkeypatch.setattr(
        dice_utils, "내성_굴림", lambda 보정치, 난이도, **kw: (내성성공, 난이도)
    )

    def 고르면_안됨(p):
        raise AssertionError("넘어짐인 턴에 1~6번 패턴을 골랐다")

    monkeypatch.setattr(monster_ai, "행동_선택", 고르면_안됨)
    키놀["상태이상"].append({"이름": "넘어짐", "지속턴": 2})
    전투상태["현재턴"] = 전투상태["참가자"].index(키놀)


def test_특수패턴_키놀은_넘어짐이면_넘어짐을_풀고_1_6번_대신_기상번개_적전체_명속성_감전(
    키놀전장, monkeypatch
):
    # 사용자 지정 2026-10-15: 알비노 고블린의 "넘어짐 해제시" 공격을 키놀의 대체행동 "기상번개"로 옮겼다

    전투상태, 키놀, 아군 = 키놀전장
    assert "특수패턴:키놀" in gf.몬스터목록["전격의 키놀"]["특성"]
    _기상번개_준비(전투상태, 키놀, monkeypatch, 내성성공=False)
    HP전 = {p["이름"]: p["현재HP"] for p in 아군}
    flow.턴_시작_처리(전투상태, 키놀)
    결과 = monster_actions.몬스터_턴_실행(전투상태, 키놀)

    assert 결과["패턴"] == "기상번개"
    assert all(i["이름"] != "넘어짐" for i in 키놀["상태이상"])
    # 1d8(6) + 지능보정치(1) + 몬스터 공통 데미지보너스, 민첩 내성 실패
    원래피해 = 6 + 1 + monster_actions.몬스터_데미지보너스(전투상태, 키놀)
    for p in 아군:
        기대 = damage.최종피해_계산(
            원래피해, stats.유효_방어력(전투상태, p), stats.유효_보호률(전투상태, p)
        )
        assert HP전[p["이름"]] - p["현재HP"] == 기대, p["이름"]
        # 명속성 피해 -> 알비노 고블린의 감전(건강 내성 실패)
        assert any(i["이름"] == "감전" for i in p["상태이상"]), p["이름"]


def test_기상번개는_민첩내성에_성공하면_피한다(키놀전장, monkeypatch):

    전투상태, 키놀, 아군 = 키놀전장
    _기상번개_준비(전투상태, 키놀, monkeypatch, 내성성공=True)
    HP전 = {p["이름"]: p["현재HP"] for p in 아군}
    flow.턴_시작_처리(전투상태, 키놀)
    결과 = monster_actions.몬스터_턴_실행(전투상태, 키놀)
    assert 결과["패턴"] == "기상번개"
    assert all(HP전[p["이름"]] == p["현재HP"] for p in 아군)


def test_알비노_고블린은_넘어짐이_끝나도_공격하지_않는다(키놀전장):
    # 사용자 지정 2026-10-15: 해제시 공격은 특수패턴:키놀로 옮기고 감전(속성피해시효과)만 남겼다
    from game.data.monster.monster_ability import 특성목록

    assert (
        "발동조건" not in 특성목록["알비노 고블린"]
        or not 특성목록["알비노 고블린"]["발동조건"]
    )
    전투상태, 키놀, 아군 = 키놀전장
    HP전 = {p["이름"]: p["현재HP"] for p in 아군}
    키놀["상태이상"].append({"이름": "넘어짐", "지속턴": 1})
    flow.턴_시작_처리(전투상태, 키놀)  # 지속턴 만료
    assert all(HP전[p["이름"]] == p["현재HP"] for p in 아군)
    assert not any("'넘어짐' 해제" in str(x.get("비고")) for x in 전투상태["로그"])


# ------------------------------------------------------- 공중에뜸 -> 넘어짐 (사용자 지정 2026-10-15)


def _내성_굴리면_실패(monkeypatch):
    def 안됨(*a, **k):
        raise AssertionError("공중에뜸이 끝난 넘어짐은 내성굴림을 하지 않는다")

    monkeypatch.setattr(dice_utils, "내성_굴림", 안됨)


def test_공중에뜸이_지속턴으로_끝나면_내성없이_넘어짐_1턴(키놀전장, monkeypatch):
    # 공중에뜸 자체의 규칙 - 아군과 적 모두
    전투상태, 키놀, 아군 = 키놀전장
    _내성_굴리면_실패(monkeypatch)
    for p in (아군[0], 키놀):
        p["상태이상"].append({"이름": "공중에뜸", "지속턴": 1})
        flow.턴_시작_처리(전투상태, p)
        assert [i["이름"] for i in p["상태이상"]] == ["넘어짐"], p["이름"]
        assert p["상태이상"][0]["지속턴"] == 1
    flow.턴_시작_처리(전투상태, 아군[0])  # 다음 자기 턴 시작에 풀린다
    assert 아군[0]["상태이상"] == []
    문장 = "'공중에뜸'이 끝나 '넘어짐' 상태이상 부여"
    assert [x["대상"] for x in 전투상태["로그"] if x.get("비고") == 문장] == [
        아군[0]["이름"],
        키놀["이름"],
    ]


def test_공중에뜸이_풀려도_넘어짐에_면역이면_넘어지지_않는다(키놀전장, monkeypatch):

    전투상태, 키놀, 아군 = 키놀전장
    monkeypatch.setattr(
        status, "상태이상_면역", lambda 전투상태, p, 이름: 이름 == "넘어짐"
    )
    키놀["상태이상"].append({"이름": "공중에뜸", "지속턴": 1})
    flow.턴_시작_처리(전투상태, 키놀)
    assert 키놀["상태이상"] == []


def test_공중에뜸에서_떨어진_키놀은_그_차례에_기상번개를_쓴다(키놀전장, monkeypatch):

    전투상태, 키놀, 아군 = 키놀전장
    _기상번개_준비(전투상태, 키놀, monkeypatch, 내성성공=True)
    키놀["상태이상"] = [{"이름": "공중에뜸", "지속턴": 1}]
    flow.턴_시작_처리(전투상태, 키놀)
    결과 = monster_actions.몬스터_턴_실행(전투상태, 키놀)
    assert 결과["패턴"] == "기상번개"
    assert 키놀["상태이상"] == []


def test_굴_구위시의_기상_충격파는_넘어짐이_풀릴_때만_터진다():
    # 사용자 지정 2026-10-15: 공중에뜸 해제시는 뺐다 - 공중에뜸 -> 넘어짐 -> 넘어짐 해제에 한 번
    rng.시드(5)
    상태 = support.새게임()
    gf.전투_시작(상태, ["굴 구위시"], 레벨=5, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    for p in 전투상태["참가자"]:
        p["현재HP"] = 999
    굴 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
    굴["상태이상"] = [{"이름": "공중에뜸", "지속턴": 1}]

    def 터진수():
        return sum(
            "'기상 충격파' 특성 발동" in str(x.get("비고")) for x in 전투상태["로그"]
        )

    flow.턴_시작_처리(전투상태, 굴)
    assert 터진수() == 0 and [i["이름"] for i in 굴["상태이상"]] == ["넘어짐"]
    flow.턴_시작_처리(전투상태, 굴)
    # 한 번 터지면 살아 있는 아군마다 한 줄
    assert 터진수() == sum(p["진영"] == "아군" for p in 전투상태["참가자"])


# ------------------------------------------------------------- 펜릴 (사용자 지정 2026-10-13)


@pytest.fixture
def 펜릴전장():
    """펜릴 1마리 대 4인 파티, 모두 HP 넉넉히."""
    rng.시드(5)
    상태 = support.새게임(
        [("", "귀검사"), ("", "격투가"), ("", "거너"), ("", "마법사")]
    )
    gf.전투_시작(상태, ["펜릴"], 레벨=4, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    펜릴 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
    아군 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "아군"),
        key=lambda p: p["대형위치"],
    )
    for p in 전투상태["참가자"]:
        p["현재HP"] = 999
    return 전투상태, 펜릴, 아군


def _몬스터_한턴(전투상태, 몬스터, monkeypatch, 패턴, 대상=None):
    """몬스터가 턴을 시작하고(턴 시작 처리) 이 패턴으로 행동한 뒤 턴을 끝낸다."""
    from game.system import monster_ai

    monkeypatch.setattr(monster_ai, "행동_선택", lambda p: 패턴)
    if 대상 is not None:
        monkeypatch.setattr(monster_ai, "타겟_선택", lambda *a, **k: 대상)
    전투상태["현재턴"] = 전투상태["참가자"].index(몬스터)
    flow.턴_시작_처리(전투상태, 몬스터)
    monster_actions.몬스터_턴_실행(전투상태, 몬스터)
    flow.턴_종료_처리(전투상태, 몬스터)


def _이름들(참가자, 상태이상):
    return [i for i in 참가자["상태이상"] if i["이름"] == 상태이상]


def test_종족_루가루는_방어력_마이너스1이라_맞을_때마다_1을_더_받는다():
    # 사용자 지정 2026-10-15 - 종족:루가루 특성에 방어력 -1(루가루 계열 다섯 종 모두)
    상태 = support.새게임()
    gf.전투_시작(상태, ["루가루"], 레벨=3, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    적 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
    assert stats.유효_방어력(전투상태, 적) == -1
    HP전 = 적["현재HP"]
    damage.피해_적용(전투상태, 적, 3)
    assert HP전 - 적["현재HP"] == 4


def test_종족_좀비는_AC_마이너스1_방어력_마이너스1():
    # 사용자 지정 2026-10-15 - 종족:좀비 특성에 AC -1, 방어력 -1(좀비 네 종 모두)
    from game.system.combat import traits

    상태 = support.새게임()
    gf.전투_시작(상태, ["포레스트 좀비"], 레벨=5, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    적 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
    assert traits.특성_수치(전투상태, 적, "AC") == -1
    assert stats.유효_방어력(전투상태, 적) == -1


def _좀비전장(몬스터="포레스트 좀비"):
    rng.시드(4)
    상태 = support.새게임()
    gf.전투_시작(상태, [몬스터], 레벨=5, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    for p in 전투상태["참가자"]:
        p["현재HP"] = 999
    좀비 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
    아군 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "아군"),
        key=lambda p: p["대형위치"],
    )
    return 전투상태, 좀비, 아군


@pytest.mark.parametrize("내성성공", [False, True])
def test_좀비_공격이_명중하면_건강내성_실패시_출혈_1턴(내성성공, monkeypatch):

    전투상태, 좀비, 아군 = _좀비전장()
    support.주사위고정(monkeypatch, 15)  # 명중
    monkeypatch.setattr(
        dice_utils, "내성_굴림", lambda 보정치, 난이도, **kw: (내성성공, 난이도)
    )
    할퀴기 = gf.몬스터목록["포레스트 좀비"]["패턴"][1]
    monkeypatch.setattr(
        __import__("game.system.monster_ai", fromlist=["x"]),
        "행동_선택",
        lambda p: 할퀴기,
    )
    monkeypatch.setattr(
        __import__("game.system.monster_ai", fromlist=["x"]),
        "타겟_선택",
        lambda *a, **k: 아군[0],
    )
    monster_actions.몬스터_턴_실행(전투상태, 좀비)
    출혈 = [i for i in 아군[0]["상태이상"] if i["이름"] == "출혈"]
    if 내성성공:
        assert not 출혈
    else:
        assert len(출혈) == 1 and 출혈[0]["지속턴"] == 1


def test_좀비는_출혈인_아군을_어그로_비중으로_우선_노린다(monkeypatch):
    from game.system import monster_ai

    전투상태, 좀비, 아군 = _좀비전장()
    아군[1]["상태이상"].append({"이름": "출혈", "지속턴": 2})
    아군[3]["상태이상"].append({"이름": "출혈", "지속턴": 2})
    본것 = []
    원래 = random.choices

    def 기록(목록, weights=None, k=1):
        본것.append([p["이름"] for p in 목록])
        return 원래(목록, weights=weights, k=k)

    monkeypatch.setattr(rng.대상, "choices", 기록)
    할퀴기 = gf.몬스터목록["포레스트 좀비"]["패턴"][1]
    monkeypatch.setattr(monster_ai, "행동_선택", lambda p: 할퀴기)
    monster_actions.몬스터_턴_실행(전투상태, 좀비)
    assert len(본것) == 1 and sorted(본것[0]) == sorted(
        [아군[1]["이름"], 아군[3]["이름"]]
    )
    # 출혈인 아군이 없으면 전원 중에서
    본것.clear()
    for p in 아군:
        p["상태이상"] = []
    monster_actions.몬스터_턴_실행(전투상태, 좀비)
    assert 본것 and len(본것[0]) == len(아군)


def _패턴_로그(전투상태, 시작, 몬스터, 이름):
    return [
        x
        for x in 전투상태["로그"][시작:]
        if x.get("패턴") == 이름 and x.get("공격자") == 몬스터["이름"]
    ]


def test_달려들기가_명중하면_턴_끝에_물어뜯고_다음_턴은_패턴_대신_그_대상에게_피니쉬(
    펜릴전장, monkeypatch
):
    전투상태, 펜릴, 아군 = 펜릴전장
    support.주사위고정(monkeypatch, 15)  # 명중, 치명타 아님
    monkeypatch.setattr(
        dice_utils, "내성_굴림", lambda 보정치, 난이도, **kw: (True, 난이도)
    )
    패턴 = gf.몬스터목록["펜릴"]["패턴"]
    시작 = len(전투상태["로그"])
    _몬스터_한턴(전투상태, 펜릴, monkeypatch, 패턴[5], 대상=아군[2])
    물기 = _패턴_로그(전투상태, 시작, 펜릴, "물어뜯기")
    assert len(물기) == 1 and 물기[0]["대상"] == 아군[2]["이름"]  # 턴 끝, 같은 대상
    assert len(_이름들(아군[2], "들러붙음")) == 1
    assert all(not _이름들(p, "들러붙음") for p in 아군 if p is not 아군[2])

    # 다음 펜릴 턴: 1~6번 패턴 대신 들러붙은 대상(무작위 대상이 아니라)에게 확정 치명타 피니쉬!
    시작 = len(전투상태["로그"])
    _몬스터_한턴(전투상태, 펜릴, monkeypatch, 패턴[1], 대상=아군[0])
    피니쉬 = _패턴_로그(전투상태, 시작, 펜릴, "피니쉬!")
    assert len(피니쉬) == 1 and 피니쉬[0]["대상"] == 아군[2]["이름"]
    [타격] = 피니쉬[0]["타격"]
    assert 타격["판정"]["성공"] and 타격["판정"]["치명타"]
    assert not _패턴_로그(전투상태, 시작, 펜릴, "두번 할퀴기")
    assert not _패턴_로그(전투상태, 시작, 펜릴, "물어뜯기")
    assert not _이름들(아군[2], "들러붙음")

    # 그 다음 턴은 다시 1~6번 패턴
    시작 = len(전투상태["로그"])
    _몬스터_한턴(전투상태, 펜릴, monkeypatch, 패턴[1], 대상=아군[0])
    assert not _패턴_로그(전투상태, 시작, 펜릴, "피니쉬!")
    assert _패턴_로그(전투상태, 시작, 펜릴, "두번 할퀴기")


def test_피니쉬는_명중굴림을_하고_빗나가면_피해없이_들러붙음만_풀린다(
    펜릴전장, monkeypatch
):
    # 사용자 지정 2026-10-15: 반드시 명중 -> 근력판정 명중굴림(명중하면 확정 치명타)
    전투상태, 펜릴, 아군 = 펜릴전장
    아군[2]["상태이상"].append({"이름": "들러붙음", "시전자id": 펜릴["id"]})
    support.주사위고정(monkeypatch, 2)  # 빗나감(펌블 아님)
    HP전 = 아군[2]["현재HP"]
    시작 = len(전투상태["로그"])
    _몬스터_한턴(
        전투상태, 펜릴, monkeypatch, gf.몬스터목록["펜릴"]["패턴"][1], 대상=아군[0]
    )
    [피니쉬] = _패턴_로그(전투상태, 시작, 펜릴, "피니쉬!")
    [타격] = 피니쉬["타격"]
    assert 타격["판정"]["명중결과"] is not None and not 타격["판정"]["성공"]
    assert 아군[2]["현재HP"] == HP전
    assert not _이름들(아군[2], "들러붙음")


def test_펜릴이_행동불가면_피니쉬_없이_들러붙음만_사라진다(펜릴전장, monkeypatch):
    전투상태, 펜릴, 아군 = 펜릴전장
    support.주사위고정(monkeypatch, 15)
    monkeypatch.setattr(
        dice_utils, "내성_굴림", lambda 보정치, 난이도, **kw: (True, 난이도)
    )
    패턴 = gf.몬스터목록["펜릴"]["패턴"]
    _몬스터_한턴(전투상태, 펜릴, monkeypatch, 패턴[5], 대상=아군[2])
    assert _이름들(아군[2], "들러붙음")
    펜릴["상태이상"].append({"이름": "기절", "지속턴": 3})
    시작 = len(전투상태["로그"])
    _몬스터_한턴(전투상태, 펜릴, monkeypatch, 패턴[1], 대상=아군[0])
    assert not _패턴_로그(전투상태, 시작, 펜릴, "피니쉬!")
    assert not _이름들(아군[2], "들러붙음")


def test_루가루의_달려들기는_명중해도_물어뜯지_않는다(monkeypatch):
    rng.시드(5)
    상태 = support.새게임()
    gf.전투_시작(상태, ["루가루"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    루가루 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
    아군 = [p for p in 전투상태["참가자"] if p["진영"] == "아군"]
    for p in 전투상태["참가자"]:
        p["현재HP"] = 999
    support.주사위고정(monkeypatch, 15)
    시작 = len(전투상태["로그"])
    _몬스터_한턴(
        전투상태, 루가루, monkeypatch, gf.몬스터목록["루가루"]["패턴"][5], 대상=아군[0]
    )
    [달려] = _패턴_로그(전투상태, 시작, 루가루, "달려들기")
    assert 달려["타격"][0]["판정"]["성공"]
    assert not _패턴_로그(전투상태, 시작, 루가루, "물어뜯기")
    assert not any(_이름들(p, "들러붙음") for p in 아군)


def test_달려들기가_빗나가면_물지_않는다(펜릴전장, monkeypatch):
    전투상태, 펜릴, 아군 = 펜릴전장
    support.주사위고정(monkeypatch, 1)  # 자동 실패
    시작 = len(전투상태["로그"])
    _몬스터_한턴(
        전투상태, 펜릴, monkeypatch, gf.몬스터목록["펜릴"]["패턴"][6], 대상=아군[0]
    )
    assert not [x for x in 전투상태["로그"][시작:] if x.get("패턴") == "물어뜯기"]


def test_독샘의_주인_펜릴의_공격이_명중하면_내성_없이_3턴_중독(펜릴전장, monkeypatch):
    전투상태, 펜릴, 아군 = 펜릴전장
    support.주사위고정(monkeypatch, 15)
    내성들 = []
    monkeypatch.setattr(
        dice_utils,
        "내성_굴림",
        lambda 보정치, 난이도, **kw: 내성들.append(난이도) or (True, 난이도),
    )
    _몬스터_한턴(
        전투상태, 펜릴, monkeypatch, gf.몬스터목록["펜릴"]["패턴"][1], 대상=아군[0]
    )
    중독 = _이름들(아군[0], "중독")
    assert len(중독) == 2 and all(
        i["지속턴"] == 3 for i in 중독
    )  # 두 번 할퀴어 둘 다 명중
    assert 내성들 == []  # 내성굴림 없음


def _펜릴_때리기(전투상태, 아군, 펜릴, monkeypatch, 굴림):
    monkeypatch.setattr(rng.확률, "random", lambda: 굴림)
    전투상태["현재턴"] = 전투상태["참가자"].index(아군[0])
    시작 = len(전투상태["로그"])
    attacks.일반공격_실행(전투상태, 아군[0], 펜릴)
    return 전투상태["로그"][시작:]


@pytest.mark.parametrize(
    "굴림, 독구름, 블러드", [(0.1, True, True), (0.3, False, True), (0.6, False, False)]
)
def test_독샘의_주인_피격시_20퍼센트_독구름_50퍼센트_포이즌_블러드(
    펜릴전장, monkeypatch, 굴림, 독구름, 블러드
):
    전투상태, 펜릴, 아군 = 펜릴전장
    support.주사위고정(monkeypatch, 15)  # 아군 공격 명중
    난이도들 = []
    monkeypatch.setattr(
        dice_utils,
        "내성_굴림",
        lambda 보정치, 난이도, **kw: 난이도들.append(난이도) or (False, 난이도),
    )
    monkeypatch.setattr(stats, "유효_방어력", lambda 전, p: 999 if p is 펜릴 else 0)
    HP전 = 펜릴["현재HP"]
    로그 = _펜릴_때리기(전투상태, 아군, 펜릴, monkeypatch, 굴림)
    assert 펜릴["현재HP"] == HP전  # 명중했지만 피해 0 - 그래도 발동한다
    중독 = {p["이름"]: len(_이름들(p, "중독")) for p in 아군}
    기대 = {p["이름"]: (1 if 독구름 else 0) for p in 아군}
    if 블러드:
        기대[아군[0]["이름"]] += 1
    assert 중독 == 기대
    assert all(i["지속턴"] == 3 for p in 아군 for i in _이름들(p, "중독"))
    assert set(난이도들) <= {12}
    비고 = " ".join(str(x.get("비고", "")) for x in 로그)
    assert ("독구름" in 비고) is 독구름 and ("포이즌 블러드" in 비고) is 블러드


def test_독샘의_주인은_지속피해로는_발동하지_않는다(펜릴전장, monkeypatch):
    전투상태, 펜릴, 아군 = 펜릴전장
    monkeypatch.setattr(rng.확률, "random", lambda: 0.0)
    펜릴["상태이상"].append({"이름": "출혈", "지속턴": 3})
    시작 = len(전투상태["로그"])
    flow.턴_종료_처리(전투상태, 펜릴)
    비고 = " ".join(str(x.get("비고", "")) for x in 전투상태["로그"][시작:])
    assert "독구름" not in 비고 and "포이즌 블러드" not in 비고


# ------------------------------------------------------------- 타우 포효/대포효 (사용자 지정 2026-10-14)


@pytest.fixture
def 샤우타전장():
    """샤우타 1마리 대 4인 파티. 모두 HP를 넉넉히 둔다."""
    rng.시드(5)
    상태 = support.새게임(
        [("", "귀검사"), ("", "격투가"), ("", "거너"), ("", "마법사")]
    )
    gf.전투_시작(상태, ["타우킹 샤우타"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    샤우타 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
    아군 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "아군"),
        key=lambda p: p["대형위치"],
    )
    for p in 전투상태["참가자"]:
        p["현재HP"] = 999
    return 전투상태, 샤우타, 아군


@pytest.mark.parametrize("번호", [5, 6], ids=["포효", "대포효"])
def test_포효는_매력내성_성공시_데미지_절반_대포효는_기절내성을_따로_모두_굴린다(
    샤우타전장, monkeypatch, 번호
):
    전투상태, 샤우타, 아군 = 샤우타전장
    from game.system import monster_ai

    패턴 = gf.몬스터목록["타우킹 샤우타"]["패턴"][번호]
    support.주사위고정(monkeypatch, 3)
    데미지DC = stats.몬스터_수식값(전투상태, 샤우타, "10+매력보정치")
    기절DC = stats.몬스터_수식값(전투상태, 샤우타, "15+매력보정치")
    # 내성굴림은 대상 목록 순서로 한다. 데미지 내성: 앞의 둘 실패, 뒤의 둘 성공.
    # 기절 내성: 실패/성공을 번갈아 - 데미지 내성 결과와 엇갈리게 둔다
    결과들 = {데미지DC: [False, False, True, True], 기절DC: [False, True, False, True]}
    기절굴림 = []

    def 내성(보정치, 난이도, **kw):
        if 난이도 == 기절DC:
            기절굴림.append(난이도)
        return 결과들[난이도].pop(0), 난이도

    monkeypatch.setattr(dice_utils, "내성_굴림", 내성)
    monkeypatch.setattr(monster_ai, "행동_선택", lambda p: 패턴)
    monkeypatch.setattr(monster_ai, "타겟_선택", lambda *a, **k: 아군[0])
    HP전 = {p["이름"]: p["현재HP"] for p in 아군}
    전투상태["공격연출"].clear()
    결과 = monster_actions.몬스터_턴_실행(전투상태, 샤우타)
    # 내성에 성공해도 절반을 맞으므로 모두 연출이 뜬다(사용자 지정 2026-10-14)
    assert sorted(e["대상id"] for e in 전투상태["공격연출"]) == sorted(
        p["id"] for p in 아군
    )
    assert {e["종류"] for e in 전투상태["공격연출"]} == {"마법:무"}

    원래피해 = stats.몬스터_수식값(
        전투상태, 샤우타, 패턴["실패시데미지"]
    ) + monster_actions.몬스터_데미지보너스(전투상태, 샤우타)

    def 기대(값, p):
        return damage.최종피해_계산(
            값, stats.유효_방어력(전투상태, p), stats.유효_보호률(전투상태, p)
        )

    assert 결과["난이도"] == 데미지DC
    assert [t["내성"] for t in 결과["타격"]] == ["실패", "실패", "성공", "성공"]
    순서 = [t["대상"] for t in 결과["타격"]]
    assert set(순서) == {p["이름"] for p in 아군}
    for p in 아군:
        k = 순서.index(p["이름"])
        assert HP전[p["이름"]] - p["현재HP"] == 기대(
            원래피해 * (1 if k < 2 else 0.5), p
        )
        기절 = any(s["이름"] == "기절" for s in p.get("상태이상", []))
        assert 기절 is (번호 == 6 and k in (0, 2)), p["이름"]
    assert len(기절굴림) == (4 if 번호 == 6 else 0)


# ------------------------------------------- 몬스터 공격 데미지의 능력치 보정치 (사용자 지정 2026-10-14)


@pytest.mark.parametrize("식", ["1d4+근력보정치", "1d4+보정치"])
def test_몬스터_공격_데미지의_근력보정치는_버프_디버프를_반영한다(monkeypatch, 식):
    """ "근력보정치"가 몬스터 원본이 아니라 버프/디버프가 반영된 근력으로 계산된다 -
    근력판정의 "보정치"와 같은 값이어야 한다(그전에는 원본 근력이라 디버프를 무시했다)."""
    from game.system import monster_ai

    rng.시드(1)
    상태 = support.새게임([("", "귀검사")])
    gf.전투_시작(상태, ["타우 아미"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    아미 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
    대상 = next(p for p in 전투상태["참가자"] if p["진영"] == "아군")
    대상["현재HP"] = 999
    원래보정 = (아미["원본"]["근력"] - 10) // 2
    아미.setdefault("디버프", []).append({"이름": "근력감소", "지속턴": 3, "중첩": 4})
    보정 = stats.유효_능력치_보정치(전투상태, 아미, "근력")
    assert 보정 == 원래보정 - 2  # 근력 -4

    패턴 = {
        "이름": "시험 공격",
        "타입": "공격패턴",
        "타겟": "적단일",
        "속성": "무속성",
        "데미지": 식,
        "데미지보너스": 0,
        "명중률": "근력판정",
        "명중보너스": 0,
        "공격횟수": 1,
        "각공격명중굴림": False,
        "효과": None,
        "조건부효과": None,
    }
    monkeypatch.setattr(
        damage, "명중_판정", lambda *a, **k: {"성공": True, "치명타": False}
    )
    monkeypatch.setattr(monster_ai, "행동_선택", lambda p: 패턴)
    monkeypatch.setattr(monster_ai, "타겟_선택", lambda *a, **k: 대상)
    support.주사위고정(monkeypatch, 4)  # 1d4 = 4
    결과 = monster_actions.몬스터_턴_실행(전투상태, 아미)

    원래피해 = 4 + 보정 + monster_actions.몬스터_데미지보너스(전투상태, 아미)
    기대 = damage.최종피해_계산(
        원래피해, stats.유효_방어력(전투상태, 대상), stats.유효_보호률(전투상태, 대상)
    )
    assert 999 - 대상["현재HP"] == 기대, 결과


# ------------------------------------------------- 타우 능력치·특성, 돌연변이:거대화 (사용자 지정 2026-10-14)


def _비스트전장():
    rng.시드(3)
    상태 = support.새게임([("", "귀검사")])
    gf.전투_시작(상태, ["타우 비스트"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    비스트 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
    return 전투상태, 비스트


def test_거대화는_종족특성까지_더한_최대HP를_2배로_한다():
    전투상태, 비스트 = _비스트전장()
    원본 = 비스트["원본"]
    종족보너스 = 원본["레벨"] * ((원본["건강"] - 10) // 2)  # 종족:타우 레벨x건강보정치
    기대 = 2 * (비스트["기본최대HP"] + 종족보너스)
    assert stats.유효_최대HP(전투상태, 비스트) == 기대
    assert 비스트["현재HP"] == 기대  # 전투 시작 HP도 2배


def test_거대화는_첫_차례는_쉬고_짝수_차례에만_행동하며_쉬는_차례에도_기절이_줄어든다(
    monkeypatch,
):
    from game.system import monster_ai

    전투상태, 비스트 = _비스트전장()
    아군 = next(p for p in 전투상태["참가자"] if p["진영"] == "아군")
    아군["현재HP"] = 999
    패턴 = gf.몬스터목록["타우 비스트"]["패턴"][1]  # 주먹 내려찍기
    monkeypatch.setattr(monster_ai, "행동_선택", lambda p: 패턴)
    monkeypatch.setattr(monster_ai, "타겟_선택", lambda *a, **k: 아군)
    행동 = []
    for 차례 in range(1, 7):
        if 차례 == 3:  # 쉬는 차례(3)와 행동 차례(4)를 걸치는 기절 2턴
            비스트.setdefault("상태이상", []).append({"이름": "기절", "지속턴": 2})
        flow.턴_시작_처리(전투상태, 비스트)
        결과 = monster_actions.몬스터_턴_실행(전투상태, 비스트)
        행동.append(결과.get("패턴") or 결과.get("행동"))
    # 3번째(쉬는 차례 - 기절이 먼저 기록된다)에 기절 2 -> 1, 4번째 시작에 1 -> 0으로 풀려
    # 4번째에 행동한다
    assert 행동 == [
        "거대화로 쉼",
        "주먹 내려찍기",
        "행동불가 상태로 무행동",
        "주먹 내려찍기",
        "거대화로 쉼",
        "주먹 내려찍기",
    ]


# ------------------------------------------------- 특수패턴:샤우타 (사용자 지정 2026-10-14)


def _샤우타_차례(전투상태, 샤우타):

    flow.턴_시작_처리(전투상태, 샤우타)
    return monster_actions.몬스터_턴_실행(전투상태, 샤우타)


@pytest.mark.parametrize("시드", range(6))
def test_기절한_적이_있으면_샤우타는_그중_한_명에게_점프_도끼_내려찍기를_한_번_쓴다(
    샤우타전장, 시드
):
    전투상태, 샤우타, 아군 = 샤우타전장
    rng.시드(시드)
    기절 = {아군[1]["이름"], 아군[3]["이름"]}
    for p in (아군[1], 아군[3]):
        p.setdefault("상태이상", []).append({"이름": "기절", "지속턴": 3})
    결과 = _샤우타_차례(전투상태, 샤우타)
    assert 결과["패턴"] == "점프 도끼 내려찍기"
    assert len(결과["타격"]) == 1 and 결과["대상"] in 기절


def test_기절한_적이_없으면_샤우타는_평소처럼_1_6번_패턴을_쓴다(
    샤우타전장, monkeypatch
):
    from game.system import monster_ai

    전투상태, 샤우타, 아군 = 샤우타전장
    아군[0].setdefault("상태이상", []).append({"이름": "공중에뜸", "지속턴": 3})
    고른 = []
    원래 = monster_ai.행동_선택
    monkeypatch.setattr(monster_ai, "행동_선택", lambda p: 고른.append(1) or 원래(p))
    결과 = _샤우타_차례(전투상태, 샤우타)
    assert 고른 == [1] and 결과.get("패턴") != "점프 도끼 내려찍기"


def test_타우의_왕은_샤우타의_방어력과_데미지보너스를_1씩_올린다(샤우타전장):

    전투상태, 샤우타, _ = 샤우타전장
    assert (
        stats.유효_방어력(전투상태, 샤우타) == (샤우타["원본"].get("방어력") or 0) + 1
    )
    원래 = list(샤우타["원본"]["특성"])
    보너스 = monster_actions.몬스터_데미지보너스(전투상태, 샤우타)
    샤우타["원본"] = dict(샤우타["원본"], 특성=[x for x in 원래 if x != "타우의 왕"])
    assert monster_actions.몬스터_데미지보너스(전투상태, 샤우타) == 보너스 - 1


# -------------------------------------------- 차수만큼 패턴 반복 (사용자 지정 2026-10-14)


def _차수전장(몬스터들, 차수):
    """몬스터들 대 4인 파티, 모두 HP 넉넉히(반응으로 몬스터가 쓰러지지 않게 몬스터도)."""
    rng.시드(5)
    상태 = support.새게임(
        [("", "귀검사"), ("", "격투가"), ("", "거너"), ("", "마법사")]
    )
    gf.전투_시작(상태, 몬스터들, 레벨=4, 차수=차수)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    적 = [p for p in 전투상태["참가자"] if p["진영"] == "적"]
    아군 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "아군"),
        key=lambda p: p["대형위치"],
    )
    for p in 전투상태["참가자"]:
        p["현재HP"] = 999
    return 전투상태, 적, 아군


def _굴림_기록(monkeypatch, 패턴들):
    """monster_ai.행동_선택(1~6 굴림)을 패턴들 순서로 돌려주게 하고, 굴린 횟수를 담을 리스트를 준다."""
    from game.system import monster_ai

    굴림 = []

    def 선택(p):
        굴림.append(p["이름"])
        return 패턴들[(len(굴림) - 1) % len(패턴들)]

    monkeypatch.setattr(monster_ai, "행동_선택", 선택)
    return 굴림


def _대상_차례로(monkeypatch, 대상들):
    from game.system import monster_ai

    남은 = list(대상들)
    monkeypatch.setattr(
        monster_ai,
        "타겟_선택",
        lambda *a, **k: 남은.pop(0) if len(남은) > 1 else 남은[0],
    )


def _한턴(전투상태, 몬스터):

    전투상태["현재턴"] = 전투상태["참가자"].index(몬스터)
    flow.턴_시작_처리(전투상태, 몬스터)
    monster_actions.몬스터_턴_실행(전투상태, 몬스터)
    flow.턴_종료_처리(전투상태, 몬스터)


def _쓴_패턴(전투상태, 시작, 몬스터):
    return [
        (x["패턴"], x["대상"])
        for x in 전투상태["로그"][시작:]
        if x.get("종류") == "타격" and x.get("공격자") == 몬스터["이름"]
    ]


@pytest.mark.parametrize("차수", [1, 2, 3])
def test_몬스터는_한_턴에_차수만큼_패턴을_새로_굴려_각각_쓴다(monkeypatch, 차수):
    전투상태, [루가루], 아군 = _차수전장(["루가루"], 차수)
    패턴 = gf.몬스터목록["루가루"]["패턴"]
    굴림 = _굴림_기록(monkeypatch, [패턴[1], 패턴[5]])
    _대상_차례로(monkeypatch, [아군[0]])
    시작 = len(전투상태["로그"])
    _한턴(전투상태, 루가루)
    assert len(굴림) == 차수
    이름 = [p for p, _ in _쓴_패턴(전투상태, 시작, 루가루)]
    assert 이름 == (["두번 할퀴기", "달려들기"] * 2)[:차수]


def test_대체행동은_기본으로_한_턴에_한_번만_쓰고_나머지는_패턴을_굴린다(monkeypatch):
    전투상태, [샤우타], 아군 = _차수전장(["타우킹 샤우타"], 2)
    아군[1]["상태이상"].append({"이름": "기절", "지속턴": 3})
    도끼 = gf.몬스터목록["타우킹 샤우타"]["패턴"][1]
    굴림 = _굴림_기록(monkeypatch, [도끼])
    _대상_차례로(monkeypatch, [아군[0]])
    시작 = len(전투상태["로그"])
    _한턴(전투상태, 샤우타)
    assert _쓴_패턴(전투상태, 시작, 샤우타) == [
        ("점프 도끼 내려찍기", 아군[1]["이름"]),
        (도끼["이름"], 아군[0]["이름"]),
    ]
    assert len(굴림) == 1


@pytest.mark.parametrize("횟수, 점프, 굴림수", [(2, 2, 1), ("전부", 3, 0)])
def test_대체횟수는_특수패턴마다_2회나_전부로_정할_수_있다(
    monkeypatch, 횟수, 점프, 굴림수
):
    전투상태, [샤우타], 아군 = _차수전장(["타우킹 샤우타"], 3)
    정의 = dict(전투상태["특성정의"]["특수패턴:샤우타"])
    정의["대체행동"] = {**정의["대체행동"], "대체횟수": 횟수}
    전투상태["특성정의"] = {**전투상태["특성정의"], "특수패턴:샤우타": 정의}
    아군[1]["상태이상"].append({"이름": "기절", "지속턴": 3})
    도끼 = gf.몬스터목록["타우킹 샤우타"]["패턴"][1]
    굴림 = _굴림_기록(monkeypatch, [도끼])
    _대상_차례로(monkeypatch, [아군[0]])
    시작 = len(전투상태["로그"])
    _한턴(전투상태, 샤우타)
    쓴 = [p for p, _ in _쓴_패턴(전투상태, 시작, 샤우타)]
    assert 쓴 == ["점프 도끼 내려찍기"] * 점프 + [도끼["이름"]] * 굴림수
    assert len(굴림) == 굴림수


def test_2차수_펜릴이_두_번_물면_나중에_문_적만_들러붙고_다음_턴_피니쉬도_그_적에게(
    monkeypatch,
):
    전투상태, [펜릴], 아군 = _차수전장(["펜릴"], 2)
    support.주사위고정(monkeypatch, 15)  # 명중, 치명타 아님
    monkeypatch.setattr(
        dice_utils, "내성_굴림", lambda 보정치, 난이도, **kw: (True, 난이도)
    )
    패턴 = gf.몬스터목록["펜릴"]["패턴"]
    _굴림_기록(monkeypatch, [패턴[5]])
    _대상_차례로(monkeypatch, [아군[0], 아군[2]])
    시작 = len(전투상태["로그"])
    _한턴(전투상태, 펜릴)
    물기 = [대상 for p, 대상 in _쓴_패턴(전투상태, 시작, 펜릴) if p == "물어뜯기"]
    assert 물기 == [아군[0]["이름"], 아군[2]["이름"]]  # 턴 끝에 명중한 순서대로
    붙음 = [p["이름"] for p in 아군 if _이름들(p, "들러붙음")]
    assert 붙음 == [아군[2]["이름"]]  # 나중에 문 적만

    굴림 = _굴림_기록(monkeypatch, [패턴[1]])
    _대상_차례로(monkeypatch, [아군[0]])
    시작 = len(전투상태["로그"])
    _한턴(전투상태, 펜릴)
    assert _쓴_패턴(전투상태, 시작, 펜릴) == [
        ("피니쉬!", 아군[2]["이름"]),
        ("두번 할퀴기", 아군[0]["이름"]),
    ]
    assert len(굴림) == 1
    assert not any(_이름들(p, "들러붙음") for p in 아군)


def test_거대화는_쉬는_차례에_통째로_쉬고_행동_차례에_차수만큼_움직인다(monkeypatch):
    전투상태, [비스트], 아군 = _차수전장(["타우 비스트"], 2)
    굴림 = _굴림_기록(monkeypatch, [gf.몬스터목록["타우 비스트"]["패턴"][1]])
    _대상_차례로(monkeypatch, [아군[0]])
    _한턴(전투상태, 비스트)
    assert len(굴림) == 0
    _한턴(전투상태, 비스트)
    assert len(굴림) == 2


# ---------------------------------- 케라하·비노슈 주문영창과 감옥 (사용자 지정 2026-10-14)


def _마녀전장(이름):
    """마녀 1마리 대 4인 파티(귀검사/격투가/거너/마법사), 모두 HP 넉넉히."""
    전투상태, [마녀], 아군 = _차수전장([이름], 1)
    return 전투상태, 마녀, 아군


def _문장들(전투상태, 시작):
    return [z for x in 전투상태["로그"][시작:] for z in gf.로그_문장들(x)]


def _감옥들(전투상태):
    return [p for p in 전투상태["참가자"] if p.get("감옥") and p["생존"]]


@pytest.mark.parametrize(
    "몬스터, 시전", [("결빙의 케라하", "블리자드"), ("화염의 비노슈", "메테오")]
)
def test_영창_패턴은_주문영창만_되고_다음_턴에_패턴_대신_시전한다(
    monkeypatch, 몬스터, 시전
):
    전투상태, 마녀, 아군 = _마녀전장(몬스터)
    패턴 = gf.몬스터목록[몬스터]["패턴"]
    _굴림_기록(monkeypatch, [패턴[6]])
    _대상_차례로(monkeypatch, [아군[1]])
    HP전 = [p["현재HP"] for p in 아군]
    시작 = len(전투상태["로그"])
    _한턴(전투상태, 마녀)
    assert _이름들(마녀, "주문영창")
    assert [p["현재HP"] for p in 아군] == HP전  # 영창하는 턴에는 공격하지 않는다
    줄 = _문장들(전투상태, 시작)
    assert 줄[:2] == [
        f"{마녀['이름']}의 {시전}!",
        f"{마녀['이름']}는 주문영창을 시작했다!",  # 하·슈 - 받침 없음
    ], 줄

    굴림 = _굴림_기록(monkeypatch, [패턴[1]])
    시작 = len(전투상태["로그"])
    _한턴(전투상태, 마녀)
    assert len(굴림) == 0  # 패턴 대신 시전
    assert {p for p, _ in _쓴_패턴(전투상태, 시작, 마녀)} == {시전}
    assert f"{마녀['이름']}의 {시전}!!" in _문장들(전투상태, 시작)
    assert not _이름들(마녀, "주문영창")


@pytest.mark.parametrize("상태", ["기절", "침묵"])
def test_주문영창은_행동불가형_상태이상이나_침묵에_걸리면_풀린다(monkeypatch, 상태):
    from game.system.skill import skill_grant

    전투상태, 마녀, 아군 = _마녀전장("결빙의 케라하")
    if (
        상태 not in 전투상태["상태이상정의"]
    ):  # 침묵은 아직 데이터에 없다 - 이름으로 판정한다
        전투상태["상태이상정의"] = {**전투상태["상태이상정의"], 상태: {"효과": {}}}
    패턴 = gf.몬스터목록["결빙의 케라하"]["패턴"]
    _굴림_기록(monkeypatch, [패턴[6]])
    _한턴(전투상태, 마녀)
    assert _이름들(마녀, "주문영창")
    skill_grant.상태이상_부여(전투상태, 마녀, 상태, 1)
    assert not _이름들(마녀, "주문영창")


def test_얼음감옥은_내성_없이_10턴_체력은_5더하기_지능보정치(monkeypatch):
    """민첩내성은 2026-10-14 삭제(사용자 지정) - 운석처럼 바로 갇힌다."""
    전투상태, 마녀, 아군 = _마녀전장("결빙의 케라하")
    패턴 = gf.몬스터목록["결빙의 케라하"]["패턴"]
    assert "내성" not in 패턴[5] and "난이도" not in 패턴[5]
    _굴림_기록(monkeypatch, [패턴[5]])
    _대상_차례로(monkeypatch, [아군[0]])
    받은DC = []

    def 내성(보정치, 난이도, **kw):
        받은DC.append(난이도)
        return True, 난이도

    monkeypatch.setattr(dice_utils, "내성_굴림", 내성)
    _한턴(전투상태, 마녀)
    지능 = stats.유효_능력치_보정치(전투상태, 마녀, "지능")
    assert 받은DC == []
    [감옥] = _감옥들(전투상태)
    assert 감옥["진영"] == "감옥" and 감옥["갇힌id"] == 아군[0]["id"]
    assert 감옥["현재HP"] == 5 + 지능
    assert [i["지속턴"] for i in _이름들(아군[0], "감옥")] == [10]
    assert stats.최종AC(전투상태, 감옥) == 1


def _가두기(monkeypatch, 이름, 대상):
    """마녀의 5번 패턴(얼음감옥/운석폭발)으로 대상을 가둔다(내성굴림은 실패로 고정)."""
    전투상태, 마녀, 아군 = _마녀전장(이름)
    _굴림_기록(monkeypatch, [gf.몬스터목록[이름]["패턴"][5]])
    _대상_차례로(monkeypatch, [아군[대상]])
    monkeypatch.setattr(
        dice_utils, "내성_굴림", lambda 보정치, 난이도, **kw: (False, 1)
    )
    _한턴(전투상태, 마녀)
    [감옥] = _감옥들(전투상태)
    return 전투상태, 마녀, 아군, 감옥


def test_갇힌_사람의_공격은_감옥이_받고_남은_데미지는_사라진다(monkeypatch):
    from game.system.combat import attacks

    전투상태, 마녀, 아군, 감옥 = _가두기(monkeypatch, "결빙의 케라하", 0)
    마녀HP = 마녀["현재HP"]
    support.주사위고정(monkeypatch, 2)  # 대실패만 아니면 감옥은 맞는다(AC 1)
    monkeypatch.setattr(stats, "피해_굴림", lambda *a, **k: 999)
    결과 = attacks.일반공격_실행(전투상태, 아군[0], 마녀)
    assert 결과["대상"] == 감옥["이름"] and 결과["판정"]["성공"]
    assert 마녀["현재HP"] == 마녀HP  # 남은 데미지는 원래 대상에게 가지 않는다
    assert 감옥["현재HP"] == 0 and not 감옥["생존"]
    assert not _이름들(아군[0], "감옥")  # 부서지면 풀린다


def test_감옥은_대실패면_빗나간다(monkeypatch):
    from game.system.combat import attacks

    전투상태, 마녀, 아군, 감옥 = _가두기(monkeypatch, "결빙의 케라하", 0)
    support.주사위고정(monkeypatch, 1)
    결과 = attacks.일반공격_실행(전투상태, 아군[1], 감옥)
    assert not 결과["판정"]["성공"] and 결과["판정"]["자동실패"]


def test_얼음감옥은_수속성_저항_화속성_취약_운석은_반대(monkeypatch):
    전투상태, 마녀, 아군, 얼음 = _가두기(monkeypatch, "결빙의 케라하", 0)
    assert damage.피해_속성배율(전투상태, 얼음, "수속성") == 0.5
    assert damage.피해_속성배율(전투상태, 얼음, "화속성") == 2
    전투상태, 마녀, 아군, 운석 = _가두기(monkeypatch, "화염의 비노슈", 0)
    assert damage.피해_속성배율(전투상태, 운석, "화속성") == 0.5
    assert damage.피해_속성배율(전투상태, 운석, "수속성") == 2


def test_감옥은_공격_대상_목록에_나오고_턴은_없고_승패에서_빠진다(monkeypatch):
    전투상태, 마녀, 아군, 감옥 = _가두기(monkeypatch, "결빙의 케라하", 0)
    상태 = {"전투상태": 전투상태}
    assert 감옥 in gf.공격대상_목록(상태) and 마녀 in gf.공격대상_목록(상태)
    assert 감옥 not in gf.적_목록(상태)  # 적 그림 칸에는 그리지 않는다
    for _ in range(12):  # 한 바퀴 넘게 돌려도 감옥 차례는 오지 않는다
        assert flow.다음_턴(전투상태) is not 감옥
    마녀["현재HP"] = 0
    마녀["생존"] = False
    전투상태["종료"] = None
    assert core.전투_종료_판정(전투상태) == "아군승리"


def test_아군의_전체공격만_감옥에_맞는다(monkeypatch):

    전투상태, 마녀, 아군, 감옥 = _가두기(monkeypatch, "결빙의 케라하", 0)
    assert 감옥 in skill_target.타겟_확장(전투상태, 아군[1], "적전체")
    assert 감옥 not in skill_target.타겟_확장(전투상태, 아군[1], "적3체", 마녀)
    # 갇힌 사람이 지정한 대상 몫은 감옥이 받는다
    assert skill_target.타겟_확장(전투상태, 아군[0], "적단일", 마녀) == [감옥]


def test_다른_캐릭터가_감옥을_때리면_넘친_데미지는_버린다(monkeypatch):
    from game.system.combat import attacks

    전투상태, 마녀, 아군, 감옥 = _가두기(monkeypatch, "결빙의 케라하", 0)
    support.주사위고정(monkeypatch, 10)
    monkeypatch.setattr(stats, "피해_굴림", lambda *a, **k: 999)
    HP전 = [p["현재HP"] for p in 아군]
    attacks.일반공격_실행(전투상태, 아군[1], 감옥)
    assert not 감옥["생존"] and not _이름들(아군[0], "감옥")
    assert [p["현재HP"] for p in 아군] == HP전


def _갇힌_사람_턴(전투상태, 사람):
    전투상태["현재턴"] = 전투상태["참가자"].index(사람)
    flow.턴_시작_처리(전투상태, 사람)
    flow.턴_종료_처리(전투상태, 사람)


def test_운석은_갇힌_사람의_턴_2번이_지나면_터져_모두에게_피해와_확정_화상(monkeypatch):
    전투상태, 마녀, 아군, 운석 = _가두기(monkeypatch, "화염의 비노슈", 2)
    assert [i["지속턴"] for i in _이름들(아군[2], "감옥")] == [2]
    HP전 = [p["현재HP"] for p in 아군]
    _갇힌_사람_턴(전투상태, 아군[2])
    assert 운석["생존"] and [p["현재HP"] for p in 아군] == HP전
    # 운석은 비노슈와 따로다 - 걸 때의 지능으로 터지고, 비노슈가 먼저 죽거나 능력치가 바뀌어도 그대로
    지능 = stats.유효_능력치_보정치(전투상태, 마녀, "지능")
    마녀["원본"] = dict(마녀["원본"], 지능=1)
    마녀["현재HP"] = 0
    마녀["생존"] = False
    support.주사위고정(monkeypatch, 6)
    _갇힌_사람_턴(전투상태, 아군[2])
    assert not 운석["생존"] and not _이름들(아군[2], "감옥")
    for p, 전 in zip(아군, HP전):
        assert 전 - p["현재HP"] == damage.최종피해_계산(
            6 + 지능, stats.유효_방어력(전투상태, p), stats.유효_보호률(전투상태, p)
        )
        assert [i["지속턴"] for i in _이름들(p, "화상")] == [3]


def test_운석을_부수면_터지지_않는다(monkeypatch):
    from game.system.combat import attacks

    전투상태, 마녀, 아군, 운석 = _가두기(monkeypatch, "화염의 비노슈", 2)
    support.주사위고정(monkeypatch, 10)
    monkeypatch.setattr(stats, "피해_굴림", lambda *a, **k: 999)
    attacks.일반공격_실행(전투상태, 아군[0], 운석)
    HP전 = [p["현재HP"] for p in 아군]
    _갇힌_사람_턴(전투상태, 아군[2])
    _갇힌_사람_턴(전투상태, 아군[2])
    assert [p["현재HP"] for p in 아군] == HP전
    assert not any(_이름들(p, "화상") for p in 아군)


def test_감옥은_하나만_새_감옥이_걸리면_앞_감옥의_벌칙이_일어난다(monkeypatch):
    전투상태, 마녀, 아군, 운석 = _가두기(monkeypatch, "화염의 비노슈", 2)
    HP전 = [p["현재HP"] for p in 아군]
    _한턴(전투상태, 마녀)  # 같은 사람에게 운석폭발 한 번 더
    [새운석] = _감옥들(전투상태)
    assert 새운석 is not 운석 and not 운석["생존"]
    assert len(_이름들(아군[2], "감옥")) == 1
    assert all(p["현재HP"] < 전 for p, 전 in zip(아군, HP전))  # 앞 운석이 터졌다


# ---------------------------------- 얼음감옥 아이스 그라운드 (사용자 지정 2026-10-14)


def _아이스그라운드(전투상태, 시작, 감옥):
    return [
        x
        for x in 전투상태["로그"][시작:]
        if x.get("종류") == "타격"
        and x.get("공격자") == 감옥["이름"]
        and x.get("패턴") == "아이스 그라운드"
    ]


@pytest.mark.parametrize("내성성공", [False, True])
def test_갇힌_사람의_턴이_끝날_때마다_얼음감옥이_아이스_그라운드를_쓴다(
    monkeypatch, 내성성공
):
    전투상태, 마녀, 아군, 감옥 = _가두기(monkeypatch, "결빙의 케라하", 0)
    받은DC = []

    def 내성(보정치, 난이도, **kw):
        받은DC.append(난이도)
        return 내성성공, 난이도

    monkeypatch.setattr(dice_utils, "내성_굴림", 내성)
    support.주사위고정(monkeypatch, 3)  # 1d4 = 3, 필중
    # 케라하와 따로다 - 케라하가 쓰러져도 감옥이 공격한다
    마녀["현재HP"] = 0
    마녀["생존"] = False
    HP전 = 아군[0]["현재HP"]
    시작 = len(전투상태["로그"])
    _갇힌_사람_턴(전투상태, 아군[0])
    [기록] = _아이스그라운드(전투상태, 시작, 감옥)
    assert 기록["대상"] == 아군[0]["이름"] and 기록["타격"][0]["판정"]["성공"]
    기대 = damage.최종피해_계산(
        3 * damage.피해_속성배율(전투상태, 아군[0], "수속성"),
        stats.유효_방어력(전투상태, 아군[0]),
        stats.유효_보호률(전투상태, 아군[0]),
    )
    assert HP전 - 아군[0]["현재HP"] == 기대  # 보정치 없는 1d4
    assert 받은DC == [10]
    assert bool(_이름들(아군[0], "빙결")) is not 내성성공
    assert [i["지속턴"] for i in _이름들(아군[0], "빙결")] == ([] if 내성성공 else [1])
    # 갇힌 사람이 아닌 아군의 턴 끝에는 쓰지 않는다
    시작 = len(전투상태["로그"])
    _갇힌_사람_턴(전투상태, 아군[1])
    assert not _아이스그라운드(전투상태, 시작, 감옥)


def test_감옥이_끝나는_턴에도_아이스_그라운드를_쓰고_부서지면_멈춘다(monkeypatch):
    from game.system.combat import attacks

    전투상태, 마녀, 아군, 감옥 = _가두기(monkeypatch, "결빙의 케라하", 0)
    [항목] = _이름들(아군[0], "감옥")
    항목["지속턴"] = 1  # 이번 턴 끝에 감옥이 끝난다
    시작 = len(전투상태["로그"])
    _갇힌_사람_턴(전투상태, 아군[0])
    assert len(_아이스그라운드(전투상태, 시작, 감옥)) == 1
    assert not 감옥["생존"] and not _이름들(아군[0], "감옥")

    전투상태, 마녀, 아군, 감옥 = _가두기(monkeypatch, "결빙의 케라하", 0)
    support.주사위고정(monkeypatch, 10)
    monkeypatch.setattr(stats, "피해_굴림", lambda *a, **k: 999)
    attacks.일반공격_실행(전투상태, 아군[1], 감옥)  # 부순다
    시작 = len(전투상태["로그"])
    _갇힌_사람_턴(전투상태, 아군[0])
    assert not _아이스그라운드(전투상태, 시작, 감옥)


# ---------------------------------- 감옥 그림 (사용자 지정 2026-10-14)


@pytest.mark.parametrize(
    "이름, 기대",
    [
        (
            "결빙의 케라하",
            (
                "asset_monster_ice_prison_back.webp",
                "asset_monster_ice_prison_front.webp",
            ),
        ),
        ("화염의 비노슈", ("asset_monster_meteor_prison.webp", None)),
    ],
)
def test_갇힌_아군의_감옥_그림은_뒤와_앞이고_부서지면_없다(monkeypatch, 이름, 기대):
    import os
    from game.system.combat import attacks

    전투상태, 마녀, 아군, 감옥 = _가두기(monkeypatch, 이름, 0)
    상태 = {"전투상태": 전투상태}
    assert gf.감옥_그림(상태, 아군[0]) == 기대
    assert gf.감옥_그림(상태, 아군[1]) == (None, None)
    for 파일 in 기대:
        if 파일:
            assert os.path.isfile(os.path.join("game", "assets", "monster", 파일)), 파일
    support.주사위고정(monkeypatch, 10)
    monkeypatch.setattr(stats, "피해_굴림", lambda *a, **k: 999)
    attacks.일반공격_실행(전투상태, 아군[1], 감옥)
    assert gf.감옥_그림(상태, 아군[0]) == (None, None)


# ------------------------------------- 명중 굴림이 없는 공격의 연출 (사용자 지정 2026-10-14)


def test_냉기방출은_내성_결과와_관계없이_모든_적에게_연출(monkeypatch):
    전투상태, [굴], 아군 = support.시험_전투(["굴 구위시"])
    결과 = iter([True, False, True, False])  # 성공해도 절반을 맞는다
    monkeypatch.setattr(
        dice_utils, "내성_굴림", lambda 보정치, 난이도, **kw: (next(결과), 난이도)
    )
    traits.특성_턴종료시_발동(전투상태, 굴)
    assert sorted(e["대상id"] for e in 전투상태["공격연출"]) == sorted(
        p["id"] for p in 아군
    )
    assert {e["종류"] for e in 전투상태["공격연출"]} == {"마법:수"}


def test_기상_충격파는_모든_적에게_타격_연출(monkeypatch):
    전투상태, [굴], 아군 = support.시험_전투(["굴 구위시"])
    monkeypatch.setattr(
        dice_utils, "내성_굴림", lambda 보정치, 난이도, **kw: (True, 난이도)
    )
    굴["상태이상"].append({"이름": "넘어짐", "지속턴": 1})
    flow.턴_시작_처리(전투상태, 굴)  # 지속턴 만료 -> 해제시 발동
    assert sorted(e["대상id"] for e in 전투상태["공격연출"]) == sorted(
        p["id"] for p in 아군
    )
    assert {e["종류"] for e in 전투상태["공격연출"]} == {"타격:무"}


def test_자폭명령은_폭사한_수만큼_맞은_대상에게_연출(monkeypatch):
    from game.system import monster_ai

    전투상태, 적, 아군 = support.시험_전투(["고블린 십장", "고블린", "고블린"])
    십장 = next(p for p in 적 if p["원본"]["몬스터명"] == "고블린 십장")
    패턴 = next(
        p
        for p in gf.몬스터목록["고블린 십장"]["패턴"].values()
        if p.get("타입") == "자폭패턴"
    )
    monkeypatch.setattr(monster_ai, "행동_선택", lambda p: 패턴)
    결과 = monster_actions.몬스터_턴_실행(전투상태, 십장)
    아군id = {p["id"] for p in 아군}
    assert 결과["폭사수"] == 2
    assert len(전투상태["공격연출"]) == 2
    assert all(
        e["대상id"] in 아군id and e["종류"] == "타격:무" for e in 전투상태["공격연출"]
    )


# ------------------------------------------------------------------ 거대 누골 (시험용, 2026-10-21 사용자 지정)


def _누골전(레벨=10):
    rng.시드(3)
    상태 = support.새게임()
    gf.전투_시작(상태, [{"이름": "거대 누골", "칭호": "보스"}], 레벨=레벨, 차수=1)
    support.반응_처리(상태)
    [누골] = gf.적_목록(상태)
    return 상태, 누골


def test_거대_누골은_능력치_15_엘리트_대형_딜러이고_샌드백_특성을_가진다():
    데이터 = gf.몬스터목록["거대 누골"]
    assert {k: 데이터[k] for k in ("근력", "민첩", "건강", "지능", "지혜", "매력")} == {
        k: 15 for k in ("근력", "민첩", "건강", "지능", "지혜", "매력")
    }
    assert (데이터["칭호"], 데이터["적등급"], 데이터["크기"], 데이터["역할군"]) == (
        None,  # 칭호는 전투를 여는 쪽(샌드백_전투)이 "보스"로 붙인다
        "엘리트",
        "대형",
        "딜러",
    )
    assert 데이터["특성"] == ["샌드백"]


def test_샌드백은_최대HP_1000을_더한다():
    """레벨 10 딜러 건강 15(보정치 2): 기본 7+올림(10x7/2)=42, 보스 칭호 2배 84, 샌드백 +1000."""
    상태, 누골 = _누골전()
    최대 = stats.유효_최대HP(상태["전투상태"], 누골)
    assert 최대 == 1084 and 누골["현재HP"] == 1084


def test_거대_누골_패턴은_1에서_6_모두_한_명에게_근력판정_1d8():
    패턴 = gf.몬스터목록["거대 누골"]["패턴"]
    assert sorted(패턴) == [1, 2, 3, 4, 5, 6]
    for p in 패턴.values():
        assert (p["타입"], p["타겟"], p["데미지"], p["명중률"], p["공격횟수"]) == (
            "공격패턴",
            "적단일",
            "1d8",
            "근력판정",
            1,
        )
