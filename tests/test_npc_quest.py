"""마을 [NPC] - 마을마다 대화할 수 있는 NPC, 대화 조건, 퀘스트 수락/완료/보상, 세이브(2026-11-04).

규칙은 docs/game-rules.md "NPC / 퀘스트".
"""

import json

import gameflow as gf
from game.system import quest_system, rng, save_system, town_system
from game.system.quest_system import NPC_목록, 퀘스트_목록
from tests import support

로리엔 = "dungeon_01A_D01_Lorien"
세리아_감옥 = (15, 3)
라이너스_평소 = {
    "망가진 장비는 내게 맡기게.",
    "장비관리는 잘 하고 있나?",
    "어이쿠 손이 미끄러졌군.",
}


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
        assert npc["대화"] and all(isinstance(줄, str) and 줄 for 줄 in npc["대화"])
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
    assert 대화["이름"] == "세리아"
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
    assert gf.NPC_말걸기(상태, "라이너스")["대사"] == "로리엔에서 세리아를 구출해주게."
    퀘스트 = _퀘스트(gf.NPC_대화(상태, "라이너스"), "세리아_구출_의뢰")
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
    assert _퀘스트(gf.NPC_대화(상태, "라이너스"), ID)["상태"] == "완료"
    # 첫 대화 뒤로는 평소 대사(퀘스트 진행과 상관없이)
    gf.NPC_말걸기(상태, "라이너스")
    assert gf.NPC_말걸기(상태, "라이너스")["대사"] in 라이너스_평소


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
    저장["진행도"].pop("대화한NPC")
    경로.write_text(json.dumps(저장, ensure_ascii=False), encoding="utf-8")

    불러온 = gf.게임_불러오기(1)
    assert 불러온["진행도"]["퀘스트"] == {}
    assert 불러온["진행도"]["대화한NPC"] == []
    assert save_system.세이브_버전 >= 17
    assert gf.마을_NPC_목록(불러온) == ["라이너스"]


# ------------------------------------------------------------------ NPC 메뉴(대화/퀘스트/상점), 일러스트


def test_NPC마다_메뉴_버튼이_다르다():
    상태 = support.새게임()
    _로리엔_클리어(상태)
    assert gf.NPC_대화(상태, "라이너스")["메뉴"] == ["대화", "퀘스트", "상점"]
    assert gf.NPC_대화(상태, "세리아")["메뉴"] == [
        "대화"
    ]  # 퀘스트 없음, 판매 목록 비어 있음


def test_일러스트는_01번_그림과_장면정보를_함께_준다():
    상태 = support.새게임()
    _로리엔_클리어(상태)
    for 이름, 파일 in (
        ("라이너스", "asset_npc_linus_01.webp"),
        ("세리아", "asset_npc_seria_01.webp"),
    ):
        for 대화 in (gf.NPC_대화(상태, 이름), gf.NPC_말걸기(상태, 이름)):
            assert 대화["일러스트"] == 파일
            장면 = 대화["일러스트장면"]
            assert set(장면) == {"가로", "세로", "열", "시간"}
            assert 장면["열"] == quest_system.장면_열수(장면["가로"], len(장면["시간"]))


def test_일러스트가_미정이면_장면정보가_없다(monkeypatch):
    상태 = support.새게임()
    monkeypatch.setitem(quest_system.NPC_찾기("라이너스"), "일러스트", "미정")
    assert gf.NPC_대화(상태, "라이너스")["일러스트장면"] is None
    assert gf.NPC_말걸기(상태, "라이너스")["일러스트장면"] is None


def test_모든_NPC의_일러스트는_장면정보가_있는_그림이다():
    from game.data.npc.npc_illust_frames import 장면정보

    for NPC in NPC_목록:
        assert NPC["일러스트"] == "미정" or NPC["일러스트"] in 장면정보, NPC["이름"]


def test_판매목록이_있는_NPC는_상점_메뉴가_생기고_그_품목만_판다(monkeypatch):
    상태 = support.새게임()
    라이너스 = quest_system.NPC_찾기("라이너스")
    monkeypatch.setitem(라이너스, "상점판매목록", ["칸나의 수제빵"])
    대화 = gf.NPC_대화(상태, "라이너스")
    assert 대화["메뉴"] == ["대화", "퀘스트", "상점"]
    assert 대화["상점판매목록"] == ["칸나의 수제빵"]
    # 마을 상점(엘븐가드 판매목록)에는 없는 품목 - NPC 상점은 마을 상점과 따로 판다
    마을목록 = gf.현재_마을정보(상태)["상점판매목록"]
    assert "칸나의 수제빵" not in 마을목록
    산것 = gf.상점_구매목록(상태, "소모품", "음식", 대화["상점판매목록"])
    assert [a["이름"] for a in 산것] == ["칸나의 수제빵"]
    assert gf.상점_구매목록(상태, "소모품", "음식", 마을목록) == []


def _언커먼_장비(상태):
    """상점 카탈로그의 언커먼 장비 {이름: 부위탭} - 무기·방어구·장신구 전부(#164)."""
    return {
        이름: 탭
        for 탭, 아이템들 in 상태["상점카탈로그"]["장비"].items()
        for 이름, 아이템 in 아이템들.items()
        if 아이템.get("레어도") == "언커먼"
    }


def test_라이너스는_언커먼_장비_전부를_팔고_마을_상점은_팔지_않는다():
    """#164(2026-11-05 사용자 결정): 언커먼 장비는 NPC 상점에서 판다 - 지금은 엘븐가드 라이너스."""
    상태 = support.새게임()
    언커먼 = _언커먼_장비(상태)
    assert len(언커먼) == 59  # 무기 25, 방어구 25, 장신구 9
    대화 = gf.NPC_대화(상태, "라이너스")
    assert 대화["메뉴"] == ["대화", "퀘스트", "상점"]
    assert sorted(대화["상점판매목록"]) == sorted(언커먼)
    판매목록 = 대화["상점판매목록"]
    for 탭 in set(언커먼.values()):
        보이는것 = {a["이름"] for a in gf.상점_구매목록(상태, "장비", 탭, 판매목록)}
        assert 보이는것 == {이름 for 이름, t in 언커먼.items() if t == 탭}, 탭
    for 마을 in town_system.기본_마을목록():
        assert not set(언커먼) & set(마을["상점판매목록"]), 마을["마을명"]


def test_라이너스_상점에서_언커먼_장비를_사면_골드가_빠지고_소지품에_들어온다():
    상태 = support.새게임()
    판매목록 = gf.NPC_대화(상태, "라이너스")["상점판매목록"]
    상태["소지품"]["골드"] = 100
    금액 = gf.상점_구매(상태, "장비", "상의", "실키얀 상의", 1, 판매목록)
    assert 금액 == 20
    assert gf.상점_보유골드(상태) == 80
    assert 상태["소지품"]["장비"].get("실키얀 상의") == 1


def test_NPC_데이터에는_일러스트와_상점_칸이_있다():
    상태 = support.새게임()
    아이템이름 = {
        이름
        for 탭모음 in 상태["상점카탈로그"].values()
        for 아이템들 in 탭모음.values()
        for 이름 in 아이템들
    }
    for npc in NPC_목록:
        assert isinstance(npc["일러스트"], str) and npc["일러스트"], npc["이름"]
        assert set(npc["상점판매목록"]) <= 아이템이름, npc["이름"]


# ------------------------------------------------------------------ 대화 패턴(첫 대화 / 평소 대사 무작위)

세리아_평소 = {
    "안녕하세요? 세리아 키르민이에요",
    "오늘도 좋은 하루 되세요.",
    "저는 항상 기다리고 있어요.",
}


def test_세리아는_첫_대화에_감사하고_그_뒤로는_평소_대사_셋_중_하나다():
    상태 = support.새게임()
    _로리엔_클리어(상태)
    gf.NPC_대화(상태, "세리아")  # 메뉴를 여는 것은 대화가 아니다
    assert 상태["진행도"]["대화한NPC"] == []
    첫 = gf.NPC_말걸기(상태, "세리아")
    assert (첫["이름"], 첫["대사"]) == ("세리아", "구해주셔서 감사해요.")
    assert 첫["일러스트"] == "asset_npc_seria_01.webp"
    assert 상태["진행도"]["대화한NPC"] == ["세리아"]
    나온 = {gf.NPC_말걸기(상태, "세리아")["대사"] for _ in range(60)}
    assert 나온 == 세리아_평소  # 무작위로 셋 다 나온다(첫 대화 대사는 다시 안 나온다)
    assert 상태["진행도"]["대화한NPC"] == ["세리아"]


def test_평소_대사는_대화_흐름으로만_굴린다():
    """대화 대사 고르기가 전투·던전·보상 무작위를 밀지 않는다(rng.대화 따로)."""
    상태 = support.새게임()
    _로리엔_클리어(상태)
    gf.NPC_말걸기(상태, "세리아")
    다른흐름 = {
        이름: 흐름.getstate() for 이름, 흐름 in rng.흐름들.items() if 이름 != "대화"
    }
    for _ in range(5):
        gf.NPC_말걸기(상태, "세리아")
    assert {
        이름: 흐름.getstate() for 이름, 흐름 in rng.흐름들.items() if 이름 != "대화"
    } == 다른흐름


def test_첫_대화_기록은_NPC마다_따로이고_세이브에_남는다(임시_세이브폴더):
    상태 = support.새게임()
    _로리엔_클리어(상태)
    assert gf.NPC_말걸기(상태, "라이너스")["대사"] == "로리엔에서 세리아를 구출해주게."
    assert gf.NPC_말걸기(상태, "세리아")["대사"] == "구해주셔서 감사해요."
    assert 상태["진행도"]["대화한NPC"] == ["라이너스", "세리아"]
    gf.게임_저장(상태, 1)
    불러온 = gf.게임_불러오기(1)
    assert 불러온["진행도"]["대화한NPC"] == ["라이너스", "세리아"]
    assert gf.NPC_말걸기(불러온, "세리아")["대사"] in 세리아_평소


def test_대화할_수_없는_NPC에게는_말을_걸_수_없다():
    상태 = support.새게임()
    try:
        gf.NPC_말걸기(상태, "세리아")  # 로리엔 전
    except ValueError:
        assert 상태["진행도"]["대화한NPC"] == []
        return
    raise AssertionError("로리엔 전에 세리아와 대화가 됐다")


def test_라이너스는_첫_대화에_구출을_부탁하고_그_뒤로는_평소_대사_셋_중_하나다():
    상태 = support.새게임()
    assert gf.NPC_말걸기(상태, "라이너스")["대사"] == "로리엔에서 세리아를 구출해주게."
    나온 = {gf.NPC_말걸기(상태, "라이너스")["대사"] for _ in range(60)}
    assert 나온 == 라이너스_평소
