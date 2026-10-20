"""S31 프렌드 실드 실전 - 퍽으로 얻은 반응스킬이 실제 몬스터 공격을 아군에게 옮긴다 (docs/scenarios.md).

기본 4인 파티를 레벨 5까지 키우며 3->4 퍽획득(1차수)에서 귀검사가 "프렌드 실드"를 고른다(그 밖은 결정적 첫 퍽).
고블린 무리를 [자동전투]로 **실제로** 치러(반응 자동 사용) 프렌드 실드가 나올 때까지(최대 10번) 진행한다 - 쓴 직후의
몬스터 공격은 고른 아군(지금 체력이 가장 많은 아군)이 맞고, 전투당 1회라 그 전투에서 다시 쓰지 않는다.
규칙의 값은 tests/test_perks_common.py가 본다.
"""

import pytest

import gameflow as gf
from game.system import rng
import scenario
import support
from tests.test_gameflow_scenarios import 구현된_전직

시드 = 0


@pytest.mark.scenario("S31")
def test_S31_프렌드_실드_실전(golden):
    rng.시드(시드)
    상태 = support.새게임()
    파티 = 상태["파티"]["파티원"]
    귀검사 = next(c for c in 파티 if c["직업"] == "귀검사")
    for 캐릭터 in 파티:
        support.성장(
            상태,
            캐릭터,
            5,
            전직=구현된_전직[캐릭터["직업"]],
            퍽고르기=lambda c, 후보: next(
                ((n, d) for n, d in 후보 if n == "프렌드 실드" and c is 귀검사),
                후보[0],
            ),
        )
    assert "프렌드 실드" in 귀검사["보유스킬"]
    gf.파티_최대치로_회복(상태)
    기록 = _진행(상태, 귀검사["캐릭터명"])
    assert 기록, "프렌드 실드가 한 번도 나오지 않았다"
    golden("scenario_S31_friend_shield", 기록)


def _진행(상태, 시전자):
    for 번 in range(1, 11):
        gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=5, 차수=1)
        종료 = scenario.실전(상태)
        로그 = [e for e in 상태["전투상태"]["로그"] if isinstance(e, dict)]
        assert gf.전투_결과_정리(상태) == 종료
        사용 = [
            i
            for i, e in enumerate(로그)
            if e.get("반응") == "프렌드 실드"
            and str(e.get("비고", "")).startswith("이번 라운드 동안")
        ]
        assert len(사용) <= 1  # 전투당 1회
        if 사용:
            받는 = (
                로그[사용[0]]["비고"].split("이번 라운드 동안 ")[1].split("이(가)")[0]
            )
            다음 = next(e for e in 로그[사용[0] + 1 :] if "대상" in e)
            assert 받는 != 시전자 and 다음["대상"] == 받는, 다음
            return [{"번": 번, "종료": 종료, "받는": 받는}]
        gf.파티_최대치로_회복(상태)
    return []
