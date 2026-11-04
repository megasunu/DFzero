"""마을 [NPC] - 마을마다 대화할 수 있는 NPC, 대화 조건, 퀘스트 수락/완료/보상, 세이브(2026-11-04).

규칙은 docs/game-rules.md "NPC / 퀘스트".
"""

import json

import gameflow as gf
from game.system import quest_system, save_system, town_system
from game.system.quest_system import NPC_목록, 퀘스트_목록
from tests import support

로리엔 = "dungeon_01A_D01_Lorien"
세리아_감옥 = (15, 3)


def _로리엔_클리어(상태):
    """로리엔 보스(세리아가 갇힌 감옥)를 깬 기록 - 실제 보상 처리(ctl_rewards)가 남기는 두 기록."""
    town_system.오브젝트_클리어_기록(상태["진행도"], 로리엔, 세리아_감옥)
    town_system.던전_클리어_처리(상태["진행도"], 로리엔)


def _퀘스트(대화, ID):
    return next(q for q in 대화["퀘스트"] if q["ID"] == ID)


# ------------------------------------------------------------------ 데이터


def test_NPC와_퀘스트_데이터는_서로_맞다():
    마을명들 = {m["마을명"] for m in town_system.기본_마을목록()}
    퀘스트ID = [q["ID"] for q in 퀘스트_목록]
    assert len(set(퀘스트ID)) == len(퀘스트ID)
    assert len({n["이름"] for n in NPC_목록}) == len(NPC_목록)
    for npc in NPC_목록:
        assert npc["마을"] == "모든마을" or set(npc["마을"]) <= 마을명들, npc["이름"]
        assert npc["대화"]
        조건 = npc["대화조건"]
        assert 조건 is None or 조건["타입"] in quest_system.조건_타입
    for 퀘스트 in 퀘스트_목록:
        assert 퀘스트["조건"]["타입"] in quest_system.조건_타입
        assert set(퀘스트["보상"]) <= {"골드"}


# ------------------------------------------------------------------ 대화 가능한 NPC


def test_새_게임_엘븐가드에는_라이너스만_있다():
    상태 = support.새게임()
    assert 상태["진행도"]["퀘스트"] == {}
    assert gf.현재_마을정보(상태)["마을명"] == "엘븐가드"
    assert gf.마을_NPC_목록(상태) == ["라이너스"]


def test_로리엔을_깨면_세리아가_엘븐가드에서_대화할_수_있다():
    상태 = support.새게임()
    _로리엔_클리어(상태)
    assert gf.마을_NPC_목록(상태) == ["라이너스", "세리아"]


def test_세리아는_모든_마을에_있고_라이너스는_엘븐가드에만_있다():
    상태 = support.새게임()
    _로리엔_클리어(상태)
    for 마을 in town_system.기본_마을목록():
        상태["진행도"]["현재마을"] = 마을["마을명"]
        목록 = gf.마을_NPC_목록(상태)
        assert "세리아" in 목록, 마을["마을명"]
        assert ("라이너스" in 목록) == (마을["마을명"] == "엘븐가드")


def test_세리아는_퀘스트가_없다():
    상태 = support.새게임()
    _로리엔_클리어(상태)
    대화 = gf.NPC_대화(상태, "세리아")
    assert 대화["이름"] == "세리아" and 대화["대사"]
    assert 대화["퀘스트"] == []


def test_조건을_못_채운_NPC와는_대화할_수_없다():
    상태 = support.새게임()
    for 이름 in ("세리아", "없는사람"):
        try:
            gf.NPC_대화(상태, 이름)
        except ValueError:
            continue
        raise AssertionError(f"{이름}과 대화가 됐다")
    상태["진행도"]["현재마을"] = "헨돈마이어"
    try:
        gf.NPC_대화(상태, "라이너스")  # 다른 마을의 NPC
    except ValueError:
        return
    raise AssertionError("헨돈마이어에서 라이너스와 대화가 됐다")


# ------------------------------------------------------------------ 라이너스 퀘스트


def test_라이너스는_세리아_구출을_부탁한다():
    상태 = support.새게임()
    대화 = gf.NPC_대화(상태, "라이너스")
    assert 대화["대사"] == "로리엔에서 세리아를 구출해주게."
    퀘스트 = _퀘스트(대화, "세리아_구출_의뢰")
    assert 퀘스트["상태"] == "수락전"
    assert 퀘스트["보상"] == "10G"


def test_퀘스트는_수락_진행_완료가능_완료로_간다():
    상태 = support.새게임()
    ID = "세리아_구출_의뢰"
    gf.퀘스트_수락(상태, ID)
    assert 상태["진행도"]["퀘스트"] == {ID: "진행중"}
    assert _퀘스트(gf.NPC_대화(상태, "라이너스"), ID)["상태"] == "진행중"

    _로리엔_클리어(상태)
    assert _퀘스트(gf.NPC_대화(상태, "라이너스"), ID)["상태"] == "완료가능"

    골드 = 상태["소지품"]["골드"]
    assert gf.퀘스트_완료_보고(상태, ID) == {"골드": 10}
    assert 상태["소지품"]["골드"] == 골드 + 10
    assert 상태["진행도"]["퀘스트"] == {ID: "완료"}
    대화 = gf.NPC_대화(상태, "라이너스")
    assert _퀘스트(대화, ID)["상태"] == "완료"
    assert 대화["대사"] != "로리엔에서 세리아를 구출해주게."  # 다 끝나면 인사가 바뀐다


def test_수락_전에_로리엔을_깼으면_수락하자마자_완료할_수_있다():
    상태 = support.새게임()
    _로리엔_클리어(상태)
    ID = "세리아_구출_의뢰"
    assert _퀘스트(gf.NPC_대화(상태, "라이너스"), ID)["상태"] == "수락전"
    gf.퀘스트_수락(상태, ID)
    assert _퀘스트(gf.NPC_대화(상태, "라이너스"), ID)["상태"] == "완료가능"


def test_순서를_어긴_수락과_보고는_막힌다():
    상태 = support.새게임()
    ID = "세리아_구출_의뢰"
    골드 = 상태["소지품"]["골드"]
    for 동작 in (
        lambda: gf.퀘스트_완료_보고(상태, ID),  # 수락 전
        lambda: gf.퀘스트_수락(상태, "없는퀘스트"),
    ):
        try:
            동작()
        except ValueError:
            continue
        raise AssertionError("막히지 않았다")
    gf.퀘스트_수락(상태, ID)
    for 동작 in (
        lambda: gf.퀘스트_수락(상태, ID),  # 두 번 수락
        lambda: gf.퀘스트_완료_보고(상태, ID),  # 조건 전
    ):
        try:
            동작()
        except ValueError:
            continue
        raise AssertionError("막히지 않았다")
    _로리엔_클리어(상태)
    gf.퀘스트_완료_보고(상태, ID)
    try:
        gf.퀘스트_완료_보고(상태, ID)  # 보상 두 번
    except ValueError:
        assert 상태["소지품"]["골드"] == 골드 + 10
        return
    raise AssertionError("보상을 두 번 받았다")


# ------------------------------------------------------------------ 세이브


def test_세이브_왕복에_퀘스트_상태가_남는다(임시_세이브폴더):
    상태 = support.새게임()
    gf.퀘스트_수락(상태, "세리아_구출_의뢰")
    gf.게임_저장(상태, 1)
    불러온 = gf.게임_불러오기(1)
    assert 불러온["진행도"]["퀘스트"] == {"세리아_구출_의뢰": "진행중"}


def test_옛_세이브는_빈_퀘스트_기록으로_불러온다(임시_세이브폴더):
    상태 = support.새게임()
    gf.게임_저장(상태, 1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    저장 = json.loads(경로.read_text(encoding="utf-8"))
    저장["버전"] = 16
    저장["진행도"].pop("퀘스트")
    경로.write_text(json.dumps(저장, ensure_ascii=False), encoding="utf-8")

    불러온 = gf.게임_불러오기(1)
    assert 불러온["진행도"]["퀘스트"] == {}
    assert save_system.세이브_버전 >= 17
    assert gf.마을_NPC_목록(불러온) == ["라이너스"]
