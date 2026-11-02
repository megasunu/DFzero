"""S44 - 2차수 레어 드랍과 측정 레어 장비·인형(2026-11-02 사용자 결정) 실전.

밸런스 측정 조건 레벨 7 파티(무작위 한 명이 레어 무기·레어 방어구 세트·금도금 세트)가 아몬 하층(D11)을 걸어
인카운트를 실전으로 싸운다. 전투마다 아라드의 흔한 인형 하나가 들어오고, 이긴 전투의 전리품에서 레어 장비가
나오면 소지품과 도감에 들어간다."""

import pytest

from game.system import rng
import gameflow as gf
import scenario
import support

시드 = 1
_아몬하층 = "dungeon_02A_D11_amon_lower"
_최대전투 = 30


def _레어도(상태, 이름):
    return next(
        (
            탭[이름].get("레어도")
            for 탭 in 상태["상점카탈로그"]["장비"].values()
            if 이름 in 탭
        ),
        None,
    )


@pytest.mark.scenario("S44")
def test_S44_아몬_하층_레어_드랍_실전():
    rng.시드(시드)
    상태 = support.새게임()
    scenario.측정_파티_준비(상태, 7)
    착용자 = [
        c
        for c in 상태["파티"]["파티원"]
        if gf.캐릭터_장착아이템(상태, c, "무기")["레어도"] == "레어"
    ]
    assert len(착용자) == 1
    기록 = {"승리": 0, "패배": 0, "인형": set(), "레어": []}
    for _ in range(_최대전투):
        gf.휴식(상태)
        gf.던전_진입(상태, _아몬하층)
        scenario.인카운트까지_걷기(상태)
        종료 = scenario.측정_실전(상태)
        인형 = [
            x["아이템"]
            for x in 상태["전투상태"]["로그"]
            if "인형" in str(x.get("행동", ""))
        ]
        assert len(인형) == 1 and 인형[0] in scenario.측정_인형
        기록["인형"].add(인형[0])
        gf.전투_결과_정리(상태)
        if 종료 == "아군승리":
            기록["승리"] += 1
            for 이름, _ in 상태["전투_전리품"]["아이템"]:
                if _레어도(상태, 이름) == "레어":
                    기록["레어"].append(이름)
                    assert 상태["소지품"]["장비"].get(이름, 0) >= 1
            if gf.전투_보상_대기중(상태):
                scenario.보상_수령(상태)
        else:
            기록["패배"] += 1
        상태["던전상태"] = None
        if 기록["레어"]:
            break
    assert 기록["레어"], 기록
    assert 기록["승리"] >= 1
