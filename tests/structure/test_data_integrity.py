"""데이터 무결성 - 데이터(game/data) 안의 수식과 이름 참조가 실제로 읽히는지 검사한다.

런타임은 일부러 관대하다: 평가할 수 없는 수식은 0/기본값으로 바뀌고(combat.participants/monster_actions/
traits, loot_system), 정의 없는 특성 이름은 건너뛴다(traits._특성_목록). "아직 미정인 데이터"를 견디려는
설계지만, 그래서 데이터 오타가 오류 없이 효과 없음이 된다(구조 점검 W-3). 이 파일이 그 안전망이다 - 런타임은
그대로 두고, 데이터가 읽히는지를 테스트에서 엄격하게 확인한다. 의도된 예외는 허용 목록에 이유와 함께 적는다.
허용 목록의 항목이 더는 필요 없어지면(데이터가 고쳐지면) 테스트가 목록에서 지우라고 알려 준다.
"""

import collections
import importlib
import pathlib
import pkgutil
import re
import sys

import pytest

import game.data as 데이터패키지
from game.system import equipment_system, rng
import gameflow as gf
from game.data.collection.collection_monster import 도감_출현장소
from game.data.equipment.eq_00_magic_seal import 마봉능력, 봉인장비_해제이름
from game.data.buff.buff import 버프목록
from game.data.buff.status_effects import 상태이상목록
from game.system.combat import formula

루트 = pathlib.Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- 수식


# 수식이 들어 있는 데이터 키. 키 이름을 목록으로 둔 이유: 문자열 값 중 무엇이 수식인지는
# 키로만 알 수 있다(설명 문구에도 숫자가 있다). 새 수식 키가 생기면 여기에 더한다.
수식_키 = {
    "데미지",
    "무기공격력",
    "난이도",
    "속도",
    "수식",
    "변동값",
    "회복량",
    "최대값",
    "최대HP",
    "AC",
    "공격횟수",
    "회피보너스",
    "임시생명력",
    "이니셔티브보너스",
    "실패시데미지",
    "명중보너스",
    "중첩량",
    "추가피해",
    "휴식당횟수",
    "해제개수",
    "획득골드",
    "최대MP",
    "지속턴",
    "수치",
    "분신수",
    "근력",
    "재굴림",
    "변경",
    "기존",
    "데미지보너스",
    "명중률보너스",
    "속도보너스",
}

# 수식_평가가 모르는 변수지만 호출하는 쪽이 먼저 숫자로 바꿔서 넘기는 것들.
# 새 변수를 여기 더하려면 그 호출 쪽이 실제로 치환하는지 확인한다.
호출쪽_치환 = {
    "중첩수": "2",  # combat/stats.py 버프디버프_수치 - 상태이상 중첩량
    "고블린수": "3",  # combat/traits.py - "집계조건"으로 센 필드의 몬스터 수
}

수식_컨텍스트 = {
    "차수": 2,
    "레벨": 5,
    "보정치": 1,
    "주문시전보정치": 3,
    "스타일성장횟수": 1,
    "대상상태이상수": 2,
    "무기공격력": "1d8",
    "추가공격": 1,
    "능력치": {이름: 14 for 이름 in ("근력", "민첩", "건강", "지능", "지혜", "매력")},
}


def _데이터_모듈들():
    for 정보 in pkgutil.walk_packages(데이터패키지.__path__, "game.data."):
        yield importlib.import_module(정보.name)


def _수식_모으기():
    """{(키, 문자열): [모듈이름, ...]} - 수식 키 아래의 숫자/변수가 든 문자열 값."""
    찾음 = collections.defaultdict(set)

    def 걷기(값, 키, 모듈):
        if isinstance(값, dict):
            for k, v in 값.items():
                걷기(v, k if isinstance(k, str) else 키, 모듈)
        elif isinstance(값, (list, tuple)):
            for v in 값:
                걷기(v, 키, 모듈)
        elif (
            isinstance(값, str)
            and 키 in 수식_키
            and re.search(r"\d|차수|보정치|레벨", 값)
        ):
            찾음[(키, 값)].add(모듈)

    for 모듈 in _데이터_모듈들():
        for 이름, 값 in vars(모듈).items():
            if 이름.startswith("__") or isinstance(값, type) or callable(값):
                continue
            if isinstance(값, type(sys)):  # 다른 모듈 참조
                continue
            걷기(값, 이름, 모듈.__name__)
    return 찾음


def test_데이터의_모든_수식이_엄격하게_평가된다():
    수식들 = _수식_모으기()
    # 수집이 깨지면(키 이름이 바뀌는 등) 검사가 조용히 비는 일을 막는다
    assert len(수식들) >= 90, f"수식을 {len(수식들)}개만 찾았다 - 수집 로직을 확인한다"

    실패 = []
    for (키, 값), 모듈들 in sorted(수식들.items()):
        식 = 값
        for 변수, 숫자 in 호출쪽_치환.items():
            식 = 식.replace(변수, 숫자)
        try:
            rng.시드(0)
            결과 = formula.수식_평가(식, dict(수식_컨텍스트))
        except Exception as 오류:  # noqa: BLE001 - 어떤 실패든 데이터 문제로 보고한다
            실패.append(
                f"{키}: {값!r} -> {type(오류).__name__}: {오류} ({sorted(모듈들)[0]})"
            )
            continue
        assert isinstance(결과, (int, float)), (키, 값, 결과)
    assert not 실패, (
        "런타임이 조용히 0/기본값으로 바꿀 수식이 있다 - 데이터를 고치거나, 호출 쪽이 먼저 치환하는 "
        "변수라면 호출쪽_치환에 더한다:\n" + "\n".join(실패)
    )


def test_호출쪽_치환_변수는_실제_데이터에서_쓰인다():
    """쓰이지 않는 변수가 목록에 남아 있으면 나중에 오타를 가릴 수 있다."""
    수식들 = _수식_모으기()
    for 변수 in 호출쪽_치환:
        assert any(변수 in 값 for (_, 값) in 수식들), (
            f"{변수}는 데이터에 없다 - 목록에서 지운다"
        )


# --------------------------------------------------------------- 드랍표
# 런타임(loot_system)은 없는 표 이름/아이템 이름을 조용히 건너뛴다(드랍 없음, 카탈로그에 없는
# 이름은 지급 안 함) - 오타가 "안 떨어짐"이 되므로 여기서 잡는다. "미정"은 아직 안 정한 값.


def _드랍표_본문들(표):
    if 표.get("타입") == "차수별":
        return list((표.get("차수표") or {}).values())
    return [표]


def test_드랍표의_아이템과_표_참조는_실제로_있고_순환하지_않는다():
    from game.data.monster.monster_drop import 드랍표_모음

    카탈로그 = gf._상점_카탈로그_생성()
    아이템 = {n for 대분류 in 카탈로그.values() for 탭 in 대분류.values() for n in 탭}
    문제 = []
    가리킴 = collections.defaultdict(set)
    for 표이름, 표 in 드랍표_모음.items():
        for 본문 in _드랍표_본문들(표):
            for 항목 in 본문.get("아이템", []):
                if "드랍표" in 항목:
                    가리킴[표이름].add(항목["드랍표"])
                    if 항목["드랍표"] not in 드랍표_모음:
                        문제.append(f"{표이름}: 없는 드랍표 {항목['드랍표']}")
                elif "아이템이름" in 항목:
                    if 항목["아이템이름"] not in 아이템 | {"미정"}:
                        문제.append(
                            f"{표이름}: 카탈로그에 없는 아이템 {항목['아이템이름']}"
                        )
                elif not isinstance(항목.get("아이템조건"), dict):
                    문제.append(f"{표이름}: 아이템 지정이 없는 항목 {항목}")
    for 이름, 몬스터 in gf.몬스터목록.items():
        for 참조 in 몬스터.get("드랍표") or []:
            if 참조["이름"] not in 드랍표_모음 and 참조["이름"] != "미정":
                문제.append(f"몬스터 {이름}: 없는 드랍표 {참조['이름']}")
    for 파일, 맵 in gf.던전_레지스트리.items():
        for 참조 in 맵.get("드랍표") or []:
            if 참조["이름"] not in 드랍표_모음:
                문제.append(f"던전 {파일}: 없는 드랍표 {참조['이름']}")

    def 순환(시작, 지금, 지나온):
        for 다음 in 가리킴.get(지금, ()):
            if 다음 == 시작 or (
                다음 not in 지나온 and 순환(시작, 다음, 지나온 | {다음})
            ):
                return True
        return False

    문제 += [
        f"{이름}: 드랍표가 순환한다" for 이름 in 가리킴 if 순환(이름, 이름, {이름})
    ]
    assert not 문제, "\n".join(문제)


# 공격 연출 모양 - combat.element.공격연출_종류 / stats.타격_공격타입
_공격타입_값 = {"참격", "타격", "관통", "역장", "마법"}


def _데미지_딕셔너리들(값, 경로=()):
    if isinstance(값, dict):
        if "데미지" in 값 or "실패시데미지" in 값:
            yield 경로, 값
        for 키, 하위 in 값.items():
            yield from _데미지_딕셔너리들(하위, 경로 + (키,))
    elif isinstance(값, (list, tuple)):
        for 번호, 하위 in enumerate(값):
            yield from _데미지_딕셔너리들(하위, 경로 + (번호,))


def _연출이_없는_피해(경로, 항목):
    """연출 모양이 필요 없는 피해: 무기 주사위(무기의 공격타입을 따른다), 본 피해에 더하는
    속성추가피해. 명중 굴림이 없는 피해(내성 피해, 자폭)도 연출이 뜬다."""
    값 = 항목.get("데미지", 항목.get("실패시데미지"))
    식 = str(값)
    return (
        값 in (None, 0, "0")
        or "보정공격력" in 식
        or "무기공격력" in 식
        or "속성추가피해" in 경로
    )


def test_명중_굴림이_있는_공격은_모두_공격타입을_적는다():
    """무기 주사위를 쓰지 않는 공격(스킬/몬스터 패턴/소환수 행동/투척 아이템/특성 공격,
    명중 굴림이 없는 내성 피해·자폭 포함)은 "공격타입"이 있어야 연출 모양이 정해진다.
    자리는 "데미지"(내성 패턴은 "실패시데미지") 바로 다음."""
    빠짐, 틀린값, 자리 = [], [], []
    for 모듈 in _데이터_모듈들():
        for 이름, 값 in vars(모듈).items():
            if 이름.startswith("_"):
                continue
            for 경로, 항목 in _데미지_딕셔너리들(값, (모듈.__name__, 이름)):
                if "공격타입" in 항목:
                    if 항목["공격타입"] not in _공격타입_값:
                        틀린값.append((경로, 항목["공격타입"]))
                    키들 = list(항목)
                    앞 = "데미지" if "데미지" in 항목 else "실패시데미지"
                    if 키들.index("공격타입") != 키들.index(앞) + 1:
                        자리.append(경로)
                elif not _연출이_없는_피해(경로, 항목):
                    빠짐.append(경로)
    assert not 빠짐, 빠짐
    assert not 틀린값, 틀린값
    assert not 자리, 자리


def test_무기는_모두_공격타입을_적는다():
    무기들 = [
        항목
        for 모듈 in _데이터_모듈들()
        if 모듈.__name__.split(".")[-1].startswith("eq_01_weapon_0")
        for 값 in vars(모듈).values()
        if isinstance(값, dict)
        for 항목 in 값.values()
        if isinstance(항목, dict) and "무기능력치" in 항목
    ]
    assert len(무기들) >= 50
    assert all(항목.get("공격타입") in _공격타입_값 for 항목 in 무기들), [
        (항목.get("이름"), 항목.get("공격타입")) for 항목 in 무기들
    ]


def _직업별_무기목록():
    """{모듈이름: 무기목록} - eq_01_weapon_010~050의 최상위 무기 딕셔너리."""
    결과 = {}
    for 모듈 in _데이터_모듈들():
        이름 = 모듈.__name__.split(".")[-1]
        if not 이름.startswith("eq_01_weapon_0"):
            continue
        for 값 in vars(모듈).values():
            if (
                isinstance(값, dict)
                and 값
                and all(isinstance(v, dict) and "무기능력치" in v for v in 값.values())
            ):
                결과[이름] = 값
    return 결과


def test_무기_이름은_직업_목록을_가로질러_겹치지_않는다():
    """상점 카탈로그는 5직업 무기를 한 사전으로 합치므로(ctl_party._상점_카탈로그_생성) 같은 이름은 하나만 남는다."""
    주인 = collections.defaultdict(list)
    for 모듈이름, 목록 in _직업별_무기목록().items():
        for 키, 항목 in 목록.items():
            assert 키 == 항목["이름"], (모듈이름, 키)
            주인[키].append(모듈이름)
    assert len(주인) >= 50
    assert not {이름: 곳 for 이름, 곳 in 주인.items() if len(곳) > 1}


def _이름_붙은(목록, 종류, 레어도, 티어):
    """그 종류의 이름 붙은 일반 무기(미정_·마법으로 봉인된·성물: 이 아닌 그 레어도·티어) - 없으면 None.
    보스유니크(크로쿠타의 가시)도 종류는 타입 맨 앞이다."""
    return next(
        (
            항목
            for 이름, 항목 in 목록.items()
            if equipment_system.무기_종류(항목) == 종류
            and 항목["레어도"] == 레어도
            and 항목["티어"] == 티어
            and not 이름.startswith(("미정_", "마법으로 봉인된 ", "성물:"))
        ),
        None,
    )


def test_소검_둔기를_뺀_무기_종류마다_미정_레어와_유니크가_있다():
    """일반 레어(티어1, 명중 기본+1)와 일반/성물 유니크(티어2, 명중 기본+2) 자리 - 이름은 미정_(레어도or성물)_(무기)
    . 소검(산들바람/성물:로켈의 글라디우스)과 둔기(공어 가시 클럽)는 넣지 않는다.
        기본값은 그 종류의 커먼 무기, 데미지보너스는 커먼 등급 페널티 없이 0.
        레어·유니크 자리는 이름과 고유 효과가 정해지면 그 무기로 바뀐다(유니크는 크로쿠타의 가시) -
        그때는 종류·레어도·티어·명중만 본다."""
    빠짐, 틀림 = [], []
    종류수 = 0
    for 모듈이름, 목록 in _직업별_무기목록().items():
        for 기본 in 목록.values():
            if 기본["레어도"] != "커먼":
                continue
            종류 = 기본["타입"]
            for 접두, 레어도, 티어, 명중가산 in (
                ("레어", "레어", 1, 1),
                ("유니크", "유니크", 2, 2),
                ("성물", "유니크", 2, 2),
            ):
                이름 = f"미정_{접두}_{종류}"
                항목 = 목록.get(이름)
                if 종류 in ("소검", "둔기"):
                    if 항목 is not None:
                        틀림.append((이름, "넣지 않는 종류"))
                    continue
                정해짐 = (
                    항목 is None
                    and 접두 in ("레어", "유니크")
                    and _이름_붙은(목록, 종류, 레어도, 티어)
                )
                if 정해짐:
                    if 정해짐["명중률보너스"] != 기본["명중률보너스"] + 명중가산:
                        틀림.append((정해짐["이름"], "명중률보너스"))
                    continue
                if 항목 is None:
                    빠짐.append((모듈이름, 이름))
                    continue
                기대 = {
                    **{
                        k: 기본[k]
                        for k in (
                            "분류",
                            "타입",
                            "공격타입",
                            "속성",
                            "무기능력치",
                            "무기공격력",
                        )
                    },
                    **{k: 기본[k] for k in ("스탯보너스", "AC보너스")},
                    "이름": 이름,
                    "레어도": 레어도,
                    "티어": 티어,
                    "데미지보너스": 0,
                    "명중률보너스": 기본["명중률보너스"] + 명중가산,
                    "속도보너스": 0,
                }
                다름 = {
                    k: (항목.get(k), v) for k, v in 기대.items() if 항목.get(k) != v
                }
                if 다름:
                    틀림.append((이름, 다름))
            종류수 += 종류 not in ("소검", "둔기")
    assert 종류수 == 23
    assert not 빠짐, 빠짐
    assert not 틀림, 틀림


def test_마봉능력의_부위_버프_상태이상_참조는_실제로_있다():
    """마봉능력(eq_00_magic_seal.py)은 아직 게임 코드가 안 쓴다 - 오타는 여기서만 잡힌다."""
    장비탭 = set(gf.상점_탭목록("장비"))
    속성들 = {"전체", "화속성", "수속성", "명속성", "암속성"}
    for 이름, 능력 in 마봉능력.items():
        assert 능력["부위"] and set(능력["부위"]) <= 장비탭, 이름
        assert 능력["효과"] and 능력["설명"], 이름
        for 효과 in 능력["효과"]:
            if "버프" in 효과:
                assert 효과["버프"] in 버프목록, (이름, 효과)
            if "상태이상" in 효과:
                assert 효과["상태이상"] in 상태이상목록, (이름, 효과)
                # 저주만 지혜 내성
                기대 = "지혜" if 효과["상태이상"] == "저주" else "건강"
                assert 효과["내성"]["능력치"] == 기대, 이름
            if "속성" in 효과:
                assert 효과["속성"] in 속성들, (이름, 효과)
            if "발동" in 효과:
                assert 효과["발동"] in ("턴시작", "공격", "명중"), (이름, 효과)
    # 봉인된 장비마다 그 부위에 나올 수 있는 마봉능력이 있다
    카탈로그 = gf.새_게임_시작([("", "귀검사")])["상점카탈로그"]["장비"]
    for 탭, 아이템들 in 카탈로그.items():
        for 봉인 in (n for n in 아이템들 if n in 봉인장비_해제이름):
            assert any(탭 in 능력["부위"] for 능력 in 마봉능력.values()), (탭, 봉인)


def test_레벨8_버프스킬은_모든_직업에서_휴식당_1회다():
    # 모든 직업의 레벨 8 버프 스킬은 휴식당 1회
    import game.data.job_level as 레벨패키지

    스킬정의 = gf.스킬데이터모음_생성()
    검사한것 = []
    for 모듈정보 in pkgutil.iter_modules(레벨패키지.__path__):
        모듈 = importlib.import_module(f"game.data.job_level.{모듈정보.name}")
        획득 = (getattr(모듈, "레벨업테이블", {}).get(8) or {}).get("획득") or {}
        for 이름 in 획득.get("획득스킬") or []:
            if 스킬정의[이름]["분류"] == "버프스킬":
                검사한것.append(이름)
                assert 스킬정의[이름].get("휴식당횟수") == 1, 이름
                # 설명은 드는 MP를 적는다(폭주가 빠졌었다)
                MP = 스킬정의[이름].get("MP소모")
                if MP:
                    assert f"MP {MP}" in 스킬정의[이름]["설명"], 이름
    assert {"오버드라이브", "잔영의 케이가", "강권"} <= set(검사한것)


def test_퍽은_분류가_퍽이고_타입에_처리종류가_하나다():
    """퍽 구조: "분류"는 모두 "퍽", 처리 종류(특성획득/스킬획득/스탯획득/일반퍽)는 "타입" 리스트에
    정확히 하나 - 레벨업 처리(character_levelup_system.퍽_처리타입)가 그것으로 갈라진다."""
    from game.system.character_levelup_system import 퍽_처리타입목록

    틀림 = []
    for 모듈이름 in ("0000", "010m", "020f", "030f", "040f", "050f"):
        모듈 = importlib.import_module(f"game.data.perks.perks_class_{모듈이름}")
        for 이름, 정의 in 모듈.퍽목록.items():
            타입 = 정의.get("타입")
            if (
                정의.get("분류") != "퍽"
                or not isinstance(타입, list)
                or sum(t in 퍽_처리타입목록 for t in 타입) != 1
            ):
                틀림.append((모듈이름, 이름, 정의.get("분류"), 타입))
    assert 틀림 == []


_퍽_선행조건_키 = {"특성보유", "스킬보유", "전직", "가용무기", "최소능력치"}


def test_퍽_선행조건과_획득스킬_형태():
    """ "선행조건"은 None 또는 아는 키 하나의 사전 - 모르는 키는 판정(ctl_levelup._선행조건_만족)을
    조용히 통과한다. "획득스킬"은 스킬획득 퍽이면 꼭 글자 하나, 특성획득 퍽이면 글자의 목록(광기)."""
    from game.system.character_levelup_system import 퍽_처리타입

    틀림 = []
    for 모듈이름 in ("0000", "010m", "020f", "030f", "040f", "050f"):
        모듈 = importlib.import_module(f"game.data.perks.perks_class_{모듈이름}")
        for 이름, 정의 in 모듈.퍽목록.items():
            조건 = 정의.get("선행조건")
            if 조건 is not None and not (
                isinstance(조건, dict)
                and len(조건) == 1
                and set(조건) <= _퍽_선행조건_키
            ):
                틀림.append((모듈이름, 이름, "선행조건", 조건))
            if not _퍽_획득스킬_형태_맞음(정의, 퍽_처리타입(정의)):
                틀림.append((모듈이름, 이름, "획득스킬", 정의.get("획득스킬")))
    assert 틀림 == []


def _퍽_획득스킬_형태_맞음(정의, 처리):
    """스킬획득 퍽은 "획득스킬"이 꼭 글자 하나 - 빠지거나 None이면 엔진이 None을 보유스킬에 넣는다.
    특성획득 퍽은 없어도 되고, 있으면 글자의 목록(광기)."""
    if 처리 == "스킬획득":
        return isinstance(정의.get("획득스킬"), str)
    if "획득스킬" not in 정의:
        return True
    값 = 정의["획득스킬"]
    return (
        처리 == "특성획득"
        and isinstance(값, list)
        and all(isinstance(v, str) for v in 값)
    )


def test_스킬획득_퍽은_획득스킬이_빠지거나_None이면_틀림():
    """얻는 순간 고르는 퍽("획득스킬": None)은 엔진이 지원하지 않는다."""
    assert _퍽_획득스킬_형태_맞음({"획득스킬": "디스인챈트"}, "스킬획득")
    assert not _퍽_획득스킬_형태_맞음({"획득스킬": None}, "스킬획득")
    assert not _퍽_획득스킬_형태_맞음({}, "스킬획득")
    assert _퍽_획득스킬_형태_맞음({}, "특성획득")
    assert _퍽_획득스킬_형태_맞음({"획득스킬": ["프렌지 전환"]}, "특성획득")
    assert not _퍽_획득스킬_형태_맞음({"획득스킬": "프렌지 전환"}, "특성획득")


def test_특성의_면역은_효과_원소로_적는다():
    """엔진(combat.status.상태이상_면역)은 특성 "효과"/"상시효과"의 {"변동대상": "상태이상면역"}만 본다 -
    최상위 "면역"/"면역획득" 키는 읽는 곳이 없어 조용히 무시된다(공중사격). "면역특성" 타입은
    면역 원소를 하나 이상 가진다."""
    틀림 = []
    for 모듈이름 in ("0000", "010m", "020f", "030f", "040f", "050f"):
        모듈 = importlib.import_module(f"game.data.ability.job_ability_{모듈이름}")
        for 이름, 정의 in 모듈.특성목록.items():
            if "면역" in 정의 or "면역획득" in 정의:
                틀림.append((모듈이름, 이름, "최상위 면역 키"))
            타입 = 정의.get("타입")
            타입들 = 타입 if isinstance(타입, list) else [타입]
            원소들 = [
                원소
                for 키 in ("효과", "상시효과")
                if isinstance(정의.get(키), list)
                for 원소 in 정의[키]
            ]
            if "면역특성" in 타입들 and not any(
                isinstance(원소, dict)
                and 원소.get("변동대상") in ("상태이상면역", "면역")
                for 원소 in 원소들
            ):
                틀림.append((모듈이름, 이름, "면역특성인데 면역 원소 없음"))
    assert 틀림 == []


def test_직업정보의_전직은_job_level_전직목록과_같다():
    """job_info.직업정보의 "전직기본스탯" 이름(과 순서)이 그 직업 job_level 파일의 "전직목록"과 같다 -
    빠진 전직·오타를 잡는다. 기본스탯은 능력치 셋을 서로 다르게 고른다."""
    from game.data.character.job_info import 직업정보
    from game.data import common_names

    for 직업, 정보 in 직업정보.items():
        모듈 = importlib.import_module(
            f"game.data.job_level.job_level_{정보['분류코드']}_{정보['영문명']}"
        )
        assert list(정보["전직기본스탯"]) == list(모듈.전직목록), 직업
        for 이름, 구성 in [(직업, 정보["기본스탯"]), *정보["전직기본스탯"].items()]:
            assert set(구성) == {"주스탯", "보조스탯", "약점스탯"}, 이름
            assert len(set(구성.values())) == 3, 이름
            assert set(구성.values()) <= common_names.능력치_집합, 이름


def _변동대상_값들(값, 경로):
    if isinstance(값, dict):
        if isinstance(값.get("변동대상"), str):
            yield 경로, 값["변동대상"]
        for 키, 하위 in 값.items():
            yield from _변동대상_값들(하위, f"{경로}.{키}")
    elif isinstance(값, (list, tuple)):
        for i, 하위 in enumerate(값):
            yield from _변동대상_값들(하위, f"{경로}[{i}]")


def test_데이터의_변동대상은_정식_이름이다():
    """데이터의 "변동대상"에 옛 이름(별칭 - "AC"/"속도"/"명중률보너스")을 쓰지 않는다 - 정식 이름은
    "AC보너스"/"명중보너스"/"속도보너스". 엔진은 별칭도 받지만 새로 쓰지 않게 막는다."""
    from game.data import common_names

    별칭 = []
    for 모듈 in _데이터_모듈들():
        for 이름, 값 in vars(모듈).items():
            if 이름.startswith("__") or not isinstance(값, (dict, list)):
                continue
            for 경로, 대상 in _변동대상_값들(값, f"{모듈.__name__}.{이름}"):
                if 대상 in common_names.변동대상_별칭:
                    별칭.append(f"{경로}: {대상}")
    별칭 = sorted(set(별칭))
    assert not 별칭, f"별칭 {len(별칭)}곳:\n" + "\n".join(별칭[:20])


@pytest.mark.parametrize(
    "던전, 보스, 기대",
    [
        (
            "dungeon_01A_D07_frost_mirkwood",
            "결빙의 케라하",
            ["결빙의 케라하", "플래그 시가브", "시가브", "나이아스", "나이아스"],
        ),
        (
            "dungeon_01A_D09_blazing_grakquarak",
            "화염의 비노슈",
            ["화염의 비노슈", "플래그 힐가브", "힐가브", "아도르", "아도르"],
        ),
    ],
)
def test_마녀_보스전_구성(던전, 보스, 기대):
    # 시가브·플래그 시가브(힐가브·플래그 힐가브)를 하나씩 빼고 정령 둘.
    맵 = importlib.import_module(f"game.data.dungeon.{던전}").맵정보
    [보스전] = [o for o in 맵["오브젝트"].values() if o.get("타입") == "보스전투"]
    assert 보스전["이름"] == 보스
    assert [m["이름"] for m in 보스전["전투몬스터"]] == 기대


# ---- 실제 배치와 참조


def _실제로_나오는_몬스터():
    """등록된 던전에서 실제로 나오는 몬스터 이름 - 인카운트(가중치 > 0), 오브젝트 전투, 연속전투, 황금 고블린 교체."""
    from game.system import dungeon_system

    나옴 = {dungeon_system.인카운트_교체몬스터}
    for 던전 in gf.던전_레지스트리.values():
        for 그룹 in (던전.get("인카운트") or {}).get("출현그룹", []):
            나옴 |= {몹 for 몹, 가중치 in 그룹["출현몬스터"].items() if 가중치 > 0}
        for 오브젝트 in 던전["오브젝트"].values():
            나옴 |= {몹["이름"] for 몹 in 오브젝트.get("전투몬스터") or []}
        for 몹 in (던전.get("연속전투") or {}).get("등장몬스터", []):
            나옴.add(몹 if isinstance(몹, str) else 몹["이름"])
    return 나옴


# 도감 글이 아직 "미정"인데 던전에 나오는 몬스터. 글을 고치면 여기서 뺀다.
_출현장소_미정_알려진예외 = {
    "강철 인형사", "결빙의 케라하", "고블린 십장", "고블린 투척십장", "굴 구위시", "나이아스", "돌 인형사",
    "돌칼의 레이조", "라키우스", "레기온", "루가루", "루스 세리말리온", "마스터 도그리", "미르키우스", "벙커워커",
    "불숨의 샐리온", "불스아이", "빛의 성주 지그하르트", "세리말리온", "스톤 골렘", "스틸 골렘", "시가브", "시로가루",
    "아도르", "악시온", "얼음인형 샤레도", "엑스 익스펠러", "오라헌터 시우스", "이블아이의 오른쪽눈",
    "이블아이의 왼쪽눈", "익스펠러", "전격의 키놀", "정원사 랄", "진흙 골렘", "진흙 인형사", "청동 골렘", "칼카자크",
    "쿠로가루", "타우 가드", "타우 비스트", "타우 어설터", "타우킹 샤우타", "틴소드맨", "펜릴", "포레스트 좀비",
    "프라그", "플래그 시가브", "플래그 힐가브", "할로우 아이", "헤븐 익스펠러", "화염의 비노슈", "황금 골렘",
    "황금의 플라타니", "힐가브",
}  # fmt: skip


def test_던전에_나오는_몬스터의_도감_출현장소는_미정이_아니다():
    """도감 [상세보기]는 출현장소 글을 그대로 보여 준다 - 이미 만난 몬스터가 "출현장소: 미정"으로 보이면 안 된다."""
    미정인데_나옴 = {
        이름 for 이름 in _실제로_나오는_몬스터() if 도감_출현장소.get(이름) == "미정"
    }
    assert 미정인데_나옴 - _출현장소_미정_알려진예외 == set(), (
        "도감 출현장소 글을 정해야 한다"
    )
    assert _출현장소_미정_알려진예외 - 미정인데_나옴 == set(), (
        "고쳐진 몬스터는 알려진 예외에서 뺀다(#574)"
    )


def test_도감_출현장소가_정해진_몬스터는_실제로_어딘가에_나온다():
    나옴 = _실제로_나오는_몬스터()
    없음 = [
        (이름, 장소)
        for 이름, 장소 in 도감_출현장소.items()
        if 장소 != "미정" and "던전에 나오지 않음" not in str(장소) and 이름 not in 나옴
    ]
    assert 없음 == []


def test_몬스터승리_업적의_몬스터는_실제로_나온다():
    from game.data.achievement.achievement_list import 업적_목록

    나옴 = _실제로_나오는_몬스터()
    대상 = [u["조건"]["몬스터"] for u in 업적_목록 if u["조건"]["종류"] == "몬스터승리"]
    assert 대상 and [이름 for 이름 in 대상 if 이름 not in 나옴] == []


def test_레벨업으로_얻는_스킬과_특성은_정의가_있다():
    """레벨업은 "획득스킬"/"획득특성" 이름을 확인 없이 보유 목록에 넣는다(character_levelup_system) - 오타면 조용히 빈 스킬이 된다."""
    스킬정의 = gf.스킬데이터모음_생성()
    표들 = [(직업, 정보["레벨업테이블"]) for 직업, 정보 in gf.직업_레지스트리.items()]
    표들 += [
        (f"{직업}/{전직}", 정보["레벨업테이블"])
        for 직업, 전직들 in gf.전직_레지스트리.items()
        for 전직, 정보 in 전직들.items()
    ]
    없음 = []
    for 이름, 표 in 표들:
        for 레벨, 항목 in 표.items():
            획득 = 항목.get("획득") or {}
            특성들 = 획득.get("획득특성") or []
            for 특성 in [특성들] if isinstance(특성들, str) else 특성들:
                if 특성 not in gf.전투용_캐릭터특성정의:
                    없음.append((이름, 레벨, "특성", 특성))
            for 스킬 in 획득.get("획득스킬") or []:
                if 스킬 not in 스킬정의:
                    없음.append((이름, 레벨, "스킬", 스킬))
    assert 없음 == []


# 발동조건이 있는 캐릭터 특성(트리거형)은 combat/traits.py가 상시 계산에서 건너뛴다 - 따로 구현해야 효과가 있다.
# 구현하면 미구현에서 구현으로 옮긴다.
_트리거형_특성_구현 = {"정밀한공격", "이중극점", "삼중극점", "호신연격"}
_트리거형_특성_미구현 = set()


def test_캐릭터_트리거형_특성은_구현됐거나_알려진_미구현이다():
    """퍽으로 고를 수 있는데 아무 효과가 없는 특성이 새로 생기지 않게 한다."""
    트리거형 = {
        이름
        for 이름, 정의 in gf.전투용_캐릭터특성정의.items()
        if 정의.get("발동조건") is not None
    }
    assert 트리거형 == _트리거형_특성_구현 | _트리거형_특성_미구현
