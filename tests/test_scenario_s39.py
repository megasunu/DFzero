"""S39 자동전투 포션 (#177, docs/scenarios.md).

4인 기본 파티가 설정 "자동전투 포션"을 켜고 로리엔 인카운트를 **실제 전투로** 치른다 - 아군 차례는 모두 [자동전투].
인카운트가 뜨면 아군 넷의 HP를 절반으로 깎아 둔다. 일반공격 방식과 전력전투 방식 한 번씩, 그 뒤 설정을 끄고 한 번 더.
아군 차례마다: 켜져 있고 HP 절반 이하·보조행동 있음·HP 포션 있음이면 공격 전에 정확히 하나를 마시고, 아니면 안 마신다.
MP 포션은 자동전투가 쓰지 않는다. 포션 개수와 회복량 규칙은 test_autobattle_potion.py와 test_consumables.py가 값으로 본다.
"""

import pytest

from game.system import rng
import gameflow as gf
import scenario
import support

로리엔 = "dungeon_01A_D01_Lorien"
시드 = 1
HP포션 = "초보자용 HP 포션"
MP포션 = "초보자용 MP 포션"


def _개수(상태, 이름):
    return 상태["소지품"].get("포션", {}).get(이름, 0)


def _전투(상태):
    """아군 차례는 모두 [자동전투]. 차례마다 마셨는지가 조건과 맞는지 보고 마신 횟수를 돌려준다."""
    support.반응_처리(상태)
    for a in gf.아군_목록(상태):
        a["현재HP"] = max(1, gf.캐릭터_최대HP(상태, a["원본"]) // 2)
    마심 = 0
    for _ in range(300):
        if gf.전투_종료됨(상태):
            return 마심
        if not gf.아군_차례인가(상태):
            gf.턴_넘기기(상태)
            continue
        현재 = gf.현재_턴_참가자(상태)
        조건 = (
            gf.자동전투_포션_여부()
            and 현재["현재HP"] * 2 <= gf.캐릭터_최대HP(상태, 현재["원본"])
            and 현재["행동자원"].get("보조행동", 0) > 0
            and _개수(상태, HP포션) > 0
        )
        전 = _개수(상태, HP포션)
        시작 = len(상태["전투상태"]["로그"])
        gf.자동전투_한_턴(상태)
        assert 전 - _개수(상태, HP포션) == (1 if 조건 else 0), (현재["이름"], 조건)
        if 조건:
            첫행동 = next(
                x
                for x in 상태["전투상태"]["로그"][시작:]
                if x.get("공격자") == 현재["이름"]
            )
            assert 첫행동.get("아이템") == HP포션  # 공격보다 먼저
            마심 += 1
    raise AssertionError("전투가 끝나지 않았다")


@pytest.mark.scenario("S39")
def test_S39_자동전투_포션_실전():
    rng.시드(시드)
    상태 = support.새게임()
    상태["소지품"]["포션"] = {HP포션: 6, MP포션: 2}
    gf.던전_진입(상태, 로리엔)
    기록 = []
    for 방식, 켜기 in (("일반공격", True), ("전력전투", True), ("전력전투", False)):
        gf.자동전투_방식_설정(방식)
        gf.자동전투_포션_설정(켜기)
        scenario.인카운트까지_걷기(상태)
        마심 = _전투(상태)
        assert gf.전투_결과_정리(상태) == "아군승리"
        scenario.보상_수령(상태)
        기록.append(마심)
    assert 기록[0] >= 1 and 기록[1] >= 1 and 기록[2] == 0, 기록
    assert _개수(상태, HP포션) == 6 - 기록[0] - 기록[1]
    assert _개수(상태, MP포션) == 2  # MP 포션은 자동전투가 쓰지 않는다
