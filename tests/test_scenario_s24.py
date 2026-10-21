"""S24 약점증가 실전 - 공용 퍽 약점증가가 실제 진행에서 이어진다 (docs/scenarios.md).

기본 4인 파티를 레벨 6(5->6 전직)까지 키우며 3->4 퍽획득에서 모든 파티원이 "약점증가"를 고른다. 배우는 즉시
주스탯·보조스탯을 뺀 4개가 8 이하가 되고, 약점제거는 회색(함께 배울 수 없음)이 된다. 4->5 능력치성장은 주스탯·보조스탯에만
들어간다. 로리엔(D01) 인카운트를 [자동전투]로 **실제로** 치르는 동안 약점은 전투 안 유효값으로도 8을 넘지 않고,
저장/불러오기 뒤에도 그대로다. 규칙의 값은 tests/test_perks_common.py가 본다.
"""

import pytest

import gameflow as gf
from game.system import rng
from game.system.combat import stats
import scenario
import support
from tests.support import 구현된_전직

로리엔 = "dungeon_01A_D01_Lorien"
시드 = 0
능력치 = ("근력", "민첩", "건강", "지능", "지혜", "매력")


def _퍽고르기(캐릭터, 후보):
    return next((n, d) for n, d in 후보 if n == "약점증가")


def _약점들(캐릭터):
    return [s for s in 능력치 if s not in (캐릭터["주스탯"], 캐릭터["보조스탯"])]


@pytest.mark.scenario("S24")
def test_S24_약점증가_실전(golden, 임시_세이브폴더):
    rng.시드(시드)
    상태 = support.새게임()
    파티 = 상태["파티"]["파티원"]
    for 캐릭터 in 파티:
        support.성장(
            상태, 캐릭터, 6, 전직=구현된_전직[캐릭터["직업"]], 퍽고르기=_퍽고르기
        )
        assert "약점증가" in 캐릭터["보유특성"]
        assert all(캐릭터[s] <= 8 for s in _약점들(캐릭터)), 캐릭터
        assert gf.퍽_선택상태(캐릭터, gf.캐릭터_전체퍽(캐릭터)["약점제거"]).startswith(
            "'약점증가'"
        )
    gf.파티_최대치로_회복(상태)

    gf.던전_진입(상태, 로리엔)
    전투수 = 0
    for _ in range(5):
        scenario.인카운트까지_걷기(상태)
        전투상태 = 상태["전투상태"]
        for p in 전투상태["참가자"]:
            if p["진영"] == "아군":
                for s in _약점들(p["원본"]):
                    assert stats.유효_능력치값(전투상태, p, s) <= 8
        종료 = scenario.실전(상태)
        assert gf.전투_결과_정리(상태) == 종료 == "아군승리"
        전투수 += 1
        scenario.보상_수령(상태)
        gf.파티_최대치로_회복(상태)

    값 = {c["직업"]: {s: c[s] for s in 능력치} for c in 파티}
    gf.게임_저장(상태, 1)
    불러온 = gf.게임_불러오기(1)
    assert {
        c["직업"]: {s: c[s] for s in 능력치} for c in 불러온["파티"]["파티원"]
    } == 값
    assert all("약점증가" in c["보유특성"] for c in 불러온["파티"]["파티원"])
    golden("scenario_S24_weakness_up", {"전투수": 전투수, "능력치": 값})
