"""S20 버서커 실전 - 혈기왕성·혈십자, 폭주, 퍽 광기(프렌지·사무치는 광기), 골드 스킬 (docs/scenarios.md, #247).

귀검사가 든 4인 파티를 레벨 9까지 키운다(귀검사는 5->6에 버서커, 레벨 9 퍽은 광기, 나머지는 기본 전직, 스킬 전부 습득).
선더랜드(D05)에 들어가 던전 [스킬]로 프렌지를 켜고 인카운트를 **실제 전투로** 치른다. 버서커는 차례마다 폭주가 없으면
걸고, HP가 40% 이하면 사무치는 광기, 다친 아군이 있으면 새크리파이스, 적이 둘 이상이면 피폭발 아니면 블러드 러스트를
쓴 뒤 남은 일반행동으로 일반공격한다. 폭주와 사무치는 광기는 휴식당 1회라 전투가 끝날 때마다 마을에서 쉬고 다시 들어간다.
MP 대신 HP를 쓰는지(MP 그대로), 프렌지의 턴 시작 HP 감소·출혈·출혈 처치 회복이 실제로 나오는지 본다.
수치 규칙은 tests/test_job_berserker.py가 값으로 검사한다.
"""

import random

import pytest

import gameflow as gf
import scenario
import support
from tests.test_gameflow_scenarios import 구현된_전직

선더랜드 = "dungeon_01A_D05_thunderland"
시드 = 0
파티구성 = [("", "귀검사"), ("", "격투가"), ("", "거너"), ("", "프리스트")]
전직표 = dict(구현된_전직, 귀검사="버서커")


def _광기_고르기(캐릭터, 후보):
    """버서커는 레벨 9에 광기, 그 밖의 퍽은 후보 맨 앞."""
    return next(((이름, 정의) for 이름, 정의 in 후보 if 이름 == "광기"), 후보[0])


def _버서커_턴(상태, bs, 기록):
    전투상태 = 상태["전투상태"]

    def 쓰기(이름, 대상=None):
        if not gf.스킬_사용_가능여부(상태, bs, 이름)[0]:
            return False
        MP = bs["현재MP"]
        gf.아군_스킬사용(상태, 이름, 중심대상=대상)
        기록[이름] = 기록.get(이름, 0) + 1
        기록["MP변화"] = 기록.get("MP변화", 0) + (bs["현재MP"] != MP)
        return True

    if not any(b["이름"] == "폭주" for b in bs["버프"]):
        쓰기("폭주")
    최대 = gf.캐릭터_최대HP(상태, bs["원본"])
    if bs["현재HP"] * 10 <= 최대 * 4 and not any(
        b["이름"] == "사무치는 광기" for b in bs["버프"]
    ):
        쓰기("사무치는 광기")
    다친 = [
        a
        for a in gf.아군_목록(상태)
        if a is not bs
        and a["생존"]
        and a["현재HP"] * 2 <= gf.캐릭터_최대HP(상태, a["원본"])
    ]
    if 다친:
        쓰기("새크리파이스", 다친[0])
    적들 = scenario._살아있는_적(상태)
    if 적들:
        쓰기("피폭발" if len(적들) >= 2 else "블러드 러스트", 적들[-1])
    while 전투상태["종료"] is None and bs["생존"]:
        적들 = scenario._살아있는_적(상태)
        if not 적들 or bs["행동자원"].get("일반행동", 0) <= 0:
            break
        gf.아군_일반공격(상태, 적들[0])
    if 전투상태["종료"] is None:
        gf.턴_넘기기(상태)


def _전투(상태, 기록):
    support.반응_처리(상태)
    for _ in range(300):
        if gf.전투_종료됨(상태):
            break
        참가자 = gf.현재_턴_참가자(상태)
        if 참가자["진영"] == "아군" and 참가자["생존"]:
            if 참가자["원본"].get("전직") == "버서커":
                _버서커_턴(상태, 참가자, 기록)
            else:
                scenario.스킬_우선_턴(상태, [])
        else:
            gf.턴_넘기기(상태)
    else:
        raise AssertionError("전투가 끝나지 않았다")
    로그 = [항목 for 항목 in 상태["전투상태"]["로그"] if isinstance(항목, dict)]
    비고 = [str(항목.get("비고", "")) for 항목 in 로그]
    기록["프렌지감소"] = sum("프렌지로 HP" in 글 for 글 in 비고)
    기록["출혈"] = sum("'출혈' 상태이상 부여" in 글 for 글 in 비고)
    기록["출혈처치회복"] = sum("쓰러뜨려 HP" in 글 for 글 in 비고)
    return 상태["전투상태"]["종료"]


@pytest.mark.scenario("S20")
def test_S20_버서커_실전(golden):
    random.seed(시드)
    상태 = support.새게임(파티구성)
    파티 = 상태["파티"]["파티원"]
    for c in 파티:
        support.성장(
            상태, c, 9, 전직=전직표[c["직업"]], 스킬습득=True, 퍽고르기=_광기_고르기
        )
    gf.파티_최대치로_회복(상태)
    [bs] = [c for c in 파티 if c["직업"] == "귀검사"]
    assert gf.캐릭터_직업표시(bs).startswith("버서커")
    assert bs["직업스타일"] == "하이브리드"
    assert {"혈기왕성", "혈십자", "프렌지"} <= set(bs["보유특성"])
    assert {
        "폭주",
        "프렌지",
        "사무치는 광기",
        "새크리파이스",
        "피폭발",
        "블러드 러스트",
    } <= set(bs["보유스킬"])

    gf.던전_진입(상태, 선더랜드)
    assert gf.던전스킬_사용(상태, bs, "프렌지")["성공"]  # 던전 [스킬]로 켠다
    assert bs["켜진특성"] == ["프렌지"]
    전투들 = []
    for _ in range(6):
        적 = scenario.인카운트까지_걷기(상태)
        기록 = {}
        종료 = _전투(상태, 기록)
        assert gf.전투_결과_정리(상태) == 종료 == "아군승리"
        scenario.보상_수령(상태)
        assert bs["켜진특성"] == ["프렌지"]  # 전투가 끝나도 켜진 채
        전투들.append({"적": 적, **기록})
        if 기록.get("폭주"):  # 휴식당 1회 - 마을로 돌아가 쉬고 다시 들어간다
            assert bs["횟수제한스킬"]["휴식제한스킬"]["폭주"] == 0
        gf.휴식(상태)
        gf.던전_진입(상태, 선더랜드)
        합 = {
            k: sum(b.get(k, 0) for b in 전투들)
            for k in ("피폭발", "블러드 러스트", "출혈", "프렌지감소", "출혈처치회복")
        }
        if all(합.values()):
            break

    def 합계(키):
        return sum(b.get(키, 0) for b in 전투들)

    assert 합계("폭주") and 합계("프렌지감소") and 합계("출혈"), 전투들
    assert 합계("피폭발") and 합계("블러드 러스트"), 전투들
    assert 합계("출혈처치회복"), 전투들
    assert 합계("MP변화") == 0, 전투들  # 혈기왕성 - 스킬 비용은 전부 HP
    assert all(b.get("폭주", 0) <= 1 for b in 전투들), 전투들  # 휴식당 1회
    golden("scenario_S20_berserker", 전투들)
