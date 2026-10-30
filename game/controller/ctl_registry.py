# 컨트롤러 - 데이터 배선 - 몬스터/직업/전직/던전/마을 레지스트리와 전투용 특성 정의 테이블
# (gameflow.py에서 분리 - N5. 화면은 gameflow.py 창구만 부른다. 설명은 gameflow.py 머리말)

from game.data.character.job_info import 직업정보
import importlib
from game.data.ability.job_ability_0000 import 특성목록 as 공용특성
from game.data.dungeon.dungeon_01A_D01_Lorien import 맵정보 as _로리엔
from game.data.dungeon.dungeon_01A_D02_Hollow_Lorien import 맵정보 as _로리엔안쪽
from game.data.dungeon.dungeon_01A_D03_mirkwood import 맵정보 as _머크우드
from game.data.dungeon.dungeon_01A_D04_Hollow_mirkwood import (
    맵정보 as _머크우드깊숙한곳,
)
from game.data.dungeon.dungeon_01A_D05_thunderland import 맵정보 as _선더랜드
from game.data.dungeon.dungeon_01A_D06_poison_thunderland import (
    맵정보 as _포이즌선더랜드,
)
from game.data.dungeon.dungeon_01A_D07_frost_mirkwood import 맵정보 as _프로스트머크우드
from game.data.dungeon.dungeon_01A_D08_grakquarak import 맵정보 as _그락카락
from game.data.dungeon.dungeon_01A_D09_blazing_grakquarak import (
    맵정보 as _불타는그락카락,
)
from game.data.dungeon.dungeon_01A_D10_shadow_thunderland import (
    맵정보 as _어둠의선더랜드,
)
from game.data.dungeon.dungeon_02A_D11_amon_lower import 맵정보 as _아몬하층
from game.data.dungeon.dungeon_02A_D12_amon_upper import 맵정보 as _아몬상층
from game.data.dungeon.dungeon_02A_D13_sephiroth_lower import 맵정보 as _세피로타하층
from game.data.dungeon.dungeon_02A_D14_sephiroth_upper import 맵정보 as _세피로타상층
from game.data.dungeon.dungeon_02A_D15_middleocean_shallow import (
    맵정보 as _미들오션천해,
)
from game.data.dungeon.dungeon_02A_D16_middleocean_deep import 맵정보 as _미들오션심해
from game.data.dungeon.dungeon_02A_D17_floating_castle import 맵정보 as _부유성
from game.data.job_level.job_level_000x_style import 전투스타일
from game.data.monster.monster_ability import 특성목록 as _몬스터특성
from game.data.monster.monster_defaults import 몬스터_기본값
from game.data.monster.monster_race_dragon import 몬스터목록 as _용족몬스터
from game.data.monster.monster_race_goblin import 몬스터목록 as _고블린몬스터
from game.data.monster.monster_race_golem import 몬스터목록 as _골렘몬스터
from game.data.monster.monster_race_expeller import 몬스터목록 as _익스펠러몬스터
from game.data.monster.monster_race_etc import 몬스터목록 as _기타몬스터
from game.data.monster.monster_race_human import 몬스터목록 as _인간몬스터
from game.data.monster.monster_race_lugaru import 몬스터목록 as _루가루몬스터
from game.data.monster.monster_race_spacefish import 몬스터목록 as _공어몬스터
from game.data.monster.monster_race_tau import 몬스터목록 as _타우몬스터
from game.data.monster.monster_race_test import 몬스터목록 as _시험몬스터
from game.data.monster.monster_race_zombie import 몬스터목록 as _좀비몬스터
from game.data.town.town_01A_T01_Elvengard import 마을정보 as _엘븐가드
from game.data.town.town_01A_T02_hendonmyre import 마을정보 as _헨돈마이어
from game.data.town.town_02A_T03_westcoast import 마을정보 as _웨스트코스트

__all__ = [
    "_몬스터파일목록",
    "_몬스터목록_합치기",
    "몬스터목록",
    "직업_데이터파일",
    "_데이터모듈",
    "_직업정보_불러오기",
    "직업_레지스트리",
    "직업목록",
    "_전직정보_생성",
    "전직_레지스트리",
    "전직_시작레벨",
    "전투용_몬스터특성정의",
    "전투용_캐릭터특성정의",
    "던전_레지스트리",
    "마을파일_레지스트리",
    "플레이어레벨업_트리거",
]


_몬스터파일목록 = [
    ("monster_race_goblin", _고블린몬스터),
    ("monster_race_tau", _타우몬스터),
    ("monster_race_lugaru", _루가루몬스터),
    ("monster_race_human", _인간몬스터),
    ("monster_race_zombie", _좀비몬스터),
    ("monster_race_dragon", _용족몬스터),
    ("monster_race_golem", _골렘몬스터),
    ("monster_race_expeller", _익스펠러몬스터),
    # 공왕 크로쿠타는 특성 "공어의 왕"과 드랍군 "공어공용군"이 미정이라 아직 뺀다(공어·대공어만, 2026-10-30)
    (
        "monster_race_spacefish",
        {k: v for k, v in _공어몬스터.items() if k != "공왕 크로쿠타"},
    ),
    ("monster_race_etc", _기타몬스터),
    ("monster_race_test", _시험몬스터),
]


def _몬스터목록_합치기(파일목록):
    """종족별 몬스터목록을 하나로 합친다. 같은 이름이 두 파일에 있으면
    어느 파일끼리 겹치는지 적어 오류를 낸다(게임 시작 시 멈춤 - 한쪽이
    조용히 덮어써지는 것을 막는다). 항목에 없는 칸은 몬스터_기본값으로 채운
    사본을 쓴다(적힌 칸의 순서와 값은 그대로)."""
    합친목록, 출처, 겹침 = {}, {}, []
    for 파일명, 목록 in 파일목록:
        for 이름, 데이터 in 목록.items():
            if 이름 in 합친목록:
                겹침.append(f"'{이름}' ({출처[이름]} / {파일명})")
            합친목록[이름] = {
                **데이터,
                **{k: v for k, v in 몬스터_기본값.items() if k not in 데이터},
            }
            출처[이름] = 파일명
    if 겹침:
        raise ValueError("몬스터 이름이 겹친다: " + ", ".join(겹침))
    return 합친목록


몬스터목록 = _몬스터목록_합치기(_몬스터파일목록)


# 직업 이름 -> {"레벨업테이블", "특성목록"(그 직업 계열 특성 전체),
# "무기목록", "스킬목록"} 딕셔너리. 새 직업 파일이 추가되면 이 레지스트리
# 에도 손으로 import + 항목 추가를 해줘야 한다(town_system.기본_마을목록
# 처럼, 이 프로젝트에는 아직 자동 스캔 레지스트리 패턴이 없다).

# 직업 하나 = 데이터 파일 한 벌. 파일명 규칙(분류코드 "010m" 등, 영문명):
#   job_level/job_level_{분류코드}_{영문명}.py   레벨업테이블, 전직목록
#   job_skill/job_skill_{분류코드}_{영문명}.py   스킬목록
#   ability/job_ability_{분류코드}.py            특성목록
#   perks/perks_class_{분류코드}.py              퍽목록
#   equipment/eq_01_weapon_{분류번호}.py         {직업}무기목록 (분류번호 = 분류코드 앞 3자리)
# 새 직업은 파일을 이 규칙대로 만들고 game/data/character/job_info.py 직업정보에 한 항목 더하면 된다.
직업_데이터파일 = {
    직업: (정보["분류코드"], 정보["영문명"]) for 직업, 정보 in 직업정보.items()
}


def _데이터모듈(경로):
    return importlib.import_module(f"game.data.{경로}")


def _직업정보_불러오기(직업, 분류코드, 영문명):
    return {
        "레벨업테이블": _데이터모듈(
            f"job_level.job_level_{분류코드}_{영문명}"
        ).레벨업테이블,
        "특성목록": _데이터모듈(f"ability.job_ability_{분류코드}").특성목록,
        "무기목록": getattr(
            _데이터모듈(f"equipment.eq_01_weapon_{분류코드[:3]}"), f"{직업}무기목록"
        ),
        "스킬목록": _데이터모듈(f"job_skill.job_skill_{분류코드}_{영문명}").스킬목록,
        "퍽목록": _데이터모듈(f"perks.perks_class_{분류코드}").퍽목록,
    }


직업_레지스트리 = {
    직업: _직업정보_불러오기(직업, *파일) for 직업, 파일 in 직업_데이터파일.items()
}


직업목록 = list(직업_레지스트리.keys())


# 1차 전직 레지스트리: {1차 계열 직업: {전직명: 정보}}.
# 데이터는 각 1차 계열 job_level_XX.py 하단 "전직목록"({전직명: {"분류번호",
# "레벨업테이블파일"}})이다. "레벨업테이블파일"이 있으면 그 파일(레벨 6~20)과
# 이름이 대응하는 job_skill 파일(job_level_ → job_skill_)을 불러와 "구현":True,
# None이면 "구현":False(선택창에 미구현으로 보이고 고를 수 없음). 레벨 5
# 캐릭터가 [레벨업]을 누르면 구현된 것 중 하나를 골라 레벨 6이 된다.
def _전직정보_생성(항목):
    파일명 = 항목.get("레벨업테이블파일")
    정보 = {
        "분류번호": str(항목.get("분류번호") or "")[:3],
        "구현": False,
        "레벨업테이블": {},
        "스킬목록": {},
        "직업스타일": None,
    }
    if not 파일명:
        return 정보
    모듈 = importlib.import_module(f"game.data.job_level.{파일명}")
    정보["레벨업테이블"] = 모듈.레벨업테이블
    정보["직업스타일"] = getattr(모듈, "직업스타일", None)
    try:
        정보["스킬목록"] = importlib.import_module(
            f"game.data.job_skill.{파일명.replace('job_level_', 'job_skill_', 1)}"
        ).스킬목록
    except ImportError:
        정보["스킬목록"] = {}
    정보["구현"] = True
    return 정보


전직_레지스트리 = {
    직업: {
        전직명: _전직정보_생성(항목)
        for 전직명, 항목 in _데이터모듈(
            f"job_level.job_level_{분류코드}_{영문명}"
        ).전직목록.items()
    }
    for 직업, (분류코드, 영문명) in 직업_데이터파일.items()
}


전직_시작레벨 = 6


# 전투_시작()에 넘길 특성 정의 테이블.
# - 몬스터용: monster_ability.py 특성목록(몬스터 종족특성 전부) + 공용 특성(job_ability_0000.py).
# - 캐릭터용: 공용 특성 + 5직업 계열 특성 전부(캐릭터 "보유특성" 이름을
#   이 테이블에서 찾는다 - 지금은 AC 계산에만 쓰인다).
전투용_몬스터특성정의 = {**공용특성, **_몬스터특성}


전투용_캐릭터특성정의 = dict(공용특성)


전투용_캐릭터특성정의.update(전투스타일)


for _직업정보 in 직업_레지스트리.values():
    전투용_캐릭터특성정의.update(_직업정보["특성목록"])


# 던전(소형지도) 레지스트리 - 01A 지역 던전 10개 + 02A(하늘성) 던전 6개.
# town_system.py의 "기본_마을목록()"과 같은 이유로, 새 던전 파일이
# 추가되면 여기에도 손으로 import + 등록을 해줘야 한다.
던전_레지스트리 = {
    "dungeon_01A_D01_Lorien": _로리엔,
    "dungeon_01A_D02_Hollow_Lorien": _로리엔안쪽,
    "dungeon_01A_D03_mirkwood": _머크우드,
    "dungeon_01A_D04_Hollow_mirkwood": _머크우드깊숙한곳,
    "dungeon_01A_D05_thunderland": _선더랜드,
    "dungeon_01A_D06_poison_thunderland": _포이즌선더랜드,
    "dungeon_01A_D07_frost_mirkwood": _프로스트머크우드,
    "dungeon_01A_D08_grakquarak": _그락카락,
    "dungeon_01A_D09_blazing_grakquarak": _불타는그락카락,
    "dungeon_01A_D10_shadow_thunderland": _어둠의선더랜드,
    "dungeon_02A_D11_amon_lower": _아몬하층,
    "dungeon_02A_D12_amon_upper": _아몬상층,
    "dungeon_02A_D13_sephiroth_lower": _세피로타하층,
    "dungeon_02A_D14_sephiroth_upper": _세피로타상층,
    "dungeon_02A_D15_middleocean_shallow": _미들오션천해,
    "dungeon_02A_D16_middleocean_deep": _미들오션심해,
    "dungeon_02A_D17_floating_castle": _부유성,
}


# 연결지역의 "연결맵"(마을 파일명) -> 마을정보. 던전 끝의 "#"으로 나가면
# 그 파일의 마을로 돌아간다(진행도["현재마을"]을 그 마을명으로 바꾼다).
마을파일_레지스트리 = {
    "town_01A_T01_Elvengard": _엘븐가드,
    "town_01A_T02_hendonmyre": _헨돈마이어,
    "town_02A_T03_westcoast": _웨스트코스트,
}


# 던전 보스를 "처음" 클리어했을 때 플레이어 레벨을 이 값으로 올린다(max()
# 처리). 로리엔(01)은 없음, 짝수 던전 보스마다 +2 - 로리엔 안쪽 2,
# 머크우드 깊숙한곳 4, 포이즌 선더랜드 6, 그락카락 8, 어둠의 선더랜드 10.
플레이어레벨업_트리거 = {
    ("dungeon_01A_D02_Hollow_Lorien", (15, 3)): 2,
    ("dungeon_01A_D04_Hollow_mirkwood", (15, 3)): 4,
    ("dungeon_01A_D06_poison_thunderland", (25, 3)): 6,
    ("dungeon_01A_D08_grakquarak", (25, 3)): 8,
    ("dungeon_01A_D10_shadow_thunderland", (35, 3)): 10,
}
