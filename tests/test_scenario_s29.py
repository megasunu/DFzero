"""S29 포켓몬 날씨 실전 - 잔비/가뭄이 실제 전투에서 이어진다 (docs/scenarios.md).

기본 4인 파티를 레벨 20까지 키우며 18->19 퍽획득(4차수)에서 모두 "포켓몬"을 고르고 귀검사는 잔비, 격투가는 가뭄을
고른다(나머지는 첫 후보, 그 전은 결정적 첫 퍽). 결빙의 케라하·시가브·힐가브를 레벨 25로 불러 [자동전투]로 **실제로** 치른다.
전투 시작에 날씨가 걸리고(둘 다 있으니 차례가 뒤인 쪽), 4라운드 이상 간 전투에서는 끝날 때 날씨가 걷혀 있다.
4라운드 이상 가는 전투가 나올 때까지(최대 15번) 진행한다. 규칙의 값은 tests/test_perks_common.py가 본다.
"""

import pytest

import gameflow as gf
from game.system import rng
import scenario
import support
from tests.test_gameflow_scenarios import 구현된_전직

시드 = 0
고를특성 = {"귀검사": "잔비", "격투가": "가뭄"}


@pytest.mark.scenario("S29")
def test_S29_포켓몬_날씨_실전(golden, monkeypatch):
    rng.시드(시드)
    상태 = support.새게임()
    파티 = 상태["파티"]["파티원"]
    원래 = support.퍽_선택값

    def 퍽_선택값(캐릭터, 이름, 정의):
        선택 = 원래(캐릭터, 이름, 정의)
        if 이름 == "포켓몬":
            선택["선택특성"] = 고를특성.get(캐릭터["직업"], 선택["선택특성"])
        return 선택

    monkeypatch.setattr(support, "퍽_선택값", 퍽_선택값)
    for 캐릭터 in 파티:
        support.성장(
            상태,
            캐릭터,
            20,
            전직=구현된_전직[캐릭터["직업"]],
            퍽고르기=lambda c, 후보: next(
                ((n, d) for n, d in 후보 if n == "포켓몬"), 후보[0]
            ),
        )
        if 캐릭터["직업"] in 고를특성:
            assert 고를특성[캐릭터["직업"]] in 캐릭터["보유특성"]
    gf.파티_최대치로_회복(상태)

    기록 = []
    for 번 in range(1, 16):
        gf.전투_시작(
            상태,
            ["결빙의 케라하", "시가브", "힐가브", "시가브", "힐가브"],
            레벨=25,
            차수=3,
        )
        support.반응_처리(상태)
        전투상태 = 상태["전투상태"]
        날씨 = dict(전투상태["날씨"])
        assert 날씨["남은라운드"] == 3 and 날씨["이름"] in ("비", "햇살")
        종료 = scenario.실전(상태)
        assert gf.전투_결과_정리(상태) == 종료 == "아군승리"
        라운드 = 전투상태["라운드"]
        if 라운드 >= 4:
            assert "날씨" not in 전투상태
        else:
            assert 전투상태["날씨"]["남은라운드"] == 4 - 라운드
        기록.append({"번": 번, "날씨": 날씨["이름"], "라운드": 라운드})
        gf.파티_최대치로_회복(상태)
        if 라운드 >= 4:
            break
    assert 기록[-1]["라운드"] >= 4, 기록
    golden("scenario_S29_pokemon_weather", 기록)
