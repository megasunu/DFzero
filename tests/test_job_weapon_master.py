"""웨펀마스터 스킬: 류심 : 쾌의 강화류심 보너스는 지정한 적 1체에게만(#580)."""

import pytest

import gameflow as gf
from game.system import rng
from game.system import skill_system as ss
from game.system.combat import flow
from tests import support


def _쾌_전장():
    """레벨 6 웨펀마스터 대 고블린 셋(HP 넉넉히), 웨펀마스터 차례에 류심자세."""
    rng.시드(1)
    상태 = support.새게임([("", "귀검사")])
    support.성장(상태, 상태["파티"]["파티원"][0], 6, 전직="웨펀마스터")
    gf.파티_최대치로_회복(상태)
    gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    p = next(x for x in 전투상태["참가자"] if x["진영"] == "아군")
    전투상태["현재턴"] = 전투상태["참가자"].index(p)
    flow.턴_시작_처리(전투상태, p)
    p["현재MP"] = 100
    적 = [x for x in 전투상태["참가자"] if x["진영"] == "적"]
    for x in 적:
        x["현재HP"] = x["최대HP"] = 999
    ss.이름있는효과_부여(전투상태, p, "류심자세", 1)
    return 상태, p, 적


@pytest.mark.parametrize("지정", [0, 1, 2])
def test_류심_쾌의_강화류심_추가피해는_지정한_적에게만_들어간다(monkeypatch, 지정):
    support.주사위고정(monkeypatch, 15)  # d20 15(명중), 피해 주사위는 최대
    피해 = {}
    for 강화 in (False, True):
        상태, p, 적 = _쾌_전장()
        if 강화:
            ss.이름있는효과_부여(상태["전투상태"], p, "강화류심", 1)
        결과 = gf.아군_스킬사용(상태, "류심 : 쾌", 중심대상=적[지정])
        피해[강화] = {t["대상"]: t["피해"] for t in 결과["타격"]}
        if 강화:  # 강화류심은 한 번만 소모된다
            assert not any(b["이름"] == "강화류심" for b in p["버프"])
    지정이름 = 적[지정]["이름"]
    assert set(피해[True]) == set(피해[False])  # 맞는 적은 같다
    for 이름, 값 in 피해[True].items():
        if 이름 == 지정이름:
            assert 값 > 피해[False][이름]  # 보정공격력만큼 더
        else:
            assert 값 == 피해[False][이름], 이름  # 양옆 적은 그대로
