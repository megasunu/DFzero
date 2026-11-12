"""S51 트리거형 퍽 특성 실전 - 퍽으로 얻은 호신연격·정밀한공격·이중극점이 실제 전투에서 발동한다 (docs/scenarios.md, #575).

기본 4인 파티에서 격투가만 레벨 19까지 키우며 퍽획득에서 호신연격 -> 정밀한공격 -> 이중극점 순으로 고른다(그 밖의 퍽은
결정적 첫 퍽 - 삼중극점은 레벨 19까지 3차수 퍽 칸이 남지 않아 단위 테스트가 본다). [설정] 전투로그 "자세하게"로 서리 머크우드(D07)
인카운트를 **실제로** [자동전투]로 치르고, 전투 기록에서 정밀한공격 치명타(명중결과가 AC보다 10 이상), 이중극점 재굴림(성공하면
치명타범위 이상), 호신연격스택이 피해 계산에 더해진 것을 찾는다. 기록 문장은 dict가 아니라 글로 보인다. 규칙의 값은
tests/test_perks_common.py가 본다.
"""

import pytest

import gameflow as gf
from game.controller import ctl_battle_log
from game.system import rng
import scenario
import support
from tests.support import 구현된_전직

서리 = "dungeon_01A_D07_frost_mirkwood"
시드 = 9  # 세 특성이 한 전투에서 모두 발동하고 이중극점 성공도 나오는 시드(2026-11-12 그란플로리스 출현표 #665로 4에서 9로, 0~14 중 9·11)
퍽순서 = ("호신연격", "정밀한공격", "이중극점")


def _퍽고르기(캐릭터, 후보):
    if 캐릭터["직업"] == "격투가":
        for 이름 in 퍽순서:
            for n, d in 후보:
                if n == 이름:
                    return n, d
    return 후보[0]


@pytest.mark.scenario("S51")
def test_S51_트리거형_퍽_특성_획득_실전_발동(golden):
    rng.시드(시드)
    상태 = support.새게임()
    격투가 = next(c for c in 상태["파티"]["파티원"] if c["직업"] == "격투가")
    support.성장(상태, 격투가, 19, 전직=구현된_전직["격투가"], 퍽고르기=_퍽고르기)
    assert set(퍽순서) <= set(격투가["보유특성"])  # 퍽획득으로 얻었다
    gf.파티_최대치로_회복(상태)
    원래 = gf.전투로그_방식()
    gf.전투로그_방식_설정("자세하게")
    try:
        gf.던전_진입(상태, 서리)
        scenario.인카운트까지_걷기(상태)
        종료 = scenario.실전(상태)
    finally:
        gf.전투로그_방식_설정(원래)
    로그 = 상태["전투상태"]["로그"]
    판정들 = [r["판정"] for r in 로그 if isinstance(r.get("판정"), dict)]
    정밀 = [p for p in 판정들 if p.get("정밀한공격")]
    극점 = [g for p in 판정들 for g in p.get("극점") or []]
    호신 = [
        v
        for r in 로그
        for n, v in (r.get("피해내역") or {}).get("추가") or []
        if n == "호신연격스택"
    ]
    assert 정밀 and all(p["치명타"] and p["명중결과"] - p["대상AC"] >= 10 for p in 정밀)
    assert 극점 and all(g["특성"] == "이중극점" for g in 극점)
    assert all(g["성공"] == (g["눈"] >= 20) for g in 극점)  # 격투가의 치명타범위 20
    assert any(g["성공"] for g in 극점)
    assert 호신 and min(호신) >= 1
    문장들 = [s for r in 로그 for s in ctl_battle_log.로그_문장들(r)]
    assert any("치명타!(정밀한공격" in s for s in 문장들)
    assert any("이중극점 20 성공" in s for s in 문장들)
    assert any("+호신연격스택(" in s for s in 문장들)
    assert not any("{'" in s for s in 문장들)
    golden(
        "scenario_S51_trigger_perks",
        {
            "종료": 종료,
            "정밀한공격": len(정밀),
            "극점": [[g["눈"], g["성공"]] for g in 극점],
            "호신연격스택": 호신,
        },
    )
