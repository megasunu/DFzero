"""마도학자(044f) - 빗자루가 있어야 쓰는 스킬(사용무기)."""

import pytest

from game.system import dice_utils, rng
from game.system.combat import core, resources, stats
from game.system.skill import skill_run
import gameflow as gf
from tests import support


def _마도학자_전투(빗자루):
    """마법사 -> 마도학자 레벨 8(스킬 전부 습득)이 고블린 하나와 싸우는 중. 빗자루면 낡은 빗자루를 든다."""
    rng.시드(5)
    상태 = support.새게임([("", "마법사")])
    c = 상태["파티"]["파티원"][0]
    support.성장(상태, c, 8, 전직="마도학자", 스킬습득=True)
    if 빗자루:
        상태["소지품"]["장비"]["낡은 빗자루"] = 1
        gf.장비_교체(상태, c, "무기", "낡은 빗자루")
    gf.전투_시작(상태, ["고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    return 상태, next(p for p in 상태["전투상태"]["참가자"] if p["원본"] is c)


@pytest.mark.parametrize("스킬", ["빗자루 스핀", "데스 파우더", "칠링 파우더"])
def test_빗자루_스킬은_빗자루를_들어야_쓴다(스킬):
    가능, 사유 = gf.스킬_사용_가능여부(*_마도학자_전투(False), 스킬)
    assert not 가능 and "빗자루" in 사유
    assert gf.스킬_사용_가능여부(*_마도학자_전투(True), 스킬)[0]


# 빗자루를 주무기로 쓰는 전직은 전직(레벨 6)하며 빗자루 마스터리를 얻는다(2026-11-02 사용자 결정) -
# 웨펀마스터의 광검 마스터리, 스트라이커의 권투글러브 마스터리와 같다. 그래서 같은 이름의 퍽은 없앴다.
@pytest.mark.parametrize("전직", ["마도학자", "인챈트리스"])
def test_빗자루_전직은_레벨6에_빗자루_마스터리를_얻는다(전직):
    상태 = support.새게임([("", "마법사")])
    c = 상태["파티"]["파티원"][0]
    support.성장(상태, c, 5)
    assert "빗자루 마스터리" not in c["보유특성"]
    support.성장(상태, c, 6, 전직=전직)
    assert "빗자루 마스터리" in c["보유특성"]
    assert "빗자루" in c["가용무기"]


def test_빗자루_마스터리_퍽은_없다():
    assert "빗자루 마스터리" not in gf.직업_레지스트리["마법사"]["퍽목록"]


# ------------------------------------------------- #411: 마도학자 특성·퍼밀리어·파우더 동작


def _차례(상태, 몬스터=("고블린", "고블린", "고블린")):
    """_마도학자_전투 대신 적 여럿 - 마도학자 차례, MP 999, 적 HP 999."""
    전투상태 = 상태["전투상태"]
    while not gf.아군_차례인가(상태):
        gf.턴_넘기기(상태)
    p = gf.현재_턴_참가자(상태)
    p["현재MP"] = 999
    p["행동자원"]["일반행동"] = 9
    for q in 전투상태["참가자"]:
        q["현재HP"] = 999
    return p, [q for q in 전투상태["참가자"] if q["진영"] == "적"]


def _명중(monkeypatch, 내성성공=False):
    support.주사위고정(monkeypatch, 20)
    monkeypatch.setattr(
        dice_utils, "내성_굴림", lambda 보정치, 난이도, **kw: (내성성공, 난이도)
    )


@pytest.mark.parametrize(
    ("눈", "캔디바", "결과", "횟수"),
    [
        (0.1, False, "실패", 3),
        (0.5, False, "성공", 5),
        (0.9, False, "대성공", 7),
        (0.1, True, "성공", 5),
        (0.6, True, "성공", 5),
        (0.7, True, "대성공", 7),
    ],
)
def test_퍼밀리어는_1_3씩_굴리고_스위트_캔디바면_실패가_없다(
    monkeypatch, 눈, 캔디바, 결과, 횟수
):
    상태, p = _마도학자_전투(False)
    전투상태 = 상태["전투상태"]
    if 캔디바:
        gf.아군_스킬사용(상태, "스위트 캔디바")
    monkeypatch.setattr(rng.확률, "random", lambda: 눈)
    스킬 = {**상태["스킬데이터모음"]["고출력 매직미사일"], "_이름": "고출력 매직미사일"}
    새 = skill_run.퍼밀리어_굴림(전투상태, p, 스킬)
    assert 새["_퍼밀리어"] == 결과 and 새["공격횟수"] == 횟수
    assert 전투상태["로그"][-1]["비고"] == f"'고출력 매직미사일' {결과}!"


def test_장판_퍼밀리어는_대성공이면_라운드_추가타격_실패면_장판_없이_단일_피해(
    monkeypatch,
):
    상태, p = _마도학자_전투(False)
    전투상태 = 상태["전투상태"]
    스킬 = {**상태["스킬데이터모음"]["애시드 클라우드"], "_이름": "애시드 클라우드"}
    monkeypatch.setattr(rng.확률, "random", lambda: 0.9)
    대성공 = skill_run.퍼밀리어_굴림(전투상태, p, 스킬)
    assert "라운드추가타격" in 대성공["지속공격"]
    assert 대성공["지속공격"]["속성"] == "수속성"
    monkeypatch.setattr(rng.확률, "random", lambda: 0.5)
    assert (
        "라운드추가타격" not in skill_run.퍼밀리어_굴림(전투상태, p, 스킬)["지속공격"]
    )
    _명중(monkeypatch)
    p, 적 = _차례(상태)
    monkeypatch.setattr(rng.확률, "random", lambda: 0.1)
    gf.아군_스킬사용(상태, "애시드 클라우드")
    assert sum(q["현재HP"] < 999 for q in 적) == 1  # 실패 - 적 1체만 맞는다
    assert not any(  # 장판(적의 상태이상 "지속공격")이 없다
        x["이름"] == "애시드 클라우드" for q in 적 for x in q["상태이상"]
    )


def test_빗자루_다루기는_빗자루를_들면_AC_1을_올린다():
    상태, p = _마도학자_전투(True)
    전투상태 = 상태["전투상태"]
    빗자루AC = stats.최종AC(전투상태, p)
    p["원본"]["보유특성"].remove("빗자루 다루기")
    assert stats.최종AC(전투상태, p) == 빗자루AC - 1


def test_빗자루_다루기는_일반공격_명중을_1_올린다(monkeypatch):
    _명중(monkeypatch)
    결과 = []
    for 빼기 in (False, True):
        상태, _ = _마도학자_전투(True)
        p, 적 = _차례(상태)
        if 빼기:
            p["원본"]["보유특성"].remove("빗자루 다루기")
        gf.아군_일반공격(상태, 적[0])
        (타격,) = [e for e in 상태["전투상태"]["로그"] if e.get("종류") == "일반공격"][
            -1:
        ]
        결과.append(타격["판정"]["명중결과"])
    assert 결과[0] - 결과[1] == 1


def test_파우더는_5스택이고_일반공격_타격마다_하나_써_명중하면_효과를_건다(monkeypatch):
    _명중(monkeypatch)
    상태, _ = _마도학자_전투(True)
    p, 적 = _차례(상태)
    gf.아군_스킬사용(상태, "데스 파우더")
    assert resources.자원_보유량(상태["전투상태"], p, "데스 파우더") == 5
    gf.아군_일반공격(상태, 적[0])
    assert resources.자원_보유량(상태["전투상태"], p, "데스 파우더") == 4
    assert any(s["이름"] == "저주" for s in 적[0]["상태이상"])
    p["행동자원"]["보조행동"] = 1
    gf.아군_스킬사용(상태, "칠링 파우더")  # 함께 못 가진다 - 데스 파우더가 밀려난다
    assert resources.자원_보유량(상태["전투상태"], p, "데스 파우더") == 0
    assert resources.자원_보유량(상태["전투상태"], p, "칠링 파우더") == 5
    gf.아군_일반공격(상태, 적[0])
    assert any(s["이름"] == "빙결" for s in 적[0]["상태이상"])


def test_빗자루_스핀은_적_1체를_5번_치고_일반공격으로_취급한다(monkeypatch):
    _명중(monkeypatch)
    상태, _ = _마도학자_전투(True)
    p, 적 = _차례(상태)
    시작 = len(상태["전투상태"]["로그"])
    gf.아군_스킬사용(상태, "빗자루 스핀", 중심대상=적[0])
    타격 = [
        t
        for e in 상태["전투상태"]["로그"][시작:]
        if e.get("스킬") == "빗자루 스핀"
        for t in e.get("타격") or []
    ]
    assert len(타격) == 5 and {t["대상"] for t in 타격} == {적[0]["이름"]}
    assert 상태["스킬데이터모음"]["빗자루 스핀"]["일반공격취급"] is True


def test_고대의_도서관은_10턴_동안_지능을_차수만큼_올린다():
    상태, p = _마도학자_전투(False)
    전투상태 = 상태["전투상태"]
    p, _ = _차례(상태)
    지능 = stats.유효_능력치값(전투상태, p, "지능")
    gf.아군_스킬사용(상태, "고대의 도서관")
    (버프,) = [b for b in p["버프"] if b["이름"] == "고대의 도서관"]
    assert 버프["지속턴"] == 10
    assert stats.유효_능력치값(전투상태, p, "지능") == 지능 + core.차수(p)
