"""데이터 무결성 - 데이터(game/data) 안의 수식과 이름 참조가 실제로 읽히는지 검사한다.

런타임은 일부러 관대하다: 평가할 수 없는 수식은 0/기본값으로 바뀌고(combat.participants/monster_actions/
traits, loot_system), 정의 없는 특성 이름은 건너뛴다(traits._특성_목록). "아직 미정인 데이터"를 견디려는
설계지만, 그래서 데이터 오타가 오류 없이 효과 없음이 된다(구조 점검 W-3). 이 파일이 그 안전망이다 - 런타임은
그대로 두고, 데이터가 읽히는지를 테스트에서 엄격하게 확인한다. 의도된 예외는 허용 목록에 이유와 함께 적는다.
허용 목록의 항목이 더는 필요 없어지면(데이터가 고쳐지면) 테스트가 목록에서 지우라고 알려 준다.
"""

import collections
import importlib
import os
import pathlib
import pkgutil
import re
import sys

import pytest

import game.data as 데이터패키지
from game.system import rng
import gameflow as gf
from game.data.collection.collection_monster import 도감_출현장소
from game.data.monster.monster_defaults import 몬스터_기본값
from game.data.equipment.eq_04_special_11_earring import 귀걸이목록
from game.data.buff.debuff import 디버프목록
from game.data.equipment.eq_04_special_10_magicstone import 마법석목록
from game.data.equipment.eq_00_magic_seal import 마봉능력, 봉인장비_해제이름
from game.data.equipment.eq_03_accessory_06_necklace import 목걸이목록
from game.data.equipment.eq_03_accessory_07_ring import 반지목록
from game.data.buff.buff import 버프목록
from game.data.equipment.eq_02_armor_04_belt import 벨트목록
from game.data.equipment.eq_04_special_09_subequipment import 보조장비목록
from game.data.equipment.eq_02_armor_01_top import 상의목록
from game.data.buff.status_effects import 상태이상목록
from game.data.equipment.eq_02_armor_05_shoes import 신발목록
from game.data.equipment.eq_02_armor_03_shoulder import 어깨목록
from game.data.monster.monster_title import 칭호목록
from game.data.equipment.eq_03_accessory_08_bracelet import 팔찌목록
from game.data.equipment.eq_02_armor_02_bottom import 하의목록
from game.system.combat import formula, resources

루트 = pathlib.Path(__file__).resolve().parents[1]


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
    "귀신보유수": 2,
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


# ---------------------------------------------------------------- 몬스터

# 몬스터 항목의 칸: 데이터 파일에 꼭 적어야 하는 칸 + 없으면 몬스터_기본값으로 채우는 칸.
몬스터_필수키 = {
    "몬스터명",
    "이미지",
    "크기",
    "분류",
    "타입",
    "칭호",
    "특성",
    "적등급",
    "역할군",
    "근력",
    "민첩",
    "건강",
    "지능",
    "지혜",
    "매력",
    "패턴",
    "드랍표",
}
패턴_필수키 = {"이름", "타입", "타겟", "명중률", "효과", "조건부효과", "설명"}

# 몬스터 데이터가 이름은 쓰는데 특성 정의가 없는 특성(허용 목록). 정의가 없으면 그 특성은
# 조용히 건너뛰어진다(traits._특성_목록). 지금은 없다 - 새로 생기면 정의를 만든다.
정의_없는_몬스터_특성 = {}
# 칭호 칸의 자리표시자(아직 안 정한 값). 칭호목록에 있거나 이 값이면 정상이다.
칭호_자리표시자 = {None, "미정"}


def _몬스터_원본_목록():
    """monster_race_*.py에 적힌 그대로의 (파일, 키, 항목) - 기본값을 채우기 전."""
    폴더 = 루트 / "game" / "data" / "monster"
    for 경로 in sorted(폴더.glob("monster_race_*.py")):
        모듈 = importlib.import_module(f"game.data.monster.{경로.stem}")
        for 키, 몬스터 in 모듈.몬스터목록.items():
            yield 경로.stem, 키, 몬스터


def test_몬스터_원본은_필수_칸을_적고_모르는_칸이_없다():
    문제 = []
    for 파일, 키, 몬스터 in _몬스터_원본_목록():
        모자람 = 몬스터_필수키 - set(몬스터)
        남음 = set(몬스터) - 몬스터_필수키 - set(몬스터_기본값)
        if 모자람 or 남음:
            문제.append(
                f"{파일} {키}: 없는 칸 {sorted(모자람)} 모르는 칸 {sorted(남음)}"
            )
    assert not 문제, "\n".join(문제)


# 아직 게임 목록(ctl_registry._몬스터파일목록)에 넣지 않은 초안 파일 - 이유와 함께.
미등록_몬스터파일 = set()
# 등록한 파일 안에서 아직 빼 둔 몬스터 - 이유와 함께(ctl_registry._몬스터파일목록).
미등록_몬스터 = {
    # 사용자 초안(2026-10-15): 특성 "공어의 왕" 효과와 드랍군 "공어공용군"이 미정
    "공왕 크로쿠타",
}


def test_미등록_몬스터파일은_정말_등록되지_않았다():
    """등록하면 이 목록에서 빼야 한다 - 빼는 것을 잊지 않게."""
    assert not 미등록_몬스터파일 & {파일 for 파일, _ in gf._몬스터파일목록}
    assert not 미등록_몬스터 & set(gf.몬스터목록)


def test_몬스터_기본값은_빈_칸만_채운다():
    assert not 몬스터_필수키 & set(몬스터_기본값)
    원본들 = [
        항목
        for 항목 in _몬스터_원본_목록()
        if 항목[0] not in 미등록_몬스터파일 and 항목[1] not in 미등록_몬스터
    ]
    assert len(원본들) == len(gf.몬스터목록)
    for _, 키, 몬스터 in 원본들:
        채운것 = gf.몬스터목록[키]
        assert 채운것 is not 몬스터  # 사본 - 데이터 모듈은 그대로
        assert all(채운것[k] == v for k, v in 몬스터.items()), 키  # 적힌 칸은 그대로
        assert list(채운것)[: len(몬스터)] == list(몬스터), 키  # 적힌 칸의 순서도
        for k, v in 몬스터_기본값.items():
            if k not in 몬스터:
                assert 채운것[k] == v, (키, k)


def test_몬스터_데이터는_필수_키와_허용값을_지킨다():
    문제 = []
    for 키, 몬스터 in gf.몬스터목록.items():
        if set(몬스터) != 몬스터_필수키 | set(몬스터_기본값):
            문제.append(
                f"{키}: 칸이 다르다 {sorted(set(몬스터) ^ (몬스터_필수키 | set(몬스터_기본값)))}"
            )
        if 몬스터.get("몬스터명") != 키:
            문제.append(f"{키}: 몬스터명 {몬스터.get('몬스터명')!r}이 목록 키와 다르다")
        if 몬스터.get("크기") not in gf.몬스터_크기_배율:
            문제.append(f"{키}: 크기 {몬스터.get('크기')!r}")
        if 몬스터.get("적등급") not in ("일반", "네임드", "엘리트"):
            문제.append(f"{키}: 적등급 {몬스터.get('적등급')!r}")
        if 몬스터.get("역할군") not in ("딜러", "탱커", "메이지"):
            문제.append(f"{키}: 역할군 {몬스터.get('역할군')!r}")
        이미지 = 몬스터.get("이미지")
        if 이미지 and not (루트 / "game" / "assets" / "monster" / 이미지).is_file():
            문제.append(f"{키}: 그림 파일이 없다 {이미지}")
        if not 몬스터.get("패턴"):
            문제.append(f"{키}: 패턴이 비었다")
        for 번호, 패턴 in (몬스터.get("패턴") or {}).items():
            빠짐 = 패턴_필수키 - set(패턴)
            if 빠짐:
                문제.append(f"{키} 패턴 {번호}: 없는 키 {sorted(빠짐)}")
            for 갈래 in ("조건충족시", "조건미충족시"):  # 조건부행동이 실제로 쓰는 패턴
                if isinstance(패턴.get(갈래), dict):
                    빠짐 = 패턴_필수키 - set(패턴[갈래])
                    if 빠짐:
                        문제.append(f"{키} 패턴 {번호} {갈래}: 없는 키 {sorted(빠짐)}")
        칭호 = 몬스터.get("칭호")
        if 칭호 not in 칭호_자리표시자 and 칭호 not in 칭호목록:
            문제.append(f"{키}: 칭호 {칭호!r}의 정의가 없다")
    assert not 문제, "\n".join(문제)


def test_고블린_분류는_모두_인간형이다():
    """고블린 종족의 타입은 인간형(사용자 지정 2026-10-13, 그전에는 야수형). 타입은
    문자열 하나 또는 리스트(예: 샹들리에로 건물형이 붙는 카겔)다."""
    틀림 = []
    for 키, 몬스터 in gf.몬스터목록.items():
        if 몬스터.get("분류") != "고블린":
            continue
        타입 = 몬스터.get("타입")
        타입들 = 타입 if isinstance(타입, list) else [타입]
        if "인간형" not in 타입들:
            틀림.append(f"{키}: {타입!r}")
    assert not 틀림, "\n".join(틀림)


def test_카겔과_봄_카겔은_사용자가_정한_대로다():
    """사용자 지정(2026-10-13). 능력치는 고블린 대비 카겔 근력+4 민첩+2, 봄 카겔 근력+2 민첩+6."""
    고블린 = gf.몬스터목록["고블린"]
    기대 = {
        "카겔": (
            "일반",
            4,
            2,
            "표창 던지기",
            "적단일",
            "다중 표창 던지기",
            "적전체",
            "2d8",
        ),
        "봄 카겔": (
            "엘리트",
            2,
            6,
            "폭탄 던지기",
            "적3체",
            "다중 폭탄 던지기",
            "적전체범위",
            "1d4",
        ),
    }
    for 이름, (
        등급,
        근력,
        민첩,
        기본,
        기본타겟,
        여섯,
        여섯타겟,
        주사위,
    ) in 기대.items():
        m = gf.몬스터목록[이름]
        assert (m["적등급"], m["크기"], m["역할군"], m["분류"]) == (
            등급,
            "소형",
            "딜러",
            "고블린",
        )
        assert m["타입"] == ["인간형", "건물형"]
        assert m["특성"] == ["종족:고블린", "샹들리에"]
        assert 도감_출현장소[이름] == ["하늘성", "웨스트코스트"]
        assert (m["근력"] - 고블린["근력"], m["민첩"] - 고블린["민첩"]) == (근력, 민첩)
        for 칸 in ("건강", "지능", "지혜", "매력"):
            assert m[칸] == 고블린[칸], (이름, 칸)
        패턴 = m["패턴"]
        assert [패턴[k]["이름"] for k in range(1, 7)] == [기본] * 5 + [여섯]
        assert [패턴[k]["타겟"] for k in range(1, 7)] == [기본타겟] * 5 + [여섯타겟]
        for k in range(1, 7):
            assert (
                패턴[k]["데미지"] == f"{주사위}+보정치"
            )  # 근력판정의 보정치 = 근력보정치
            assert (패턴[k]["속성"], 패턴[k]["명중률"]) == ("무속성", "근력판정")
            효과 = 패턴[k]["효과"]
            if 이름 == "카겔":
                assert (효과["이름"], 효과["내성"], 효과["난이도"], 효과["지속턴"]) == (
                    "출혈",
                    "건강",
                    10,
                    3,
                )
            else:
                assert 효과 is None
    assert gf.몬스터목록["카겔"]["드랍표"][-1]["이름"] == "카겔군"
    assert gf.몬스터목록["봄 카겔"]["드랍표"][-1]["이름"] == "봄카겔군"


def test_도감_출현장소는_몬스터마다_하나씩_있다():
    """출현장소는 몬스터 데이터가 아니라 도감 자료(collection_monster.py)에 적는다(사용자 지정
    2026-10-13). 실제 출현은 각 던전 파일이 정하고 도감 글과 항상 같지는 않다."""
    assert set(도감_출현장소) == set(gf.몬스터목록)
    for 이름, 장소 in 도감_출현장소.items():
        assert isinstance(장소, (str, list)) and 장소, 이름


def test_프라그_패턴은_십장과_투척십장을_합친_것이다():
    """사용자 지정(2026-10-13). 데미지보너스/명중보너스는 가져온 패턴과 같다."""
    몬 = gf.몬스터목록
    십장, 투척, 플래그 = (
        몬[n]["패턴"] for n in ("고블린 십장", "고블린 투척십장", "플래그 힐가브")
    )
    프라그 = 몬["프라그"]["패턴"]
    for 번호, 원본 in ((1, 십장[1]), (2, 투척[1]), (3, 십장[4]), (4, 투척[4])):
        assert {k: v for k, v in 프라그[번호].items() if k != "설명"} == {
            k: v for k, v in 원본.items() if k != "설명"
        }, 번호
    스매시 = 프라그[5]
    assert (스매시["이름"], 스매시["타겟"], 스매시["명중률"], 스매시["데미지"]) == (
        "파워 스매시",
        "적단일",
        "근력판정",
        "3d4+보정치",  # 근력판정의 보정치 = 근력보정치
    )
    assert (스매시["데미지보너스"], 스매시["명중보너스"]) == (
        십장[1]["데미지보너스"],
        십장[1]["명중보너스"],
    )
    부채꼴 = 프라그[6]
    assert 부채꼴["이름"] == "돌맹이 부채꼴 삼연속 투척"
    assert (부채꼴["타겟"], 부채꼴["공격횟수"], 부채꼴["각공격명중굴림"]) == (
        "적3체",
        3,
        True,
    )
    assert (부채꼴["명중률"], 부채꼴["데미지"], 부채꼴["속성"]) == (
        "민첩판정",
        "1d4+보정치",
        "무속성",
    )
    assert (부채꼴["데미지보너스"], 부채꼴["명중보너스"]) == (
        플래그[6]["데미지보너스"],
        플래그[6]["명중보너스"],
    )
    assert 부채꼴["효과"] is None


def test_루가루의_할퀴기는_모두_데미지보너스_마이너스1이다():
    """사용자 지정(2026-10-13): 분류 루가루인 몬스터의 할퀴기 패턴(두번/마구)은 데미지보너스 -1."""
    틀림 = [
        (이름, 번호, 패턴.get("데미지보너스"))
        for 이름, m in gf.몬스터목록.items()
        if m["분류"] == "루가루"
        for 번호, 패턴 in m["패턴"].items()
        if "할퀴기" in str(패턴.get("이름")) and 패턴.get("데미지보너스") != -1
    ]
    assert not 틀림, 틀림


def test_몬스터_데이터의_칭호는_모두_None이다():
    """칭호는 칸만 두고 던전 파일(맵 이벤트/인카운트)이 붙인다(사용자 지정 2026-10-13)."""
    틀림 = [키 for 키, m in gf.몬스터목록.items() if m["칭호"] is not None]
    assert not 틀림, 틀림


def test_용족_분류는_타입에_용족이_있다():
    """세리말리온 계열 4종의 타입(사용자 지정 2026-10-13, 그전에는 "미정")과 용인족 3종(2026-10-29),
    이블아이 두 눈(2026-10-30 #483)."""
    용족 = {k: m for k, m in gf.몬스터목록.items() if m.get("분류") == "용족"}
    assert len(용족) == 9
    for 키, 몬스터 in 용족.items():
        타입 = 몬스터["타입"]
        assert "용족" in (타입 if isinstance(타입, list) else [타입]), 키


def test_샹들리에_몬스터는_타입에_건물형이_있다():
    for 키, 몬스터 in gf.몬스터목록.items():
        if "샹들리에" in (몬스터.get("특성") or []):
            assert "건물형" in 몬스터["타입"], 키


def test_케라하와_비노슈는_타입이_인간형과_마녀다():
    """2026-10-28 사용자 결정 - 전에는 인간형 하나였다."""
    for 키 in ("결빙의 케라하", "화염의 비노슈"):
        assert gf.몬스터목록[키]["타입"] == ["인간형", "마녀"], 키


def test_공어_몬스터는_그림이_연결된다():
    """공어 3종 그림(사용자 제공 2026-10-15). 아직 미등록이라 데이터 파일을 직접 읽는다."""
    공어 = {
        키: 몬스터["이미지"]
        for 파일, 키, 몬스터 in _몬스터_원본_목록()
        if 파일 == "monster_race_spacefish"
    }
    for 이미지 in 공어.values():
        assert (루트 / "game" / "assets" / "monster" / 이미지).is_file(), 이미지
    assert 공어 == {
        "공어": "asset_monster_spacefish.webp",
        "대공어": "asset_monster_big_spacefish.webp",
        "공왕 크로쿠타": "asset_monster_crocuta.webp",
    }


def test_용족_몬스터는_그림과_적등급을_가지고_등록된다():
    """세리말리온 계열(용인족은 tests/test_dragonkin.py)."""
    용족 = {
        n: d
        for n, d in gf.몬스터목록.items()
        if d["분류"] == "용족" and "종족:세리말리온" in d["특성"]
    }
    assert {n: (d["이미지"], d["적등급"]) for n, d in 용족.items()} == {
        "세리말리온": ("asset_monster_serimalion.webp", "일반"),
        "루스 세리말리온": ("asset_monster_louis_serimalion.webp", "일반"),
        "하스 세리말리온": ("asset_monster_haas_serimalion.webp", "엘리트"),
        "불숨의 샐리온": ("asset_monster_firebreath_selion.webp", "네임드"),
    }
    돌연변이 = {
        "세리말리온": "명",
        "루스 세리말리온": "수",
        "하스 세리말리온": "암",
        "불숨의 샐리온": "화",
    }
    능력치 = ("근력", "민첩", "건강", "지능", "지혜", "매력")
    for 이름, 몬스터 in 용족.items():
        assert 몬스터["특성"] == [
            "종족:용족",
            "종족:세리말리온",
            f"돌연변이:{돌연변이[이름]}",
        ], 이름
        assert [몬스터[k] for k in 능력치] == [14, 16, 12, 8, 10, 10], 이름
        assert 몬스터["역할군"] == "딜러", 이름
        assert 몬스터["칭호"] is None, 이름  # 보스 칭호는 던전 맵 이벤트가 붙인다
        assert 몬스터["크기"] == "소형", 이름
        assert {"이름": "세리말리온군", "발동확률": 1} in 몬스터["드랍표"], 이름
    정의 = gf.전투용_몬스터특성정의
    assert 정의["종족:용족"]["효과"] == [
        {"변동대상": "AC보너스", "변동값": 1},
        {"변동대상": "속성내성", "속성": "전체", "변동값": 1},
    ]
    assert 정의["종족:세리말리온"]["효과"] == [
        {"변동대상": "상태이상면역", "변동값": "넘어짐"},
        {"변동대상": "상태이상면역", "변동값": "공중에뜸"},
    ]
    from game.data.item.item_materials import 재료_데이터
    from game.data.monster.monster_drop import 드랍표_모음

    심장 = 재료_데이터["잡템"]["새끼용의 심장"]
    assert (심장["분류"], 심장["타입"], 심장["가격"]) == ("재료", "잡템", 10)
    assert [
        (a["아이템이름"], a["드랍확률"]) for a in 드랍표_모음["세리말리온군"]["아이템"]
    ] == [("새끼용의 심장", 0.3)]


def _패턴_요약(패턴):
    """패턴 칸 하나의 이름(조건부행동은 "미충족시/충족시")과 속성."""
    if 패턴["이름"] == "조건부행동":
        return f"{패턴['조건미충족시']['이름']}/{패턴['조건충족시']['이름']}", None
    return 패턴["이름"], 패턴.get("속성")


def test_용족_패턴_구성():
    물기, 날기 = "물기", ("공중날기", None)
    기대 = {
        "세리말리온": ["명"] * 5,
        "루스 세리말리온": ["수"] * 3 + [("아이스 바운스", "수속성")] * 2,
        "하스 세리말리온": ["암"] * 2 + [("상승공격/하강공격", None)] * 3,
        "불숨의 샐리온": ["화"] * 2
        + [("브레스", "화속성")] * 2
        + [("광란의 브레스", "화속성")],
    }
    for 이름, 칸들 in 기대.items():
        칸들 = [(물기, f"{c}속성") if len(c) == 1 else c for c in 칸들] + [날기]
        패턴 = gf.몬스터목록[이름]["패턴"]
        assert [_패턴_요약(패턴[k]) for k in sorted(패턴)] == 칸들, 이름
    아이스 = gf.몬스터목록["루스 세리말리온"]["패턴"][4]
    assert (아이스["타겟"], 아이스["대상수"], 아이스["명중률"]) == (
        "적랜덤",
        2,
        "지능판정",
    )
    하스 = gf.몬스터목록["하스 세리말리온"]["패턴"][3]
    assert 하스["조건"] == {"보유버프": "상승"}
    assert 하스["조건미충족시"]["자신버프획득"] == "상승"
    assert 하스["조건충족시"]["자신버프해제"] == "상승"
    assert 하스["조건충족시"]["공격단계2"]["효과"]["이름"] == "넘어짐"
    assert 하스["조건미충족시"]["효과"]["이름"] == "공중에뜸"
    하강 = 하스["조건충족시"]
    assert [
        하스["조건미충족시"]["속성"],
        하강["공격단계1"]["속성"],
        하강["공격단계2"]["속성"],
    ] == ["암속성", "암속성", "무속성"]
    assert (
        하스["조건미충족시"]["효과"]["지속턴"]
        == 하강["공격단계2"]["효과"]["지속턴"]
        == 1
    )
    광란 = gf.몬스터목록["불숨의 샐리온"]["패턴"][5]
    assert (광란["타겟"], 광란["명중률"], 광란["각공격명중굴림"]) == (
        "적전체",
        "민첩판정",
        True,
    )
    from game.data.buff.buff import 버프목록

    assert 버프목록["공중날기"]["효과"] == {"변동대상": "AC보너스", "변동값": 5}


def test_몬스터_특성_이름은_정의가_있다():
    정의 = gf.전투용_몬스터특성정의
    없는 = collections.defaultdict(set)
    for 키, 몬스터 in gf.몬스터목록.items():
        for 이름 in 몬스터.get("특성") or []:
            if 이름 not in 정의:
                없는[이름].add(키)
    assert dict(없는) == 정의_없는_몬스터_특성, (
        "정의 없는 몬스터 특성이 허용 목록과 다르다. 새로 생겼으면 정의를 만들거나 오타를 고치고, "
        "허용 목록의 특성에 정의가 생겼으면 목록에서 지운다:\n" + repr(dict(없는))
    )


def _이름_참조_모으기(값, 결과):
    """데이터에서 버프/상태이상/자원을 이름으로 가리키는 곳을 모은다."""
    if isinstance(값, dict):
        종류 = 값.get("종류")
        if 종류 in (
            "상태이상",
            "자동상태",
            "지속피해",
            "아군버프",
            "버프해제",
            "디버프해제",
        ) and isinstance(값.get("이름"), str):
            결과.append(값["이름"])
        for 키 in ("버프획득", "자신버프획득", "자신버프해제"):
            획득 = 값.get(키)
            if isinstance(획득, str):
                결과.append(획득)
            elif isinstance(획득, list):
                결과.extend(이름 for 이름 in 획득 if isinstance(이름, str))
        for v in 값.values():
            _이름_참조_모으기(v, 결과)
    elif isinstance(값, (list, tuple)):
        for v in 값:
            _이름_참조_모으기(v, 결과)


def _이름_풀림(이름):
    """런타임이 이 이름을 풀 수 있는가: 상태이상/버프/디버프/기술효과, 또는 "소환:<이름>"
    (combat.monster_actions._몬스터_소환수_목록이 접두어를 떼어 소환수 목록에서 찾는다)."""
    if 이름 in 상태이상목록 or resources.효과정의_조회(이름)[0] is not None:
        return True
    from game.data.buff import summon_00

    return 이름.startswith("소환:") and 이름[len("소환:") :] in summon_00.소환수목록


def test_스킬과_몬스터_패턴의_버프_이름은_풀린다():
    참조 = []
    for 직업, 정보 in gf.직업_레지스트리.items():
        for 이름, 스킬 in 정보["스킬목록"].items():
            목록 = []
            _이름_참조_모으기(스킬, 목록)
            참조 += [(f"스킬 {직업}/{이름}", n) for n in 목록]
    for 키, 몬스터 in gf.몬스터목록.items():
        목록 = []
        _이름_참조_모으기(몬스터["패턴"], 목록)
        참조 += [(f"몬스터 {키}", n) for n in 목록]
    assert len(참조) >= 60, f"참조를 {len(참조)}개만 찾았다 - 수집 로직을 확인한다"
    못푼 = [f"{곳}: {이름!r}" for 곳, 이름 in 참조 if not _이름_풀림(이름)]
    assert not 못푼, "런타임이 풀지 못하는 버프/상태이상 이름:\n" + "\n".join(못푼)


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
    """장판스킬이면서 지속공격이면 명중 굴림 없이 피해를 주고 내성굴림으로 반감한다(2026-10-21 사용자
    규칙, #350). 엔진은 이 방식을 라운드종료 발동(attacks.라운드종료_지속공격)에서만 친다."""
    문제 = []
    for 이름, 스킬 in gf.스킬데이터모음_생성().items():
        타입 = 스킬.get("타입", [])
        if not ("장판스킬" in 타입 and "지속공격" in 타입):
            continue
        상세 = 스킬["지속공격"]
        if (상세.get("명중률"), 상세.get("발동시점"), 상세.get("내성성공시")) != (
            "자동",
            "라운드종료",
            "데미지절반",
        ) or not 상세.get("내성"):
            문제.append(이름)
    assert not 문제, 문제


def test_디버프스킬은_버프획득이나_효과로_건다():
    """실행 엔진은 "버프획득"이 있으면 버프스킬처럼, 없으면 "효과"(상태이상)를 대상마다 적용한다
    (skill_run.스킬_실행, 도발 #352)."""
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
    마을 [던전 이동]으로 들어가도 그 포탈의 진입좌표에 선다(2026-10-30 사용자 지정)."""
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


# [던전 이동] 목록에서 이름 대신 보여 줄 그림(사용자가 준 168x73 배너, 그림 안에 이름이 있다).
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


def test_장비_타입은_부위와_재질이고_봉인_장비에는_마법봉인이_붙는다():
    """2026-10-19 사용자 결정: 방어구 "타입" = [부위, 재질], 악세서리/특수장비 = [부위],
    무기는 종류 글자 그대로. "마법으로 봉인된 ~"은 그 뒤에 "마법봉인"을 더한다(무기는 [종류, "마법봉인"])."""
    카탈로그 = gf._상점_카탈로그_생성()["장비"]
    틀림 = {}
    for 탭, 아이템들 in 카탈로그.items():
        for 이름, a in 아이템들.items():
            봉인 = (a.get("봉인원본") or 이름) in 봉인장비_해제이름
            if 탭 == "무기":
                종류 = a["타입"][0] if isinstance(a["타입"], list) else a["타입"]
                기대 = [종류, "마법봉인"] if 봉인 else 종류
            else:
                기대 = [a["분류"]] + ([a["재질"]] if "재질" in a else [])
                기대 += ["마법봉인"] if 봉인 else []
            if a.get("타입") != 기대:
                틀림[이름] = (a.get("타입"), 기대)
    assert not 틀림, 틀림


def test_루트_경로는_저장소_최상위다():
    assert os.path.isfile(루트 / "gameflow.py")


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


# 공격 연출 모양(사용자 지정 2026-10-14) - combat.damage.공격연출_종류 / stats.타격_공격타입
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
    속성추가피해. 명중 굴림이 없는 피해(내성 피해, 자폭)도 연출이 뜬다(사용자 지정 2026-10-14)."""
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


def _이름_붙은_레어(목록, 종류):
    """그 종류의 이름 붙은 일반 레어 무기(미정_·마법으로 봉인된 이 아닌 레어 티어1) - 없으면 None."""
    return next(
        (
            항목
            for 이름, 항목 in 목록.items()
            if 항목["타입"] == 종류
            and 항목["레어도"] == "레어"
            and 항목["티어"] == 1
            and not 이름.startswith("미정_")
        ),
        None,
    )


def test_소검_둔기를_뺀_무기_종류마다_미정_레어와_유니크가_있다():
    """일반 레어(티어1, 명중 기본+1)와 일반/성물 유니크(티어2, 명중 기본+2) 자리 - 이름은 미정_(레어도or성물)_(무기)
    (2026-10-26 사용자 결정). 소검(산들바람/성물:로켈의 글라디우스)과 둔기(공어 가시 클럽)는 넣지 않는다.
    기본값은 그 종류의 커먼 무기, 데미지보너스는 커먼 등급 페널티 없이 0.
    레어 자리는 이름과 고유 효과가 정해지면 그 무기로 바뀐다(#437) - 그때는 종류·레어도·티어·명중만 본다."""
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
                정해짐 = 항목 is None and 접두 == "레어" and _이름_붙은_레어(목록, 종류)
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
                # 저주만 지혜 내성(2026-10-27 사용자 결정, #437)
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
    # 2026-10-20 사용자 결정(#247): 모든 직업의 레벨 8 버프 스킬은 휴식당 1회
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
    assert {"오버드라이브", "잔영의 케이가", "강권"} <= set(검사한것)


def test_퍽은_분류가_퍽이고_타입에_처리종류가_하나다():
    """퍽 구조(#289): "분류"는 모두 "퍽", 처리 종류(특성획득/스킬획득/스탯획득/일반퍽)는 "타입" 리스트에
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


def test_특성의_면역은_효과_원소로_적는다():
    """엔진(combat.status.상태이상_면역)은 특성 "효과"/"상시효과"의 {"변동대상": "상태이상면역"}만 본다 -
    최상위 "면역"/"면역획득" 키는 읽는 곳이 없어 조용히 무시된다(#395 공중사격). "면역특성" 타입은
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
    "AC보너스"/"명중보너스"/"속도보너스"(#459). 엔진은 별칭도 받지만 새로 쓰지 않게 막는다."""
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
def test_마녀_보스전_구성과_모든_출현그룹의_정령(던전, 보스, 기대):
    # 사용자 지정 2026-10-31 - 시가브·플래그 시가브(힐가브·플래그 힐가브)를 하나씩 빼고 정령 둘, 출현그룹마다 정령 0.2
    맵 = importlib.import_module(f"game.data.dungeon.{던전}").맵정보
    [보스전] = [o for o in 맵["오브젝트"].values() if o.get("타입") == "보스전투"]
    assert 보스전["이름"] == 보스
    assert [m["이름"] for m in 보스전["전투몬스터"]] == 기대
    정령 = 기대[-1]
    assert all(g["출현몬스터"].get(정령) == 0.2 for g in 맵["인카운트"]["출현그룹"])
