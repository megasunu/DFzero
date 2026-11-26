# =====================
# 마을 화면 - 마을, 모험단, 마을 이동 목록, 상점, 주점(모험단 숙소)
# =====================
# main.py가 game/screens/ 일곱 파일의 화면을 ScreenManager에 등록한다.

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.metrics import dp

import gameflow
from game.screens.screens_common import (
    게임메뉴_열기,
    _기본_초상화_코드,
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
    타이틀_경고,
    닫기_버튼,
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
그림_버튼_간격 = 16  # 마을 그림과 버튼 사이(버튼 사이보다 8 더)
하단_버튼_높이 = 785  # 휴식~창고 5줄 + 타이틀


def 소지품_열기(화면, 복귀화면):
    """마을/던전에서 소지품 화면으로 - 나가면 복귀화면으로 돌아간다."""
    화면.manager.get_screen("소지품").복귀화면 = 복귀화면
    화면.manager.current = "소지품"


class 마을화면(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 상단(1170): 1줄 파티원 상자, 2~4줄 마을 그림(비율 유지, 970 칸의 아래에 붙이고 남는 위는 비움)
        # 하단(1170): 버튼/타이틀을 위에 붙이고(그림과 사이에 검은 곳 없이), 메시지는 그 아래
        # - 마을 이름 줄은 없다
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
        # 그림틀: 마을 그림 위에 NPC [대화] 장면(가운데 일러스트 + 아래쪽 대화창)을 겹친다 - 평소에는 비어 있다
        self._그림틀 = FloatLayout(size_hint=(1, None), height=상단_그림_높이)
        그림칸.size_hint = (1, 1)
        그림칸.pos_hint = {"x": 0, "y": 0}
        self._그림틀.add_widget(그림칸)
        상단.add_widget(self._그림틀)
        루트.add_widget(상단)
        self._대화_장면_만들기()

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

        # [스킬] - 전환스킬(나선의 넨·프렌지) 켜고 끄기(던전 [스킬]과 같은 처리)
        스킬버튼 = Button(text="스킬")
        스킬버튼.bind(on_release=self._스킬_클릭)
        버튼그리드.add_widget(스킬버튼)

        # [NPC] - 이 마을에서 대화할 수 있는 NPC와 대화·퀘스트
        NPC버튼 = Button(text="NPC")
        NPC버튼.bind(on_release=self._NPC_클릭)
        버튼그리드.add_widget(NPC버튼)

        나머지.add_widget(버튼그리드)

        타이틀버튼 = Button(text="타이틀로 돌아가기", size_hint=(1, 0.2))
        타이틀버튼.bind(
            on_release=lambda *_: 확인_팝업(
                "타이틀로 돌아가기",
                타이틀_경고,
                lambda: setattr(self.manager, "current", "메인메뉴"),
            )
        )
        나머지.add_widget(타이틀버튼)

        # 대화 장면이 떠 있어도 아래 버튼은 누를 수 있다 - 누르면 장면을 닫고 그 버튼의 일을 한다
        for 버튼 in list(버튼그리드.children) + [타이틀버튼]:
            버튼.bind(on_release=self._대화_닫기)

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
        """옛 세이브(버전 10 이하)에서 이미 전직한 캐릭터는 능력치 역할을 한 번 다시 고른다.
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
        self.manager.get_screen("상점").판매목록 = None  # 마을 상점
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

    def _NPC_클릭(self, *args):
        """[NPC] - 이 마을에서 지금 대화할 수 있는 NPC 목록 팝업."""
        게임상태 = App.get_running_app().게임상태
        이름들 = gameflow.마을_NPC_목록(게임상태)
        본문 = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        팝업 = Popup(
            title="NPC",
            content=본문,
            size_hint=(0.8, None),
            height=dp(140 + 64 * max(1, len(이름들))),
        )

        def 대화(이름):
            팝업.dismiss()
            self._NPC_메뉴_열기(이름)

        if not 이름들:
            본문.add_widget(Label(text="대화할 수 있는 NPC가 없습니다."))
        for 이름 in 이름들:
            버튼 = Button(text=이름)
            버튼.bind(on_release=lambda *_, 이름=이름: 대화(이름))
            본문.add_widget(버튼)
        본문.add_widget(닫기_버튼(팝업))
        팝업.open()
        self._NPC_팝업 = 팝업

    def _NPC_메뉴_열기(self, 이름):
        """NPC 메뉴 팝업 - NPC마다 다른 버튼: [대화](늘), [퀘스트](퀘스트가 있으면), [상점](판매목록이 있으면)."""
        게임상태 = App.get_running_app().게임상태
        대화 = gameflow.NPC_대화(게임상태, 이름)
        본문 = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        팝업 = Popup(
            title=이름,
            content=본문,
            size_hint=(0.8, None),
            height=dp(140 + 64 * len(대화["메뉴"])),
        )

        def 고르기(메뉴):
            팝업.dismiss()
            if 메뉴 == "대화":
                self._대화_장면_열기(gameflow.NPC_말걸기(게임상태, 이름))
            elif 메뉴 == "퀘스트":
                self._NPC_퀘스트_열기(이름)
            else:  # 상점 - 마을 상점 화면을 이 NPC의 판매목록으로 연다
                상점 = self.manager.get_screen("상점")
                상점.복귀화면 = "마을"
                상점.판매목록 = 대화["상점판매목록"]
                self.manager.current = "상점"

        for 메뉴 in 대화["메뉴"]:
            버튼 = Button(text=메뉴)
            버튼.bind(on_release=lambda *_, 메뉴=메뉴: 고르기(메뉴))
            본문.add_widget(버튼)
        본문.add_widget(닫기_버튼(팝업))
        팝업.open()
        self._NPC_메뉴_팝업 = 팝업

    def _대화_장면_만들기(self):
        """[대화] 장면 위젯 - 마을 그림 가운데 NPC 일러스트, 그림 아래쪽 대화창(누르면 닫힘)."""
        self.NPC그림 = Image(
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(0.8, 0.8),
            pos_hint={"center_x": 0.5, "center_y": 0.55},
        )
        self._대화층 = AnchorLayout(
            anchor_y="bottom",
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
            padding=(하단_좌우여백 + 16, 0, 하단_좌우여백 + 16, 16),
        )
        self.대화창 = 뒤로키_버튼(
            Button(
                markup=True,
                size_hint=(1, None),
                height=300,
                halign="left",
                valign="top",
                padding=(24, 20),
                background_normal="",
                background_color=(0.05, 0.05, 0.08, 0.85),
            )
        )
        self.대화창.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        self.대화창.bind(on_release=self._대화_닫기)
        self._대화층.add_widget(self.대화창)
        self._대화중 = False
        self._NPC장면_예약 = None
        self.NPC장면번호 = -1

    def _대화_장면_열기(self, 대화):
        """마을 그림 위에 NPC 일러스트(그림이 있으면)와 대화창을 띄운다."""
        self._대화_닫기()
        경로 = _에셋_경로("npc", 대화["일러스트"])
        if 경로 and 대화.get("일러스트장면"):
            self._NPC장면_시작(경로, 대화["일러스트장면"])
            self._그림틀.add_widget(self.NPC그림)
        self.대화창.text = f"[b]{대화['이름']}[/b]\n\n{대화['대사']}"
        self._그림틀.add_widget(self._대화층)
        self._대화중 = True

    def _대화_닫기(self, *args):
        if not self._대화중:
            return
        if self._NPC장면_예약 is not None:
            self._NPC장면_예약.cancel()
            self._NPC장면_예약 = None
        for 위젯 in (self.NPC그림, self._대화층):
            if 위젯.parent is not None:
                self._그림틀.remove_widget(위젯)
        self._대화중 = False

    def _NPC장면_시작(self, 경로, 장면):
        """장면을 이어 붙인 일러스트를 장면 크기로 잘라 장면별 시간마다 넘긴다(대화를 닫으면 멈춘다).
        게임은 움직이는 웹피를 열지 못해 정지 그림 + 장면 정보(gameflow.NPC_말걸기의 "일러스트장면")로 움직인다."""
        전체 = CoreImage(경로).texture
        전체.mag_filter = "nearest"
        가로, 세로, 열 = 장면["가로"], 장면["세로"], 장면["열"]
        # 텍스처 좌표는 아래에서 위로 센다 - 그림의 첫 줄이 텍스처의 맨 위다
        self._NPC장면들 = [
            전체.get_region(
                (번호 % 열) * 가로, 전체.height - (번호 // 열 + 1) * 세로, 가로, 세로
            )
            for 번호 in range(len(장면["시간"]))
        ]
        self._NPC장면시간 = [밀리초 / 1000 for 밀리초 in 장면["시간"]]
        self.NPC장면번호 = -1
        self._NPC장면_넘기기()

    def _NPC장면_넘기기(self, *args):
        self.NPC장면번호 = (self.NPC장면번호 + 1) % len(self._NPC장면들)
        self.NPC그림.texture = self._NPC장면들[self.NPC장면번호]
        self._NPC장면_예약 = None
        if len(self._NPC장면들) > 1:
            self._NPC장면_예약 = Clock.schedule_once(
                self._NPC장면_넘기기, self._NPC장면시간[self.NPC장면번호]
            )

    def _NPC_퀘스트_열기(self, 이름):
        """NPC 퀘스트 팝업 - 그 NPC의 퀘스트(받기/완료 보고). 열려 있던 퀘스트 팝업은 먼저 닫는다 -
        닫히는 중인 메뉴의 [퀘스트]가 한 번 더 눌려도 팝업이 겹치지 않게(#846)."""
        이전 = getattr(self, "_NPC_퀘스트_팝업", None)
        if 이전 is not None:
            이전.dismiss(animation=False)
        게임상태 = App.get_running_app().게임상태
        대화 = gameflow.NPC_대화(게임상태, 이름)
        본문 = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        팝업 = Popup(
            title=f"{이름} - 퀘스트",
            content=본문,
            size_hint=(0.9, None),
            height=dp(140 + 150 * len(대화["퀘스트"])),
        )

        def 다시_열기(문구):
            팝업.dismiss()
            self.메시지라벨.text = 문구
            self._NPC_퀘스트_열기(이름)

        # 닫히는 중인 팝업의 버튼이 늦게 눌리면 이미 받은/보고한 퀘스트일 수 있다 - 그 이유를 보이고 다시 그린다
        def 받기(퀘스트):
            try:
                gameflow.퀘스트_수락(게임상태, 퀘스트["ID"])
            except ValueError as 오류:
                다시_열기(str(오류))
                return
            다시_열기(f"퀘스트 [{퀘스트['이름']}]을(를) 받았습니다.")

        def 보고(퀘스트):
            try:
                보상 = gameflow.퀘스트_완료_보고(게임상태, 퀘스트["ID"])
            except ValueError as 오류:
                다시_열기(str(오류))
                return
            다시_열기(
                f"퀘스트 [{퀘스트['이름']}] 완료 - {보상.get('골드', 0)}G를 받았습니다."
            )

        버튼글 = {
            "수락전": "퀘스트 받기",
            "진행중": "진행 중",
            "완료가능": "완료 보고",
            "완료": "완료함",
        }
        for 퀘스트 in 대화["퀘스트"]:
            설명 = Label(
                text=(
                    f"[퀘스트] {퀘스트['이름']}\n{퀘스트['설명']}\n"
                    f"보상: {퀘스트['보상']}"
                ),
                halign="left",
                valign="middle",
                size_hint=(1, None),
                height=dp(90),
            )
            설명.bind(size=lambda inst, size: setattr(inst, "text_size", size))
            본문.add_widget(설명)
            버튼 = Button(
                text=버튼글[퀘스트["상태"]],
                size_hint=(1, None),
                height=dp(52),
                disabled=퀘스트["상태"] in ("진행중", "완료"),
            )
            if 퀘스트["상태"] == "수락전":
                버튼.bind(on_release=lambda *_, q=퀘스트: 받기(q))
            elif 퀘스트["상태"] == "완료가능":
                버튼.bind(on_release=lambda *_, q=퀘스트: 보고(q))
            본문.add_widget(버튼)
        본문.add_widget(닫기_버튼(팝업, size_hint=(1, None), height=dp(52)))
        팝업.open()
        self._NPC_퀘스트_팝업 = 팝업


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


# =====================================================
# 4-2b. 소지품 화면 (마을 [소지품/창고] -> [소지품], 던전 방향키 왼쪽 아래 [소지품])
# =====================================================
# 상점처럼 대분류 -> 탭(-> 하위 탭) -> 목록. 줄마다 [상세보기], 쓸 수 있는 것(항아리/회복포션/
# 음식/주류)은 [사용]. 항아리는 바로 열고, 나머지는 쓸 파티원을 고른다. 전투 중 아이템은 전투 화면에서.


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
