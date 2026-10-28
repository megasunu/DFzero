"""인형사 몬스터(2026-10-28 사용자 결정) - 진흙/돌/강철 인형사, 마스터 도그리와 그들이 쓰는 규칙:
상태이상패턴(피해 없이 상태이상만 거는 패턴).

규칙은 docs/game-rules.md "인형사 몬스터".
"""

from game.system import dice_utils, monster_ai
from game.system.combat import flow, monster_actions
from tests import support


def _한턴(전투상태, 몬스터, 패턴, 대상, monkeypatch):
    """몬스터가 패턴을 대상에게 한 번 쓴다(차수 1)."""
    monkeypatch.setattr(monster_ai, "행동_선택", lambda p: 패턴)
    monkeypatch.setattr(monster_ai, "타겟_선택", lambda *a, **k: 대상)
    전투상태["현재턴"] = 전투상태["참가자"].index(몬스터)
    flow.턴_시작_처리(전투상태, 몬스터)
    monster_actions.몬스터_턴_실행(전투상태, 몬스터)


def _상태이상들(참가자):
    return [(i["이름"], i["지속턴"]) for i in 참가자.get("상태이상", [])]


# ------------------------------------------------------------- 상태이상패턴


def _상태이상패턴(효과):
    return {
        "이름": "시험 상태이상",
        "타입": "상태이상패턴",
        "타겟": "적단일",
        "효과": 효과,
        "조건부효과": None,
        "설명": "",
    }


_암흑 = {
    "종류": "상태이상",
    "이름": "암흑",
    "내성": "지혜",
    "난이도": "10+지능보정치",
    "적용시점": "명중후",
    "지속턴": 2,
}


def test_상태이상패턴은_피해_없이_내성에_실패한_대상에게만_건다(monkeypatch):
    전투상태, [마녀], 아군 = support.시험_전투(["결빙의 케라하"])
    받은 = []

    def 내성(보정치, 난이도, **kw):
        받은.append(난이도)
        return False, 1

    monkeypatch.setattr(dice_utils, "내성_굴림", 내성)
    HP = {p["id"]: p["현재HP"] for p in 아군}
    _한턴(전투상태, 마녀, _상태이상패턴(_암흑), 아군[0], monkeypatch)
    assert _상태이상들(아군[0]) == [("암흑", 2)]
    assert 받은 == [10 + 3]  # 케라하 지능 16
    assert {p["id"]: p["현재HP"] for p in 아군} == HP


def test_상태이상패턴은_내성에_성공하면_걸리지_않는다(monkeypatch):
    전투상태, [마녀], 아군 = support.시험_전투(["결빙의 케라하"])
    monkeypatch.setattr(
        dice_utils, "내성_굴림", lambda 보정치, 난이도, **kw: (True, 20)
    )
    _한턴(전투상태, 마녀, _상태이상패턴(_암흑), 아군[0], monkeypatch)
    assert _상태이상들(아군[0]) == []


def test_내성_없는_상태이상패턴은_반드시_건다(monkeypatch):
    전투상태, [마녀], 아군 = support.시험_전투(["결빙의 케라하"])

    def 굴리면_안됨(*a, **k):
        raise AssertionError("내성 없는 효과는 굴리지 않는다")

    monkeypatch.setattr(dice_utils, "내성_굴림", 굴리면_안됨)
    혼란 = {"종류": "상태이상", "이름": "혼란", "지속턴": 2}
    _한턴(전투상태, 마녀, _상태이상패턴(혼란), 아군[1], monkeypatch)
    assert _상태이상들(아군[1]) == [("혼란", 2)]
