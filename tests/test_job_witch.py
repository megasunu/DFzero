"""마도학자(044f) - 빗자루가 있어야 쓰는 스킬(사용무기)."""

import pytest

from game.system import rng
import gameflow as gf
from tests import support


def _마도학자_전투(빗자루):
    """마법사 -> 마도학자 레벨 8(스킬 전부 습득)이 고블린 하나와 싸우는 중. 빗자루면 낡은 빗자루를 든다."""
    rng.시드(5)
    상태 = support.새게임([("", "마법사")])
    c = 상태["파티"]["파티원"][0]
    support.성장(상태, c, 8, 전직="마도학자", 스킬습득=True)
    if 빗자루:
        상태["소지품"]["장비"]["낡은 빗자루"] = 1
        gf.장비_교체(상태, c, "무기", "낡은 빗자루")
    gf.전투_시작(상태, ["고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    return 상태, next(p for p in 상태["전투상태"]["참가자"] if p["원본"] is c)


@pytest.mark.parametrize("스킬", ["빗자루 스핀", "데스 파우더", "칠링 파우더"])
def test_빗자루_스킬은_빗자루를_들어야_쓴다(스킬):
    가능, 사유 = gf.스킬_사용_가능여부(*_마도학자_전투(False), 스킬)
    assert not 가능 and "빗자루" in 사유
    assert gf.스킬_사용_가능여부(*_마도학자_전투(True), 스킬)[0]
