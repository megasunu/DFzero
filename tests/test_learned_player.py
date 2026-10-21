"""밸런스 측정 조건과 배운 플레이어 - tests/scenario.py의 측정 파티 준비·실전·학습정책."""

import pytest

from game.system import rng
import gameflow as gf
from tests import support
from tests.support import 새게임


# ----------------------------------------- 밸런스 측정 조건 (tests/scenario.py)


@pytest.mark.parametrize("레벨, 인원", [(1, 0), (2, 1), (3, 2), (4, 3), (5, 4)])
def test_측정_파티_준비는_골드_스킬_없이_레벨별_언커먼_무기를_끼운다(레벨, 인원):
    import scenario

    상태 = 새게임()
    scenario.측정_파티_준비(상태, 레벨)
    파티 = 상태["파티"]["파티원"]
    레어도 = [gf.캐릭터_장착아이템(상태, c, "무기")["레어도"] for c in 파티]
    assert 레어도 == ["언커먼"] * 인원 + ["커먼"] * (len(파티) - 인원)
    for c in 파티:
        assert c["레벨"] == 레벨 and c["현재HP"] == gf.캐릭터_최대HP(상태, c)
        배운것 = set(c["보유스킬"]) & {
            이름 for 이름, _, _ in gf.캐릭터_습득가능_스킬(c)
        }
        assert not 배운것  # 골드 스킬은 배우지 않았다(아직 배울 수 있는 채로 남는다)
    if 레벨 >= 3:
        assert any(gf.캐릭터_습득가능_스킬(c) for c in 파티)


def test_측정_실전은_전투당_초보자용_포션을_한_번만_마신다():
    import scenario

    rng.시드(1)
    상태 = 새게임()
    scenario.측정_파티_준비(상태, 1)
    for c in 상태["파티"]["파티원"]:
        c["현재HP"] = 1  # 모두 절반 이하
    gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=1, 차수=1)
    scenario.측정_실전(상태)
    마심 = [x for x in 상태["전투상태"]["로그"] if "초보자용 HP 포션" in str(x)]
    assert len(마심) == 1, 마심


# ------------------------ 배운 플레이어 (사용자 지정 2026-10-15, tests/scenario.py)


def _아군_차례까지(상태):
    support.반응_처리(상태)
    while not gf.아군_차례인가(상태):
        gf.턴_넘기기(상태)
    return gf.현재_턴_참가자(상태)


def _고블린전(시드=1):
    import scenario

    rng.시드(시드)
    상태 = 새게임()
    scenario.측정_파티_준비(상태, 1)
    gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=1, 차수=1)
    return 상태


def test_학습정책은_탐험률_0이면_표에서_승률이_가장_높은_행동을_고른다():
    import scenario

    상태 = _고블린전()
    참가자 = _아군_차례까지(상태)
    정책 = scenario.학습정책(탐험률=0)
    상황 = 정책.상황(상태, 참가자)
    후보 = [키 for 키, _ in 정책.후보(상태, 참가자)]
    assert ("일반공격", "HP최저") in 후보 and len(후보) > 1
    for 키 in 후보:
        정책.표[(상황, 키)] = [10, 10] if 키 == ("일반공격", "HP최저") else [0, 10]
    시작 = len(상태["전투상태"]["로그"])
    정책.턴(상태)
    첫행동 = next(
        x for x in 상태["전투상태"]["로그"][시작:] if x.get("공격자") == 참가자["이름"]
    )
    assert 첫행동["종류"] == "일반공격"


def test_학습정책은_전투가_끝나면_고른_행동마다_승패를_센다():
    import scenario

    상태 = _고블린전()
    정책 = scenario.학습정책(탐험률=1.0)
    종료 = scenario.측정_실전(상태, 정책=정책)
    assert 정책.표 and not 정책.이번전투
    이김 = 종료 in ("아군승리", "적도망")
    for 승, 전 in 정책.표.values():
        assert 전 >= 1 and 승 == (전 if 이김 else 0)


def test_측정_학습은_무작위로_배운_뒤_탐험률_30퍼센트로_잰다():
    import scenario

    본것 = []

    def 한판(정책):
        본것.append(정책.탐험률)

    정책 = scenario.측정_학습(한판, 학습판수=3)
    assert 본것 == [1.0, 1.0, 1.0]
    assert 정책.탐험률 == scenario.측정_탐험률 == 0.3


# ---------------------- 퍽 선택도 배운다 (사용자 지정 2026-10-16, tests/scenario.py)


def test_측정_파티_준비는_정책이_없으면_직업_퍽_맨_앞을_고른다():
    import scenario

    상태 = 새게임()
    scenario.측정_파티_준비(상태, 4)
    퍽 = [gf.캐릭터_보유퍽(c) for c in 상태["파티"]["파티원"]]
    # 레벨 4는 1차수 - 직업 퍽 중 2차수(오토가드 등)는 빠지고 무기 마스터리가 맨 앞(10-16)
    assert 퍽 == [
        ["도 마스터리"],
        ["클로 마스터리"],
        ["보우건 마스터리"],
        ["염주 마스터리"],
    ]


def test_학습정책은_탐험률_0이면_퍽표에서_승률이_가장_높은_퍽을_고른다():
    import scenario

    정책 = scenario.학습정책(탐험률=0)
    정책.퍽표[("귀검사", 4, "선빵필승")] = [10, 10]
    상태 = 새게임()
    scenario.측정_파티_준비(상태, 4, 정책=정책)
    귀검사 = 상태["파티"]["파티원"][0]
    assert 귀검사["직업"] == "귀검사"
    assert gf.캐릭터_보유퍽(귀검사) == ["선빵필승"]
    assert ("귀검사", 4, "선빵필승") in 정책.이번퍽


def test_학습정책은_탐험률_1이면_퍽을_무작위로_고른다():
    import scenario

    본퍽 = set()
    for 시드 in range(8):
        rng.시드(시드)
        상태 = 새게임()
        scenario.측정_파티_준비(상태, 4, 정책=scenario.학습정책(탐험률=1.0))
        본퍽.add(gf.캐릭터_보유퍽(상태["파티"]["파티원"][0])[0])
    assert len(본퍽) > 1, 본퍽


def test_학습정책은_전투가_끝날_때마다_고른_퍽에_승패를_센다():
    import scenario

    rng.시드(1)
    정책 = scenario.학습정책(탐험률=1.0)
    상태 = 새게임()
    scenario.측정_파티_준비(상태, 4, 정책=정책)
    고른퍽 = list(정책.이번퍽)
    assert len(고른퍽) == 4
    for _ in range(2):  # 한 판에 전투가 두 번 - 퍽은 두 번 다 센다
        gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=1, 차수=1)
        scenario.측정_실전(상태, 정책=정책)
        gf.휴식(상태)
    assert 정책.이번퍽 == 고른퍽
    for 키 in 고른퍽:
        assert 정책.퍽표[키][1] == 2
    표 = scenario.퍽_승률표(정책)
    assert {퍽 for 퍽, *_ in 표[("귀검사", 4)]} == {고른퍽[0][2]}
    # 새로 준비하면 이번 판의 퍽 기록은 새로 시작한다
    scenario.측정_파티_준비(새게임(), 4, 정책=정책)
    assert len(정책.이번퍽) == 4
