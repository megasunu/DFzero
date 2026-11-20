"""combat/ 시험 공용 픽스처.

`전장`은 고블린 셋과 4인 파티(귀검사·격투가·거너·마법사)의 전투 - 전투 규칙 시험들이 같이 쓴다.
같은 이름의 픽스처를 파일 안에 따로 둔 시험은 그쪽이 우선한다(pytest 규칙).
"""

import pytest

import gameflow as gf
from game.system import rng
from tests import support


@pytest.fixture
def 전장():
    rng.시드(7)
    상태 = support.새게임(
        [("", "귀검사"), ("", "격투가"), ("", "거너"), ("", "마법사")]
    )
    gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    적 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "적"),
        key=lambda p: p["대형위치"],
    )
    아군 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "아군"),
        key=lambda p: p["대형위치"],
    )
    return 상태, 전투상태, 적, 아군
