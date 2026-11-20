"""던전 공용 보석 드랍 - 기본보석군(모든 던전)과 하늘성보석군(하늘성 던전), 그 재료의 도감.

규칙은 docs/game-rules.md "던전 공용 드랍".
"""

import gameflow as gf
from game.controller.ctl_registry import 던전_레지스트리
from game.data.monster.monster_drop import 드랍표_모음
from game.system import loot_system, rng
from tests import support

기본보석 = ["오닉스", "아쿠아마린", "다이아몬드", "혈류석", "옵시디언"]
하늘성보석 = ["스피넬", "지르콘", "플로라이트"]
하늘성던전 = [
    "dungeon_02A_D11_amon_lower",
    "dungeon_02A_D12_amon_upper",
    "dungeon_02A_D13_sephiroth_lower",
    "dungeon_02A_D14_sephiroth_upper",
    "dungeon_02A_D15_middleocean_shallow",
    "dungeon_02A_D16_middleocean_deep",
    "dungeon_02A_D17_floating_castle",
]


def _확률표(표이름):
    표 = 드랍표_모음[표이름]
    assert 표["타입"] == "독립형"
    return {h["아이템이름"]: h["드랍확률"] for h in 표["아이템"]}


def _던전드랍(던전):
    return {d["이름"]: d["발동확률"] for d in 던전_레지스트리[던전].get("드랍표", [])}


def test_기본보석군은_보석마다_2퍼센트_라이언_코크스_30퍼센트로_따로_굴린다():
    assert _확률표("기본보석군") == {
        **dict.fromkeys(기본보석, 0.02),
        "라이언 코크스": 0.3,
    }


def test_하늘성보석군은_보석마다_2퍼센트로_따로_굴린다():
    assert _확률표("하늘성보석군") == dict.fromkeys(하늘성보석, 0.02)


def test_모든_던전에_기본보석군이_100퍼센트로_들어간다():
    assert len(던전_레지스트리) >= 17
    for 던전 in 던전_레지스트리:
        assert _던전드랍(던전).get("기본보석군") == 1.0, 던전


def test_하늘성_던전에만_하늘성보석군이_100퍼센트로_들어간다():
    for 던전 in 던전_레지스트리:
        기대 = 1.0 if 던전 in 하늘성던전 else None
        assert _던전드랍(던전).get("하늘성보석군") == 기대, 던전


def test_따로_굴리면_한_번에_여러_개가_나올_수_있다(monkeypatch):
    monkeypatch.setattr(rng.보상, "random", lambda: 0.0)
    assert loot_system.드랍표_굴림(드랍표_모음["기본보석군"], {}) == [
        *기본보석,
        "라이언 코크스",
    ]
    monkeypatch.setattr(rng.보상, "random", lambda: 0.1)
    assert loot_system.드랍표_굴림(드랍표_모음["기본보석군"], {}) == ["라이언 코크스"]


def test_보석과_강화재료가_재료_도감에_나온다():
    상태 = support.새게임([("", "귀검사")])
    탭 = [t for 줄 in gf.도감_탭줄(상태, "재료") for t in 줄]
    assert "보석" in 탭 and "강화재료" in 탭
    보석 = [a["이름"] for a, _ in gf.도감_목록(상태, "재료", "보석")]
    assert 보석 == 기본보석 + 하늘성보석
    강화재료 = [a["이름"] for a, _ in gf.도감_목록(상태, "재료", "강화재료")]
    # 모순의 결정체/강렬한 기운은 드랍되지 않지만 연금술로 얻으므로 도감에 있다
    assert 강화재료 == ["라이언 코크스", "모순의 결정체", "강렬한 기운"]
