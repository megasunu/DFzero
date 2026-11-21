"""스핏파이어 닐 스나이핑(레벨 13)과 버스터 샷(3차수 골드 스킬) 규칙(#801).

닐 스나이핑: 일반행동·MP 30·무색 큐브 조각 5. 쓴 라운드의 끝부터 3번, 라운드가 끝날 때마다 가장 강한 적
(보스 -> 네임드 -> 엘리트 -> 일반, 같으면 현재 HP가 낮은 적, 그것도 같으면 무작위)을 (차수)d8로 쏜다(명중 +2,
방어력·보호율 무시). 시전자가 쓰러져도 계속된다.
버스터 샷: 일반행동·MP 30, (차수+3)d8. 남은 장전 탄을 빗나가도 모두 쓰고, 명중하면 탄마다 (발 수 x 추가피해)를
더한다. 철갑탄 몫은 방어 무시, 작열탄 몫은 양옆에도, 상태이상은 탄 종류마다 한 번."""

import pytest

import gameflow as gf
from game.system import rng
from game.system import skill_system as ss
from game.system.combat import core, stats
from game.system.skill import skill_turn
from tests import support


@pytest.fixture
def 전장():
    """스핏파이어 레벨 13(골드 스킬 전부 습득)과 귀검사, 고블린 셋(HP 999, 저항 없음). 무색 큐브 조각 20."""
    rng.시드(5)
    상태 = support.새게임([("", "거너"), ("", "귀검사")])
    스핏, 귀 = 상태["파티"]["파티원"]
    support.성장(상태, 스핏, 13, 전직="스핏파이어", 스킬습득=True)
    support.성장(상태, 귀, 8, 전직="웨펀마스터")
    상태["소지품"]["재료"]["무색 큐브 조각"] = 20
    gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    적 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "적"),
        key=lambda p: p["대형위치"],
    )
    for p in 적:
        p["현재HP"] = p["최대HP"] = 999
        p["생존"] = True
        p["원본"] = {**p["원본"], "저항": [], "취약": [], "면역": []}
    s = next(p for p in 전투상태["참가자"] if p["원본"] is 스핏)
    s["장비보너스"] = {}
    s["현재MP"] = s["최대MP"] = 200
    return 상태, 전투상태, 적, s


def _스킬(이름):
    return dict(gf.스킬데이터모음_생성()[이름], _이름=이름)


def _쓰기(전투상태, p, 이름, 대상=None):
    p["행동자원"].update(일반행동=1, 보조행동=1)
    return ss.스킬_실행(전투상태, p, 이름, _스킬(이름), 대상)


def _굴림(monkeypatch, 눈):
    """명중 d20은 눈으로 고정, 피해 주사위는 전부 최댓값."""
    monkeypatch.setattr(stats.dice_utils, "d20_굴림", lambda 이점=False, 불리=False: 눈)
    monkeypatch.setattr(rng.주사위, "randint", lambda a, b: b)


def _장전(전투상태, p, 탄, 개수):
    ss.이름있는효과_부여(전투상태, p, f"장전 : {탄}", 개수)


def _장전들(p):
    return [i["이름"] for i in p["버프"] if i["이름"].startswith("장전 : ")]


def _버스터_피해(전투상태, s, 대상):
    전 = 대상["현재HP"]
    _쓰기(전투상태, s, "버스터 샷", 대상)
    피해 = 전 - 대상["현재HP"]
    대상["현재HP"] = 999
    return 피해


# ---------- 습득 ----------


def test_13레벨에_닐_스나이핑을_얻고_버스터_샷은_11레벨_150골드_골드_스킬이다(전장):
    상태, _, _, s = 전장
    assert "닐 스나이핑" in s["원본"]["보유스킬"]
    assert "버스터 샷" in s["원본"]["보유스킬"]
    데이터 = _스킬("버스터 샷")
    assert (데이터["습득레벨"], 데이터["습득차수"], 데이터["MP소모"]) == (11, 3, 30)


# ---------- 버스터 샷 ----------


def test_버스터_샷은_남은_탄마다_발_수만큼_추가피해를_더한다(전장, monkeypatch):
    _, 전투상태, 적, s = 전장
    _굴림(monkeypatch, 15)
    기본 = _버스터_피해(전투상태, s, 적[1])
    _장전(전투상태, s, "냉동탄", 2)
    _장전(전투상태, s, "은탄", 3)
    # 냉동탄 2발 x 1d8(최대 8) + 은탄 3발 x 1d4(최대 4)
    assert _버스터_피해(전투상태, s, 적[1]) - 기본 == 2 * 8 + 3 * 4
    assert _장전들(s) == []


def test_버스터_샷은_빗나가도_탄을_모두_쓴다(전장, monkeypatch):
    _, 전투상태, 적, s = 전장
    _굴림(monkeypatch, 1)
    _장전(전투상태, s, "철갑탄", 3)
    _장전(전투상태, s, "작열탄", 1)
    assert _버스터_피해(전투상태, s, 적[1]) == 0
    assert _장전들(s) == []


def test_버스터_샷의_작열탄_몫은_양옆에도_들어간다(전장, monkeypatch):
    _, 전투상태, 적, s = 전장
    _굴림(monkeypatch, 15)
    monkeypatch.setattr(stats.dice_utils, "내성_굴림", lambda *a, **k: (True, 20))
    _장전(전투상태, s, "작열탄", 2)
    _쓰기(전투상태, s, "버스터 샷", 적[1])
    # 양옆은 작열탄 2발 x 1d4(최대 4)만 받는다
    assert [999 - p["현재HP"] for p in (적[0], 적[2])] == [8, 8]


def test_버스터_샷의_상태이상은_탄_종류마다_한_번만_건다(전장, monkeypatch):
    _, 전투상태, 적, s = 전장
    _굴림(monkeypatch, 15)
    굴린 = []
    monkeypatch.setattr(
        stats.dice_utils, "내성_굴림", lambda *a, **k: 굴린.append(1) or (False, 1)
    )
    _장전(전투상태, s, "냉동탄", 3)
    _쓰기(전투상태, s, "버스터 샷", 적[1])
    assert len(굴린) == 1
    assert "빙결" in {i["이름"] for i in 적[1]["상태이상"]}


def test_버스터_샷의_철갑탄_몫은_방어를_무시한다(전장, monkeypatch):
    _, 전투상태, 적, s = 전장
    _굴림(monkeypatch, 15)
    monkeypatch.setattr(stats, "유효_방어력", lambda *a, **k: 0)
    기본 = _버스터_피해(전투상태, s, 적[1])
    _장전(전투상태, s, "철갑탄", 2)
    맨몸 = _버스터_피해(전투상태, s, 적[1]) - 기본
    monkeypatch.setattr(stats, "유효_방어력", lambda *a, **k: 5)
    기본 = _버스터_피해(전투상태, s, 적[1])
    _장전(전투상태, s, "철갑탄", 2)
    assert _버스터_피해(전투상태, s, 적[1]) - 기본 == 맨몸 == 2 * 8


# ---------- 닐 스나이핑 ----------


def test_닐_스나이핑은_MP30과_큐브5로_쓰고_쓸_때는_치지_않는다(전장, monkeypatch):
    상태, 전투상태, 적, s = 전장
    _굴림(monkeypatch, 15)
    _쓰기(전투상태, s, "닐 스나이핑")
    assert s["현재MP"] == 200 - 30
    assert 상태["소지품"]["재료"]["무색 큐브 조각"] == 15
    assert all(p["현재HP"] == 999 for p in 적)


def test_닐_스나이핑은_라운드_끝마다_3번_쏘고_방어를_무시한다(전장, monkeypatch):
    _, 전투상태, 적, s = 전장
    _굴림(monkeypatch, 15)
    monkeypatch.setattr(stats, "유효_방어력", lambda *a, **k: 50)
    _쓰기(전투상태, s, "닐 스나이핑")
    한발 = 8 * core.차수(s)
    for 회 in range(1, 5):
        skill_turn.라운드종료_처리(전투상태)
        # 같은 등급이면 HP가 낮은 적 - 처음 맞은 적을 계속 노린다
        assert sum(999 - p["현재HP"] for p in 적) == 한발 * min(회, 3)


def test_닐_스나이핑은_보스_네임드_엘리트_일반_순서로_노린다(전장, monkeypatch):
    _, 전투상태, 적, s = 전장
    _굴림(monkeypatch, 15)
    적[0]["원본"]["적등급"] = "엘리트"
    적[2]["원본"]["적등급"] = "네임드"
    적[2]["현재HP"] = 999
    _쓰기(전투상태, s, "닐 스나이핑")
    skill_turn.라운드종료_처리(전투상태)
    assert [p["현재HP"] < 999 for p in 적] == [False, False, True]
    적[1]["원본"]["칭호"] = "보스"
    skill_turn.라운드종료_처리(전투상태)
    assert 적[1]["현재HP"] < 999


def test_닐_스나이핑은_등급이_같으면_HP가_낮은_적을_노린다(전장, monkeypatch):
    _, 전투상태, 적, s = 전장
    _굴림(monkeypatch, 15)
    적[2]["현재HP"] = 500
    _쓰기(전투상태, s, "닐 스나이핑")
    skill_turn.라운드종료_처리(전투상태)
    assert 적[2]["현재HP"] < 500 and 적[0]["현재HP"] == 적[1]["현재HP"] == 999


def test_닐_스나이핑은_빗나갈_수_있고_명중_2를_받는다(전장, monkeypatch):
    _, 전투상태, 적, s = 전장
    assert _스킬("닐 스나이핑")["명중보너스"] == 2
    _굴림(monkeypatch, 1)
    _쓰기(전투상태, s, "닐 스나이핑")
    skill_turn.라운드종료_처리(전투상태)
    assert all(p["현재HP"] == 999 for p in 적)


def test_닐_스나이핑은_시전자가_쓰러져도_계속된다(전장, monkeypatch):
    _, 전투상태, 적, s = 전장
    _굴림(monkeypatch, 15)
    _쓰기(전투상태, s, "닐 스나이핑")
    s["현재HP"] = 0
    s["생존"] = False
    skill_turn.라운드종료_처리(전투상태)
    assert sum(999 - p["현재HP"] for p in 적) == 8 * core.차수(s)
