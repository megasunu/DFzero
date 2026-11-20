"""데이터 무결성 - 몬스터 데이터(필수 키, 패턴, 특성·칭호 이름, 발동 조건, 이름 참조)가 실제로 읽히는지 검사한다.

test_data_integrity.py에서 갈라져 나왔다(안전망의 취지는 그 파일 머리말). 의도된 예외는 허용 목록에 이유와 함께 적는다."""

import collections
import importlib
import pathlib
import pkgutil
import game.data as 데이터패키지
import gameflow as gf
from game.data.collection.collection_monster import 도감_출현장소
from game.data.monster.monster_defaults import 몬스터_기본값
from game.data.buff.buff import 버프목록
from game.data.buff.status_effects import 상태이상목록
from game.data.monster.monster_title import 칭호목록
from game.system.combat import resources

루트 = pathlib.Path(__file__).resolve().parents[2]


def _데이터_모듈들():
    for 정보 in pkgutil.walk_packages(데이터패키지.__path__, "game.data."):
        yield importlib.import_module(정보.name)


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
미등록_몬스터 = set()


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


def test_몬스터_원본은_기본값과_같은_칸을_적지_않는다():
    # 기본값과 같은 칸은 생략한다(기본값을 바꾸면 모든 몬스터에 한 번에 적용되도록).
    같은칸 = [
        f"{파일명}:{키}:{k}"
        for 파일명, 키, 몬스터 in _몬스터_원본_목록()
        for k, v in 몬스터_기본값.items()
        if k in 몬스터 and 몬스터[k] == v and type(몬스터[k]) is type(v)
    ]
    assert not 같은칸, 같은칸


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


def test_보스_칭호의_AC_증가는_고정_2다():
    assert {"변동대상": "AC보너스", "변동값": 2} in 칭호목록["보스"]["효과"]


def test_고블린_분류는_모두_인간형이다():
    """고블린 종족의 타입은 인간형이다. 타입은
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
    """능력치는 고블린 대비 카겔 근력+4 민첩+2, 봄 카겔 근력+2 민첩+6."""
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
    """출현장소는 몬스터 데이터가 아니라 도감 자료(collection_monster.py)에 적는다.
    실제 출현은 각 던전 파일이 정하고 도감 글과 항상 같지는 않다."""
    assert set(도감_출현장소) == set(gf.몬스터목록)
    for 이름, 장소 in 도감_출현장소.items():
        assert isinstance(장소, (str, list)) and 장소, 이름


def test_프라그_패턴은_십장과_투척십장을_합친_것이다():
    """데미지보너스/명중보너스는 가져온 패턴과 같다."""
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


def test_벙커워커는_프라그에서_근력_민첩과_패턴_홀짝만_다르다():
    """근력 14, 민첩 10, 패턴 1<->2, 3<->4, 5<->6."""
    몬 = gf.몬스터목록
    프라그, 벙커 = 몬["프라그"], 몬["벙커워커"]
    assert (벙커["근력"], 벙커["민첩"]) == (14, 10)
    다른키 = {"몬스터명", "이미지", "근력", "민첩", "패턴"}
    assert {k: v for k, v in 벙커.items() if k not in 다른키} == {
        k: v for k, v in 프라그.items() if k not in 다른키
    }
    assert 벙커["이미지"] == "asset_monster_bunker_walker.webp"  # 전용 그림
    맞바꿈 = {1: 2, 2: 1, 3: 4, 4: 3, 5: 6, 6: 5}
    assert 벙커["패턴"] == {번호: 프라그["패턴"][원래] for 번호, 원래 in 맞바꿈.items()}


def test_벙커워커는_프로스트머크우드_고블린_묶음에서_0점1로_나온다():
    from game.data.dungeon.dungeon_01A_D07_frost_mirkwood import 맵정보

    고블린묶음 = next(
        g for g in 맵정보["인카운트"]["출현그룹"] if "고블린 십장" in g["출현몬스터"]
    )
    assert 고블린묶음["출현몬스터"]["벙커워커"] == 0.1


def test_루가루의_할퀴기는_모두_데미지보너스_마이너스1이다():
    """분류 루가루인 몬스터의 할퀴기 패턴(두번/마구)은 데미지보너스 -1."""
    틀림 = [
        (이름, 번호, 패턴.get("데미지보너스"))
        for 이름, m in gf.몬스터목록.items()
        if m["분류"] == "루가루"
        for 번호, 패턴 in m["패턴"].items()
        if "할퀴기" in str(패턴.get("이름")) and 패턴.get("데미지보너스") != -1
    ]
    assert not 틀림, 틀림


def test_몬스터_데이터의_칭호는_모두_None이다():
    """칭호는 칸만 두고 던전 파일(맵 이벤트/인카운트)이 붙인다."""
    틀림 = [키 for 키, m in gf.몬스터목록.items() if m["칭호"] is not None]
    assert not 틀림, 틀림


def test_용족_분류는_타입에_용족이_있다():
    """세리말리온 계열 4종의 타입과 용인족 3종,
    이블아이 두 눈."""
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
    for 키 in ("결빙의 케라하", "화염의 비노슈"):
        assert gf.몬스터목록[키]["타입"] == ["인간형", "마녀"], 키


def test_공어_몬스터는_그림이_연결된다():
    """공어 3종 그림. 아직 미등록이라 데이터 파일을 직접 읽는다."""
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
    """세리말리온 계열(용인족은 tests/monsters/test_dragonkin.py)."""
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
        assert [몬스터[k] for k in 능력치] == [8, 14, 10, 8, 10, 10], 이름
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
        {"변동대상": "AC보너스", "변동값": -1},
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


_몬스터_발동조건_시점 = {"공격명중시", "턴종료시", "라운드종료시", "전투시작시"}


def _해제시_조건인가(조건):
    return (
        isinstance(조건, str)
        and 조건.endswith(" 해제시")
        and 조건[: -len(" 해제시")] in 상태이상목록
    )


def test_몬스터_특성_발동조건과_효과_형태를_지킨다():
    """monster_ability.py 양식 3번. traits의 공격명중시·턴종료시·라운드종료시·전투시작시 판정은 글자를
    != 로만 비교하므로 목록으로 쓰면 조용히 발동하지 않는다. 목록은 해제시 판정만 받는다."""
    from game.data.monster.monster_ability import 특성목록

    틀림 = {}
    for 이름, 정의 in 특성목록.items():
        조건 = 정의.get("발동조건")
        if 조건 is None:
            continue
        if isinstance(조건, list):
            맞음 = bool(조건) and all(_해제시_조건인가(c) for c in 조건)
        else:
            맞음 = 조건 in _몬스터_발동조건_시점 or _해제시_조건인가(조건)
        효과 = 정의.get("효과")
        if not 맞음:
            틀림[이름] = f"발동조건 {조건!r}"
        elif not (isinstance(효과, dict) and "종류" in 효과):
            틀림[이름] = f"트리거형인데 효과가 '종류' 사전이 아님: {효과!r}"
    assert not 틀림, 틀림


def test_명중시버프강탈은_True_또는_전부다():
    """monster_patterns.버프_강탈은 "전부"만 따로 보고 나머지 참값은 하나 강탈로 처리한다.
    True == 1 이므로 is True로 따로 본다."""
    from game.data.monster.monster_ability import 특성목록

    틀림 = {
        이름: 정의["명중시버프강탈"]
        for 이름, 정의 in 특성목록.items()
        if "명중시버프강탈" in 정의
        and not (정의["명중시버프강탈"] is True or 정의["명중시버프강탈"] == "전부")
    }
    assert not 틀림, 틀림


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


def test_직업_스킬의_버프획득은_하나여도_리스트다():
    틀림 = [
        f"{직업}/{이름}"
        for 직업, 정보 in gf.직업_레지스트리.items()
        for 이름, 스킬 in 정보["스킬목록"].items()
        for 자료 in (스킬, 스킬.get("특성강화") or {})
        if "버프획득" in 자료 and not isinstance(자료["버프획득"], list)
    ]
    assert not 틀림


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
