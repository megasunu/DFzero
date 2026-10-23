"""런처(032f) 전직 특성/스킬 규칙 (2026-10-23 사용자 결정).

레벨 6 "APG-63"(근력·치명타범위 +1), "중화기 마스터리"("중화기" 타입 스킬 명중·데미지보너스 +1), "듀얼 트리거"
(화/명 속성강화 중 낮은 쪽이 높은 쪽을 따라가고 둘 다 +1), 레벨 8 버프 "미라클 비전"(중화기 명중 +1, 피해 이점),
골드 스킬 슈타이어 대전차포(근력 명중 3회, 훔쳐배우기), 레이저 라이플(충전 - 캐스팅 우선도 -1), 양자폭탄(명중한
적에게 라운드가 끝날 때 피해, 민첩 내성 절반)."""

import itertools

import pytest

import gameflow as gf
from game.system import rng
from game.system import skill_system as ss
from game.system.combat import attacks, damage, stats
from tests import support


@pytest.fixture
def 런처전장():
    """거너 -> 런처 레벨 8(골드 스킬 전부 습득)과 귀검사, 고블린 셋(HP 999). 근력 16(보정치 3)."""
    rng.시드(5)
    상태 = support.새게임([("", "거너"), ("", "귀검사")])
    런, _ = 상태["파티"]["파티원"]
    support.성장(상태, 런, 8, 전직="런처", 스킬습득=True)
    gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    적 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "적"),
        key=lambda p: p["대형위치"],
    )
    for p in 적:
        p["현재HP"] = p["최대HP"] = 999
    r = next(p for p in 전투상태["참가자"] if p["원본"] is 런)
    r["원본"]["근력"] = 16
    r["장비보너스"] = {}  # 장비 데미지보너스 없이 센다
    return 상태, 전투상태, 적, r


def _스킬(이름):
    return dict(gf.스킬데이터모음_생성()[이름], _이름=이름)


def _쓰기(전투상태, p, 이름, 대상=None):
    p["행동자원"].update(일반행동=1, 보조행동=1)
    p["현재MP"] = max(p["현재MP"], 50)
    return ss.스킬_실행(전투상태, p, 이름, _스킬(이름), 대상)


def _굴림_기록(monkeypatch, 눈):
    """d20은 눈으로 고정하고, 피해 주사위는 전부 최솟값 1로 굴린다."""
    monkeypatch.setattr(stats.dice_utils, "d20_굴림", lambda 이점=False, 불리=False: 눈)
    monkeypatch.setattr(rng.주사위, "randint", lambda a, b: a)


def test_레벨6에_특성_셋을_레벨8에_미라클_비전을_얻고_골드_스킬을_산다(런처전장):
    _, _, _, r = 런처전장
    c = r["원본"]
    assert {"APG-63", "중화기 마스터리", "듀얼 트리거"} <= set(c["보유특성"])
    assert {"미라클 비전", "슈타이어 대전차포", "레이저 라이플", "양자폭탄"} <= set(
        c["보유스킬"]
    )


def test_슈타이어_대전차포는_훔쳐배우기_대상이다():
    assert "훔쳐배우기스킬" in _스킬("슈타이어 대전차포")["타입"]


def test_APG63은_근력과_치명타범위를_1씩_올린다(런처전장):
    _, 전투상태, _, r = 런처전장
    assert damage.유효_치명타범위(전투상태, r) == 19
    상태 = support.새게임([("", "거너")])
    c = 상태["파티"]["파티원"][0]
    support.성장(상태, c, 5)
    근력 = c["근력"]
    support.성장(상태, c, 6, 전직="런처")
    assert c["근력"] == 근력 + 1


def test_개틀링건과_화염방사기는_중화기다():
    assert "중화기" in _스킬("개틀링건")["타입"]
    assert "중화기" in _스킬("화염방사기")["타입"]


def test_중화기_마스터리는_중화기_스킬에만_명중과_데미지보너스_1(런처전장):
    _, 전투상태, _, r = 런처전장
    중화기 = ("스킬", "중화기")
    assert stats.스킬타입_조건_수치(전투상태, r, "명중보너스", 중화기) == 1
    assert stats.스킬타입_조건_수치(전투상태, r, "명중보너스", ("스킬",)) == 0
    assert stats.스킬타입_조건_수치(전투상태, r, "데미지보너스", 중화기) == 1


def test_중화기_마스터리_데미지보너스가_개틀링건_피해에_붙는다(런처전장, monkeypatch):
    _, 전투상태, 적, r = 런처전장
    _굴림_기록(monkeypatch, 15)
    결과 = _쓰기(전투상태, r, "개틀링건", 적[0])
    # 1d4(1) x (4+2x2) = 8, 중화기 마스터리 +1
    assert 결과["타격"][0]["피해"] == 9


def test_듀얼_트리거는_낮은_속성강화가_높은_쪽을_따라가고_둘_다_1_오른다(런처전장):
    _, 전투상태, _, r = 런처전장
    assert stats.속성_보정합(전투상태, r, "속성강화", "화속성") == 1
    assert stats.속성_보정합(전투상태, r, "속성강화", "명속성") == 1
    assert stats.속성_보정합(전투상태, r, "속성강화", "수속성") == 0
    # 명속성 강화 버프(+1)를 받으면 화속성도 같이 2
    r["버프"].append({"이름": "태양의 가호", "지속턴": 3})
    assert stats.속성_보정합(전투상태, r, "속성강화", "명속성") == 2
    assert stats.속성_보정합(전투상태, r, "속성강화", "화속성") == 2


def test_미라클_비전은_중화기_스킬에_명중_1과_피해_이점(런처전장):
    _, 전투상태, _, r = 런처전장
    중화기 = ("스킬", "중화기")
    assert not stats.피해이점인가(전투상태, r, 중화기)
    _쓰기(전투상태, r, "미라클 비전")
    assert stats.스킬타입_조건_수치(전투상태, r, "명중보너스", 중화기) == 2
    assert stats.스킬타입_조건_수치(전투상태, r, "명중보너스", ("스킬",)) == 0
    assert stats.피해이점인가(전투상태, r, 중화기)
    assert not stats.피해이점인가(전투상태, r, ("스킬",))
    지속 = {b["이름"]: b.get("지속턴") for b in r["버프"]}
    assert 지속["미라클 비전"] == 10
    assert r["행동자원"]["일반행동"] == 1  # 행동을 쓰지 않는다


def test_미라클_비전의_피해_이점은_두_번_굴려_높은_쪽(런처전장, monkeypatch):
    _, 전투상태, 적, r = 런처전장
    _쓰기(전투상태, r, "미라클 비전")
    monkeypatch.setattr(stats.dice_utils, "d20_굴림", lambda 이점=False, 불리=False: 15)
    눈들 = itertools.chain(
        [1, 4], itertools.repeat(1)
    )  # 개틀링건 1d4 - 첫 굴림 1, 이점 굴림 4
    monkeypatch.setattr(rng.주사위, "randint", lambda a, b: next(눈들))
    결과 = _쓰기(전투상태, r, "개틀링건", 적[0])
    assert 결과["타격"][0]["피해"] == 4 * 8 + 1


def test_슈타이어는_근력_명중으로_화속성_관통_3회(런처전장, monkeypatch):
    _, 전투상태, 적, r = 런처전장
    _굴림_기록(monkeypatch, 15)
    결과 = _쓰기(전투상태, r, "슈타이어 대전차포", 적[0])
    타격 = 결과["타격"]
    assert len(타격) == 3
    # (차수+1)d10 = 3d10 -> 3, 듀얼 트리거 화속성강화 1 -> x1.1 올림 4
    assert [t["피해"] for t in 타격] == [4, 4, 4]
    assert all(t["판정"]["성공"] for t in 타격)


def test_레이저_라이플은_충전으로_우선도만_1_내려가고_밀린_차례에_쏜다(런처전장):
    _, 전투상태, 적, r = 런처전장
    결과 = _쓰기(전투상태, r, "레이저 라이플", 적[0])
    assert 결과["캐스팅"]
    assert r["캐스팅"]["밀림"] == {"우선도": -1, "이니셔티브": 0}
    assert _스킬("레이저 라이플")["데미지"] == "(2차수+2)d12"


def test_양자폭탄은_명중한_적에게_라운드가_끝날_때_피해를_준다(런처전장, monkeypatch):
    _, 전투상태, 적, r = 런처전장
    _굴림_기록(monkeypatch, 15)
    결과 = _쓰기(전투상태, r, "양자폭탄")
    assert all(t["피해"] == 0 for t in 결과["타격"])
    assert all(p["현재HP"] == 999 for p in 적)
    monkeypatch.setattr(
        stats.dice_utils,
        "내성_굴림",
        lambda 보정치, 난이도, 이점=False, 불리=False: (False, 1),
    )
    assert attacks.라운드종료_지속공격(전투상태)
    # 3d12 = 3, 명속성강화 1 -> 4
    assert [999 - p["현재HP"] for p in 적] == [4, 4, 4]
    assert not any(s.get("종류") == "지속공격" for p in 적 for s in p["상태이상"])


def test_양자폭탄은_민첩_내성에_성공하면_절반(런처전장, monkeypatch):
    _, 전투상태, 적, r = 런처전장
    monkeypatch.setattr(stats.dice_utils, "d20_굴림", lambda 이점=False, 불리=False: 15)
    monkeypatch.setattr(rng.주사위, "randint", lambda a, b: b)
    _쓰기(전투상태, r, "양자폭탄")
    기록 = []

    def 가짜(보정치, 난이도, 이점=False, 불리=False):
        기록.append(난이도)
        return True, 20

    monkeypatch.setattr(stats.dice_utils, "내성_굴림", 가짜)
    attacks.라운드종료_지속공격(전투상태)
    assert 기록 == [13, 13, 13]  # 10 + 근력보정치 3
    # 3d12 = 36 -> 절반 18, 명속성강화 1 -> 19.8 올림 20
    assert [999 - p["현재HP"] for p in 적] == [20, 20, 20]


def test_양자폭탄이_빗나간_적은_라운드가_끝나도_맞지_않는다(런처전장, monkeypatch):
    _, 전투상태, 적, r = 런처전장
    _굴림_기록(monkeypatch, 1)
    _쓰기(전투상태, r, "양자폭탄")
    assert not attacks.라운드종료_지속공격(전투상태)
    assert all(p["현재HP"] == 999 for p in 적)
