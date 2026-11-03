"""몬스터 칭호 "챔피언"(#546) - 인카운트에서 붙이기, 공통 효과, 돌연변이, 챔피언 버프, 이름 표시, 골드."""

import pytest

import gameflow as gf
from game.controller.ctl_registry import 전투용_몬스터특성정의
from game.data.buff.status_effects import 상태이상목록
from game.data.monster import monster_title
from game.system import dungeon_system, loot_system, rng
from game.system.combat import damage, monster_actions, stats, status, traits
from game.system.combat import formula
from tests.support import 새게임, 전투_열기


def _챔피언(이름="고블린", 돌연변이="돌연변이", 버프=()):
    return {
        "이름": 이름,
        "칭호": "챔피언",
        "돌연변이": 돌연변이,
        "챔피언버프": list(버프),
    }


def _전투(몬스터들):
    rng.시드(3)
    상태 = 새게임()
    전투_열기(상태, 몬스터들)
    return 상태


def _적(상태, 몬스터명, 챔피언=None):
    for p in gf.적_목록(상태):
        if p["원본"]["몬스터명"] != 몬스터명:
            continue
        if 챔피언 is None or (p["원본"].get("칭호") == "챔피언") == 챔피언:
            return p
    raise AssertionError(몬스터명)


def _명중(전투상태, p):
    return traits.특성_수치(전투상태, p, "명중보너스") + traits.칭호_수치(
        전투상태, p, "명중보너스"
    )


# ---------------------------------------------------------------- 붙이기


def test_챔피언은_보스가_아닌_일반과_엘리트에게만_붙는다(monkeypatch):
    monkeypatch.setattr(dungeon_system, "챔피언_확률", 1.0)
    rng.시드(1)
    결과 = dungeon_system.챔피언_부여(
        ["고블린", "플래그 힐가브", "전격의 키놀"], gf.몬스터목록
    )
    assert [항목 if isinstance(항목, str) else 항목["칭호"] for 항목 in 결과] == [
        "챔피언",
        "챔피언",
        "전격의 키놀",
    ]
    for 항목 in 결과[:2]:
        assert 항목["돌연변이"] in monster_title.챔피언_돌연변이
        버프 = 항목["챔피언버프"]
        assert 1 <= len(버프) <= 5
        assert len(set(버프)) == len(버프)
        assert set(버프) <= set(monster_title.챔피언버프_뽑기목록)


def test_챔피언_확률이_빗나가면_이름_그대로다(monkeypatch):
    monkeypatch.setattr(dungeon_system, "챔피언_확률", 0.0)
    assert dungeon_system.챔피언_부여(["고블린", "고블린"], gf.몬스터목록) == [
        "고블린",
        "고블린",
    ]


def test_챔피언_확률은_10퍼센트다():
    assert dungeon_system.챔피언_확률 == 0.1


def test_챔피언_버프_개수는_1에서_5개_사이로_고르게_나온다(monkeypatch):
    monkeypatch.setattr(dungeon_system, "챔피언_확률", 1.0)
    rng.시드(7)
    개수 = {
        len(dungeon_system.챔피언_부여(["고블린"], gf.몬스터목록)[0]["챔피언버프"])
        for _ in range(200)
    }
    assert 개수 == {1, 2, 3, 4, 5}


def test_챔피언_버프_뽑기목록에는_정의된_버프만_있다():
    정의 = 전투용_몬스터특성정의
    for 이름 in monster_title.챔피언버프_뽑기목록:
        assert 정의[이름]["분류"] == "챔피언버프", 이름


def test_무작위_인카운트_전투에_챔피언이_붙는다(monkeypatch):
    monkeypatch.setattr(dungeon_system, "챔피언_확률", 1.0)
    monkeypatch.setattr(
        dungeon_system, "인카운트_판정", lambda *_: {"등장몬스터": ["고블린"]}
    )
    rng.시드(2)
    상태 = 새게임()
    gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
    for 방향 in ("위", "아래", "왼쪽", "오른쪽"):
        결과 = gf.던전_이동(상태, 방향)
        if 결과["결과"] == "전투시작":
            break
    else:
        pytest.fail("인카운트 전투가 열리지 않았다")
    적 = gf.적_목록(상태)[0]
    assert 적["원본"]["칭호"] == "챔피언"
    assert 적["이름"].startswith("[") and 적["이름"].endswith("챔피언-고블린]")


# ---------------------------------------------------------------- 공통 효과와 이름


def test_챔피언은_HP_1점5배_AC_명중_데미지보너스가_1씩_오른다():
    상태 = _전투(["고블린", _챔피언()])
    전투상태 = 상태["전투상태"]
    보통, 챔피언 = _적(상태, "고블린", False), _적(상태, "고블린", True)
    기본 = 보통["기본최대HP"]
    assert stats.유효_최대HP(전투상태, 보통) == 기본 - 1  # 종족:고블린 -1
    assert stats.유효_최대HP(전투상태, 챔피언) == formula.올림(기본 * 1.5) - 1
    assert stats.최종AC(전투상태, 챔피언) == stats.최종AC(전투상태, 보통) + 1
    assert _명중(전투상태, 챔피언) == _명중(전투상태, 보통) + 1
    # 돌연변이(돌연변이:무)의 데미지보너스 2까지 더해 3
    assert (
        monster_actions.몬스터_데미지보너스(전투상태, 챔피언)
        == monster_actions.몬스터_데미지보너스(전투상태, 보통) + 3
    )


def test_챔피언_이름은_돌연변이_접두와_함께_앞에_붙는다():
    상태 = _전투([_챔피언("고블린", "불타는")])
    assert gf.적_목록(상태)[0]["이름"] == "[불타는 챔피언-고블린]"


def test_보스_이름은_보스_칭호가_앞에_붙는다():
    상태 = _전투([{"이름": "전격의 키놀", "칭호": "보스"}])
    assert gf.적_목록(상태)[0]["이름"] == "[보스-전격의 키놀]"


def test_챔피언_골드는_두_배다():
    원본 = dict(gf.몬스터목록["고블린"], 레벨=3)
    assert loot_system.공식_골드(
        dict(원본, 칭호="챔피언")
    ) == 2 * loot_system.공식_골드(원본)


def test_전투_시작에_챔피언_버프를_알린다():
    상태 = _전투([_챔피언("고블린", "싸늘한", ["경화", "불멸의"])])
    assert any(
        항목.get("공격자") == "[싸늘한 챔피언-고블린]"
        and 항목.get("비고") == "챔피언 버프 - 경화, 불멸의"
        for 항목 in 상태["전투상태"]["로그"]
    )


# ---------------------------------------------------------------- 돌연변이


@pytest.mark.parametrize(
    "접두, 특성",
    [
        ("돌연변이", "돌연변이:무"),
        ("불타는", "돌연변이:화"),
        ("싸늘한", "돌연변이:수"),
        ("빛나는", "돌연변이:명"),
        ("저주받은", "돌연변이:암"),
    ],
)
def test_돌연변이_접두는_그_돌연변이_특성을_준다(접두, 특성):
    상태 = _전투([_챔피언("고블린", 접두)])
    assert 특성 in gf.적_목록(상태)[0]["원본"]["특성"]


def test_이미_있는_돌연변이는_하나만_적용된다():
    상태 = _전투([_챔피언("전격의 키놀", "빛나는")])
    assert gf.적_목록(상태)[0]["원본"]["특성"].count("돌연변이:명") == 1


def test_돌연변이_무는_무속성_저항과_데미지보너스_2다():
    상태 = _전투([_챔피언("고블린", "돌연변이")])
    전투상태 = 상태["전투상태"]
    챔피언 = gf.적_목록(상태)[0]
    assert damage.속성_피해배율(전투상태, 챔피언, "무속성") == 0.5
    assert traits.특성_수치(전투상태, 챔피언, "데미지보너스") == 2 - 1  # 종족:고블린 -1


# ---------------------------------------------------------------- 챔피언 버프


def test_가속_공격은_명중보너스_2다():
    상태 = _전투([_챔피언(), _챔피언(버프=["가속-공격"])])
    a, b = gf.적_목록(상태)
    assert _명중(상태["전투상태"], b) == _명중(상태["전투상태"], a) + 2


def test_강화_공격력은_데미지보너스_2다():
    상태 = _전투([_챔피언(), _챔피언(버프=["강화-공격력"])])
    전투상태 = 상태["전투상태"]
    a, b = gf.적_목록(상태)
    assert (
        monster_actions.몬스터_데미지보너스(전투상태, b)
        == monster_actions.몬스터_데미지보너스(전투상태, a) + 2
    )


def test_경화는_방어력과_보호률_2다():
    상태 = _전투([_챔피언(), _챔피언(버프=["경화"])])
    전투상태 = 상태["전투상태"]
    a, b = gf.적_목록(상태)
    assert stats.유효_방어력(전투상태, b) == stats.유효_방어력(전투상태, a) + 2
    assert stats.유효_보호률(전투상태, b) == stats.유효_보호률(전투상태, a) + 2


def test_가속_히트커버리는_경직을_받지_않는다():
    상태 = _전투([_챔피언(버프=["가속-히트커버리"])])
    챔피언 = gf.적_목록(상태)[0]
    전 = (챔피언["우선도"], 챔피언["이니셔티브"])
    damage.경직_적용(상태["전투상태"], 챔피언)
    damage.경직_적용(상태["전투상태"], 챔피언, 태그=("잡기",))
    assert (챔피언["우선도"], 챔피언["이니셔티브"]) == 전


@pytest.mark.parametrize("속성", ["화속성", "수속성", "명속성", "암속성"])
def test_이뮨_속성은_그_속성_피해가_0이다(속성):
    상태 = _전투([_챔피언(버프=[f"이뮨-{속성}"])])
    챔피언 = gf.적_목록(상태)[0]
    assert damage.속성_피해배율(상태["전투상태"], 챔피언, 속성) == 0.0


def test_이뮨_상태변화는_지속피해와_CC에_면역이다():
    상태 = _전투([_챔피언(버프=["이뮨-상태변화"])])
    전투상태, 챔피언 = 상태["전투상태"], gf.적_목록(상태)[0]
    해로운 = [
        이름
        for 이름, 정의 in 상태이상목록.items()
        if 정의["분류"] in ("지속피해형", "약화CC", "무력화CC")
    ]
    assert {"출혈", "암흑", "기절"} <= set(해로운)
    assert all(status.상태이상_면역(전투상태, 챔피언, 이름) for 이름 in 해로운)
    assert not status.상태이상_면역(전투상태, 챔피언, "축복")


def test_기타_뜨지않음은_공중에뜸_면역이다():
    상태 = _전투([_챔피언(버프=["기타-뜨지않음"])])
    assert status.상태이상_면역(상태["전투상태"], gf.적_목록(상태)[0], "공중에뜸")


def test_챔피언_최대HP는_정수로_올림한다():
    상태 = _전투([_챔피언()])
    챔피언 = gf.적_목록(상태)[0]
    assert isinstance(stats.유효_최대HP(상태["전투상태"], 챔피언), int)


def test_불멸의는_최대HP가_총_3배다():
    상태 = _전투([_챔피언(), _챔피언(버프=["불멸의"])])
    전투상태 = 상태["전투상태"]
    a, b = gf.적_목록(상태)
    기본 = a["기본최대HP"]
    assert stats.유효_최대HP(전투상태, b) == 2 * stats.유효_최대HP(전투상태, a)
    assert stats.유효_최대HP(전투상태, a) == formula.올림(기본 * 1.5) - 1
    assert b["현재HP"] == stats.유효_최대HP(전투상태, b)
