# 공용 퍽(perks_class_0000.py) 중 전투 특성 퍽 - 만독불침/심안/웨펀브레이커/아머브레이커
# (2026-10-19 사용자 결정). 규칙은 docs/game-rules.md "공용 퍽 - 전투 특성".

import random

import pytest

import gameflow as gf
from game.data.ability.job_ability_0000 import 특성목록
from game.data.perks.perks_class_0000 import 퍽목록
from game.system import dice_utils, effect_engine
from game.system.combat import attacks, damage, stats, status, traits
from tests import support


def _전장(특성이름=None):
    random.seed(5)
    상태 = support.새게임([("", "귀검사"), ("", "격투가")])
    gf.전투_시작(상태, ["고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    for p in 전투상태["참가자"]:
        p["현재HP"] = 999
    고블린 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
    귀검사 = next(p for p in 전투상태["참가자"] if p["진영"] == "아군")
    if 특성이름:
        effect_engine.특성_부여(귀검사["원본"], 특성이름, 특성목록[특성이름])
    return 전투상태, 고블린, 귀검사


@pytest.mark.parametrize(
    "퍽이름, 차수",
    [("만독불침", 1), ("웨펀브레이커", 2), ("아머브레이커", 2), ("심안", 4)],
)
def test_전투_특성_퍽은_선행없는_특성획득이다(퍽이름, 차수):
    퍽 = 퍽목록[퍽이름]
    assert (퍽["분류"], 퍽["차수"], 퍽["선행조건"]) == ("특성획득", 차수, None)
    assert 퍽["획득특성"] == 퍽이름
    assert 퍽이름 in 특성목록


# ------------------------------------------------------------------ 만독불침


def test_만독불침은_건강_1을_올린다():
    캐릭터 = support.새게임([("", "귀검사")])["파티"]["파티원"][0]
    전 = 캐릭터["건강"]
    effect_engine.특성_부여(캐릭터, "만독불침", 특성목록["만독불침"])
    assert 캐릭터["건강"] == 전 + 1


def test_만독불침은_중독에_걸리지_않는다():
    전투상태, 고블린, 귀검사 = _전장("만독불침")
    assert status.상태이상_면역(전투상태, 귀검사, "중독")
    assert not status.상태이상_면역(전투상태, 귀검사, "출혈")
    traits.상태이상_효과_적용(
        전투상태, 고블린, 귀검사, {"종류": "상태이상", "이름": "중독"}, "시험"
    )
    assert not any(s["이름"] == "중독" for s in 귀검사["상태이상"])


def test_퍽이_없으면_중독에_걸린다():
    전투상태, 고블린, 귀검사 = _전장()
    assert not status.상태이상_면역(전투상태, 귀검사, "중독")
    traits.상태이상_효과_적용(
        전투상태, 고블린, 귀검사, {"종류": "상태이상", "이름": "중독"}, "시험"
    )
    assert any(s["이름"] == "중독" for s in 귀검사["상태이상"])


# ------------------------------------------------------------------ 심안


def _굴림_기록(monkeypatch):
    기록 = []

    def 굴림(이점=False, 불리=False):
        기록.append((이점, 불리))
        return 10

    monkeypatch.setattr(damage.dice_utils, "d20_굴림", 굴림)
    return 기록


def test_심안은_암흑에_걸리지_않는다():
    전투상태, 고블린, 귀검사 = _전장("심안")
    assert status.상태이상_면역(전투상태, 귀검사, "암흑")


def test_심안은_공격할_때_이점(monkeypatch):
    전투상태, 고블린, 귀검사 = _전장("심안")
    기록 = _굴림_기록(monkeypatch)
    damage.명중_판정_계산(전투상태, 귀검사, 고블린, "보정명중률")
    assert 기록 == [(True, False)]


def test_심안을_공격하는_상대는_불리점(monkeypatch):
    전투상태, 고블린, 귀검사 = _전장("심안")
    기록 = _굴림_기록(monkeypatch)
    damage.명중_판정_계산(전투상태, 고블린, 귀검사, "보정명중률")
    assert 기록 == [(False, True)]


def test_심안이_없으면_이점도_불리점도_없다(monkeypatch):
    전투상태, 고블린, 귀검사 = _전장()
    기록 = _굴림_기록(monkeypatch)
    damage.명중_판정_계산(전투상태, 귀검사, 고블린, "보정명중률")
    damage.명중_판정_계산(전투상태, 고블린, 귀검사, "보정명중률")
    assert 기록 == [(False, False), (False, False)]


# ------------------------------------------------------------------ 웨펀/아머브레이커


def _명중시키기(monkeypatch, 고블린):
    고블린["원본"]["AC보너스"] = -99
    monkeypatch.setattr(dice_utils.random, "randint", lambda a, b: min(max(10, a), b))


@pytest.mark.parametrize(
    "퍽이름, 디버프, 변동대상",
    [
        ("웨펀브레이커", "데미지차감", "데미지보너스"),
        ("아머브레이커", "방어감소", "방어력"),
    ],
)
def test_브레이커는_명중마다_1씩_최대_10중첩(monkeypatch, 퍽이름, 디버프, 변동대상):
    전투상태, 고블린, 귀검사 = _전장(퍽이름)
    _명중시키기(monkeypatch, 고블린)
    전 = stats.버프디버프_수치(전투상태, 고블린, 변동대상)
    결과 = attacks.일반공격_실행(전투상태, 귀검사, 고블린)
    assert 결과["판정"]["성공"]
    걸린 = [d for d in 고블린["디버프"] if d["이름"] == 디버프]
    assert len(걸린) == 1 and "지속턴" not in 걸린[0]  # 전투가 끝날 때까지
    for _ in range(12):
        고블린["현재HP"] = 999
        attacks.일반공격_실행(전투상태, 귀검사, 고블린)
    assert sum(1 for d in 고블린["디버프"] if d["이름"] == 디버프) == 10
    assert stats.버프디버프_수치(전투상태, 고블린, 변동대상) == 전 - 10


def test_브레이커는_빗나가면_걸지_않는다(monkeypatch):
    전투상태, 고블린, 귀검사 = _전장("웨펀브레이커")
    고블린["원본"]["AC보너스"] = 99
    monkeypatch.setattr(dice_utils.random, "randint", lambda a, b: min(max(10, a), b))
    결과 = attacks.일반공격_실행(전투상태, 귀검사, 고블린)
    assert not 결과["판정"]["성공"]
    assert not 고블린["디버프"]


def test_브레이커가_없으면_명중해도_디버프가_없다(monkeypatch):
    전투상태, 고블린, 귀검사 = _전장()
    _명중시키기(monkeypatch, 고블린)
    assert attacks.일반공격_실행(전투상태, 귀검사, 고블린)["판정"]["성공"]
    assert not 고블린["디버프"]
