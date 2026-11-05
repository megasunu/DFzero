"""배틀메이지(2026-10-26 사용자 결정, #411) - 체이서 얻기·최대·소모 순서, 체이서 사출·프레스, 체이서 밤, 콤보본능,
니우의 전투술, 강화위상변화, 원무곤, 쇄패, 무기 마스터리 퍽. 규칙은 docs/game-rules.md "마법사 2차 전직"."""

import pytest

import gameflow as gf
from game.system import rng
from game.system.combat import flow, resources, stats, traits
from tests import support
from tests.support import 새게임, 성장


def _배틀메이지(monkeypatch, 레벨=8, 퍽고르기=None, 적=("고블린", "고블린", "고블린")):
    """레벨까지 키운 배틀메이지 혼자 대 적들. 배틀메이지 차례, MP 999, 적 HP 999, 모든 주사위 20(명중)."""
    rng.시드(5)
    상태 = 새게임([("", "마법사")])
    성장(
        상태,
        상태["파티"]["파티원"][0],
        레벨,
        전직="배틀메이지",
        스킬습득=True,
        퍽고르기=퍽고르기,
    )
    gf.전투_시작(상태, list(적), 레벨=1, 차수=1)
    support.반응_처리(상태)
    while not gf.아군_차례인가(상태):
        gf.턴_넘기기(상태)
    p = gf.현재_턴_참가자(상태)
    p["현재MP"] = 999
    적목록 = [q for q in 상태["전투상태"]["참가자"] if q["진영"] == "적"]
    for q in 적목록:
        q["현재HP"] = 999
    support.주사위고정(monkeypatch, 20)
    return 상태, p, 적목록


def _체이서수(p):
    return len(resources.체이서_목록(p))


def _버프중첩(p, 이름):
    return sum(b.get("중첩", 1) for b in p["버프"] if b["이름"] == 이름)


def test_체이서는_자기_턴_시작에_하나_얻고_체이서_밤이면_하나_더(monkeypatch):
    상태, p, _ = _배틀메이지(monkeypatch, 레벨=6)
    전투상태 = 상태["전투상태"]
    resources.체이서_소모(p)
    flow.턴_시작_처리(전투상태, p)
    assert _체이서수(p) == 1
    상태, p, _ = _배틀메이지(monkeypatch, 레벨=8)
    전투상태 = 상태["전투상태"]
    gf.아군_스킬사용(상태, "체이서 밤")
    resources.체이서_소모(p)
    flow.턴_시작_처리(전투상태, p)
    assert _체이서수(p) == 2


def test_체이서는_합쳐_9개까지이고_먼저_생긴_것부터_쓴다(monkeypatch):
    상태, p, _ = _배틀메이지(monkeypatch)
    resources.체이서_소모(p)
    얻음 = resources.체이서_얻기(상태["전투상태"], p, 12)
    assert len(얻음) == 9 and _체이서수(p) == 9
    처음 = [b["이름"].split(" : ")[1] for b in resources.체이서_목록(p)[:2]]
    assert resources.체이서_소모(p, 2) == [f"{x}속성" for x in 처음]
    assert _체이서수(p) == 7


def test_체이서가_없으면_체이서_사출을_못_쓰고_있으면_하나를_그_속성으로_쏜다(
    monkeypatch,
):
    상태, p, 적 = _배틀메이지(monkeypatch)
    resources.체이서_소모(p)
    assert not gf.스킬_사용_가능여부(상태, p, "체이서 사출")[0]
    resources.체이서_얻기(상태["전투상태"], p, 2)
    둘째 = resources.체이서_목록(p)[1]
    gf.아군_스킬사용(상태, "체이서 사출", 중심대상=적[0])
    assert resources.체이서_목록(p) == [둘째]  # 먼저 생긴 것을 썼다
    assert 적[0]["현재HP"] < 999


def test_체이서_프레스는_체이서를_전부_하나씩_쏜다(monkeypatch):
    상태, p, 적 = _배틀메이지(monkeypatch)
    resources.체이서_소모(p)
    resources.체이서_얻기(상태["전투상태"], p, 3)
    시작 = len(상태["전투상태"]["로그"])
    gf.아군_스킬사용(상태, "체이서 프레스", 중심대상=적[0])
    assert _체이서수(p) == 0
    타격 = [
        e
        for e in 상태["전투상태"]["로그"][시작:]
        if e.get("스킬") == "체이서 프레스" and e.get("총피해")
    ]
    assert len(타격) == 3, 타격


def test_체이서_밤이면_명중할_때마다_체이서를_얻는다(monkeypatch):
    상태, p, 적 = _배틀메이지(monkeypatch)
    gf.아군_스킬사용(상태, "체이서 밤")
    resources.체이서_소모(p)
    gf.아군_일반공격(상태, 적[0])
    assert _체이서수(p) == 1


def test_콤보본능은_명중마다_쌓이고_자기_턴이_끝나면_사라진다(monkeypatch):
    상태, p, 적 = _배틀메이지(monkeypatch, 레벨=6)
    전투상태 = 상태["전투상태"]
    근력 = stats.유효_능력치값(전투상태, p, "근력")
    gf.아군_일반공격(상태, 적[0])
    assert _버프중첩(p, "콤보본능") == 1
    assert stats.유효_능력치값(전투상태, p, "근력") == 근력 + 1
    gf.턴_넘기기(상태)
    assert _버프중첩(p, "콤보본능") == 0


def test_니우의_전투술은_일반공격에_주문시전보정치를_더한다(monkeypatch):
    상태, p, _ = _배틀메이지(monkeypatch, 레벨=6)
    (원소,) = traits.캐릭터특성_무기효과(상태["전투상태"], p, "일반공격추가피해")
    assert 원소["변동값"] == "주문시전보정치"


def test_원무곤은_때리고_붙잡아_넘어뜨린다(monkeypatch):
    상태, p, 적 = _배틀메이지(monkeypatch)
    gf.아군_스킬사용(상태, "원무곤", 중심대상=적[0])
    assert 적[0]["현재HP"] < 999
    이름들 = {s["이름"] for s in 적[0]["상태이상"]}
    assert "넘어짐" in 이름들 and ("홀딩" in 이름들 or "잡기" in 이름들), 이름들


def test_쇄패는_적_3체를_치고_일반공격으로_취급한다(monkeypatch):
    상태, p, 적 = _배틀메이지(monkeypatch)
    gf.아군_스킬사용(상태, "쇄패", 중심대상=적[1])
    assert all(q["현재HP"] < 999 for q in 적)
    assert 상태["스킬데이터모음"]["쇄패"]["일반공격취급"] is True


@pytest.mark.parametrize(
    ("무기종류", "주사위", "명중"),
    [("창", "1d12", 0), ("봉", "1d8", 2), ("검", None, 0)],
)
def test_배틀메이지의_무기_마스터리는_창_1d12_봉_1d8과_명중_2(
    monkeypatch, 무기종류, 주사위, 명중
):
    상태, p, _ = _배틀메이지(monkeypatch, 레벨=6)
    전투상태 = 상태["전투상태"]
    p["원본"]["보유특성"].append("배틀메이지의 무기 마스터리")
    monkeypatch.setattr(traits, "장착무기_타입", lambda 참가자: 무기종류)
    주사위들 = [
        o["변동값"] for o in traits.캐릭터특성_무기효과(전투상태, p, "무기공격력")
    ]
    assert 주사위들 == ([주사위] if 주사위 else [])
    명중원소 = [
        o
        for o in traits.캐릭터특성_무기효과(전투상태, p, "명중보너스")
        if o.get("무기조건")
    ]
    assert sum(o["변동값"] for o in 명중원소) == 명중
