# 컨트롤러 - 스킬 습득 - 지금 직업 계열의 스킬을 골드(50 x 차수)를 내고 배운다(skill_learn_system.py)
# (gameflow.py에서 분리 - N5. 화면은 gameflow.py 창구만 부른다. 설명은 gameflow.py 머리말)
#
# 지금 직업 계열의 스킬을 골드(50 x 차수)를 내고 배운다 - skill_learn_system.py.

from game.system import skill_learn_system
from game.controller.ctl_registry import 전직_레지스트리, 직업_레지스트리

__all__ = [
    "_차수별_스킬목록",
    "_상세값",
    "_스킬_상세글",
    "캐릭터_습득가능_스킬",
    "캐릭터_스킬_습득",
    "캐릭터_배운스킬_골드",
]


def _차수별_스킬목록(캐릭터):
    """[(1, 1차 계열 스킬목록), (2, 1차 전직 스킬목록)] - 전직 전이면 1차만."""
    결과 = [(1, 직업_레지스트리[캐릭터["직업"]]["스킬목록"])]
    전직정보 = 전직_레지스트리.get(캐릭터["직업"], {}).get(캐릭터.get("전직"))
    if 전직정보:
        결과.append((2, 전직정보["스킬목록"]))
    return 결과


def _상세값(값):
    if isinstance(값, bool):
        return "예" if 값 else "아니오"
    if isinstance(값, dict):
        return "{" + ", ".join(f"{k}: {_상세값(v)}" for k, v in 값.items()) + "}"
    if isinstance(값, (list, tuple)):
        return ", ".join(_상세값(v) for v in 값) if 값 else "없음"
    return "없음" if 값 is None else str(값)


def _스킬_상세글(스킬):
    """[스킬습득] 상세보기 팝업 글 - 설명을 먼저, 그 밖의 스킬 데이터를 전부
    "키: 값" 줄로(데이터 순서)."""
    줄 = [f"{키}: {_상세값(값)}" for 키, 값 in 스킬.items() if 키 != "설명"]
    return "\n\n".join(글 for 글 in (스킬.get("설명", ""), "\n".join(줄)) if 글)


def 캐릭터_습득가능_스킬(캐릭터):
    """[(스킬이름, 비용, 상세글)] - [스킬습득] 팝업 목록."""
    return [
        (이름, 비용, _스킬_상세글(스킬))
        for 이름, _차수, 비용, 스킬 in skill_learn_system.습득가능_스킬목록(
            캐릭터, _차수별_스킬목록(캐릭터)
        )
    ]


def 캐릭터_스킬_습득(게임상태, 캐릭터, 스킬이름):
    """골드를 내고 스킬을 배운다. 낸 골드를 반환한다. 실패하면 ValueError."""
    return skill_learn_system.스킬_습득(
        캐릭터,
        게임상태["소지품"],
        스킬이름,
        _차수별_스킬목록(캐릭터),
        특성정의모음=직업_레지스트리[캐릭터["직업"]]["특성목록"],
    )


def 캐릭터_배운스킬_골드(캐릭터):
    """[스킬습득]으로 배운 스킬 값의 합 - 레테의 강물이 돌려준다(skill_learn_system.배운스킬_골드)."""
    return skill_learn_system.배운스킬_골드(캐릭터, _차수별_스킬목록(캐릭터))
