"""2차수(D11~) 레어 장비 드랍(2026-11-02 사용자 결정) - 레어무기군/레어방어구군/레어악세군과 그 셋을 고르는
레어장비군, D11~D17 던전 공용 드랍표의 레어장비군 30%."""

import pytest
from support import 새게임

import gameflow as gf
from game.data.monster.monster_drop import 드랍표_모음
from game.system import loot_system as 전리품
from game.system import rng

_탭별 = {
    "레어무기군": ["무기"],
    "레어방어구군": ["상의", "하의", "어깨", "벨트", "신발"],
    "레어악세군": ["목걸이", "반지", "팔찌"],
}
_하늘성 = [
    "dungeon_02A_D11_amon_lower",
    "dungeon_02A_D12_amon_upper",
    "dungeon_02A_D13_sephiroth_lower",
    "dungeon_02A_D14_sephiroth_upper",
    "dungeon_02A_D15_middleocean_shallow",
    "dungeon_02A_D16_middleocean_deep",
    "dungeon_02A_D17_floating_castle",
]


def _이름들(표):
    return [a["아이템이름"] for a in 드랍표_모음[표]["아이템"]]


def _레어_후보(카탈로그, 탭):
    """이름 있는 레어와 "마법으로 봉인된" 레어 - 봉인을 풀어 만드는 "마법의 ..." 변형과 치트는 뺀다."""
    return {
        n
        for n, d in 카탈로그[탭].items()
        if d.get("레어도") == "레어"
        and "치트" not in n
        and (n.startswith("마법으로 봉인된") or "마법봉인" not in d.get("타입", []))
    }


@pytest.mark.parametrize("표", list(_탭별))
def test_레어_군은_이름_있는_레어와_마법으로_봉인된_레어를_같은_비율로_고른다(표):
    카탈로그 = 새게임()["상점카탈로그"]["장비"]
    기대 = set().union(*(_레어_후보(카탈로그, 탭) for 탭 in _탭별[표]))
    봉인 = {n for n in 기대 if n.startswith("마법으로 봉인된")}
    assert 봉인 and 기대 - 봉인, 표  # 봉인된 것과 이름 있는 것이 둘 다 있다
    assert sorted(_이름들(표)) == sorted(기대)
    assert len({a["드랍비율"] for a in 드랍표_모음[표]["아이템"]}) == 1
    assert 드랍표_모음[표]["타입"] == "가중형"


def test_레어장비군은_무기_방어구_악세를_4_4_1로_고른다():
    assert 드랍표_모음["레어장비군"] == {
        "타입": "가중형",
        "아이템": [
            {"드랍표": "레어무기군", "드랍비율": 0.4},
            {"드랍표": "레어방어구군", "드랍비율": 0.4},
            {"드랍표": "레어악세군", "드랍비율": 0.1},
        ],
    }


@pytest.mark.parametrize("파일명", _하늘성)
def test_하늘성_던전_드랍표에_레어장비군_30퍼센트가_더해진다(파일명):
    assert gf.던전_레지스트리[파일명]["드랍표"] == [
        {"이름": "커먼장비군", "발동확률": 0.3},
        {"이름": "언커먼장비군", "발동확률": 0.3},
        {"이름": "레어장비군", "발동확률": 0.3},
    ]


def test_1차수_던전에는_레어장비군이_없다():
    for 파일명, 맵 in gf.던전_레지스트리.items():
        if "_01A_" in 파일명:
            assert all(
                참조["이름"] != "레어장비군" for 참조 in 맵.get("드랍표") or []
            ), 파일명


def test_아몬_하층에서_쓰러뜨린_몬스터가_실제로_레어를_떨어뜨린다():
    rng.시드(0)
    카탈로그 = 새게임()["상점카탈로그"]["장비"]
    레어 = set(_이름들("레어무기군") + _이름들("레어방어구군") + _이름들("레어악세군"))
    몬스터 = {"드랍표": gf.던전_레지스트리[_하늘성[0]]["드랍표"]}
    나온것 = []
    for _ in range(200):
        나온것 += 전리품.몬스터_전리품(몬스터, 드랍표_모음, 카탈로그)[1]
    나온레어 = [n for n in 나온것 if n in 레어]
    assert 나온레어
    assert {카탈로그_레어도(카탈로그, n) for n in 나온레어} == {"레어"}


def 카탈로그_레어도(카탈로그, 이름):
    return next(탭[이름]["레어도"] for 탭 in 카탈로그.values() if 이름 in 탭)
