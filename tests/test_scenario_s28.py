"""S28 포켓몬 2차 특성 실전 - 피격 발동 4종과 부자유친이 실제 전투에서 이어진다 (docs/scenarios.md).

기본 4인 파티를 레벨 20까지 키우며 18->19 퍽획득(4차수)에서 모두 "포켓몬"을 고르고 특성은 귀검사 까칠한피부,
격투가 독가시, 거너 불꽃몸, 프리스트 부자유친을 고른다(그 전은 결정적 첫 퍽). 시가브·힐가브를 파티와 같은 레벨 20으로
불러 [자동전투]로 **실제로** 치러, 까칠한피부 반격 피해·독가시/불꽃몸 상태이상 시도(부여 또는 피함)·부자유친 추가 피해가
다 나올 때까지(최대 15번) 진행한다. 규칙의 값은 tests/test_perks_common.py가 본다.
"""

import pytest

import gameflow as gf
from game.system import rng
import scenario
import support
from tests.test_gameflow_scenarios import 구현된_전직

시드 = 0
고를특성 = {
    "귀검사": "까칠한피부",
    "격투가": "독가시",
    "거너": "불꽃몸",
    "프리스트": "부자유친",
}


@pytest.mark.scenario("S28")
def test_S28_포켓몬_피격_부자유친_실전(golden, monkeypatch):
    rng.시드(시드)
    상태 = support.새게임()
    파티 = 상태["파티"]["파티원"]
    원래 = support.퍽_선택값

    def 퍽_선택값(캐릭터, 이름, 정의):
        선택 = 원래(캐릭터, 이름, 정의)
        if 이름 == "포켓몬":
            선택["선택특성"] = 고를특성[캐릭터["직업"]]
        return 선택

    monkeypatch.setattr(support, "퍽_선택값", 퍽_선택값)
    for 캐릭터 in 파티:
        support.성장(
            상태,
            캐릭터,
            20,
            전직=구현된_전직[캐릭터["직업"]],
            퍽고르기=lambda c, 후보: next(
                ((n, d) for n, d in 후보 if n == "포켓몬"), 후보[0]
            ),
        )
        assert 고를특성[캐릭터["직업"]] in 캐릭터["보유특성"]
    gf.파티_최대치로_회복(상태)

    본것 = {"반격": 0, "가시": 0, "부자유친": 0}
    for 번 in range(1, 16):
        gf.전투_시작(상태, ["시가브", "힐가브", "시가브", "힐가브"], 레벨=20, 차수=3)
        support.반응_처리(상태)
        전투상태 = 상태["전투상태"]
        종료 = scenario.실전(상태)
        assert gf.전투_결과_정리(상태) == 종료 == "아군승리"
        for e in 전투상태["로그"]:
            비고 = str(e.get("비고", "")) if isinstance(e, dict) else ""
            if "'까칠한피부' 피격시 반격 피해" in 비고:
                본것["반격"] += 1
            if "'독가시'" in 비고 or "'불꽃몸'" in 비고:
                본것["가시"] += 1
            if 비고 == "부자유친":
                본것["부자유친"] += 1
        gf.파티_최대치로_회복(상태)
        if all(본것.values()):
            break
    assert all(본것.values()), 본것
    golden("scenario_S28_pokemon_hit", {"전투": 번, **본것})
