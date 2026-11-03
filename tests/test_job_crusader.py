"""크루세이더(051f) 공격 스킬 수치 (2026-11-03 사용자 결정 - 스킬 밸런스 기준과 견줘 조정).

승리의 창: 일반행동, MP 10, 적 1체, (차수+1)d8+주문시전보정치(전에는 (차수)d8+(차수)x주문시전보정치)."""

import pytest

import gameflow as gf
from game.system import rng
from game.system import skill_system as ss
from game.system.combat import stats
from tests import support


@pytest.fixture
def 크루전장():
    """프리스트 -> 크루세이더 레벨 8(골드 스킬 전부 습득)과 귀검사, 고블린 셋(HP 999)."""
    rng.시드(5)
    상태 = support.새게임([("", "프리스트"), ("", "귀검사")])
    크, _ = 상태["파티"]["파티원"]
    support.성장(상태, 크, 8, 전직="크루세이더", 스킬습득=True)
    gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    적 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "적"),
        key=lambda p: p["대형위치"],
    )
    for p in 적:
        p["현재HP"] = p["최대HP"] = 999
    c = next(p for p in 전투상태["참가자"] if p["원본"] is 크)
    c["장비보너스"] = {}
    return 상태, 전투상태, 적, c


def _스킬(이름):
    return dict(gf.스킬데이터모음_생성()[이름], _이름=이름)


def test_승리의_창은_차수_더하기_1_d8_더하기_주문시전보정치(크루전장, monkeypatch):
    _, 전투상태, 적, c = 크루전장
    monkeypatch.setattr(stats.dice_utils, "d20_굴림", lambda 이점=False, 불리=False: 15)
    monkeypatch.setattr(rng.주사위, "randint", lambda a, b: b)  # 주사위 최대 눈
    c["행동자원"].update(일반행동=1, 보조행동=1)
    c["현재MP"] = 50
    결과 = ss.스킬_실행(전투상태, c, "승리의 창", _스킬("승리의 창"), 적[0])
    assert c["현재MP"] == 40
    assert not _스킬("승리의 창")["일반공격취급"]
    # 레벨 8 = 2차수 -> 3d8 최대 24 + 주문시전보정치(한 번만)
    assert 결과["타격"][0]["피해"] == 24 + stats.주문시전_보정치(전투상태, c)
