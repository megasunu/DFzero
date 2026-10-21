"""S32 아수라 실전 - 6레벨 특성(살기감지·관조·정신이 번쩍!), 8레벨 살의의 파동, 골드 스킬 (docs/scenarios.md, #325).

귀검사가 든 4인 파티를 레벨 9까지 키운다(귀검사는 5->6에 아수라, 나머지는 기본 전직, 스킬 전부 습득).
선더랜드(D05)에 들어가 인카운트를 **실제 전투로** 치른다. 아수라는 차례마다 살의의 파동이 없으면 걸고(휴식당 1회),
골드 스킬(아이스 웨이브·파이어 웨이브·진공참)을 가장 덜 쓴 것부터 하나 쓴 뒤 남은 일반행동으로 일반공격한다.
하단공격 스킬은 공중에 뜬 적을 고르지 않는다. 살의의 파동이 적의 턴 시작마다 실제로 피해를 주는지, 정신이 번쩍!이
전투당 한 번만 발동하는지, 빙결·화상이 실제로 걸리는지 본다. 수치 규칙은 tests/test_job_asura.py가 값으로 검사한다.
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
전직표 = dict(구현된_전직, 귀검사="아수라")
골드스킬 = ("아이스 웨이브", "파이어 웨이브", "진공참")


def _아수라_턴(상태, a, 기록, 누적):
    전투상태 = 상태["전투상태"]

    def 쓰기(이름, 대상=None):
        if not gf.스킬_사용_가능여부(상태, a, 이름)[0]:
            return False
        gf.아군_스킬사용(상태, 이름, 중심대상=대상)
        기록[이름] = 기록.get(이름, 0) + 1
        누적[이름] = 누적.get(이름, 0) + 1
        return True

    if not any(b["이름"] == "살의의 파동" for b in a["버프"]):
        쓰기("살의의 파동")
    # 골드 스킬은 (전투 전체에서) 가장 덜 쓴 것부터 돌아가며(쓸 수 있고 고를 적이 있는 것). 하단공격은 뜬 적을 고르지 않는다
    for 이름 in sorted(골드스킬, key=lambda n: 누적.get(n, 0)):
        적들 = [
            e
            for e in scenario._살아있는_적(상태)
            if not gf.스킬_지정불가인가(상태, 상태["스킬데이터모음"][이름], e)
        ]
        if 적들 and 쓰기(이름, 적들[0]):
            break
    while 전투상태["종료"] is None and a["생존"]:
        적들 = scenario._살아있는_적(상태)
        if not 적들 or a["행동자원"].get("일반행동", 0) <= 0:
            break
        gf.아군_일반공격(상태, 적들[0])
    if 전투상태["종료"] is None:
        gf.턴_넘기기(상태)


def _전투(상태, 아수라, 기록, 누적):
    support.반응_처리(상태)
    for _ in range(300):
        if gf.전투_종료됨(상태):
            break
        참가자 = gf.현재_턴_참가자(상태)
        if 참가자["진영"] == "아군" and 참가자["생존"]:
            if 참가자["원본"] is 아수라:
                _아수라_턴(상태, 참가자, 기록, 누적)
            else:
                scenario.스킬_우선_턴(상태, [])
        else:
            gf.턴_넘기기(상태)
    else:
        raise AssertionError("전투가 끝나지 않았다")
    로그 = [항목 for 항목 in 상태["전투상태"]["로그"] if isinstance(항목, dict)]
    비고 = [str(항목.get("비고", "")) for 항목 in 로그]
    기록["살의피해"] = sum(
        1 for 항목 in 로그 if 항목.get("스킬") == "살의의 파동" and 항목.get("타격")
    )
    기록["정신이 번쩍!"] = sum("'정신이 번쩍!' 특성" in 글 for 글 in 비고)
    효과줄 = [
        str(e)
        for 항목 in 로그
        for t in 항목.get("타격") or []
        for e in t.get("효과로그") or []
    ]
    기록["빙결"] = sum("'빙결' 부여" in 줄 for 줄 in 효과줄)
    기록["화상"] = sum(
        "지속피해 '화상' 등록" in 줄 for 줄 in 효과줄
    )  # 화상은 지속피해형
    기록["화상판정"] = sum("'화상'" in 줄 for 줄 in 효과줄)  # 걸렸든 피했든
    return 상태["전투상태"]["종료"]


@pytest.mark.scenario("S32")
def test_S32_아수라_실전(golden):
    rng.시드(시드)
    상태 = support.새게임(파티구성)
    파티 = 상태["파티"]["파티원"]
    for c in 파티:
        support.성장(상태, c, 9, 전직=전직표[c["직업"]], 스킬습득=True)
    gf.파티_최대치로_회복(상태)
    [a] = [c for c in 파티 if c["직업"] == "귀검사"]
    assert gf.캐릭터_직업표시(a).startswith("아수라")
    assert a["주문시전능력치"] == "지혜"
    assert {"살기감지", "관조", "정신이 번쩍!"} <= set(a["보유특성"])
    assert {"살의의 파동", "웨이브", *골드스킬} <= set(a["보유스킬"])

    gf.던전_진입(상태, 선더랜드)
    전투들 = []
    누적 = {}  # 골드 스킬 순서 - 전투가 바뀌어도 이어서 돈다
    for _ in range(10):
        적 = scenario.인카운트까지_걷기(상태)
        기록 = {}
        종료 = _전투(상태, a, 기록, 누적)
        assert gf.전투_결과_정리(상태) == 종료 == "아군승리"
        scenario.보상_수령(상태)
        전투들.append({"적": 적, **기록})
        gf.휴식(상태)  # 살의의 파동은 휴식당 1회 - 마을에서 쉬고 다시 들어간다
        gf.던전_진입(상태, 선더랜드)
        합 = {
            k: sum(b.get(k, 0) for b in 전투들)
            for k in ("살의피해", "정신이 번쩍!", "빙결", "화상판정", *골드스킬)
        }
        if all(합.values()):
            break

    def 합계(키):
        return sum(b.get(키, 0) for b in 전투들)

    assert 합계("살의의 파동") and 합계("살의피해"), 전투들
    assert 합계("파이어 웨이브") and 합계("진공참") and 합계("아이스 웨이브"), 전투들
    assert 합계("정신이 번쩍!") and 합계("화상판정"), 전투들
    assert 합계("빙결") + 합계("화상"), 전투들  # 건강 내성에 실패한 적이 실제로 있다
    assert all(b.get("정신이 번쩍!", 0) <= 1 for b in 전투들), 전투들  # 전투당 한 번
    assert all(b.get("살의의 파동", 0) <= 1 for b in 전투들), 전투들  # 휴식당 1회
    golden("scenario_S32_asura", 전투들)
