"""상점 갈래 화면 - 상점(구매·판매·장비/인형 탭), 전문직업(해체·봉인·강화·마법부여·인형사·연금술), 소지품/창고.

마을 화면(screens_town.py)에서 갈라져 나왔다. 전문직업화면과 소지품화면은 상점화면의 목록 틀을 물려받는다."""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.utils import escape_markup
import gameflow
from game.screens.screens_common import (
    _버튼_높이,
    _버튼_폰트크기,
    뒤로키_버튼,
    능력치역할_팝업,
    확인_팝업,
    닫기_버튼,
    탭_줄,
    글자_높이,
    아이템_이름_글,
)


_행_글자크기 = "16sp"  # 상점 아이템 줄의 글자 크기(이름/버튼/가격/수량 모두)


class 상점화면(Screen):
    제목 = "상점"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.복귀화면 = "마을"
        # None이면 마을 "상점판매목록", NPC [상점]으로 열면 그 NPC의 판매목록(나가면 None으로)
        self.판매목록 = None

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
        self.판매목록 = None
        self.manager.current = self.복귀화면

    def _판매목록(self, 마을정보):
        return (
            self.판매목록 if self.판매목록 is not None else 마을정보.get("상점판매목록")
        )

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
        elif 모드 == "판매":
            # 체크박스 판매 - [일괄해제] [일괄선택] [판매]는 목록 아래(판매는 오른쪽 아래)
            self.내용틀.add_widget(self._일괄판매_줄(대분류, 목록틀))

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
        self._판매체크 = []  # 판매 줄마다 (부위 탭, 이름, 수량상태, 체크박스)
        self._판매_표시탭 = 탭
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
                    self._판매목록(마을정보),
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
        # 판매 줄은 1.5배 높이(잘못 누르기 쉬웠다)
        줄높이 = 행높이 * 3 // 2 if 모드 == "판매" else 행높이
        글자 = _행_글자크기  # 이 줄의 글자/버튼은 모두 같은 크기, 세로 가운데
        행 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=줄높이, spacing=4
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

        if 모드 == "판매":  # 줄마다 [판매] 대신 체크박스 - 체크한 줄을 그 수량만큼 판다
            체크 = CheckBox(size_hint=(0.12, 1))
            self._판매체크.append((탭, 아이템["이름"], 수량상태, 체크))
            행.add_widget(체크)
            return 행
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
                    상점판매목록=self._판매목록(마을정보),
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

    def _일괄판매_줄(self, 대분류, 목록틀):
        """[일괄해제](체크 모두 풀기) [일괄선택](지금 목록 모두 체크) [판매](체크한 것, 오른쪽 아래) -."""
        줄 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=글자_높이(), spacing=4
        )
        해제 = Button(text="일괄해제")
        해제.bind(on_release=lambda *_: self._판매체크_모두(False))
        선택 = Button(text="일괄선택")
        선택.bind(on_release=lambda *_: self._판매체크_모두(True))
        판매 = Button(text="판매")
        판매.bind(on_release=lambda *_: self._체크_판매(대분류, 목록틀))
        for 버튼 in (해제, 선택, 판매):
            줄.add_widget(버튼)
        return 줄

    def _판매체크_모두(self, 켜기):
        for *_, 체크 in getattr(self, "_판매체크", []):
            체크.active = 켜기

    def _체크_판매(self, 대분류, 목록틀):
        항목들 = [
            (탭, 이름, 수량상태["값"])
            for 탭, 이름, 수량상태, 체크 in getattr(self, "_판매체크", [])
            if 체크.active
        ]
        if not 항목들:
            self.안내라벨.text = "판매할 물건을 체크하세요."
            return
        try:
            금액 = gameflow.상점_일괄판매(
                App.get_running_app().게임상태, 대분류, 항목들
            )
        except ValueError as 오류:
            self.안내라벨.text = str(오류)
            return
        self.안내라벨.text = f"{len(항목들)}종을 {금액}G에 팔았습니다."
        self._골드_갱신()
        self._아이템목록_그리기("판매", 대분류, self._판매_표시탭, 목록틀)

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

    # 레어 무기의 고유효과/오라/스킬강화는 원소를 그대로 보이지 않고 "설명"으로 보인다
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
            # 긴 글(레어 무기 "설명")은 줄을 바꿔 그만큼 높아진다(겹치지 않게)
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


class 전문직업화면(상점화면):
    """마을 [전문직업] - 장비강화/장비해체/마법부여/봉인해제/봉인변환, 인형사.
    장비해체는 상점에 있던 [해체]를 옮겨 온 것(상점화면의 해체 목록을 그대로 쓴다).
    봉인해제/봉인변환/장비강화/마법부여는 장착 중인 장비도 고를 수 있다.
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
            elif 메뉴 == "장비강화":
                버튼.bind(on_release=lambda *_: self._강화메뉴_그리기())
            elif 메뉴 == "마법부여":
                버튼.bind(on_release=lambda *_: self._부여_그리기())
            elif 메뉴 == "연금술":
                버튼.bind(on_release=lambda *_: self._연금술_그리기())
            elif 구현됨:
                버튼.bind(on_release=lambda *_, m=메뉴: self._봉인_그리기(m))
            self.내용틀.add_widget(버튼)
        나가기버튼 = Button(text="나가기", font_size=_버튼_폰트크기)
        뒤로키_버튼(나가기버튼)
        나가기버튼.bind(on_release=self._나가기)
        self.내용틀.add_widget(나가기버튼)

    def _하위창_틀(self, 제목글, 뒤로=None):
        """[◀ 뒤로] + 제목 줄과 스크롤 목록틀(self._목록틀)을 그린다 - 봉인해제/봉인변환/인형사/장비강화 공용.
        뒤로를 주면 [◀ 뒤로]가 그것을 부른다(기본은 전문직업 메뉴)."""
        self._비우기()
        상단 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=글자_높이()
        )
        뒤로버튼 = Button(text="◀ 뒤로", size_hint=(0.32, 1))
        뒤로키_버튼(뒤로버튼)
        뒤로버튼.bind(on_release=lambda *_: (뒤로 or self._메인_그리기)())
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
            f"{escape_markup(항목['캐릭터']['캐릭터명'])} 착용"
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

    # ------------------------------------------------------------ 장비강화

    def _강화메뉴_그리기(self):
        """[장비강화] - 무기강화/무기증폭/무기재련/방어구강화/악세재련/특수장비증폭."""
        self._하위창_틀("장비강화")
        self.안내라벨.text = ""
        for 선택지 in gameflow.장비강화_메뉴:
            버튼 = Button(
                text=선택지,
                font_size=_버튼_폰트크기,
                size_hint=(1, None),
                height=글자_높이() * 1.6,
            )
            버튼.bind(on_release=lambda *_, s=선택지: self._강화_그리기(s))
            self._목록틀.add_widget(버튼)

    def _강화_그리기(self, 선택지):
        """선택지의 소지품/장착 장비 목록 - 줄마다 이름(장착 중이면 (착용중)), 비용, [자세히], 실행 버튼."""
        self._하위창_틀(선택지, 뒤로=self._강화메뉴_그리기)
        self._강화목록_채우기(선택지)

    def _강화목록_채우기(self, 선택지):
        목록틀 = self._목록틀
        목록틀.clear_widgets()
        항목들 = gameflow.전문직업_강화목록(App.get_running_app().게임상태, 선택지)
        if not 항목들:
            목록틀.add_widget(
                Label(
                    text="강화할 수 있는 장비가 없습니다.",
                    size_hint=(1, None),
                    height=글자_높이(),
                )
            )
            return
        for 항목 in 항목들:
            목록틀.add_widget(self._강화_행(선택지, 항목))

    def _강화_행(self, 선택지, 항목):
        글자 = _행_글자크기
        행 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=72, spacing=4
        )
        위치 = (
            f" (착용중) - {escape_markup(항목['캐릭터']['캐릭터명'])}"
            if 항목["캐릭터"] is not None
            else f" x{항목['수량']}"
        )
        왼쪽 = BoxLayout(orientation="vertical", size_hint=(0.6, 1))
        for 글, 크기 in (
            (f"{아이템_이름_글(항목['아이템'])}{위치}", 글자),
            (
                항목["불가"] or f"비용: {항목['비용글']}",
                "13sp",
            ),  # 아래 줄 - 비용 또는 못 하는 이유
        ):
            라벨 = Label(
                text=글,
                markup=True,
                halign="left",
                valign="middle",
                font_size=크기,
                shorten=True,
                shorten_from="right",
            )
            라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
            왼쪽.add_widget(라벨)
        행.add_widget(왼쪽)
        자세히버튼 = Button(text="자세히", size_hint=(0.16, 1), font_size=글자)
        자세히버튼.bind(on_release=lambda *_: self._자세히보기(항목["아이템"]))
        행.add_widget(자세히버튼)
        실행버튼 = Button(
            text=선택지[-2:],
            size_hint=(0.24, 1),
            font_size=글자,
            disabled=bool(항목["불가"]),
        )
        실행버튼.bind(on_release=lambda *_: self._강화_실행(선택지, 항목))
        행.add_widget(실행버튼)
        return 행

    def _강화_실행(self, 선택지, 항목):
        try:
            새이름 = gameflow.전문직업_강화(
                App.get_running_app().게임상태, 항목, 선택지
            )
        except ValueError as 오류:
            self.안내라벨.text = str(오류)
            return
        self._골드_갱신()
        self._강화목록_채우기(선택지)
        self.안내라벨.text = f"{항목['이름']} -> {새이름}"

    # ------------------------------------------------------------ 마법부여

    def _부여_그리기(self, 탭=None):
        """[마법부여] - 부위 탭 2줄 + 그 부위의 소지품/장착 장비 목록(줄마다 [자세히], [선택])."""
        탭줄들 = gameflow.마법부여_탭줄()
        self._부여탭 = 탭 or 탭줄들[0][0]
        self._하위창_틀("마법부여")
        칸수 = max(len(줄) for 줄 in 탭줄들)
        그룹 = f"마법부여부위{id(self)}"
        for 줄 in 탭줄들:  # 제목 줄과 목록 사이에 넣는다(목록 스크롤이 맨 끝 = index 0)
            self.내용틀.add_widget(
                탭_줄(
                    줄,
                    self._부여목록_채우기,
                    self._부여탭,
                    높이=글자_높이("14sp"),
                    그룹=그룹,
                    칸수=칸수,
                ),
                index=1,
            )
        self._부여목록_채우기(self._부여탭)

    def _부여목록_채우기(self, 탭):
        self._부여탭 = 탭
        목록틀 = self._목록틀
        목록틀.clear_widgets()
        항목들 = gameflow.전문직업_마법부여목록(App.get_running_app().게임상태, 탭)
        if not 항목들:
            목록틀.add_widget(
                Label(
                    text=f"{탭} 장비가 없습니다.",
                    size_hint=(1, None),
                    height=글자_높이(),
                )
            )
            return
        for 항목 in 항목들:
            아래 = 항목["불가"] or (
                f"마법부여: {항목['아이템'].get('마법부여') or '없음'}"
            )
            목록틀.add_widget(
                self._부여_행(
                    항목,
                    아래,
                    "선택",
                    lambda 항목=항목: self._부여선택_그리기(항목),
                    자세히=True,
                )
            )

    def _부여_행(self, 항목, 아래글, 버튼글, 누르기, 자세히=False):
        """[이름(위치) / 아래글] + ([자세히]) + 실행 버튼 한 줄 - 장비 목록과 마법부여 목록 공용."""
        글자 = _행_글자크기
        행 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=72, spacing=4
        )
        if "아이템" in 항목:
            위치 = (
                f" (착용중) - {escape_markup(항목['캐릭터']['캐릭터명'])}"
                if 항목["캐릭터"] is not None
                else f" x{항목['수량']}"
            )
            위글 = f"{아이템_이름_글(항목['아이템'])}{위치}"
        else:
            위글 = f"{항목['이름']} - {항목['설명']}"
        왼쪽 = BoxLayout(orientation="vertical", size_hint=(0.6 if 자세히 else 0.76, 1))
        for 글, 크기 in ((위글, 글자), (아래글, "13sp")):
            라벨 = Label(
                text=글,
                markup=True,
                halign="left",
                valign="middle",
                font_size=크기,
                shorten=True,
                shorten_from="right",
            )
            라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
            왼쪽.add_widget(라벨)
        행.add_widget(왼쪽)
        if 자세히:
            자세히버튼 = Button(text="자세히", size_hint=(0.16, 1), font_size=글자)
            자세히버튼.bind(on_release=lambda *_: self._자세히보기(항목["아이템"]))
            행.add_widget(자세히버튼)
        실행버튼 = Button(
            text=버튼글,
            size_hint=(0.24, 1),
            font_size=글자,
            disabled=bool(항목["불가"]),
        )
        실행버튼.bind(on_release=lambda *_: 누르기())
        행.add_widget(실행버튼)
        return 행

    def _부여선택_그리기(self, 항목):
        """장비 하나에 걸 수 있는 마법부여 목록 - 줄마다 이름·효과, 비용(또는 못 거는 이유), [부여]."""
        탭 = self._부여탭
        self._하위창_틀(
            f"마법부여 - {항목['이름']}", 뒤로=lambda: self._부여_그리기(탭)
        )
        self.안내라벨.text = ""
        게임상태 = App.get_running_app().게임상태
        for 선택지 in gameflow.전문직업_마법부여선택지(게임상태, 항목):
            self._목록틀.add_widget(
                self._부여_행(
                    선택지,
                    선택지["불가"] or f"비용: {선택지['비용글']}",
                    "부여",
                    lambda s=선택지["이름"]: self._부여_실행(항목, s),
                )
            )

    def _부여_실행(self, 항목, 부여):
        try:
            새이름 = gameflow.전문직업_마법부여(
                App.get_running_app().게임상태, 항목, 부여
            )
        except ValueError as 오류:
            self.안내라벨.text = str(오류)
            return
        self._골드_갱신()
        self._부여_그리기(self._부여탭)
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

    # ------------------------------------------------------------ 연금술 (전체/재료/소모품 탭)

    def _연금술_그리기(self, 탭="전체"):
        self._하위창_틀("연금술")
        탭줄 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=글자_높이()
        )
        for 이름 in gameflow.연금술_탭목록:
            탭버튼 = ToggleButton(
                text=이름, group="연금술탭", state="down" if 이름 == 탭 else "normal"
            )
            탭버튼.bind(on_release=lambda *_, t=이름: self._연금술_그리기(t))
            탭줄.add_widget(탭버튼)
        self.내용틀.add_widget(탭줄, index=1)  # 제목 줄과 목록 사이
        self._연금술탭 = 탭
        self._연금술목록_채우기()

    def _연금술목록_채우기(self):
        self._목록틀.clear_widgets()
        상태 = App.get_running_app().게임상태
        for 항목 in gameflow.전문직업_연금술목록(상태, self._연금술탭):
            self._목록틀.add_widget(self._연금술_행(항목))

    def _연금술_행(self, 항목):
        글자 = _행_글자크기
        행 = BoxLayout(
            orientation="horizontal", size_hint=(1, None), height=56, spacing=4
        )
        이름라벨 = Label(
            text=f"{항목['이름']}  ({항목['재료글']})",
            size_hint=(0.8, 1),
            halign="left",
            valign="middle",
            font_size=글자,
            shorten=True,
            shorten_from="right",
        )
        이름라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        행.add_widget(이름라벨)
        제작버튼 = Button(
            text="제작",
            size_hint=(0.2, 1),
            font_size=글자,
            disabled=not 항목["제작가능"],
        )
        제작버튼.bind(on_release=lambda *_: self._연금술_제작(항목))
        행.add_widget(제작버튼)
        return 행

    def _연금술_제작(self, 항목):
        try:
            gameflow.전문직업_연금술(App.get_running_app().게임상태, 항목)
        except ValueError as 오류:
            self.안내라벨.text = str(오류)
            return
        self._연금술목록_채우기()
        self.안내라벨.text = f"'{항목['이름']}'을(를) 만들었습니다."


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
        if 종류 == "스프레이":  # 던전 안에서만 - 파티 전체 효과라 고를 대상이 없다
            try:
                문구 = gameflow.스프레이_사용(게임상태, 이름)
            except ValueError as 오류:
                self._알림(이름, str(오류))
                return
            self._알림(이름, 문구)
            self._다시그리기()
            return
        self._대상_고르기(종류, 이름)

    def _레테_사용(self, 팝업, 종류, 이름, 캐릭터):
        """레테의 강물·눈물 - 고른 캐릭터의 주/보조/약점을 다시 고른다(처음엔 지금 역할).
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
            elif 종류 == "부여":  # 속성 플라스크
                결과 = gameflow.캐릭터_부여아이템사용(게임상태, 캐릭터, 이름)
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
