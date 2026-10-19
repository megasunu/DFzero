"""S14 얀데레·흡혈귀 퍽 실전 - 레벨업에서 고른 두 공용 퍽이 실제 전투에 반영된다 (docs/scenarios.md).

4인 기본 파티를 레벨 4까지 키우며 3->4 퍽획득에서 귀검사는 "얀데레", 격투가는 "흡혈귀"를 고른다(나머지는
결정적 첫 퍽). 귀검사에게는 집요함이 있어야 얀데레가 드러나므로 "마법으로 봉인된 소검"을 [전문직업]
봉인해제/봉인변환으로 "맹타"(집요함 +1)가 나올 때까지 바꿔 쥔다(봉인 장비는 무작위로만 얻어 소지품에 넣는다).
로리엔(D01) 인카운트를 [자동전투]로 **실제로** 치러 격투가의 흡혈 회복과 귀검사의 펌블 집요함 증폭이
로그에 나올 때까지(최대 12번) 진행한다. 수치 규칙 하나하나는 tests/test_combat_rules.py "얀데레 퍽"·
"흡혈귀 퍽" 절이 값으로 검사한다.
"""

import random

import pytest

import gameflow as gf
import scenario
import support
from game.system.combat import stats

로리엔 = "dungeon_01A_D01_Lorien"
시드 = 0
소검 = "마법으로 봉인된 소검"
고를퍽 = {"귀검사": "얀데레", "격투가": "흡혈귀"}


def _퍽고르기(캐릭터, 후보):
    원하는 = 고를퍽.get(캐릭터["직업"])
    return next(((n, d) for n, d in 후보 if n == 원하는), 후보[0])


def _맹타_소검(상태, 귀검사):
    """장착한 봉인 소검을 풀고 "맹타"가 나올 때까지 봉인변환한다. 바꾼 횟수."""
    [항목] = [
        h
        for h in gf.전문직업_봉인목록(상태, "봉인해제")
        if h["캐릭터"] is 귀검사 and h["슬롯"] == "무기"
    ]
    이름 = gf.전문직업_봉인해제(상태, 항목)
    횟수 = 0
    while 상태["상점카탈로그"]["장비"]["무기"][이름]["마봉능력"] != "맹타":
        [항목] = [
            h
            for h in gf.전문직업_봉인목록(상태, "봉인변환")
            if h["캐릭터"] is 귀검사 and h["슬롯"] == "무기"
        ]
        이름 = gf.전문직업_봉인변환(상태, 항목)
        횟수 += 1
        assert 횟수 < 200
    return 횟수


@pytest.mark.scenario("S14")
def test_S14_얀데레_흡혈귀_실전(golden):
    random.seed(시드)
    상태 = support.새게임()
    파티 = 상태["파티"]["파티원"]
    for 캐릭터 in 파티:
        support.성장(상태, 캐릭터, 4, 퍽고르기=_퍽고르기)
    귀검사 = next(c for c in 파티 if c["직업"] == "귀검사")
    격투가 = next(c for c in 파티 if c["직업"] == "격투가")
    assert "얀데레" in 귀검사["보유특성"] and "흡혈귀" in 격투가["보유특성"]
    assert {"암속성", "수속성"} <= set(격투가["저항"])
    assert {"화속성", "명속성"} <= set(격투가["취약"])

    소지품 = 상태["소지품"]
    소지품["골드"] = 100000
    소지품["재료"]["레어 소울"] = 1000
    소지품["장비"][소검] = 1
    gf.장비_교체(상태, 귀검사, "무기", 소검)
    변환 = _맹타_소검(상태, 귀검사)
    gf.파티_최대치로_회복(상태)

    gf.던전_진입(상태, 로리엔)
    기록 = []
    for _ in range(12):
        적 = scenario.인카운트까지_걷기(상태)
        전투상태 = 상태["전투상태"]
        귀검사참가자 = next(p for p in 전투상태["참가자"] if p["원본"] is 귀검사)
        종료 = scenario.실전(상태)
        로그 = [e for e in 전투상태["로그"] if isinstance(e, dict)]
        흡혈 = [e for e in 로그 if e.get("비고") == "흡혈"]
        집요 = [
            e
            for e in 로그
            if e.get("비고") == "집요함" and e["공격자"] == 귀검사참가자["이름"]
        ]
        증폭 = [e for e in 집요 if "펌블증폭" in e]
        for e in 흡혈:  # 흡혈은 흡혈귀 격투가만
            assert e["공격자"] == 격투가["캐릭터명"] and e["회복"] > 0
        for e in 증폭:  # 치명타 주사위 기본 1 -> 집요함 2배
            assert e["펌블증폭"] == 1 + stats.치명타_주사위수(전투상태, 귀검사참가자)
        assert gf.전투_결과_정리(상태) == 종료
        기록.append(
            {
                "적": 적,
                "종료": 종료,
                "흡혈": len(흡혈),
                "흡혈회복": sum(e["회복"] for e in 흡혈),
                "집요함": len(집요),
                "펌블증폭": len(증폭),
            }
        )
        if 종료 != "아군승리":
            break
        scenario.보상_수령(상태)
        if sum(r["흡혈"] for r in 기록) and sum(r["펌블증폭"] for r in 기록):
            break

    assert sum(r["흡혈"] for r in 기록) > 0, 기록
    assert sum(r["펌블증폭"] for r in 기록) > 0, 기록
    golden("scenario_S14_yandere_vampire", {"소검_변환횟수": 변환, "전투": 기록})
