"""S30 위상력 각성 실전 - 위상력 : 스트라이커와 결전기 : 유성검이 실제 진행에서 이어진다 (docs/scenarios.md).

기본 4인 파티를 레벨 9까지 키우며 8->9 퍽획득(2차수)에서 귀검사가 "위상력 각성"을 고르고 특성 "위상력 : 스트라이커"를
고른다(결전기 : 유성검도 배운다, 그 밖은 결정적 첫 퍽). 시가브·힐가브를 파티와 같은 레벨 9로 불러(로리엔
인카운트는 귀검사 차례 전에 끝난다) [자동전투] "전력전투"(스킬 우선) 방식으로 **실제로** 치러 유성검이 나올 때까지
(최대 10번) 진행한다 - 대사 "별빛에☆잠겨라!"가 그 스킬의 피해 줄보다 먼저 나오고, 휴식당 1회라 휴식 전에는 다시 못 쓴다.
규칙의 값은 tests/test_perks_common.py가 본다.
"""

import pytest

import gameflow as gf
from game.system import rng
import scenario
import support
from tests.support import 구현된_전직

# 0 -> 1(2026-10-26): 추천 주/보조/약점(#420)으로 능력치가 바뀌어 옛 시드는 효과가 안 나온다
시드 = 1


@pytest.mark.scenario("S30")
def test_S30_위상력_각성_실전(golden, monkeypatch):
    rng.시드(시드)
    상태 = support.새게임()
    파티 = 상태["파티"]["파티원"]
    귀검사 = next(c for c in 파티 if c["직업"] == "귀검사")
    원래 = support.퍽_선택값

    def 퍽_선택값(캐릭터, 이름, 정의):
        선택 = 원래(캐릭터, 이름, 정의)
        if 이름 == "위상력 각성":
            선택["선택특성"] = "위상력 : 스트라이커"
        return 선택

    monkeypatch.setattr(support, "퍽_선택값", 퍽_선택값)
    for 캐릭터 in 파티:
        support.성장(
            상태,
            캐릭터,
            9,
            전직=구현된_전직[캐릭터["직업"]],
            퍽고르기=lambda c, 후보: next(
                ((n, d) for n, d in 후보 if n == "위상력 각성" and c is 귀검사),
                후보[0],
            ),
        )
    assert "위상력 : 스트라이커" in 귀검사["보유특성"]
    assert "결전기 : 유성검" in 귀검사["보유스킬"]
    gf.파티_최대치로_회복(상태)

    원래방식 = gf.자동전투_방식()
    gf.자동전투_방식_설정("전력전투")  # 일반공격 방식은 스킬을 쓰지 않는다
    try:
        기록 = _진행(상태)
    finally:
        gf.자동전투_방식_설정(원래방식)
    assert 기록, "유성검이 한 번도 나오지 않았다"
    assert 기록[0]["대사"] == 1  # 휴식당 1회
    golden("scenario_S30_phase_power", 기록)


def _진행(상태):
    기록 = []
    for 번 in range(1, 11):
        gf.전투_시작(상태, ["시가브", "힐가브", "시가브", "힐가브"], 레벨=9, 차수=2)
        종료 = scenario.실전(상태)
        로그 = [e for e in 상태["전투상태"]["로그"] if isinstance(e, dict)]
        assert gf.전투_결과_정리(상태) == 종료 == "아군승리"
        대사 = [i for i, e in enumerate(로그) if e.get("대사") == "별빛에☆잠겨라!"]
        if 대사:
            다음 = 로그[대사[0] + 1]
            assert 다음.get("스킬", "").startswith("결전기 : 유성검"), 다음
            기록.append({"번": 번, "대사": len(대사)})
            break
        gf.파티_최대치로_회복(상태)
    return 기록
