"""전투 로그 항목의 "종류" 칸과 화면 문장(gameflow.로그_문장들)을 지킨다 (품질 계획 P4, Q-2).

- 문장 기준: 골든 파일에 든 전투 로그 항목 전부를 로그_문장들로 바꾼 결과를 골든
  `battle_log_sentences`에 고정한다. 로그 항목의 모양이 바뀌어도(칸 추가) 화면 문장은 그대로여야 한다.
- 종류 규칙: 엔진이 쌓는 dict 항목은 전부 로그_문장들이 아는 "종류"를 갖는다(conftest의
  `전투_로그_종류_검사`가 모든 테스트에서 core.로그를 지켜보고, 여기서는 골든에 든 항목을 본다).
"""

import json
import os

from game.system import rng
import gameflow as gf
from game.system.combat import core
from tests import support

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden")
문장_골든 = support.문장_골든


def test_골든_로그의_화면_문장이_기준과_같다(golden):
    문장들 = support.골든_문장들(GOLDEN_DIR)
    assert sum(len(v) for v in 문장들.values()) > 1000  # 골든에서 로그를 실제로 찾았나
    golden(문장_골든, 문장들)


def test_골든_로그의_dict_항목은_전부_아는_종류를_갖는다():
    모름 = [
        (이름, 항목)
        for 이름, 항목들 in support.골든_로그들(GOLDEN_DIR).items()
        for 항목 in 항목들
        if isinstance(항목, dict) and 항목.get("종류") not in gf.로그_종류_목록
    ]
    assert not 모름[:5], f"종류 없는/모르는 로그 항목 {len(모름)}개"


def test_문장_처리표는_엔진의_로그_종류를_빠짐없이_안다():
    assert set(gf.로그_종류_목록) == set(core.로그_종류)


def test_거대화로_쉬는_차례는_은는을_맞춰_쉬고있다로_보인다():
    """사용자 지정 2026-10-14 - 받침에 맞춰 "은/는"을 붙인다."""

    from game.system.combat import flow, monster_actions

    rng.시드(3)
    상태 = support.새게임([("", "귀검사")])
    gf.전투_시작(상태, ["타우 비스트"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    비스트 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
    flow.턴_시작_처리(전투상태, 비스트)
    monster_actions.몬스터_턴_실행(전투상태, 비스트)  # 첫 차례는 쉰다
    assert gf.로그_문장들(전투상태["로그"][-1]) == ["타우 비스트는 쉬고있다."]
    # 받침이 있는 이름은 "은"
    assert gf.로그_문장들(전투상태["로그"][-1] | {"공격자": "타우 비스트 B"}) == [
        "타우 비스트 B는 쉬고있다."
    ]
    assert gf.로그_문장들(전투상태["로그"][-1] | {"공격자": "거대 루가루 L"}) == [
        "거대 루가루 L은 쉬고있다."
    ]


def test_집요함은_집요한_공격으로_데미지를_입었다로_보인다():
    """2026-10-15 사용자 지정 문장."""
    항목 = {
        "공격자": "타우 아미",
        "대상": "레인저",
        "피해": 2,
        "비고": "집요함",
        "종류": "비고",
    }
    assert gf.로그_문장들(항목) == ["집요한 공격으로 2의 데미지를 입었다."]
    assert gf.로그_문장들(항목 | {"쓰러짐": ["레인저"]}) == [
        "집요한 공격으로 2의 데미지를 입었다.",
        "레인저는 쓰러졌다!",
    ]


def test_내성에_성공해도_절반_피해를_입었으면_피했다가_아니라_데미지로_보인다():
    """ "내성성공시": "데미지절반" 공격(#328) - 성공해도 피해가 있으면 데미지 줄, 0이면 피했다."""
    항목 = {
        "공격자": "타우 전사",
        "스킬": "포효",
        "난이도": 12,
        "타격": [
            {"대상": "레인저", "내성": "성공", "내성값": 15, "피해": 3},
            {"대상": "넨마스터", "내성": "성공", "내성값": 14, "피해": 0},
            {"대상": "런처", "내성": "실패", "내성값": 5, "피해": 6},
        ],
        "종류": "타격",
    }
    문장 = gf.로그_문장들(항목)
    assert "레인저는 3의 데미지를 받았다." in 문장
    assert "레인저는 공격을 피했다." not in 문장
    assert "넨마스터는 공격을 피했다." in 문장
    assert "런처는 6의 데미지를 받았다." in 문장


def _세션(*, 작업자=False):
    """pytest_sessionfinish에 넘길 가짜 세션. 병렬 실행(xdist)의 작업자는 config에 workerinput이 있다."""
    from types import SimpleNamespace

    설정 = SimpleNamespace(workerinput={}) if 작업자 else SimpleNamespace()
    return SimpleNamespace(config=설정)


def test_골든을_갱신하면_세션_끝에_문장_골든을_다른_골든에서_다시_쓴다(
    tmp_path, monkeypatch
):
    """문장 골든은 다른 골든에서 만들어진다 - 테스트 순서(병렬 포함)와 상관없이 갱신 한 번으로 맞아야 한다."""
    from tests import conftest

    항목 = {
        "공격자": "타우 아미",
        "대상": "레인저",
        "피해": 2,
        "비고": "집요함",
        "종류": "비고",
    }
    (tmp_path / "가.json").write_text(
        json.dumps({"로그": [항목]}, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / f"{문장_골든}.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(conftest, "GOLDEN_DIR", str(tmp_path))
    문장_파일 = tmp_path / f"{문장_골든}.json"

    monkeypatch.delenv("UPDATE_GOLDEN", raising=False)
    conftest.pytest_sessionfinish(_세션(), 0)
    assert (
        문장_파일.read_text(encoding="utf-8") == "{}\n"
    )  # 갱신 모드가 아니면 건드리지 않는다

    monkeypatch.setenv("UPDATE_GOLDEN", "1")
    conftest.pytest_sessionfinish(_세션(작업자=True), 0)
    assert (
        문장_파일.read_text(encoding="utf-8") == "{}\n"
    )  # 병렬 작업자는 쓰지 않는다(주 프로세스가 한 번)

    conftest.pytest_sessionfinish(_세션(), 0)
    with open(문장_파일, encoding="utf-8") as f:
        assert json.load(f) == {"가": [gf.로그_문장들(항목)]}


def test_핵심_로그는_적의_타격만_뺀다():
    """골든 축소(#237): 효과·스킬 스윕 뒤 라운드의 몬스터 공격은 몬스터 스윕이 따로 본다 - 그 줄만 뺀다."""
    전투상태 = {
        "참가자": [
            {"이름": "귀검사", "진영": "아군"},
            {"이름": "고블린", "진영": "적"},
        ]
    }
    로그 = [
        {"공격자": "고블린", "대상": "귀검사", "종류": "타격", "총피해": 3},
        {"공격자": "고블린", "대상": "귀검사", "종류": "일반공격"},
        {"공격자": "고블린", "대상": "고블린", "종류": "비고", "비고": "출혈"},
        {"공격자": "귀검사", "대상": "고블린", "종류": "타격", "총피해": 5},
        {"공격자": "귀검사", "종류": "반응", "스킬": "백스텝커터"},
        "라운드 2",
        # 반응이 걸린 적의 공격은 남긴다(반응 스윕이 보는 것)
        {"공격자": "고블린", "종류": "타격", "반응": "가드"},
        {"공격자": "고블린", "종류": "일반공격", "판정": {"반응회피": "위상 변화"}},
        {
            "공격자": "고블린",
            "종류": "타격",
            "타격": [{"판정": {"반응회피": "건가드"}}],
        },
    ]
    assert support.핵심_로그(전투상태, 로그) == 로그[2:]


def test_수치_변화는_바뀐_칸만_전후로_남긴다():
    전 = {"AC": 12, "능력치": {"근력": 3, "민첩": 2}, "변동": {"명중": 0}}
    후 = {"AC": 14, "능력치": {"근력": 3, "민첩": 4}, "변동": {"명중": 0}}
    assert support.수치_변화(전, 후) == {"AC": [12, 14], "능력치.민첩": [2, 4]}
    assert support.수치_변화(전, 전) == {}
