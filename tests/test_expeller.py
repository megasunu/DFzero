"""익스펠러 종족(2026-10-29 사용자 지정, #472) - 종족:익스펠러(석상 상태로 등장, 공격타입 고정 피해 감소,
속도)와 헤븐 익스펠러의 하늘성의 친위대장(모든 공격 명속성, 명속성 저항, 패턴 1회 추가).

패턴 데이터 값은 전수 골든(test_combat_monsters)이 본다. 여기는 규칙을 정확한 값으로 본다.
"""

import pytest

import gameflow as gf
from game.system import monster_ai
from game.system.combat import damage, flow, monster_actions, stats, status, traits
from tests import support


def _전장(이름):
    전투상태, 적, 아군 = support.시험_전투([이름])
    아군 = sorted(아군, key=lambda p: p["대형위치"])
    return 전투상태, 적[0], 아군


def _석상(몬스터):
    return [s for s in 몬스터["상태이상"] if s["이름"] == "석상"]


def _석상_새로(몬스터):
    """전투 시작 때 몬스터가 먼저 움직였을 수 있으니 석상을 처음 등장한 상태로 되돌린다."""
    몬스터["상태이상"] = [s for s in 몬스터["상태이상"] if s["이름"] != "석상"]
    몬스터["상태이상"].append({"이름": "석상", "지속턴": None})


def _차례(전투상태, 몬스터, monkeypatch, 패턴=None):
    """몬스터가 턴을 시작하고 행동한 뒤 턴을 끝낸다. 행동했으면 True."""
    if 패턴 is not None:
        monkeypatch.setattr(monster_ai, "행동_선택", lambda p: 패턴)
    전투상태["현재턴"] = 전투상태["참가자"].index(몬스터)
    flow.턴_시작_처리(전투상태, 몬스터)
    결과 = monster_actions.몬스터_턴_실행(전투상태, 몬스터)
    flow.턴_종료_처리(전투상태, 몬스터)
    return "무행동" not in str((결과 or {}).get("행동", ""))


def _패턴(몬스터, 이름):
    return next(p for p in 몬스터["원본"]["패턴"].values() if p["이름"] == 이름)


def _맞히기(전투상태, 공격자, 몬스터):
    damage.피격_처리(전투상태, 공격자, 몬스터, {"성공": True})


# ------------------------------------------------------------- 석상 상태


@pytest.mark.parametrize("이름", ["익스펠러", "엑스 익스펠러", "헤븐 익스펠러"])
def test_익스펠러는_석상_상태로_등장한다(이름):
    _, 몬스터, _ = _전장(이름)
    assert _석상(몬스터)


def test_석상은_맞지_않으면_두_번_쉬고_세_번째_차례에_풀린다(monkeypatch):
    전투상태, 몬스터, _ = _전장("익스펠러")
    _석상_새로(몬스터)
    찌르기 = _패턴(몬스터, "찌르기")
    assert not _차례(전투상태, 몬스터, monkeypatch, 찌르기)
    assert not _차례(전투상태, 몬스터, monkeypatch, 찌르기)
    assert _차례(전투상태, 몬스터, monkeypatch, 찌르기)
    assert not _석상(몬스터)


def test_첫_차례_전에_맞아도_첫_차례는_쉬고_다음_차례에_풀린다(monkeypatch):
    전투상태, 몬스터, 아군 = _전장("익스펠러")
    _석상_새로(몬스터)
    _맞히기(전투상태, 아군[0], 몬스터)
    찌르기 = _패턴(몬스터, "찌르기")
    assert not _차례(전투상태, 몬스터, monkeypatch, 찌르기)
    assert _석상(몬스터)
    assert _차례(전투상태, 몬스터, monkeypatch, 찌르기)
    assert not _석상(몬스터)


def test_첫_차례_뒤에_맞으면_다음_차례에_풀려_행동한다(monkeypatch):
    전투상태, 몬스터, 아군 = _전장("익스펠러")
    _석상_새로(몬스터)
    찌르기 = _패턴(몬스터, "찌르기")
    assert not _차례(전투상태, 몬스터, monkeypatch, 찌르기)
    _맞히기(전투상태, 아군[0], 몬스터)
    assert _차례(전투상태, 몬스터, monkeypatch, 찌르기)


def test_석상은_받는_피해가_절반이고_풀리면_원래대로():
    전투상태, 몬스터, _ = _전장("익스펠러")
    _석상_새로(몬스터)
    assert stats.유효_보호률(전투상태, 몬스터) == 0.5
    몬스터["상태이상"] = []
    assert stats.유효_보호률(전투상태, 몬스터) == 0


@pytest.mark.parametrize("상태이상", ["기절", "출혈", "넘어짐", "석화", "중독"])
def test_석상은_모든_상태이상에_면역이다(상태이상):
    전투상태, 몬스터, _ = _전장("익스펠러")
    _석상_새로(몬스터)
    assert status.상태이상_면역(전투상태, 몬스터, 상태이상)
    몬스터["상태이상"] = []
    assert not status.상태이상_면역(전투상태, 몬스터, 상태이상)


def test_석상일_때는_기사석상_그림_풀리면_본래_그림():
    _, 몬스터, _ = _전장("헤븐 익스펠러")
    _석상_새로(몬스터)
    assert gf.적_그림_파일(몬스터) == "asset_monster_knight_statue.webp"
    몬스터["상태이상"] = []
    assert gf.적_그림_파일(몬스터) == "asset_monster_heaven_expeller.webp"


def test_다른_몬스터의_그림은_원본_그대로():
    _, 골렘, _ = _전장("진흙 골렘")
    assert gf.적_그림_파일(골렘) == "asset_monster_mud_golem.webp"


# ------------------------------------------------------------- 종족:익스펠러


def test_종족_익스펠러는_속도보너스_3():
    전투상태, 몬스터, _ = _전장("익스펠러")
    assert traits.특성_수치(전투상태, 몬스터, "속도보너스") == 3


@pytest.mark.parametrize(
    "공격타입, 감소", [("관통", 3), ("참격", 3), ("타격", 3), ("역장", 0), (None, 0)]
)
def test_익스펠러는_관통_참격_타격_피해를_3_덜_받는다(공격타입, 감소):
    전투상태, 몬스터, _ = _전장("익스펠러")
    몬스터["상태이상"] = []  # 석상의 절반 감소를 빼고 본다
    방어력 = stats.유효_방어력(전투상태, 몬스터)
    HP전 = 몬스터["현재HP"]
    damage.피해_적용(전투상태, 몬스터, 10, 공격타입=공격타입)
    assert HP전 - 몬스터["현재HP"] == 10 - 방어력 - 감소


def test_가드는_2턴_받는_피해_절반(monkeypatch):
    전투상태, 몬스터, _ = _전장("익스펠러")
    몬스터["상태이상"] = []
    _차례(전투상태, 몬스터, monkeypatch, _패턴(몬스터, "가드"))
    assert stats.유효_보호률(전투상태, 몬스터) == 0.5
    가드 = [b for b in 몬스터["버프"] if b["이름"] == "보호률증가"]
    assert 가드 and 가드[0]["지속턴"] == 2


# ------------------------------------------------------------- 하늘성의 친위대장


def _헤븐(monkeypatch):
    전투상태, 몬스터, 아군 = _전장("헤븐 익스펠러")
    몬스터["상태이상"] = []
    support.주사위고정(monkeypatch, 10)
    monkeypatch.setattr(
        damage,
        "명중_판정",
        lambda *a, **k: {
            "성공": True,
            "자연눈": 10,
            "치명타": False,
            "자동실패": False,
        },
    )
    return 전투상태, 몬스터, 아군


def test_친위대장은_찌르기도_명속성으로_공격한다(monkeypatch):
    전투상태, 몬스터, 아군 = _헤븐(monkeypatch)
    받은 = []
    원래 = damage.피해_적용

    def 기록(*a, **k):
        받은.append(k.get("속성"))
        return 원래(*a, **k)

    monkeypatch.setattr(damage, "피해_적용", 기록)
    _차례(전투상태, 몬스터, monkeypatch, _패턴(몬스터, "찌르기"))
    assert 받은 and set(받은) == {"명속성"}


def test_친위대장은_명속성_저항():
    전투상태, 몬스터, _ = _전장("헤븐 익스펠러")
    assert damage.속성_피해배율(전투상태, 몬스터, "명속성") == 0.5


def test_친위대장은_한_턴에_패턴을_두_번_쓴다(monkeypatch):
    전투상태, 몬스터, _ = _헤븐(monkeypatch)
    시작 = len(전투상태["로그"])
    _차례(전투상태, 몬스터, monkeypatch, _패턴(몬스터, "찌르기"))
    타격 = [x for x in 전투상태["로그"][시작:] if x.get("종류") == "타격"]
    assert len(타격) == 2


def test_친위대장이_없는_익스펠러는_한_번만_쓴다(monkeypatch):
    전투상태, 몬스터, _ = _전장("엑스 익스펠러")
    몬스터["상태이상"] = []
    시작 = len(전투상태["로그"])
    _차례(전투상태, 몬스터, monkeypatch, _패턴(몬스터, "찌르기"))
    타격 = [x for x in 전투상태["로그"][시작:] if x.get("종류") == "타격"]
    assert len(타격) == 1


def test_익스펠러_그림_파일이_모두_있다():
    from pathlib import Path

    from game.data.buff.status_effects import 상태이상목록
    from game.data.monster.monster_race_expeller import 몬스터목록

    폴더 = Path(__file__).resolve().parent.parent / "game" / "assets" / "monster"
    그림들 = [m["이미지"] for m in 몬스터목록.values()]
    그림들.append(상태이상목록["석상"]["효과"]["표시그림"])
    assert all((폴더 / 그림).is_file() for 그림 in 그림들)
