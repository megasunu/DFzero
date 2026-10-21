"""S27 포켓몬 실전 - 포켓몬 퍽으로 고른 특성이 실제 진행에서 이어진다 (docs/scenarios.md).

기본 4인 파티를 레벨 20까지 키우며 18->19 퍽획득(4차수)에서 모두 "포켓몬"을 고르고 특성은 귀검사 마중물(수),
격투가 타오르는불꽃(화), 거너 질풍날개, 프리스트 불가사의부적을 고른다(그 전은 결정적 첫 퍽). 서리 머크우드(D07 - 시가브
수속성, 힐가브 화속성)의 몬스터를 파티와 같은 레벨 20으로 불러 [자동전투]로 **실제로** 치러(던전 인카운트는 레벨 4라
공격을 받기 전에 끝난다) 흡수(면역 + 회복 로그)가 나올 때까지(최대 15번) 진행한다.
전투 시작마다 HP가 가득인 질풍날개 거너는 우선도가 1 올라 있다. 규칙의 값은 tests/test_perks_common.py가 본다.
"""

import pytest

import gameflow as gf
from game.system import rng
from game.system.combat import stats
import scenario
import support
from tests.support import 구현된_전직

시드 = 0
고를특성 = {
    "귀검사": "마중물",
    "격투가": "타오르는불꽃",
    "거너": "질풍날개",
    "프리스트": "불가사의부적",
}


@pytest.mark.scenario("S27")
def test_S27_포켓몬_실전(golden, monkeypatch):
    rng.시드(시드)
    상태 = support.새게임()
    파티 = 상태["파티"]["파티원"]
    원래 = support.퍽_선택값

    def 퍽_선택값(캐릭터, 이름, 정의):
        선택 = 원래(캐릭터, 이름, 정의)
        if 이름 == "포켓몬":
            선택["선택특성"] = 고를특성[캐릭터["직업"]]
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
        assert 고를특성[캐릭터["직업"]] in 캐릭터["보유특성"]
    gf.파티_최대치로_회복(상태)

    흡수 = []
    for 번 in range(1, 16):
        gf.전투_시작(상태, ["시가브", "힐가브", "시가브", "힐가브"], 레벨=20, 차수=3)
        support.반응_처리(상태)
        전투상태 = 상태["전투상태"]
        거너 = next(p for p in 전투상태["참가자"] if p["원본"]["직업"] == "거너")
        assert 거너.get("질풍날개") is True  # 전투 시작에 HP 가득
        assert 거너["우선도"] == stats.유효_우선도(전투상태, 거너)
        종료 = scenario.실전(상태)
        assert gf.전투_결과_정리(상태) == 종료 == "아군승리"
        로그 = [e for e in 전투상태["로그"] if isinstance(e, dict)]
        흡수 += [
            (번, e["대상"], e["회복"]) for e in 로그 if e.get("비고") == "속성 흡수"
        ]
        gf.파티_최대치로_회복(상태)
        if 흡수:
            break
    assert 흡수, "흡수가 한 번도 나오지 않았다"
    golden("scenario_S27_pokemon", {"흡수": 흡수})
