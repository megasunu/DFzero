"""카겔/봄 카겔 특성 "하늘성 불침번"(2026-10-29 사용자 지정) - 전투 시작에 "암전" 상태를 받는다.
암전인 동안 암전이 없는 대상을 공격하면 명중 -2와 명중 불리점. 암전은 공격에 맞거나(명중) 쓰러지면 풀린다.

규칙은 docs/game-rules.md "카겔 - 하늘성 불침번".
"""

import gameflow as gf
from game.system import dice_utils
from game.system.combat import damage
from tests import support


def _암전(참가자):
    return [i for i in 참가자.get("상태이상", []) if i["이름"] == "암전"]


def _판정(전투상태, 공격자, 대상, monkeypatch):
    """눈 10 고정으로 명중 판정 - (명중결과, d20_굴림에 넘긴 불리)."""
    받은 = {}

    def 굴림(이점=False, 불리=False):
        받은.update(이점=이점, 불리=불리)
        return 10

    monkeypatch.setattr(dice_utils, "d20_굴림", 굴림)
    판정 = damage.명중_판정_계산(전투상태, 공격자, 대상, "근력판정")
    return 판정["명중결과"], 받은["불리"]


def test_카겔과_봄_카겔은_하늘성_불침번_특성을_가진다():
    for 이름 in ("카겔", "봄 카겔"):
        assert "하늘성 불침번" in gf.몬스터목록[이름]["특성"]


def test_전투가_시작되면_카겔과_봄_카겔은_지속턴_없는_암전이다():
    _, 적, 아군 = support.시험_전투(["카겔", "봄 카겔"])
    for p in 적:
        assert _암전(p) == [{"이름": "암전", "지속턴": None}]
    assert all(not _암전(p) for p in 아군)


def test_암전이면_암전이_없는_대상에게_명중_마이너스2와_불리점(monkeypatch):
    전투상태, [카겔], 아군 = support.시험_전투(["카겔"])
    암전값, 암전불리 = _판정(전투상태, 카겔, 아군[0], monkeypatch)
    카겔["상태이상"] = [i for i in 카겔["상태이상"] if i["이름"] != "암전"]
    평소값, 평소불리 = _판정(전투상태, 카겔, 아군[0], monkeypatch)
    assert (암전값, 암전불리) == (평소값 - 2, True)
    assert 평소불리 is False


def test_대상도_암전이면_불이익이_없다(monkeypatch):
    전투상태, [카겔, 봄카겔], _ = support.시험_전투(["카겔", "봄 카겔"])
    암전값, 암전불리 = _판정(전투상태, 카겔, 봄카겔, monkeypatch)
    카겔["상태이상"] = [i for i in 카겔["상태이상"] if i["이름"] != "암전"]
    평소값, _ = _판정(전투상태, 카겔, 봄카겔, monkeypatch)
    assert (암전값, 암전불리) == (평소값, False)


def test_자세한_명중_내역에_암전_마이너스2가_보인다(monkeypatch):
    전투상태, [카겔], 아군 = support.시험_전투(["카겔"])
    전투상태["상세로그"] = True
    monkeypatch.setattr(dice_utils, "d20_굴림", lambda 이점=False, 불리=False: 10)
    판정 = damage.명중_판정_계산(전투상태, 카겔, 아군[0], "근력판정")
    assert ("암전", -2) in 판정["명중내역"]


def test_암전은_공격에_맞으면_풀리고_빗나가면_남는다():
    전투상태, [카겔], 아군 = support.시험_전투(["카겔"])
    damage.피격_처리(전투상태, 아군[0], 카겔, {"성공": False})
    assert _암전(카겔)
    damage.피격_처리(전투상태, 아군[0], 카겔, {"성공": True})
    assert not _암전(카겔)


def test_암전은_쓰러지면_풀린다():
    전투상태, [카겔], 아군 = support.시험_전투(["카겔"])
    damage.피해_적용(전투상태, 카겔, 9999, 피해감소무시=True, 방어력무시=True)
    assert not 카겔["생존"]
    assert not _암전(카겔)
