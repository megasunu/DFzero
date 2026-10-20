"""버서커(013m) 전직 특성/스킬/퍽 규칙 (#247, 2026-10-20 사용자 결정)."""

import random

import pytest

import gameflow as gf
from game.system import dice_utils, skill_system as ss
from game.system.combat import damage, status, stats, traits
from tests import support


@pytest.fixture
def 버서커전장():
    """귀검사 -> 버서커 레벨 8(스킬 전부 습득)과 격투가, 고블린 셋."""
    random.seed(7)
    상태 = support.새게임([("", "귀검사"), ("", "격투가")])
    c = 상태["파티"]["파티원"][0]
    support.성장(상태, c, 8, 전직="버서커", 스킬습득=True)
    gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    적 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "적"),
        key=lambda p: p["대형위치"],
    )
    bs = next(p for p in 전투상태["참가자"] if p["원본"].get("전직") == "버서커")
    for p in 적:
        p["현재HP"] = 999
    return 상태, 전투상태, 적, bs


def _주사위고정(monkeypatch, 값):
    monkeypatch.setattr(dice_utils.random, "randint", lambda a, b: min(max(값, a), b))


def _스킬(이름):
    return dict(gf.스킬데이터모음_생성()[이름], _이름=이름)


def _명중():
    return {"성공": True, "자연눈": 15, "치명타": False, "자동실패": False}


def _특성_빼기(bs, 이름):
    bs["원본"]["보유특성"] = [n for n in bs["원본"]["보유특성"] if n != 이름]


def _쓰기(전투상태, bs, 이름, 대상=None):
    bs["행동자원"].update(일반행동=1, 보조행동=1)
    return ss.스킬_실행(전투상태, bs, 이름, _스킬(이름), 대상)


# ------------------------------------------------------------------ 직업스타일, 레벨 6


def test_버서커는_하이브리드이고_레벨6에_혈기왕성과_혈십자를_얻는다(버서커전장):
    상태, _, _, bs = 버서커전장
    c = bs["원본"]
    assert gf.캐릭터_직업표시(c).startswith("버서커")
    assert c["직업스타일"] == "하이브리드"
    assert {"혈기왕성", "혈십자"} <= set(c["보유특성"])


def test_혈기왕성은_MP_대신_절반을_올림한_HP를_쓴다(버서커전장):
    _, 전투상태, 적, bs = 버서커전장
    bs["현재HP"], MP = 20, bs["현재MP"]
    _쓰기(전투상태, bs, "귀신 : 카잔")  # MP 10 -> HP 5
    assert (bs["현재HP"], bs["현재MP"]) == (15, MP)
    _쓰기(전투상태, bs, "블러드 러스트", 적[0])  # MP 5 -> HP 3(2.5 올림)
    assert (bs["현재HP"], bs["현재MP"]) == (12, MP)


def test_혈기왕성은_HP를_1_아래로_내리지_않고_MP가_없어도_쓴다(버서커전장):
    _, 전투상태, _, bs = 버서커전장
    bs["현재HP"], bs["현재MP"] = 2, 0
    assert ss.사용_가능여부(전투상태, bs, _스킬("귀신 : 카잔"))[0]
    _쓰기(전투상태, bs, "귀신 : 카잔")
    assert (bs["현재HP"], bs["현재MP"]) == (1, 0)


def test_혈기왕성이_없으면_MP를_쓴다(버서커전장):
    _, 전투상태, _, bs = 버서커전장
    _특성_빼기(bs, "혈기왕성")
    bs["현재HP"], bs["현재MP"] = 20, 30
    _쓰기(전투상태, bs, "귀신 : 카잔")
    assert (bs["현재HP"], bs["현재MP"]) == (20, 20)


def test_전투_스킬창은_혈기왕성이면_HP_비용을_보인다(버서커전장):
    상태, _, _, bs = 버서커전장
    assert gf.스킬_팝업_줄(상태, bs, "귀신 : 카잔")["MP"] == "HP 5"
    assert gf.스킬_팝업_줄(상태, bs, "블러드 러스트")["MP"] == "HP 3"


@pytest.mark.parametrize(
    "비율,단계", [(1.0, 1), (0.7, 2), (0.5, 3), (0.3, 4), (0.0, 5)]
)
def test_혈십자는_HP가_낮을수록_단계마다_명중_AC_속도가_1씩_오른다(
    버서커전장, 비율, 단계
):
    _, 전투상태, _, bs = 버서커전장
    bs["현재HP"] = max(1, int(stats.유효_최대HP(전투상태, bs) * 비율))

    def 값들():
        return tuple(
            traits.특성_수치(전투상태, bs, 이름)
            for 이름 in ("명중보너스", "AC", "속도")
        )

    있음 = 값들()
    _특성_빼기(bs, "혈십자")
    없음 = 값들()
    assert tuple(a - b for a, b in zip(있음, 없음)) == (단계, 단계, 단계)


def test_혈십자_단계는_경계에서_높은_단계다():
    assert [traits.혈십자_단계(h, 100) for h in (100, 81, 80, 61, 60, 41, 40)] == [
        1,
        1,
        2,
        2,
        3,
        3,
        4,
    ]
    assert [traits.혈십자_단계(h, 100) for h in (21, 20, 1, 0)] == [4, 5, 5, 5]
    assert traits.혈십자_단계(13, 25) == 3  # 52%


# ------------------------------------------------------------------ 레벨 8 폭주


def _폭주_걸기(전투상태, bs):
    return _쓰기(전투상태, bs, "폭주")


def test_폭주는_레벨8_버프이고_행동없이_HP_5로_10턴_휴식당_1회다(버서커전장):
    _, 전투상태, _, bs = 버서커전장
    폭주 = _스킬("폭주")
    assert "폭주" in bs["원본"]["보유스킬"]
    assert (폭주["습득방법"], 폭주["행동"], 폭주["타겟"]) == ("레벨진행", None, "자신")
    assert (폭주["MP소모"], 폭주["휴식당횟수"]) == (10, 1)
    bs["현재HP"] = 30
    행동 = dict(bs["행동자원"])
    _폭주_걸기(전투상태, bs)
    assert bs["현재HP"] == 25  # 혈기왕성: MP 10 -> HP 5
    assert [(b["이름"], b["지속턴"]) for b in bs["버프"]] == [("폭주", 10)]
    assert not ss.사용_가능여부(전투상태, bs, 폭주)[0]
    assert {k: bs["행동자원"][k] for k in 행동} == {
        **행동,
        "일반행동": 1,
        "보조행동": 1,
    }  # _쓰기가 채운 행동이 그대로 - 행동을 쓰지 않는다


def test_폭주는_공격에_이점_피격에_공격자_이점을_준다(버서커전장, monkeypatch):
    _, 전투상태, 적, bs = 버서커전장
    굴림 = []
    원래 = damage.dice_utils.d20_굴림

    def 기록(이점=False, 불리=False):
        굴림.append((이점, 불리))
        return 원래(이점=이점, 불리=불리)

    monkeypatch.setattr(damage.dice_utils, "d20_굴림", 기록)
    damage.명중_판정_계산(전투상태, bs, 적[0], "보정명중률")
    damage.명중_판정_계산(전투상태, 적[0], bs, "근력판정")
    assert 굴림 == [(False, False), (False, False)]
    _폭주_걸기(전투상태, bs)
    damage.명중_판정_계산(전투상태, bs, 적[0], "보정명중률")
    damage.명중_판정_계산(전투상태, 적[0], bs, "근력판정")
    assert 굴림[2:] == [(True, False), (True, False)]


def test_폭주는_무력화CC_면역이고_약화CC와_지속피해_내성에_이점이다(버서커전장):
    _, 전투상태, _, bs = 버서커전장
    assert not status.상태이상_면역(전투상태, bs, "기절")
    assert not traits.상태이상_내성이점(전투상태, bs, "둔화")
    _폭주_걸기(전투상태, bs)
    assert all(
        status.상태이상_면역(전투상태, bs, n)
        for n in ("기절", "공중에뜸", "수면", "빙결", "석화")
    )
    assert not status.상태이상_면역(전투상태, bs, "둔화")
    assert all(
        traits.상태이상_내성이점(전투상태, bs, n)
        for n in ("둔화", "넘어짐", "출혈", "중독")
    )
    assert not traits.상태이상_내성이점(전투상태, bs, "은신")


def test_폭주_중_무력화_상태이상은_걸리지_않는다(버서커전장):
    _, 전투상태, _, bs = 버서커전장
    _폭주_걸기(전투상태, bs)
    ss.상태이상_부여(전투상태, bs, "기절", 1)
    assert all(s["이름"] != "기절" for s in bs["상태이상"])
