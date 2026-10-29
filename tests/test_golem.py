"""골렘 종족(2026-10-29 사용자 지정) - 종족:골렘 특성(잡기불가, 속도·AC, 관통·참격 저항, 주기 슈퍼아머)과
골렘 패턴이 일으키는 규칙(매 회 무작위 대상, 명중 뒤 따로 굴리는 추가 공격, 조건부 자동 회피, 석 레이저).

패턴 데이터 값은 전수 골든(test_combat_monsters)이 본다. 여기는 규칙을 정확한 값으로 본다.
"""

import pytest

import gameflow as gf
from game.system import monster_ai, rng
from game.system.combat import attacks, damage, flow, monster_actions, stats, traits
from tests import support


def _전장(이름):
    전투상태, 적, 아군 = support.시험_전투([이름])
    아군 = sorted(아군, key=lambda p: p["대형위치"])
    return 전투상태, 적[0], 아군


def _한턴(전투상태, 몬스터, monkeypatch, 패턴, 대상=None):
    """몬스터가 턴을 시작하고 이 패턴으로 한 번 행동한 뒤 턴을 끝낸다."""
    monkeypatch.setattr(monster_ai, "행동_선택", lambda p: 패턴)
    if 대상 is not None:
        monkeypatch.setattr(monster_ai, "타겟_선택", lambda *a, **k: 대상)
    전투상태["현재턴"] = 전투상태["참가자"].index(몬스터)
    flow.턴_시작_처리(전투상태, 몬스터)
    monster_actions.몬스터_턴_실행(전투상태, 몬스터)
    flow.턴_종료_처리(전투상태, 몬스터)


def _패턴(몬스터, 이름):
    return next(p for p in 몬스터["원본"]["패턴"].values() if p["이름"] == 이름)


def _타격로그(전투상태, 시작, 이름):
    return [
        x
        for x in 전투상태["로그"][시작:]
        if x.get("종류") == "타격" and x.get("패턴") == 이름
    ]


def _명중_차례로(monkeypatch, 성공들):
    """명중 판정을 차례로 성공/실패로 고정한다(남는 판정은 성공)."""
    남은 = list(성공들)

    def 판정(*a, **k):
        성공 = 남은.pop(0) if 남은 else True
        return {"성공": 성공, "자연눈": 10, "치명타": False, "자동실패": False}

    monkeypatch.setattr(damage, "명중_판정", 판정)


# ------------------------------------------------------------- 종족:골렘


def test_종족_골렘은_속도보너스_마이너스3_AC_플러스1_잡기불가():
    전투상태, 골렘, _ = _전장("진흙 골렘")
    assert traits.특성_수치(전투상태, 골렘, "속도보너스") == -3
    assert traits.특성_수치(전투상태, 골렘, "AC보너스") == 1
    from game.system.combat import status

    assert status.특성_플래그(전투상태, 골렘, "잡기불가")


@pytest.mark.parametrize(
    "공격타입, 받는피해", [("관통", 5), ("참격", 5), ("타격", 10), (None, 10)]
)
def test_골렘은_관통_참격_피해를_절반만_받는다(공격타입, 받는피해):
    전투상태, 골렘, _ = _전장("진흙 골렘")
    방어력 = stats.유효_방어력(전투상태, 골렘)
    HP전 = 골렘["현재HP"]
    damage.피해_적용(전투상태, 골렘, 10, 공격타입=공격타입)
    assert HP전 - 골렘["현재HP"] == 받는피해 - 방어력


def test_일반공격은_무기의_공격타입을_피해_적용에_넘긴다(monkeypatch):
    전투상태, 골렘, 아군 = _전장("진흙 골렘")
    공격자 = 아군[0]
    받은 = []
    원래 = damage.피해_적용

    def 기록(*a, **k):
        받은.append(k.get("공격타입"))
        return 원래(*a, **k)

    monkeypatch.setattr(damage, "피해_적용", 기록)
    _명중_차례로(monkeypatch, [True])
    attacks.일반공격_실행(전투상태, 공격자, 골렘)
    assert 받은[0] == stats.타격_공격타입(공격자, "보정공격력", None)
    assert 받은[0] is not None


def test_골렘은_3번째_차례부터_슈퍼아머가_끊기지_않는다():
    전투상태, 골렘, _ = _전장("진흙 골렘")

    def 슈퍼아머():
        return [s for s in 골렘["상태이상"] if s["이름"] == "슈퍼아머"]

    있음 = []
    for _ in range(8):
        flow.턴_시작_처리(전투상태, 골렘)
        있음.append(bool(슈퍼아머()))
        flow.턴_종료_처리(전투상태, 골렘)
    assert 있음 == [False, False] + [True] * 6
    flow.턴_시작_처리(전투상태, 골렘)  # 9번째 차례 = 다시 거는 차례
    assert 슈퍼아머()[0]["지속턴"] == 3


# ------------------------------------------------------------- 패턴


def test_강철탄환은_5번_매번_무작위_적을_새로_고른다(monkeypatch):
    전투상태, 골렘, 아군 = _전장("스틸 골렘")
    순서 = [아군[0], 아군[2], 아군[2], 아군[1], 아군[3]]
    남은 = list(순서)
    monkeypatch.setattr(rng.대상, "choice", lambda 후보: 남은.pop(0))
    _명중_차례로(monkeypatch, [])
    시작 = len(전투상태["로그"])
    _한턴(전투상태, 골렘, monkeypatch, _패턴(골렘, "강철탄환"))
    로그 = _타격로그(전투상태, 시작, "강철탄환")
    assert [x["대상"] for x in 로그] == [p["이름"] for p in 순서]
    assert all(len(x["타격"]) == 1 for x in 로그)


@pytest.mark.parametrize("본탄명중", [True, False])
def test_청동탄은_명중하면_명중굴림을_따로_해_1d6_역장을_더_준다(본탄명중, monkeypatch):
    전투상태, 골렘, 아군 = _전장("청동 골렘")
    대상 = 아군[0]
    support.주사위고정(monkeypatch, 4)
    판정수 = []

    def 판정(*a, **k):
        판정수.append(1)
        return {"성공": 본탄명중, "자연눈": 10, "치명타": False, "자동실패": False}

    monkeypatch.setattr(damage, "명중_판정", 판정)
    시작 = len(전투상태["로그"])
    _한턴(전투상태, 골렘, monkeypatch, _패턴(골렘, "청동탄 발사"), 대상)
    폭발 = _타격로그(전투상태, 시작, "청동탄 폭발")
    if 본탄명중:
        assert len(판정수) == 2
        assert len(폭발) == 1 and 폭발[0]["대상"] == 대상["이름"]
        # 1d6(4) + 탱커 데미지 -1, 보정치 없음
        assert 폭발[0]["타격"][0]["피해"] == max(
            0, 3 - stats.유효_방어력(전투상태, 대상)
        )
    else:
        assert len(판정수) == 1 and not 폭발


def test_키_큰놈들_죽어는_넘어진_적과_마법사를_반드시_빗맞힌다(monkeypatch):
    전투상태, 레이조, 아군 = _전장("돌칼의 레이조")
    마법사 = next(p for p in 아군 if p["원본"]["직업"] == "마법사")
    넘어진 = next(p for p in 아군 if p["원본"]["직업"] == "귀검사")
    넘어진["상태이상"].append({"이름": "넘어짐", "지속턴": 1})
    판정대상 = []

    def 판정(전투상태_, 공격자, 대상, *a, **k):
        판정대상.append(대상["이름"])
        return {"성공": True, "자연눈": 10, "치명타": False, "자동실패": False}

    monkeypatch.setattr(damage, "명중_판정", 판정)
    HP전 = {p["이름"]: p["현재HP"] for p in 아군}
    _한턴(전투상태, 레이조, monkeypatch, _패턴(레이조, "키 큰놈들 죽어!"))
    for p in 아군:
        맞음 = p["현재HP"] < HP전[p["이름"]]
        assert 맞음 == (p is not 마법사 and p is not 넘어진), p["이름"]
    assert 마법사["이름"] not in 판정대상 and 넘어진["이름"] not in 판정대상
    문장 = [줄 for 항목 in 전투상태["로그"] for 줄 in gf.로그_문장들(항목)]
    assert 문장.count("자동 회피!") == 2


def test_석_레이저는_범위에_반드시_맞고_건강내성_실패시_1턴_석화(monkeypatch):
    전투상태, 골렘, 아군 = _전장("스톤 골렘")
    가운데 = 아군[1]
    monkeypatch.setattr(stats, "대상_내성굴림", lambda *a, **k: (False, 1, 0))
    _한턴(전투상태, 골렘, monkeypatch, _패턴(골렘, "석 레이저"), 가운데)
    석화 = [p["이름"] for p in 아군 if any(s["이름"] == "석화" for s in p["상태이상"])]
    assert 석화 == [p["이름"] for p in 아군[0:3]]
