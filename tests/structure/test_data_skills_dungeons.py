"""데이터 무결성 - 스킬 데이터(필수 키)와 던전·지도·레벨 데이터가 실제로 읽히는지 검사한다.

test_data_integrity.py에서 갈라져 나왔다(안전망의 취지는 그 파일 머리말). 의도된 예외는 허용 목록에 이유와 함께 적는다."""

import collections
import importlib
import os
import pathlib
import pkgutil
import re
import pytest
import game.data as 데이터패키지
import gameflow as gf
from game.data.equipment.eq_04_special_11_earring import 귀걸이목록
from game.data.buff.debuff import 디버프목록
from game.data.equipment.eq_04_special_10_magicstone import 마법석목록
from game.data.equipment.eq_00_magic_seal import 봉인장비_해제이름
from game.data.equipment.eq_03_accessory_06_necklace import 목걸이목록
from game.data.equipment.eq_03_accessory_07_ring import 반지목록
from game.data.buff.buff import 버프목록
from game.data.equipment.eq_02_armor_04_belt import 벨트목록
from game.data.equipment.eq_04_special_09_subequipment import 보조장비목록
from game.data.equipment.eq_02_armor_01_top import 상의목록
from game.data.buff.status_effects import 상태이상목록
from game.data.equipment.eq_02_armor_05_shoes import 신발목록
from game.data.equipment.eq_02_armor_03_shoulder import 어깨목록
from game.data.equipment.eq_03_accessory_08_bracelet import 팔찌목록
from game.data.equipment.eq_02_armor_02_bottom import 하의목록

루트 = pathlib.Path(__file__).resolve().parents[2]


def _데이터_모듈들():
    for 정보 in pkgutil.walk_packages(데이터패키지.__path__, "game.data."):
        yield importlib.import_module(정보.name)


# ---------------------------------------------------------------- 스킬

스킬_필수키 = {"분류", "타입", "습득방법", "행동", "MP소모", "설명"}


def test_스킬_데이터는_필수_키를_가진다():
    문제 = []
    for 직업, 정보 in gf.직업_레지스트리.items():
        for 이름, 스킬 in 정보["스킬목록"].items():
            빠짐 = 스킬_필수키 - set(스킬)
            if 빠짐:
                문제.append(f"{직업}/{이름}: 없는 키 {sorted(빠짐)}")
    assert not 문제, "\n".join(문제)


def test_장판스킬_지속공격은_명중_없이_내성으로_절반이다():
    """장판스킬이면서 지속공격이면 명중 굴림 없이 피해를 주고 내성굴림으로 반감한다(피해가 없으면 - 역병의 라사 -
    내성굴림만). 엔진은 이 방식을 라운드종료 발동(attacks.라운드종료_지속공격)에서만 친다."""
    문제 = []
    for 이름, 스킬 in gf.스킬데이터모음_생성().items():
        타입 = 스킬.get("타입", [])
        if not ("장판스킬" in 타입 and "지속공격" in 타입):
            continue
        상세 = 스킬["지속공격"]
        if (상세.get("명중률"), 상세.get("발동시점"), 상세.get("내성성공시")) != (
            "자동",
            "라운드종료",
            "데미지절반" if "데미지" in 상세 else None,
        ) or not 상세.get("내성"):
            문제.append(이름)
    assert not 문제, 문제


def test_디버프스킬은_버프획득이나_효과로_건다():
    """실행 엔진은 "버프획득"이 있으면 버프스킬처럼, 없으면 "효과"(상태이상)를 대상마다 적용한다
    (skill_run.스킬_실행, 도발)."""
    for 이름, 스킬 in gf.스킬데이터모음_생성().items():
        if 스킬["분류"] == "디버프스킬":
            assert 스킬.get("버프획득") or 스킬.get("효과"), 이름


@pytest.mark.parametrize(
    "이름,레지스트리",
    [
        ("버프", lambda: 버프목록),
        ("디버프", lambda: 디버프목록),
        ("상태이상", lambda: 상태이상목록),
    ],
)
def test_버프_디버프_상태이상은_필수_키를_가진다(이름, 레지스트리):
    필수 = {"분류", "중첩", "효과", "설명"} | (
        {"타입"} if 이름 != "상태이상" else set()
    )
    문제 = [
        f"{키}: {sorted(필수 - set(값))}"
        for 키, 값 in 레지스트리().items()
        if 필수 - set(값)
    ]
    assert not 문제, "\n".join(문제)


def test_버프_디버프_효과는_사전이거나_사전의_목록이다():
    """읽는 쪽(combat.stats)은 사전을 [사전]으로 감싸 목록과 같게 처리한다 - 그 밖의 형태(글자,
    사전이 아닌 원소)는 조용히 무시되므로 여기서 막는다. 빈 목록 = 수치 효과 없음(시한부)."""
    틀림 = [
        (이름, 정의.get("효과"))
        for 레지스트리 in (버프목록, 디버프목록)
        for 이름, 정의 in 레지스트리.items()
        if not (
            정의.get("효과") is None
            or isinstance(정의["효과"], dict)
            or (
                isinstance(정의["효과"], list)
                and all(isinstance(원소, dict) for 원소 in 정의["효과"])
            )
        )
    ]
    assert 틀림 == []


def test_기술효과_지속턴은_정수나_전투종료나_소모시다():
    """skill_effects.py 머리말 "지속턴: 숫자 | "전투종료" | "소모시"". 그 밖의 글자는 플레이어 경로
    (skill_grant._효과_지속턴)가 수식으로 평가하다 0이 되고, 몬스터 경로(combat.resources)는 정수만
    받아 영구 버프가 된다 - "전투 종료" 같은 오타를 여기서 막는다. 키가 없으면 수명을 다른 키가 정한다."""
    from game.data.buff.skill_effects import 기술효과목록

    틀림 = [
        (이름, 정의["지속턴"])
        for 이름, 정의 in 기술효과목록.items()
        if "지속턴" in 정의
        and not (
            (isinstance(정의["지속턴"], int) and not isinstance(정의["지속턴"], bool))
            or 정의["지속턴"] in ("전투종료", "소모시")
        )
    ]
    assert 틀림 == []


@pytest.mark.parametrize(
    "이름,레지스트리,접미",
    [("버프", lambda: 버프목록, "버프"), ("디버프", lambda: 디버프목록, "디버프")],
)
def test_버프_디버프_타입은_머리말_표기_규칙을_따른다(이름, 레지스트리, 접미):
    """buff.py/debuff.py 머리말의 "타입" 규칙: 하나면 글자, 둘 이상이면 리스트(원소 하나짜리 리스트 금지).
    버프는 턴제버프/스택버프/자원버프, 디버프는 대칭으로 턴제디버프/스택디버프/자원디버프.
    리스트에 스택이 있으면 "중첩": True. 글자와 리스트가 섞인 것은 이 규칙대로다(통일 대상이 아니다)."""
    허용 = {f"턴제{접미}", f"스택{접미}", f"자원{접미}"}
    문제 = []
    for 키, 값 in 레지스트리().items():
        타입 = 값.get("타입")
        if isinstance(타입, str):
            if 타입 not in 허용:
                문제.append(f"{키}: 모르는 타입 {타입!r}")
        elif not isinstance(타입, list) or len(타입) < 2 or set(타입) - 허용:
            문제.append(f"{키}: 리스트는 {sorted(허용)} 중 둘 이상 - {타입!r}")
        elif f"스택{접미}" in 타입 and 값.get("중첩") is not True:
            문제.append(f"{키}: 스택{접미}인데 중첩이 True가 아니다")
    assert not 문제, "\n".join(문제)


# ---------------------------------------------------------------- 던전/마을/상점


def test_던전_데이터의_좌표와_참조가_맞는다():
    문제 = []
    for 이름, 던전 in gf.던전_레지스트리.items():
        격자 = 던전["지도"]
        너비, 높이 = len(격자[0]), len(격자)

        def 안(좌표):
            return 0 <= 좌표[0] < 너비 and 0 <= 좌표[1] < 높이

        if set("".join(격자)) - set("XYO@#"):  # dungeon_format.py <지도 기호>
            문제.append(f"{이름}: 모르는 지도 기호 {set(''.join(격자)) - set('XYO@#')}")
        for 기호, 파일들 in (던전.get("타일") or {}).items():
            if 기호 not in "XYO@#":
                문제.append(f"{이름}: 타일의 모르는 지도 기호 {기호!r}")
            for 파일 in [파일들] if isinstance(파일들, str) else 파일들:
                if not (루트 / "game" / "assets" / "dungeon" / 파일).is_file():
                    문제.append(f"{이름}: 타일 그림 {파일} 없음")
        for 좌표, 오브젝트 in 던전["오브젝트"].items():
            파일 = 오브젝트.get("타일")
            if 파일 and not (루트 / "game" / "assets" / "dungeon" / 파일).is_file():
                문제.append(f"{이름}: 오브젝트 {좌표} 타일 그림 {파일} 없음")
            if not isinstance(오브젝트.get("타일크기", 1), int):
                문제.append(f"{이름}: 오브젝트 {좌표} 타일크기는 정수")
        if any(len(행) != 너비 for 행 in 격자):
            문제.append(f"{이름}: 지도 행 길이가 다르다")
        if 던전.get("입장좌표") and not 안(던전["입장좌표"]):
            문제.append(f"{이름}: 입장좌표 {던전['입장좌표']}가 지도 밖")
        for 좌표, 오브젝트 in 던전["오브젝트"].items():
            if not 안(좌표):
                문제.append(f"{이름}: 오브젝트 {좌표}가 지도 밖")
            for 몹 in 오브젝트.get("전투몬스터") or []:
                if 몹["이름"] not in gf.몬스터목록:
                    문제.append(f"{이름}: 보스전 몬스터 {몹['이름']!r} 없음")
        for 좌표, 연결 in 던전["연결지역"].items():
            if not 안(좌표):
                문제.append(f"{이름}: 연결 {좌표}가 지도 밖")
            대상 = 연결["연결맵"]
            if 대상 not in gf.던전_레지스트리 and 대상 not in gf.마을파일_레지스트리:
                문제.append(f"{이름}: 연결맵 {대상!r} 없음")
            elif 연결.get("진입좌표") and 대상 in gf.던전_레지스트리:
                격자2 = gf.던전_레지스트리[대상]["지도"]
                x, y = 연결["진입좌표"]
                if not (0 <= x < len(격자2[0]) and 0 <= y < len(격자2)):
                    문제.append(
                        f"{이름}: {대상}의 진입좌표 {연결['진입좌표']}가 지도 밖"
                    )
        for 그룹 in (던전.get("인카운트") or {}).get(
            "출현그룹", []
        ):  # "인카운트"는 선택 항목(dungeon_format.py) - 없는 던전도 있다
            for 몹, 가중치 in 그룹[
                "출현몬스터"
            ].items():  # 가중치는 상대값(random.choices)이라 합이 1일 필요는 없다
                if 몹 not in gf.몬스터목록:
                    문제.append(f"{이름}: 인카운트 몬스터 {몹!r} 없음")
                if not 가중치 > 0:
                    문제.append(f"{이름}: {몹!r}의 가중치 {가중치}")
    assert not 문제, "\n".join(문제)


def test_포탈로_이어진_던전은_목록으로_들어가도_포탈_도착_칸에서_시작한다():
    """번호가 낮은 던전에서 포탈로 들어가는 던전(로리엔 -> 로리엔 안쪽, 아몬 하층 -> 상층 ...)은
    마을 [던전 이동]으로 들어가도 그 포탈의 진입좌표에 선다."""
    from game.system import town_system

    문제 = []
    for 출발, 던전 in gf.던전_레지스트리.items():
        for 연결 in 던전["연결지역"].values():
            대상 = 연결["연결맵"]
            if 대상 not in gf.던전_레지스트리:
                continue
            if town_system.던전_번호(대상) <= town_system.던전_번호(출발):
                continue
            입장 = gf.던전_레지스트리[대상].get("입장좌표")
            if 입장 != 연결["진입좌표"]:
                문제.append(
                    f"{대상}: 입장좌표 {입장} != {출발} 포탈 {연결['진입좌표']}"
                )
    assert not 문제, "\n".join(문제)


# [던전 이동] 목록에서 이름 대신 보여 줄 그림(168x73 배너, 그림 안에 이름이 있다).
# 하늘성(D11~D16)은 아직 그림이 없어 이름 버튼으로 남는다.
_던전_목록그림 = {
    "dungeon_01A_D01_Lorien": "asset_banner_lorien.webp",
    "dungeon_01A_D02_Hollow_Lorien": "asset_banner_hollow_lorien.webp",
    "dungeon_01A_D03_mirkwood": "asset_banner_mirkwood.webp",
    "dungeon_01A_D04_Hollow_mirkwood": "asset_banner_hollow_mirkwood.webp",
    "dungeon_01A_D05_thunderland": "asset_banner_thunderland.webp",
    "dungeon_01A_D06_poison_thunderland": "asset_banner_poison_thunderland.webp",
    "dungeon_01A_D07_frost_mirkwood": "asset_banner_frost_mirkwood.webp",
    "dungeon_01A_D08_grakquarak": "asset_banner_grakquarak.webp",
    "dungeon_01A_D09_blazing_grakquarak": "asset_banner_blazing_grakquarak.webp",
    "dungeon_01A_D10_shadow_thunderland": "asset_banner_shadow_thunderland.webp",
}


def _던전번호(파일명):
    return int(re.match(r"dungeon_\d+A_D(\d+)_", 파일명).group(1))


def _레벨값들(값):
    """던전 데이터 안의 모든 "레벨" 값(인카운트, 전투 오브젝트)."""
    if isinstance(값, dict):
        for 키, 안 in 값.items():
            if 키 == "레벨":
                yield 안
            yield from _레벨값들(안)
    elif isinstance(값, (list, tuple)):
        for 안 in 값:
            yield from _레벨값들(안)


@pytest.mark.parametrize("파일명", list(gf.던전_레지스트리))
def test_던전_레벨은_던전_2개당_1씩_오른다(파일명):
    # D01·D02 1, D03·D04 2 ... D11·D12 6 ... D29·D30 15
    기대 = (_던전번호(파일명) + 1) // 2
    레벨들 = set(_레벨값들(gf.던전_레지스트리[파일명]))
    assert 레벨들 == {기대}, (파일명, 레벨들)


def test_플레이어_레벨은_짝수_던전_보스를_처음_깨면_번호_반_더하기_1이_된다():
    # D02 2 ... D10 6, D12 7, D14 8, D16 9, D18 10 ...
    from game.controller.ctl_registry import 플레이어레벨업_트리거

    기대 = {
        파일명: _던전번호(파일명) // 2 + 1
        for 파일명 in gf.던전_레지스트리
        if _던전번호(파일명) % 2 == 0
    }
    실제 = {파일명: 레벨 for (파일명, _), 레벨 in 플레이어레벨업_트리거.items()}
    assert len(실제) == len(플레이어레벨업_트리거)  # 던전마다 트리거 하나
    assert 실제 == 기대
    for 파일명, 좌표 in 플레이어레벨업_트리거:
        오브젝트 = gf.던전_레지스트리[파일명]["오브젝트"][좌표]
        assert 오브젝트["타입"] == "보스전투", (파일명, 좌표)


def test_던전_목록그림은_정한_던전에만_있고_파일이_있다():
    목록그림 = {
        이름: 던전["목록그림"]
        for 이름, 던전 in gf.던전_레지스트리.items()
        if 던전.get("목록그림")
    }
    assert 목록그림 == _던전_목록그림
    없음 = [
        파일
        for 파일 in 목록그림.values()
        if not (루트 / "game" / "assets" / "dungeon" / 파일).is_file()
    ]
    assert not 없음, 없음


def test_마을_데이터와_상점_품목이_맞는다():
    카탈로그 = gf._상점_카탈로그_생성()
    품목 = set()

    def 모으기(값):
        if isinstance(값, dict):
            for 키, v in 값.items():
                품목.add(키)
                모으기(v)

    모으기(카탈로그)
    문제 = []
    for 이름, 마을 in gf.마을파일_레지스트리.items():
        for 던전 in 마을["던전목록"]:
            if 던전 not in gf.던전_레지스트리:
                문제.append(f"{이름}: 던전 {던전!r} 없음")
        조건 = 마을.get("개방조건")
        if 조건 and 조건.get("대상") not in gf.던전_레지스트리:
            문제.append(f"{이름}: 개방조건 대상 {조건.get('대상')!r} 없음")
        if not (루트 / "game" / "assets" / "town" / 마을["배경이미지"]).is_file():
            문제.append(f"{이름}: 배경이미지 {마을['배경이미지']} 없음")
        for 품 in 마을["상점판매목록"]:
            if 품 not in 품목:
                문제.append(f"{이름}: 상점 품목 {품!r}이 카탈로그에 없다")
    assert not 문제, "\n".join(문제)


def test_장비_이름은_목록을_가로질러_겹치지_않는다():
    """같은 이름이 두 목록에 있으면 소지품/상점이 어느 쪽인지 가를 수 없다."""
    목록들 = {
        "상의": 상의목록,
        "하의": 하의목록,
        "어깨": 어깨목록,
        "벨트": 벨트목록,
        "신발": 신발목록,
        "목걸이": 목걸이목록,
        "반지": 반지목록,
        "팔찌": 팔찌목록,
        "보조장비": 보조장비목록,
        "마법석": 마법석목록,
        "귀걸이": 귀걸이목록,
    }
    주인 = collections.defaultdict(list)
    for 이름, 목록 in 목록들.items():
        for 키, 항목 in 목록.items():
            주인[키].append(이름)
            assert 항목.get("이름") == 키, f"{이름}/{키}: 이름 칸 {항목.get('이름')!r}"
    겹침 = {키: v for 키, v in 주인.items() if len(v) > 1}
    assert not 겹침, 겹침


_레어도배수 = {
    "커먼": 1,
    "언커먼": 2,
    "레어": 3,
    "유니크": 4,
    "크로니클": 5,
    "레전더리": 5,
    "에픽": 6,
    "치트": 0,
}


def test_장비_가격은_가격_공식대로다():
    """eq_01_weapon_format.py <가격 공식>: 무기 5 x 티어 x 레어도배수 x 10, 그 밖은 티어 x 레어도배수 x 10.
    "미정" 같은 글 가격은 상점이 숫자로 비교하다 깨진다."""
    카탈로그 = gf._상점_카탈로그_생성()["장비"]
    틀림 = {}
    for 탭, 아이템들 in 카탈로그.items():
        for 이름, a in 아이템들.items():
            if "마봉능력" in a or "가격" not in a:
                continue  # 봉인을 푼 마법의 장비는 봉인 장비 가격을 그대로 쓴다
            기대 = (
                a["티어"] * _레어도배수[a["레어도"]] * 10 * (5 if 탭 == "무기" else 1)
            )
            if a["가격"] != 기대:
                틀림[이름] = (a["가격"], 기대)
    assert not 틀림, 틀림


# 보스가 주는 유니크 무기 - 타입이 [종류, "보스유니크"]
보스유니크_무기 = {"크로쿠타의 가시"}


def test_장비_타입은_부위와_재질이고_봉인_장비에는_마법봉인이_붙는다():
    """방어구 "타입" = [부위, 재질], 악세서리/특수장비 = [부위],
    무기는 종류 글자 그대로. "마법으로 봉인된 ~"은 그 뒤에 "마법봉인"을 더한다(무기는 [종류, "마법봉인"])."""
    카탈로그 = gf._상점_카탈로그_생성()["장비"]
    틀림 = {}
    for 탭, 아이템들 in 카탈로그.items():
        for 이름, a in 아이템들.items():
            봉인 = (a.get("봉인원본") or 이름) in 봉인장비_해제이름
            if 탭 == "무기":
                종류 = a["타입"][0] if isinstance(a["타입"], list) else a["타입"]
                기대 = [종류, "마법봉인"] if 봉인 else 종류
                if 이름 in 보스유니크_무기:
                    기대 = [종류, "보스유니크"]
            else:
                기대 = [a["분류"]] + ([a["재질"]] if "재질" in a else [])
                기대 += ["마법봉인"] if 봉인 else []
            if a.get("타입") != 기대:
                틀림[이름] = (a.get("타입"), 기대)
    assert not 틀림, 틀림


def test_루트_경로는_저장소_최상위다():
    assert os.path.isfile(루트 / "gameflow.py")
