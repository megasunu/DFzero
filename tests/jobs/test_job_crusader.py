"""크루세이더(051f) 공격 스킬 수치(스킬 밸런스 기준과 견줘 조정).

승리의 창: 일반행동, MP 10, 적 1체, (차수+1)d8+주문시전보정치. 잡기 - 피해는 바로 주고 홀딩(홀딩값 1)을 건다."""

import pytest

import gameflow as gf
from game.system import rng
from game.system import skill_system as ss
from game.system.combat import flow, stats
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


def test_승리의_창은_피해를_바로_주고_홀딩만_건다(크루전장, monkeypatch):
    """2026-11-17 - 홀딩과 피해 시점은 따로다. 승리의 창은 "홀딩" 태그 없이 홀딩값 1 - 피해는 바로,
    홀딩으로 우선도 -1, 경직으로 이니셔티브 -1. 대상의 차례가 시작되면 피해 없이 풀린다."""
    _, 전투상태, 적, c = 크루전장
    스킬 = _스킬("승리의 창")
    assert "잡기" in 스킬["타입"] and "홀딩" not in 스킬["타입"] and 스킬["홀딩값"] == 1
    monkeypatch.setattr(stats.dice_utils, "d20_굴림", lambda 이점=False, 불리=False: 15)
    c["행동자원"].update(일반행동=1, 보조행동=1)
    c["현재MP"] = 50
    e = 적[0]
    우선도, 이니 = e.get("우선도", 0), e["이니셔티브"]
    로그수 = len(전투상태["로그"])
    결과 = ss.스킬_실행(전투상태, c, "승리의 창", 스킬, e)
    피해 = 결과["타격"][0]["피해"]
    assert 피해 > 0 and e["현재HP"] == 999 - 피해
    assert [s["이름"] for s in e["상태이상"]].count("홀딩") == 1
    assert (e["우선도"], e["이니셔티브"]) == (우선도 - 1, 이니 - 1)
    문장 = [줄 for 항목 in 전투상태["로그"][로그수:] for 줄 in gf.로그_문장들(항목)]
    assert any("붙잡았다!" in 줄 for 줄 in 문장)
    assert not any("움직일 때 들어간다" in 줄 for 줄 in 문장)
    flow.턴_시작_처리(전투상태, e)
    assert e["현재HP"] == 999 - 피해 and all(s["이름"] != "홀딩" for s in e["상태이상"])


def _그랜드_크로스(전투상태, c, 대상, monkeypatch, 눈):
    monkeypatch.setattr(stats.dice_utils, "d20_굴림", lambda 이점=False, 불리=False: 눈)
    monkeypatch.setattr(rng.주사위, "randint", lambda a, b: b)  # 주사위 최대 눈
    c["행동자원"].update(일반행동=1, 보조행동=1)
    c["현재MP"] = 50
    return ss.스킬_실행(전투상태, c, "그랜드 크로스", _스킬("그랜드 크로스"), 대상)


def _용맹의_축복_지속턴(c):
    return [b["지속턴"] for b in c["버프"] if b.get("출처스킬") == "용맹의 축복"]


def test_그랜드_크로스는_3차수_골드_차수_더하기_3_d10_보정치_없음(
    크루전장, monkeypatch
):
    _, 전투상태, 적, c = 크루전장
    데이터 = _스킬("그랜드 크로스")
    assert (데이터["습득방법"], 데이터["습득레벨"], 데이터["습득차수"]) == (
        "구매습득",
        11,
        3,
    )
    결과 = _그랜드_크로스(전투상태, c, 적[0], monkeypatch, 15)
    assert c["현재MP"] == 30
    # 레벨 8 = 2차수 -> 5d10 최대 50, 보정치를 더하지 않는다
    assert 결과["타격"][0]["피해"] == 50


def test_용맹의_축복은_5턴이고_그랜드_크로스가_빗나가도_5턴_늘린다(
    크루전장, monkeypatch
):
    _, 전투상태, 적, c = 크루전장
    assert _스킬("용맹의 축복")["지속턴"] == 5
    ss.스킬_실행(전투상태, c, "용맹의 축복", _스킬("용맹의 축복"), None)
    assert _용맹의_축복_지속턴(c) == [5, 5]  # 근력증가·지능증가
    _그랜드_크로스(전투상태, c, 적[0], monkeypatch, 1)  # 1은 빗나감
    assert _용맹의_축복_지속턴(c) == [10, 10]
    # 다른 아군에게 건 용맹의 축복은 늘지 않는다
    아군 = next(p for p in 전투상태["참가자"] if p["진영"] == "아군" and p is not c)
    assert [
        b["지속턴"] for b in 아군["버프"] if b.get("출처스킬") == "용맹의 축복"
    ] == [5, 5]


def test_용맹의_축복이_없으면_그랜드_크로스는_지속턴을_건드리지_않는다(
    크루전장, monkeypatch
):
    _, 전투상태, 적, c = 크루전장
    _그랜드_크로스(전투상태, c, 적[0], monkeypatch, 15)
    assert _용맹의_축복_지속턴(c) == []
