"""인챈트리스(2026-10-26 사용자 결정, #411) - 퍼페티어, 흑마법 빗자루, 사악한 호기심, 인형 바구니, 인형 : 매드
(능력치·밀리 행동·매디 가드·테러블 로어), 화끈한 애정의 캐스팅속도, 하베스팅·리젝트 쏜. 규칙은 docs/game-rules.md
"마법사 2차 전직"."""

import pytest

import gameflow as gf
from game.system import dice_utils, rng
from game.system.combat import damage, stats
from game.system.skill import skill_grant, skill_run
from tests import support


def _인챈트리스(monkeypatch, 빗자루=False, 퍽고르기=None, 둘=False):
    """레벨 8 인챈트리스(스킬 전부 습득)[와 귀검사] 대 고블린 셋. 인챈트리스 차례, MP 999, 모두 HP 999,
    모든 주사위 20, 내성은 모두 실패."""
    rng.시드(5)
    파티 = [("", "마법사")] + ([("", "귀검사")] if 둘 else [])
    상태 = support.새게임(파티)
    c = 상태["파티"]["파티원"][0]
    support.성장(상태, c, 8, 전직="인챈트리스", 스킬습득=True, 퍽고르기=퍽고르기)
    if 빗자루:
        상태["소지품"]["장비"]["낡은 빗자루"] = 1
        gf.장비_교체(상태, c, "무기", "낡은 빗자루")
    gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=1, 차수=1)
    support.반응_처리(상태)
    while not (gf.아군_차례인가(상태) and gf.현재_턴_참가자(상태)["원본"] is c):
        gf.턴_넘기기(상태)
    p = gf.현재_턴_참가자(상태)
    p["현재MP"] = 999
    for q in 상태["전투상태"]["참가자"]:
        q["현재HP"] = 999
    support.주사위고정(monkeypatch, 20)
    monkeypatch.setattr(
        dice_utils, "내성_굴림", lambda 보정치, 난이도, **kw: (False, 난이도)
    )
    적 = [q for q in 상태["전투상태"]["참가자"] if q["진영"] == "적"]
    return 상태, p, 적


def _특성_빼기(p, 이름):
    p["원본"]["보유특성"].remove(이름)


def test_퍼페티어면_저주에_걸리지_않는다(monkeypatch):
    상태, p, _ = _인챈트리스(monkeypatch)
    skill_grant.상태이상_부여(상태["전투상태"], p, "저주", 2)
    assert not any(s["이름"] == "저주" for s in p["상태이상"])
    _특성_빼기(p, "퍼페티어")
    skill_grant.상태이상_부여(상태["전투상태"], p, "저주", 2)
    assert any(s["이름"] == "저주" for s in p["상태이상"])


def test_흑마법_빗자루는_빗자루를_들면_AC를_2_올린다(monkeypatch):
    상태, p, _ = _인챈트리스(monkeypatch, 빗자루=True)
    전투상태 = 상태["전투상태"]
    있음 = stats.최종AC(전투상태, p)
    _특성_빼기(p, "흑마법 빗자루")
    assert 있음 - stats.최종AC(전투상태, p) == 2


def test_사악한_호기심은_치명타범위와_치명타주사위를_1씩_올린다(monkeypatch):
    상태, p, _ = _인챈트리스(monkeypatch)
    전투상태 = 상태["전투상태"]
    범위, 주사위 = (
        damage.유효_치명타범위(전투상태, p),
        stats.치명타_주사위수(전투상태, p),
    )
    _특성_빼기(p, "사악한 호기심")
    assert damage.유효_치명타범위(전투상태, p) - 범위 == 1  # 치명타가 나는 가장 낮은 눈
    assert 주사위 - stats.치명타_주사위수(전투상태, p) == 1


def test_인형_바구니면_인형을_써도_소모품이_줄지_않고_인형이_효과를_얻는다(monkeypatch):
    상태, p, _ = _인챈트리스(monkeypatch)
    p["원본"]["보유특성"].append("인형 바구니")
    상태["소지품"]["소모품"]["28호"] = 1
    gf.인형_사용(상태, "28호")
    assert 상태["소지품"]["소모품"]["28호"] == 1
    assert "인형 바구니 효과" in 상태["파티"]["인형"]["보유특성"]


def _매드_부르기(상태):
    gf.아군_스킬사용(상태, "인형 : 매드")
    아군 = [q for q in 상태["전투상태"]["참가자"] if q["진영"] == "아군"]
    return 아군[-1]


def test_인형_매드는_아군_맨_뒤로_들어오고_부른_사람의_능력치를_쓴다(monkeypatch):
    상태, p, _ = _인챈트리스(monkeypatch, 둘=True)
    매드 = _매드_부르기(상태)
    assert 매드.get("인형") and 매드["원본"]["인형"] == "매드"
    assert 상태["파티"]["인형"] is 매드["원본"]
    for 능력치 in ("근력", "민첩", "지능", "지혜", "매력"):
        assert 매드["원본"][능력치] == p["원본"][능력치], 능력치
    assert "인형:매드" in 매드["원본"]["보유특성"]


def test_매드는_밀리라_차수만큼_행동하고_매디_가드는_자신과_부른_사람에게_임시생명력(
    monkeypatch,
):
    상태, p, _ = _인챈트리스(monkeypatch, 둘=True)
    매드 = _매드_부르기(상태)
    전투상태 = 상태["전투상태"]
    support.주사위고정(monkeypatch, 3)  # 매디 가드
    시작 = len(전투상태["로그"])
    gf.인형_턴(상태, 매드)
    가드 = [e for e in 전투상태["로그"][시작:] if e.get("스킬") == "매디 가드"]
    assert len(가드) == 2  # 레벨 8 - 차수 2
    for q in (매드, p):
        (버프,) = [b for b in q["버프"] if b["이름"] == "매디 가드"]
        assert 버프["지속턴"] == 2


def test_테러블_로어는_적_전체를_친다(monkeypatch):
    상태, p, 적 = _인챈트리스(monkeypatch)
    매드 = _매드_부르기(상태)
    support.주사위고정(monkeypatch, 6)  # 테러블 로어
    gf.인형_턴(상태, 매드)
    assert all(q["현재HP"] < 999 for q in 적)


def test_화끈한_애정이면_캐스팅속도로_덜_밀리고_0이면_바로_쏜다(monkeypatch):
    상태, p, _ = _인챈트리스(monkeypatch, 둘=True)
    전투상태 = 상태["전투상태"]
    캐스팅 = {"캐스팅시간": {"우선도": -4}}
    바로 = {"캐스팅시간": {"우선도": -1}}
    assert skill_run.캐스팅_밀림(전투상태, p, 캐스팅)["우선도"] == -4
    assert not skill_run.캐스팅_바로쏨(전투상태, p, 바로)
    gf.아군_스킬사용(상태, "화끈한 애정")
    for q in (x for x in 전투상태["참가자"] if x["진영"] == "아군"):
        (버프,) = [b for b in q["버프"] if b["이름"] == "화끈한 애정"]
        assert 버프["지속턴"] == 10
    assert skill_run.캐스팅_밀림(전투상태, p, 캐스팅)["우선도"] == 0
    assert skill_run.캐스팅_바로쏨(전투상태, p, 바로)


@pytest.mark.parametrize(("스킬", "맞는수"), [("하베스팅", 1), ("리젝트 쏜", 3)])
def test_하베스팅과_리젝트_쏜은_암속성_관통(monkeypatch, 스킬, 맞는수):
    상태, p, 적 = _인챈트리스(monkeypatch)
    데이터 = 상태["스킬데이터모음"][스킬]
    assert (데이터["속성"], 데이터["공격타입"]) == ("암속성", "관통")
    gf.아군_스킬사용(상태, 스킬, 중심대상=적[1])
    assert sum(q["현재HP"] < 999 for q in 적) == 맞는수
    if 스킬 == "리젝트 쏜":
        for q in 적:
            (몹몰이,) = [s for s in q["상태이상"] if s["이름"] == "몹몰이"]
            assert 몹몰이["지속턴"] == 2
