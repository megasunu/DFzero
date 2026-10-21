"""S33 검귀 실전 - 6레벨 특성(청혈투귀·검귀의 도 마스터리), 8레벨 귀혼일체 (docs/scenarios.md, #330).

귀검사가 든 4인 파티를 레벨 9까지 키운다(귀검사는 5->6에 검귀, 나머지는 기본 전직, 스킬 전부 습득).
검귀는 레벨 2에 고른 무기 마스터리를 6레벨에 잃고, 9레벨 퍽에서도 무기 마스터리를 고를 수 없다.
도(예리한 카타나)를 들고 선더랜드(D05)에 들어가 인카운트를 **실제 전투로** 치른다. 검귀는 차례마다 귀혼일체가
없으면 걸고(행동·MP 소모 없음, 휴식당 1회) 일반행동이 남는 동안 일반공격한다. 귀혼일체가 MP를 쓰지 않는지,
치명타 범위 19(청혈투귀)로 19 눈 치명타가 실제로 나는지 본다. 수치 규칙은 tests/test_job_ghostblade.py가 값으로 검사한다.
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
전직표 = dict(구현된_전직, 귀검사="검귀")
도 = "예리한 카타나"
마스터리5종 = [
    "소검 마스터리",
    "도 마스터리",
    "둔기 마스터리",
    "대검 마스터리",
    "광검 마스터리",
]


def _검귀_턴(상태, g, 기록):
    전투상태 = 상태["전투상태"]
    if not any(b["이름"] == "귀혼일체" for b in g["버프"]):
        if gf.스킬_사용_가능여부(상태, g, "귀혼일체")[0]:
            MP = g["현재MP"]
            gf.아군_스킬사용(상태, "귀혼일체")
            기록["귀혼일체"] = 기록.get("귀혼일체", 0) + 1
            기록["귀혼일체MP"] = 기록.get("귀혼일체MP", 0) + MP - g["현재MP"]
    while 전투상태["종료"] is None and g["생존"]:
        적들 = scenario._살아있는_적(상태)
        if not 적들 or g["행동자원"].get("일반행동", 0) <= 0:
            break
        gf.아군_일반공격(상태, 적들[0])
    if 전투상태["종료"] is None:
        gf.턴_넘기기(상태)


def _전투(상태, 검귀, 기록):
    support.반응_처리(상태)
    for _ in range(300):
        if gf.전투_종료됨(상태):
            break
        참가자 = gf.현재_턴_참가자(상태)
        if 참가자["진영"] == "아군" and 참가자["생존"]:
            if 참가자["원본"] is 검귀:
                _검귀_턴(상태, 참가자, 기록)
            else:
                scenario.스킬_우선_턴(상태, [])
        else:
            gf.턴_넘기기(상태)
    else:
        raise AssertionError("전투가 끝나지 않았다")
    공격들 = [
        항목
        for 항목 in 상태["전투상태"]["로그"]
        if isinstance(항목, dict)
        and 항목.get("종류") == "일반공격"
        and 항목.get("공격자") == 검귀["캐릭터명"]
    ]
    기록["일반공격"] = len(공격들)
    기록["치명타"] = sum(1 for 항목 in 공격들 if 항목["판정"].get("치명타"))
    기록["19눈치명타"] = sum(
        1
        for 항목 in 공격들
        if 항목["판정"].get("치명타") and 항목["판정"].get("자연눈") == 19
    )
    return 상태["전투상태"]["종료"]


@pytest.mark.scenario("S33")
def test_S33_검귀_실전(golden):
    rng.시드(시드)
    상태 = support.새게임(파티구성)
    파티 = 상태["파티"]["파티원"]
    [g] = [c for c in 파티 if c["직업"] == "귀검사"]
    for c in 파티:
        support.성장(
            상태, c, 5 if c is g else 9, 전직=전직표[c["직업"]], 스킬습득=c is not g
        )
    assert any(n in g["보유특성"] for n in 마스터리5종)  # 레벨 2에 고른 무기 마스터리
    support.성장(상태, g, 8, 전직="검귀")
    assert not any(n in g["보유특성"] for n in 마스터리5종)
    assert not any(이름 in 마스터리5종 for 이름, _ in support.퍽_후보(g))  # 9레벨 퍽
    support.성장(상태, g, 9, 스킬습득=True)
    assert gf.캐릭터_직업표시(g).startswith("검귀")
    assert {"청혈투귀", "검귀의 도 마스터리"} <= set(g["보유특성"])
    assert "귀혼일체" in g["보유스킬"]
    상태["소지품"]["장비"][도] = 1
    gf.장비_교체(상태, g, "무기", 도)
    gf.파티_최대치로_회복(상태)

    gf.던전_진입(상태, 선더랜드)
    전투들 = []
    for _ in range(8):
        적 = scenario.인카운트까지_걷기(상태)
        기록 = {}
        종료 = _전투(상태, g, 기록)
        assert gf.전투_결과_정리(상태) == 종료 == "아군승리"
        scenario.보상_수령(상태)
        전투들.append({"적": 적, **기록})
        gf.휴식(상태)  # 귀혼일체는 휴식당 1회 - 마을에서 쉬고 다시 들어간다
        gf.던전_진입(상태, 선더랜드)
        if sum(b.get("19눈치명타", 0) for b in 전투들):
            break

    def 합계(키):
        return sum(b.get(키, 0) for b in 전투들)

    assert 합계("귀혼일체") and 합계("일반공격"), 전투들
    assert 합계("귀혼일체MP") == 0, 전투들  # 소모값 없음
    assert all(b.get("귀혼일체", 0) <= 1 for b in 전투들), 전투들  # 휴식당 1회
    assert 합계("19눈치명타"), 전투들  # 청혈투귀 - 치명타 범위 19
    golden("scenario_S33_ghostblade", 전투들)
