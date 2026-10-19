# 컨트롤러 - 도감 - 메뉴 [도감] 화면용 분류/목록/등록 현황
# (화면은 gameflow.py 창구만 부른다. 설명은 gameflow.py 머리말)
#
# 기록과 목록 규칙은 collection_system.py. 등록은 아이템이 들어오는 곳(ctl_rewards/ctl_potion/
# ctl_shop/ctl_session/ctl_tavern)이 collection_system을 직접 부른다.

from game.data.collection.collection_monster import 도감_출현장소
from game.data.monster.monster_drop import 드랍표_모음
from game.system import collection_system
from game.controller.ctl_registry import 몬스터목록
from game.controller.ctl_shop import 상점_탭목록, 상점_탭줄

__all__ = [
    "_재료탭",
    "_항목들",
    "_이름",
    "_글",
    "도감_대분류목록",
    "도감_탭줄",
    "도감_목록",
    "도감_장비필터_기본",
    "도감_장비필터_바꾸기",
    "도감_장비필터_선택지",
    "도감_장비필터_목록",
    "도감_등록현황",
    "도감_몬스터_상세",
]

도감_대분류목록 = list(collection_system.도감_대분류)


def _재료탭(게임상태):
    return collection_system.재료_탭목록(
        게임상태["상점카탈로그"]["재료"], 몬스터목록, 드랍표_모음
    )


def 도감_탭줄(게임상태, 대분류):
    """소분류 탭 줄들 - 몬스터는 종족, 장비는 상점과 같은 부위 2줄, 소모품은 [포션], 재료는 재료 탭."""
    if 대분류 == "몬스터":
        return [collection_system.몬스터_종족목록(몬스터목록)]
    if 대분류 == "장비":
        return 상점_탭줄("판매", "장비")
    if 대분류 == "소모품":
        return [["포션"]]
    return [list(_재료탭(게임상태))]


def _항목들(게임상태, 대분류, 탭):
    카탈로그 = 게임상태["상점카탈로그"]
    if 대분류 == "몬스터":
        return collection_system.몬스터_목록(몬스터목록, 탭)
    if 대분류 == "장비":
        return collection_system.장비_목록(카탈로그["장비"], 탭)
    if 대분류 == "소모품":
        return collection_system.소모품_목록(카탈로그["소모품"])
    return _재료탭(게임상태).get(탭, [])


def _이름(대분류, 항목):
    return 항목["몬스터명"] if 대분류 == "몬스터" else 항목["이름"]


def 도감_목록(게임상태, 대분류, 탭):
    """[(데이터, 등록여부)] - 등록하지 않은 것도 목록에 있다(화면이 어둡게 보여준다)."""
    진행도 = 게임상태["진행도"]
    return [
        (항목, collection_system.등록됨(진행도, 대분류, _이름(대분류, 항목)))
        for 항목 in _항목들(게임상태, 대분류, 탭)
    ]


도감_장비필터_기본 = dict(collection_system.장비필터_기본)


def 도감_장비필터_바꾸기(필터, 키, 값):
    """장비 도감 고르는 상자 하나를 바꾼 새 필터(그 아래 분류는 전체로)."""
    return collection_system.장비필터_바꾸기(필터, 키, 값)


def 도감_장비필터_선택지(게임상태, 필터):
    """{"상위"/"중위"/"하위"/"레어도": [전체, ...]} - 고를 수 없는 상자는 []."""
    return collection_system.장비필터_선택지(게임상태["상점카탈로그"]["장비"], 필터)


def 도감_장비필터_목록(게임상태, 필터):
    """[(장비, 등록여부)] - 필터를 통과한 장비를 부위 탭 순서대로."""
    장비들 = collection_system.장비필터_목록(
        게임상태["상점카탈로그"]["장비"], 상점_탭목록("장비"), 필터
    )
    진행도 = 게임상태["진행도"]
    return [(a, collection_system.등록됨(진행도, "장비", a["이름"])) for a in 장비들]


def 도감_등록현황(게임상태, 대분류):
    """(등록한 수, 전체 수) - 그 대분류의 모든 소분류를 합친다."""
    탭들 = [t for 줄 in 도감_탭줄(게임상태, 대분류) for t in 줄]
    if 대분류 == "소모품":
        탭들 = 탭들[:1]  # 소모품은 탭이 하나라도 같은 목록이다
    목록 = [항목 for 탭 in 탭들 for 항목 in 도감_목록(게임상태, 대분류, 탭)]
    return sum(1 for _, 등록 in 목록 if 등록), len(목록)


def _글(값):
    if isinstance(값, (list, tuple)):
        return ", ".join(map(str, 값))
    return str(값)


def 도감_몬스터_상세(이름):
    """몬스터 [상세보기] 줄들 - 종족, 등급, 출현장소(도감 자료 collection_monster.py의 글)."""
    몬스터 = 몬스터목록[이름]
    return [
        f"종족: {몬스터['분류']}",
        f"등급: {_글(몬스터['적등급'])}",
        f"출현장소: {_글(도감_출현장소.get(이름, '미정'))}",
    ]
