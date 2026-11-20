"""전투 화면의 팝업 - 전투 보상, 스킬 선택(스킬 줄), 대상 선택, 효과 목록, 행동 선택.

전투 화면(screens_battle.py)에서 갈라져 나왔다. 팝업은 전투 화면을 모른다(전투 화면이 이 모듈을 부른다)."""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.metrics import dp
import gameflow
from game.screens.screens_common import (
    _테두리박스,
    뒤로키_버튼,
    아이템_이름_글_찾아서,
    가로맞춤_라벨,
    글자_높이,
)


# 상태/그래픽/배경 박스 테두리 색 - 전부 흰색 테두리로 통일한다.
_박스_테두리색 = (1, 1, 1, 1)


class _전투보상팝업(Popup):
    """전투 보상 - 큰 테두리 박스 안에 왼쪽/중앙/오른쪽 세 박스(아이템 이름,
    빈칸은 비워 둔다). 박스를 누르고 [선택]으로 받는다. 중앙 박스 아래
    [포기하기(10골드)]는 고르지 않는 대신 골드를 받는다. 닫기 버튼은 없다.
    받거나 포기하면 완료()를 부른다."""

    def __init__(self, 칸목록, 완료, **kwargs):
        self._완료 = 완료
        self._고른칸 = None
        self._박스들 = []

        # 칸은 세 줄(이름 / 부위 / 보유·착용) 높이, 팝업도 그 높이에 맞춘다
        칸높이 = 글자_높이("15sp", 0) + 2 * 글자_높이("13sp", 0) + dp(16)
        버튼높이 = dp(48)
        큰박스높이 = 칸높이 + 버튼높이 + dp(8) + 2 * dp(10)
        본문높이 = 큰박스높이 + 버튼높이 + dp(8) + 2 * dp(8)

        본문 = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(8))
        큰박스 = _테두리박스(
            _박스_테두리색,
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8),
            size_hint_y=None,
            height=큰박스높이,
        )
        박스줄 = BoxLayout(
            orientation="horizontal", spacing=dp(8), size_hint_y=None, height=칸높이
        )
        게임상태 = App.get_running_app().게임상태
        for 번호, 이름 in enumerate(칸목록):
            박스 = _테두리박스(_박스_테두리색, 기본두께=1.2, padding=dp(4))
            if 이름:
                # 이름(15sp, 길면 가로로 눌러 한 줄에) / 부위 / 보유·착용(13sp 회색). 보유·착용이
                # 없으면 그 줄을 빼고, 남은 줄 묶음을 칸 가운데에 둔다(위아래 빈 칸으로).
                줄들 = [(아이템_이름_글_찾아서(게임상태, 이름), "15sp", None)]
                for 줄 in (
                    gameflow.전투_보상_부위(게임상태, 이름),
                    gameflow.전투_보상_보유표시(게임상태, 이름),
                ):
                    if 줄:
                        줄들.append((줄, "13sp", (0.62, 0.65, 0.7, 1)))
                묶음 = BoxLayout(
                    orientation="vertical",
                    size_hint_y=None,
                    height=sum(글자_높이(크기, 0) for _, 크기, _ in 줄들),
                )
                for 글, 크기, 색 in 줄들:
                    라벨 = 가로맞춤_라벨(
                        text=글,
                        markup=True,
                        font_size=크기,
                        size_hint_y=None,
                        height=글자_높이(크기, 0),
                    )
                    if 색:
                        라벨.color = 색
                    묶음.add_widget(라벨)
                박스.add_widget(Widget())
                박스.add_widget(묶음)
                박스.add_widget(Widget())
                박스.bind(on_release=lambda _b, n=번호: self._칸_선택(n))
            else:
                박스.disabled = True
            박스줄.add_widget(박스)
            self._박스들.append(박스)
        큰박스.add_widget(박스줄)

        포기줄 = BoxLayout(
            orientation="horizontal", spacing=dp(8), size_hint_y=None, height=버튼높이
        )
        포기줄.add_widget(Widget(size_hint_x=0.5))
        포기버튼 = Button(
            text=f"포기하기({gameflow.보상_포기_골드}골드)", size_hint_x=4
        )  # 좌우로 넓게
        포기버튼.bind(on_release=lambda *_: self._포기())
        포기줄.add_widget(포기버튼)
        포기줄.add_widget(Widget(size_hint_x=0.5))
        큰박스.add_widget(포기줄)
        본문.add_widget(큰박스)

        self._선택버튼 = Button(
            text="선택", size_hint_y=None, height=버튼높이, disabled=True
        )
        self._선택버튼.bind(on_release=lambda *_: self._받기())
        본문.add_widget(self._선택버튼)

        kwargs.setdefault("size_hint", (0.9, None))
        kwargs.setdefault("height", 본문높이 + dp(64))  # 제목줄 포함
        kwargs.setdefault("title", "전투 보상")
        kwargs.setdefault("auto_dismiss", False)
        super().__init__(content=본문, **kwargs)

    def _칸_선택(self, 번호):
        self._고른칸 = 번호
        for n, 박스 in enumerate(self._박스들):
            박스.현재턴_표시(n == 번호)
        self._선택버튼.disabled = False

    def _받기(self):
        if self._고른칸 is None:
            return
        gameflow.전투_보상_받기(App.get_running_app().게임상태, self._고른칸)
        self.dismiss()
        self._완료()

    def _포기(self):
        gameflow.전투_보상_포기(App.get_running_app().게임상태)
        self.dismiss()
        self._완료()


# 스킬 줄의 칸 너비 비율 - 이름(왼쪽 정렬) | 남은 횟수 | MP | 행동
# 이름만 넘치면 "..."로 줄이고, 나머지 세 칸은 잘리지 않을 만큼 둔다("[일반][보조]", "MP 20", "5/5").
# 이름 칸을 넓히려고 나머지 세 칸은 글을 조금 작게 쓴다(_스킬줄_작은글).
_스킬줄_칸 = ((0.43, "left"), (0.12, "center"), (0.17, "center"), (0.28, "right"))


_스킬줄_작은글 = "13sp"


def _스킬_줄(이름, 줄, 가능):
    """버튼 위에 글 칸 4개를 겹친 한 줄. (줄 위젯, 누를 버튼). 글 칸은 터치를 받지 않아
    버튼이 받는다. 못 쓰면 버튼과 글 칸 모두 비활성(회색)."""
    틀 = FloatLayout(size_hint_y=None, height=dp(56))
    버튼 = Button(pos_hint={"x": 0, "y": 0}, disabled=not 가능)
    버튼.스킬이름 = 이름
    틀.add_widget(버튼)
    칸들 = BoxLayout(pos_hint={"x": 0, "y": 0}, padding=(dp(10), 0), spacing=dp(2))
    글들 = (
        줄.get("이름", 이름),
        줄["남은"],
        줄["MP"],
        줄["행동"],
    )  # 이름: 합격 : 월령참
    for 번호, (글, (비율, 정렬)) in enumerate(zip(글들, _스킬줄_칸)):
        칸 = Label(
            text=글,
            size_hint_x=비율,
            halign=정렬,
            valign="middle",
            shorten=번호 == 0,  # 이름만 넘치면 "..."
            **({} if 번호 == 0 else {"font_size": _스킬줄_작은글}),
            shorten_from="right",
            disabled=not 가능,
        )
        칸.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        칸들.add_widget(칸)
    틀.add_widget(칸들)
    return 틀, 버튼


class _스킬선택팝업(Popup):
    """ "스킬" 버튼을 누르면 뜨는 목록 팝업(액션 버튼 5칸 고정 레이아웃이라
    화면에 스킬 목록을 펼칠 자리가 없다)."""

    def __init__(self, 항목목록, 선택콜백, 제목="스킬 선택", **kwargs):
        super().__init__(title=제목, size_hint=(0.85, 0.75), **kwargs)
        self.선택콜백 = 선택콜백

        스크롤 = ScrollView()
        목록틀 = BoxLayout(
            orientation="vertical", spacing=6, padding=6, size_hint_y=None
        )
        목록틀.bind(minimum_height=목록틀.setter("height"))

        for 이름, 스킬데이터, 가능, *나머지 in 항목목록:
            표시 = 나머지[0] if 나머지 else 이름
            if isinstance(표시, dict):  # 스킬 줄: 이름 | 남은 횟수 | MP | 행동
                줄틀, 버튼 = _스킬_줄(이름, 표시, 가능)
            else:
                줄틀 = 버튼 = Button(
                    text=표시, size_hint_y=None, height=dp(56), disabled=not 가능
                )
            버튼.bind(on_release=lambda inst, n=이름, d=스킬데이터: self._선택(n, d))
            목록틀.add_widget(줄틀)

        스크롤.add_widget(목록틀)
        self.content = 스크롤

    def _선택(self, 이름, 스킬데이터):
        self.선택콜백(이름, 스킬데이터)
        self.dismiss()


class _대상선택팝업(Popup):
    """일반공격/적 대상 스킬의 대상 고르기 - 살아 있는 적(과 감옥) 이름 목록과 맨 아래
    [취소]. 적을 누르면 닫고 선택콜백(적참가자), [취소](뒤로 키)는 닫고 취소콜백()."""

    def __init__(self, 제목, 적목록, 선택콜백, 취소콜백, **kwargs):
        self._선택콜백 = 선택콜백
        self._취소콜백 = 취소콜백

        게임상태 = App.get_running_app().게임상태
        목록 = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
        for 적 in 적목록:
            버튼 = Button(
                text=f"{gameflow.적_이름표(적)}\n{gameflow.적_HP표시(게임상태, 적)}",
                halign="center",
            )
            버튼.bind(on_release=lambda inst, p=적: self._선택(p))
            목록.add_widget(버튼)
        취소버튼 = Button(
            text="취소", background_normal="", background_color=(0.3, 0.31, 0.35, 1)
        )
        뒤로키_버튼(취소버튼)
        취소버튼.bind(on_release=lambda *_: self._취소())
        목록.add_widget(취소버튼)

        kwargs.setdefault("title", 제목)
        kwargs.setdefault("size_hint", (0.7, None))  # 이름이 넘치지 않게
        kwargs.setdefault("height", dp(110 + 64 * (len(적목록) + 1)))
        kwargs.setdefault("auto_dismiss", False)
        super().__init__(content=목록, **kwargs)

    def _선택(self, 적참가자):
        self.dismiss(animation=False)
        self._선택콜백(적참가자)

    def _취소(self):
        self.dismiss(animation=False)
        self._취소콜백()


class _효과목록팝업(Popup):
    """칸을 누르면 뜨는 적용 중인 효과 목록 - gameflow.상태_목록의 묶음마다 [묶음] 제목과 한 줄에
    하나씩, 없으면 "적용 중인 효과 없음". 길면 스크롤, 맨 아래 [닫기](뒤로 키)."""

    def __init__(self, 제목, 묶음들, **kwargs):
        줄들 = []
        for 묶음, 글들 in 묶음들:
            줄들.append(f"[b][{묶음}][/b]")
            줄들 += 글들
        self.글 = (
            "\n".join(줄들) if 줄들 else "적용 중인 효과 없음"
        )  # 화면 스모크가 확인한다

        틀 = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
        스크롤 = ScrollView()
        라벨 = Label(
            text=self.글,
            markup=True,
            size_hint_y=None,
            halign="left",
            valign="top",
            font_size="15sp",
        )
        라벨.bind(
            width=lambda 글칸, w: setattr(글칸, "text_size", (w, None)),
            texture_size=lambda 글칸, s: setattr(글칸, "height", s[1]),
        )
        스크롤.add_widget(라벨)
        틀.add_widget(스크롤)
        닫기 = Button(
            text="닫기",
            size_hint_y=None,
            height=dp(48),
            background_normal="",
            background_color=(0.3, 0.31, 0.35, 1),
        )
        뒤로키_버튼(닫기)
        닫기.bind(on_release=lambda *_: self.dismiss(animation=False))
        틀.add_widget(닫기)

        줄수 = max(1, len(줄들))
        kwargs.setdefault("title", 제목)
        kwargs.setdefault("size_hint", (0.8, None))
        kwargs.setdefault("height", dp(min(560, 150 + 24 * 줄수)))
        super().__init__(content=틀, **kwargs)


class _행동선택팝업(Popup):
    """스킬의 일반행동을 낼 수단이 여러 개일 때(쇼타임행동/일반행동/보조행동) 고르는
    팝업 - 수단마다 버튼(남은 개수 표시)과 맨 아래 [취소]."""

    def __init__(self, 제목, 선택지, 선택콜백, 취소콜백, **kwargs):
        self._선택콜백 = 선택콜백
        self._취소콜백 = 취소콜백

        목록 = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(6))
        for 수단, 표시 in 선택지:
            버튼 = Button(text=표시)
            버튼.bind(on_release=lambda inst, s=수단: self._선택(s))
            목록.add_widget(버튼)
        취소버튼 = Button(
            text="취소", background_normal="", background_color=(0.3, 0.31, 0.35, 1)
        )
        뒤로키_버튼(취소버튼)
        취소버튼.bind(on_release=lambda *_: self._취소())
        목록.add_widget(취소버튼)

        kwargs.setdefault("title", 제목)
        kwargs.setdefault("size_hint", (0.5, None))
        kwargs.setdefault("height", dp(110 + 54 * (len(선택지) + 1)))
        kwargs.setdefault("auto_dismiss", False)
        super().__init__(content=목록, **kwargs)

    def _선택(self, 수단):
        self.dismiss(animation=False)
        self._선택콜백(수단)

    def _취소(self):
        self.dismiss(animation=False)
        self._취소콜백()
