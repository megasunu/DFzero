"""캐스팅과 차징의 피격 취소 - 캐스팅/차징 상태에서 공격에 맞으면 캐스팅은 지혜, 차징은 건강 내성굴림(DC 10)을
하고, 실패하면 공격이 취소된다(쓴 행동·MP는 돌려받지 못한다). 슈퍼아머면 취소되지 않는다. 밀림(캐스트 이니셔티브,
차지 우선도)은 직업 테스트(엘리멘탈마스터·넨마스터·런처·미스트리스·인챈트리스)가 지킨다. 규칙은 docs/game-rules.md "캐스팅".
"""

import pytest

import gameflow as gf
from game.system.combat import hit_effects, monster_actions, stats
from game.system.skill import skill_run
from tests import support

성공 = {"성공": True}


def _스킬(이름):
    return dict(gf.스킬데이터모음_생성()[이름], _이름=이름)


def _상태(p, 이름):
    return any(s.get("이름") == 이름 for s in p.get("상태이상") or [])


def _시작(스킬이름):
    """마법사가 스킬을 쓴 직후 - 일반행동과 MP 10은 이미 냈고 보조행동 1이 남았다."""
    전투상태, 적, 아군 = support.시험_전투(["고블린"])
    p = 아군[3]
    p["행동자원"].update(일반행동=0, 보조행동=1)
    p["현재MP"] = 20
    skill_run.캐스팅_시작(전투상태, p, _스킬(스킬이름), 적[0])
    return 전투상태, 적[0], p


@pytest.mark.parametrize(
    "스킬, 종류, 내성",
    [("축염포", "캐스팅", "지혜"), ("레이저 라이플", "차징", "건강")],
)
def test_피격되면_종류에_맞는_내성을_DC10으로_굴린다(monkeypatch, 스킬, 종류, 내성):
    전투상태, 적, p = _시작(스킬)
    assert _상태(p, 종류)
    굴림 = []

    def 가짜(전투상태, 대상, 내성스탯, 난이도, **_):
        굴림.append((대상["이름"], 내성스탯, 난이도))
        return True, 20, 0

    monkeypatch.setattr(stats, "대상_내성굴림", 가짜)
    hit_effects.피격_처리(전투상태, 적, p, 성공)
    assert 굴림 == [(p["이름"], 내성, 10)]
    assert _상태(p, 종류)  # 성공하면 그대로


@pytest.mark.parametrize(
    "스킬, 종류", [("축염포", "캐스팅"), ("레이저 라이플", "차징")]
)
def test_내성에_실패하면_취소되고_쓴_행동과_MP는_돌려받지_못한다(
    monkeypatch, 스킬, 종류
):
    전투상태, 적, p = _시작(스킬)
    support.주사위고정(monkeypatch, 1)
    hit_effects.피격_처리(전투상태, 적, p, 성공)
    assert not _상태(p, 종류)
    assert p["캐스팅"]["취소"]
    글 = [str(x.get("비고", "")) for x in 전투상태["로그"]]
    assert any(f"{스킬} {종류}이 피격으로 취소되었다" in g for g in 글)
    HP = 적["현재HP"]
    assert skill_run.캐스팅_발사(전투상태, p) is None  # 밀린 차례에 쏘지 않는다
    assert 적["현재HP"] == HP
    assert p["현재MP"] == 20
    assert (p["행동자원"]["일반행동"], p["행동자원"]["보조행동"]) == (0, 1)
    assert "캐스팅" not in p


def test_한_번_취소되면_다시_굴리지_않는다(monkeypatch):
    전투상태, 적, p = _시작("축염포")
    support.주사위고정(monkeypatch, 1)
    hit_effects.피격_처리(전투상태, 적, p, 성공)
    monkeypatch.setattr(
        stats, "대상_내성굴림", lambda *a, **k: pytest.fail("다시 굴렸다")
    )
    hit_effects.피격_처리(전투상태, 적, p, 성공)


def test_빗나간_공격은_굴리지_않는다(monkeypatch):
    전투상태, 적, p = _시작("축염포")
    monkeypatch.setattr(
        stats, "대상_내성굴림", lambda *a, **k: pytest.fail("빗나갔는데 굴렸다")
    )
    hit_effects.피격_처리(전투상태, 적, p, {"성공": False})
    assert _상태(p, "캐스팅")


@pytest.mark.parametrize(
    "스킬, 종류", [("축염포", "캐스팅"), ("레이저 라이플", "차징")]
)
def test_슈퍼아머면_취소되지_않는다(monkeypatch, 스킬, 종류):
    전투상태, 적, p = _시작(스킬)
    p["상태이상"].append({"이름": "슈퍼아머", "지속턴": 2})
    support.주사위고정(monkeypatch, 1)
    hit_effects.피격_처리(전투상태, 적, p, 성공)
    assert _상태(p, 종류)
    assert not p["캐스팅"].get("취소")


def test_몬스터_차징도_피격으로_취소되면_밀린_차례에_쓰지_않는다(monkeypatch):
    전투상태, 적, 아군 = support.시험_전투(["라키우스"])
    라키 = 적[0]
    패턴 = next(
        p for p in 라키["원본"]["패턴"].values() if p.get("이름") == "심장 찌르기"
    )
    라키["원본"] = dict(  # 늘 심장 찌르기, 턴 시작 감옥(특수패턴:라키우스) 없이
        라키["원본"],
        패턴={1: 패턴},
        특성=[t for t in 라키["원본"]["특성"] if t != "특수패턴:라키우스"],
    )
    전투상태["현재턴"] = 전투상태["참가자"].index(라키)
    monster_actions.몬스터_턴_실행(전투상태, 라키)
    assert _상태(라키, "차징")
    assert 라키["캐스팅"]["밀림"] == {"우선도": -1, "이니셔티브": 0}
    support.주사위고정(monkeypatch, 1)
    hit_effects.피격_처리(전투상태, 아군[0], 라키, 성공)
    assert not _상태(라키, "차징")
    라키.pop("캐스팅시작")
    라키["캐스팅발사"] = True
    로그수 = len(전투상태["로그"])
    monster_actions.몬스터_턴_실행(전투상태, 라키)
    assert not [x for x in 전투상태["로그"][로그수:] if x.get("패턴") == "심장 찌르기"]
    assert "캐스팅" not in 라키
