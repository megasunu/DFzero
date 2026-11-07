# 공용 퍽 "제아봉침" - 스킬 "제아봉칩이십오만배"(불사/시한부, #311 사용자 결정 2026-10-20).
# 규칙은 docs/game-rules.md "공용 퍽 - 제아봉침". 실전 흐름은 풀 시나리오 S47.

import pytest

import gameflow as gf
from game.data.buff.debuff import 디버프목록
from game.data.buff.buff import 버프목록
from game.data.job_skill.job_skill_0000 import 스킬목록
from game.data.perks.perks_class_0000 import 퍽목록
from game.system import character_data_system as 캐릭터데이터
from game.system import rng
from game.system import skill_system as ss
from game.system.combat import core, damage, stats, status
from game.data import common_names
from tests import support

스킬 = "제아봉칩이십오만배"


def _전장(약점제거=False):
    """귀검사(제아봉침 보유)와 프리스트 대 고블린 - 귀검사의 차례, 모두 HP 999."""
    rng.시드(5)
    상태 = support.새게임([("", "귀검사"), ("", "프리스트")])
    귀검사원본 = 상태["파티"]["파티원"][0]
    귀검사원본["보유스킬"].append(스킬)
    if 약점제거:
        귀검사원본["보유특성"].append("약점제거")
    gf.전투_시작(상태, ["고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    for p in 전투상태["참가자"]:
        p["현재HP"] = 999
    _차례까지(상태, 귀검사원본)
    p = gf.현재_턴_참가자(상태)
    return 상태, 전투상태, p


def _차례까지(상태, 원본):
    for _ in range(50):
        현재 = gf.현재_턴_참가자(상태)
        if gf.아군_차례인가(상태) and 현재["원본"] is 원본:
            return
        gf.턴_넘기기(상태)
    raise AssertionError("차례가 오지 않았다")


def _이름들(p, 목록):
    return {i["이름"] for i in p[목록]}


# ------------------------------------------------------------------ 데이터


def test_제아봉침은_선행없는_4차수_스킬획득_퍽이다():
    퍽 = 퍽목록["제아봉침"]
    assert (퍽["분류"], 퍽["타입"], 퍽["차수"], 퍽["선행조건"]) == (
        "퍽",
        ["스킬획득"],
        4,
        None,
    )
    assert 퍽["획득스킬"] == 스킬


def test_제아봉칩이십오만배는_행동과_MP없는_휴식당_1회_버프스킬이다():
    데이터 = 스킬목록[스킬]
    assert 데이터["분류"] == "버프스킬"
    assert (데이터["행동"], 데이터["MP소모"], 데이터["휴식당횟수"]) == (None, 0, 1)
    assert (데이터["습득방법"], 데이터["습득퍽"]) == ("퍽습득", "제아봉침")
    assert 버프목록["불사"]["효과"] and 디버프목록["시한부"]["해제불가"]


def test_레벨업으로_제아봉침을_고르면_스킬을_얻는다():
    상태 = support.새게임([("", "귀검사")])
    c = 상태["파티"]["파티원"][0]
    c["레벨"], c["근력"] = 18, 18
    assert "제아봉침" in dict(gf.선택가능_퍽목록(c))


# ------------------------------------------------------------------ 사용


def test_쓰면_행동과_MP를_쓰지_않고_불사_시한부_슈퍼아머를_얻는다():
    상태, 전투상태, p = _전장()
    MP, 자원 = p["현재MP"], dict(p["행동자원"])
    gf.아군_스킬사용(상태, 스킬)
    assert p["현재MP"] == MP and p["행동자원"] == 자원
    assert {"제아봉침", "불사"} <= _이름들(p, "버프")
    assert "시한부" in _이름들(p, "디버프")
    assert "슈퍼아머" in _이름들(p, "상태이상")


def test_휴식당_1회라_두번째는_쓸_수_없다():
    상태, 전투상태, p = _전장()
    gf.아군_스킬사용(상태, 스킬)
    가능, 사유 = gf.스킬_사용_가능여부(상태, p, 스킬)
    assert not 가능 and "휴식당" in 사유


def test_행동불가_상태에서는_쓸_수_없다():
    상태, 전투상태, p = _전장()
    ss.상태이상_부여(전투상태, p, "기절", 1)
    가능, 사유 = gf.스킬_사용_가능여부(상태, p, 스킬)
    assert not 가능 and "행동불가" in 사유


@pytest.mark.parametrize("약점제거", [False, True])
def test_약점이_아닌_능력치가_10_오른다(약점제거):
    상태, 전투상태, p = _전장(약점제거)
    약점 = set(캐릭터데이터.약점스탯_목록(p["원본"]))
    assert bool(약점) != 약점제거
    전 = {s: stats.유효_능력치값(전투상태, p, s) for s in common_names.능력치_목록}
    gf.아군_스킬사용(상태, 스킬)
    for s in common_names.능력치_목록:
        후 = stats.유효_능력치값(전투상태, p, s)
        assert 후 - 전[s] == (0 if s in 약점 else 10), s


def test_건강이_오른_만큼_최대HP와_현재HP가_같이_오른다():
    상태, 전투상태, p = _전장()
    p["현재HP"] = 10
    전최대 = stats.유효_최대HP(전투상태, p)
    gf.아군_스킬사용(상태, 스킬)
    늘어남 = stats.유효_최대HP(전투상태, p) - 전최대
    assert 늘어남 > 0
    assert p["현재HP"] == 10 + 늘어남


def test_불사면_어떤_피해에도_HP가_1_아래로_내려가지_않는다():
    상태, 전투상태, p = _전장()
    gf.아군_스킬사용(상태, 스킬)
    damage.피해_적용(전투상태, p, 10**6, 피해감소무시=True)
    assert p["현재HP"] == 1 and p["생존"]


def test_명중이점과_무력화_약화CC_면역(monkeypatch):
    상태, 전투상태, p = _전장()
    gf.아군_스킬사용(상태, 스킬)
    for 이름 in ("기절", "빙결", "둔화", "암흑"):
        assert status.상태이상_면역(전투상태, p, 이름), 이름
    기록 = []

    def 굴림(이점=False, 불리=False):
        기록.append((이점, 불리))
        return 10

    monkeypatch.setattr(damage.dice_utils, "d20_굴림", 굴림)
    고블린 = next(e for e in gf.적_목록(상태) if e["생존"])
    damage.명중_판정_계산(전투상태, p, 고블린, "보정명중률")
    assert 기록 == [(True, False)]


def test_디버프해제로_시한부를_지울_수_없다():
    상태, 전투상태, p = _전장()
    gf.아군_스킬사용(상태, 스킬)
    ss.이름있는효과_해제(p, "디버프", "시한부")
    assert "시한부" in _이름들(p, "디버프")
    프리스트원본 = 상태["파티"]["파티원"][1]
    프리스트원본["보유스킬"].append("큐어")
    gf.턴_넘기기(상태)
    _차례까지(상태, 프리스트원본)
    gf.현재_턴_참가자(상태)["현재MP"] = 100
    gf.아군_스킬사용(상태, "큐어")
    assert "시한부" in _이름들(p, "디버프")


def test_자동전투_전력전투는_쓰지_않는다(monkeypatch):
    상태, 전투상태, p = _전장()
    고른 = gf.전력전투_고르기(상태, p)
    assert 고른 is None or 고른[0] != 스킬
    # 표시가 없으면 버프스킬로 먼저 골랐을 것이다 - 표시가 막는 것이다
    표시없음 = {
        k: v for k, v in 상태["스킬데이터모음"][스킬].items() if k != "자동전투금지"
    }
    monkeypatch.setitem(상태["스킬데이터모음"], 스킬, 표시없음)
    assert gf.전력전투_고르기(상태, p)[0] == 스킬


# ------------------------------------------------------------------ 지속과 사망


def test_다음_자기_차례에_행동이_하나씩_늘고_그_차례_끝에_사망한다():
    상태, 전투상태, p = _전장()
    기본 = dict(p["행동자원"])
    gf.아군_스킬사용(상태, 스킬)
    gf.턴_넘기기(상태)  # 쓴 차례의 끝 - 걸린 차례는 세지 않는다
    assert {"제아봉침", "불사"} <= _이름들(p, "버프") and p["생존"]
    _차례까지(상태, p["원본"])
    assert {"제아봉침", "불사"} <= _이름들(p, "버프")
    assert "시한부" in _이름들(p, "디버프") and "슈퍼아머" in _이름들(p, "상태이상")
    for 종류 in ("일반행동", "보조행동", "반응행동"):
        assert p["행동자원"][종류] == 기본[종류] + 1, 종류
    gf.턴_넘기기(상태)
    assert not p["생존"] and p["현재HP"] == 0
    assert "시한부" not in _이름들(p, "디버프")
    assert "불사" not in _이름들(p, "버프")


def test_시한부가_남은_채_전투가_끝나도_사망한다():
    상태, 전투상태, p = _전장()
    gf.아군_스킬사용(상태, 스킬)
    support.강제_승리(상태)
    assert 전투상태["종료"] == "아군승리"
    assert not p["생존"] and p["현재HP"] == 0
    gf.전투_결과_정리(상태)
    assert p["원본"]["현재HP"] == 0


def test_시한부가_없으면_전투가_끝나도_살아_있다():
    상태, 전투상태, p = _전장()
    support.강제_승리(상태)
    assert p["생존"] and p["현재HP"] > 0
    assert core.전투_종료_판정(전투상태) == "아군승리"
