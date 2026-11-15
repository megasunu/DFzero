# 데이터 칸이 문자열 하나 또는 목록 두 형태로 오는 곳 - 둘 다 같은 뜻으로 읽는지(#653 #654 #657 #662).

import gameflow as gf
from game.controller import ctl_autobattle, ctl_skills
from game.system import character_levelup_system as 캐릭터레벨업
from game.system import effect_engine, rng
from tests import support


# ------------------------------------------------------------------ #654 훔쳐배우기 특성 구매항목의 "타입"


def test_특성_구매항목의_문자열_타입은_글자로_쪼개지_않는다():
    assert ctl_skills._특성_구매항목({"타입": "스탯획득"})["타입"] == ["스탯획득"]


def test_특성_구매항목의_목록_타입은_그대로다():
    assert ctl_skills._특성_구매항목({"타입": ["스탯획득", "면역특성"]})["타입"] == [
        "스탯획득",
        "면역특성",
    ]


def test_특성_구매항목의_타입이_없으면_빈_목록이다():
    assert ctl_skills._특성_구매항목({})["타입"] == []


# ------------------------------------------------------------------ #653 대체특성 제거


def _대체특성_제거_결과(monkeypatch, 보유특성정의):
    뺀것 = []
    monkeypatch.setattr(
        effect_engine, "특성_제거", lambda 캐릭터, 이름, 정의: 뺀것.append(이름)
    )
    캐릭터 = {"보유특성": list(보유특성정의)}
    캐릭터레벨업._대체특성_제거(캐릭터, {"대체특성타입": "마스터리"}, 보유특성정의)
    return 뺀것


def test_대체특성은_문자열_타입_특성을_뺀다(monkeypatch):
    assert _대체특성_제거_결과(
        monkeypatch, {"가": {"타입": "마스터리"}, "나": {"타입": "기타"}}
    ) == ["가"]


def test_대체특성은_목록_타입_특성도_뺀다(monkeypatch):
    정의 = {
        "가": {"타입": ["스탯획득", "마스터리"]},
        "나": {"타입": ["기타"]},
        "다": {},
    }
    assert _대체특성_제거_결과(monkeypatch, 정의) == ["가"]


# ------------------------------------------------------------------ #662 퍽 숨김 - 목록형 획득스킬


def _캐릭터():
    rng.시드(1)
    상태 = support.새게임([("", "귀검사")])
    return 상태["파티"]["파티원"][0]


def test_목록형_획득스킬을_모두_배운_스킬획득_퍽은_숨긴다():
    c = _캐릭터()
    c["보유스킬"] += ["가스킬", "나스킬"]
    assert (
        gf.퍽_선택상태(c, {"타입": ["스킬획득"], "획득스킬": ["가스킬", "나스킬"]})
        is None
    )


def test_목록형_획득스킬을_일부만_배웠으면_숨기지_않는다():
    c = _캐릭터()
    c["보유스킬"] += ["가스킬"]
    assert (
        gf.퍽_선택상태(c, {"타입": ["스킬획득"], "획득스킬": ["가스킬", "나스킬"]})
        is not None
    )


def test_문자열_획득스킬을_배운_퍽은_그대로_숨긴다():
    c = _캐릭터()
    c["보유스킬"] += ["가스킬"]
    assert gf.퍽_선택상태(c, {"타입": ["스킬획득"], "획득스킬": "가스킬"}) is None


# ------------------------------------------------------------------ #657 자동전투 - 행동이 목록인 공격스킬


def _공격스킬_쓸만한가(monkeypatch, 행동, 기대):
    monkeypatch.setattr(ctl_autobattle, "공격_평가", lambda 상태, 참가자, 이름: 기대)
    monkeypatch.setattr(ctl_autobattle, "일반공격_기대피해", lambda 상태, 참가자: 10)
    return ctl_autobattle._전력전투_쓸만한가(
        {}, {}, "시험스킬", {"분류": "공격스킬", "행동": 행동}
    )


def test_행동이_목록이어도_일반행동이면_일반공격보다_약할_때_쓰지_않는다(monkeypatch):
    assert not _공격스킬_쓸만한가(monkeypatch, ["일반행동", "보조행동"], 5)
    assert _공격스킬_쓸만한가(monkeypatch, ["일반행동", "보조행동"], 15)


def test_행동이_문자열_일반행동이면_같은_기준이다(monkeypatch):
    assert not _공격스킬_쓸만한가(monkeypatch, "일반행동", 5)
    assert _공격스킬_쓸만한가(monkeypatch, "일반행동", 15)


def test_보조행동_공격스킬은_일반공격과_비교하지_않는다(monkeypatch):
    assert _공격스킬_쓸만한가(monkeypatch, "보조행동", 5)
