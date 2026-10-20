"""귀검사 달빛베기와 소울브링어(012m) 전직 특성/스킬 규칙 (#244, 2026-10-20 사용자 결정)."""

import random

import pytest

import gameflow as gf
from game.system import dice_utils, skill_system as ss
from tests import support


@pytest.fixture
def 전장():
    random.seed(7)
    상태 = support.새게임([("", "귀검사"), ("", "격투가")])
    gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    적 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "적"),
        key=lambda p: p["대형위치"],
    )
    귀검사 = next(p for p in 전투상태["참가자"] if p["원본"]["직업"] == "귀검사")
    for p in 적:
        p["현재HP"] = 999
    return 상태, 전투상태, 적, 귀검사


def _주사위고정(monkeypatch, 값):
    monkeypatch.setattr(dice_utils.random, "randint", lambda a, b: min(max(값, a), b))


def _스킬(이름):
    return dict(gf.스킬데이터모음_생성()[이름], _이름=이름)


# ------------------------------------------------------------------ 달빛베기


def test_달빛베기는_레벨3_귀검사_스킬이고_1타_보정공격력_2타_무기공격력이다():
    달빛베기 = _스킬("달빛베기")
    assert 달빛베기["습득레벨"] == 3
    assert 달빛베기["행동"] == ["일반행동", "보조행동"]
    assert 달빛베기["MP소모"] == 5
    assert 달빛베기["일반공격취급"] is True
    assert 달빛베기["공격횟수"] == 2 and 달빛베기["각공격명중굴림"] is True
    assert 달빛베기["데미지"] == ["보정공격력", "무기공격력"]


def test_달빛베기의_공중에뜸은_2타에만_걸린다(전장, monkeypatch):
    _, 전투상태, 적, 귀검사 = 전장
    달빛베기 = dict(_스킬("달빛베기"), 명중률=["필중", "필중"])
    _주사위고정(monkeypatch, 1)  # 내성굴림 1 - 실패
    결과 = ss.공격스킬_실행(전투상태, 귀검사, 달빛베기, 적[0])
    첫타, 둘째타 = 결과["타격"]
    assert 첫타["효과로그"] == []
    assert any("공중에뜸" in 줄 for 줄 in 둘째타["효과로그"])
    assert [(s["이름"], s["지속턴"]) for s in 적[0]["상태이상"]] == [("공중에뜸", 1)]


def test_공중에뜸은_다시_걸려도_1턴에서_늘지_않는다(전장, monkeypatch):
    _, 전투상태, 적, 귀검사 = 전장
    달빛베기 = dict(_스킬("달빛베기"), 명중률=["필중", "필중"])
    _주사위고정(monkeypatch, 1)
    ss.공격스킬_실행(전투상태, 귀검사, 달빛베기, 적[0])
    ss.공격스킬_실행(전투상태, 귀검사, 달빛베기, 적[0])
    # 비중첩 상태이상도 다시 걸면 항목이 하나 더 생기지만(기존 동작) 모두 1턴이라 함께 끝난다
    assert {(s["이름"], s["지속턴"]) for s in 적[0]["상태이상"]} == {("공중에뜸", 1)}
