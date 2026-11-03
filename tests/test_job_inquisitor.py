"""이단심판관(052f) 전직 특성/스킬 규칙 (2026-11-02 사용자 결정, #512).

레벨 6 "심판관의 전투술"(화/명 속성강화 중 낮은 쪽이 높은 쪽을 따라가고 둘 다 +1), 레벨 8 버프 "광적인 믿음"
(치명타 범위·치명타 주사위 +1), 골드 스킬 성화(전투당 1회 - 2+2x차수 스택, 일반공격·일반공격취급 타격마다 1스택을
쓰고 화/명속성을 더하고 명중·피해 이점), 심판의 일격(보정공격력x2), 징벌의 일격(보정공격력x3), 플레게의 화염병
(명·화속성 주문 피해, 지혜 내성 실패 시 3턴 화상, 훔쳐배우기)."""

import pytest

import gameflow as gf
from game.system import rng
from game.system import skill_system as ss
from game.system.combat import damage, stats
from tests import support


@pytest.fixture
def 심판관전장():
    """프리스트 -> 이단심판관 레벨 8(골드 스킬 전부 습득)과 귀검사, 고블린 셋(HP 999)."""
    rng.시드(5)
    상태 = support.새게임([("", "프리스트"), ("", "귀검사")])
    심, _ = 상태["파티"]["파티원"]
    support.성장(상태, 심, 8, 전직="이단심판관", 스킬습득=True)
    gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    적 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "적"),
        key=lambda p: p["대형위치"],
    )
    for p in 적:
        p["현재HP"] = p["최대HP"] = 999
    s = next(p for p in 전투상태["참가자"] if p["원본"] is 심)
    s["장비보너스"] = {}
    return 상태, 전투상태, 적, s


def _스킬(이름):
    return dict(gf.스킬데이터모음_생성()[이름], _이름=이름)


def _쓰기(전투상태, p, 이름, 대상=None):
    p["행동자원"].update(일반행동=1, 보조행동=1)
    p["현재MP"] = max(p["현재MP"], 50)
    return ss.스킬_실행(전투상태, p, 이름, _스킬(이름), 대상)


def _속성_기록(monkeypatch):
    """피해_적용에 넘어간 속성을 모은다."""
    기록 = []
    원래 = damage.피해_적용

    def 가짜(*a, **k):
        기록.append(k.get("속성"))
        return 원래(*a, **k)

    monkeypatch.setattr(damage, "피해_적용", 가짜)
    return 기록


def _성화(p):
    return next((b for b in p["버프"] if b["이름"] == "성화"), None)


def test_레벨6에_특성을_레벨8에_광적인_믿음을_얻고_골드_스킬을_산다(심판관전장):
    _, _, _, s = 심판관전장
    c = s["원본"]
    assert "심판관의 전투술" in c["보유특성"]
    assert {
        "광적인 믿음",
        "성화",
        "심판의 일격",
        "징벌의 일격",
        "플레게의 화염병",
    } <= set(c["보유스킬"])


def test_플레게의_화염병은_명화속성_피해와_지혜_내성_실패시_3턴_화상(
    심판관전장, monkeypatch
):
    _, 전투상태, 적, s = 심판관전장
    monkeypatch.setattr(stats.dice_utils, "d20_굴림", lambda 이점=False, 불리=False: 15)
    monkeypatch.setattr(rng.주사위, "randint", lambda a, b: a)
    내성 = []

    def 가짜(보정치, 난이도, 이점=False, 불리=False):
        내성.append(난이도)
        return False, 1

    monkeypatch.setattr(stats.dice_utils, "내성_굴림", 가짜)
    속성들 = _속성_기록(monkeypatch)
    결과 = _쓰기(전투상태, s, "플레게의 화염병", 적[0])
    assert s["현재MP"] == 40
    보정치 = stats.주문시전_보정치(전투상태, s)
    # (차수+1)d8 = 3d8 -> 3 + 주문시전보정치, 화·명속성강화 1 -> x1.1 올림
    assert 결과["타격"][0]["피해"] == -(-(3 + 보정치) * 11 // 10)
    assert set(속성들[0]) == {"화속성", "명속성"}  # 피해_적용이 가장 아픈 쪽을 고른다
    assert 내성 == [10 + 보정치]
    화상 = [x for x in 적[0]["상태이상"] if x["이름"] == "화상"]
    assert 화상 and 화상[0]["지속턴"] == 3


def test_플레게의_화염병_주사위는_d12(심판관전장, monkeypatch):
    # 2026-11-03 사용자 결정 - (차수+1)d8에서 (차수+1)d12로
    _, 전투상태, 적, s = 심판관전장
    monkeypatch.setattr(stats.dice_utils, "d20_굴림", lambda 이점=False, 불리=False: 15)
    monkeypatch.setattr(rng.주사위, "randint", lambda a, b: b)  # 주사위 최대 눈
    결과 = _쓰기(전투상태, s, "플레게의 화염병", 적[0])
    보정치 = stats.주문시전_보정치(전투상태, s)
    # 3d12 최대 36 + 주문시전보정치, 화·명속성강화 1 -> x1.1 올림
    assert 결과["타격"][0]["피해"] == -(-(36 + 보정치) * 11 // 10)
