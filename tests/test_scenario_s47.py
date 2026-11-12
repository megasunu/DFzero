"""S47 제아봉침 실전 - 퍽 획득부터 시한부 사망, 휴식 뒤 다음 전투까지 이어진다 (docs/scenarios.md, #311).

기본 4인 파티에서 귀검사만 레벨 19까지 키우며 18->19 퍽획득(4차수)에서 제아봉침을 고른다(그 밖의 퍽은 결정적 첫 퍽).
서리 머크우드(D07) 인카운트를 **실제로** 치르며 귀검사의 첫 차례에 [스킬]로 제아봉칩이십오만배를 쓰고 나머지는
[자동전투]로 진행한다. 쓴 순간 행동·MP가 그대로이고 약점 아닌 능력치 +10·HP가 오르는지, 그 뒤 살아 있는 동안
HP가 1 아래로 내려가지 않는지(불사), 다음 자기 차례에 행동이 하나씩 늘었는지, 그 차례 끝에 시한부로
사망하는지 본다(전투가 먼저 끝나 전투 끝에 죽는 경우는 tests/test_perk_jeabong.py). 휴식하면 다시 살아나 다음 전투에서 스킬을 다시 쓸 수 있고, 자동전투는
그 스킬을 쓰지 않는다. 규칙의 값은 tests/test_perk_jeabong.py가 본다.
"""

import pytest

import gameflow as gf
from game.data import common_names
from game.system import character_data_system as 캐릭터데이터
from game.system import rng
from game.system.combat import stats
import scenario
import support
from tests.support import 구현된_전직

서리 = "dungeon_01A_D07_frost_mirkwood"
시드 = 5  # 다음 자기 차례 끝까지 가는 전투(2026-11-12 그란플로리스 출현표 #665로 7에서 5로 - D07 0~14 중 다른 시드는 그 전에 전투가 끝나 전투 끝에 죽는다 - 단위 테스트가 본다)
스킬 = "제아봉칩이십오만배"
행동들 = ("일반행동", "보조행동", "반응행동")


def _퍽고르기(캐릭터, 후보):
    if 캐릭터["직업"] == "귀검사":
        for n, d in 후보:
            if n == "제아봉침":
                return n, d
    return 후보[0]


def _나(상태, 원본):
    return next(x for x in 상태["전투상태"]["참가자"] if x["원본"] is 원본)


def _사용(상태, p, 기록):
    """귀검사의 차례에 [스킬] 제아봉칩이십오만배 - 쓴 순간의 변화를 단언한다."""
    전투상태 = 상태["전투상태"]
    약점 = set(캐릭터데이터.약점스탯_목록(p["원본"]))
    전 = {s: stats.유효_능력치값(전투상태, p, s) for s in common_names.능력치_목록}
    HP, MP, 자원 = p["현재HP"], p["현재MP"], dict(p["행동자원"])
    gf.아군_스킬사용(상태, 스킬)
    assert p["현재MP"] == MP and p["행동자원"] == 자원  # 행동·MP를 쓰지 않는다
    for s in common_names.능력치_목록:
        assert stats.유효_능력치값(전투상태, p, s) - 전[s] == (
            0 if s in 약점 else 10
        ), s
    assert p["현재HP"] > HP  # 건강이 올라 현재HP도 오른다
    assert "시한부" in {d["이름"] for d in p["디버프"]}
    기록.update(사용라운드=전투상태["라운드"], HP증가=p["현재HP"] - HP)


def _실전(상태, 원본, 기록):
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    # 평소 차례의 행동 수(전투 시작 값) - 쓴 차례는 기절이 막 풀려 0일 수 있다(행동 없이 쓰는 스킬)
    기록["기본행동"] = {k: _나(상태, 원본)["행동자원"][k] for k in 행동들}
    for _ in range(300):
        if gf.전투_종료됨(상태):
            return 전투상태["종료"]
        p = _나(상태, 원본)
        if "사용라운드" in 기록 and p["생존"]:
            assert p["현재HP"] >= 1  # 불사
        if gf.아군_차례인가(상태):
            if gf.현재_턴_참가자(상태) is p:
                if "사용라운드" not in 기록:
                    _사용(상태, p, 기록)
                elif "다음차례_행동" not in 기록:
                    기록["다음차례_행동"] = {k: p["행동자원"][k] for k in 행동들}
            gf.자동전투_한_턴(상태)
        else:
            gf.턴_넘기기(상태)
    raise AssertionError("전투가 끝나지 않았다")


@pytest.mark.scenario("S47")
def test_S47_제아봉침_획득_사용_시한부_사망_실전(golden):
    rng.시드(시드)
    상태 = support.새게임()
    파티 = 상태["파티"]["파티원"]
    귀검사 = next(c for c in 파티 if c["직업"] == "귀검사")
    support.성장(상태, 귀검사, 19, 전직=구현된_전직["귀검사"], 퍽고르기=_퍽고르기)
    assert 스킬 in 귀검사["보유스킬"]  # 레벨 19 퍽획득(4차수)으로 얻었다
    gf.파티_최대치로_회복(상태)

    gf.던전_진입(상태, 서리)
    scenario.인카운트까지_걷기(상태)
    기록 = {}
    종료 = _실전(상태, 귀검사, 기록)
    전투상태 = 상태["전투상태"]
    p = _나(상태, 귀검사)
    assert not p["생존"] and p["현재HP"] == 0
    사망 = [
        r["비고"]
        for r in 전투상태["로그"]
        if r.get("대상") == p["이름"] and "사망" in str(r.get("비고"))
    ]
    assert len(사망) == 1
    # 다음 자기 차례에 행동이 하나씩 늘었고 그 차례 끝에 시한부로 죽었다
    assert 기록["다음차례_행동"] == {k: 기록["기본행동"][k] + 1 for k in 행동들}
    assert 사망[0].startswith("시한부가 다해")
    gf.전투_결과_정리(상태)
    assert 귀검사["현재HP"] == 0
    if 종료 == "아군승리":
        scenario.보상_수령(상태)

    # 휴식하면 살아나고 스킬도 다시 쓸 수 있다 - 다음 전투는 [자동전투]만(스킬을 쓰지 않는다)
    gf.휴식(상태)
    assert 귀검사["현재HP"] == gf.캐릭터_최대HP(상태, 귀검사)
    gf.던전_진입(상태, 서리)
    scenario.인카운트까지_걷기(상태)
    p = _나(상태, 귀검사)
    assert gf.스킬_사용_가능여부(상태, p, 스킬)[0]
    다음종료 = scenario.실전(상태)
    assert not any(r.get("스킬") == 스킬 for r in 상태["전투상태"]["로그"])
    assert "시한부" not in {d["이름"] for d in p["디버프"]}
    golden(
        "scenario_S47_jeabong",
        {
            "종료": 종료,
            "사용라운드": 기록["사용라운드"],
            "HP증가": 기록["HP증가"],
            "다음차례_행동": 기록.get("다음차례_행동"),
            "사망": 사망[0],
            "다음전투": 다음종료,
        },
    )
