"""배틀메이지 - 체이서 얻기·최대·소모 순서, 체이서 사출·프레스, 체이서 밤, 콤보본능,
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


def _피해기록(monkeypatch):
    """피해_적용마다 (대상 이름, 양, 속성)을 남긴다."""
    from game.system.combat import damage

    기록 = []
    원래 = damage.피해_적용

    def 적용(전투상태, 대상, 양, **k):
        기록.append((대상["이름"], 양, k.get("속성")))
        return 원래(전투상태, 대상, 양, **k)

    monkeypatch.setattr(damage, "피해_적용", 적용)
    return 기록


def _체이서_넣기(p, *줄임):
    resources.체이서_소모(p)
    for s in 줄임:
        p["버프"].append({"이름": f"체이서 : {s}", "지속턴": None})


def test_체이서_프레스는_체이서를_모두_써서_적3체에_한_번에_피해를_합쳐_친다(
    monkeypatch,
):
    상태, p, 적 = _배틀메이지(monkeypatch)
    _체이서_넣기(p, "화", "수", "화")
    피해 = _피해기록(monkeypatch)
    시작 = len(상태["전투상태"]["로그"])
    gf.아군_스킬사용(상태, "체이서 프레스", 중심대상=적[1])
    assert _체이서수(p) == 0
    타격 = [
        e for e in 상태["전투상태"]["로그"][시작:] if e.get("스킬") == "체이서 프레스"
    ]
    assert len(타격) == 1 and len(타격[0]["타격"]) == 3, 타격
    assert sorted(이름 for 이름, _, _ in 피해) == sorted(q["이름"] for q in 적)
    assert {tuple(s) for _, _, s in 피해} == {("화속성", "수속성")}
    s = gf.스킬데이터모음_생성()["체이서 프레스"]
    assert (s["타겟"], s["체이서데미지"]) == ("적3체", "1d8+주문시전보정치")


def test_체이서_프레스_피해는_체이서마다_1d8과_주문시전보정치를_더한다(monkeypatch):
    from game.system.skill import skill_run

    상태, p, 적 = _배틀메이지(monkeypatch)
    _체이서_넣기(p, "명", "용")
    잡힌 = []
    원래 = skill_run.공격스킬_실행

    def 잡기(전투상태, 시전자, 스킬데이터, *a, **k):
        잡힌.append(스킬데이터)
        return 원래(전투상태, 시전자, 스킬데이터, *a, **k)

    monkeypatch.setattr(skill_run, "공격스킬_실행", 잡기)
    gf.아군_스킬사용(상태, "체이서 프레스", 중심대상=적[1])
    (한번,) = 잡힌
    assert 한번["데미지"] == "(1d8+주문시전보정치)+(1d8+주문시전보정치)"
    assert 한번["속성"] == [
        "명속성",
        "화속성",
        "수속성",
        "암속성",
    ]  # 드래곤 체이서는 네 속성


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


# ------------------------------------------------------------------ 3차수 - 황룡천공, 체이서 퀀타이즈


def test_황룡천공은_레벨13에_얻는다():
    from game.data.job_level import job_level_043f_battle_mage as 표

    assert 표.레벨업테이블[13]["획득"]["획득스킬"] == ["황룡천공"]
    rng.시드(5)
    상태 = 새게임([("", "마법사")])
    c = 상태["파티"]["파티원"][0]
    성장(상태, c, 12, 전직="배틀메이지", 스킬습득=True)
    assert "황룡천공" not in c["보유스킬"]
    성장(상태, c, 13)
    assert "황룡천공" in c["보유스킬"]


def test_황룡천공은_체이서를_드래곤_체이서로_바꿔_보정공격_뒤_하나씩_사출한다(
    monkeypatch,
):
    상태, p, 적 = _배틀메이지(monkeypatch, 레벨=13)
    상태["소지품"]["재료"]["무색 큐브 조각"] = 20
    _체이서_넣기(p, "화", "수")
    피해 = _피해기록(monkeypatch)
    시작 = len(상태["전투상태"]["로그"])
    gf.아군_스킬사용(상태, "황룡천공", 중심대상=적[0])
    assert _체이서수(p) == 0
    assert p["현재MP"] == 969 and 상태["소지품"]["재료"]["무색 큐브 조각"] == 15
    스킬들 = [e.get("스킬") for e in 상태["전투상태"]["로그"][시작:] if e.get("타격")]
    assert 스킬들 == [
        "황룡천공",
        "황룡천공 (드래곤 체이서)",
        "황룡천공 (드래곤 체이서)",
    ], 스킬들
    assert [이름 for 이름, _, _ in 피해] == [적[0]["이름"]] * 3
    assert all(
        sorted(s) == sorted(["화속성", "수속성", "명속성", "암속성"])
        for _, _, s in 피해[1:]
    )


def test_황룡천공은_대상이_쓰러지면_남은_드래곤_체이서를_남긴다(monkeypatch):
    from game.system.combat import damage

    상태, p, 적 = _배틀메이지(monkeypatch, 레벨=13)
    상태["소지품"]["재료"]["무색 큐브 조각"] = 20
    _체이서_넣기(p, "화", "수", "명")
    원래 = damage.피해_적용

    def 적용(전투상태, 대상, 양, **k):  # 첫 드래곤 체이서(네 속성)에 쓰러지게 한다
        if isinstance(k.get("속성"), list) and 대상 is 적[0]:
            대상["현재HP"] = 1
        return 원래(전투상태, 대상, 양, **k)

    monkeypatch.setattr(damage, "피해_적용", 적용)
    시작 = len(상태["전투상태"]["로그"])
    gf.아군_스킬사용(상태, "황룡천공", 중심대상=적[0])
    assert not 적[0]["생존"]
    스킬들 = [e.get("스킬") for e in 상태["전투상태"]["로그"][시작:] if e.get("타격")]
    assert 스킬들 == ["황룡천공", "황룡천공 (드래곤 체이서)"], 스킬들
    assert _체이서수(p) == 2  # 남은 드래곤 체이서는 사라지지 않는다


def test_황룡천공은_체이서가_없으면_쓸_수_없다(monkeypatch):
    상태, p, 적 = _배틀메이지(monkeypatch, 레벨=13)
    상태["소지품"]["재료"]["무색 큐브 조각"] = 20
    resources.체이서_소모(p)
    가능, 사유 = gf.스킬_사용_가능여부(상태, p, "황룡천공")
    assert not 가능 and "체이서" in 사유


def test_체이서_퀀타이즈는_배틀메이지_전용_3차수_퍽():
    from game.data.perks.perks_class_040f import 퍽목록

    퍽 = 퍽목록["체이서 퀀타이즈"]
    assert (퍽["차수"], 퍽["선행조건"], 퍽["획득특성"], 퍽["획득스킬"]) == (
        3, {"전직": "배틀메이지"}, "체이서 퀀타이즈", ["체이서 퀀타이즈"]
    )  # fmt: skip


def _퀀타이즈(monkeypatch, 켜기=True):
    상태, p, 적 = _배틀메이지(monkeypatch, 레벨=13)
    p["원본"]["보유특성"].append("체이서 퀀타이즈")
    p["원본"]["보유스킬"].append("체이서 퀀타이즈")
    if 켜기:
        gf.아군_스킬사용(상태, "체이서 퀀타이즈")
    return 상태, p, 적


def test_체이서_퀀타이즈를_켜면_체이서_사출에_보조행동이_들지_않는다(monkeypatch):
    상태, p, 적 = _퀀타이즈(monkeypatch)
    _체이서_넣기(p, "화", "수")
    보조 = p["행동자원"]["보조행동"]
    gf.아군_스킬사용(상태, "체이서 사출", 중심대상=적[0])
    # 손으로 쏜 사출이 명중해 하나가 더 저절로 나간다
    assert p["행동자원"]["보조행동"] == 보조 and _체이서수(p) == 0
    _체이서_넣기(p, "화")
    p["원본"]["켜진특성"].remove("체이서 퀀타이즈")  # 끈다(전환스킬은 턴당 한 번)
    gf.아군_스킬사용(상태, "체이서 사출", 중심대상=적[0])
    assert p["행동자원"]["보조행동"] == 보조 - 1


def test_체이서_퀀타이즈면_명중마다_그_적에게_자동_사출하고_연쇄하지_않는다(
    monkeypatch,
):
    상태, p, 적 = _퀀타이즈(monkeypatch)
    _체이서_넣기(p, "화", "수", "명")
    시작 = len(상태["전투상태"]["로그"])
    gf.아군_일반공격(상태, 적[1])
    자동 = [
        e
        for e in 상태["전투상태"]["로그"][시작:]
        if e.get("스킬") == "체이서 사출 (체이서 퀀타이즈)"
    ]
    # 일반공격 1번 명중에 사출 1번 - 사출의 명중으로 다시 나가면 체이서 셋을 다 쓴다
    assert len(자동) == 1 and _체이서수(p) == 2, 자동
    assert [t["대상"] for t in 자동[0]["타격"]] == [적[1]["이름"]]
    assert not p.get("자동사출대기")


def test_체이서_퀀타이즈가_꺼져_있으면_자동_사출하지_않는다(monkeypatch):
    상태, p, 적 = _퀀타이즈(monkeypatch, 켜기=False)
    _체이서_넣기(p, "화")
    gf.아군_일반공격(상태, 적[1])
    assert _체이서수(p) == 1 and not p.get("자동사출대기")


def test_체이서_밤이면_명중으로_체이서를_먼저_얻고_자동_사출한다(monkeypatch):
    상태, p, 적 = _퀀타이즈(monkeypatch)
    gf.아군_스킬사용(상태, "체이서 밤")
    resources.체이서_소모(p)
    gf.아군_일반공격(상태, 적[1])
    자동 = [
        e
        for e in 상태["전투상태"]["로그"]
        if e.get("스킬") == "체이서 사출 (체이서 퀀타이즈)" and e.get("타격")
    ]
    assert 자동, "체이서가 없던 상태에서도 명중으로 얻은 체이서를 쏜다"
