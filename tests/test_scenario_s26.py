"""S26 우마무스메·주인공의 운명 실전 - 말딸과 주인공 특성이 실제 진행에서 이어진다 (docs/scenarios.md).

기본 4인 파티에서 귀검사만 레벨 15까지 키우며(나머지는 레벨 1) 8->9 퍽획득(2차수)에서 우마무스메, 13->14(3차수)에서 주인공의 운명을
고른다(그 밖의 퍽은 결정적 첫 퍽). 서리 머크우드(D07) 인카운트를 [자동전투]로 **실제로** 치르며, 매 전투 시작에 말딸의
근력·민첩이 실제 우선도만큼 올라 있는지, 전투가 끝났을 때 주인공의 보너스(데미지·속도)가 쓰러진 아군 수와 같은지 본다.
규칙의 값은 tests/test_perks_common.py가 본다.
"""

import pytest

import gameflow as gf
from game.system import rng
from game.system.combat import stats, traits
import scenario
import support
from tests.support import 구현된_전직

서리 = "dungeon_01A_D07_frost_mirkwood"
시드 = 0


def _퍽고르기(캐릭터, 후보):
    if 캐릭터["직업"] == "귀검사":
        for 이름 in ("우마무스메", "주인공의 운명"):
            for n, d in 후보:
                if n == 이름:
                    return n, d
    return 후보[0]


def _주인공_보너스(전투상태, p):
    원본 = p["원본"]
    자리 = 원본["보유특성"].index("주인공")
    원본["보유특성"].pop(자리)
    없을때 = traits.특성_수치(전투상태, p, "데미지보너스")
    원본["보유특성"].insert(자리, "주인공")
    return traits.특성_수치(전투상태, p, "데미지보너스") - 없을때


@pytest.mark.scenario("S26")
def test_S26_우마무스메_주인공_실전(golden):
    rng.시드(시드)
    상태 = support.새게임()
    파티 = 상태["파티"]["파티원"]
    귀검사 = next(c for c in 파티 if c["직업"] == "귀검사")
    # 귀검사만 레벨 15 - 나머지는 레벨 1이라 실전에서 쓰러지는 아군이 나온다
    support.성장(상태, 귀검사, 15, 전직=구현된_전직["귀검사"], 퍽고르기=_퍽고르기)
    assert {"말딸", "주인공"} <= set(귀검사["보유특성"])
    gf.파티_최대치로_회복(상태)

    gf.던전_진입(상태, 서리)
    기록 = []
    for 번 in range(1, 21):
        scenario.인카운트까지_걷기(상태)
        전투상태 = 상태["전투상태"]
        p = next(x for x in 전투상태["참가자"] if x["원본"] is 귀검사)
        우선도 = stats.유효_우선도(전투상태, p)
        assert 우선도 >= 1
        for s in ("근력", "민첩"):
            assert stats.유효_능력치값(전투상태, p, s) >= 귀검사[s] + 우선도
        종료 = scenario.실전(상태)
        쓰러진 = traits.쓰러진아군수(전투상태, p)
        assert _주인공_보너스(전투상태, p) == 쓰러진
        기록.append({"번": 번, "종료": 종료, "우선도": 우선도, "쓰러진아군": 쓰러진})
        gf.전투_결과_정리(상태)
        if 종료 != "아군승리" or 쓰러진:
            break
        scenario.보상_수령(상태)  # 회복하지 않는다 - 쓰러지는 아군이 나올 때까지
    golden("scenario_S26_uma_hero", 기록)
