"""S2 스킬 실전 (docs/scenarios.md).

레벨 5, 스킬을 전부 배운 4인 파티가 [자동전투]가 아니라 스킬 우선 정책(tests/scenario.py)으로
로리엔 인카운트(고블린), 머크우드 인카운트(루가루/고블린), 머크우드 보스(타우)를 **실제로** 치른다.
5개 직업을 각각 선두로 해 5번 돌린다. 스킬 하나하나의 결과는 test_combat_skills.py(골든)가 보고,
여기서는 스킬이 실전의 흐름 속에서 자원/행동/효과를 제대로 쓰고 거두는지를 본다.
"""

import pytest

from game.system import rng
import gameflow as gf
import scenario
import support

직업들 = ["귀검사", "격투가", "거너", "마법사", "프리스트"]
로리엔 = "dungeon_01A_D01_Lorien"
머크우드 = "dungeon_01A_D03_mirkwood"
행동종류 = ("일반행동", "보조행동", "쇼타임행동")


def _스킬_검사(상태, 사용):
    """스킬 한 번의 결과가 자원/행동/효과 규칙에 맞는지."""
    데이터 = 상태["스킬데이터모음"][사용["스킬"]]
    assert 사용["MP소모"] == (데이터.get("MP소모") or 0), 사용
    행동 = {k: v for k, v in 사용["행동소비"].items() if k in 행동종류}
    assert sum(행동.values()) == 1, f"행동은 정확히 1개 소비: {사용}"
    분류 = 사용["분류"]
    if 분류 == "공격스킬":
        assert 사용["적HP변화"] <= 0, 사용
    elif 분류 == "회복스킬":
        assert sum(사용["아군HP변화"].values()) > 0, 사용
        assert 사용["적HP변화"] == 0
    elif 분류 in ("버프스킬", "자원스킬", "소환스킬"):
        assert 사용["적HP변화"] == 0, 사용
    if 분류 == "버프스킬":
        전 = sum(len(v["버프"]) for v in 사용["효과전"].values())
        후 = sum(len(v["버프"]) for v in 사용["효과후"].values())
        assert 후 > 전 or 후 == 전 and 전 > 0, f"버프가 걸리지 않았다: {사용}"
    if 분류 == "해제스킬":
        전 = sum(len(v["디버프"]) + len(v["상태이상"]) for v in 사용["효과전"].values())
        후 = sum(len(v["디버프"]) + len(v["상태이상"]) for v in 사용["효과후"].values())
        assert 후 < 전, f"해제가 아무것도 풀지 못했다: {사용}"


def _효과_검사(사용기록, 효과기록):
    """지속턴은 다시 걸지 않는 한 줄기만 하고, 0 이하로 남아 있지 않다. 사라진 효과 수를 센다."""
    만료 = 0
    for 앞, 뒤 in zip(효과기록, 효과기록[1:]):
        다시건 = any(
            앞["라운드"] <= u["라운드"] <= 뒤["라운드"] and u["분류"] == "버프스킬"
            for u in 사용기록
        )
        for 이름, 앞효과 in 앞["효과"].items():
            뒤효과 = 뒤["효과"].get(이름)
            if 뒤효과 is None:
                continue  # 쓰러졌다
            for 종류 in ("버프", "디버프"):
                for 효과, 지속 in 앞효과[종류].items():
                    if 효과 not in 뒤효과[종류]:
                        만료 += 1
                    elif 지속 is not None and not 다시건:
                        assert 뒤효과[종류][효과] <= 지속, (이름, 효과, 앞["라운드"])
    for 기록 in 효과기록:
        for 이름, 효과 in 기록["효과"].items():
            for 종류 in ("버프", "디버프"):
                for 지속 in 효과[종류].values():
                    assert 지속 is None or 지속 >= 1, (이름, 기록["라운드"])
    return 만료


def _전투(상태, 라벨, 결과목록):
    """지금 열린 전투를 스킬 우선 정책으로 치르고 요약을 결과목록에 더한다."""
    적 = [e["이름"] for e in gf.적_목록(상태)]
    사용, 효과 = [], []
    종료 = scenario.스킬_실전(상태, 사용, 효과)
    for u in 사용:
        _스킬_검사(상태, u)
    만료 = _효과_검사(사용, 효과)
    스킬수 = {}
    for u in 사용:
        스킬수[u["스킬"]] = 스킬수.get(u["스킬"], 0) + 1
    관측 = sorted({s for r in 효과 for v in r["효과"].values() for s in v["상태이상"]})
    assert 종료 == "아군승리", f"{라벨} {적}: {종료}"
    결과목록.append(
        {
            "라벨": 라벨,
            "적": 적,
            "라운드": 상태["전투상태"]["라운드"],
            "스킬": 스킬수,
            "MP사용": sum(u["MP소모"] for u in 사용),
            "아군HP": scenario.전투중_아군_HP(상태),
            "만료된_효과": 만료,
            "관측된_상태이상": 관측,
        }
    )


@pytest.mark.scenario("S2")
@pytest.mark.parametrize("순번, 직업", list(enumerate(직업들)))
def test_S2_스킬_실전(순번, 직업, golden):
    rng.시드(100 + 순번)
    파티 = [직업] + [j for j in 직업들 if j != 직업][:3]
    상태 = support.새게임([("", j) for j in 파티])
    for 캐릭터 in 상태["파티"]["파티원"]:
        support.성장(상태, 캐릭터, 5, 스킬습득=True)
        assert len(캐릭터["보유스킬"]) > 1
    gf.파티_최대치로_회복(상태)
    결과 = []

    def 전투처리(라벨):
        def _처리(s):
            _전투(s, 라벨, 결과)

        return _처리

    # 로리엔/머크우드 인카운트 - 전투 사이에 휴식(마을 휴식 호출)으로 MP를 채운다
    for 이름, 던전 in (("로리엔 인카운트", 로리엔), ("머크우드 인카운트", 머크우드)):
        gf.던전_진입(상태, 던전)
        scenario.인카운트까지_걷기(상태)
        전투처리(이름)(상태)
        assert gf.전투_결과_정리(상태) == "아군승리"
        gf.휴식(상태)

    # 머크우드 보스(타우) - 가는 길의 인카운트도 같은 정책으로 싸운다
    gf.던전_진입(상태, 머크우드)
    결과_보스, _ = support.보스_처치(상태, 전투처리=전투처리("머크우드 보스 길목"))
    assert 결과_보스 == "아군승리"
    assert "타우 비스트" in 결과[-1]["적"]
    결과[-1]["라벨"] = "머크우드 보스"

    # 직업마다 자기 스킬을 하나는 실전에서 썼다
    쓴 = {s for r in 결과 for s in r["스킬"]}
    for 캐릭터 in 상태["파티"]["파티원"]:
        assert 쓴 & set(캐릭터["보유스킬"]), 캐릭터["직업"]
    golden(f"scenario_S2_skills_{직업}", 결과)
