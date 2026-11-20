"""파티원 화면 - 한 파티원의 능력치·장비창, 장비 교체 팝업, 아이템 상세 팝업.

파티 관리 화면(screens_party.py)에서 갈라져 나왔다."""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.graphics import Color, Line
from kivy.utils import escape_markup
import gameflow
from game.screens.screens_common import (
    _캐릭터이미지_경로,
    뒤로키_버튼,
    스크롤_목록,
    닫기_버튼,
    탭_줄,
    아이템_이름_글,
)
from game.screens.screens_party import (
    _줄바꿈_라벨,
)


_장비창_왼쪽 = ["어깨", "상의", "하의", "벨트", "신발"]


_장비창_오른쪽 = [
    "무기",
    "칭호",
    "팔찌",
    "목걸이",
    "보조장비",
    "반지",
    "귀걸이",
    "마법석",
]


def _아이템_요약(아이템):
    """상세보기에 쓰는 전체 효과 - 항목마다 한 줄씩."""
    조각 = []
    if 아이템.get("무기공격력"):
        조각.append(f"무기 공격력 {아이템['무기공격력']}")
    if 아이템.get("재질"):
        조각.append(아이템["재질"])
    for 키, 표시 in (
        ("AC보너스", "AC"),
        ("명중률보너스", "명중"),
        ("데미지보너스", "데미지"),
        ("속도보너스", "속도"),
    ):
        값 = 아이템.get(키, 0)
        if isinstance(값, (int, float)) and 값:
            조각.append(f"{표시}{값:+d}")
    for 스탯, 값 in (아이템.get("스탯보너스") or {}).items():
        if 값:
            조각.append(f"{스탯}{값:+d}")
    if 아이템.get("설명"):  # 레어 무기의 고유 효과
        조각.append(아이템["설명"])
    return "\n".join(조각)


def _아이템_간단요약(아이템, 슬롯):
    """교체 팝업 칸에 쓰는 짧은 요약 - 무기는 공격력, 방어구(장비창 왼쪽
    5종)는 AC(0이어도 표시), 나머지 부위는 비운다. 전체는 [상세보기]."""
    if 슬롯 == "무기":
        return f"무기 공격력 {아이템.get('무기공격력') or 0}"
    if 슬롯 in _장비창_왼쪽:
        값 = 아이템.get("AC보너스", 0)
        return f"AC {값 if isinstance(값, (int, float)) else 0}"
    return ""


class _테두리상자(BoxLayout):
    """테두리를 그린 가로 상자 - 교체 팝업에서 장비 칸끼리 구분한다."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.45, 0.47, 0.52, 1)
            self._테두리 = Line(width=dp(1))
        self.bind(pos=self._다시그리기, size=self._다시그리기)

    def _다시그리기(self, *args):
        self._테두리.rectangle = (
            self.x + 1,
            self.y + 1,
            max(self.width - 2, 0),
            max(self.height - 2, 0),
        )


def _아이템_상세_팝업(아이템, 사유=None):
    효과 = _아이템_요약(아이템) or "(효과 없음)"
    글 = f"[b]{아이템_이름_글(아이템)}[/b]\n\n{escape_markup(효과)}"
    if 사유:
        글 += f"\n\n[color=e05555]{escape_markup(사유)}[/color]"
    세트 = gameflow.아이템_세트정보(App.get_running_app().게임상태, 아이템)
    if 세트:  # 세트 구성과 효과
        글 += (
            f"\n\n[b]{escape_markup(세트['세트명'])}[/b]\n"
            + "\n".join(escape_markup(n) for n in 세트["구성"])
            + f"\n세트 효과: {escape_markup(', '.join(세트['효과']))}"
            + f"\n[size=13sp]{escape_markup(세트['조건'])}[/size]"
        )
    부여 = gameflow.아이템_마법부여정보(아이템)
    if 부여:  # 마법부여 효과는 맨 아래에 따로
        글 += (
            f"\n\n[b]{escape_markup('[마법부여] ' + 부여['이름'])}[/b]\n"
            + escape_markup(부여["설명"])
        )
    본문 = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(10))
    스크롤 = ScrollView(size_hint=(1, 1))
    스크롤.add_widget(_줄바꿈_라벨(글, font_size="15sp"))
    본문.add_widget(스크롤)
    닫기 = Button(text="닫기", size_hint=(1, None), height=dp(48))
    뒤로키_버튼(닫기)
    본문.add_widget(닫기)
    팝업 = Popup(title="상세보기", content=본문, size_hint=(0.9, 0.5))
    닫기.bind(on_release=lambda *_: 팝업.dismiss())
    팝업.open()


def _장비_칸(아이템, 슬롯, 글머리="", 수량=None, 사유=None, 선택=None):
    """테두리 칸 하나: 왼쪽은 이름+간단요약(선택이 있으면 누르면 교체),
    오른쪽은 [상세보기]. 사유(착용 불가)가 있으면 칸을 누를 수 없다."""
    이름 = 아이템_이름_글(아이템) + (f" x{수량}" if 수량 is not None else "")
    요약 = _아이템_간단요약(아이템, 슬롯)
    # 높이는 글 줄 수만큼
    줄수 = 1 + bool(요약) + bool(사유)
    칸 = _테두리상자(
        orientation="horizontal",
        size_hint=(1, None),
        height=max(dp(52), dp(20) * 줄수 + dp(24)),
        padding=dp(6),
        spacing=dp(6),
    )
    글 = f"{글머리}[b]{이름}[/b]" + (f"\n{요약}" if 요약 else "")
    if 사유:
        글 += "\n[size=12sp][color=e05555]착용 불가[/color][/size]"
    공통 = dict(
        text=글,
        markup=True,
        font_size="15sp",
        halign="left",
        valign="middle",
        size_hint=(0.72, 1),
    )
    if 선택 is None:
        왼쪽 = Label(**공통)
    else:
        왼쪽 = Button(disabled=bool(사유), **공통)
        왼쪽.bind(on_release=lambda *_: 선택())
    왼쪽.bind(
        size=lambda inst, size: setattr(inst, "text_size", (size[0] - dp(12), size[1]))
    )
    칸.add_widget(왼쪽)
    상세 = Button(text="상세보기", font_size="14sp", size_hint=(0.28, 1))
    상세.bind(on_release=lambda *_: _아이템_상세_팝업(아이템, 사유))
    칸.add_widget(상세)
    return 칸


def _장비교체_팝업(캐릭터, 슬롯, 완료콜백):
    """소지품에 있는 그 부위 아이템 목록(착용 불가는 사유와 함께 비활성),
    [해제](무기 제외)/[취소]. 바꾸면 창을 닫고 완료콜백()을 부른다."""
    게임상태 = App.get_running_app().게임상태
    현재 = gameflow.캐릭터_장착아이템(게임상태, 캐릭터, 슬롯)
    탭목록 = gameflow.장비_교체_탭목록(게임상태, 캐릭터, 슬롯)

    본문 = BoxLayout(orientation="vertical", spacing=6, padding=10)
    if 현재:
        본문.add_widget(_장비_칸(현재, 슬롯, 글머리="[color=9ea6b3]현재[/color]  "))
    else:
        본문.add_widget(Label(text="현재: (없음)", size_hint=(1, None), height=dp(48)))
    # 분류 탭(무기 종류 / 방어구 재질) - 악세서리·특수장비는 탭 없음
    # 처음 탭은 방어구면 그 캐릭터의 숙련 재질
    처음탭 = gameflow.장비_교체_처음탭(게임상태, 캐릭터, 슬롯)
    if 탭목록:
        본문.add_widget(탭_줄(탭목록, lambda 탭: 목록_채우기(탭), 처음탭))
    안내 = Label(text="", size_hint=(1, 0.08))
    스크롤, 목록틀 = 스크롤_목록(0.64, 간격=dp(6))
    본문.add_widget(스크롤)
    본문.add_widget(안내)

    팝업 = Popup(
        title=f"{슬롯} 교체", content=본문, size_hint=(0.95, 0.85), auto_dismiss=False
    )

    def 완료():
        팝업.dismiss(animation=False)
        완료콜백()

    def 교체(이름):
        try:
            gameflow.장비_교체(게임상태, 캐릭터, 슬롯, 이름)
        except ValueError as 오류:
            안내.text = str(오류)
            return
        완료()

    def 해제(*_):
        try:
            gameflow.장비_해제(게임상태, 캐릭터, 슬롯)
        except ValueError as 오류:
            안내.text = str(오류)
            return
        완료()

    def 목록_채우기(탭):
        목록틀.clear_widgets()
        스크롤.scroll_y = 1
        후보 = gameflow.장비_교체_후보(게임상태, 캐릭터, 슬롯, 탭)
        if not 후보:
            목록틀.add_widget(
                Label(
                    text="(소지품에 바꿀 장비가 없습니다)",
                    size_hint=(1, None),
                    height=dp(40),
                )
            )
        for 아이템, 수량, 착용가능, 사유 in 후보:
            목록틀.add_widget(
                _장비_칸(
                    아이템,
                    슬롯,
                    수량=수량,
                    사유=None if 착용가능 else 사유,
                    선택=lambda n=아이템["이름"]: 교체(n),
                )
            )

    목록_채우기(처음탭)

    아래 = BoxLayout(orientation="horizontal", size_hint=(1, 0.12), spacing=6)
    해제버튼 = Button(text="해제", disabled=(현재 is None or 슬롯 == "무기"))
    해제버튼.bind(on_release=해제)
    아래.add_widget(해제버튼)
    취소버튼 = Button(text="취소")
    뒤로키_버튼(취소버튼)
    취소버튼.bind(on_release=lambda *_: 팝업.dismiss())
    아래.add_widget(취소버튼)
    본문.add_widget(아래)
    팝업.open()


class 파티원화면(Screen):
    _능력치_목록 = gameflow.능력치_목록

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.캐릭터 = None
        self.복귀화면 = "파티관리"
        self.탭 = "장비와 스탯"
        self.하위탭 = "스킬"

        루트 = BoxLayout(orientation="vertical", padding=12, spacing=8)

        # 최상단: 왼쪽 이름/직업, 오른쪽 탭 버튼 두 개
        머리 = BoxLayout(orientation="horizontal", size_hint=(1, 0.07), spacing=6)
        self.이름라벨 = Label(
            text="", halign="left", valign="middle", size_hint=(0.44, 1)
        )
        self.이름라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        머리.add_widget(self.이름라벨)
        self.탭버튼 = {}
        for 이름 in ("장비와 스탯", "스킬과 특성"):
            버튼 = ToggleButton(
                text=이름,
                group="파티원탭",
                size_hint=(0.28, 1),
                allow_no_selection=False,
            )
            버튼.bind(on_release=lambda inst, n=이름: self._탭_선택(n))
            self.탭버튼[이름] = 버튼
            머리.add_widget(버튼)
        루트.add_widget(머리)

        self.본문 = BoxLayout(orientation="vertical", size_hint=(1, 0.85), spacing=8)
        루트.add_widget(self.본문)

        뒤로버튼 = Button(text="뒤로", size_hint=(1, 0.08))
        뒤로키_버튼(뒤로버튼)
        뒤로버튼.bind(on_release=self._뒤로_클릭)
        루트.add_widget(뒤로버튼)
        self.add_widget(루트)

    def on_pre_enter(self, *args):
        self.갱신()

    def _뒤로_클릭(self, *args):
        self.manager.current = self.복귀화면

    def _탭_선택(self, 이름):
        self.탭 = 이름
        self.갱신()

    def _하위탭_선택(self, 이름):
        self.하위탭 = 이름
        self.갱신()

    def 갱신(self):
        게임상태 = App.get_running_app().게임상태
        if 게임상태 is None or self.캐릭터 is None:
            return
        캐릭터 = self.캐릭터
        self.이름라벨.text = (
            f"{캐릭터['캐릭터명']}  {gameflow.캐릭터_직업표시(캐릭터)}"
            + ("" if 캐릭터["현재HP"] > 0 else " (쓰러짐)")
        )
        for 이름, 버튼 in self.탭버튼.items():
            버튼.state = "down" if 이름 == self.탭 else "normal"

        self.본문.clear_widgets()
        if self.탭 == "장비와 스탯":
            self.본문.add_widget(self._장비창(게임상태, 캐릭터))
            self.본문.add_widget(self._스탯창(게임상태, 캐릭터))
        else:
            self._스킬특성_탭(게임상태, 캐릭터)

    # -------------------------------------------------
    # 장비와 스탯 탭
    # -------------------------------------------------

    def _슬롯_버튼(self, 게임상태, 캐릭터, 슬롯):
        if 슬롯 == "칭호":
            칭호 = 캐릭터.get("칭호")
            return Button(
                text=f"칭호\n{칭호 or '(미구현)'}",
                disabled=True,
                font_size="12sp",
                halign="center",
                valign="middle",
            )
        아이템 = gameflow.캐릭터_장착아이템(게임상태, 캐릭터, 슬롯)
        버튼 = Button(
            text=f"[b]{슬롯}[/b]\n{아이템_이름_글(아이템) if 아이템 else '-'}",
            markup=True,
            font_size="12sp",
            halign="center",
            valign="middle",
        )
        버튼.bind(
            size=lambda inst, size: setattr(
                inst, "text_size", (size[0] - 8, size[1] - 4)
            )
        )
        버튼.bind(
            on_release=lambda inst, 슬=슬롯: _장비교체_팝업(캐릭터, 슬, self.갱신)
        )
        return 버튼

    def _장비창(self, 게임상태, 캐릭터):
        창 = BoxLayout(orientation="horizontal", size_hint=(1, 0.58), spacing=6)

        왼쪽 = BoxLayout(orientation="vertical", size_hint=(0.26, 1), spacing=4)
        for 슬롯 in _장비창_왼쪽:
            왼쪽.add_widget(self._슬롯_버튼(게임상태, 캐릭터, 슬롯))
        창.add_widget(왼쪽)

        가운데 = BoxLayout(orientation="vertical", size_hint=(0.3, 1))
        가운데.add_widget(
            Image(
                allow_stretch=True,
                source=_캐릭터이미지_경로(gameflow.초상화_코드(캐릭터)),
            )
        )
        창.add_widget(가운데)

        오른쪽 = GridLayout(cols=2, size_hint=(0.44, 1), spacing=4)
        for 슬롯 in _장비창_오른쪽:
            오른쪽.add_widget(self._슬롯_버튼(게임상태, 캐릭터, 슬롯))
        창.add_widget(오른쪽)
        return 창

    def _스탯창(self, 게임상태, 캐릭터):
        창 = BoxLayout(
            orientation="vertical", size_hint=(1, 0.42), spacing=6, padding=(0, 8, 0, 0)
        )
        창.add_widget(
            Label(
                text=(
                    f"Lv.{캐릭터['레벨']}    "
                    f"HP {캐릭터['현재HP']}/{gameflow.캐릭터_최대HP(게임상태, 캐릭터)}    "
                    f"MP {캐릭터['현재MP']}/{gameflow.캐릭터_최대MP(게임상태, 캐릭터)}"
                    + (
                        f"    [{gameflow.음주_표시(캐릭터.get('상태이상'))}]"
                        if gameflow.음주_표시(캐릭터.get("상태이상"))
                        else ""
                    )
                ),
                size_hint=(1, 0.22),
            )
        )
        유효 = gameflow.캐릭터_유효능력치(게임상태, 캐릭터)
        능력치판 = GridLayout(cols=3, size_hint=(1, 0.5), spacing=4)
        for 이름 in self._능력치_목록:
            차이 = 유효[이름] - 캐릭터[이름]
            능력치판.add_widget(
                Label(text=f"{이름} {유효[이름]}" + (f"({차이:+d})" if 차이 else ""))
            )
        창.add_widget(능력치판)
        버튼줄 = BoxLayout(orientation="horizontal", size_hint=(1, 0.26), spacing=6)
        상세버튼 = Button(text="상세보기")
        상세버튼.bind(on_release=lambda *_: self._상세정보_팝업(게임상태, 캐릭터))
        버튼줄.add_widget(상세버튼)
        포션버튼 = Button(text="포션/주류")
        포션버튼.bind(on_release=lambda *_: self._포션_팝업(게임상태, 캐릭터))
        버튼줄.add_widget(포션버튼)
        창.add_widget(버튼줄)
        return 창

    def _포션_팝업(self, 게임상태, 캐릭터):
        """소지품의 회복포션과 주류 목록 - 누르면 이 캐릭터에게 1개 쓰고 결과를 보여준다.
        팝업은 열어 둔 채 목록을 다시 그린다(여러 개 연달아 마실 수 있게)."""
        본문 = BoxLayout(orientation="vertical", spacing=6, padding=10)
        안내 = Label(text="", size_hint=(1, 0.12))
        스크롤, 목록틀 = 스크롤_목록(0.76)

        def 다시그리기():
            목록틀.clear_widgets()
            목록 = [
                ("포션", *항목)
                for 항목 in gameflow.캐릭터_회복포션_목록(게임상태, 캐릭터)
            ] + [
                ("주류", *항목) for 항목 in gameflow.캐릭터_주류_목록(게임상태, 캐릭터)
            ]
            if not 목록:
                목록틀.add_widget(
                    Label(
                        text="(회복포션/주류가 없습니다)",
                        size_hint_y=None,
                        height=dp(48),
                    )
                )
            for 종류, 이름, 개수, 사유 in 목록:
                버튼 = Button(
                    text=f"{이름} x{개수}" + (f"\n({사유})" if 사유 else ""),
                    size_hint_y=None,
                    height=dp(56),
                    disabled=사유 is not None,
                    halign="center",
                )
                버튼.bind(on_release=lambda inst, k=종류, n=이름: 마시기(k, n))
                목록틀.add_widget(버튼)

        def 마시기(종류, 이름):
            try:
                if 종류 == "주류":
                    회복, 결과 = gameflow.캐릭터_주류사용(게임상태, 캐릭터, 이름)
                    안내.text = f"{이름}: {gameflow.주류_결과_문구(회복, 결과)}"
                else:
                    대상, 회복 = gameflow.캐릭터_포션사용(게임상태, 캐릭터, 이름)
                    안내.text = f"{이름}: {대상} {회복} 회복"
            except ValueError as 오류:
                안내.text = str(오류)
                return
            다시그리기()
            self.갱신()

        다시그리기()
        본문.add_widget(안내)
        본문.add_widget(스크롤)
        팝업 = Popup(
            title=f"{캐릭터['캐릭터명']} 포션/주류 사용",
            content=본문,
            size_hint=(0.9, 0.75),
            auto_dismiss=False,
        )
        닫기 = 닫기_버튼(팝업, size_hint=(1, 0.12))
        본문.add_widget(닫기)
        팝업.open()

    def _상세정보_팝업(self, 게임상태, 캐릭터):
        본문 = BoxLayout(orientation="vertical", spacing=6, padding=10)
        목록틀 = BoxLayout(orientation="vertical", size_hint_y=None, spacing=2)
        목록틀.bind(minimum_height=목록틀.setter("height"))
        for 제목, 줄목록 in gameflow.캐릭터_상세정보(게임상태, 캐릭터):
            목록틀.add_widget(_줄바꿈_라벨(f"[b]{escape_markup(제목)}[/b]"))
            목록틀.add_widget(
                _줄바꿈_라벨("\n".join(escape_markup(줄) for 줄 in 줄목록))
            )
        스크롤 = ScrollView(size_hint=(1, 0.88))
        스크롤.add_widget(목록틀)
        본문.add_widget(스크롤)
        팝업 = Popup(
            title=f"{캐릭터['캐릭터명']} 상세 정보",
            content=본문,
            size_hint=(0.95, 0.9),
            auto_dismiss=False,
        )
        닫기 = 닫기_버튼(팝업, size_hint=(1, 0.12))
        본문.add_widget(닫기)
        팝업.open()

    # -------------------------------------------------
    # 스킬과 특성 탭
    # -------------------------------------------------

    def _스킬특성_탭(self, 게임상태, 캐릭터):
        하위머리 = BoxLayout(orientation="horizontal", size_hint=(1, 0.09), spacing=6)
        for 이름 in ("스킬", "특성", "퍽"):
            버튼 = ToggleButton(
                text=이름,
                group="파티원하위탭",
                allow_no_selection=False,
                state="down" if 이름 == self.하위탭 else "normal",
            )
            버튼.bind(on_release=lambda inst, n=이름: self._하위탭_선택(n))
            하위머리.add_widget(버튼)
        self.본문.add_widget(하위머리)

        목록틀 = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=6, padding=(4, 4)
        )
        목록틀.bind(minimum_height=목록틀.setter("height"))
        if self.하위탭 == "스킬":
            항목들 = [
                (이름, 요약, 설명)
                for 이름, 요약, 설명 in gameflow.캐릭터_스킬목록(게임상태, 캐릭터)
            ]
        elif self.하위탭 == "특성":
            항목들 = [
                (이름, "", 설명) for 이름, 설명 in gameflow.캐릭터_특성목록(캐릭터)
            ]
        else:
            항목들 = [(이름, "", 설명) for 이름, 설명 in gameflow.캐릭터_퍽목록(캐릭터)]
        if not 항목들:
            목록틀.add_widget(_줄바꿈_라벨(f"(보유한 {self.하위탭}이(가) 없습니다)"))
        for 이름, 요약, 설명 in 항목들:
            머리글 = f"[b]{escape_markup(이름)}[/b]"
            if 요약:
                머리글 += f"   [size=13sp]{escape_markup(요약)}[/size]"
            # 항목마다 테두리 상자 - 줄글이 이어져 어디서 끝나는지 읽기 어려웠다
            라벨 = _줄바꿈_라벨(머리글 + (f"\n{escape_markup(설명)}" if 설명 else ""))
            상자 = _테두리상자(
                orientation="vertical", size_hint=(1, None), padding=dp(6)
            )
            상자.항목상자 = True  # 화면 스모크가 찾는다
            라벨.bind(height=lambda inst, h, b=상자: setattr(b, "height", h + dp(12)))
            상자.add_widget(라벨)
            목록틀.add_widget(상자)
        스크롤 = ScrollView(size_hint=(1, 0.91))
        스크롤.add_widget(목록틀)
        self.본문.add_widget(스크롤)
