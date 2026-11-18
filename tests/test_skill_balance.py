"""tools/skill_balance.py - 스킬 밸런스 기준표(기대 피해 vs 기준 피해)."""

import dataclasses

import pytest

from tools import skill_balance as sb


def _스킬(이름):
    for _, 목록 in sb.직업별_스킬():
        if 이름 in 목록:
            return 목록[이름]
    raise KeyError(이름)


def _행(이름, 차수, 빌드=sb.기준빌드):
    return sb.스킬_행(이름, _스킬(이름), 빌드, 차수)


def test_스킬기준표가_지금_데이터와_같다():
    """스킬 데이터나 기준을 바꾸면 `python tools/skill_balance.py`로 표를 다시 쓴다."""
    with open(sb.표_경로, encoding="utf-8") as f:
        assert f.read() == sb.전체_문서(), (
            "docs/balance/스킬기준표.md가 낡았다 - python tools/skill_balance.py"
        )


@pytest.mark.parametrize(
    "데이터, 차수, 기대",
    [
        (
            {"행동": "일반행동", "MP소모": 30, "재료소모": {"무색 큐브 조각": 5}},
            3,
            52.5,
        ),
        ({"행동": "일반행동", "일반공격취급": True, "MP소모": 10}, 4, 15),
        ({"행동": "보조행동", "MP소모": 10}, 2, 12),
        ({"행동": "반응행동", "MP소모": 5}, 1, 12),
        ({"행동": None, "MP소모": 0}, 5, 0),
    ],
)
def test_비용은_기준표의_행동_MP_큐브_값을_더한다(데이터, 차수, 기대):
    assert sb.비용(데이터, 차수)[0] == 기대


def test_손으로_셈한_3차수_표와_같다():
    """docs/balance/귀검사.md "3차수 스킬 식 기대값"(손 계산)과 같은 값."""
    assert _행("맹룡단공참", 3)["기대"] == pytest.approx(16.07, abs=0.01)
    assert _행("맹룡단공참", 3)["기준"] == 15
    assert _행("혼백참", 3)["기대"] == pytest.approx(48.21, abs=0.01)
    assert _행("악귀참수", 4)["기대"] == pytest.approx(72.32, abs=0.01)
    아웃 = _행("아웃레이지 브레이크", 3)
    assert (아웃["기대"], 아웃["기준"]) == (67.5, 78.75)
    블러디 = _행("블러디 레이브", 3)
    assert (블러디["기대"], 블러디["기준"]) == (10, 12.5)
    assert 블러디["대상"] == "전체(1체당)"
    assert _행("환영검무", 4)["기대"] == 67.5


def test_빌드를_바꾸면_기대만_바뀌고_기준은_그대로다():
    기준 = _행("맹룡단공참", 3)
    빌드 = dataclasses.replace(sb.기준빌드, 명중보너스=1, 데미지보너스=2)
    바뀜 = _행("맹룡단공참", 3, 빌드)
    assert 바뀜["기준"] == 기준["기준"]
    # 명중 +2(스킬 +1, 빌드 +1) = 80%, 타격마다 (7.5 x 2 + 2)
    assert 바뀜["기대"] == pytest.approx(17 * 0.8 / 0.7)
    무기 = _행("맹룡단공참", 3, dataclasses.replace(sb.기준빌드, 무기="1d12"))
    assert 무기["기대"] == pytest.approx((6.5 + 3) * 2 * 0.75 / 0.7)


def test_명중반복은_앞_시도가_모두_맞아야_다음_시도가_나간다():
    데이터 = {
        "데미지": "10",
        "명중률": "보정명중률",
        "명중보너스": 0,
        "타겟": "적단일",
        "명중반복": {"최대": 3, "명중보너스변화": -2},
    }
    합, _ = sb.부분_기대(데이터, sb.기준빌드, 1)
    # 명중 70%, 60%, 50%: 10 x (0.7 + 0.7 x 0.6 + 0.7 x 0.6 x 0.5) / 0.7
    assert 합 == pytest.approx(10 * (0.7 + 0.42 + 0.21) / 0.7)


def test_셀_수_없는_스킬은_수동_확인으로_남긴다():
    행 = _행("역병의 라사", 3)
    assert 행["기대"] is None and 행["비고"][0].startswith("수동 확인")
    sb.보충["맹룡단공참"] = "시험"
    try:
        assert _행("맹룡단공참", 3)["비고"][0] == "수동 확인: 시험"
    finally:
        del sb.보충["맹룡단공참"]


def test_반영하지_않은_키는_비고에_적는다():
    assert "홀딩값" in _행("블러디 레이브", 3)["비고"][0]
    assert _행("맹룡단공참", 3)["비고"] == []


def test_측정파티_캐릭터의_수치로_빌드를_만든다():
    빌드, 차수 = sb.측정파티_빌드("검귀")
    assert 차수 == 2 and 빌드.이름.startswith("검귀")
    assert 빌드.추가공격 == 1 and 빌드.무기 == "1d8"


def test_명령(capsys):
    assert sb.main(["--직업", "웨펀마스터", "--보정치", "4"]) == 0
    출력 = capsys.readouterr().out
    assert "## 웨펀마스터" in 출력 and "보정치 +4" in 출력 and "## 검귀" not in 출력
    assert sb.main(["--측정파티", "검귀"]) == 0
    assert "| 2차수 |" in capsys.readouterr().out
    assert sb.main(["--직업", "없는직업"]) == 1
