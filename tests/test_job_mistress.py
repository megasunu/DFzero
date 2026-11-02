"""미스트리스(054f) 전직 특성/스킬 규칙 (2026-11-02 사용자 결정, #514).

레벨 6 "죄업에 짓눌린 육신"(어그로 -5, 죄업 7종 - 전투 끝까지), "짊어진 자의 낫 마스터리"(속도 +5, 낫이면 무기공격력
1d10), 레벨 8 버프 "일곱개의 대죄"(매 턴 죄악행동 - 죄악 스킬만). 낫 스킬(낫을 들어야, 일반공격취급, MP 10): 길로틴
(적 전체 명중 -1, 맞은 적 중 무작위 1명에게 한 번 더), 롤링 러쉬(5회, 훔쳐배우기). 죄악 스킬(보조행동, MP 10, DC 10+무기
능력치 보정치): 러스트 핸드(건강 - 공중에뜸, 죄업 쾌락), 프라이드 악셀(매력 - AC -1 3턴, 죄업 교만), 슬로스 바디(캐스팅
우선도 1, 민첩 - 둔화 3턴, 죄업 나태)."""

import pytest

import gameflow as gf
from game.system import rng
from game.system import skill_system as ss
from game.system.skill import skill_run
from game.system.combat import damage, flow, resources, stats
from tests import support


@pytest.fixture
def 미스트리스전장():
    """프리스트 -> 미스트리스 레벨 8(골드 스킬 전부, 녹슨 낫)과 귀검사, 고블린 셋(HP 999)."""
    rng.시드(5)
    상태 = support.새게임([("", "프리스트"), ("", "귀검사")])
    미, _ = 상태["파티"]["파티원"]
    support.성장(상태, 미, 8, 전직="미스트리스", 스킬습득=True)
    상태["소지품"]["장비"]["녹슨 낫"] = 1
    gf.장비_교체(상태, 미, "무기", "녹슨 낫")
    gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    적 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "적"),
        key=lambda p: p["대형위치"],
    )
    for p in 적:
        p["현재HP"] = p["최대HP"] = 999
    m = next(p for p in 전투상태["참가자"] if p["원본"] is 미)
    m["장비보너스"] = {}
    return 상태, 전투상태, 적, m


def _스킬(이름):
    return dict(gf.스킬데이터모음_생성()[이름], _이름=이름)


def _쓰기(전투상태, p, 이름, 대상=None):
    p["행동자원"].update(일반행동=1, 보조행동=1)
    p["현재MP"] = max(p["현재MP"], 50)
    return ss.스킬_실행(전투상태, p, 이름, _스킬(이름), 대상)


def _고정(monkeypatch, 눈=15):
    monkeypatch.setattr(stats.dice_utils, "d20_굴림", lambda 이점=False, 불리=False: 눈)
    monkeypatch.setattr(rng.주사위, "randint", lambda a, b: a)


def _내성_실패(monkeypatch):
    기록 = []

    def 가짜(보정치, 난이도, 이점=False, 불리=False):
        기록.append((난이도, 불리))
        return False, 1

    monkeypatch.setattr(stats.dice_utils, "내성_굴림", 가짜)
    return 기록


def _죄업(전투상태, p, 이름):
    resources.몬스터_버프_부여(전투상태, p, f"죄업 : {이름}", None)


def test_레벨6_특성_둘과_레벨8_일곱개의_대죄_골드_스킬(미스트리스전장):
    _, _, _, m = 미스트리스전장
    c = m["원본"]
    assert {"죄업에 짓눌린 육신", "짊어진 자의 낫 마스터리"} <= set(c["보유특성"])
    assert {
        "일곱개의 대죄",
        "길로틴",
        "롤링 러쉬",
        "러스트 핸드",
        "프라이드 악셀",
        "슬로스 바디",
    } <= set(c["보유스킬"])
    assert "훔쳐배우기스킬" in _스킬("롤링 러쉬")["타입"]
    for 이름 in ("러스트 핸드", "프라이드 악셀", "슬로스 바디"):
        assert "죄악" in _스킬(이름)["타입"]


def test_죄업에_짓눌린_육신은_어그로_5를_낮춘다():
    rng.시드(5)
    상태 = support.새게임([("", "프리스트")])
    c = 상태["파티"]["파티원"][0]
    support.성장(상태, c, 5)
    어그로 = c["어그로"]
    support.성장(상태, c, 6, 전직="미스트리스")
    assert c["어그로"] == 어그로 - 5


def test_낫_마스터리는_속도_5와_낫_무기공격력_1d10(미스트리스전장):
    _, 전투상태, _, m = 미스트리스전장
    무기 = m["장비데이터"]["무기"]
    assert stats.유효_무기공격력(전투상태, m, 무기) == "1d10"
    속도 = stats.속도보너스_합(전투상태, m)
    m["원본"]["보유특성"].remove("짊어진 자의 낫 마스터리")
    assert stats.속도보너스_합(전투상태, m) == 속도 - 5
    assert stats.유효_무기공격력(전투상태, m, 무기) == 무기["무기공격력"]


def test_죄업_쾌락_교만_탐욕_폭식_수치(미스트리스전장):
    _, 전투상태, _, m = 미스트리스전장
    AC = stats.최종AC(전투상태, m)
    방어 = stats.유효_방어력(전투상태, m)
    _죄업(전투상태, m, "쾌락")
    _죄업(전투상태, m, "교만")
    assert stats.버프디버프_수치(전투상태, m, "명중보너스") == 2
    assert stats.최종AC(전투상태, m) == AC - 2
    assert stats.버프디버프_수치(전투상태, m, "데미지보너스") == 2
    assert stats.유효_방어력(전투상태, m) == 방어 - 2
    수 = stats.속성_보정합(전투상태, m, "속성강화", "수속성")
    내성 = stats.속성_보정합(전투상태, m, "속성내성", "암속성")
    _죄업(전투상태, m, "탐욕")
    assert stats.속성_보정합(전투상태, m, "속성강화", "수속성") == 수 + 2
    assert stats.속성_보정합(전투상태, m, "속성내성", "암속성") == 내성 - 2
    치명 = damage.유효_치명타범위(전투상태, m)
    _죄업(전투상태, m, "폭식")
    assert damage.유효_치명타범위(전투상태, m) == 치명 - 1
    assert stats.버프디버프_수치(전투상태, m, "펌블범위") == 1
    # 죄업은 전투가 끝날 때까지 - 지속턴이 없다
    assert all(
        b.get("지속턴") is None for b in m["버프"] if b["이름"].startswith("죄업")
    )


def test_죄업_분노는_공격과_피격_모두_명중_이점(미스트리스전장, monkeypatch):
    _, 전투상태, 적, m = 미스트리스전장
    이점들 = []

    def d20(이점=False, 불리=False):
        이점들.append(이점)
        return 15

    monkeypatch.setattr(stats.dice_utils, "d20_굴림", d20)
    _죄업(전투상태, m, "분노")
    damage.명중_판정(전투상태, m, 적[0], "보정명중률")
    damage.명중_판정(전투상태, 적[0], m, "보정명중률")
    assert 이점들 == [True, True]


def test_죄업_질투는_적의_내성과_자신의_내성에_불리(미스트리스전장, monkeypatch):
    _, 전투상태, 적, m = 미스트리스전장
    기록 = _내성_실패(monkeypatch)
    _죄업(전투상태, m, "질투")
    stats.대상_내성굴림(전투상태, 적[0], "건강", 10, 시전자=m)
    stats.대상_내성굴림(전투상태, m, "건강", 10)
    stats.대상_내성굴림(전투상태, 적[1], "건강", 10)
    assert [불리 for _, 불리 in 기록] == [True, True, False]


def test_슬로스_바디는_죄업_나태로_슈퍼아머와_속도_5_감소(미스트리스전장, monkeypatch):
    _, 전투상태, 적, m = 미스트리스전장
    _고정(monkeypatch)
    기록 = _내성_실패(monkeypatch)
    속도 = stats.속도보너스_합(전투상태, m)
    결과 = _쓰기(전투상태, m, "슬로스 바디", 적[0])
    assert 결과["캐스팅"]
    assert m["캐스팅"]["밀림"]["우선도"] == -1
    assert m["현재MP"] == 40
    skill_run.캐스팅_발사(전투상태, m)
    assert any(s["이름"] == "둔화" for s in 적[0]["상태이상"])
    assert 기록[0][0] == 10 + stats.평타_능력치_보정치(전투상태, m)
    assert any(s["이름"] == "슈퍼아머" for s in m["상태이상"])
    assert stats.속도보너스_합(전투상태, m) == 속도 - 5


def test_러스트_핸드는_공중에뜸과_죄업_쾌락_보조행동(미스트리스전장, monkeypatch):
    _, 전투상태, 적, m = 미스트리스전장
    _고정(monkeypatch)
    기록 = _내성_실패(monkeypatch)
    _쓰기(전투상태, m, "러스트 핸드", 적[0])
    assert m["행동자원"]["보조행동"] == 0 and m["행동자원"]["일반행동"] == 1
    assert m["현재MP"] == 40
    assert any(s["이름"] == "공중에뜸" for s in 적[0]["상태이상"])
    assert 기록[0][0] == 10 + stats.평타_능력치_보정치(전투상태, m)
    assert any(b["이름"] == "죄업 : 쾌락" for b in m["버프"])


def test_프라이드_악셀은_매력_내성_AC_감소_3턴과_죄업_교만(미스트리스전장, monkeypatch):
    _, 전투상태, 적, m = 미스트리스전장
    _고정(monkeypatch)
    _내성_실패(monkeypatch)
    AC = stats.최종AC(전투상태, 적[0])
    _쓰기(전투상태, m, "프라이드 악셀", 적[0])
    assert stats.최종AC(전투상태, 적[0]) == AC - 1
    assert any(d["이름"] == "회피률감소" and d["지속턴"] == 3 for d in 적[0]["디버프"])
    assert any(b["이름"] == "죄업 : 교만" for b in m["버프"])


def test_일곱개의_대죄는_매_턴_죄악행동으로_죄악_스킬만(미스트리스전장):
    _, 전투상태, 적, m = 미스트리스전장
    _쓰기(전투상태, m, "일곱개의 대죄")
    flow.행동자원_채우기(전투상태, m)
    assert m["기타행동"]["죄악행동"] == 1
    m["현재MP"] = 50
    m["행동자원"]["보조행동"] = 0
    # 보조행동이 없어도 죄악행동으로 죄악 스킬을 쓴다
    assert ss.사용_가능여부(전투상태, m, _스킬("러스트 핸드"))[0]
    ss.스킬_실행(전투상태, m, "러스트 핸드", _스킬("러스트 핸드"), 적[0])
    assert m["기타행동"]["죄악행동"] == 0
    assert not ss.사용_가능여부(전투상태, m, _스킬("프라이드 악셀"))[0]


def test_낫_스킬은_낫을_들어야_쓴다(미스트리스전장):
    _, 전투상태, _, m = 미스트리스전장
    for 이름 in ("길로틴", "롤링 러쉬"):
        assert ss.사용_가능여부(전투상태, m, _스킬(이름))[0]
    m["장비데이터"]["무기"] = {**m["장비데이터"]["무기"], "타입": "십자가"}
    for 이름 in ("길로틴", "롤링 러쉬"):
        가능, 사유 = ss.사용_가능여부(전투상태, m, _스킬(이름))
        assert not 가능 and "낫" in 사유


def test_롤링_러쉬는_무기공격력_5회(미스트리스전장, monkeypatch):
    _, 전투상태, 적, m = 미스트리스전장
    _고정(monkeypatch)
    결과 = _쓰기(전투상태, m, "롤링 러쉬", 적[0])
    assert m["현재MP"] == 40
    assert len(결과["타격"]) == 5
    assert all(t["피해"] == 1 for t in 결과["타격"])  # 1d10 -> 1
    assert _스킬("롤링 러쉬")["일반공격취급"]


def test_길로틴은_적_전체를_치고_맞은_적_중_하나를_한_번_더(
    미스트리스전장, monkeypatch
):
    _, 전투상태, 적, m = 미스트리스전장
    _고정(monkeypatch)
    결과 = _쓰기(전투상태, m, "길로틴")
    assert len(결과["1단계"]["타격"]) == 3
    assert len(결과["2단계"]["타격"]) == 1
    assert sorted(999 - p["현재HP"] for p in 적) == [1, 1, 2]
    assert _스킬("길로틴")["공격단계1"]["명중보너스"] == -1


def test_길로틴_1단계가_모두_빗나가면_2단계는_없다(미스트리스전장, monkeypatch):
    _, 전투상태, 적, m = 미스트리스전장
    _고정(monkeypatch, 눈=1)
    결과 = _쓰기(전투상태, m, "길로틴")
    assert 결과["2단계"]["타격"] == []
