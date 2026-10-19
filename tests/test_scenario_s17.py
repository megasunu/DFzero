"""S17 유루캠 실전 - 던전 캠핑이 실제 진행에서 이어진다 (docs/scenarios.md).

기본 4인 파티를 레벨 4까지 키우며 3->4 퍽획득에서 프리스트가 "유루캠"을 고른다(나머지는 결정적 첫 퍽).
머크우드(D03) 인카운트를 [자동전투]로 **실제로** 치러 파티가 다칠 때까지(최대 6번) 진행하고, 던전 [스킬]로
던전 캠핑을 써 파티원 전체 HP가 최대치가 되는지(MP는 그대로), 두 번째는 막히는지, 저장/불러오기 뒤에도
남은 횟수가 0인지, 마을 휴식 뒤 다시 쓸 수 있는지 본다. 규칙의 값은 tests/test_dungeon_skills.py가 본다.
"""

import random

import pytest

import gameflow as gf
import scenario
import support

머크우드 = "dungeon_01A_D03_mirkwood"
시드 = 0


def _퍽고르기(캐릭터, 후보):
    if 캐릭터["직업"] == "프리스트":
        return next((n, d) for n, d in 후보 if n == "유루캠")
    return 후보[0]


def _캠핑줄(상태):
    return next(줄 for 줄 in gf.던전스킬_목록(상태) if 줄["스킬"] == "던전 캠핑")


@pytest.mark.scenario("S17")
def test_S17_유루캠_던전_캠핑_실전(golden):
    random.seed(시드)
    상태 = support.새게임()
    파티 = 상태["파티"]["파티원"]
    for 캐릭터 in 파티:
        support.성장(상태, 캐릭터, 4, 퍽고르기=_퍽고르기)
    프리스트 = next(c for c in 파티 if c["직업"] == "프리스트")
    assert "던전 캠핑" in 프리스트["보유스킬"]
    gf.파티_최대치로_회복(상태)

    gf.던전_진입(상태, 머크우드)
    기록 = []
    for _ in range(6):
        적 = scenario.인카운트까지_걷기(상태)
        종료 = scenario.실전(상태)
        assert gf.전투_결과_정리(상태) == 종료
        잃은HP = sum(gf.캐릭터_최대HP(상태, c) - c["현재HP"] for c in 파티)
        기록.append({"적": 적, "종료": 종료, "잃은HP": 잃은HP})
        assert 종료 == "아군승리", 기록
        scenario.보상_수령(상태)
        if 잃은HP > 0 and 프리스트["현재HP"] > 0:
            break
    assert 기록[-1]["잃은HP"] > 0, 기록

    MP = [c["현재MP"] for c in 파티]
    assert _캠핑줄(상태)["가능"]
    결과 = gf.던전스킬_사용(상태, 프리스트, "던전 캠핑")
    assert 결과["성공"], 결과
    assert all(c["현재HP"] == gf.캐릭터_최대HP(상태, c) for c in 파티)
    assert [c["현재MP"] for c in 파티] == MP  # HP만 채운다
    assert not gf.던전스킬_사용(상태, 프리스트, "던전 캠핑")["성공"]

    gf.게임_저장(상태, 1)  # 던전 안 저장 - 남은 횟수 0이 세이브에 남는다
    상태 = gf.게임_불러오기(1)
    프리스트 = next(c for c in 상태["파티"]["파티원"] if c["직업"] == "프리스트")
    gf.던전_진입(상태, 머크우드)
    assert _캠핑줄(상태)["남은"] == (0, 1)

    gf.휴식(상태)
    gf.던전_진입(상태, 머크우드)
    assert _캠핑줄(상태)["가능"] and _캠핑줄(상태)["남은"] == (1, 1)
    golden("scenario_S17_dungeon_camping", {"전투": 기록, "문구": 결과["문구"]})
