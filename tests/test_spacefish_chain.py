"""공어 연속전투(사용자 지정 2026-11-03, #490) - 공어/대공어를 처치하고 이긴 전투가 끝날 때, 보상 전에
잡은 공어·대공어 1마리당 1% 확률로 공왕 크로쿠타(보스 칭호)+대공어 2+공어 2가 바로 나온다(맵 데이터 "연속전투").
두 전투를 모두 이기면 첫 전투 보상과 크로쿠타 전투 보상을 차례로 받고, 크로쿠타 전투에서 지거나 도망치면
첫 전투 보상도 없다. 크로쿠타를 한 번 이기면 업적에서 크로쿠타의 가시를 받는다."""

import copy

import pytest

import gameflow as gf
from game.data.achievement.achievement_list import 업적_목록
from game.system import achievement_system, dungeon_system, rng
from tests import support

천해 = "dungeon_02A_D15_middleocean_shallow"
심해 = "dungeon_02A_D16_middleocean_deep"
크로쿠타 = "공왕 크로쿠타"


def _맵(파일명):
    return gf.던전_레지스트리[파일명]


def _공어_전투(monkeypatch, 몬스터들, 굴림):
    """천해에서 몬스터들과 싸워 이긴 상태. 연속전투 판정 굴림(rng.던전.random)을 굴림으로 고정한다."""
    상태 = support.새게임([("", "귀검사")])
    gf.던전_진입(상태, 천해)
    gf.전투_시작(상태, 몬스터들, 레벨=8, 차수=2)
    support.반응_처리(상태)
    monkeypatch.setattr(rng.던전, "random", lambda: 굴림)
    support.강제_승리(상태)
    return 상태


def _골드(상태):
    return 상태["소지품"]["골드"]


def _보상_끝내기(상태):
    while gf.전투_보상_대기중(상태):
        gf.전투_보상_포기(상태)


# =====================================================
# 맵 데이터와 판정
# =====================================================


@pytest.mark.parametrize("파일명", [천해, 심해])
def test_공어가_나오는_맵에_연속전투가_적혀_있다(파일명):
    연속 = _맵(파일명)["연속전투"]
    assert 연속["조건몬스터"] == ["공어", "대공어"]
    assert 연속["마리당확률"] == 0.01
    assert 연속["등장몬스터"] == [
        {"이름": 크로쿠타, "칭호": "보스"},
        "대공어",
        "대공어",
        "공어",
        "공어",
    ]


def test_공어_출현_맵에는_모두_연속전투가_있다():
    for 파일명, 맵 in gf.던전_레지스트리.items():
        그룹들 = (맵.get("인카운트") or {}).get("출현그룹") or []
        공어맵 = any("공어" in g["출현몬스터"] for g in 그룹들)
        assert 공어맵 == ("연속전투" in 맵), 파일명


def test_확률은_잡은_공어와_대공어_1마리당_1퍼센트(monkeypatch):
    맵 = _맵(천해)
    처치 = ["공어", "대공어", "세리말리온"]  # 공어류 2마리 -> 2%
    monkeypatch.setattr(rng.던전, "random", lambda: 0.0199)
    assert dungeon_system.연속전투_판정(맵, 처치) == 맵["연속전투"]["등장몬스터"]
    monkeypatch.setattr(rng.던전, "random", lambda: 0.02)
    assert dungeon_system.연속전투_판정(맵, 처치) is None
    assert dungeon_system.연속전투_판정(맵, ["세리말리온"]) is None
    assert dungeon_system.연속전투_판정({"인카운트": None}, ["공어"]) is None


# =====================================================
# 흐름
# =====================================================


def test_판정에_걸리면_보상_전에_크로쿠타_전투가_이어진다(monkeypatch):
    상태 = _공어_전투(monkeypatch, ["공어", "대공어"], 0.0)
    골드 = _골드(상태)
    assert gf.전투_결과_정리(상태) == "연속전투"
    assert _골드(상태) == 골드 and not gf.전투_보상_대기중(상태)
    gf.연속전투_시작(상태)
    support.반응_처리(상태)
    적 = sorted(gf.적_목록(상태), key=lambda p: p["대형위치"])
    assert sorted(p["원본"]["몬스터명"] for p in 적) == sorted(
        [크로쿠타, "대공어", "대공어", "공어", "공어"]
    )
    왕 = next(p for p in 적 if p["원본"]["몬스터명"] == 크로쿠타)
    assert 왕["원본"]["칭호"] == "보스"
    assert (왕["원본"]["레벨"], 왕["원본"]["차수"]) == (8, 2)  # 천해 인카운트를 따른다


def test_두_전투를_이기면_첫_전투_보상과_크로쿠타_보상을_차례로_받는다(monkeypatch):
    상태 = _공어_전투(monkeypatch, ["공어", "대공어"], 0.0)
    골드 = _골드(상태)
    gf.전투_결과_정리(상태)
    gf.연속전투_시작(상태)
    support.반응_처리(상태)
    support.강제_승리(상태)
    assert gf.전투_결과_정리(상태) == "아군승리"
    # 연속전투 안에서 다시 연속전투는 없다(굴림이 0이어도)
    assert _골드(상태) > 골드
    assert gf.전투_보상_대기중(상태)
    gf.전투_보상_포기(상태)
    assert gf.전투_보상_대기중(상태)  # 두 번째(크로쿠타 전투) 보상
    gf.전투_보상_포기(상태)
    assert not gf.전투_보상_대기중(상태)


@pytest.mark.parametrize("끝", ["적승리", "전투이탈"])
def test_크로쿠타_전투에서_지거나_도망치면_첫_전투_보상도_없다(monkeypatch, 끝):
    상태 = _공어_전투(monkeypatch, ["공어", "공어"], 0.0)
    골드 = _골드(상태)
    가방 = copy.deepcopy(상태["소지품"])
    gf.전투_결과_정리(상태)
    gf.연속전투_시작(상태)
    support.반응_처리(상태)
    if 끝 == "적승리":
        support.강제_패배(상태)
    else:
        상태["전투상태"]["종료"] = "전투이탈"
    assert gf.전투_결과_정리(상태) == 끝
    assert _골드(상태) == 골드
    assert 상태["소지품"] == 가방
    assert not gf.전투_보상_대기중(상태)
    # 다음 전투는 평소처럼(남은 연속전투 기록이 없다) - 전멸하면 화면이 마을에서 쉬게 한다
    gf.파티_최대치로_회복(상태)
    gf.전투_시작(상태, ["세리말리온"], 레벨=8, 차수=2)
    support.반응_처리(상태)
    support.강제_승리(상태)
    assert gf.전투_결과_정리(상태) == "아군승리"


def test_판정에_안_걸리면_평소처럼_보상(monkeypatch):
    상태 = _공어_전투(monkeypatch, ["공어", "대공어"], 0.99)
    assert gf.전투_결과_정리(상태) == "아군승리"
    assert gf.전투_보상_대기중(상태)
    _보상_끝내기(상태)


def test_공어가_없는_전투는_연속전투가_없다(monkeypatch):
    상태 = _공어_전투(monkeypatch, ["세리말리온"], 0.0)
    assert gf.전투_결과_정리(상태) == "아군승리"


# =====================================================
# 업적
# =====================================================


def _크로쿠타_업적():
    return next(u for u in 업적_목록 if u["ID"] == "공왕_크로쿠타_처치")


def test_크로쿠타를_한_번_이기면_업적에서_크로쿠타의_가시를_받는다(monkeypatch):
    업적 = _크로쿠타_업적()
    assert 업적["분류"] == "특수업적"
    assert achievement_system.보상_내용(업적) == {"아이템": [("크로쿠타의 가시", 1)]}
    상태 = _공어_전투(monkeypatch, ["공어"], 0.0)
    assert not achievement_system.달성(상태["진행도"], 업적)
    gf.전투_결과_정리(상태)
    gf.연속전투_시작(상태)
    support.반응_처리(상태)
    support.강제_승리(상태)
    gf.전투_결과_정리(상태)
    _보상_끝내기(상태)
    assert achievement_system.달성(상태["진행도"], 업적)


def test_크로쿠타를_쓰러뜨려도_전투에서_지면_업적이_아니다(monkeypatch):
    업적 = _크로쿠타_업적()
    상태 = _공어_전투(monkeypatch, ["공어"], 0.0)
    gf.전투_결과_정리(상태)
    gf.연속전투_시작(상태)
    support.반응_처리(상태)
    왕 = next(p for p in gf.적_목록(상태) if p["원본"]["몬스터명"] == 크로쿠타)
    왕["생존"] = False
    support.강제_패배(상태)
    gf.전투_결과_정리(상태)
    assert not achievement_system.달성(상태["진행도"], 업적)
