"""세이브·설정 시스템 단위 테스트 - 저장/불러오기, 슬롯 표시, 옛 버전 세이브 고치기, 던전 위치, 세이브 폴더, 설정 파일 읽기·쓰기.

test_systems_items.py(상점/장비/세이브/레벨업)에서 갈라져 나왔다."""

import json
import pytest
import gameflow as gf
from game.system import (
    player_system,
    save_system,
    settings_system,
)
from tests import support


# ------------------------------------------------------------------- save


def _핵심캐릭터(이름, **추가):
    """세이브 불러오기 검사(state_schema.캐릭터_핵심)를 통과하는 최소 캐릭터."""
    return {
        "캐릭터명": 이름,
        "직업": "귀검사",
        "레벨": 1,
        "현재HP": 10,
        "현재MP": 5,
        **dict.fromkeys(("근력", "민첩", "건강", "지능", "지혜", "매력"), 10),
        "장착장비": {},
        **추가,
    }


def test_세이브_구버전_형식과_요약(임시_세이브폴더):
    구버전 = {
        "파티": {"파티원": [_핵심캐릭터("철수")], "골드": 77},
        "진행도": {"현재마을": "엘븐가드", "클리어한오브젝트": [["d", [1, 2]]]},
    }
    (임시_세이브폴더 / "slot_2.json").write_text(
        json.dumps(구버전, ensure_ascii=False), encoding="utf-8"
    )
    플레이어, 진행도 = save_system.게임_불러오기(2)
    assert 플레이어["소지품"]["골드"] == 77 and 플레이어["선택된초상화"] == "001m"
    assert 진행도["클리어한던전"] == set() and 진행도["클리어한오브젝트"] == {
        ("d", (1, 2))
    }
    assert save_system.세이브_요약(2) == {
        "슬롯번호": 2,
        "저장시각": None,
        "현재마을": "엘븐가드",
        "대표캐릭터명": "철수",
        "파티인원수": 1,
    }
    요약 = save_system.전체_세이브_요약()
    assert [s.get("비어있음", False) for s in 요약] == [
        True,
        True,
        False,
        True,
    ]  # 0번은 자동 저장 칸
    with pytest.raises(FileNotFoundError):
        save_system.게임_불러오기(1)
    save_system.세이브_삭제(1)  # 없는 슬롯 삭제는 조용히 넘어간다
    assert save_system.세이브_요약(3) is None


def test_세이브_map_던전파일명은_dungeon으로_바꿔_불러온다(임시_세이브폴더):
    구버전 = {
        "플레이어": player_system.빈_플레이어(),
        "진행도": {
            "클리어한던전": ["map_01A_D01_Lorien"],
            "클리어한오브젝트": [["map_01A_D02_Hollow_Lorien", [15, 3]]],
        },
    }
    (임시_세이브폴더 / "slot_1.json").write_text(
        json.dumps(구버전, ensure_ascii=False), encoding="utf-8"
    )
    _, 진행도 = save_system.게임_불러오기(1)
    assert 진행도["클리어한던전"] == {"dungeon_01A_D01_Lorien"}
    assert 진행도["클리어한오브젝트"] == {("dungeon_01A_D02_Hollow_Lorien", (15, 3))}


def test_세이브_신버전_기본값_채움(임시_세이브폴더):
    (임시_세이브폴더 / "slot_1.json").write_text(
        json.dumps(
            {"플레이어": {"파티": {"파티원": []}}, "진행도": {"클리어한던전": ["a"]}}
        ),
        encoding="utf-8",
    )
    플레이어, 진행도 = save_system.게임_불러오기(1)
    assert 플레이어["레벨"] == 1 and 플레이어["선택된초상화"] == "001m"
    assert 플레이어["소지품"] == player_system.빈_소지품()
    assert 진행도["클리어한던전"] == {"a"}
    assert save_system.세이브_요약(1)["대표캐릭터명"] == "-"


def test_세이브_폴더는_game_saves(monkeypatch):
    monkeypatch.undo()  # 자동 픽스처의 바꿔치기를 풀고 실제 경로 계산만 확인
    assert save_system._세이브_폴더().replace("\\", "/").endswith("game/saves")


# 세이브 안정화(N1a) - 원자적 쓰기, 백업(.bak), 손상 슬롯. 구조 점검 W-1.


def _저장(슬롯번호, 마을="엘븐가드", 이름="철수"):
    플레이어 = player_system.빈_플레이어()
    플레이어["파티"]["파티원"] = [_핵심캐릭터(이름)]
    save_system.게임_저장(슬롯번호, 플레이어, {"현재마을": 마을, "플레이어레벨": 1})


def test_세이브_원자적_쓰기는_임시파일을_남기지_않고_이전_세이브를_백업한다(
    임시_세이브폴더,
):
    _저장(1, 마을="엘븐가드")
    assert not (
        임시_세이브폴더 / "slot_1.json.bak"
    ).exists()  # 처음엔 백업할 이전 세이브가 없다
    첫내용 = (임시_세이브폴더 / "slot_1.json").read_text(encoding="utf-8")

    _저장(1, 마을="헨돈마이어")
    assert sorted(p.name for p in 임시_세이브폴더.iterdir()) == [
        "slot_1.json",
        "slot_1.json.bak",
    ]  # .tmp 같은 찌꺼기가 없다
    assert (임시_세이브폴더 / "slot_1.json.bak").read_text(encoding="utf-8") == 첫내용
    assert save_system.세이브_요약(1)["현재마을"] == "헨돈마이어"


def test_세이브_저장이_중간에_실패하면_이전_세이브가_그대로다(
    임시_세이브폴더, monkeypatch
):
    _저장(1, 마을="엘븐가드")
    이전 = (임시_세이브폴더 / "slot_1.json").read_text(encoding="utf-8")

    def 실패(*args, **kwargs):
        raise OSError("디스크가 가득 찼다")

    # 임시 파일에 쓴 뒤 바꿔치기 직전(fsync)에 실패하는 경우
    with monkeypatch.context() as m:
        m.setattr(save_system.os, "fsync", 실패)
        with pytest.raises(OSError):
            _저장(1, 마을="헨돈마이어")
    assert (임시_세이브폴더 / "slot_1.json").read_text(encoding="utf-8") == 이전
    assert [p.name for p in 임시_세이브폴더.iterdir()] == [
        "slot_1.json"
    ]  # 임시 파일 정리

    # 직렬화 단계에서 실패해도 본 파일은 그대로다(파일을 열기 전에 끝낸다)
    with monkeypatch.context() as m:
        m.setattr(save_system.json, "dumps", 실패)
        with pytest.raises(OSError):
            _저장(1, 마을="헨돈마이어")
    assert (임시_세이브폴더 / "slot_1.json").read_text(encoding="utf-8") == 이전


def test_세이브_본파일이_잘리면_백업으로_불러오고_요약에_복구본이_뜬다(임시_세이브폴더):
    _저장(2, 마을="엘븐가드", 이름="철수")
    _저장(2, 마을="헨돈마이어", 이름="영희")  # .bak = 앞의 세이브
    잘린 = (임시_세이브폴더 / "slot_2.json").read_text(encoding="utf-8")[:30]
    (임시_세이브폴더 / "slot_2.json").write_text(
        잘린, encoding="utf-8"
    )  # 쓰다 끊긴 파일

    플레이어, 진행도 = save_system.게임_불러오기(2)
    assert 플레이어["파티"]["파티원"][0]["캐릭터명"] == "철수"
    assert 진행도["현재마을"] == "엘븐가드"
    assert save_system.세이브_요약(2)["복구본"] is True
    assert save_system.세이브_요약(2)["대표캐릭터명"] == "철수"


def test_세이브_본파일도_백업도_못_읽으면_손상오류_요약은_예외없이_손상(
    임시_세이브폴더,
):
    _저장(1, 이름="온전")
    (임시_세이브폴더 / "slot_2.json").write_text(
        '{"플레이어": {"파티": {"파', encoding="utf-8"
    )

    with pytest.raises(save_system.세이브_손상오류) as 오류:
        save_system.게임_불러오기(2)
    assert 오류.value.슬롯번호 == 2 and "손상" in str(오류.value)
    assert save_system.세이브_요약(2) == {"슬롯번호": 2, "손상": True}

    # 슬롯 하나가 망가져도 목록은 만들어지고 다른 슬롯은 그대로다(메인 메뉴가 막히지 않는다)
    요약 = save_system.전체_세이브_요약()
    assert 요약[1]["대표캐릭터명"] == "온전"
    assert 요약[2] == {"슬롯번호": 2, "손상": True}
    assert 요약[3] == {"슬롯번호": 3, "비어있음": True}

    # 형태가 틀린 JSON(리스트, 진행도 없음)도 손상으로 본다
    (임시_세이브폴더 / "slot_3.json").write_text("[1, 2]", encoding="utf-8")
    assert save_system.세이브_요약(3) == {"슬롯번호": 3, "손상": True}
    (임시_세이브폴더 / "slot_3.json").write_text('{"플레이어": {}}', encoding="utf-8")
    assert save_system.세이브_요약(3) == {"슬롯번호": 3, "손상": True}


def test_세이브_망가진_본파일을_덮어써도_좋은_백업은_지켜진다(임시_세이브폴더):
    _저장(1, 이름="첫째")
    _저장(1, 이름="둘째")  # .bak = 첫째
    (임시_세이브폴더 / "slot_1.json").write_text("{끊김", encoding="utf-8")
    _저장(1, 이름="셋째")  # 망가진 본 파일은 백업하지 않는다
    assert (임시_세이브폴더 / "slot_1.json.bak").read_text(encoding="utf-8").count(
        "첫째"
    ) == 1
    assert save_system.게임_불러오기(1)[0]["파티"]["파티원"][0]["캐릭터명"] == "셋째"


def test_세이브_삭제는_백업과_임시파일도_지운다(임시_세이브폴더):
    _저장(1)
    _저장(1)
    (임시_세이브폴더 / "slot_1.json.tmp").write_text("x", encoding="utf-8")
    save_system.세이브_삭제(1)
    assert list(임시_세이브폴더.iterdir()) == []
    assert save_system.세이브_요약(1) is None


def test_gameflow는_손상오류를_그대로_올린다(임시_세이브폴더):
    (임시_세이브폴더 / "slot_1.json").write_text("{", encoding="utf-8")
    assert gf.세이브_손상오류 is save_system.세이브_손상오류
    with pytest.raises(gf.세이브_손상오류):
        gf.게임_불러오기(1)
    assert gf.전체_세이브_요약()[1] == {"슬롯번호": 1, "손상": True}


def _첫_파티원_고치기(폴더, 고치기, 접미=""):
    경로 = 폴더 / f"slot_1.json{접미}"
    데이터 = json.loads(경로.read_text(encoding="utf-8"))
    고치기(데이터["플레이어"]["파티"]["파티원"][0])
    경로.write_text(json.dumps(데이터, ensure_ascii=False), encoding="utf-8")


@pytest.mark.parametrize(
    "고치기",
    [
        lambda c: c.__setitem__("직업", "데이터에_없는_직업"),  # KeyError
        lambda c: c.__setitem__("보유특성", 3),  # TypeError
        lambda c: c.__setitem__("장착장비", {"무기": 1.5}),  # TypeError(강화 이름 해석)
    ],
)
def test_읽혔지만_게임상태로_못_만드는_세이브는_백업으로_불러온다(
    임시_세이브폴더, 고치기
):
    """파일 검사는 통과하지만 컨트롤러가 다시 계산하다 죽는 세이브(#845) - 예외 대신 백업으로,
    백업도 그렇게 망가졌으면 세이브_손상오류. 슬롯 목록에도 복구본/손상으로 보인다."""
    상태 = support.새게임()
    gf.게임_저장(상태, 1)
    상태["소지품"]["골드"] = 77
    gf.게임_저장(상태, 1)  # .bak = 골드 0인 앞 세이브
    _첫_파티원_고치기(임시_세이브폴더, 고치기)

    assert gf.게임_불러오기(1)["소지품"]["골드"] == 0  # 백업
    assert gf.전체_세이브_요약()[1]["복구본"] is True

    _첫_파티원_고치기(임시_세이브폴더, 고치기, ".bak")
    with pytest.raises(gf.세이브_손상오류):
        gf.게임_불러오기(1)
    assert gf.전체_세이브_요약()[1] == {"슬롯번호": 1, "손상": True}


def test_백업_없이_게임상태로_못_만드는_세이브는_손상오류(임시_세이브폴더):
    gf.게임_저장(support.새게임(), 1)  # 첫 저장이라 .bak이 없다
    _첫_파티원_고치기(임시_세이브폴더, lambda c: c.__setitem__("보유특성", 3))
    with pytest.raises(gf.세이브_손상오류):
        gf.게임_불러오기(1)
    with pytest.raises(FileNotFoundError):  # 빈 슬롯은 그대로 FileNotFoundError
        gf.게임_불러오기(2)
    요약 = gf.전체_세이브_요약()
    assert 요약[1] == {"슬롯번호": 1, "손상": True}
    assert 요약[2] == {"슬롯번호": 2, "비어있음": True}


# 세이브 버전과 마이그레이션(N1b)


def test_세이브에는_버전이_들어_있다(임시_세이브폴더):
    _저장(1)
    저장 = json.loads((임시_세이브폴더 / "slot_1.json").read_text(encoding="utf-8"))
    assert 저장["버전"] == save_system.세이브_버전 == 22


def test_버전_없는_세이브는_0으로_보고_현재_형태로_변환한다(임시_세이브폴더):
    옛 = {
        "파티": {
            "파티원": [
                _핵심캐릭터("철수", 보유특성=["웨펀마스터", "엘레멘탈 번", "공용"])
            ],
            "골드": 40,
        },
        "진행도": {
            "클리어한던전": ["map_01A_D01_Lorien"],
            "클리어한오브젝트": [["map_01A_D01_Lorien", [3, 4]]],
        },
    }
    (임시_세이브폴더 / "slot_1.json").write_text(
        json.dumps(옛, ensure_ascii=False), encoding="utf-8"
    )
    플레이어, 진행도 = save_system.게임_불러오기(1)
    철수 = 플레이어["파티"]["파티원"][0]
    assert 철수["보유특성"] == [
        "무기의 극의",
        "공용",
    ]  # 바뀐 이름은 바꾸고 없어진 특성은 뺀다
    assert (철수["성별"], 철수["전직"], 철수["치명타주사위"]) == ("m", None, 1)
    assert 철수["횟수제한스킬"] == {"휴식제한스킬": {}}
    assert 플레이어["소지품"]["골드"] == 40 and 플레이어["숙소"] == []
    assert 진행도["플레이어레벨"] == 플레이어["레벨"] == 1
    assert 진행도["클리어한던전"] == {"dungeon_01A_D01_Lorien"}
    assert 진행도["클리어한오브젝트"] == {("dungeon_01A_D01_Lorien", (3, 4))}


def test_버전4_세이브의_반응특성은_반응스킬로_옮긴다(임시_세이브폴더):
    """반응특성 분류가 없어지고 반응스킬이 됐다 - 보유특성에서 보유스킬로."""
    _저장(1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    옛 = json.loads(경로.read_text(encoding="utf-8"))
    옛["버전"] = 4
    옛["플레이어"]["파티"]["파티원"] = [
        _핵심캐릭터(
            "철수",
            보유특성=["군인", "건가드", "리벤저"],
            보유스킬=["리벤저", "헤드샷"],
        )
    ]
    옛["플레이어"]["숙소"] = [_핵심캐릭터("영희", 보유특성=["위상 변화"], 보유스킬=[])]
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    플레이어, _ = save_system.게임_불러오기(1)
    철수 = 플레이어["파티"]["파티원"][0]
    assert 철수["보유특성"] == ["군인"]
    assert 철수["보유스킬"] == ["리벤저", "헤드샷", "건가드"]  # 이미 있으면 한 번만
    영희 = 플레이어["숙소"][0]
    assert (영희["보유특성"], 영희["보유스킬"]) == ([], ["위상 변화"])


def test_버전5_세이브의_파티에는_인형이_없다(임시_세이브폴더):
    """인형사 도입 - 그전 세이브는 파티["인형"] = None으로 불러온다."""
    _저장(1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    옛 = json.loads(경로.read_text(encoding="utf-8"))
    옛["버전"] = 5
    옛["플레이어"]["파티"].pop("인형", None)
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    플레이어, _ = save_system.게임_불러오기(1)
    assert 플레이어["파티"]["인형"] is None


def test_버전6_세이브의_던전위치에는_봉절이_없다(임시_세이브폴더):
    """봉절 도입 - 그전에 던전 안에서 저장한 세이브는 봉절 걸음 0으로 불러온다."""
    상태 = support.새게임()
    gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
    gf.게임_저장(상태, 1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    옛 = json.loads(경로.read_text(encoding="utf-8"))
    옛["버전"] = 6
    옛["던전위치"].pop("봉절걸음")
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    플레이어, _ = save_system.게임_불러오기(1)
    assert 플레이어["던전위치"]["봉절걸음"] == 0
    assert gf.게임_불러오기(1)["던전상태"]["봉절걸음"] == 0


def _머크우드_보스를_이기고_그_칸에_선다(상태):
    """머크우드의 타우 비스트(15, 3 - 통행가능화)를 이기고 열린 칸으로 들어간다."""
    gf.던전_진입(상태, "dungeon_01A_D03_mirkwood")
    상태["던전상태"]["위치"] = (14, 3)
    결과 = gf.던전_이동(상태, "오른쪽")
    gf.오브젝트_상호작용(상태, 결과["위치"], 결과["오브젝트"])
    support.반응_처리(상태)
    support.강제_승리(상태)
    gf.전투_결과_정리(상태)
    while gf.전투_보상_대기중(상태):
        gf.전투_보상_포기(상태)
    상태["전투상태"] = None
    assert gf.던전_이동(상태, "오른쪽")["결과"] == "이동"
    assert 상태["던전상태"]["위치"] == (15, 3)


def test_던전_안_저장은_이번_방문에_열린_칸을_되살린다(임시_세이브폴더):
    """이번 방문에서 이겨 열린 보스 칸(통행가능화)은 던전 안에서 저장하고 불러와도 열려 있다."""
    상태 = support.새게임([("", "귀검사")])
    _머크우드_보스를_이기고_그_칸에_선다(상태)
    gf.게임_저장(상태, 1)

    불러옴 = gf.게임_불러오기(1)
    assert 불러옴["던전상태"]["위치"] == (15, 3)
    assert 불러옴["던전상태"]["그리드"][3][15] == "O"
    assert gf.던전_이동(불러옴, "왼쪽")["결과"] == "이동"
    assert gf.던전_이동(불러옴, "오른쪽")["결과"] == "이동"

    # 던전을 나갔다 다시 들어오면 그대로 다시 막힌다(통행가능화는 이번 방문만)
    gf.던전_진입(불러옴, "dungeon_01A_D03_mirkwood")
    assert 불러옴["던전상태"]["그리드"][3][15] == "@"


def test_열린칸은_원래_오브젝트_칸만_되살린다(임시_세이브폴더):
    """세이브의 "열린칸"이 지도에서 "@"가 아닌 칸(벽 등)을 가리키거나 모양이 틀리면 무시한다."""
    상태 = support.새게임([("", "귀검사")])
    gf.던전_진입(상태, "dungeon_01A_D03_mirkwood")
    gf.게임_저장(상태, 1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    데이터 = json.loads(경로.read_text(encoding="utf-8"))
    데이터["던전위치"]["열린칸"] = [[0, 0, "O"], [15, 3, "X"], [99, 99, "O"], "망가짐"]
    경로.write_text(json.dumps(데이터, ensure_ascii=False), encoding="utf-8")
    그리드 = gf.게임_불러오기(1)["던전상태"]["그리드"]
    assert 그리드[0][0] == "X" and 그리드[3][15] == "@"


def test_버전19_세이브의_던전위치에는_열린칸이_없다(임시_세이브폴더):
    """열린 칸 저장 도입(세이브 버전 20) - 그전에 던전 안에서 저장한 세이브는 열린 칸 없음으로 불러온다."""
    상태 = support.새게임([("", "귀검사")])
    _머크우드_보스를_이기고_그_칸에_선다(상태)
    gf.게임_저장(상태, 1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    옛 = json.loads(경로.read_text(encoding="utf-8"))
    옛["버전"] = 19
    옛["던전위치"].pop("열린칸")
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    플레이어, _ = save_system.게임_불러오기(1)
    assert 플레이어["던전위치"]["열린칸"] == []
    assert gf.게임_불러오기(1)["던전상태"]["그리드"][3][15] == "@"


def test_버전7_세이브의_버서커가_아닌_캐릭터는_블러드_러스트를_잃는다(임시_세이브폴더):
    """블러드 러스트가 귀검사 비전직 스킬에서 버서커 골드 스킬로 옮겨 갔다."""
    _저장(1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    옛 = json.loads(경로.read_text(encoding="utf-8"))
    옛["버전"] = 7
    옛["플레이어"]["파티"]["파티원"] = [
        _핵심캐릭터("철수", 보유스킬=["귀참", "블러드 러스트"]),
        _핵심캐릭터("영희", 전직="버서커", 보유스킬=["블러드 러스트", "귀참"]),
    ]
    옛["플레이어"]["숙소"] = [
        _핵심캐릭터("민수", 전직="웨펀마스터", 보유스킬=["블러드 러스트"])
    ]
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    플레이어, _ = save_system.게임_불러오기(1)
    철수, 영희 = 플레이어["파티"]["파티원"]
    assert 철수["보유스킬"] == ["귀참"]
    assert 영희["보유스킬"] == ["블러드 러스트", "귀참"]  # 버서커는 그대로
    assert 플레이어["숙소"][0]["보유스킬"] == []


def test_버전8_세이브의_무기_숙련은_마스터리로_이름이_바뀐다(임시_세이브폴더):
    """무기 숙련 "OO숙련" -> "OO 마스터리". 방어구 숙련은 그대로다."""
    _저장(1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    옛 = json.loads(경로.read_text(encoding="utf-8"))
    옛["버전"] = 8
    옛["플레이어"]["파티"]["파티원"] = [
        _핵심캐릭터(
            "철수",
            보유특성=["도숙련", "천갑숙련", "군인"],
            보유퍽=["소검숙련", "가죽숙련"],
        )
    ]
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    플레이어, _ = save_system.게임_불러오기(1)
    철수 = 플레이어["파티"]["파티원"][0]
    assert 철수["보유특성"] == ["도 마스터리", "천갑숙련", "군인"]
    assert 철수["보유퍽"] == ["소검 마스터리", "가죽숙련"]


def test_버전9_세이브의_파동검_지열은_웨이브로_이름이_바뀐다(임시_세이브폴더):
    """귀검사 "파동검 지열" -> "웨이브" - 보유스킬과 스킬강화."""
    _저장(1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    옛 = json.loads(경로.read_text(encoding="utf-8"))
    옛["버전"] = 9
    옛["플레이어"]["파티"]["파티원"] = [
        _핵심캐릭터(
            "철수",
            보유스킬=["귀참", "파동검 지열"],
            스킬강화={"스킬": "파동검 지열", "최종피해배율": 1.5, "MP소모배율": 2},
        ),
        _핵심캐릭터("영희", 보유스킬=["귀참"]),
    ]
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    플레이어, _ = save_system.게임_불러오기(1)
    철수, 영희 = 플레이어["파티"]["파티원"]
    assert 철수["보유스킬"] == ["귀참", "웨이브"]
    assert 철수["스킬강화"]["스킬"] == "웨이브"
    assert 영희["보유스킬"] == ["귀참"] and "스킬강화" not in 영희


def test_버전11_세이브의_귀신_라사는_귀신_사야로_이름이_바뀐다(임시_세이브폴더):
    """소울브링어 "귀신 : 라사"는 "귀신 : 사야"의 오타였다 - 보유스킬과 스킬강화."""
    _저장(1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    옛 = json.loads(경로.read_text(encoding="utf-8"))
    옛["버전"] = 11
    옛["플레이어"]["파티"]["파티원"] = [
        _핵심캐릭터(
            "철수",
            보유스킬=["귀참", "귀신 : 라사"],
            스킬강화={"스킬": "귀신 : 라사", "최종피해배율": 1.5, "MP소모배율": 2},
        ),
    ]
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    플레이어, _ = save_system.게임_불러오기(1)
    (철수,) = 플레이어["파티"]["파티원"]
    assert 철수["보유스킬"] == ["귀참", "귀신 : 사야"]
    assert 철수["스킬강화"]["스킬"] == "귀신 : 사야"


def test_버전21_세이브의_슈타이어_대전차포는_슈타이어_중저격총으로_이름이_바뀐다(
    임시_세이브폴더,
):
    """런처 골드 스킬 이름 변경(2026-11-20) - 보유스킬과 스킬강화."""
    _저장(1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    옛 = json.loads(경로.read_text(encoding="utf-8"))
    옛["버전"] = 21
    옛["플레이어"]["파티"]["파티원"] = [
        _핵심캐릭터(
            "철수",
            보유스킬=["미라클 비전", "슈타이어 대전차포"],
            스킬강화={
                "스킬": "슈타이어 대전차포",
                "최종피해배율": 1.5,
                "MP소모배율": 2,
            },
        ),
    ]
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    플레이어, _ = save_system.게임_불러오기(1)
    (철수,) = 플레이어["파티"]["파티원"]
    assert 철수["보유스킬"] == ["미라클 비전", "슈타이어 중저격총"]
    assert 철수["스킬강화"]["스킬"] == "슈타이어 중저격총"


def test_버전12_세이브의_수플렉스썬더와_귀참드라이브는_연계스킬로_옮겨진다(
    임시_세이브폴더,
):
    """특성 "수플렉스 썬더"(넨마스터 골드 스킬, 훔쳐배우기 포함)는 보유스킬로 옮기고, 특성 "사슬 해제"가
    있는 소울브링어는 귀참드라이브 스킬을 얻는다(둘 다 연계스킬)."""
    _저장(1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    옛 = json.loads(경로.read_text(encoding="utf-8"))
    옛["버전"] = 12
    옛["플레이어"]["파티"]["파티원"] = [
        _핵심캐릭터("넨", 보유특성=["빛의 친화", "수플렉스 썬더"], 보유스킬=["넨탄"]),
        _핵심캐릭터("소울", 보유특성=["사슬 해제"], 보유스킬=["귀참"]),
        _핵심캐릭터("귀검", 보유특성=["어둠의 친화"], 보유스킬=["귀참"]),
    ]
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    플레이어, _ = save_system.게임_불러오기(1)
    넨, 소울, 귀검 = 플레이어["파티"]["파티원"]
    assert 넨["보유특성"] == ["빛의 친화"]
    assert 넨["보유스킬"] == ["넨탄", "수플렉스 썬더"]
    assert 소울["보유특성"] == ["사슬 해제"]
    assert 소울["보유스킬"] == ["귀참", "귀참드라이브"]
    assert 귀검["보유스킬"] == ["귀참"]


def test_버전13_세이브의_메모라이즈는_지능1과_이동캐스팅을_얻는다(임시_세이브폴더):
    """메모라이즈가 지능 +1(얻을 때 캐릭터에 더하는 효과)로 바뀌고 레벨 6에 이동캐스팅이 더해졌다
    이미 메모라이즈를 가진 엘리멘탈마스터에게 둘을 준다."""
    _저장(1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    옛 = json.loads(경로.read_text(encoding="utf-8"))
    옛["버전"] = 13
    옛["플레이어"]["파티"]["파티원"] = [
        _핵심캐릭터("엘마", 지능=14, 보유특성=["마법재능", "메모라이즈"]),
        _핵심캐릭터("마법", 지능=14, 보유특성=["마법재능"]),
    ]
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    플레이어, _ = save_system.게임_불러오기(1)
    엘마, 마법 = 플레이어["파티"]["파티원"]
    assert 엘마["지능"] == 15
    assert 엘마["보유특성"] == ["마법재능", "메모라이즈", "이동캐스팅"]
    assert 마법["지능"] == 14
    assert 마법["보유특성"] == ["마법재능"]


def test_버전14_세이브의_낭익천_남익천은_야빠빠_야빠빠_하나로_합쳐진다(임시_세이브폴더):
    """특성 낭익천·남익천이 특성 "야빠빠 야빠빠"의 두 형태가 됐다."""
    _저장(1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    옛 = json.loads(경로.read_text(encoding="utf-8"))
    옛["버전"] = 14
    옛["플레이어"]["파티"]["파티원"] = [
        _핵심캐릭터("란마", 보유특성=["군인", "낭익천", "남익천"], 보유퍽=["란마 1/2"]),
        _핵심캐릭터("철수", 보유특성=["군인"]),
    ]
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    플레이어, _ = save_system.게임_불러오기(1)
    란마, 철수 = 플레이어["파티"]["파티원"]
    assert 란마["보유특성"] == ["군인", "야빠빠 야빠빠"]
    assert 란마["보유퍽"] == ["란마 1/2"]
    assert 철수["보유특성"] == ["군인"]


def test_인형은_세이브_왕복에서_그대로_남는다(임시_세이브폴더):
    상태 = support.새게임()
    상태["소지품"]["소모품"]["28호"] = 1
    gf.인형_사용(상태, "28호")
    상태["파티"]["인형"]["현재HP"] -= 1
    gf.게임_저장(상태, 1)
    불러옴 = gf.게임_불러오기(1)
    인형 = 불러옴["파티"]["인형"]
    assert (
        인형["캐릭터명"] == "28호" and 인형["현재HP"] == 상태["파티"]["인형"]["현재HP"]
    )


def test_현재_버전_세이브는_변환을_다시_거치지_않는다(임시_세이브폴더):
    _저장(1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    저장 = json.loads(경로.read_text(encoding="utf-8"))
    저장["플레이어"]["파티"]["파티원"][0].pop("성별", None)
    경로.write_text(json.dumps(저장, ensure_ascii=False), encoding="utf-8")
    # 버전 1이면 "성별이 없다"는 형식 오류가 아니라 그냥 값이다 - 변환이 덮어쓰지 않는다
    assert "성별" not in save_system.게임_불러오기(1)[0]["파티"]["파티원"][0]


def test_마이그레이션은_저장된_버전보다_높은_것만_순서대로_적용한다(
    임시_세이브폴더, monkeypatch
):
    순서 = []
    다음 = save_system.세이브_버전 + 1  # 지금 버전 다음 두 개를 가짜로 더한다

    def 변환1(데이터):
        순서.append(다음)
        데이터["플레이어"]["표시"] = 데이터["플레이어"].get("표시", "") + "1"

    def 변환2(데이터):
        순서.append(다음 + 1)
        데이터["플레이어"]["표시"] += "2"

    _저장(1)  # 지금 버전으로 저장
    monkeypatch.setattr(save_system, "세이브_버전", 다음 + 1)
    monkeypatch.setattr(
        save_system,
        "_마이그레이션",
        save_system._마이그레이션 + [(다음, 변환1), (다음 + 1, 변환2)],
    )
    플레이어, _ = save_system.게임_불러오기(1)
    assert 순서 == [다음, 다음 + 1] and 플레이어["표시"] == "12"
    # 이미 새 버전으로 저장된 세이브는 건너뛴다
    _저장(2)
    순서.clear()
    save_system.게임_불러오기(2)
    assert 순서 == []


def test_더_새로운_버전_세이브는_막고_백업으로_돌아가지_않는다(임시_세이브폴더):
    _저장(1)
    _저장(1)  # .bak은 현재 버전
    경로 = 임시_세이브폴더 / "slot_1.json"
    저장 = json.loads(경로.read_text(encoding="utf-8"))
    저장["버전"] = save_system.세이브_버전 + 1
    경로.write_text(json.dumps(저장, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(save_system.세이브_버전오류) as 오류:
        save_system.게임_불러오기(1)
    assert 오류.value.버전 == save_system.세이브_버전 + 1 and "새로운 버전" in str(
        오류.value
    )
    assert isinstance(
        오류.value, save_system.세이브_손상오류
    )  # 화면은 하나만 잡아도 된다
    assert save_system.세이브_요약(1) == {"슬롯번호": 1, "손상": True, "새버전": True}


def test_세이브_버전이나_구조가_이상하면_손상으로_본다(임시_세이브폴더):
    경로 = 임시_세이브폴더 / "slot_1.json"
    for 내용 in (
        {"버전": "1", "진행도": {}},  # 버전이 정수가 아님
        {"버전": -1, "진행도": {}},
        {"버전": True, "진행도": {}},
        {"플레이어": [], "진행도": {}},  # 변환하다 실패하는 구조
        {"플레이어": {"파티": {"파티원": [1]}}, "진행도": {}},
    ):
        경로.write_text(json.dumps(내용), encoding="utf-8")
        assert save_system.세이브_요약(1) == {"슬롯번호": 1, "손상": True}, 내용
        with pytest.raises(save_system.세이브_손상오류):
            save_system.게임_불러오기(1)

    # 본 파일의 구조만 이상하면 백업으로 돌아간다
    _저장(1, 이름="온전")
    _저장(1, 이름="새것")
    경로.write_text(json.dumps({"플레이어": [], "진행도": {}}), encoding="utf-8")
    assert save_system.게임_불러오기(1)[0]["파티"]["파티원"][0]["캐릭터명"] == "온전"


# 세이브 폴더를 앱 데이터 폴더로 옮기기(N1c) - 옛 위치(game/saves)의 세이브는 한 번만 복사한다.

_원래_세이브_폴더 = (
    save_system._세이브_폴더
)  # conftest의 자동 픽스처가 바꿔치기하기 전 함수


@pytest.fixture
def 폴더_설정(tmp_path, monkeypatch):
    """옛 폴더(= 기본 위치)와 새 폴더를 tmp에 두고 실제 폴더 계산 함수를 되살린다."""
    옛 = tmp_path / "옛"
    옛.mkdir()
    새 = tmp_path / "새" / "saves"  # 아직 없는 폴더 - 설정이 만든다
    monkeypatch.setattr(save_system, "_세이브_폴더", _원래_세이브_폴더)
    monkeypatch.setattr(save_system, "_기본_세이브_폴더", lambda: str(옛))
    monkeypatch.setattr(save_system, "_폴더_재정의", None)
    return 옛, 새


def test_세이브_폴더_설정은_옛_세이브를_한번_복사하고_옛_파일은_남긴다(폴더_설정):
    옛, 새 = 폴더_설정
    (옛 / "slot_1.json").write_text("{옛1}", encoding="utf-8")
    (옛 / "slot_1.json.bak").write_text("{옛1백업}", encoding="utf-8")
    (옛 / "slot_3.json").write_text("{옛3}", encoding="utf-8")
    (옛 / "slot_9.json").write_text("{범위 밖}", encoding="utf-8")

    복사 = save_system.세이브_폴더_설정(str(새))
    assert 복사 == ["slot_1.json", "slot_1.json.bak", "slot_3.json"]
    assert save_system._세이브_폴더() == str(새)
    assert (새 / "slot_1.json").read_text(encoding="utf-8") == "{옛1}"
    assert (새 / "slot_1.json.bak").read_text(encoding="utf-8") == "{옛1백업}"
    assert not (새 / "slot_9.json").exists()
    assert (옛 / "slot_1.json").exists() and (
        옛 / "slot_3.json"
    ).exists()  # 옛 파일은 지우지 않는다
    assert not list(새.glob("*.tmp"))


def test_세이브_폴더_설정_후_저장은_새_폴더에_된다(폴더_설정):
    옛, 새 = 폴더_설정
    save_system.세이브_폴더_설정(str(새))
    _저장(1)
    assert (새 / "slot_1.json").exists() and not (옛 / "slot_1.json").exists()
    assert save_system.세이브_요약(1)["대표캐릭터명"] == "철수"


def test_옛_세이브는_두번_가져오지_않아_지운_슬롯이_되살아나지_않는다(폴더_설정):
    옛, 새 = 폴더_설정
    (옛 / "slot_1.json").write_text("{옛}", encoding="utf-8")
    save_system.세이브_폴더_설정(str(새))
    save_system.세이브_삭제(1)  # 사용자가 슬롯을 지웠다
    assert save_system.세이브_폴더_설정(str(새)) == []  # 다음 실행
    assert not (새 / "slot_1.json").exists()


def test_새_폴더에_이미_있는_슬롯은_덮어쓰지_않는다(폴더_설정):
    옛, 새 = 폴더_설정
    새.mkdir(parents=True)
    (새 / "slot_1.json").write_text("{새}", encoding="utf-8")
    (옛 / "slot_1.json").write_text("{옛}", encoding="utf-8")
    (옛 / "slot_2.json").write_text("{옛2}", encoding="utf-8")
    assert save_system.세이브_폴더_설정(str(새)) == ["slot_2.json"]
    assert (새 / "slot_1.json").read_text(encoding="utf-8") == "{새}"


def test_옛_폴더가_없거나_같은_폴더면_복사하지_않고_표시만_남긴다(
    폴더_설정, tmp_path, monkeypatch
):
    옛, 새 = 폴더_설정
    monkeypatch.setattr(
        save_system, "_기본_세이브_폴더", lambda: str(tmp_path / "없음")
    )
    assert save_system.세이브_폴더_설정(str(새)) == []
    assert (새 / save_system._가져옴_표시파일).exists()

    같은 = tmp_path / "같은"
    같은.mkdir()
    (같은 / "slot_1.json").write_text("{x}", encoding="utf-8")
    monkeypatch.setattr(save_system, "_기본_세이브_폴더", lambda: str(같은))
    assert save_system.세이브_폴더_설정(str(같은)) == []


def test_복사에_실패해도_앱은_계속되고_다음_실행에_다시_시도한다(
    폴더_설정, monkeypatch
):
    옛, 새 = 폴더_설정
    (옛 / "slot_1.json").write_text("{옛}", encoding="utf-8")

    def 실패(*args, **kwargs):
        raise OSError("읽기 실패")

    with monkeypatch.context() as m:
        m.setattr(save_system.shutil, "copy2", 실패)
        assert save_system.세이브_폴더_설정(str(새)) == []
    assert not (새 / save_system._가져옴_표시파일).exists()  # 표시가 없어 다시 시도한다
    assert save_system.세이브_폴더_설정(str(새)) == ["slot_1.json"]
    assert (새 / save_system._가져옴_표시파일).exists()


def test_gameflow는_세이브_폴더_설정을_내보낸다(폴더_설정):
    옛, 새 = 폴더_설정
    assert gf.세이브_폴더_설정(str(새)) == []
    assert save_system._세이브_폴더() == str(새)


def test_세이브_던전위치를_저장하고_옛_세이브는_던전위치_없음(임시_세이브폴더):
    플레이어 = player_system.빈_플레이어()
    진행도 = {
        "현재마을": "엘븐가드",
        "클리어한던전": set(),
        "클리어한오브젝트": set(),
        "플레이어레벨": 1,
    }
    위치 = {"던전파일명": "dungeon_01A_D01_Lorien", "위치": [3, 4], "걸음수": 7}
    save_system.게임_저장(1, 플레이어, 진행도, 던전위치=위치)
    읽은플레이어, _ = save_system.게임_불러오기(1)
    assert 읽은플레이어["던전위치"] == 위치
    assert save_system.세이브_요약(1)["던전파일명"] == "dungeon_01A_D01_Lorien"
    save_system.게임_저장(2, 플레이어, 진행도)  # 마을에서 저장
    assert save_system.게임_불러오기(2)[0]["던전위치"] is None
    assert "던전파일명" not in save_system.세이브_요약(2)
    # 버전 1 세이브(던전위치 칸이 없던 때)는 던전위치 없음으로 읽는다
    _저장(3)
    경로 = 임시_세이브폴더 / "slot_3.json"
    옛 = json.loads(경로.read_text(encoding="utf-8"))
    옛["버전"] = 1
    del 옛["던전위치"]
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    assert save_system.게임_불러오기(3)[0]["던전위치"] is None
    assert save_system.세이브_버전 >= 2  # 던전위치는 버전 2에서 생겼다


def test_버전3_세이브의_도감은_바뀐_몬스터_이름으로_읽는다(임시_세이브폴더):
    """ "타우 어썰터" -> "타우 어설터". 둘 다 있으면 하나만 남긴다."""
    _저장(1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    옛 = json.loads(경로.read_text(encoding="utf-8"))
    옛["버전"] = 3
    옛["진행도"]["도감"] = {"몬스터": ["타우 아미", "타우 어썰터", "고블린"]}
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    assert save_system.게임_불러오기(1)[1]["도감"]["몬스터"] == [
        "타우 아미",
        "타우 어설터",
        "고블린",
    ]
    옛["진행도"]["도감"] = {"몬스터": ["타우 어설터", "타우 어썰터"]}
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    assert save_system.게임_불러오기(1)[1]["도감"]["몬스터"] == ["타우 어설터"]


# 기기 설정 파일(설정.json) - 세이브와 별개인 앱 설정. 경로는 화면이 넘긴다(품질 계획 P8).


@pytest.mark.parametrize(
    "내용",
    [None, '{"반응자'.encode(), b"[1, 2]", b"\xff"],
    ids=["없음", "끊긴JSON", "딕셔너리아님", "깨진글자"],
)
def test_설정_읽기는_없거나_깨졌거나_딕셔너리가_아니면_빈_설정(tmp_path, 내용):
    경로 = tmp_path / "설정.json"
    if 내용 is not None:
        경로.write_bytes(내용)
    assert settings_system.설정_읽기(str(경로)) == {}


def test_설정_쓰기는_읽기와_왕복하고_한글을_그대로_쓴다(tmp_path):
    경로 = str(tmp_path / "설정.json")
    설정 = {"반응자동": True, "자동전투방식": "전력전투"}
    assert settings_system.설정_쓰기(경로, 설정) is True
    assert settings_system.설정_읽기(경로) == 설정
    assert "전력전투" in open(경로, encoding="utf-8").read()


def test_설정_쓰기는_쓸_수_없으면_False(tmp_path):
    assert settings_system.설정_쓰기(str(tmp_path), {"반응자동": True}) is False


def test_설정_쓰기는_도중에_실패해도_옛_파일을_지키고_임시_파일을_남기지_않는다(
    tmp_path, monkeypatch
):
    경로 = tmp_path / "설정.json"
    settings_system.설정_쓰기(str(경로), {"반응자동": True})

    def 쓰다_끊김(설정, 파일, **_):
        파일.write('{"반')
        raise OSError("디스크 가득")

    monkeypatch.setattr(settings_system.json, "dump", 쓰다_끊김)
    assert settings_system.설정_쓰기(str(경로), {"반응자동": False}) is False
    assert settings_system.설정_읽기(str(경로)) == {"반응자동": True}
    assert sorted(p.name for p in tmp_path.iterdir()) == ["설정.json"]


def test_버전20_세이브의_퍽_귀영보는_골드_스킬_귀영보와_귀영섬_켜진_특성이_된다(
    임시_세이브폴더,
):
    """퍽/반응스킬 귀영보가 없어지고 골드 스킬(켜고 끄는 특성 + 귀영섬)이 됐다."""
    _저장(1)
    경로 = 임시_세이브폴더 / "slot_1.json"
    옛 = json.loads(경로.read_text(encoding="utf-8"))
    옛["버전"] = 20
    옛["플레이어"]["파티"]["파티원"] = [
        _핵심캐릭터(
            "철수", 전직="소울브링어", 보유스킬=["귀참", "귀영보"], 보유퍽=["귀영보"]
        ),
        _핵심캐릭터("영희", 전직="소울브링어", 보유스킬=["귀참"], 보유퍽=[]),
    ]
    경로.write_text(json.dumps(옛, ensure_ascii=False), encoding="utf-8")
    플레이어, _ = save_system.게임_불러오기(1)
    철수, 영희 = 플레이어["파티"]["파티원"]
    assert 철수["보유퍽"] == []
    assert 철수["보유스킬"] == ["귀참", "귀영보", "귀영섬"]
    assert "귀영보" in 철수["보유특성"] and 철수["켜진특성"] == ["귀영보"]
    assert 영희["보유스킬"] == ["귀참"] and "귀영보" not in (영희.get("보유특성") or [])


# ------------------------------------------------------------------ 데이터에 없는 장비 이름(#853)
# 장비 이름을 바꾸며 마이그레이션을 빠뜨린 옛 세이브 - 불러올 때 장착 칸만 비우고 소지품은 그대로 둔다.


def _없는_장비_세이브(임시_세이브폴더):
    상태 = support.새게임()
    c = 상태["파티"]["파티원"][0]
    c["장착장비"]["무기"] = "옛 이름 소검"
    상태["소지품"].setdefault("장비", {})["옛 이름 상의"] = 1
    gf.게임_저장(상태, 1)
    return gf.게임_불러오기(1)


def test_데이터에_없는_장착_장비는_불러올_때_칸을_비운다(임시_세이브폴더):
    상태 = _없는_장비_세이브(임시_세이브폴더)
    c = 상태["파티"]["파티원"][0]
    assert c["장착장비"]["무기"] is None
    assert c["장착장비"]["상의"] == "허름한 경갑 상의"  # 데이터에 있는 칸은 그대로
    assert 상태["소지품"]["장비"]["옛 이름 상의"] == 1  # 소지품은 건드리지 않는다


def test_비운_칸은_화면과_장비_데이터가_같다(임시_세이브폴더):
    """전에는 화면에 옛 이름이 보이는데 장비 데이터에서는 빠져 있었다. 이제 둘 다 빈 칸이다
    (무기가 없으면 일반공격은 그대로 거부된다 - 다른 무기를 끼우면 된다)."""
    상태 = _없는_장비_세이브(임시_세이브폴더)
    c = 상태["파티"]["파티원"][0]
    assert c["장착장비"]["무기"] is None
    assert gf.캐릭터_장착아이템(상태, c, "무기") is None
