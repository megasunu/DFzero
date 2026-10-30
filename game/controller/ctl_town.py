# 컨트롤러 - 마을 - 이동, 휴식
# (gameflow.py에서 분리 - N5. 화면은 gameflow.py 창구만 부른다. 설명은 gameflow.py 머리말)

from game.data.buff.status_effects import 상태이상목록
from game.system import drink_system, town_system
from game.controller.ctl_party import 내아내몬_보유, 인형_동기화, 파티_최대치로_회복
from game.controller.ctl_registry import 던전_레지스트리

__all__ = [
    "현재_마을정보",
    "이동가능마을목록",
    "마을_이동",
    "이동가능던전목록",
    "던전_열림",
    "던전목록_표시",
    "휴식",
]


def 현재_마을정보(게임상태):
    마을명 = 게임상태["진행도"]["현재마을"]
    for 마을 in town_system.기본_마을목록():
        if 마을["마을명"] == 마을명:
            return 마을
    return town_system.기본_마을목록()[0]


def 이동가능마을목록(게임상태):
    return town_system.이동가능마을목록(
        town_system.기본_마을목록(),
        게임상태["진행도"],
    )


def 마을_이동(게임상태, 목표마을명):
    town_system.마을_이동(게임상태["진행도"], 목표마을명)


def 이동가능던전목록(게임상태):
    return town_system.이동가능던전목록(현재_마을정보(게임상태))


def 휴식(게임상태):
    # 인형은 마을 휴식으로 사라진다(인형사) - 내아내몬 보유자가 있으면 남아서 같이 회복한다
    인형 = 게임상태["파티"].get("인형")
    if 인형 and 내아내몬_보유(게임상태):
        인형_동기화(게임상태)
        인형["현재HP"] = 인형["기본최대HP"]
    else:
        게임상태["파티"]["인형"] = None
    town_system.휴식_처리(게임상태["파티"])
    for 캐릭터 in 게임상태["파티"]["파티원"]:  # 취기/만취는 휴식으로 풀린다
        캐릭터["상태이상"] = drink_system.휴식_해제(
            캐릭터.get("상태이상") or [], 상태이상목록
        )
    # town_system은 장비를 모르므로 장비 반영 최대치로 다시 채운다.
    파티_최대치로_회복(게임상태)


def 던전_열림(게임상태, 던전파일명):
    """D02~D10, D12~D17은 바로 앞 번호 던전의 보스를 깨야 열린다(town_system.던전_열림)."""
    return town_system.던전_열림(던전파일명, 게임상태["진행도"], 던전_레지스트리)


def 던전목록_표시(게임상태):
    """[던전 이동] 화면용 [(파일명, 표시이름, 열림, 목록그림), ...] - 마을 던전 목록 순서.
    목록그림은 이름 대신 버튼으로 보여 줄 game/assets/dungeon/ 배너 파일명(없으면 None)."""
    return [
        (
            파일명,
            던전_레지스트리.get(파일명, {}).get("지도명", 파일명),
            던전_열림(게임상태, 파일명),
            던전_레지스트리.get(파일명, {}).get("목록그림"),
        )
        for 파일명 in 이동가능던전목록(게임상태)
    ]
