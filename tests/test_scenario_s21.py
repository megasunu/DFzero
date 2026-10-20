"""S21 란마 1/2 실전 - 낭익천/남익천이 실제 진행에서 이어진다 (docs/scenarios.md).

기본 4인 파티를 레벨 9(5->6 전직)까지 키우며 8->9 퍽획득에서 모든 파티원이 "란마 1/2"를 고른다(그 전은
결정적 첫 퍽). 맞기 전 형태는 성별이다(귀검사·격투가 남자, 거너·프리스트 여자). 서리 머크우드(D07 - 시가브 계열의 수속성,
힐가브의 화속성 공격이 다 나온다) 인카운트를 [자동전투]로 **실제로** 치러, 남자 -> 여자와 여자 -> 남자가
한 번씩 실제로 일어날 때까지(최대 30번) 진행한다. 바뀐 형태가 전투 뒤, 휴식 뒤, 저장/불러오기 뒤에도
남는지 본다. 규칙의 값은 tests/test_perks_common.py가 본다.
"""

import random

import pytest

import gameflow as gf
import scenario
import support
from tests.test_gameflow_scenarios import 구현된_전직

서리 = "dungeon_01A_D07_frost_mirkwood"
시드 = 1


def _퍽고르기(캐릭터, 후보):
    return next(((n, d) for n, d in 후보 if n == "란마 1/2"), 후보[0])


def _형태들(상태):
    return {c["직업"]: c.get("란마성별") or c["성별"] for c in 상태["파티"]["파티원"]}


@pytest.mark.scenario("S21")
def test_S21_란마_실전(golden, 임시_세이브폴더):
    random.seed(시드)
    상태 = support.새게임()
    파티 = 상태["파티"]["파티원"]
    for 캐릭터 in 파티:
        support.성장(
            상태, 캐릭터, 9, 전직=구현된_전직[캐릭터["직업"]], 퍽고르기=_퍽고르기
        )
        assert {"낭익천", "남익천"} <= set(캐릭터["보유특성"])
        assert "란마성별" not in 캐릭터
    for 캐릭터 in 파티[
        :2
    ]:  # 남녀 둘씩 - 마을 프로필의 성별 바꾸기와 같다(귀검사, 격투가 남자)
        gf.캐릭터_성별_설정(캐릭터, "m")
    gf.파티_최대치로_회복(상태)

    gf.던전_진입(상태, 서리)
    바뀜 = []  # (전투 번호, 직업, 전 형태 -> 새 형태)
    for 번 in range(1, 31):
        전 = _형태들(상태)
        scenario.인카운트까지_걷기(상태)
        종료 = scenario.실전(상태)
        로그 = [e for e in 상태["전투상태"]["로그"] if isinstance(e, dict)]
        assert gf.전투_결과_정리(상태) == 종료 == "아군승리"
        뒤 = _형태들(상태)
        이번 = [(번, j, f"{전[j]}->{뒤[j]}") for j in 뒤 if 뒤[j] != 전[j]]
        if 이번:
            assert any("가 되었다" in str(e.get("비고", "")) for e in 로그)
        바뀜 += 이번
        scenario.보상_수령(상태)
        gf.파티_최대치로_회복(상태)
        종류 = {변화 for _, _, 변화 in 바뀜}
        if {"m->f", "f->m"} <= 종류:
            break
    assert {"m->f", "f->m"} <= {변화 for _, _, 변화 in 바뀜}, 바뀜
    귀검사 = next(c for c in 파티 if c["직업"] == "귀검사")
    assert (
        gf.초상화_코드(귀검사) == f"011{_형태들(상태)['귀검사']}"
    )  # 011f/011m 둘 다 있다

    형태 = _형태들(상태)
    gf.휴식(상태)
    assert _형태들(상태) == 형태
    gf.게임_저장(상태, 1)
    assert _형태들(gf.게임_불러오기(1)) == 형태
    golden("scenario_S21_ranma", {"바뀜": 바뀜, "형태": 형태})
