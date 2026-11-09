"""격투가(020f) 1차 계열 규칙 - 분신(#278, 2026-10-20 사용자 결정 / #616, 2026-11-09 개편)."""

import pytest

from game.system import rng
import gameflow as gf
from game.system import skill_system as ss
from game.system.combat import damage, monster_actions, stats
from tests import support


@pytest.fixture
def 격투가전장():
    """격투가 레벨 3(분신 습득)과 고블린 둘."""
    rng.시드(3)
    상태 = support.새게임([("", "격투가")])
    c = 상태["파티"]["파티원"][0]
    support.성장(상태, c, 3)
    assert "분신" in c["보유스킬"]
    c[c["주문시전능력치"]] = (
        16  # 주문시전보정치 +3 - 레벨 3 기본값(+0)이면 실드가 0이다
    )
    gf.전투_시작(상태, ["고블린", "고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    격 = next(p for p in 전투상태["참가자"] if p["진영"] == "아군")
    적 = [p for p in 전투상태["참가자"] if p["진영"] == "적"]
    return 전투상태, 격, 적


def _스킬(이름):
    return dict(gf.스킬데이터모음_생성()[이름], _이름=이름)


def _분신(전투상태, 격):
    격["행동자원"].update(일반행동=1, 보조행동=1)
    격["현재MP"] = 99
    return ss.스킬_실행(전투상태, 격, "분신", _스킬("분신"))


def _분신버프(격):
    return next((b for b in 격["버프"] if b["이름"] == "분신"), None)


def _분신수(격):
    항목 = _분신버프(격)
    return None if 항목 is None else 항목.get("분신수")


def _빗나감(전투상태, 적, 격, monkeypatch):
    """적의 공격이 격투가에게 빗나간다(자연 1)."""
    support.주사위고정(monkeypatch, 1)
    판정 = damage.명중_판정(전투상태, 적, 격, "근력판정")
    monkeypatch.undo()
    assert not 판정["성공"]
    return 판정


def test_분신은_차수더하기1개를_3턴_동안_만든다(격투가전장):
    전투상태, 격, _ = 격투가전장
    _분신(전투상태, 격)
    assert _분신수(격) == 2  # 비전직 차수 1 -> 2개 (2026-11-09 주인 결정 #616)
    assert _분신버프(격)["지속턴"] == 3


def test_분신은_1개당_AC2(격투가전장):
    전투상태, 격, _ = 격투가전장
    전 = stats.최종AC(전투상태, 격)
    _분신(전투상태, 격)
    assert stats.최종AC(전투상태, 격) == 전 + 2 * 2


def test_분신은_1개당_어그로2를_몬스터_대상_고르기에_더한다(격투가전장, monkeypatch):
    전투상태, 격, 적 = 격투가전장
    가중치 = []

    def 기록(목록, weights, k):
        가중치.append(list(weights))
        return [목록[0]]

    monkeypatch.setattr(rng.대상, "choices", 기록)
    monster_actions.몬스터_대상_선택(전투상태, 적[0], [격])
    _분신(전투상태, 격)
    monster_actions.몬스터_대상_선택(전투상태, 적[0], [격])
    배율 = 격["원본"].get("어그로배율", 1.0)
    assert 가중치[1][0] == pytest.approx(가중치[0][0] + 2 * 2 * 배율)


def test_적의_공격을_피할_때마다_분신이_1개_사라지고_로그를_남긴다(
    격투가전장, monkeypatch
):
    전투상태, 격, 적 = 격투가전장
    _분신(전투상태, 격)
    _빗나감(전투상태, 적[0], 격, monkeypatch)
    assert _분신수(격) == 1
    로그 = 전투상태.get("뒤따를로그", []) + 전투상태["로그"]
    assert any("분신" in str(e.get("비고", "")) for e in 로그)
    _빗나감(전투상태, 적[0], 격, monkeypatch)
    assert _분신버프(격) is None  # 마지막 분신이 사라지면 버프도 사라진다


def test_분신은_피해를_흡수하지_않는다(격투가전장):
    전투상태, 격, 적 = 격투가전장
    _분신(전투상태, 격)
    HP = 격["현재HP"]
    damage.피해_적용(전투상태, 격, 3, 공격자=적[0], 피해감소무시=True)
    assert 격["현재HP"] == HP - 3 and _분신수(격) == 2


def test_분신을_다시_쓰면_개수가_새로_채워진다(격투가전장, monkeypatch):
    전투상태, 격, 적 = 격투가전장
    _분신(전투상태, 격)
    _빗나감(전투상태, 적[0], 격, monkeypatch)
    assert _분신수(격) == 1
    _분신(전투상태, 격)
    assert _분신수(격) == 2
