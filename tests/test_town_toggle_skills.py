# 마을에서 전환스킬(나선의 넨·프렌지) 켜고 끄기(#283). 던전 화면 [스킬]과 같은 규칙 -
# 전투 밖이면 행동/MP 없이 캐릭터 "켜진특성"을 바꾼다(ctl_dungeon.전환스킬_목록/전환스킬_사용).


from game.system import rng
import gameflow as gf
from tests import support


def _넨마스터():
    rng.시드(5)
    상태 = support.새게임([("", "격투가")])
    c = 상태["파티"]["파티원"][0]
    support.성장(상태, c, 8, 전직="넨마스터", 스킬습득=True)
    return 상태, c


def _넨_줄(상태):
    return next(줄 for 줄 in gf.전환스킬_목록(상태) if 줄["스킬"] == "나선의 넨")


def test_마을에서_나선의넨을_MP없이_켜고_끈다():
    상태, c = _넨마스터()
    assert 상태.get("던전상태") is None  # 마을
    줄 = _넨_줄(상태)
    assert 줄["가능"] and 줄["전환"] == "꺼짐" and 줄["캐릭터"] is c
    MP = c["현재MP"]
    결과 = gf.전환스킬_사용(상태, c, "나선의 넨")
    assert 결과["성공"] and "켰다" in 결과["문구"]
    assert c["켜진특성"] == ["나선의 넨"] and c["현재MP"] == MP
    assert _넨_줄(상태)["전환"] == "켜짐"
    assert "껐다" in gf.전환스킬_사용(상태, c, "나선의 넨")["문구"]
    assert c["켜진특성"] == [] and c["현재MP"] == MP


def test_마을에서_켠_전환스킬은_던전과_전투로_이어진다():
    상태, c = _넨마스터()
    gf.전환스킬_사용(상태, c, "나선의 넨")
    gf.던전_진입(상태, "dungeon_01A_D05_thunderland")
    [줄] = [줄 for 줄 in gf.던전스킬_목록(상태) if 줄["스킬"] == "나선의 넨"]
    assert 줄["전환"] == "켜짐"
    gf.전투_시작(상태, ["고블린"], 레벨=1, 차수=1)
    support.반응_처리(상태)
    n = next(p for p in 상태["전투상태"]["참가자"] if p.get("원본") is c)
    assert "나선의 넨" in n["원본"]["켜진특성"]


def test_전환스킬_목록에는_던전스킬이_없다():
    상태, c = _넨마스터()
    c["보유스킬"].append("던전 캠핑")
    이름들 = [줄["스킬"] for 줄 in gf.전환스킬_목록(상태)]
    assert "나선의 넨" in 이름들 and "던전 캠핑" not in 이름들
    assert not gf.전환스킬_사용(상태, c, "던전 캠핑")["성공"]


def test_전환스킬이_없으면_목록이_비어_있다():
    rng.시드(5)
    상태 = support.새게임()
    assert gf.전환스킬_목록(상태) == []


def test_전투_중에는_마을_전환을_쓸_수_없다():
    상태, c = _넨마스터()
    gf.던전_진입(상태, "dungeon_01A_D05_thunderland")
    gf.전투_시작(상태, ["고블린"], 레벨=1, 차수=1)
    support.반응_처리(상태)
    assert gf.전환스킬_목록(상태) == []
    assert not gf.전환스킬_사용(상태, c, "나선의 넨")["성공"]
    assert not (c.get("켜진특성") or [])


def test_쓰러진_캐릭터는_전환스킬을_바꿀_수_없다():
    상태, c = _넨마스터()
    c["현재HP"] = 0
    줄 = _넨_줄(상태)
    assert not 줄["가능"] and "쓰러" in 줄["사유"]
    assert not gf.전환스킬_사용(상태, c, "나선의 넨")["성공"]
    assert not (c.get("켜진특성") or [])


def test_보유하지_않은_전환스킬은_바꿀_수_없다():
    상태, c = _넨마스터()
    다른 = support.새게임()["파티"]["파티원"][0]
    assert not gf.전환스킬_사용(상태, 다른, "나선의 넨")["성공"]
