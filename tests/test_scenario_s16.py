"""S16 만독불침·웨펀/아머브레이커·심안 실전 - 전투 특성 퍽이 실제 진행에서 이어진다 (docs/scenarios.md).

기본 4인 파티를 레벨 9(5->6 전직)까지 키우며 3->4 퍽획득에서 귀검사는 "만독불침", 8->9 퍽획득에서 귀검사는
"웨펀브레이커", 격투가는 "아머브레이커"를 고른다(나머지는 결정적 첫 퍽). 심안은 4차수라(레벨 19) 지금 게임에서는
얻을 수 없어 거너에게 특성을 직접 준다. 독의 썬더랜드(D06) 인카운트를 [자동전투]로 **실제로** 치러, 두 브레이커의
디버프 줄이 로그에 나올 때까지(최대 6번) 진행한다. 수치 규칙은 tests/test_perks_common.py가 값으로 본다.
"""

import pytest

from game.system import rng
import gameflow as gf
import scenario
import support
from game.data.ability.job_ability_0000 import 특성목록
from game.system import effect_engine
from tests.test_gameflow_scenarios import 구현된_전직

독천둥 = "dungeon_01A_D06_poison_thunderland"
시드 = 0
고를퍽 = {"귀검사": ["만독불침", "웨펀브레이커"], "격투가": ["아머브레이커"]}


def _퍽고르기(캐릭터, 후보):
    for 원하는 in 고를퍽.get(캐릭터["직업"], []):
        for n, d in 후보:
            if n == 원하는:
                return n, d
    return 후보[0]


@pytest.mark.scenario("S16")
def test_S16_전투_특성_퍽_실전(golden):
    rng.시드(시드)
    상태 = support.새게임()
    파티 = 상태["파티"]["파티원"]
    귀검사 = next(c for c in 파티 if c["직업"] == "귀검사")
    격투가 = next(c for c in 파티 if c["직업"] == "격투가")
    거너 = next(c for c in 파티 if c["직업"] == "거너")
    for 캐릭터 in 파티:
        성장 = support.성장(
            상태, 캐릭터, 9, 전직=구현된_전직[캐릭터["직업"]], 퍽고르기=_퍽고르기
        )
        if 캐릭터 is 귀검사:  # 만독불침을 고른 레벨(4)에 건강이 1 오른다
            레벨별 = {r["레벨"]: r for r in 성장}
            assert 레벨별[4]["선택"].get("퍽이름") == "만독불침", 레벨별[4]["선택"]
            assert 레벨별[4]["능력치"]["건강"] == 레벨별[3]["능력치"]["건강"] + 1
    assert {"만독불침", "웨펀브레이커"} <= set(귀검사["보유특성"])
    assert "아머브레이커" in 격투가["보유특성"]
    effect_engine.특성_부여(거너, "심안", 특성목록["심안"])
    gf.파티_최대치로_회복(상태)

    gf.던전_진입(상태, 독천둥)
    기록 = []
    for _ in range(6):
        적 = scenario.인카운트까지_걷기(상태)
        종료 = scenario.실전(상태)
        전투상태 = 상태["전투상태"]
        로그 = [e for e in 전투상태["로그"] if isinstance(e, dict)]
        아군 = {p["원본"]["직업"]: p for p in 전투상태["참가자"] if p["진영"] == "아군"}
        웨펀 = [
            e
            for e in 로그
            if e.get("공격자") == 아군["귀검사"]["이름"]
            and str(e.get("비고", "")).startswith("특성 - '데미지차감'")
        ]
        아머 = [
            e
            for e in 로그
            if e.get("공격자") == 아군["격투가"]["이름"]
            and str(e.get("비고", "")).startswith("특성 - '방어감소'")
        ]
        for p in 전투상태["참가자"]:
            if p["진영"] != "적":
                continue
            for 변동대상 in ("데미지보너스", "방어력"):
                걸린 = [d for d in p["디버프"] if d.get("특성대상변동") == 변동대상]
                assert len(걸린) <= 10 and all("지속턴" not in d for d in 걸린)
        assert not any(s["이름"] == "중독" for s in 아군["귀검사"]["상태이상"])
        assert not any(s["이름"] == "암흑" for s in 아군["거너"]["상태이상"])
        assert gf.전투_결과_정리(상태) == 종료
        중독면역 = [
            e
            for e in 로그
            if e.get("대상") == 아군["귀검사"]["이름"]
            and "'중독' 상태이상 면역" in str(e.get("비고", ""))
        ]
        기록.append(
            {
                "적": 적,
                "종료": 종료,
                "웨펀": len(웨펀),
                "아머": len(아머),
                "중독면역": len(중독면역),
            }
        )
        if 종료 != "아군승리":
            break
        scenario.보상_수령(상태)
        if sum(r["웨펀"] for r in 기록) and sum(r["아머"] for r in 기록):
            break
    assert sum(r["웨펀"] for r in 기록) > 0, 기록
    assert sum(r["아머"] for r in 기록) > 0, 기록
    golden("scenario_S16_combat_perks", {"전투": 기록})
