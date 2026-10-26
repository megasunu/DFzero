"""S15 원펀맨·인형사·내아내몬 실전 - 세 공용 기능이 실제 진행에서 이어진다 (docs/scenarios.md).

기본 4인 파티를 레벨 6(5->6 전직)까지 키우며 3->4 퍽획득에서 귀검사는 "원펀맨", 프리스트는 "내아내몬"을
고른다(나머지는 결정적 첫 퍽). 마을 소지품에서 인형 "28호"를 [사용]하고(얻는 곳이 아직 없어 소지품에 넣는다)
로리엔(D01) 인카운트를 [자동전투]로 **실제로** 치러, 인형의 넨탄(스스로 행동)과 원펀맨의 합친 일반공격(배수 =
일반행동 x (1 + 추가공격))이 로그에 나올 때까지(최대 8번) 진행한다. 그 뒤 휴식해도 인형이 남는지
(내아내몬), 저장/불러오기 왕복 뒤에도 같은지 본다. 수치 규칙은 tests/test_combat_rules.py 각 절이 값으로 본다.
"""

import pytest

from game.system import rng
import gameflow as gf
import scenario
import support
from tests.support import 구현된_전직

로리엔 = "dungeon_01A_D01_Lorien"
# 2 -> 0(2026-10-26): 추천 주/보조/약점(#420)으로 능력치가 바뀌어 옛 시드는 효과가 안 나온다
시드 = 0  # 예전: 난수 흐름 분리(2026-10-20) 뒤 시드 0은 효과가 안 나와 2를 썼다
고를퍽 = {"귀검사": "원펀맨", "프리스트": "내아내몬"}


def _퍽고르기(캐릭터, 후보):
    원하는 = 고를퍽.get(캐릭터["직업"])
    return next(((n, d) for n, d in 후보 if n == 원하는), 후보[0])


@pytest.mark.scenario("S15")
def test_S15_원펀맨_인형사_내아내몬_실전(golden):
    rng.시드(시드)
    상태 = support.새게임()
    파티 = 상태["파티"]["파티원"]
    for 캐릭터 in 파티:
        support.성장(
            상태, 캐릭터, 6, 전직=구현된_전직[캐릭터["직업"]], 퍽고르기=_퍽고르기
        )
    귀검사 = next(c for c in 파티 if c["직업"] == "귀검사")
    프리스트 = next(c for c in 파티 if c["직업"] == "프리스트")
    assert "원펀맨" in 귀검사["보유특성"] and 귀검사["추가공격"] >= 1
    assert "내아내몬" in 프리스트["보유특성"]
    gf.파티_최대치로_회복(상태)

    상태["소지품"]["소모품"]["28호"] = 1
    인형 = gf.인형_사용(상태, "28호")  # 마을 소지품 [사용]
    증가 = gf.캐릭터_능력치_보정치(상태, 프리스트, "매력")
    assert 인형["지능"] == 16 + 증가 and 인형["레벨"] == 상태["진행도"]["플레이어레벨"]

    gf.던전_진입(상태, 로리엔)
    기록 = []
    for _ in range(8):
        적 = scenario.인카운트까지_걷기(상태)
        종료 = scenario.실전(상태)
        로그 = [e for e in 상태["전투상태"]["로그"] if isinstance(e, dict)]
        넨탄 = [
            e for e in 로그 if e.get("공격자") == "28호" and e.get("스킬") == "넨탄"
        ]
        쉼 = [e for e in 로그 if e.get("공격자") == "28호" and e.get("쉼")]
        한방 = [e for e in 로그 if e.get("종류") == "일반공격" and "배수" in e]
        for e in 한방:  # 일반행동 1 x (1 + 추가공격)
            assert e["배수"] == 1 + 귀검사["추가공격"], e
        assert gf.전투_결과_정리(상태) == 종료
        기록.append(
            {
                "적": 적,
                "종료": 종료,
                "인형_넨탄": len(넨탄),
                "인형_쉼": len(쉼),
                "원펀맨": len(한방),
                "인형HP": (상태["파티"]["인형"] or {}).get("현재HP"),
            }
        )
        # 내아내몬이 있으니 인형은 쓰러져도 파티에 남는다
        assert 상태["파티"]["인형"] is not None
        if 종료 != "아군승리":
            break
        scenario.보상_수령(상태)
        if sum(r["인형_넨탄"] for r in 기록) and sum(r["원펀맨"] for r in 기록):
            break
    assert sum(r["인형_넨탄"] for r in 기록) > 0, 기록
    assert sum(r["원펀맨"] for r in 기록) > 0, 기록

    gf.휴식(상태)  # 내아내몬 - 휴식해도 인형이 남고 회복한다
    인형 = 상태["파티"]["인형"]
    assert 인형 is not None and 인형["현재HP"] == 인형["기본최대HP"]
    gf.게임_저장(상태, 1)
    불러옴 = gf.게임_불러오기(1)
    assert 불러옴["파티"]["인형"] == 인형
    golden("scenario_S15_onepunch_doll", {"전투": 기록, "인형": 인형["기본최대HP"]})
