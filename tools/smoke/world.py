"""화면 스모크 단계 - 던전 지도 칸·출입구·목록 스크롤·화면 배치·던전 목록과 스킬·마을 이동·NPC·화면 틀."""

# common을 먼저 불러 kivy 창 설정을 끝낸다.
from tools.smoke.common import (
    _NPC그림폴더,
    _대상버튼들,
    _뒤로키,
    _스크롤_확인,
    _아군_차례로,
    _찍기,
    _팝업_닫기,
    _팝업_버튼,
    _팝업글,
    _팝업수,
    결과,
)
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
import gameflow as gf
from game.screens import screens_common, screens_party
from game.system import quest_system
from tests import support


class 세계단계:
    def _단계_맵_타일(self, 상태, 매니저):
        """하늘성 탑(아몬 상층)이 맵정보 "타일"의 그림(발판/벽/하늘, 포탈은 벽 위 하늘성
        게이트)으로, 로리엔 보스의 세리아 감옥이 2x2칸 크기로 그려지는지"""
        from kivy.graphics import Rectangle

        def 그린_사각형(지도):
            return [c for c in 지도.canvas.children if isinstance(c, Rectangle)]

        _팝업_닫기()
        gf.던전_진입(상태, "dungeon_02A_D12_amon_upper")
        상태["던전상태"]["위치"] = (
            4,
            16,
        )  # 왼쪽 아래 - 발판/벽/하늘/마을 포탈이 보인다
        매니저.current = "던전"
        던전 = 매니저.get_screen("던전")
        던전.갱신()
        yield 0.5
        지도 = 던전.지도위젯
        그린것 = {id(c.texture) for c in 그린_사각형(지도) if c.texture is not None}
        for 기호 in ("O", "X", "Y", "#"):
            텍스처들 = 지도._맵_타일(기호)
            assert 텍스처들, (기호, "타일 그림을 못 읽음")
            for 텍스처 in 텍스처들:
                assert id(텍스처) in 그린것, (기호, "맵 타일이 그려지지 않음")
        assert len(지도._맵_타일("#")) == 2  # 벽 위에 게이트
        # 칸은 정사각형, 짧은 쪽(세로)에 9칸, 가로로 긴 위젯이면 가로 칸이 더 많다
        칸폭, 칸높이 = 지도._칸_크기()
        assert abs(칸폭 - 칸높이) < 0.01, (칸폭, 칸높이)
        assert 지도._행수 == 9 and 지도._열수 >= 지도._행수, (지도._열수, 지도._행수)
        assert 지도._열수 * 칸폭 >= 지도.width, "가로 끝까지 칸을 그리지 않음"
        assert 지도._타일("풀밭") is None or id(지도._타일("풀밭")) not in 그린것
        _찍기("dungeon_map_tiles")
        # 플레이어 그림: 직업(그림 크기)이 달라도 도트 하나 크기가 같고, 원래 비율로 칸 가운데에 선다
        원래코드 = 지도.초상화코드
        도트들 = set()
        for 코드 in ("034f", "073m"):  # 가장 작은 그림(22x36)과 가장 넓은 그림(71x48)
            지도.초상화코드 = 코드
            지도._다시그리기()
            yield 0.2
            사각 = 지도._플레이어_사각
            tw, th = 사각.texture.size
            assert abs(사각.size[0] / tw - 사각.size[1] / th) < 0.01, (코드, 사각.size)
            assert 사각.texture.mag_filter == "nearest"
            x, _ = 지도._칸위치(지도._열수 // 2, 지도._행수 // 2)
            assert abs(사각.pos[0] + 사각.size[0] / 2 - (x + 칸폭 / 2)) < 1
            도트들.add(round(사각.size[0] / tw, 3))
            _찍기(f"dungeon_player_dot_{코드}")
        assert len(도트들) == 1 and 도트들.pop() >= 1, 도트들
        지도.초상화코드 = 원래코드
        지도._다시그리기()
        결과["단계"].append(
            "던전 지도 플레이어 그림 - 직업(그림 크기)이 달라도 같은 도트 배율, 원래 비율, 칸 가운데"
        )

        # 로리엔 보스(15,3) - 세리아 감옥은 한 칸이지만 2x2칸 크기로, 바닥 위/플레이어 아래
        gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
        상태["던전상태"]["위치"] = (14, 3)
        던전.갱신()
        yield 0.5
        칸폭, 칸높이 = 지도._칸_크기()
        사각형들 = 그린_사각형(지도)
        감옥 = [
            i
            for i, c in enumerate(사각형들)
            if abs(c.size[0] - 칸폭 * 2) < 1 and abs(c.size[1] - 칸높이 * 2) < 1
        ]
        assert 감옥, "감옥이 2x2칸 크기로 그려지지 않음"
        # 출입구("#") 칸은 감옥보다 위에 그린다(_단계_출입구_위) - 바닥 비교에서 뺀다
        출입구칸 = [
            지도._칸위치(화면x, 화면y)
            for 화면y in range(지도._행수)
            for 화면x in range(지도._열수)
            if 지도._칸_문자(*지도._맵_좌표(화면x, 화면y)) == "#"
        ]

        def 출입구에(c):  # 캔버스 좌표는 float32라 조금 어긋난다
            return any(
                abs(c.pos[0] - x) < 1 and abs(c.pos[1] - y) < 1 for x, y in 출입구칸
            )

        assert 출입구칸, "로리엔 보스 옆 출입구가 안 보임"
        칸들 = [
            i
            for i, c in enumerate(사각형들)
            if abs(c.size[0] - 칸폭) < 1
            and abs(c.size[1] - 칸높이) < 1
            and not 출입구에(c)
        ]
        assert max(칸들) < 감옥[0], "감옥이 바닥보다 먼저 그려짐"
        assert any(출입구에(c) for c in 사각형들[감옥[0] :]), (
            "출입구가 감옥보다 먼저 그려짐"
        )
        assert 지도.canvas.children[-1] is not 사각형들[감옥[0]]  # 플레이어가 맨 위
        # 감옥은 보스 칸에서 한 칸 아래 중심
        보스위치 = next(
            지도._칸위치(화면x, 화면y)
            for 화면y in range(지도._행수)
            for 화면x in range(지도._열수)
            if 지도._맵_좌표(화면x, 화면y) == (15, 3)
        )
        감옥칸 = 사각형들[감옥[0]]
        assert (
            abs(감옥칸.pos[1] + 감옥칸.size[1] / 2 - (보스위치[1] - 칸높이 / 2)) < 2
        ), (
            감옥칸.pos,
            보스위치,
        )
        _찍기("dungeon_prison_2x2")
        gf.던전_진입(상태, "dungeon_02A_D11_amon_lower")
        상태["던전상태"]["위치"] = (19, 3)  # 아몬 하층 보스(19,1) 아래 - 로리안 감옥
        던전.갱신()
        yield 0.5
        로리안 = 지도._오브젝트_타일(19, 1)
        assert 로리안 is not None, "로리안 감옥 그림을 못 읽음"
        assert any(
            c.texture is not None
            and c.texture.size != (0, 0)
            and abs(c.size[0] - 칸폭 * 2) < 1
            for c in 그린_사각형(지도)
        ), "로리안 감옥이 2x2칸으로 그려지지 않음"
        _찍기("dungeon_prison_lorien")
        # 포탈로 이어진 맵을 함께 그린다 - 아몬 하층 천장 포탈(19,0) 위로 상층이
        # 이어진다(상층 (19,18) 발판이 하층 좌표 (19,-1)), 이웃 맵의 "@"는 감춘다
        assert 지도._칸_문자(19, -1) == "O", 지도._칸_문자(19, -1)
        assert 지도._칸_문자(3, -1) == "O"  # 상층 마을 포탈 앞 보스 -> 발판으로
        assert 지도._칸_문자(19, 0) == "#"  # 겹친 포탈 칸은 지금 맵
        # 한 번 클리어한 로리엔 감옥 보스는 다시 들어오면 감옥 대신 보스 몬스터 그림(비율 유지)
        from game.system import town_system

        town_system.오브젝트_클리어_기록(
            상태["진행도"], "dungeon_01A_D01_Lorien", (15, 3)
        )
        gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
        상태["던전상태"]["위치"] = (14, 3)
        던전.갱신()
        yield 0.5
        assert 지도._보스그림인가(15, 3)
        보스 = 지도._오브젝트_타일(15, 3)
        assert 보스 is not None and 보스 is not 지도._파일_타일(
            "asset_tile_prison_seria.webp"
        )
        _찍기("dungeon_prison_cleared_boss")
        # 잘라 그리기(get_region)라 같은 GL 텍스처의 조각이다 - id로 찾는다
        보스칸 = [
            c
            for c in 그린_사각형(지도)
            if c.texture is not None and c.texture.id == 보스.id
        ]
        assert len(보스칸) == 1, len(보스칸)
        tw, th = 보스.size
        크기 = 보스칸[0].size
        assert abs(크기[0] / 크기[1] - tw / th) < 0.05, (
            "보스 그림 비율",
            크기,
            보스.size,
        )
        # 보스 그림은 1칸 안(2x2는 감옥만)
        칸폭, 칸높이 = 지도._칸_크기()
        assert 크기[0] <= 칸폭 + 1 and 크기[1] <= 칸높이 + 1, (크기, 칸폭)
        상태["진행도"]["클리어한오브젝트"].discard(("dungeon_01A_D01_Lorien", (15, 3)))
        # 감옥이 없는 보스(로리엔 안쪽 타우 아미)는 처음부터 보스 그림, 아래 칸(15,4) 나무의
        # 위 절반보다 나중에 그린다
        gf.던전_진입(상태, "dungeon_01A_D02_Hollow_Lorien")
        상태["던전상태"]["위치"] = (14, 3)
        던전.갱신()
        yield 0.5
        assert 지도._보스그림인가(15, 3)
        보스 = 지도._오브젝트_타일(15, 3)
        사각형들 = 그린_사각형(지도)
        보스번호 = [
            i
            for i, c in enumerate(사각형들)
            if c.texture is not None and c.texture.id == 보스.id
        ]
        나무 = 지도._높은타일_반쪽("나무")[1]
        나무번호 = [
            i
            for i, c in enumerate(사각형들)
            if c.texture is not None and c.texture.id == 나무.id
        ]
        assert len(보스번호) == 1 and 나무번호 and 보스번호[0] > max(나무번호), (
            보스번호,
            나무번호[-3:],
        )
        _찍기("dungeon_boss_over_tree")
        결과["단계"].append(
            "감옥 보스전은 한 번 클리어하면 보스 칭호 몬스터 그림(1칸)으로, 감옥은 한 칸 아래, "
            "감옥 없는 보스는 처음부터 그림이고 나무보다 위"
        )
        gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
        상태["던전상태"]["위치"] = (14, 3)  # 보스(감옥) 왼쪽 - 오른쪽에 로리엔 안쪽
        던전.갱신()
        yield 0.5
        assert 지도._칸_문자(17, 3) == "O", "로리엔 오른쪽에 로리엔 안쪽이 안 이어짐"
        _찍기("dungeon_neighbor_maps")
        상태["던전상태"] = None
        매니저.current = "마을"
        yield 0.3
        결과["단계"].append(
            "맵 타일(하늘성 발판/벽/노을 하늘/게이트 겹침), 정사각형 칸, 감옥 2x2칸(바닥 위, 플레이어 아래), 이어진 맵 함께 보이기"
        )

    def _단계_출입구_위(self, 상태, 매니저):
        """출입구("#")는 한 칸 그림으로, 나무/큰 오브젝트를 다 그린 뒤(플레이어 아래)에
        그려서 가려지지 않는다 - 그란플로리스(로리엔)와 하늘성(아몬 상층) 둘 다"""
        from kivy.graphics import Rectangle

        _팝업_닫기()
        매니저.current = "던전"
        던전 = 매니저.get_screen("던전")
        지도 = 던전.지도위젯

        def 사각형들():
            return [c for c in 지도.canvas.children if isinstance(c, Rectangle)]

        def 마지막(텍스처):
            # 잘라 그리기(get_region) 조각도 같은 GL 텍스처라 id로 찾는다
            return max(
                (
                    i
                    for i, c in enumerate(사각형들())
                    if c.texture is not None and c.texture.id == 텍스처.id
                ),
                default=-1,
            )

        # 로리엔 서쪽 출입구(0,3) - 바로 아래(0,4)가 나무라 그 위 절반이 출입구 칸에 겹친다
        gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
        상태["던전상태"]["위치"] = (2, 3)
        던전.갱신()
        yield 0.5
        assert 지도._칸_문자(0, 3) == "#" and 지도._칸_문자(0, 4) == "X"
        게이트 = 지도._타일("게이트")
        assert 게이트 is not None, "그란플로리스 게이트 그림을 못 읽음"
        assert 게이트.size == (8, 8), ("게이트 그림이 한 칸이 아님", 게이트.size)
        칸폭, 칸높이 = 지도._칸_크기()
        게이트칸 = [
            c for c in 사각형들() if c.texture is not None and c.texture.id == 게이트.id
        ]
        assert 게이트칸 and all(
            abs(c.size[0] - 칸폭) < 1 and abs(c.size[1] - 칸높이) < 1 for c in 게이트칸
        ), "게이트가 한 칸 크기로 그려지지 않음"
        assert 마지막(게이트) > 마지막(지도._타일("나무")), "게이트가 나무에 가려짐"
        assert 지도.canvas.children[-1] is not 게이트칸[-1]  # 플레이어가 맨 위
        _찍기("dungeon_gate_grandflores")

        # 아몬 상층 마을 포탈(3,19) - 벽 위 하늘성 게이트도 다른 칸을 다 그린 뒤에
        gf.던전_진입(상태, "dungeon_02A_D12_amon_upper")
        상태["던전상태"]["위치"] = (4, 16)
        던전.갱신()
        yield 0.5
        하늘성 = 지도._맵_타일("#")[-1]
        발판 = 지도._맵_타일("O")[-1]
        assert 마지막(하늘성) > 마지막(발판) >= 0, "하늘성 게이트가 먼저 그려짐"
        _찍기("dungeon_gate_skycastle")
        상태["던전상태"] = None
        매니저.current = "마을"
        yield 0.3
        결과["단계"].append(
            "출입구는 한 칸 그림으로 나무/큰 오브젝트 위(플레이어 아래)에 - 그란플로리스·하늘성"
        )

    def _단계_목록_스크롤(self, 상태, 매니저):
        """상점/장비 교체 목록 스크롤(끌어서 내림)"""
        # 목록 스크롤: 상점 구매/판매/해체[전체], 장비 교체 팝업(소지품) - 항목이 많을 때
        카탈로그 = 상태["상점카탈로그"]["장비"]
        # 봉인을 푼 마법의 장비(1천여 종)는 넣지 않는다 - 목록이 지나치게 길어진다
        for 이름, 데이터 in 카탈로그["무기"].items():
            if 데이터.get("레어도") != "치트" and "마봉능력" not in 데이터:
                상태["소지품"]["장비"][이름] = 상태["소지품"]["장비"].get(이름, 0) + 1
        for 탭 in ("상의", "하의", "어깨", "벨트", "신발"):
            for 이름, 데이터 in 카탈로그[탭].items():
                if "마봉능력" not in 데이터:
                    상태["소지품"]["장비"][이름] = (
                        상태["소지품"]["장비"].get(이름, 0) + 1
                    )
        매니저.current = "상점"
        상점 = 매니저.get_screen("상점")

        def 목록스크롤():
            return next(
                w
                for w in 상점.내용틀.walk(restrict=True)
                if isinstance(w, ScrollView) and w.do_scroll_y
            )

        # S24 세로 화면(1080x2340)에서는 마을 판매 목록이 한 화면에 다 들어간다 -
        # 스크롤을 보려고 이 단계에서만 카탈로그 장비(치트 제외)를 판매 목록에 잠시 더한다.
        판매목록 = gf.현재_마을정보(상태)["상점판매목록"]
        원래_판매목록 = list(판매목록)
        판매목록.extend(
            이름
            for 탭 in 카탈로그.values()
            for 이름, 데이터 in 탭.items()
            if 데이터.get("레어도") != "치트"
            and "마봉능력"
            not in 데이터  # 봉인을 푼 마법의 장비(1천여 종)는 상점 물건이 아니다
            and 이름 not in 원래_판매목록
        )
        try:
            for 모드, 이름 in (
                ("구매", "shop_scroll_buy"),
                ("판매", "shop_scroll_sell"),
                ("해체", "shop_scroll_dismantle"),
            ):
                상점._탭목록_그리기(모드, "장비")
                yield 0.4
                yield from _스크롤_확인(목록스크롤(), f"상점 {모드}")
                _찍기(이름)
        finally:
            판매목록[:] = 원래_판매목록
        매니저.current = "파티원"
        screens_party._장비교체_팝업(상태["파티"]["파티원"][0], "무기", lambda: None)
        yield 0.5
        팝업스크롤 = next(
            w
            for w in list(Window.children)[0].walk(restrict=True)
            if isinstance(w, ScrollView)
        )
        yield from _스크롤_확인(팝업스크롤, "장비 교체 팝업")
        _찍기("equip_swap_scroll")
        _팝업_닫기()
        결과["단계"].append(
            "목록 스크롤(상점 구매/판매/해체, 장비 교체 팝업 - 끌어서 내림, 맨 아래 보임)"
        )

    def _단계_화면_배치(self, 상태, 매니저):
        """마을/던전/전투 - 상단 1170(4줄) + 하단 1170(4줄), 정사각형 200은 같은 간격"""
        sc = screens_common

        def 같은간격(줄, 칸수):
            칸들 = sorted(줄.children, key=lambda w: w.x)
            assert len(칸들) == 칸수, (len(칸들), 칸수)
            for 칸 in 칸들:
                assert (
                    abs(칸.width - sc.정사각형_크기) < 1
                    and abs(칸.height - sc.정사각형_크기) < 1
                ), 칸.size
            간격 = (
                [칸들[0].x - 줄.x]
                + [b.x - a.right for a, b in zip(칸들, 칸들[1:])]
                + [줄.right - 칸들[-1].right]
            )
            assert max(간격) - min(간격) < 1.5, 간격
            return 칸들

        def 파티칸(줄, 칸수):
            """파티원 상자 - 4명이면 양 끝 16, 사이 8만 남기고 줄을 꽉 채운다(폭 256)."""
            칸들 = sorted(줄.children, key=lambda w: w.x)
            assert len(칸들) == 칸수, (len(칸들), 칸수)
            폭 = (줄.width - 2 * sc.하단_좌우여백 - 3 * sc.파티칸_틈) / 4
            assert abs(폭 - 256) < 1, 폭
            for 칸 in 칸들:
                assert abs(칸.width - 폭) < 1 and abs(칸.height - 줄.height) < 1, (
                    칸.size
                )
            assert all(
                abs(b.x - a.right - sc.파티칸_틈) < 1 for a, b in zip(칸들, 칸들[1:])
            ), [c.x for c in 칸들]
            assert abs((칸들[0].x - 줄.x) - (줄.right - 칸들[-1].right)) < 1  # 가운데
            if 칸수 == 4:
                assert abs(칸들[0].x - 줄.x - sc.하단_좌우여백) < 1, 칸들[0].x
            return 칸들

        # 마을: 1줄 파티원 상자(위 끝), 2~4줄 마을 그림(970 칸 아래에 붙음), 하단은 버튼이 위에 붙고 메시지는 그 아래
        매니저.current = "마을"
        마을 = 매니저.get_screen("마을")
        마을.갱신()
        yield 0.4
        파티수 = len(상태["파티"]["파티원"])
        파티칸(마을.파티줄, 파티수)
        assert abs(마을.파티줄.top - sc.기준화면_높이) < 1, 마을.파티줄.top
        그림 = 마을.배경그림
        # 높이는 비율대로, 최대 970(어느 마을 그림이 와도 - 지금 마을 그림 비율에 기대지 않는다)
        기대높이 = min(sc.상단_그림_높이, 그림.width / 그림.image_ratio)
        assert abs(그림.height - 기대높이) < 1, (그림.size, 그림.image_ratio)
        assert abs(그림.y - sc.하단_높이) < 1, 그림.y  # 칸 아래에 붙는다(빈 곳은 위)
        assert abs(그림.norm_image_size[1] - 그림.height) < 1, 그림.norm_image_size
        # 양 옆 끝은 버튼과 같은 16 여백
        assert abs(그림.x - sc.하단_좌우여백) < 1, 그림.x
        assert abs(그림.right - (sc.기준화면_폭 - sc.하단_좌우여백)) < 1, 그림.right
        assert not hasattr(마을, "마을명라벨")
        버튼구역 = next(
            w for w in 마을.메시지라벨.parent.children if w is not 마을.메시지라벨
        )
        # 그림과 버튼 사이 16, 버튼 사이 8, 버튼 양 옆 끝 = 그림 양 옆 끝
        from game.screens import screens_town

        간격 = screens_town.버튼_간격
        assert abs(그림.y - 버튼구역.top - screens_town.그림_버튼_간격) < 1, (
            버튼구역.top
        )
        버튼들 = sorted(
            (w for w in 버튼구역.walk(restrict=True) if isinstance(w, Button)),
            key=lambda w: (-w.y, w.x),
        )
        assert abs(버튼들[0].y - 버튼들[2].top - 간격) < 1, (버튼들[0].y, 버튼들[2].top)
        assert abs(버튼들[0].x - 그림.x) < 1 and abs(버튼들[1].right - 그림.right) < 1
        assert 마을.메시지라벨.top <= 버튼구역.y + 1, (마을.메시지라벨.top, 버튼구역.y)
        # 칸 글은 줄마다 한 줄 - 칸 폭보다 긴 글은 가로로 눌려 칸 폭 안에 그려진다
        줄라벨 = [
            w
            for w in 마을.파티줄.walk(restrict=True)
            if isinstance(w, sc.가로맞춤_라벨)
        ]
        assert len(줄라벨) == 4 * 파티수, len(줄라벨)
        for 라벨 in 줄라벨:
            assert 라벨.texture_size[0] <= 라벨.width, (
                라벨.text,
                라벨.texture_size,
                라벨.width,
            )
        # 상자가 256으로 넓어져 "엘리멘탈마스터"도 그대로 들어간다 - 폭보다 긴 줄만 눌린다
        for r in 줄라벨:
            기대 = [min(r.texture.size[0], r.width - r.여백), r.texture.size[1]]
            assert all(abs(x - y) < 1 for x, y in zip(r.texture_size, 기대)), (
                r.text,
                r.texture_size,
                r.texture.size,
            )
        _찍기("layout_town")

        # 던전: 1줄 파티원 상자, 2~4줄 지도 970, 하단 1줄 던전 이름(위치/걸음수 대신)
        gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
        매니저.current = "던전"
        던전 = 매니저.get_screen("던전")
        던전.갱신()
        yield 0.4
        파티칸(던전.파티줄, 파티수)
        assert abs(던전.지도위젯.height - sc.상단_그림_높이) < 1
        assert abs(던전.지도위젯.y - sc.하단_높이) < 1
        assert 던전.상태라벨.text == "로리엔", 던전.상태라벨.text
        _찍기("layout_dungeon")
        # 인형이 있으면 마을/던전 상단 줄 맨 오른쪽에 인형 칸(이름, HP) - 5칸 기준 폭
        상태["파티"]["인형"] = gf.인형_만들기(상태, "28호")
        상태["장비데이터모음"] = gf.장비데이터모음_생성(
            상태["파티"], 상태["상점카탈로그"]
        )
        던전.갱신()
        yield 0.3
        인형칸 = [w for w in 던전.파티줄.children if getattr(w, "인형칸", False)]
        assert len(인형칸) == 1 and 던전.파티줄.칸수 == gf.파티_최대인원 + 1
        assert 인형칸[0] is 던전.파티줄.children[0], "인형 칸은 맨 오른쪽"
        assert 인형칸[0].right <= 던전.파티줄.right + 1, "인형 칸이 화면 밖으로"
        _찍기("layout_dungeon_doll")
        매니저.get_screen("마을").갱신()
        assert any(
            getattr(w, "인형칸", False)
            for w in 매니저.get_screen("마을").파티줄.children
        ), "마을 상단 줄에 인형 칸이 없다"
        상태["파티"]["인형"] = None
        던전.갱신()

        # 전투: 적 정사각형 / 몬스터 그림 385 / 파티원 그림 385 / 파티원 상자, 하단 1줄 전투 기록
        gf.전투_시작(상태, ["고블린", "고블린", "고블린 투척병"], 레벨=1, 차수=1)
        support.반응_처리(상태)
        _아군_차례로(상태)
        매니저.current = "전투"
        전투 = 매니저.get_screen("전투")
        전투.갱신(신규=True)
        yield 0.6
        적칸 = 같은간격(전투.적상태틀, 3)
        아군칸 = 파티칸(전투.아군상태틀, len(gf.아군_목록(상태)))
        파티칸(전투.아군그래픽행, len(아군칸))
        assert abs(전투.적상태틀.top - sc.기준화면_높이) < 1
        for 줄, 칸들 in ((전투.적그래픽행, 적칸), (전투.아군그래픽행, 아군칸)):
            assert abs(줄.height - sc.그림줄_높이) < 1, 줄.height
            그림칸 = sorted(줄.children, key=lambda w: w.x)
            assert [round(w.center_x) for w in 그림칸] == [
                round(w.center_x) for w in 칸들
            ]
        assert abs(전투.아군상태틀.y - sc.하단_높이) < 1, 전투.아군상태틀.y
        # 전투 칸 글도 짧은 줄은 그대로, 긴 줄만 눌린다
        for 줄 in (전투.적상태틀, 전투.아군상태틀):
            for r in [
                w for w in 줄.walk(restrict=True) if isinstance(w, sc.가로맞춤_라벨)
            ]:
                한계 = r.width - r.여백
                기대 = min(r.texture.size[0], 한계)
                assert abs(r.texture_size[0] - 기대) < 1, (
                    r.text,
                    r.texture_size,
                    r.texture.size,
                    r.width,
                )
        _찍기("layout_battle")
        상태["전투상태"] = None
        상태["던전상태"] = None
        매니저.current = "마을"
        결과["단계"].append(
            "화면 배치(마을/던전/전투 상단 4줄 + 하단, 적 정사각형 200 같은 간격, 파티원 상자 256 꽉 채움, 마을 버튼 세로 가운데, 그림 970/385)"
        )

    def _단계_던전목록(self, 상태, 매니저):
        """던전 이동 목록 - 배너 그림이 버튼이고, 바로 앞 번호 던전 보스를 안 깬 던전은
        어둡게 비활성. 열린 배너를 누르면 그 던전에 들어간다. 그림 없는 하늘성 던전은 이름 버튼."""
        진행도 = 상태["진행도"]
        원래 = (
            진행도["현재마을"],
            set(진행도.get("클리어한던전", set())),
            상태["던전상태"],
        )

        def 목록():
            return {
                w.던전파일명: w
                for w in 매니저.current_screen.목록틀.children
                if hasattr(w, "던전파일명")
            }

        try:
            매니저.current = "던전목록"
            yield 0.3
            로리엔 = 목록()["dungeon_01A_D01_Lorien"]
            assert isinstance(로리엔, screens_common._이미지버튼), 로리엔
            assert 로리엔.source.endswith("asset_banner_lorien.webp"), 로리엔.source
            # 그림 없는 하늘성 던전은 이름 버튼 - 일곱 곳이 번호 순, 아몬 하층만 열림(순서 해금)
            진행도["현재마을"] = "웨스트코스트"
            매니저.current_screen.갱신()
            yield 0.3
            버튼 = 목록()
            아몬 = 버튼["dungeon_02A_D11_amon_lower"]
            assert isinstance(아몬, Button) and 아몬.text == "아몬 하층", 아몬
            assert [
                w.text for w in reversed(매니저.current_screen.목록틀.children)
            ] == [
                "아몬 하층",
                "아몬 상층",
                "세피로타 하층",
                "세피로타 상층",
                "미들오션 천해",
                "미들오션 심해",
                "부유성",
            ]
            assert [f for f, w in 버튼.items() if not w.disabled] == [
                "dungeon_02A_D11_amon_lower"
            ], 버튼
            _찍기("dungeon_list_skycastle")
            # 아몬 하층 보스를 깨면 아몬 상층이 열리고, 목록으로 들어가도 하층에서 오는 포탈 도착 칸에 선다
            진행도["클리어한던전"].add("dungeon_02A_D11_amon_lower")
            매니저.current_screen.갱신()
            yield 0.3
            버튼 = 목록()
            assert not 버튼["dungeon_02A_D12_amon_upper"].disabled, 버튼
            assert 버튼["dungeon_02A_D13_sephiroth_lower"].disabled, 버튼
            버튼["dungeon_02A_D12_amon_upper"].dispatch("on_release")
            yield 0.3
            assert 매니저.current == "던전", 매니저.current
            assert tuple(상태["던전상태"]["위치"]) == (19, 18), 상태["던전상태"]["위치"]
            매니저.current = "던전목록"
            yield 0.3
            진행도["클리어한던전"] = {
                "dungeon_01A_D01_Lorien",
                "dungeon_01A_D02_Hollow_Lorien",
            }
            진행도["현재마을"] = "헨돈마이어"
            매니저.current_screen.갱신()
            yield 0.4
            버튼 = 목록()
            assert [f for f, w in 버튼.items() if not w.disabled] == [
                "dungeon_01A_D03_mirkwood"
            ], 버튼
            assert len(버튼) == 8, 버튼  # 헨돈마이어는 D03~D10 전부
            _찍기("dungeon_list_hendonmyre")
            yield from _스크롤_확인(매니저.current_screen.목록스크롤, "던전 목록")
            for 파일명, 이름 in [
                ("dungeon_01A_D03_mirkwood", "mirkwood"),
                ("dungeon_01A_D05_thunderland", "thunderland"),
                ("dungeon_01A_D08_grakquarak", "grakquarak"),
            ]:
                w = 버튼[파일명]
                assert isinstance(w, screens_common._이미지버튼), w
                assert w.source.endswith(f"asset_banner_{이름}.webp"), w.source
                assert w.texture is not None, w.source  # 그림을 실제로 읽었다
            assert tuple(버튼["dungeon_01A_D03_mirkwood"].color) == (1, 1, 1, 1)
            assert 버튼["dungeon_01A_D05_thunderland"].color[0] < 1  # 잠김은 어둡게
            _찍기("dungeon_list_locked")
            진행도["클리어한던전"].add("dungeon_01A_D04_Hollow_mirkwood")
            매니저.current_screen.갱신()
            yield 0.3
            버튼 = 목록()
            assert not 버튼["dungeon_01A_D05_thunderland"].disabled, 버튼
            assert 버튼["dungeon_01A_D08_grakquarak"].disabled, 버튼
            # 머크우드 깊숙한곳(D04)은 목록으로 들어가도 머크우드에서 오는 포탈 도착 칸(0, 3)에 선다
            버튼["dungeon_01A_D04_Hollow_mirkwood"].dispatch("on_release")
            yield 0.3
            assert 매니저.current == "던전", 매니저.current
            assert tuple(상태["던전상태"]["위치"]) == (0, 3), 상태["던전상태"]["위치"]
            매니저.current = "던전목록"
            yield 0.3
            버튼 = 목록()
            assert tuple(버튼["dungeon_01A_D05_thunderland"].color) == (1, 1, 1, 1)
            버튼["dungeon_01A_D03_mirkwood"].dispatch("on_release")
            yield 0.3
            assert 매니저.current == "던전", 매니저.current
            assert 상태["던전상태"]["던전파일명"] == "dungeon_01A_D03_mirkwood"
            결과["단계"].append(
                "던전 이동 목록 - 배너 그림 버튼, 앞 던전 보스 전엔 어둡게 비활성, 누르면 입장, "
                "하늘성 일곱 곳 순서 해금, 이어진 던전은 포탈 도착 칸에서 시작"
            )
        finally:
            진행도["현재마을"], 진행도["클리어한던전"], 상태["던전상태"] = 원래
            매니저.current = "마을"

    def _단계_던전_스킬(self, 상태, 매니저):
        """던전 화면 [스킬](유루캠 "던전 캠핑"): 방향판 오른쪽 아래 칸.
        팝업 줄 "이름 - 스킬 남은/최대 MP n"을 누르면 파티 HP가 최대가 되고(쓰러진 파티원도), 다시 열면
        그 줄이 비활성(휴식당 1회 사유)이다."""
        귀검사 = next(c for c in 상태["파티"]["파티원"] if c["직업"] == "귀검사")
        원래 = (상태.get("던전상태"), list(귀검사["보유스킬"]))
        try:
            귀검사["보유스킬"].append("던전 캠핑")
            gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
            파티 = 상태["파티"]["파티원"]
            파티[1]["현재HP"] = 0
            파티[2]["현재HP"] = 1
            던전 = 매니저.get_screen("던전")
            던전.갱신()
            매니저.current = "던전"
            yield 0.4
            스킬버튼 = next(
                w
                for w in 던전.walk(restrict=True)
                if isinstance(w, Button) and w.text == "스킬"
            )
            스킬버튼.trigger_action(duration=0)
            yield 0.3
            줄 = [b for b in _대상버튼들() if "던전 캠핑" in b.text]
            assert len(줄) == 1 and not 줄[0].disabled, [b.text for b in _대상버튼들()]
            assert "1/1" in 줄[0].text and "MP 0" in 줄[0].text, 줄[0].text
            _찍기("dungeon_skill_popup")
            줄[0].trigger_action(duration=0)
            yield 0.4
            assert _팝업수() == 0, _팝업수()
            for c in 파티:
                assert c["현재HP"] == gf.캐릭터_최대HP(상태, c), c["직업"]
            assert "던전 캠핑" in 던전.메시지라벨.text, 던전.메시지라벨.text
            _찍기("dungeon_skill_used")
            스킬버튼.trigger_action(duration=0)
            yield 0.3
            줄 = [b for b in _대상버튼들() if "던전 캠핑" in b.text]
            assert 줄[0].disabled and "0/1" in 줄[0].text and "휴식" in 줄[0].text, 줄[
                0
            ].text
            _팝업_닫기()
            yield 0.2
            # 봉절: 쓰면 상태줄에 남은 걸음, 다시 열면 (풀기), 누르면 풀린다
            귀검사["보유스킬"].append("봉절")
            귀검사["현재MP"] = 귀검사["기본최대MP"]
            스킬버튼.trigger_action(duration=0)
            yield 0.3
            줄 = [b for b in _대상버튼들() if " - 봉절" in b.text]
            assert len(줄) == 1 and "MP 5" in 줄[0].text, [
                b.text for b in _대상버튼들()
            ]
            줄[0].trigger_action(duration=0)
            yield 0.4
            걸음 = 10 + 귀검사["레벨"]
            assert f"봉절 {걸음}" in 던전.상태라벨.text, 던전.상태라벨.text
            assert f"{걸음}걸음" in 던전.메시지라벨.text, 던전.메시지라벨.text
            _찍기("dungeon_skill_seal")
            스킬버튼.trigger_action(duration=0)
            yield 0.3
            줄 = [b for b in _대상버튼들() if " - 봉절" in b.text]
            assert "(풀기)" in 줄[0].text and not 줄[0].disabled, 줄[0].text
            줄[0].trigger_action(duration=0)
            yield 0.4
            assert "봉절" not in 던전.상태라벨.text, 던전.상태라벨.text
            assert "풀렸다" in 던전.메시지라벨.text, 던전.메시지라벨.text
            # 전환스킬 프렌지(버서커 퍽 광기): 줄 끝이 (꺼짐) -> 누르면 켜지고 다시 열면 (켜짐)
            귀검사["보유스킬"].append("프렌지")
            스킬버튼.trigger_action(duration=0)
            yield 0.3
            줄 = [b for b in _대상버튼들() if " - 프렌지" in b.text]
            assert len(줄) == 1 and "(꺼짐)" in 줄[0].text, [
                b.text for b in _대상버튼들()
            ]
            줄[0].trigger_action(duration=0)
            yield 0.4
            assert 귀검사.get("켜진특성") == ["프렌지"], 귀검사.get("켜진특성")
            assert "켰다" in 던전.메시지라벨.text, 던전.메시지라벨.text
            스킬버튼.trigger_action(duration=0)
            yield 0.3
            줄 = [b for b in _대상버튼들() if " - 프렌지" in b.text]
            assert "(켜짐)" in 줄[0].text, 줄[0].text
            _찍기("dungeon_skill_toggle")
            _팝업_닫기()
            yield 0.2
            # 전환스킬 나선의 넨(넨마스터 골드 스킬): 던전에서는 MP 없이 켠다
            귀검사["보유스킬"].append("나선의 넨")
            MP = 귀검사["현재MP"]
            스킬버튼.trigger_action(duration=0)
            yield 0.3
            줄 = [b for b in _대상버튼들() if " - 나선의 넨" in b.text]
            assert len(줄) == 1 and "(꺼짐)" in 줄[0].text, [
                b.text for b in _대상버튼들()
            ]
            줄[0].trigger_action(duration=0)
            yield 0.4
            assert "나선의 넨" in 귀검사.get("켜진특성", []), 귀검사.get("켜진특성")
            assert 귀검사["현재MP"] == MP
            _팝업_닫기()
            yield 0.2
            결과["단계"].append(
                "던전 [스킬]: 던전 캠핑 줄(1/1, MP 0) -> 파티 HP 최대(쓰러진 파티원 포함), 다시 열면 0/1 비활성. "
                "봉절(MP 5) -> 상태줄 '봉절 N' -> 다시 열면 (풀기) -> 풀림. "
                "프렌지 (꺼짐) -> 누르면 켜짐, 다시 열면 (켜짐). 나선의 넨 (꺼짐) -> MP 없이 켜짐"
            )
        finally:
            상태["던전상태"] = 원래[0]
            귀검사["보유스킬"][:] = 원래[1]
            귀검사.get("횟수제한스킬", {}).get("휴식제한스킬", {}).pop(
                "던전 캠핑", None
            )
            귀검사.pop("켜진특성", None)
            gf.파티_최대치로_회복(상태)
            매니저.current = "마을"

    def _단계_마을_전환스킬(self, 상태, 매니저):
        """마을 [스킬]: 전환스킬 줄 "이름 - 스킬  (꺼짐)"을 누르면 MP 없이 켜지고 다시 열면 (켜짐),
        한 번 더 누르면 꺼진다. 전환스킬이 없으면 팝업 없이 안내 문구."""
        귀검사 = next(c for c in 상태["파티"]["파티원"] if c["직업"] == "귀검사")
        원래 = list(귀검사["보유스킬"])
        # 레벨 3 이상 마법사는 전환스킬 오라 실드가 있다 - "전환스킬이 없으면" 확인 동안 잠깐 뺀다
        다른 = {
            id(c): (c, list(c["보유스킬"]))
            for c in 상태["파티"]["파티원"]
            if c is not 귀검사 and "오라 실드" in c["보유스킬"]
        }
        for c, _ in 다른.values():
            c["보유스킬"].remove("오라 실드")
        try:
            마을 = 매니저.get_screen("마을")
            매니저.current = "마을"
            yield 0.4
            스킬버튼 = next(
                w
                for w in 마을.walk(restrict=True)
                if isinstance(w, Button) and w.text == "스킬"
            )
            스킬버튼.trigger_action(duration=0)
            yield 0.3
            assert _팝업수() == 0, _팝업수()
            assert "없습니다" in 마을.메시지라벨.text, 마을.메시지라벨.text
            귀검사["보유스킬"].append("나선의 넨")
            MP = 귀검사["현재MP"]
            스킬버튼.trigger_action(duration=0)
            yield 0.3
            줄 = [b for b in _대상버튼들() if " - 나선의 넨" in b.text]
            assert len(줄) == 1 and "(꺼짐)" in 줄[0].text, [
                b.text for b in _대상버튼들()
            ]
            _찍기("town_toggle_skill_popup")
            줄[0].trigger_action(duration=0)
            yield 0.4
            assert _팝업수() == 0, _팝업수()
            assert 귀검사.get("켜진특성") == ["나선의 넨"], 귀검사.get("켜진특성")
            assert 귀검사["현재MP"] == MP
            assert "켰다" in 마을.메시지라벨.text, 마을.메시지라벨.text
            스킬버튼.trigger_action(duration=0)
            yield 0.3
            줄 = [b for b in _대상버튼들() if " - 나선의 넨" in b.text]
            assert "(켜짐)" in 줄[0].text, 줄[0].text
            _찍기("town_toggle_skill_on")
            줄[0].trigger_action(duration=0)
            yield 0.4
            assert 귀검사.get("켜진특성") == [], 귀검사.get("켜진특성")
            assert "껐다" in 마을.메시지라벨.text, 마을.메시지라벨.text
            # 오라 실드(마법사 레벨 3): 특성이 기본 켜짐이라 처음부터 (켜짐) -> 누르면 꺼짐
            귀검사["보유스킬"].append("오라 실드")
            귀검사["켜진특성"] = ["오라 실드"]
            스킬버튼.trigger_action(duration=0)
            yield 0.3
            줄 = [b for b in _대상버튼들() if " - 오라 실드" in b.text]
            assert len(줄) == 1 and "(켜짐)" in 줄[0].text, [
                b.text for b in _대상버튼들()
            ]
            _찍기("town_toggle_aura_shield")
            줄[0].trigger_action(duration=0)
            yield 0.4
            assert 귀검사.get("켜진특성") == [], 귀검사.get("켜진특성")
            assert "껐다" in 마을.메시지라벨.text, 마을.메시지라벨.text
            결과["단계"].append(
                "마을 [스킬]: 전환스킬이 없으면 안내 문구. 나선의 넨 (꺼짐) -> MP 없이 켜짐, "
                "다시 열면 (켜짐) -> 누르면 꺼짐. 오라 실드는 처음부터 (켜짐) -> 누르면 꺼짐"
            )
        finally:
            _팝업_닫기()
            귀검사["보유스킬"][:] = 원래
            귀검사.pop("켜진특성", None)
            for c, 스킬 in 다른.values():
                c["보유스킬"][:] = 스킬
            마을.메시지라벨.text = ""

    def _단계_마을_NPC(self, 상태, 매니저):
        """마을 [NPC]: 엘븐가드에는 라이너스만 -> NPC 메뉴([대화]/[퀘스트]/[상점]은 NPC마다) ->
        [대화]는 마을 그림 위에 일러스트+대화창(누르면 닫힘) -> [퀘스트] 받기/완료 보고(10G) -> 세리아는 [대화]뿐 ->
        판매목록이 있으면 [상점]이 그 품목만 파는 상점 화면."""
        로리엔 = "dungeon_01A_D01_Lorien"
        진행도 = 상태["진행도"]
        원래 = (
            진행도["현재마을"],
            set(진행도["클리어한던전"]),
            dict(진행도.get("퀘스트", {})),
            list(진행도.get("대화한NPC", [])),
            상태["소지품"]["골드"],
        )
        마을 = 매니저.get_screen("마을")
        라이너스 = quest_system.NPC_찾기("라이너스")
        원래판매 = list(라이너스["상점판매목록"])
        try:
            진행도["현재마을"] = "엘븐가드"
            진행도["클리어한던전"].discard(로리엔)
            진행도["퀘스트"] = {}
            진행도["대화한NPC"] = []
            매니저.current = "마을"
            yield 0.4
            NPC버튼 = next(
                w
                for w in 마을.walk(restrict=True)
                if isinstance(w, Button) and w.text == "NPC"
            )
            NPC버튼.trigger_action(duration=0)
            yield 0.3
            글 = _팝업글()
            assert "라이너스" in 글 and "세리아" not in 글, 글
            _찍기("town_npc_list")

            def 메뉴(이름):
                NPC버튼.trigger_action(duration=0)
                yield 0.3
                _팝업_버튼(이름).trigger_action(duration=0)
                yield 0.4
                assert _팝업수() == 1, _팝업수()

            _팝업_버튼("라이너스").trigger_action(duration=0)
            yield 0.4
            글 = _팝업글()
            assert "대화" in 글 and "퀘스트" in 글 and "상점" in 글, (
                글
            )  # 언커먼 장비 상점
            _찍기("town_npc_menu")

            # 엔피시 그림은 모두 게임(SDL2 그림 읽기)이 실제로 열 수 있어야 한다 - 움직이는 웹피는 못 연다
            for 그림 in sorted(_NPC그림폴더.glob("*.webp")):
                CoreImage(str(그림))

            # [대화] - 팝업이 닫히고 마을 그림 위에 일러스트(장면을 넘기며 움직임)와 대화창
            장면 = gf.NPC_대화(상태, "라이너스")["일러스트장면"]
            _팝업_버튼("대화").trigger_action(duration=0)
            yield 0.05
            assert _팝업수() == 0 and 마을._대화중
            assert "세리아를 구출해주게" in 마을.대화창.text, 마을.대화창.text
            assert 마을.대화창.parent is not None and 마을.NPC그림.parent is not None
            assert tuple(마을.NPC그림.texture.size) == (장면["가로"], 장면["세로"])
            처음 = (마을.NPC장면번호, 마을.NPC그림.texture)
            _찍기("town_npc_talk")
            yield 장면["시간"][0] / 1000 + 0.15
            assert 마을.NPC장면번호 != 처음[0] and 마을.NPC그림.texture is not 처음[1]
            마을.대화창.trigger_action(duration=0)  # 대화창을 누르면 닫힘
            yield 0.3
            assert not 마을._대화중 and 마을._대화층.parent is None
            assert 마을.NPC그림.parent is None and 마을._NPC장면_예약 is None
            yield from 메뉴("라이너스")
            _팝업_버튼("대화").trigger_action(duration=0)
            yield 0.3
            _뒤로키()  # [뒤로] 키도 닫는다
            yield 0.3
            assert not 마을._대화중
            yield from 메뉴("라이너스")
            _팝업_버튼("대화").trigger_action(duration=0)
            yield 0.3
            NPC버튼.trigger_action(
                duration=0
            )  # 아래 버튼은 그대로 눌리고 장면은 닫힌다
            yield 0.3
            assert not 마을._대화중 and _팝업수() == 1, _팝업수()
            _팝업_닫기()
            yield 0.2

            # [퀘스트] - 받기 -> 진행 중
            yield from 메뉴("라이너스")
            _팝업_버튼("퀘스트").trigger_action(duration=0)
            yield 0.4
            assert _팝업수() == 1, _팝업수()
            _찍기("town_npc_linus")
            _팝업_버튼("퀘스트 받기").trigger_action(duration=0)
            yield 0.4
            assert _팝업수() == 1, _팝업수()
            assert _팝업_버튼("진행 중").disabled
            assert 진행도["퀘스트"] == {"세리아_구출_의뢰": "진행중"}
            assert "받았습니다" in 마을.메시지라벨.text, 마을.메시지라벨.text
            _팝업_닫기()
            yield 0.2

            진행도["클리어한던전"].add(로리엔)
            NPC버튼.trigger_action(duration=0)
            yield 0.3
            assert "세리아" in _팝업글(), _팝업글()
            _팝업_닫기()
            yield from 메뉴("라이너스")
            _팝업_버튼("퀘스트").trigger_action(duration=0)
            yield 0.4
            골드 = 상태["소지품"]["골드"]
            _팝업_버튼("완료 보고").trigger_action(duration=0)
            yield 0.4
            assert 상태["소지품"]["골드"] == 골드 + 10
            assert _팝업_버튼("완료함").disabled
            _찍기("town_npc_linus_done")
            _팝업_닫기()
            yield 0.2

            # 세리아 - 메뉴는 [대화]뿐
            yield from 메뉴("세리아")
            글 = _팝업글()
            assert "대화" in 글 and "퀘스트" not in 글 and "상점" not in 글, 글
            _팝업_버튼("대화").trigger_action(duration=0)
            yield 0.3
            # 첫 대화는 감사 인사, 그 뒤로는 평소 대사 셋 중 하나
            assert "구해주셔서 감사해요." in 마을.대화창.text, 마을.대화창.text
            _찍기("town_npc_seria")
            마을.대화창.trigger_action(duration=0)
            yield 0.2
            yield from 메뉴("세리아")
            _팝업_버튼("대화").trigger_action(duration=0)
            yield 0.3
            assert any(
                줄 in 마을.대화창.text
                for 줄 in (
                    "안녕하세요? 세리아 키르민이에요",
                    "오늘도 좋은 하루 되세요.",
                    "저는 항상 기다리고 있어요.",
                )
            ), 마을.대화창.text
            _찍기("town_npc_seria_again")
            마을.대화창.trigger_action(duration=0)
            yield 0.2

            # [상점] - 판매목록이 있는 NPC만(라이너스는 언커먼 장비 전부) -> 그 품목만 파는 상점 화면
            yield from 메뉴("라이너스")
            _팝업_버튼("상점").trigger_action(duration=0)
            yield 0.4
            상점 = 매니저.get_screen("상점")
            assert 매니저.current == "상점" and 상점.판매목록 == 원래판매, 상점.판매목록
            assert "실키얀 상의" in 상점.판매목록 and "강철 소검" in 상점.판매목록
            _찍기("town_npc_linus_shop")
            상점._나가기()
            yield 0.4
            assert 매니저.current == "마을" and 상점.판매목록 is None
            결과["단계"].append(
                "마을 [NPC]: 엘븐가드 라이너스만 -> 메뉴(대화/퀘스트/상점) -> [대화] 마을 그림 위 대화창(누름·뒤로 키·아래 "
                "버튼으로 닫힘) -> [퀘스트] 받기 -> 진행 중, 로리엔 클리어 뒤 세리아(메뉴는 대화뿐)가 생기고 "
                "완료 보고로 10G, 세리아 첫 대화는 감사 인사·그 뒤로는 평소 대사, 라이너스 [상점]은 언커먼 장비만 파는 상점 화면을 연다"
            )
        finally:
            _팝업_닫기()
            진행도["현재마을"] = 원래[0]
            진행도["클리어한던전"] = 원래[1]
            진행도["퀘스트"] = 원래[2]
            진행도["대화한NPC"] = 원래[3]
            상태["소지품"]["골드"] = 원래[4]
            라이너스["상점판매목록"] = 원래판매
            마을._대화_닫기()
            마을.메시지라벨.text = ""

    def _단계_화면_틀(self, 매니저):
        """기준 화면 틀 - 비율이 다른 창에서 검정 여백, 터치 위치, 팝업 크기"""
        from kivy.tests.common import UnitTestTouch
        from kivy.uix.popup import Popup

        틀 = self.root
        원래크기 = tuple(Window.size)
        assert 틀.배율 == 1 and tuple(틀.틀.pos) == (0, 0), (틀.배율, 틀.틀.pos)
        try:
            # 기준보다 길쭉한 창(위아래 여백)과 넓적한 창(좌우 여백)
            for 이름, 크기 in (("tall", (900, 2340)), ("wide", (1080, 1440))):
                Window.size = 크기
                yield 0.5
                assert tuple(Window.size) == 크기, (이름, Window.size)
                배율 = screens_common.기준화면_배율(*크기)
                assert abs(틀.배율 - 배율) < 1e-6, (이름, 틀.배율, 배율)
                보이는폭 = screens_common.기준화면_폭 * 배율
                보이는높이 = screens_common.기준화면_높이 * 배율
                x, y = 틀.틀.pos
                assert abs(x - (크기[0] - 보이는폭) / 2) < 1, (이름, 틀.틀.pos)
                assert abs(y - (크기[1] - 보이는높이) / 2) < 1, (이름, 틀.틀.pos)

                # 줄어든 화면에서 손가락으로 누른 곳이 그 버튼에 닿는다
                매니저.current = "설정"
                yield 0.3
                _찍기("frame_" + 이름)
                뒤로 = next(
                    w
                    for w in 매니저.current_screen.walk(restrict=True)
                    if isinstance(w, Button) and w.text == "뒤로"
                )
                손 = UnitTestTouch(*뒤로.to_window(*뒤로.center))
                손.touch_down()
                손.touch_up()
                yield 0.3
                assert 매니저.current == "메인메뉴", (이름, 매니저.current)

                # 팝업은 가운데에, 크기 비율은 기준 화면에 대해
                팝업 = Popup(title="틀 점검", size_hint=(0.9, 0.5))
                팝업.open(animation=False)
                yield 0.3
                assert abs(팝업.width - 0.9 * 보이는폭) < 1, (이름, 팝업.size)
                assert abs(팝업.height - 0.5 * 보이는높이) < 1, (이름, 팝업.size)
                assert abs(팝업.center_x - Window.width / 2) < 1, (이름, 팝업.center)
                assert abs(팝업.center_y - Window.height / 2) < 1, (이름, 팝업.center)
                _찍기("frame_" + 이름 + "_popup")
                팝업.dismiss(animation=False)
                yield 0.3
            결과["단계"].append(
                "기준 화면 틀(1080x2340) - 길쭉/넓적한 창에서 검정 여백, 가운데 배치, 터치, 팝업 크기"
            )
        finally:
            Window.size = 원래크기
        yield 0.5
        assert abs(틀.배율 - 1) < 1e-6, 틀.배율
        매니저.current = "마을"
