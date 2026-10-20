"""S25 3차 행동 퍽 실전 - 유연함/세번째 손/스파이더 센서가 실제 진행에서 이어진다 (docs/scenarios.md).

기본 4인 파티를 레벨 15까지 키우며 13->14 퍽획득(3차수)에서 귀검사·프리스트는 유연함, 격투가는 세번째 손,
거너는 스파이더 센서를 고른다(그 전은 결정적 첫 퍽). 셋 중 하나를 배우면 나머지 둘은 회색(함께 배울 수 없음)이다.
로리엔(D01) 인카운트를 [자동전투]로 **실제로** 치르며, 턴 시작 행동자원에 각 퍽의 +1이 들어 있는지 본다.
규칙의 값은 tests/test_perks_common.py가 본다.
"""

import pytest

import gameflow as gf
from game.system import rng
from game.system.combat import flow
import scenario
import support
from tests.test_gameflow_scenarios import 구현된_전직

로리엔 = "dungeon_01A_D01_Lorien"
시드 = 0
고를퍽 = {
    "귀검사": "유연함",
    "격투가": "세번째 손",
    "거너": "스파이더 센서",
    "프리스트": "유연함",
}
셋 = ("유연함", "세번째 손", "스파이더 센서")


@pytest.mark.scenario("S25")
def test_S25_3차_행동_퍽_실전(golden):
    rng.시드(시드)
    상태 = support.새게임()
    파티 = 상태["파티"]["파티원"]
    for 캐릭터 in 파티:
        퍽 = 고를퍽[캐릭터["직업"]]
        support.성장(
            상태,
            캐릭터,
            15,
            전직=구현된_전직[캐릭터["직업"]],
            퍽고르기=lambda c, 후보, 퍽=퍽: next(
                ((n, d) for n, d in 후보 if n == 퍽), 후보[0]
            ),
        )
        assert 퍽 in 캐릭터["보유특성"]
        전체 = gf.캐릭터_전체퍽(캐릭터)
        for 다른 in 셋:
            if 다른 != 퍽:
                assert (
                    gf.퍽_선택상태(캐릭터, 전체[다른])
                    == f"'{퍽}'과(와) 함께 배울 수 없음"
                )
    gf.파티_최대치로_회복(상태)

    gf.던전_진입(상태, 로리엔)
    행동 = {}
    for _ in range(3):
        scenario.인카운트까지_걷기(상태)
        전투상태 = 상태["전투상태"]
        for p in 전투상태["참가자"]:
            if p["진영"] != "아군":
                continue
            원본 = p["원본"]
            퍽 = 고를퍽[원본["직업"]]
            자리 = 원본["보유특성"].index(퍽)
            원본["보유특성"].pop(
                자리
            )  # 퍽이 없을 때와 비교한다(직업 특성의 행동보너스가 따로 있다)
            flow.행동자원_채우기(전투상태, p)
            없을때 = dict(p["행동자원"])
            원본["보유특성"].insert(자리, 퍽)
            flow.행동자원_채우기(전투상태, p)  # 첫 턴 시작이 다시 채운다
            자원 = p["행동자원"]
            if 퍽 == "세번째 손":
                assert 자원["보조행동"] == 없을때["보조행동"] + 1
            if 퍽 == "스파이더 센서":
                assert 자원["반응행동"] == 없을때["반응행동"] + 1
            assert p["추가공격_사용가능"] == 원본["추가공격"]
            행동[원본["직업"]] = {**자원, "추가공격": 원본["추가공격"]}
        종료 = scenario.실전(상태)
        assert gf.전투_결과_정리(상태) == 종료 == "아군승리"
        scenario.보상_수령(상태)
        gf.파티_최대치로_회복(상태)
    golden("scenario_S25_action_perks", 행동)
