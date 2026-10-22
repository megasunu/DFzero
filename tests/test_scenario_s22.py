"""S22 훔쳐배우기 실전 - [스킬습득]에서 다른 전직의 스킬을 5배 값에 사서 실제 전투에서 쓴다
(docs/scenarios.md, #279, #365).

귀검사가 든 4인 파티를 레벨 9까지 키운다(귀검사는 5->6에 버서커, 나머지는 기본 전직). 버서커는 훔쳐배우기
후보 중 첫 스킬을 골드로 산다. 선더랜드(D05) 인카운트를 **실제 전투로** 치른다. 버서커는 차례마다 훔쳐 배운 스킬을 쓸 수
있으면 쓰고 남은 일반행동으로 일반공격한다. 나머지 파티원은 스킬 우선 정책이다. 훔쳐 배운 스킬이 실제로 나가는지,
저장/불러오기 뒤에도 남는지 본다. 후보·값·레벨 규칙은 tests/test_growth.py가 값으로 검사한다.
"""

import pytest

from game.system import rng
import gameflow as gf
import scenario
import support
from tests.support import 구현된_전직

선더랜드 = "dungeon_01A_D05_thunderland"
시드 = 0
파티구성 = [("", "귀검사"), ("", "격투가"), ("", "거너"), ("", "프리스트")]
전직표 = dict(구현된_전직, 귀검사="버서커")


def _버서커_턴(상태, bs, 스킬, 기록):
    전투상태 = 상태["전투상태"]
    적들 = scenario._살아있는_적(상태)
    if 적들 and gf.스킬_사용_가능여부(상태, bs, 스킬)[0]:
        gf.아군_스킬사용(상태, 스킬, 중심대상=적들[0])
        기록["사용"] = 기록.get("사용", 0) + 1
    while 전투상태["종료"] is None and bs["생존"]:
        적들 = scenario._살아있는_적(상태)
        if not 적들 or bs["행동자원"].get("일반행동", 0) <= 0:
            break
        gf.아군_일반공격(상태, 적들[0])
    if 전투상태["종료"] is None:
        gf.턴_넘기기(상태)


def _전투(상태, 스킬, 기록):
    support.반응_처리(상태)
    for _ in range(300):
        if gf.전투_종료됨(상태):
            break
        참가자 = gf.현재_턴_참가자(상태)
        if 참가자["진영"] == "아군" and 참가자["생존"]:
            if 참가자["원본"].get("전직") == "버서커":
                _버서커_턴(상태, 참가자, 스킬, 기록)
            else:
                scenario.스킬_우선_턴(상태, [])
        else:
            gf.턴_넘기기(상태)
    else:
        raise AssertionError("전투가 끝나지 않았다")
    로그 = [항목 for 항목 in 상태["전투상태"]["로그"] if isinstance(항목, dict)]
    # 분할공격(차지크래시)은 "OO (1단계)"처럼 단계가 붙는다
    기록["로그줄"] = sum(str(항목.get("스킬") or "").startswith(스킬) for 항목 in 로그)
    return 상태["전투상태"]["종료"]


@pytest.mark.scenario("S22")
def test_S22_훔쳐배우기_실전(golden, 임시_세이브폴더):
    rng.시드(시드)
    상태 = support.새게임(파티구성)
    파티 = 상태["파티"]["파티원"]
    [bs] = [c for c in 파티 if c["직업"] == "귀검사"]
    for c in 파티:
        support.성장(상태, c, 9, 전직=전직표[c["직업"]])
    후보 = [h for h in gf.캐릭터_훔쳐배우기_후보(bs) if h["종류"] == "스킬"]
    assert 후보, "버서커가 훔쳐배울 것이 없다"
    스킬 = 후보[0]["이름"]
    상태["소지품"]["골드"] = 500
    assert gf.캐릭터_스킬_습득(상태, bs, 스킬) == 500  # 전직 스킬 100골드의 5배
    assert 스킬 in bs["보유스킬"] and 상태["소지품"]["골드"] == 0
    gf.파티_최대치로_회복(상태)

    gf.던전_진입(상태, 선더랜드)
    전투들 = []
    for _ in range(4):
        적 = scenario.인카운트까지_걷기(상태)
        기록 = {}
        종료 = _전투(상태, 스킬, 기록)
        assert gf.전투_결과_정리(상태) == 종료 == "아군승리"
        scenario.보상_수령(상태)
        gf.파티_최대치로_회복(상태)
        전투들.append({"적": 적, **기록})
        if sum(b.get("사용", 0) for b in 전투들) >= 2:
            break
    assert sum(b.get("사용", 0) for b in 전투들), 전투들
    assert all(b.get("로그줄", 0) >= b.get("사용", 0) for b in 전투들), 전투들

    gf.게임_저장(상태, 1)
    불러옴 = gf.게임_불러오기(1)
    [bs2] = [c for c in 불러옴["파티"]["파티원"] if c["직업"] == "귀검사"]
    assert 스킬 in bs2["보유스킬"]
    golden("scenario_S22_steal_learn", {"스킬": 스킬, "전투": 전투들})
