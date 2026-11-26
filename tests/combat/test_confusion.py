"""상태이상 "혼란" - 공격할 때 50% 확률로 자기 편의 무작위 동료(자신 제외)를
대상으로 삼는다. 스킬 제한은 없다. 범위 공격은 그 동료를 중심으로, 전체 공격은 자기 편 전체(자신 제외)를 친다.
상태이상 항목의 "아군공격확률"(마스터 도그리가 건 혼란은 1)이 있으면 그 확률을 쓴다. 아군과 몬스터 모두 같다.

규칙은 docs/game-rules.md "혼란".
"""

import pytest

from game.controller import ctl_battle_log
from game.system import monster_ai, rng
from game.system import skill_system as ss
from game.system.combat import attacks, flow, monster_actions
from tests import support


@pytest.fixture
def 전장():
    전투상태, 적, 아군 = support.시험_전투(["고블린", "고블린", "고블린"])
    return 전투상태, 적, 아군


def _혼란(참가자, 확률=None):
    항목 = {"이름": "혼란", "지속턴": 2}
    if 확률 is not None:
        항목["아군공격확률"] = 확률
    참가자.setdefault("상태이상", []).append(항목)


def _확률굴림(monkeypatch, 값):
    monkeypatch.setattr(rng.확률, "random", lambda: 값)


def _동료고르기(monkeypatch, 순번=0):
    """무작위 동료 고르기를 후보 목록의 순번째로 고정한다."""
    monkeypatch.setattr(rng.대상, "choice", lambda 후보: list(후보)[순번])


def _스킬(**kw):
    기본 = {
        "_이름": "시험",
        "분류": "공격스킬",
        "행동": "일반행동",
        "MP소모": 0,
        "데미지": "1",
        "공격타입": "타격",
        "명중률": "보정명중률",
        "속성": "무속성",
    }
    기본.update(kw)
    return 기본


def _맞은_대상(전투상태, 시작):
    이름들 = []
    for x in 전투상태["로그"][시작:]:
        if x.get("종류") != "타격":
            continue
        if "타격" in x:  # 단일 대상은 타격마다가 아니라 항목에 "대상"이 있다
            이름들 += [t.get("대상", x.get("대상")) for t in x["타격"]]
        elif x.get("대상"):
            이름들.append(x["대상"])
    return 이름들


def test_혼란이어도_일반공격취급이_아닌_스킬을_쓸_수_있다(전장):
    전투상태, _, 아군 = 전장
    flow.턴_시작_처리(전투상태, 아군[0])
    _혼란(아군[0])
    assert ss.사용_가능여부(전투상태, 아군[0], _스킬()) == (True, None)


def test_혼란_일반공격은_50퍼센트_아래면_자신이_아닌_동료를_친다(전장, monkeypatch):
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    _혼란(아군[0])
    _확률굴림(monkeypatch, 0.49)
    _동료고르기(monkeypatch)
    결과 = attacks.일반공격_실행(전투상태, 아군[0], 적[0])
    assert 결과["대상"] == 아군[1]["이름"]


def test_혼란_일반공격은_50퍼센트_이상이면_고른_적을_친다(전장, monkeypatch):
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    _혼란(아군[0])
    _확률굴림(monkeypatch, 0.5)
    결과 = attacks.일반공격_실행(전투상태, 아군[0], 적[0])
    assert 결과["대상"] == 적[0]["이름"]


def test_혼란으로_동료를_치면_문장이_나온다(전장, monkeypatch):
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    _혼란(아군[0])
    _확률굴림(monkeypatch, 0.0)
    시작 = len(전투상태["로그"])
    attacks.일반공격_실행(전투상태, 아군[0], 적[0])
    문장 = [줄 for x in 전투상태["로그"][시작:] for 줄 in ctl_battle_log.로그_문장들(x)]
    assert f"{아군[0]['이름']}: 영문도 모른 채 아군을 공격했다!" in 문장


def test_아군공격확률_1인_혼란은_언제나_동료를_친다(전장, monkeypatch):
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    _혼란(아군[0], 확률=1)
    _확률굴림(monkeypatch, 0.99)
    _동료고르기(monkeypatch)
    결과 = attacks.일반공격_실행(전투상태, 아군[0], 적[0])
    assert 결과["대상"] == 아군[1]["이름"]


def test_혼란_단일_스킬은_동료를_친다(전장, monkeypatch):
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    _혼란(아군[0])
    _확률굴림(monkeypatch, 0.0)
    _동료고르기(monkeypatch, 1)
    시작 = len(전투상태["로그"])
    ss.스킬_실행(전투상태, 아군[0], "시험", _스킬(타겟="적단일"), 중심대상=적[0])
    assert _맞은_대상(전투상태, 시작) == [아군[2]["이름"]]


def test_혼란_전체_스킬은_자신을_뺀_자기_편_전체를_친다(전장, monkeypatch):
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    _혼란(아군[0])
    _확률굴림(monkeypatch, 0.0)
    시작 = len(전투상태["로그"])
    ss.스킬_실행(전투상태, 아군[0], "시험", _스킬(타겟="적전체"), 중심대상=적[0])
    assert sorted(_맞은_대상(전투상태, 시작)) == sorted(p["이름"] for p in 아군[1:])


def test_혼란_범위_스킬은_동료를_중심으로_자기_편에_잡힌다(전장, monkeypatch):
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    줄 = sorted(아군, key=lambda p: p["대형위치"])
    _혼란(줄[0])
    _확률굴림(monkeypatch, 0.0)
    monkeypatch.setattr(rng.대상, "choice", lambda 후보: 줄[2])
    시작 = len(전투상태["로그"])
    ss.스킬_실행(전투상태, 줄[0], "시험", _스킬(타겟="적3체"), 중심대상=적[0])
    assert sorted(_맞은_대상(전투상태, 시작)) == sorted(p["이름"] for p in 줄[1:4])


def test_혼란_버프_스킬은_대상이_바뀌지_않는다(전장, monkeypatch):
    전투상태, _, 아군 = 전장
    _혼란(아군[0])
    _확률굴림(monkeypatch, 0.0)
    스킬 = {
        "_이름": "시험버프",
        "분류": "버프스킬",
        "행동": "일반행동",
        "MP소모": 0,
        "타겟": "자신",
        "버프획득": "가드",
        "지속턴": 2,
    }
    ss.스킬_실행(전투상태, 아군[0], "시험버프", 스킬, 중심대상=아군[0])
    assert any(b["이름"] == "가드" for b in 아군[0].get("버프", []))


def test_동료가_없으면_혼란이어도_적을_친다(monkeypatch):
    전투상태, 적, 아군 = support.시험_전투(["고블린"])
    support.주사위고정(monkeypatch, 20)
    for p in 아군[1:]:
        p["생존"] = False
    _혼란(아군[0])
    _확률굴림(monkeypatch, 0.0)
    결과 = attacks.일반공격_실행(전투상태, 아군[0], 적[0])
    assert 결과["대상"] == 적[0]["이름"]


def test_혼란_몬스터는_다른_몬스터를_친다(전장, monkeypatch):
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    _혼란(적[0])
    _확률굴림(monkeypatch, 0.0)
    _동료고르기(monkeypatch, 1)
    패턴 = {
        "이름": "시험 때리기",
        "타입": "공격패턴",
        "타겟": "적단일",
        "속성": "무속성",
        "데미지": "1",
        "공격타입": "타격",
        "데미지보너스": 0,
        "명중률": "근력판정",
        "명중보너스": 0,
        "공격횟수": 1,
        "각공격명중굴림": False,
        "효과": None,
        "조건부효과": None,
    }
    monkeypatch.setattr(monster_ai, "행동_선택", lambda p: 패턴)
    monkeypatch.setattr(monster_ai, "타겟_선택", lambda *a, **k: 아군[0])
    전투상태["현재턴"] = 전투상태["참가자"].index(적[0])
    flow.턴_시작_처리(전투상태, 적[0])
    시작 = len(전투상태["로그"])
    monster_actions.몬스터_턴_실행(전투상태, 적[0])
    assert _맞은_대상(전투상태, 시작) == [적[2]["이름"]]


def test_혼란_몬스터의_전체_패턴은_자신을_뺀_몬스터_전체를_친다(전장, monkeypatch):
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    _혼란(적[0])
    _확률굴림(monkeypatch, 0.0)
    패턴 = {
        "이름": "시험 휘두르기",
        "타입": "공격패턴",
        "타겟": "적전체",
        "속성": "무속성",
        "데미지": "1",
        "공격타입": "타격",
        "데미지보너스": 0,
        "명중률": "근력판정",
        "명중보너스": 0,
        "공격횟수": 1,
        "각공격명중굴림": True,
        "효과": None,
        "조건부효과": None,
    }
    monkeypatch.setattr(monster_ai, "행동_선택", lambda p: 패턴)
    monkeypatch.setattr(monster_ai, "타겟_선택", lambda *a, **k: 아군[0])
    전투상태["현재턴"] = 전투상태["참가자"].index(적[0])
    flow.턴_시작_처리(전투상태, 적[0])
    시작 = len(전투상태["로그"])
    monster_actions.몬스터_턴_실행(전투상태, 적[0])
    assert sorted(_맞은_대상(전투상태, 시작)) == sorted(p["이름"] for p in 적[1:])


# ---- 은신(지정불가) 동료는 노리는 동료 후보에서 빠진다 (#843) ----


def _은신(참가자):
    참가자.setdefault("상태이상", []).append({"이름": "은신", "지속턴": 3})


def _후보_기록(monkeypatch):
    """무작위 동료 고르기를 후보 목록의 맨 앞으로 고정하고, 받은 후보 목록을 모은다."""
    받은 = []

    def 고르기(후보):
        받은.append(list(후보))
        return list(후보)[0]

    monkeypatch.setattr(rng.대상, "choice", 고르기)
    return 받은


def test_혼란_일반공격은_은신한_동료를_노리지_않는다(전장, monkeypatch):
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    _은신(아군[1])
    _혼란(아군[0], 확률=1)
    받은 = _후보_기록(monkeypatch)
    결과 = attacks.일반공격_실행(전투상태, 아군[0], 적[0])
    assert 받은 == [[아군[2], 아군[3]]]
    assert 결과["대상"] == 아군[2]["이름"]


def test_혼란_일반공격은_동료가_모두_은신이면_고른_적을_친다(전장, monkeypatch):
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    for p in 아군[1:]:
        _은신(p)
    _혼란(아군[0], 확률=1)
    결과 = attacks.일반공격_실행(전투상태, 아군[0], 적[0])
    assert 결과["대상"] == 적[0]["이름"]


def test_혼란_단일_스킬은_은신한_동료를_노리지_않는다(전장, monkeypatch):
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    _은신(아군[1])
    _혼란(아군[0], 확률=1)
    받은 = _후보_기록(monkeypatch)
    시작 = len(전투상태["로그"])
    ss.스킬_실행(전투상태, 아군[0], "시험", _스킬(타겟="적단일"), 중심대상=적[0])
    assert 받은 == [[아군[2], 아군[3]]]
    assert _맞은_대상(전투상태, 시작) == [아군[2]["이름"]]


def test_혼란_단일_스킬은_동료가_모두_은신이면_자원을_쓰고_고른_적을_친다(
    전장, monkeypatch
):
    """전에는 은신 동료를 중심대상으로 바꿔 대상_검증이 ValueError를 냈고 MP·행동만 빠졌다."""
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    flow.턴_시작_처리(전투상태, 아군[0])
    for p in 아군[1:]:
        _은신(p)
    _혼란(아군[0], 확률=1)
    아군[0]["현재MP"] = 10
    시작 = len(전투상태["로그"])
    ss.스킬_실행(
        전투상태, 아군[0], "시험", _스킬(타겟="적단일", MP소모=3), 중심대상=적[0]
    )
    assert 아군[0]["현재MP"] == 7
    assert 아군[0]["행동자원"]["일반행동"] == 0
    assert _맞은_대상(전투상태, 시작) == [적[0]["이름"]]


def _몬스터_패턴_실행(전투상태, 몬스터, 대상, monkeypatch, 타겟):
    패턴 = {
        "이름": "시험 때리기",
        "타입": "공격패턴",
        "타겟": 타겟,
        "속성": "무속성",
        "데미지": "1",
        "공격타입": "타격",
        "데미지보너스": 0,
        "명중률": "근력판정",
        "명중보너스": 0,
        "공격횟수": 1,
        "각공격명중굴림": True,
        "효과": None,
        "조건부효과": None,
    }
    monkeypatch.setattr(monster_ai, "행동_선택", lambda p: 패턴)
    monkeypatch.setattr(monster_ai, "타겟_선택", lambda *a, **k: 대상)
    전투상태["현재턴"] = 전투상태["참가자"].index(몬스터)
    flow.턴_시작_처리(전투상태, 몬스터)
    시작 = len(전투상태["로그"])
    monster_actions.몬스터_턴_실행(전투상태, 몬스터)
    return _맞은_대상(전투상태, 시작)


def test_혼란_몬스터는_은신한_몬스터를_노리지_않는다(전장, monkeypatch):
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    _은신(적[1])
    _혼란(적[0], 확률=1)
    받은 = _후보_기록(monkeypatch)
    맞은 = _몬스터_패턴_실행(전투상태, 적[0], 아군[0], monkeypatch, "적단일")
    assert 받은 == [[적[2]]]
    assert 맞은 == [적[2]["이름"]]


def test_혼란_몬스터는_다른_몬스터가_모두_은신이면_원래_대상을_친다(전장, monkeypatch):
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    for p in 적[1:]:
        _은신(p)
    _혼란(적[0], 확률=1)
    맞은 = _몬스터_패턴_실행(전투상태, 적[0], 아군[0], monkeypatch, "적단일")
    assert 맞은 == [아군[0]["이름"]]


def test_혼란_몬스터의_전체_패턴은_은신한_몬스터도_맞힌다(전장, monkeypatch):
    """범위 공격은 은신이어도 맞는다 - 노리는 후보에서만 뺀다."""
    전투상태, 적, 아군 = 전장
    support.주사위고정(monkeypatch, 20)
    _은신(적[1])
    _혼란(적[0], 확률=1)
    맞은 = _몬스터_패턴_실행(전투상태, 적[0], 아군[0], monkeypatch, "적전체")
    assert sorted(맞은) == sorted(p["이름"] for p in 적[1:])
