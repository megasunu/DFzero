"""무녀(053f) 전직 특성/스킬 규칙.

직업스타일 하이브리드. 레벨 6 "천녀기우제"(수속성강화 +1, 4라운드부터 전투 끝까지 비), "법력강화"(명중 +1, 캐스팅속도
+5), 레벨 8 버프 "신탁의 기원"(자신 데미지보너스 +2, 아군 보호률 +1 - 10%). 골드 스킬: 부적 구속제압부(훔쳐배우기,
(차수+1)d8+주문시전보정치, 경직)·심혼흡성부(적 전체 (차수)d4+주문시전보정치, 몹몰이), 염주를 들어야 쓰는 염주사출
(일반공격취급 MP 0)·목환자경(적 전체)·공력의 구(다음 자기 턴 시작에 같은 적을 백어택 - 그때까지 염주 스킬과
염주 일반공격 잠금)."""

import pytest

import gameflow as gf
from game.data.job_level import job_level_053f_shaman
from game.system import rng
from game.system import skill_system as ss
from game.system.combat import contribution, flow, hit, stats, traits
from tests import support


@pytest.fixture
def 무녀전장():
    """프리스트 -> 무녀 레벨 8(골드 스킬 전부 습득, 조악한 염주)과 귀검사, 고블린 셋(HP 999)."""
    rng.시드(5)
    상태 = support.새게임([("", "프리스트"), ("", "귀검사")])
    무, _ = 상태["파티"]["파티원"]
    support.성장(상태, 무, 8, 전직="무녀", 스킬습득=True)
    상태["소지품"]["장비"]["조악한 염주"] = 1
    gf.장비_교체(상태, 무, "무기", "조악한 염주")
    gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    적 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "적"),
        key=lambda p: p["대형위치"],
    )
    for p in 적:
        p["현재HP"] = p["최대HP"] = 999
    m = next(p for p in 전투상태["참가자"] if p["원본"] is 무)
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


def test_하이브리드이고_레벨6_특성_둘과_레벨8_신탁의_기원_골드_스킬(무녀전장):
    _, _, _, m = 무녀전장
    c = m["원본"]
    assert job_level_053f_shaman.직업스타일 == "하이브리드"
    assert {"천녀기우제", "법력강화"} <= set(c["보유특성"])
    assert {
        "신탁의 기원",
        "구속제압부",
        "심혼흡성부",
        "염주사출",
        "목환자경",
        "공력의 구",
    } <= set(c["보유스킬"])
    assert "훔쳐배우기스킬" in _스킬("구속제압부")["타입"]
    assert (
        "부적" in _스킬("구속제압부")["타입"] and "부적" in _스킬("심혼흡성부")["타입"]
    )


def test_천녀기우제는_수속성강화_1이고_4라운드부터_전투_끝까지_비(무녀전장):
    _, 전투상태, _, m = 무녀전장
    assert stats.속성_보정합(전투상태, m, "속성강화", "수속성") == 1
    assert not 전투상태.get("날씨")
    전투상태["라운드"] = 3
    flow.이니셔티브_재계산_및_정렬(전투상태)
    assert not 전투상태.get("날씨")
    전투상태["라운드"] = 4
    flow.이니셔티브_재계산_및_정렬(전투상태)
    assert 전투상태["날씨"]["이름"] == "비"
    for 라운드 in range(5, 15):
        전투상태["라운드"] = 라운드
        flow.이니셔티브_재계산_및_정렬(전투상태)
    assert 전투상태["날씨"]["이름"] == "비"
    assert stats.속성_보정합(전투상태, m, "속성강화", "수속성") == 2


def test_법력강화는_명중_1과_캐스팅속도_5(무녀전장):
    _, 전투상태, _, m = 무녀전장
    명중 = traits.특성_수치(전투상태, m, "명중보너스")
    assert traits.특성_수치(전투상태, m, "캐스팅속도") == 5
    m["원본"]["보유특성"].remove("법력강화")
    assert traits.특성_수치(전투상태, m, "명중보너스") == 명중 - 1


def test_신탁의_기원은_자신_데미지보너스_2와_아군_보호률_1(무녀전장):
    _, 전투상태, _, m = 무녀전장
    아군 = [p for p in 전투상태["참가자"] if p["진영"] == "아군"]
    동료 = next(p for p in 아군 if p is not m)
    mp = m["현재MP"] = 50
    m["행동자원"].update(일반행동=1, 보조행동=1)
    ss.스킬_실행(전투상태, m, "신탁의 기원", _스킬("신탁의 기원"))
    assert m["현재MP"] == mp  # 아군 버프라 MP 없음
    assert m["행동자원"]["일반행동"] == 1
    assert stats.버프디버프_수치(전투상태, m, "데미지보너스") == 2
    assert stats.버프디버프_수치(전투상태, 동료, "데미지보너스") == 0
    assert stats.유효_보호률(전투상태, m) == 1
    assert stats.유효_보호률(전투상태, 동료) == 1


def test_구속제압부는_주문_피해와_경직(무녀전장, monkeypatch):
    _, 전투상태, 적, m = 무녀전장
    _고정(monkeypatch)
    우선도, 이니 = 적[0]["우선도"], 적[0]["이니셔티브"]
    결과 = _쓰기(전투상태, m, "구속제압부", 적[0])
    assert m["현재MP"] == 40
    # (차수+1)d8 = 3d8 -> 3 + 주문시전보정치
    assert 결과["타격"][0]["피해"] == 3 + stats.주문시전_보정치(전투상태, m)
    # 경직 태그 - 경직량 5만큼 이니셔티브, 우선도는 그대로
    assert (적[0]["우선도"], 적[0]["이니셔티브"]) == (우선도, 이니 - 5)


def test_구속제압부는_차수_더하기_1_d8(무녀전장, monkeypatch):
    _, 전투상태, 적, m = 무녀전장
    _고정(monkeypatch)
    monkeypatch.setattr(rng.주사위, "randint", lambda a, b: b)  # 주사위 최대 눈
    결과 = _쓰기(전투상태, m, "구속제압부", 적[0])
    # 레벨 8 = 2차수 -> 3d8 최대 24
    assert 결과["타격"][0]["피해"] == 24 + stats.주문시전_보정치(전투상태, m)


def test_공력의_구는_일반공격취급이지만_추가공격을_열지_않는다(무녀전장):
    # 일반공격취급이고, 쓴 뒤 추가공격은 없고 다음 차례 백어택은 일반공격취급이 아니다
    _, 전투상태, 적, m = 무녀전장
    공력 = _스킬("공력의 구")
    assert 공력["일반공격취급"]
    assert not 공력["다음턴추가공격"]["일반공격취급"]
    assert m["원본"]["추가공격"] == 1
    _쓰기(전투상태, m, "공력의 구", 적[0])
    assert m["행동자원"]["일반행동"] == 0
    assert gf.추가행동_남은수(m) == 0


def test_심혼흡성부는_적_전체에_피해와_몹몰이(무녀전장, monkeypatch):
    _, 전투상태, 적, m = 무녀전장
    _고정(monkeypatch)
    결과 = _쓰기(전투상태, m, "심혼흡성부")
    assert m["현재MP"] == 30
    assert len(결과["타격"]) == 3
    assert all(any(s["이름"] == "몹몰이" for s in p["상태이상"]) for p in 적)


@pytest.mark.parametrize("스킬", ["염주사출", "목환자경", "공력의 구"])
def test_염주_스킬은_염주를_들어야_쓴다(무녀전장, 스킬):
    상태, 전투상태, _, m = 무녀전장
    assert ss.사용_가능여부(전투상태, m, _스킬(스킬))[0]
    m["장비데이터"]["무기"] = {**m["장비데이터"]["무기"], "타입": "십자가"}
    가능, 사유 = ss.사용_가능여부(전투상태, m, _스킬(스킬))
    assert not 가능 and "염주" in 사유


def test_염주사출은_MP_없이_주문_명중으로_무기공격력_더하기_주문시전보정치(
    무녀전장, monkeypatch
):
    _, 전투상태, 적, m = 무녀전장
    _고정(monkeypatch)
    결과 = _쓰기(전투상태, m, "염주사출", 적[0])
    assert m["현재MP"] == 50
    assert _스킬("염주사출")["일반공격취급"]
    assert _스킬("염주사출")["명중률"] == "주문시전명중률"
    # 염주 1d4 -> 1
    assert 결과["타격"][0]["피해"] == 1 + stats.주문시전_보정치(전투상태, m)


def test_목환자경은_적_전체를_친다(무녀전장, monkeypatch):
    _, 전투상태, 적, m = 무녀전장
    _고정(monkeypatch)
    결과 = _쓰기(전투상태, m, "목환자경")
    assert m["현재MP"] == 30
    assert len(결과["타격"]) == 3
    assert all(p["현재HP"] < 999 for p in 적)


def _무녀_차례까지(전투상태, m):
    for _ in range(20):
        다음 = ss.다음_턴(전투상태)
        if 다음 is m:
            return
    raise AssertionError("무녀 차례가 오지 않았다")


def test_공력의_구는_다음_자기_턴_시작에_같은_적을_백어택으로_한_번_더(
    무녀전장, monkeypatch
):
    상태, 전투상태, 적, m = 무녀전장
    _고정(monkeypatch)
    이점들 = []

    def d20(이점=False, 불리=False):
        이점들.append(이점)
        return 15

    monkeypatch.setattr(stats.dice_utils, "d20_굴림", d20)
    전투상태["현재턴"] = 전투상태["참가자"].index(m)
    _쓰기(전투상태, m, "공력의 구", 적[0])
    한번 = 999 - 적[0]["현재HP"]
    assert m["현재MP"] == 40
    assert 이점들 == [False]
    # 다음 자기 턴 시작까지 염주 스킬과 염주 일반공격을 못 쓴다
    가능, 사유 = ss.사용_가능여부(전투상태, m, _스킬("염주사출"))
    assert not 가능 and "공력의 구" in 사유
    assert not gf.일반공격_가능여부(상태, m)
    _무녀_차례까지(전투상태, m)
    assert 이점들[-1] is True  # 백어택 - 명중 이점
    assert 999 - 적[0]["현재HP"] == 한번 * 2
    assert ss.사용_가능여부(전투상태, m, _스킬("염주사출"))[0]
    assert gf.일반공격_가능여부(상태, m)


def test_공력의_구_2단계는_대상이_쓰러졌으면_나가지_않는다(무녀전장, monkeypatch):
    _, 전투상태, 적, m = 무녀전장
    _고정(monkeypatch)
    전투상태["현재턴"] = 전투상태["참가자"].index(m)
    _쓰기(전투상태, m, "공력의 구", 적[0])
    적[0]["현재HP"] = 0
    적[0]["생존"] = False
    로그수 = len(전투상태["로그"])
    _무녀_차례까지(전투상태, m)
    assert not any("공력의 구" in str(줄) for 줄 in 전투상태["로그"][로그수:])


# ------------------------------------------------------------------ 3차수 - 레벨 13 부동주박진, 골드 백팔염주


@pytest.fixture
def 무녀13():
    """프리스트 -> 무녀 레벨 13(3차수, 골드 스킬 전부, 조악한 염주 1d4)과 고블린 셋(HP 10**6), 무색 큐브 조각 5."""
    rng.시드(5)
    상태 = support.새게임([("", "프리스트")])
    c = 상태["파티"]["파티원"][0]
    support.성장(상태, c, 13, 전직="무녀", 스킬습득=True)
    상태["소지품"]["장비"]["조악한 염주"] = 1
    gf.장비_교체(상태, c, "무기", "조악한 염주")
    상태["소지품"]["재료"]["무색 큐브 조각"] = 5
    gf.전투_시작(상태, ["고블린", "고블린", "고블린"], 레벨=2, 차수=1)
    support.반응_처리(상태)
    전투상태 = 상태["전투상태"]
    적 = sorted(
        (p for p in 전투상태["참가자"] if p["진영"] == "적"),
        key=lambda p: p["대형위치"],
    )
    for p in 적:
        p.update(생존=True, 현재HP=10**6, 최대HP=10**6, 상태이상=[])
    m = next(p for p in 전투상태["참가자"] if p["원본"] is c)
    m["장비보너스"] = {}
    return 상태, 전투상태, 적, m


def test_레벨13에_부동주박진을_얻고_백팔염주는_11레벨부터_3차수_골드다(무녀13):
    _, _, _, m = 무녀13
    assert job_level_053f_shaman.레벨업테이블[13]["획득"]["획득스킬"] == ["부동주박진"]
    assert {"부동주박진", "백팔염주"} <= set(m["원본"]["보유스킬"])
    백팔 = _스킬("백팔염주")
    assert (백팔["습득방법"], 백팔["습득레벨"], 백팔["습득차수"]) == ("구매습득", 11, 3)
    assert (백팔["MP소모"], 백팔["공격횟수"], 백팔["공격타입"]) == (30, 108, "타격")
    for 이름 in ("부동주박진", "백팔염주"):
        assert _스킬(이름)["사용무기"] == "염주"


def test_부동주박진은_맞은_적만_피해와_경직이고_내성굴림은_명중과_상관없이(
    무녀13, monkeypatch
):
    상태, 전투상태, 적, m = 무녀13
    _고정(monkeypatch)
    맞을 = 적[0]["이름"]
    monkeypatch.setattr(
        hit,
        "명중_판정",
        lambda 전투상태, 공격자, 대상, *a, **kw: {
            "성공": 대상["이름"] == 맞을,
            "자연눈": 15,
            "치명타": False,
            "자동실패": False,
        },
    )
    난이도들 = []

    def 내성(보정치, 난이도, 이점=False, 불리=False):
        난이도들.append(난이도)
        return False, 1

    monkeypatch.setattr(stats.dice_utils, "내성_굴림", 내성)
    이니 = [p["이니셔티브"] for p in 적]
    결과 = _쓰기(전투상태, m, "부동주박진")
    assert m["현재MP"] == 20 and not 상태["소지품"]["재료"].get("무색 큐브 조각")
    # (차수+1)d4 = 4d4 -> 4 + 주문시전보정치, 맞은 적만
    assert [t["피해"] for t in 결과["타격"]] == [
        4 + stats.주문시전_보정치(전투상태, m),
        0,
        0,
    ]
    assert [p["이니셔티브"] for p in 적] == [이니[0] - 5, 이니[1], 이니[2]]
    # 빗나간 적도 내성굴림(DC 10+지능보정치)을 하고, 실패하면 구속·몹몰이 2턴
    지능 = stats.유효_능력치_보정치(전투상태, m, "지능")
    assert 난이도들 == [10 + 지능] * 3
    for p in 적:
        assert {s["이름"] for s in p["상태이상"]} >= {"구속", "몹몰이"}


@pytest.mark.parametrize(
    "눈, 감옥, 맞음",
    [(20, False, True), (19, False, False), (2, True, True), (1, True, False)],
)
def test_주사위20_명중은_눈_20에만_맞고_치명타가_아니다(
    무녀13, monkeypatch, 눈, 감옥, 맞음
):
    _, 전투상태, 적, m = 무녀13
    받은 = []

    def d20(이점=False, 불리=False):
        받은.append((이점, 불리))
        return 눈

    monkeypatch.setattr(stats.dice_utils, "d20_굴림", d20)
    monkeypatch.setattr(
        hit, "유효_치명타범위", lambda *a: 15
    )  # 치명타범위 확장도 보지 않는다
    if 감옥:
        적[0]["감옥"] = True
    판정 = hit.명중_판정(전투상태, m, 적[0], "주사위20", 명중보너스=30, 명중이점=True)
    assert (판정["성공"], 판정["치명타"]) == (맞음, False)
    assert 받은 == [(False, False)]  # 이점·불리점 없이 한 번
    if not 감옥:
        assert contribution.스킬_명중확률(전투상태, m, 적[0], "주사위20") == 1 / 20


def _백팔_기록(전투상태):
    return gf.로그_문장들(next(h for h in 전투상태["로그"] if h.get("명중만기록")))


def test_백팔염주는_적_하나당_10번까지_맞고_남은_공격은_버린다(무녀13, monkeypatch):
    _, 전투상태, 적, m = 무녀13
    _고정(monkeypatch, 눈=20)
    support.주사위고정(monkeypatch, 4)
    결과 = _쓰기(전투상태, m, "백팔염주")
    assert m["현재MP"] == 20
    친 = [t for t in 결과["타격"] if "판정" in t]
    assert len(친) == 30 and all(not t["판정"]["치명타"] for t in 친)
    for p in 적:
        assert sum(t["대상"] == p["이름"] for t in 친) == 10
    # (차수+1)d4 + 주문시전보정치 - (차수+3), 3차수 주사위 최대 -> 16 + 보정치 - 6
    assert {t["피해"] for t in 친} == {stats.주문시전_보정치(전투상태, m) + 10}
    줄들 = _백팔_기록(전투상태)
    assert 줄들[:2] == [f"{m['이름']}의 백팔염주!!", "30번 중 30번 명중!"]
    assert len(줄들) == 2 + 3  # 맞은 적마다 한 줄


def test_백팔염주는_빗나간_공격을_세지_않는다(무녀13, monkeypatch):
    _, 전투상태, 적, m = 무녀13
    _고정(monkeypatch)
    눈들 = iter([20, 1] * 54)
    monkeypatch.setattr(
        stats.dice_utils, "d20_굴림", lambda 이점=False, 불리=False: next(눈들)
    )
    결과 = _쓰기(전투상태, m, "백팔염주")
    친 = [t for t in 결과["타격"] if "판정" in t]
    assert (
        len(친) == 59
    )  # 30번째로 맞은 59번째 공격에서 모든 적이 10번 - 남은 공격은 버린다
    assert sum(t["판정"]["성공"] for t in 친) == 30
    줄들 = _백팔_기록(전투상태)
    assert 줄들[1] == "59번 중 30번 명중!"
    assert all("번 맞아" in 줄 for 줄 in 줄들[2:5])
