# =====================
# 마을 화면 - 마을, 모험단, 마을 이동 목록, 상점, 주점(모험단 숙소)
# =====================
# main.py가 game/screens/ 일곱 파일의 화면을 ScreenManager에 등록한다.

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.metrics import dp
from kivy.uix.widget import Widget

import gameflow
from game.screens.screens_common import (
    게임메뉴_열기,
    _기본_초상화_코드,
    _버튼_높이,
    _버튼_폰트크기,
    _이미지버튼,
    _초상화선택팝업,
    _캐릭터이미지_경로,
    _에셋_경로,
    _도트_필터,
    뒤로키_버튼,
    능력치역할_팝업,
    스크롤_목록,
    스탯고르기판,
    확인_팝업,
    닫기_버튼,
    탭_줄,
    글자_높이,
    아이템_이름_글,
    파티칸줄,
    파티원_정사각형_채우기,
    상단_높이,
    하단_높이,
    정사각형_크기,
    상단_그림_높이,
    하단_좌우여백,
)


# =====================================================
# 4. 마을 화면
# =====================================================


버튼_간격 = 8  # 마을 버튼 사이
그림_버튼_간격 = (
    16  # 마을 그림과 버튼 사이(2026-10-09 사용자 요청 - 버튼 사이보다 8 더)
)
하단_버튼_높이 = (
    785  # 휴식~창고 5줄 + 타이틀(예전 하단 880 구역에서 메시지 칸을 뺀 크기)
)


def 소지품_열기(화면, 복귀화면):
    """마을/던전에서 소지품 화면으로 - 나가면 복귀화면으로 돌아간다."""
    화면.manager.get_screen("소지품").복귀화면 = 복귀화면
    화면.manager.current = "소지품"


class 마을화면(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 상단(1170): 1줄 파티원 상자, 2~4줄 마을 그림(비율 유지, 970 칸의 아래에 붙이고 남는 위는 비움)
        # 하단(1170): 버튼/타이틀을 위에 붙이고(그림과 사이에 검은 곳 없이), 메시지는 그 아래
        # - 마을 이름 줄은 없다(2026-10-09 사용자 요청)
        루트 = BoxLayout(orientation="vertical")
        상단 = BoxLayout(orientation="vertical", size_hint=(1, None), height=상단_높이)
        self.파티줄 = 파티칸줄(size_hint=(1, None), height=정사각형_크기)
        상단.add_widget(self.파티줄)
        그림칸 = AnchorLayout(
            anchor_y="bottom",
            size_hint=(1, None),
            height=상단_그림_높이,
            padding=(하단_좌우여백, 0, 하단_좌우여백, 0),  # 양 옆 끝을 버튼과 맞춘다
        )
        self.배경그림 = Image(
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, None),
            height=상단_그림_높이,
        )
        # 폭/그림이 바뀐 다음 프레임에 한 번 - 배치 중간값(기본 폭 100)으로 남지 않게
        self._그림_높이_예약 = Clock.create_trigger(self._그림_높이)
        self.배경그림.bind(texture=self._그림_높이_예약, size=self._그림_높이_예약)
        _도트_필터(self.배경그림)
        그림칸.add_widget(self.배경그림)
        상단.add_widget(그림칸)
        루트.add_widget(상단)

        하단 = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=하단_높이,
            padding=(하단_좌우여백, 그림_버튼_간격, 하단_좌우여백, 하단_좌우여백),
            spacing=버튼_간격,
        )
        나머지 = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=하단_버튼_높이,
            spacing=버튼_간격,
        )
        하단.add_widget(나머지)
        self.메시지라벨 = Label(text="")
        하단.add_widget(self.메시지라벨)
        루트.add_widget(하단)

        버튼그리드 = GridLayout(cols=2, size_hint=(1, 0.8), spacing=버튼_간격)

        휴식버튼 = Button(text="휴식 (HP/MP 전체 회복)")
        휴식버튼.bind(on_release=self._휴식)
        버튼그리드.add_widget(휴식버튼)

        던전버튼 = Button(text="던전 이동")
        던전버튼.bind(on_release=self._던전이동)
        버튼그리드.add_widget(던전버튼)

        파티버튼 = Button(text="파티")
        파티버튼.bind(on_release=self._파티_클릭)
        버튼그리드.add_widget(파티버튼)

        모험단버튼 = Button(text="모험단")
        모험단버튼.bind(on_release=self._모험단_클릭)
        버튼그리드.add_widget(모험단버튼)

        마을이동버튼 = Button(text="마을 이동")
        마을이동버튼.bind(on_release=self._마을이동)
        버튼그리드.add_widget(마을이동버튼)

        # [메뉴] - 저장하기/불러오기/설정/타이틀로 돌아가기(던전과 같은 팝업)
        메뉴버튼 = Button(text="메뉴")
        메뉴버튼.bind(on_release=lambda *_: 게임메뉴_열기(self))
        버튼그리드.add_widget(메뉴버튼)

        상점버튼 = Button(text="상점")
        상점버튼.bind(on_release=self._상점_클릭)
        버튼그리드.add_widget(상점버튼)

        주점버튼 = Button(text="주점")
        주점버튼.bind(on_release=lambda *_: setattr(self.manager, "current", "주점"))
        버튼그리드.add_widget(주점버튼)

        전문직업버튼 = Button(text="전문직업")
        전문직업버튼.bind(
            on_release=lambda *_: setattr(self.manager, "current", "전문직업")
        )
        버튼그리드.add_widget(전문직업버튼)

        창고버튼 = Button(text="소지품/창고")
        창고버튼.bind(on_release=self._소지품창고_클릭)
        버튼그리드.add_widget(창고버튼)

        # [스킬] - 전환스킬(나선의 넨·프렌지) 켜고 끄기(#283, 던전 [스킬]과 같은 처리)
        스킬버튼 = Button(text="스킬")
        스킬버튼.bind(on_release=self._스킬_클릭)
        버튼그리드.add_widget(스킬버튼)

        나머지.add_widget(버튼그리드)

        타이틀버튼 = Button(text="타이틀로 돌아가기", size_hint=(1, 0.2))
        타이틀버튼.bind(
            on_release=lambda *_: setattr(self.manager, "current", "메인메뉴")
        )
        나머지.add_widget(타이틀버튼)

        self.add_widget(루트)

    def _그림_높이(self, *args):
        """마을 그림 높이를 비율대로(최대 970) - 칸 아래에 붙어 버튼과 사이가 비지 않는다."""
        비율 = self.배경그림.image_ratio
        높이 = self.배경그림.width / 비율 if 비율 else 상단_그림_높이
        self.배경그림.height = min(상단_그림_높이, 높이)

    def 갱신(self):
        앱 = App.get_running_app()
        게임상태 = 앱.게임상태
        if 게임상태 is None:
            return

        마을정보 = gameflow.현재_마을정보(게임상태)

        경로 = _에셋_경로("town", 마을정보.get("배경이미지"))
        self.배경그림.source = 경로 or ""
        파티원_정사각형_채우기(self.파티줄, 게임상태)
        self.메시지라벨.text = ""

    def on_pre_enter(self, *args):
        self.갱신()

    def on_enter(self, *args):
        self._능력치재선택_묻기()

    def _능력치재선택_묻기(self):
        """옛 세이브(버전 10 이하)에서 이미 전직한 캐릭터는 능력치 역할을 한 번 다시 고른다(#351).
        한 명씩 묻고, 확정하면 다음 사람. 꼭 정해야 해서 [취소]가 없다(지금 역할 그대로 [확인]해도 된다)."""
        게임상태 = App.get_running_app().게임상태
        대기 = gameflow.능력치재선택_대기(게임상태) if 게임상태 else []
        if not 대기 or getattr(self, "_재선택팝업", None) is not None:
            return
        캐릭터 = 대기[0]

        def 확정(구성):
            self._재선택팝업 = None
            gameflow.능력치재선택_확정(게임상태, 캐릭터, 구성)
            self.갱신()
            self._능력치재선택_묻기()

        self._재선택팝업 = 능력치역할_팝업(
            f"{캐릭터['캐릭터명']} - 능력치 다시 고르기",
            캐릭터,
            gameflow.능력치재선택_기본구성(캐릭터),
            확인콜백=확정,
            안내="전직할 때 주/보조/약점을 다시 고르게 됐습니다(한 번).\n"
            "지금 역할 그대로 확인해도 됩니다. 값은 역할끼리 바뀝니다.",
        )

    def _휴식(self, *args):
        앱 = App.get_running_app()
        gameflow.휴식(앱.게임상태)
        self.갱신()
        self.메시지라벨.text = "파티 전원이 휴식을 취해 HP/MP를 모두 회복했습니다."

    def _던전이동(self, *args):
        self.manager.current = "던전목록"

    def _마을이동(self, *args):
        self.manager.current = "마을이동목록"

    def _스킬_클릭(self, *args):
        """[스킬] - 파티원의 전환스킬 목록 팝업. 줄을 누르면 MP 없이 켜고 끈다."""
        줄들 = gameflow.전환스킬_목록(App.get_running_app().게임상태)
        if not 줄들:
            self.메시지라벨.text = "마을에서 켜고 끌 스킬이 없습니다."
            return
        본문 = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        팝업 = Popup(
            title="전환 스킬", content=본문, size_hint=(0.9, None), height=dp(480)
        )
        스크롤, 목록틀 = 스크롤_목록(0.85, 간격=dp(6))
        for 줄 in 줄들:
            캐릭터 = 줄["캐릭터"]
            이름 = 캐릭터.get("캐릭터명") or 캐릭터.get("직업", "")
            글 = f"{이름} - {줄['스킬']}  ({줄['전환']})"
            if not 줄["가능"]:
                글 += f"\n({줄['사유']})"
            버튼 = Button(
                text=글,
                size_hint_y=None,
                height=dp(72),
                halign="center",
                disabled=not 줄["가능"],
            )
            버튼.bind(
                on_release=lambda *_, 캐릭터=캐릭터, 스킬=줄["스킬"]: self._스킬_전환(
                    팝업, 캐릭터, 스킬
                )
            )
            목록틀.add_widget(버튼)
        본문.add_widget(스크롤)
        본문.add_widget(닫기_버튼(팝업, size_hint=(1, 0.15)))
        팝업.open()
        self._스킬_팝업 = 팝업

    def _스킬_전환(self, 팝업, 캐릭터, 스킬이름):
        팝업.dismiss()
        결과 = gameflow.전환스킬_사용(App.get_running_app().게임상태, 캐릭터, 스킬이름)
        self.메시지라벨.text = 결과["문구"]

    def _파티_클릭(self, *args):
        self.manager.get_screen("파티관리").복귀화면 = "마을"
        self.manager.current = "파티관리"

    def _상점_클릭(self, *args):
        self.manager.get_screen("상점").복귀화면 = "마을"
        self.manager.current = "상점"

    def _모험단_클릭(self, *args):
        self.manager.current = "모험단"

    def _소지품창고_클릭(self, *args):
        """[소지품] / [창고 (미구현)] 고르기 팝업."""
        본문 = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        팝업 = Popup(
            title="소지품/창고", content=본문, size_hint=(0.8, None), height=dp(300)
        )

        def 소지품(*_):
            팝업.dismiss()
            소지품_열기(self, "마을")

        소지품버튼 = Button(text="소지품")
        소지품버튼.bind(on_release=소지품)
        본문.add_widget(소지품버튼)
        본문.add_widget(Button(text="창고 (미구현)", disabled=True))
        본문.add_widget(닫기_버튼(팝업))
        팝업.open()
        self._소지품창고_팝업 = 팝업


# =====================================================
# 3-1. 모험단 화면
# =====================================================
# 파티 전체가 공유하는 값(플레이어 레벨/소지금)과 파티원 목록, 그리고
# 던전에서 표시할 SD 초상화를 고르는 "모험단 프로필"을 보여준다.


class 모험단화면(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._현재코드 = _기본_초상화_코드

        루트 = BoxLayout(orientation="vertical", padding=16, spacing=10)

        루트.add_widget(
            Label(
                text="모험단",
                size_hint=(1, 0.06),
                font_size="20sp",
                bold=True,
            )
        )

        self.정보라벨 = Label(text="", size_hint=(1, 0.1), halign="left", valign="top")
        self.정보라벨.bind(
            size=lambda *_: setattr(
                self.정보라벨,
                "text_size",
                self.정보라벨.size,
            )
        )
        루트.add_widget(self.정보라벨)

        # 파티원별 "캐릭터 초상화"(직업 기반, 성별만 터치로 토글) - 플레이어
        # 초상화(아래)와는 완전히 별개다.
        캐릭터초상화틀 = BoxLayout(
            orientation="vertical", size_hint=(1, 0.34), spacing=4
        )
        캐릭터초상화틀.add_widget(
            Label(
                text="파티원 초상화 (터치하면 성별 변경)",
                size_hint=(1, 0.18),
            )
        )
        self.파티원행 = BoxLayout(
            orientation="horizontal", spacing=8, size_hint=(1, 0.82)
        )
        캐릭터초상화틀.add_widget(self.파티원행)
        루트.add_widget(캐릭터초상화틀)

        프로필틀 = BoxLayout(orientation="vertical", size_hint=(1, 0.38), spacing=4)
        프로필틀.add_widget(
            Label(
                text="던전 지도용 플레이어 초상화 (터치하면 이미지 변경)",
                size_hint=(1, 0.15),
            )
        )
        self.프로필버튼 = _이미지버튼(size_hint=(1, 0.85), allow_stretch=True)
        self.프로필버튼.bind(on_release=self._프로필_클릭)
        프로필틀.add_widget(self.프로필버튼)
        루트.add_widget(프로필틀)

        뒤로버튼 = Button(text="◀ 마을로", size_hint=(1, 0.12))
        뒤로키_버튼(뒤로버튼)
        뒤로버튼.bind(on_release=lambda *_: setattr(self.manager, "current", "마을"))
        루트.add_widget(뒤로버튼)

        self.add_widget(루트)

    def 갱신(self):
        앱 = App.get_running_app()
        게임상태 = 앱.게임상태
        if 게임상태 is None:
            return

        골드 = gameflow.상점_보유골드(게임상태)
        self.정보라벨.text = (
            f"레벨  {게임상태['진행도']['플레이어레벨']}\n소지금  {골드}G"
        )

        self.파티원행.clear_widgets()
        파티원목록 = 게임상태["파티"]["파티원"]
        if 파티원목록:
            for 캐릭터 in 파티원목록:
                self.파티원행.add_widget(self._캐릭터_카드(캐릭터))
        else:
            self.파티원행.add_widget(Label(text="(파티원 없음)"))

        self._현재코드 = 게임상태.get("선택된초상화", _기본_초상화_코드)
        self.프로필버튼.source = _캐릭터이미지_경로(self._현재코드)

    def _캐릭터_카드(self, 캐릭터):
        """파티원 한 명의 이름/직업 + 직업 기반 초상화(터치하면 성별
        토글) 카드 위젯을 만든다."""
        칸 = BoxLayout(orientation="vertical", spacing=2)
        이름라벨 = Label(
            text=f"{캐릭터['캐릭터명']}\n{캐릭터.get('직업') or '무직업'}",
            size_hint=(1, 0.3),
            halign="center",
            valign="middle",
            font_size="13sp",
        )
        이름라벨.bind(size=lambda inst, *_: setattr(inst, "text_size", inst.size))
        칸.add_widget(이름라벨)

        초상화버튼 = _이미지버튼(
            source=_캐릭터이미지_경로(gameflow.초상화_코드(캐릭터)),
            size_hint=(1, 0.7),
            allow_stretch=True,
        )
        초상화버튼.bind(on_release=lambda *args, c=캐릭터: self._성별_토글(c))
        칸.add_widget(초상화버튼)
        return 칸

    def _성별_토글(self, 캐릭터):
        새성별 = "f" if 캐릭터.get("성별", "m") == "m" else "m"
        gameflow.캐릭터_성별_설정(캐릭터, 새성별)
        self.갱신()

    def on_pre_enter(self, *args):
        self.갱신()

    def _프로필_클릭(self, *args):
        _초상화선택팝업(
            현재선택=self._현재코드,
            선택콜백=self._초상화_변경,
        ).open()

    def _초상화_변경(self, 코드):
        앱 = App.get_running_app()
        gameflow.초상화_설정(앱.게임상태, 코드)
        self.갱신()


# =====================================================
# 4-0. 마을 이동 목록 화면 (마을 -> 다른 마을로 이동)
# =====================================================


class 마을이동목록화면(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        루트 = BoxLayout(orientation="vertical", padding=16, spacing=10)
        루트.add_widget(Label(text="마을 이동", font_size="24sp", size_hint=(1, 0.12)))

        self.목록틀 = BoxLayout(orientation="vertical", size_hint=(1, 0.68), spacing=8)
        루트.add_widget(self.목록틀)

        self.안내라벨 = Label(text="", size_hint=(1, 0.1))
        루트.add_widget(self.안내라벨)

        뒤로버튼 = Button(text="뒤로", size_hint=(1, 0.1))
        뒤로키_버튼(뒤로버튼)
        뒤로버튼.bind(on_release=lambda *_: setattr(self.manager, "current", "마을"))
        루트.add_widget(뒤로버튼)

        self.add_widget(루트)

    def on_pre_enter(self, *args):
        self.갱신()

    def 갱신(self):
        self.목록틀.clear_widgets()
        앱 = App.get_running_app()
        게임상태 = 앱.게임상태
        현재마을명 = 게임상태["진행도"]["현재마을"]
        마을목록 = gameflow.이동가능마을목록(게임상태)

        표시할목록 = [마을 for 마을 in 마을목록 if 마을["마을명"] != 현재마을명]
        if not 표시할목록:
            self.안내라벨.text = "지금 이동할 수 있는 다른 마을이 없습니다."
            return
        self.안내라벨.text = ""

        for 마을 in 표시할목록:
            버튼 = Button(text=마을["마을명"], size_hint=(1, None), height=dp(56))
            버튼.bind(on_release=lambda inst, m=마을["마을명"]: self._선택(m))
            self.목록틀.add_widget(버튼)

    def _선택(self, 마을명):
        앱 = App.get_running_app()
        gameflow.마을_이동(앱.게임상태, 마을명)
        self.manager.get_screen("마을").갱신()
        self.manager.current = "마을"


# =====================================================
# 4-2. 상점 화면 (shop_system.py 연동 - 마을 -> 상점)
# =====================================================
# 단계 구성: 메인(구매/판매/나가기) -> 대분류(장비/소모품/재료) -> 탭(부위/
# 종류) -> 개별 아이템 목록(구매/판매, 수량 -/+ 스테퍼, "자세히 보기"
# 팝업). 실제 거래 로직은 전부 gameflow.상점_*() -> shop_system.py에
# 있고, 이 클래스는 화면 단계 전환과 위젯 생성만 한다. 재료 탭은 아직
# 미구현이라 안내 문구만 보여준다.


_행_글자크기 = "16sp"  # 상점 아이템 줄의 글자 크기(이름/버튼/가격/수량 모두)


class 상점화면(Screen):
    제목 = "상점"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.복귀화면 = "마을"

        # 머리줄/뒤로 줄/탭/안내줄은 글자 높이에 맞춘 높이(글자_높이) - 남는 높이는 목록이 쓴다
        루트 = BoxLayout(orientation="vertical", padding=12, spacing=6)

        머리 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=글자_높이("20sp")
        )
        머리.add_widget(Label(text=self.제목, font_size="20sp", halign="left"))
        self.골드라벨 = Label(text="")
        머리.add_widget(self.골드라벨)
        루트.add_widget(머리)

        self.내용틀 = BoxLayout(orientation="vertical", size_hint=(1, 1), spacing=6)
        루트.add_widget(self.내용틀)

        self.안내라벨 = Label(text="", size_hint=(1, None), height=글자_높이())
        루트.add_widget(self.안내라벨)

        self.add_widget(루트)

    def on_pre_enter(self, *args):
        self.안내라벨.text = ""
        self._골드_갱신()
        self._메인_그리기()

    def _골드_갱신(self):
        앱 = App.get_running_app()
        self.골드라벨.text = f"보유 골드: {gameflow.상점_보유골드(앱.게임상태)}G"

    def _비우기(self):
        self.내용틀.clear_widgets()

    # -------------------------------------------------
    # 단계 1: 구매 / 판매 / 나가기
    # -------------------------------------------------

    def _메인_그리기(self):
        self._비우기()
        self.안내라벨.text = ""

        구매버튼 = Button(text="구매", font_size=_버튼_폰트크기)
        구매버튼.bind(on_release=lambda *_: self._대분류_그리기("구매"))
        self.내용틀.add_widget(구매버튼)

        판매버튼 = Button(text="판매", font_size=_버튼_폰트크기)
        판매버튼.bind(on_release=lambda *_: self._대분류_그리기("판매"))
        self.내용틀.add_widget(판매버튼)

        나가기버튼 = Button(text="나가기", font_size=_버튼_폰트크기)
        뒤로키_버튼(나가기버튼)
        나가기버튼.bind(on_release=self._나가기)
        self.내용틀.add_widget(나가기버튼)

    def _나가기(self, *args):
        self.manager.current = self.복귀화면

    # -------------------------------------------------
    # 단계 2: 대분류(장비 / 소모품 / 재료)
    # -------------------------------------------------

    def _대분류_그리기(self, 모드):
        self._비우기()

        상단 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=글자_높이()
        )
        뒤로버튼 = Button(text="◀ 뒤로", size_hint=(0.32, 1))
        뒤로키_버튼(뒤로버튼)
        뒤로버튼.bind(on_release=lambda *_: self._메인_그리기())
        상단.add_widget(뒤로버튼)
        상단.add_widget(Label(text=모드, size_hint=(0.68, 1)))
        self.내용틀.add_widget(상단)

        for 대분류 in gameflow.상점_대분류목록:
            버튼 = Button(text=대분류)
            if 대분류 == "재료":
                버튼.bind(on_release=lambda *_, m=모드: self._재료_그리기(m))
            else:
                버튼.bind(
                    on_release=lambda *_, m=모드, d=대분류: self._탭목록_그리기(m, d)
                )
            self.내용틀.add_widget(버튼)

    def _재료_그리기(self, 모드):
        self._비우기()
        상단 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=글자_높이()
        )
        뒤로버튼 = Button(text="◀ 뒤로", size_hint=(0.32, 1))
        뒤로키_버튼(뒤로버튼)
        뒤로버튼.bind(on_release=lambda *_, m=모드: self._대분류_그리기(m))
        상단.add_widget(뒤로버튼)
        self.내용틀.add_widget(상단)
        self.내용틀.add_widget(Label(text="아직 구현되지 않았습니다."))

    # -------------------------------------------------
    # 단계 3: 탭(부위 / 종류) + 단계 4: 개별 아이템 목록
    # -------------------------------------------------

    def _탭목록_그리기(self, 모드, 대분류):
        self._비우기()

        상단 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=글자_높이()
        )
        뒤로버튼 = Button(text="◀ 뒤로", size_hint=(0.32, 1))
        뒤로키_버튼(뒤로버튼)
        뒤로버튼.bind(
            on_release=lambda *_: (
                self._메인_그리기() if 모드 == "해체" else self._대분류_그리기(모드)
            )
        )
        상단.add_widget(뒤로버튼)
        상단.add_widget(Label(text=f"{모드} - {대분류}", size_hint=(0.68, 1)))
        self.내용틀.add_widget(상단)

        # 부위 탭 - 장비는 2줄(윗줄 무기~신발, 아랫줄 악세서리/특수장비)을 한 묶음으로,
        # 밀어서 넘기지 않고 다 보인다. 그 아래 하위 탭(무기: 직업군 -> 종류, 방어구: 재질).
        탭줄들 = self._탭줄(모드, 대분류)
        칸수 = max(len(줄) for 줄 in 탭줄들) if 탭줄들 else 1
        그룹 = f"상점부위{id(self)}"
        처음탭 = 탭줄들[0][0] if 탭줄들 and 탭줄들[0] else None
        for 줄 in 탭줄들:
            self.내용틀.add_widget(
                탭_줄(
                    줄,
                    lambda t, m=모드, d=대분류: self._부위_고르기(m, d, t),
                    처음탭,
                    높이=글자_높이("14sp"),  # 글자 높이에 맞춘 탭
                    그룹=그룹,
                    칸수=칸수,
                )
            )
        self._하위탭틀 = BoxLayout(
            orientation="vertical", size_hint=(1, None), height=0, spacing=dp(4)
        )
        self.내용틀.add_widget(self._하위탭틀)

        목록스크롤 = ScrollView(size_hint=(1, 1))
        목록틀 = BoxLayout(orientation="vertical", size_hint_y=None, spacing=4)
        목록틀.bind(minimum_height=목록틀.setter("height"))
        목록스크롤.add_widget(목록틀)
        self.내용틀.add_widget(목록스크롤)
        self._목록틀 = 목록틀

        if 모드 == "해체":
            # 일괄해체 줄은 목록 아래(화면 하단)
            self.내용틀.add_widget(self._일괄해체_줄(목록틀))

        if 처음탭:
            self._부위_고르기(모드, 대분류, 처음탭)

    def _탭줄(self, 모드, 대분류):
        return gameflow.상점_탭줄(모드, 대분류)

    def _부위_고르기(self, 모드, 대분류, 탭):
        """부위 탭을 누르면 하위 탭을 다시 그리고(고른 것은 [전체]로) 목록을 그린다."""
        self._필터 = {"직업군": None, "분류": None}
        self._하위탭_그리기(모드, 대분류, 탭)
        self._아이템목록_그리기(모드, 대분류, 탭, self._목록틀)

    def _하위탭_그리기(self, 모드, 대분류, 탭):
        틀 = self._하위탭틀
        틀.clear_widgets()
        게임상태 = App.get_running_app().게임상태
        줄들 = []
        if 대분류 == "장비" and 탭 == "무기":
            직업군 = self._필터["직업군"]
            줄들.append((gameflow.상점_무기_직업군탭(게임상태), 직업군, "직업군"))
            종류탭 = gameflow.상점_무기_종류탭(게임상태, 직업군)
            if 종류탭:
                줄들.append((종류탭, self._필터["분류"], "분류"))
        elif 대분류 == "장비" and 탭 in gameflow.상점_방어구_부위:
            줄들.append((gameflow.상점_방어구_재질탭, self._필터["분류"], "분류"))
        높이 = 글자_높이("13sp")
        for 탭들, 고른, 키 in 줄들:
            틀.add_widget(
                탭_줄(
                    탭들,
                    lambda 값, k=키, m=모드, d=대분류, t=탭: self._하위_고르기(
                        m, d, t, k, 값
                    ),
                    고른 or 탭들[0],
                    높이=높이,
                    font_size="13sp",
                )
            )
        틀.height = len(줄들) * 높이 + max(0, len(줄들) - 1) * dp(4)

    def _하위_고르기(self, 모드, 대분류, 탭, 키, 값):
        self._필터[키] = 값
        if 키 == "직업군":
            self._필터["분류"] = None  # 직업군이 바뀌면 종류는 [전체]부터
            self._하위탭_그리기(모드, 대분류, 탭)
        self._아이템목록_그리기(모드, 대분류, 탭, self._목록틀)

    def _아이템목록_그리기(self, 모드, 대분류, 탭, 목록틀):
        목록틀.clear_widgets()
        앱 = App.get_running_app()
        게임상태 = 앱.게임상태

        if 모드 == "구매":
            마을정보 = gameflow.현재_마을정보(게임상태)
            항목목록 = [
                (아이템, gameflow.상점_최대구매수량)
                for 아이템 in gameflow.상점_구매목록(
                    게임상태,
                    대분류,
                    탭,
                    마을정보.get("상점판매목록"),
                )
            ]
            빈문구 = "팔고 있는 물건이 없습니다."
        elif 모드 == "해체":
            항목목록 = gameflow.상점_해체목록(게임상태, 탭)
            빈문구 = (
                "해체할 수 있는 장비가 없습니다(장착 중인 장비는 해체할 수 없습니다)."
            )
        else:
            항목목록 = gameflow.상점_판매목록(게임상태, 대분류, 탭)
            빈문구 = "팔 수 있는 물건이 없습니다."

        # 하위 탭(무기 직업군/종류, 방어구 재질)으로 거른다
        필터 = getattr(self, "_필터", None) or {}
        항목목록 = [
            항목
            for 항목 in 항목목록
            if gameflow.상점_분류_일치(
                항목[2] if len(항목) > 2 else 탭,
                항목[0],
                필터.get("직업군"),
                필터.get("분류"),
            )
        ]
        self._현재탭 = 탭
        if not 항목목록:
            목록틀.add_widget(Label(text=빈문구, size_hint=(1, None), height=dp(40)))
            return

        for 항목 in 항목목록:
            아이템, 최대수량 = 항목[0], 항목[1]
            부위 = (
                항목[2] if len(항목) > 2 else 탭
            )  # 해체 [전체]는 장비마다 부위가 다르다
            목록틀.add_widget(
                self._행_생성(모드, 대분류, 부위, 아이템, 최대수량, 목록틀, 표시탭=탭)
            )

    def _행_생성(self, 모드, 대분류, 탭, 아이템, 최대수량, 목록틀, 표시탭=None):
        if 모드 == "구매":
            단가글 = f"{아이템['가격']}G"
        elif 모드 == "해체":
            단가글 = 아이템.get("레어도", "")
        else:
            단가글 = f"{gameflow.상점_판매가(아이템)}G"

        행높이 = 56
        글자 = _행_글자크기  # 이 줄의 글자/버튼은 모두 같은 크기, 세로 가운데
        행 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=행높이, spacing=4
        )

        이름라벨 = Label(
            text=아이템_이름_글(아이템),  # 레어도 색
            markup=True,
            size_hint=(0.34, 1),
            halign="left",
            valign="middle",
            font_size=글자,
            shorten=True,
            shorten_from="right",
        )
        이름라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        행.add_widget(이름라벨)

        자세히버튼 = Button(text="자세히", size_hint=(0.16, 1), font_size=글자)
        자세히버튼.bind(on_release=lambda *_, a=아이템: self._자세히보기(a))
        행.add_widget(자세히버튼)

        단가라벨 = Label(text=단가글, size_hint=(0.14, 1), font_size=글자)
        행.add_widget(단가라벨)

        수량상태 = {"값": 1}

        # -/+ 는 줄 높이와 같은 정사각형
        감소버튼 = Button(text="-", size_hint=(None, 1), width=행높이, font_size=글자)
        수량라벨 = Label(text="1", size_hint=(0.08, 1), font_size=글자)
        증가버튼 = Button(text="+", size_hint=(None, 1), width=행높이, font_size=글자)

        def 감소(*_):
            if 수량상태["값"] > 1:
                수량상태["값"] -= 1
                수량라벨.text = str(수량상태["값"])

        def 증가(*_):
            if 수량상태["값"] < 최대수량:
                수량상태["값"] += 1
                수량라벨.text = str(수량상태["값"])

        감소버튼.bind(on_release=감소)
        증가버튼.bind(on_release=증가)
        행.add_widget(감소버튼)
        행.add_widget(수량라벨)
        행.add_widget(증가버튼)

        거래버튼 = Button(text=모드, size_hint=(0.12, 1), font_size=글자)
        거래버튼.bind(
            on_release=lambda *_, a=아이템: self._거래_클릭(
                모드,
                대분류,
                탭,
                a["이름"],
                수량상태,
                목록틀,
                표시탭=표시탭,
            )
        )
        행.add_widget(거래버튼)

        return 행

    # -------------------------------------------------
    # 거래 처리
    # -------------------------------------------------

    def _거래_클릭(self, 모드, 대분류, 탭, 이름, 수량상태, 목록틀, 표시탭=None):
        앱 = App.get_running_app()
        게임상태 = 앱.게임상태
        수량 = 수량상태["값"]

        try:
            if 모드 == "구매":
                마을정보 = gameflow.현재_마을정보(게임상태)
                금액 = gameflow.상점_구매(
                    게임상태,
                    대분류,
                    탭,
                    이름,
                    수량,
                    상점판매목록=마을정보.get("상점판매목록"),
                )
                self.안내라벨.text = f"{이름} {수량}개를 {금액}G에 샀습니다."
            elif 모드 == "해체":
                얻음 = gameflow.상점_해체(게임상태, 탭, 이름, 수량)
                self.안내라벨.text = f"{이름} {수량}개 해체: " + ", ".join(
                    f"{재료} {개수}" for 재료, 개수 in 얻음.items()
                )
            else:
                금액 = gameflow.상점_판매(게임상태, 대분류, 탭, 이름, 수량)
                self.안내라벨.text = f"{이름} {수량}개를 {금액}G에 팔았습니다."
        except ValueError as 오류:
            self.안내라벨.text = str(오류)
            return

        self._골드_갱신()
        # 판매는 보유 수량이 바뀌므로, 구매/판매 둘 다 목록을 다시 그려
        # (품절/재고 변화를) 반영한다.
        self._아이템목록_그리기(모드, 대분류, 표시탭 or 탭, 목록틀)

    # -------------------------------------------------
    # 일괄해체 - [일괄해체] + 등급/부위 범위(기본 커먼 / 전체)
    # -------------------------------------------------

    def _일괄해체_줄(self, 목록틀):
        줄 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=글자_높이(), spacing=4
        )
        # 세 칸 모두 "일괄해체" 글자 너비에 맞춘 같은 크기로, 오른쪽 끝에 붙인다.
        일괄버튼 = Button(text="일괄해체", size_hint=(None, 1))
        self.일괄등급 = Spinner(
            text="커먼", values=gameflow.상점_해체_등급목록, size_hint=(None, 1)
        )
        self.일괄부위 = Spinner(
            text="전체", values=gameflow.상점_해체_탭목록, size_hint=(None, 1)
        )

        def 너비_맞추기(inst, ts):
            for 칸 in (일괄버튼, self.일괄등급, self.일괄부위):
                칸.width = ts[0] + dp(28)

        일괄버튼.bind(texture_size=너비_맞추기)
        일괄버튼.bind(on_release=lambda *_: self._일괄해체_확인(목록틀))
        줄.add_widget(Widget())  # 왼쪽 빈 공간
        줄.add_widget(일괄버튼)
        줄.add_widget(self.일괄등급)
        줄.add_widget(self.일괄부위)
        return 줄

    def _일괄해체_확인(self, 목록틀):
        게임상태 = App.get_running_app().게임상태
        등급, 부위 = self.일괄등급.text, self.일괄부위.text
        대상 = gameflow.상점_일괄해체_대상(게임상태, 등급, 부위)
        if not 대상:
            self.안내라벨.text = f"{등급} · {부위}: 해체할 장비가 없습니다."
            return
        개수 = sum(수량 for _, 수량, _ in 대상)
        본문 = BoxLayout(orientation="vertical", spacing=8, padding=12)
        본문.add_widget(
            Label(
                text=f"{등급} · {부위} 장비 {개수}개({len(대상)}종)를 모두 해체할까요?\n"
                "되돌릴 수 없습니다. 장착 중인 장비는 빠집니다.",
                halign="center",
            )
        )
        팝업 = Popup(
            title="일괄해체", content=본문, size_hint=(0.85, 0.45), auto_dismiss=False
        )

        def 해체(*_):
            팝업.dismiss()
            try:
                수, 얻음 = gameflow.상점_일괄해체(게임상태, 등급, 부위)
            except ValueError as 오류:
                self.안내라벨.text = str(오류)
                return
            self.안내라벨.text = f"{수}개 해체: " + ", ".join(
                f"{재료} {n}" for 재료, n in 얻음.items()
            )
            self._아이템목록_그리기("해체", "장비", self._현재탭, 목록틀)

        버튼줄 = BoxLayout(orientation="horizontal", spacing=8, size_hint=(1, 0.35))
        해체버튼 = Button(text="해체")
        해체버튼.bind(on_release=해체)
        취소버튼 = Button(text="취소")
        뒤로키_버튼(취소버튼)
        취소버튼.bind(on_release=lambda *_: 팝업.dismiss())
        버튼줄.add_widget(해체버튼)
        버튼줄.add_widget(취소버튼)
        본문.add_widget(버튼줄)
        팝업.open()

    # -------------------------------------------------
    # 자세히 보기 팝업
    # -------------------------------------------------

    # 레어 무기의 고유효과/오라/스킬강화는 원소를 그대로 보이지 않고 "설명"으로 보인다(#437)
    _상세_제외키 = {"이름", "마봉효과", "봉인원본", "고유효과", "오라", "스킬강화"}

    def _자세히보기(self, 아이템):
        본문 = BoxLayout(orientation="vertical", spacing=6, padding=12)

        스크롤 = ScrollView(size_hint=(1, 1))
        내용틀 = BoxLayout(orientation="vertical", size_hint_y=None, spacing=4)
        내용틀.bind(minimum_height=내용틀.setter("height"))
        스크롤.add_widget(내용틀)
        본문.add_widget(스크롤)
        이름줄 = Label(
            text=f"[b]{아이템_이름_글(아이템)}[/b]",
            markup=True,
            size_hint=(1, None),
            height=dp(36),
            halign="left",
            font_size="17sp",
        )
        이름줄.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        내용틀.add_widget(이름줄)

        for 키, 값 in 아이템.items():
            if 키 in self._상세_제외키 or 값 in (None, 0, "", {}, []):
                continue
            라벨 = Label(
                text=f"{키}: {self._값_문자열(값)}",
                size_hint=(1, None),
                height=dp(32),
                halign="left",
                valign="middle",
            )
            # 긴 글(레어 무기 "설명" - #437)은 줄을 바꿔 그만큼 높아진다(겹치지 않게)
            라벨.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
            라벨.bind(
                texture_size=lambda inst, ts: setattr(
                    inst, "height", max(dp(32), ts[1])
                )
            )
            내용틀.add_widget(라벨)

        닫기버튼 = Button(text="닫기", size_hint=(1, None), height=_버튼_높이)
        뒤로키_버튼(닫기버튼)
        본문.add_widget(닫기버튼)

        팝업 = Popup(
            title=아이템["이름"],
            content=본문,
            size_hint=(0.85, 0.75),
            auto_dismiss=False,
        )
        닫기버튼.bind(on_release=lambda *_: 팝업.dismiss())
        팝업.open()

    @staticmethod
    def _값_문자열(값):
        if isinstance(값, dict):
            return ", ".join(
                f"{k} {v:+d}" if isinstance(v, int) else f"{k} {v}"
                for k, v in 값.items()
            )
        if isinstance(값, (list, tuple)):
            return ", ".join(
                # 장비효과·오라 원소 - "최대MP +10", "AC +1"
                f"{gameflow.변동대상_표시이름(v['변동대상'])} {v['변동값']:+d}"
                if isinstance(v, dict) and isinstance(v.get("변동값"), int)
                else str(v)
                for v in 값
            )
        return str(값)


# =====================================================
# 4-2b. 소지품 화면 (마을 [소지품/창고] -> [소지품], 던전 방향키 왼쪽 아래 [소지품])
# =====================================================
# 상점처럼 대분류 -> 탭(-> 하위 탭) -> 목록. 줄마다 [상세보기], 쓸 수 있는 것(항아리/회복포션/
# 음식/주류)은 [사용]. 항아리는 바로 열고, 나머지는 쓸 파티원을 고른다. 전투 중 아이템은 전투 화면에서.


class 전문직업화면(상점화면):
    """마을 [전문직업] - 장비강화/장비해체/마법부여/봉인해제/봉인변환(2026-10-15 사용자 결정), 인형사(2026-10-19).
    장비해체는 상점에 있던 [해체]를 옮겨 온 것(상점화면의 해체 목록을 그대로 쓴다).
    봉인해제/봉인변환은 장착 중인 장비도 고를 수 있다. 장비강화/마법부여는 미구현.
    인형사는 인형제작 창 - 인형마다 필요 재료(보유/필요), [상세보기], [제작]."""

    제목 = "전문직업"

    def _메인_그리기(self):
        self._비우기()
        self.안내라벨.text = ""
        for 메뉴 in gameflow.전문직업_메뉴:
            구현됨 = 메뉴 in gameflow.전문직업_구현됨
            버튼 = Button(
                text=메뉴 if 구현됨 else f"{메뉴} (미구현)",
                font_size=_버튼_폰트크기,
                disabled=not 구현됨,
            )
            if 메뉴 == "장비해체":
                버튼.bind(on_release=lambda *_: self._탭목록_그리기("해체", "장비"))
            elif 메뉴 == "인형사":
                버튼.bind(on_release=lambda *_: self._인형사_그리기())
            elif 구현됨:
                버튼.bind(on_release=lambda *_, m=메뉴: self._봉인_그리기(m))
            self.내용틀.add_widget(버튼)
        나가기버튼 = Button(text="나가기", font_size=_버튼_폰트크기)
        뒤로키_버튼(나가기버튼)
        나가기버튼.bind(on_release=self._나가기)
        self.내용틀.add_widget(나가기버튼)

    def _하위창_틀(self, 제목글):
        """[◀ 뒤로] + 제목 줄과 스크롤 목록틀(self._목록틀)을 그린다 - 봉인해제/봉인변환/인형사 공용."""
        self._비우기()
        상단 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=글자_높이()
        )
        뒤로버튼 = Button(text="◀ 뒤로", size_hint=(0.32, 1))
        뒤로키_버튼(뒤로버튼)
        뒤로버튼.bind(on_release=lambda *_: self._메인_그리기())
        상단.add_widget(뒤로버튼)
        상단.add_widget(Label(text=제목글, size_hint=(0.68, 1)))
        self.내용틀.add_widget(상단)

        목록스크롤 = ScrollView(size_hint=(1, 1))
        목록틀 = BoxLayout(orientation="vertical", size_hint_y=None, spacing=4)
        목록틀.bind(minimum_height=목록틀.setter("height"))
        목록스크롤.add_widget(목록틀)
        self.내용틀.add_widget(목록스크롤)
        self._목록틀 = 목록틀

    def _봉인_그리기(self, 모드):
        """봉인해제: 봉인 장비 목록, 봉인변환: 봉인을 푼 장비 목록 - 줄마다 [자세히]와 실행 버튼."""
        self._하위창_틀(f"{모드} ({gameflow.전문직업_비용글})")
        self._봉인목록_채우기(모드)

    def _봉인목록_채우기(self, 모드):
        목록틀 = self._목록틀
        목록틀.clear_widgets()
        항목들 = gameflow.전문직업_봉인목록(App.get_running_app().게임상태, 모드)
        if not 항목들:
            빈글 = (
                "봉인된 장비가 없습니다."
                if 모드 == "봉인해제"
                else "봉인을 푼 장비가 없습니다."
            )
            목록틀.add_widget(Label(text=빈글, size_hint=(1, None), height=글자_높이()))
            return
        for 항목 in 항목들:
            목록틀.add_widget(self._봉인_행(모드, 항목))

    def _봉인_행(self, 모드, 항목):
        글자 = _행_글자크기
        행 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=56, spacing=4
        )
        위치 = (
            f"{항목['캐릭터']['캐릭터명']} 착용"
            if 항목["캐릭터"] is not None
            else f"소지품 {항목['수량']}개"
        )
        이름라벨 = Label(
            text=f"{아이템_이름_글(항목['아이템'])}  ({위치})",
            markup=True,
            size_hint=(0.6, 1),
            halign="left",
            valign="middle",
            font_size=글자,
            shorten=True,
            shorten_from="right",
        )
        이름라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        행.add_widget(이름라벨)
        자세히버튼 = Button(text="자세히", size_hint=(0.16, 1), font_size=글자)
        자세히버튼.bind(on_release=lambda *_: self._자세히보기(항목["아이템"]))
        행.add_widget(자세히버튼)
        실행버튼 = Button(text=모드, size_hint=(0.24, 1), font_size=글자)
        실행버튼.bind(on_release=lambda *_: self._봉인_실행(모드, 항목))
        행.add_widget(실행버튼)
        return 행

    def _봉인_실행(self, 모드, 항목):
        게임상태 = App.get_running_app().게임상태
        처리 = (
            gameflow.전문직업_봉인해제
            if 모드 == "봉인해제"
            else gameflow.전문직업_봉인변환
        )
        try:
            새이름 = 처리(게임상태, 항목)
        except ValueError as 오류:
            self.안내라벨.text = str(오류)
            return
        self._골드_갱신()
        self._봉인목록_채우기(모드)
        self.안내라벨.text = f"{항목['이름']} -> {새이름}"

    # ------------------------------------------------------------ 인형사 (인형제작 창)

    def _인형사_그리기(self):
        self._하위창_틀("인형제작")
        self._인형목록_채우기()

    def _인형목록_채우기(self):
        self._목록틀.clear_widgets()
        for 항목 in gameflow.전문직업_인형목록(App.get_running_app().게임상태):
            self._목록틀.add_widget(self._인형_행(항목))

    def _인형_행(self, 항목):
        글자 = _행_글자크기
        행 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=56, spacing=4
        )
        이름라벨 = Label(
            text=f"{항목['이름']}  ({항목['재료글']})",
            size_hint=(0.56, 1),
            halign="left",
            valign="middle",
            font_size=글자,
            shorten=True,
            shorten_from="right",
        )
        이름라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        행.add_widget(이름라벨)
        상세버튼 = Button(text="상세보기", size_hint=(0.24, 1), font_size=글자)
        상세버튼.bind(on_release=lambda *_: self._인형_상세(항목["이름"]))
        행.add_widget(상세버튼)
        제작버튼 = Button(
            text="제작",
            size_hint=(0.2, 1),
            font_size=글자,
            disabled=not 항목["제작가능"],
        )
        제작버튼.bind(on_release=lambda *_: self._인형_제작(항목["이름"]))
        행.add_widget(제작버튼)
        return 행

    def _인형_상세(self, 이름):
        본문 = BoxLayout(orientation="vertical", spacing=6, padding=12)
        스크롤 = ScrollView(size_hint=(1, 1))
        내용틀 = BoxLayout(orientation="vertical", size_hint_y=None, spacing=4)
        내용틀.bind(minimum_height=내용틀.setter("height"))
        스크롤.add_widget(내용틀)
        본문.add_widget(스크롤)
        for 줄 in gameflow.전문직업_인형상세(이름):
            라벨 = Label(text=줄, size_hint=(1, None), height=dp(32), halign="left")
            라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
            내용틀.add_widget(라벨)
        팝업 = Popup(
            title=이름, content=본문, size_hint=(0.85, 0.75), auto_dismiss=False
        )
        본문.add_widget(닫기_버튼(팝업, size_hint=(1, None), height=_버튼_높이))
        팝업.open()
        return 팝업

    def _인형_제작(self, 이름):
        try:
            gameflow.전문직업_인형제작(App.get_running_app().게임상태, 이름)
        except ValueError as 오류:
            self.안내라벨.text = str(오류)
            return
        self._인형목록_채우기()
        self.안내라벨.text = (
            f"인형 '{이름}'을(를) 만들었습니다. (소지품 > 소모품 > 인형)"
        )


class 소지품화면(상점화면):
    제목 = "소지품"
    모드 = "소지품"

    def _메인_그리기(self):
        self._대분류_그리기(self.모드)

    def _대분류_그리기(self, 모드):
        self._비우기()
        상단 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=글자_높이()
        )
        나가기버튼 = Button(text="◀ 나가기", size_hint=(0.32, 1))
        뒤로키_버튼(나가기버튼)
        나가기버튼.bind(on_release=self._나가기)
        상단.add_widget(나가기버튼)
        상단.add_widget(Label(text=모드, size_hint=(0.68, 1)))
        self.내용틀.add_widget(상단)
        for 대분류 in gameflow.상점_대분류목록:
            버튼 = Button(text=대분류, font_size=_버튼_폰트크기)
            버튼.bind(on_release=lambda *_, d=대분류: self._탭목록_그리기(모드, d))
            self.내용틀.add_widget(버튼)

    def _탭줄(self, 모드, 대분류):
        return gameflow.소지품_탭줄(App.get_running_app().게임상태, 대분류)

    def _아이템목록_그리기(self, 모드, 대분류, 탭, 목록틀):
        목록틀.clear_widgets()
        self._현재 = (대분류, 탭, 목록틀)
        게임상태 = App.get_running_app().게임상태
        필터 = getattr(self, "_필터", None) or {}
        항목목록 = [
            항목
            for 항목 in gameflow.소지품_목록(게임상태, 대분류, 탭)
            if gameflow.상점_분류_일치(
                탭, 항목[0], 필터.get("직업군"), 필터.get("분류")
            )
        ]
        if not 항목목록:
            목록틀.add_widget(
                Label(text="가진 물건이 없습니다.", size_hint=(1, None), height=dp(40))
            )
            return
        for 아이템, 개수, 종류 in 항목목록:
            목록틀.add_widget(self._소지품_행(아이템, 개수, 종류))

    def _다시그리기(self):
        대분류, 탭, 목록틀 = self._현재
        self._아이템목록_그리기(self.모드, 대분류, 탭, 목록틀)

    def _소지품_행(self, 아이템, 개수, 종류):
        글자 = _행_글자크기
        행 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=56, spacing=4
        )
        이름라벨 = Label(
            text=아이템_이름_글(아이템),
            markup=True,
            size_hint=(0.44, 1),
            halign="left",
            valign="middle",
            font_size=글자,
            shorten=True,
            shorten_from="right",
        )
        이름라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        행.add_widget(이름라벨)
        행.add_widget(Label(text=f"x{개수}", size_hint=(0.14, 1), font_size=글자))
        상세버튼 = Button(text="상세보기", size_hint=(0.22, 1), font_size=글자)
        상세버튼.bind(on_release=lambda *_: self._상세보기(아이템))
        행.add_widget(상세버튼)
        if 종류:
            사용버튼 = Button(text="사용", size_hint=(0.2, 1), font_size=글자)
            사용버튼.bind(on_release=lambda *_: self._사용(종류, 아이템))
            행.add_widget(사용버튼)
        else:
            행.add_widget(Widget(size_hint=(0.2, 1)))
        return 행

    def _상세보기(self, 아이템):
        줄들 = gameflow.소지품_상세(아이템)
        if 줄들 is None:
            self._자세히보기(아이템)
            return
        줄들 = 줄들 + [
            f"가격: {아이템.get('가격', 0)}G (판매가 {gameflow.상점_판매가(아이템)}G)"
        ]
        self._알림(아이템["이름"], "\n".join(줄들))

    def _알림(self, 제목, 문구):
        본문 = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        문구라벨 = Label(text=문구, markup=True, halign="center", valign="middle")
        문구라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        본문.add_widget(문구라벨)
        팝업 = Popup(title=제목, content=본문, size_hint=(0.85, None), height=dp(300))
        본문.add_widget(닫기_버튼(팝업, size_hint=(1, None), height=dp(52)))
        팝업.open()
        return 팝업

    def _사용(self, 종류, 아이템):
        게임상태 = App.get_running_app().게임상태
        이름 = 아이템["이름"]
        if 종류 == "항아리":
            try:
                장비 = gameflow.항아리_열기(게임상태, 이름)
            except ValueError as 오류:
                self._알림(이름, str(오류))
                return
            self._알림(이름, f"{아이템_이름_글(장비)}이(가) 나왔습니다!")
            self._다시그리기()
            return
        if 종류 == "인형":  # 파티에 붙는다(있으면 새 인형으로) - 고를 대상이 없다
            try:
                인형 = gameflow.인형_사용(게임상태, 이름)
            except ValueError as 오류:
                self._알림(이름, str(오류))
                return
            self._알림(이름, f"인형 '{인형['캐릭터명']}'이(가) 파티에 합류했습니다!")
            self._다시그리기()
            return
        self._대상_고르기(종류, 이름)

    def _레테_사용(self, 팝업, 종류, 이름, 캐릭터):
        """레테의 강물·눈물(#351) - 고른 캐릭터의 주/보조/약점을 다시 고른다(처음엔 지금 역할).
        강물은 레벨 1로 되돌리므로 한 번 더 묻는다."""
        팝업.dismiss()
        게임상태 = App.get_running_app().게임상태
        강물 = 종류 == "레테의 강물"

        def 쓰기(구성):
            try:
                if 강물:
                    환급 = gameflow.레테의_강물_사용(게임상태, 캐릭터, 구성)
                    결과 = f"레벨 1로 돌아갔습니다. {환급}골드를 돌려받았습니다."
                else:
                    gameflow.레테의_눈물_사용(게임상태, 캐릭터, 구성)
                    결과 = "능력치를 다시 골랐습니다."
            except ValueError as 오류:
                self.안내라벨.text = f"{캐릭터['캐릭터명']}: {오류}"
                return
            self.안내라벨.text = f"{캐릭터['캐릭터명']} - {이름}: {결과}"
            self._다시그리기()

        def 확인(구성):
            if not 강물:
                쓰기(구성)
                return
            환급 = gameflow.레테_환급골드(캐릭터)
            self._레테_확인팝업 = 확인_팝업(
                이름,
                f"{캐릭터['캐릭터명']}을(를) 레벨 1로 되돌립니다.\n"
                f"퍽·특성·전직과 배운 스킬을 잊고, 스킬 값 {환급}골드를 돌려받습니다.",
                lambda: 쓰기(구성),
            )

        self._레테_팝업 = 능력치역할_팝업(
            f"{이름} - {캐릭터['캐릭터명']}",
            캐릭터,
            gameflow.능력치재선택_기본구성(캐릭터),
            확인콜백=확인,
            안내="주/보조/약점 능력치를 다시 고른다."
            + (
                "\n레벨 1의 13/12/10/8로 시작한다."
                if 강물
                else "\n값은 역할끼리 바뀐다."
            ),
            취소콜백=lambda: None,
        )

    def _대상_고르기(self, 종류, 이름):
        게임상태 = App.get_running_app().게임상태
        본문 = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(12))
        팝업 = Popup(title=f"{이름} - 누구에게?", content=본문, size_hint=(0.85, 0.6))
        for 캐릭터 in 게임상태["파티"]["파티원"]:
            버튼 = Button(
                text=f"{캐릭터['캐릭터명']}  HP {캐릭터['현재HP']}/"
                f"{gameflow.캐릭터_최대HP(게임상태, 캐릭터)}  MP {캐릭터['현재MP']}/"
                f"{gameflow.캐릭터_최대MP(게임상태, 캐릭터)}"
            )
            사용 = self._레테_사용 if 종류.startswith("레테") else self._대상에게_사용
            버튼.bind(on_release=lambda *_, c=캐릭터, f=사용: f(팝업, 종류, 이름, c))
            본문.add_widget(버튼)
        본문.add_widget(닫기_버튼(팝업, size_hint=(1, None), height=dp(52)))
        팝업.open()
        self._대상팝업 = 팝업

    def _대상에게_사용(self, 팝업, 종류, 이름, 캐릭터):
        게임상태 = App.get_running_app().게임상태
        try:
            if 종류 == "회복포션":
                대상, 회복 = gameflow.캐릭터_포션사용(게임상태, 캐릭터, 이름)
                결과 = f"{대상} {회복} 회복"
            elif 종류 == "주류":
                회복, 취기 = gameflow.캐릭터_주류사용(게임상태, 캐릭터, 이름)
                결과 = gameflow.주류_결과_문구(회복, 취기)
            else:
                회복 = gameflow.캐릭터_음식사용(게임상태, 캐릭터, 이름)
                결과 = ", ".join(f"{k} {v} 회복" for k, v in 회복.items())
        except ValueError as 오류:
            self.안내라벨.text = f"{캐릭터['캐릭터명']}: {오류}"
            팝업.dismiss()
            return
        팝업.dismiss()
        self.안내라벨.text = f"{캐릭터['캐릭터명']} - {이름}: {결과}"
        self._다시그리기()


# =====================================================
# 4-3. 주점 화면 (마을 -> 주점) - 파티원 영입/대기/합류/추방
# =====================================================
# 파티에 없는 동료는 "모험단 숙소"(최대 20명)에서 기다린다. 로직은 전부
# gameflow.파티원_*() -> lodge_system.py에 있고, 이 화면은 버튼/팝업만 만든다.


def _동료_글(캐릭터):
    return f"{캐릭터['캐릭터명']}  ({gameflow.캐릭터_직업표시(캐릭터)})  Lv.{캐릭터['레벨']}"


class 주점화면(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        루트 = BoxLayout(orientation="vertical", padding=16, spacing=10)
        루트.add_widget(Label(text="주점", font_size="24sp", size_hint=(1, 0.12)))

        self.현황라벨 = Label(text="", size_hint=(1, 0.1))
        루트.add_widget(self.현황라벨)

        버튼그리드 = GridLayout(cols=2, size_hint=(1, 0.46), spacing=8)
        for 글, 처리 in (
            ("파티원 영입", self._영입_팝업),
            ("파티원 대기", self._대기_팝업),
            ("파티원 합류", self._합류_팝업),
            ("파티원 추방", self._추방_팝업),
        ):
            버튼 = Button(text=글)
            버튼.bind(on_release=lambda *_, f=처리: f())
            버튼그리드.add_widget(버튼)
        루트.add_widget(버튼그리드)

        self.안내라벨 = Label(
            text="", size_hint=(1, 0.12), halign="center", valign="middle"
        )
        self.안내라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        루트.add_widget(self.안내라벨)

        뒤로버튼 = Button(text="뒤로", size_hint=(1, 0.1))
        뒤로키_버튼(뒤로버튼)
        뒤로버튼.bind(on_release=lambda *_: setattr(self.manager, "current", "마을"))
        루트.add_widget(뒤로버튼)
        self.add_widget(루트)

    def on_pre_enter(self, *args):
        self.안내라벨.text = ""
        self.갱신()

    def _게임상태(self):
        return App.get_running_app().게임상태

    def 갱신(self):
        현황 = gameflow.주점_현황(self._게임상태())
        self.현황라벨.text = (
            f"파티 {현황['파티인원']}/{현황['파티최대']}명  ·  "
            f"모험단 숙소 {현황['숙소인원']}/{현황['숙소최대']}명  ·  "
            f"보유 골드 {현황['골드']}"
        )

    def _실행(self, 처리, 성공글, 팝업=None):
        """처리()가 ValueError면 안내 줄에 이유를 보이고 팝업은 그대로 둔다."""
        try:
            처리()
        except ValueError as 오류:
            self.안내라벨.text = str(오류)
        else:
            self.안내라벨.text = 성공글
            if 팝업 is not None:
                팝업.dismiss()
        self.갱신()

    # -------------------------------------------------
    # 영입 - 이름 + 직업, 레벨 1, 영입_비용 골드
    # -------------------------------------------------

    def _영입_팝업(self):
        본문 = BoxLayout(orientation="vertical", spacing=8, padding=12)
        본문.add_widget(
            Label(
                text=f"새 동료 (레벨 1, {gameflow.영입_비용}골드)\n"
                "파티가 가득 차 있으면 모험단 숙소로 갑니다.",
                size_hint=(1, 0.2),
                halign="center",
            )
        )
        이름칸 = TextInput(
            text="",
            hint_text=gameflow.캐릭터명_안내 + " (비우면 직업 이름)",
            multiline=False,
            size_hint=(1, 0.11),
        )
        이름칸.bind(
            text=lambda inst, 값: (
                setattr(inst, "text", gameflow.이름_자르기(값))
                if gameflow.이름_폭(값) > gameflow.캐릭터명_최대폭
                else None
            )
        )
        본문.add_widget(이름칸)
        직업선택 = Spinner(
            text=gameflow.직업목록[0], values=gameflow.직업목록, size_hint=(1, 0.11)
        )
        본문.add_widget(직업선택)
        # 능력치 칸을 터치해 주(노랑)/보조(파랑)/약점(빨강)스탯을 고른다 - 점수는 바로 보인다
        자원라벨 = Label(text="", markup=True, size_hint=(1, 0.08))
        본문.add_widget(자원라벨)

        def 미리보기_갱신(스탯구성):
            미리 = gameflow.캐릭터_미리보기(직업선택.text, 스탯구성)
            자원라벨.text = (
                f"[color=e05555]HP {미리['기본최대HP']}[/color]    "
                f"[color=6fa0ff]MP {미리['기본최대MP']}[/color]"
            )
            if None in 스탯구성.values():  # 안내 줄은 팝업에 가려서 여기 알린다
                자원라벨.text += (
                    "    [color=e05555]주/보조/약점을 모두 고르세요[/color]"
                )
            스탯판.설정(스탯구성, 미리)

        스탯판 = 스탯고르기판(바뀜=미리보기_갱신, font_size="14sp", size_hint=(1, 0.24))
        본문.add_widget(스탯판)
        직업선택.bind(text=lambda inst, 값: 미리보기_갱신(gameflow.기본_스탯구성(값)))
        미리보기_갱신(gameflow.기본_스탯구성(직업선택.text))
        팝업 = Popup(
            title="파티원 영입",
            content=본문,
            size_hint=(0.85, 0.75),
            auto_dismiss=False,
        )
        결과 = {}

        def 영입():
            결과["캐릭터"], 결과["자리"] = gameflow.파티원_영입(
                self._게임상태(), 이름칸.text, 직업선택.text, 스탯판.스탯구성
            )

        def 누름(*_):
            self._실행(영입, "", 팝업)
            if 결과:
                자리글 = (
                    "파티에 합류했습니다"
                    if 결과["자리"] == "파티"
                    else "모험단 숙소로 갔습니다"
                )
                self.안내라벨.text = (
                    f"{결과['캐릭터']['캐릭터명']}을(를) 영입해 {자리글}."
                )

        버튼줄 = BoxLayout(orientation="horizontal", spacing=8, size_hint=(1, 0.14))
        영입버튼 = Button(text=f"영입 ({gameflow.영입_비용}골드)")
        영입버튼.bind(on_release=누름)
        취소버튼 = Button(text="취소")
        뒤로키_버튼(취소버튼)
        취소버튼.bind(on_release=lambda *_: 팝업.dismiss())
        버튼줄.add_widget(영입버튼)
        버튼줄.add_widget(취소버튼)
        본문.add_widget(버튼줄)
        팝업.open()

    # -------------------------------------------------
    # 대기 / 합류 / 추방 - 동료 목록 팝업
    # -------------------------------------------------

    def _목록_팝업(self, 제목, 안내, 캐릭터목록, 누르면):
        본문 = BoxLayout(orientation="vertical", spacing=8, padding=12)
        본문.add_widget(Label(text=안내, size_hint=(1, 0.1)))
        스크롤, 목록틀 = 스크롤_목록(0.78)
        본문.add_widget(스크롤)
        팝업 = Popup(
            title=제목, content=본문, size_hint=(0.9, 0.85), auto_dismiss=False
        )
        if not 캐릭터목록:
            목록틀.add_widget(Label(text="(없음)", size_hint=(1, None), height=dp(40)))
        for 캐릭터 in 캐릭터목록:
            버튼 = Button(text=_동료_글(캐릭터), size_hint=(1, None), height=dp(48))
            버튼.bind(on_release=lambda *_, c=캐릭터: 누르면(c, 팝업))
            목록틀.add_widget(버튼)
        닫기 = 닫기_버튼(팝업, size_hint=(1, 0.12))
        본문.add_widget(닫기)
        팝업.open()

    def _대기_팝업(self):
        상태 = self._게임상태()
        self._목록_팝업(
            "파티원 대기",
            "모험단 숙소로 보낼 파티원 (최소 1명은 남아야 합니다)",
            list(상태["파티"]["파티원"]),
            lambda c, 팝업: self._실행(
                lambda: gameflow.파티원_대기(상태, c),
                f"{c['캐릭터명']}이(가) 모험단 숙소로 갔습니다.",
                팝업,
            ),
        )

    def _합류_팝업(self):
        상태 = self._게임상태()
        self._목록_팝업(
            "파티원 합류",
            "모험단 숙소에서 데려올 동료",
            list(gameflow.숙소_목록(상태)),
            lambda c, 팝업: self._실행(
                lambda: gameflow.파티원_합류(상태, c),
                f"{c['캐릭터명']}이(가) 파티에 합류했습니다.",
                팝업,
            ),
        )

    def _추방_팝업(self):
        상태 = self._게임상태()
        self._목록_팝업(
            "파티원 추방",
            "추방할 동료 (끼고 있던 장비는 소지품으로 돌아갑니다)",
            list(상태["파티"]["파티원"]) + list(gameflow.숙소_목록(상태)),
            lambda c, 팝업: self._추방_확인(c, 팝업),
        )

    def _추방_확인(self, 캐릭터, 목록팝업):
        본문 = BoxLayout(orientation="vertical", spacing=8, padding=12)
        본문.add_widget(
            Label(
                text=f"{_동료_글(캐릭터)}\n\n정말 추방할까요? 되돌릴 수 없습니다.\n"
                "끼고 있던 장비는 소지품으로 돌아갑니다.",
                halign="center",
            )
        )
        팝업 = Popup(
            title="파티원 추방", content=본문, size_hint=(0.8, 0.5), auto_dismiss=False
        )

        def 추방(*_):
            팝업.dismiss()
            self._실행(
                lambda: gameflow.파티원_추방(self._게임상태(), 캐릭터),
                f"{캐릭터['캐릭터명']}을(를) 추방했습니다.",
                목록팝업,
            )

        버튼줄 = BoxLayout(orientation="horizontal", spacing=8, size_hint=(1, 0.3))
        추방버튼 = Button(text="추방")
        추방버튼.bind(on_release=추방)
        취소버튼 = Button(text="취소")
        뒤로키_버튼(취소버튼)
        취소버튼.bind(on_release=lambda *_: 팝업.dismiss())
        버튼줄.add_widget(추방버튼)
        버튼줄.add_widget(취소버튼)
        본문.add_widget(버튼줄)
        팝업.open()
