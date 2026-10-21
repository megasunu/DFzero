# =====================
# 공용 부품 - 초상화 경로/초상화 선택 팝업, 버튼·입력칸 크기, 기기 설정 파일,
# 카드 디자인 색상과 둥근상자·게이지·평면버튼
# =====================
# main.py가 game/screens/ 여섯 파일의 화면을 ScreenManager에 등록한다.

import os

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.modalview import ModalView
from kivy.uix.dropdown import DropDown
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.scatterlayout import ScatterLayout
from kivy.metrics import dp, sp
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.utils import escape_markup

import gameflow


# =====================================================
# 초상화 시스템 - 서로 완전히 별개인 두 가지
# =====================================================
# 1) "플레이어 초상화" - 던전 지도(던전화면.지도위젯)에 "내 위치"로
#    표시할 이미지. 직업과 무관하게 마을 [모험단] 화면에서 65장 그리드
#    (아래 _초상화_행목록/_초상화선택팝업)에서 직접 골라서 정하고,
#    게임상태 최상위 "선택된초상화" 키 하나에 저장된다(gameflow.
#    초상화_설정/게임상태["선택된초상화"] 참고). 파티원이 여러 명이어도
#    공용 값 하나뿐이다.
# 2) "캐릭터 초상화" - 모험단화면의 파티원 목록, 전투화면의 아군 그래픽
#    박스에 쓰는, 캐릭터 개인별 초상화. 직업으로 앞자리가 자동 정해지고
#    (gameflow.초상화_코드 참고) 성별만 캐릭터별로 토글한다 - 65장
#    그리드에서 고르지 않는다.
#
# 둘 다 파일명 규칙(asset_sd_character_{코드}.webp)과 아래
# _캐릭터이미지_경로()를 함께 쓴다.
_초상화_접두사 = "asset_sd_character_"

# "플레이어 초상화" 그리드용 - 실제 파일 목록(game/assets/character/
# 전체 65장) 그대로 파일명 순서대로
# 5칸씩 끊은 것뿐이다. 직업과는 아무 관계가 없다(그래서 63장이 아니라
# 65장이 정확히 13행으로 나눠떨어져 빈 칸이 없다).
_초상화_행목록 = [
    ("001f", "001m", "011f", "011m", "012f"),
    ("012m", "013f", "013m", "014f", "014m"),
    ("015f", "015m", "021f", "021m", "022f"),
    ("022m", "023f", "023m", "024f", "024m"),
    ("031f", "031m", "032f", "032m", "033f"),
    ("033m", "034f", "034m", "035m", "041f"),
    ("041m", "042f", "042m", "043f", "043m"),
    ("044f", "044m", "045f", "045m", "051f"),
    ("051m", "052f", "052m", "053f", "053m"),
    ("054f", "054m", "061f", "062f", "063f"),
    ("064f", "071m", "072m", "073m", "074m"),
    ("081f", "082f", "083f", "084f", "091m"),
    ("092m", "093m", "094m", "101f", "102f"),
]

_기본_초상화_코드 = "001m"


def _이미지_원경로(코드):
    파일명 = f"{_초상화_접두사}{코드}.webp"
    # 이 파일은 game/screens/ 안에 있으므로 한 단계 위(game/)의 assets를 쓴다.
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "assets",
        "character",
        파일명,
    )


def _이미지_존재(코드):
    return os.path.isfile(_이미지_원경로(코드))


def _캐릭터이미지_경로(코드):
    """코드(예: "020f")에 대응하는 SD 캐릭터 이미지의 전체 경로를
    돌려준다. 그 코드의 실제 파일이 아직 없으면(예: 직업 기반 비전직
    코드는 "분류번호"만 정해져 있고 원화가 없는 경우가 있음) 같은
    계열(앞 2자리)·같은 성별로 실제 존재하는 파일 중 가장 앞 순번으로
    대신 보여주고, 그마저 없으면 공용 기본 초상화(001)로 대체한다."""
    if _이미지_존재(코드):
        return _이미지_원경로(코드)
    계열, 성별 = 코드[:2], 코드[-1]
    for 순번 in "123456789":
        대체코드 = f"{계열}{순번}{성별}"
        if _이미지_존재(대체코드):
            return _이미지_원경로(대체코드)
    return _이미지_원경로(f"{_기본_초상화_코드[:-1]}{성별}")


def _에셋_경로(폴더, 파일명):
    """game/assets/{폴더}/{파일명}의 전체 경로를 돌려준다. 파일명이 없거나
    "미정"이거나 실제 파일이 없으면 None. 던전 타일(dungeon), 몬스터
    이미지(monster), 마을 배경(town)에 쓴다."""
    if not 파일명 or 파일명 == "미정":
        return None
    경로 = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "assets",
        폴더,
        파일명,
    )
    return 경로 if os.path.isfile(경로) else None


def _도트_필터(이미지위젯):
    """도트 이미지를 크게 늘려도 번지지 않게 텍스처 확대 필터를
    nearest로 둔다(텍스처가 나중에 로드돼도 적용되게 bind까지 건다)."""

    def 적용(inst, 텍스처):
        if 텍스처 is not None:
            텍스처.mag_filter = "nearest"

    이미지위젯.bind(texture=적용)
    적용(이미지위젯, 이미지위젯.texture)


class _이미지버튼(ButtonBehavior, Image):
    """터치 가능한 이미지 - "플레이어 초상화" 그리드 팝업 썸네일,
    모험단 프로필의 캐릭터별 성별 토글, 전투화면 그래픽 박스에 쓴다."""

    pass


class _초상화선택팝업(Popup):
    """ "플레이어 초상화"(던전 지도 표시용, 직업과 무관)를 65장 그리드
    에서 고르는 팝업."""

    def __init__(self, 현재선택, 선택콜백, **kwargs):
        super().__init__(title="플레이어 초상화 선택", size_hint=(0.95, 0.9), **kwargs)
        self._선택콜백 = 선택콜백

        스크롤 = ScrollView()
        격자 = GridLayout(cols=5, size_hint_y=None, spacing=4, padding=4)
        격자.bind(minimum_height=격자.setter("height"))

        for 행 in _초상화_행목록:
            for 코드 in 행:
                if 코드 is None:
                    격자.add_widget(Widget(size_hint_y=None, height=dp(90)))
                    continue
                버튼 = _이미지버튼(
                    source=_캐릭터이미지_경로(코드),
                    size_hint_y=None,
                    height=dp(90),
                    allow_stretch=True,
                )
                버튼.bind(on_release=lambda inst, c=코드: self._선택(c))
                격자.add_widget(버튼)

        스크롤.add_widget(격자)
        self.content = 스크롤

    def _선택(self, 코드):
        self._선택콜백(코드)
        self.dismiss()


# =====================================================
# 메인메뉴/파티생성 화면에서 쓰는 버튼·입력칸 크기를 여기 상수로 모아둔다.
# (사용자 요청 - 상자는 세로로 작게, 글자는 상자에 맞게 크게, 두 화면의
# 버튼/입력칸이 서로 다른 크기로 따로 놀지 않게 하나로 통일) 값만 바꾸면
# 아래에서 이 상수를 쓰는 모든 버튼/입력칸에 그대로 반영된다.
_버튼_높이 = dp(56)
_버튼_폰트크기 = "26sp"
_입력_높이 = dp(52)
_입력_폰트크기 = 36

# -----------------------------------------------------
# 기기 설정 파일 - 세이브와 별개인 앱 설정(반응 자동/자동전투/전투로그 방식).
# 앱 데이터 폴더의 설정.json. 화면은 경로만 정하고 읽기/쓰기는 gameflow 창구
# (ctl_battle -> settings_system)가 한다.
# -----------------------------------------------------


def _설정_경로():
    앱 = App.get_running_app()
    폴더 = getattr(앱, "user_data_dir", None) or os.path.dirname(
        os.path.abspath(__file__)
    )
    return os.path.join(폴더, "설정.json")


def 설정_불러오기():
    return gameflow.설정_파일_불러오기(_설정_경로())


def 설정_저장(키, 값):
    gameflow.설정_파일_저장(
        _설정_경로(), 키, 값
    )  # 못 써도 이번 실행에는 이미 반영돼 있다


# 파티 화면 디자인: 파티원마다 넓은 카드 한 장 - 왼쪽 초상화,
# 가운데 이름·직업·레벨 / HP·MP 게이지 / 능력치 3×2, 오른쪽 [레벨업][상세보기].
_카드_배경색 = (0.13, 0.14, 0.17, 1)
_카드_쓰러짐색 = (0.18, 0.11, 0.11, 1)
_강조색 = (0.22, 0.56, 0.86, 1)
_흐린글자색 = (0.62, 0.65, 0.7, 1)
_HP색 = (0.85, 0.27, 0.27, 1)
_MP색 = (0.27, 0.5, 0.9, 1)
_게이지_바탕색 = (0.24, 0.25, 0.29, 1)


class _둥근상자(BoxLayout):
    """둥근 모서리 배경을 칠한 BoxLayout."""

    def __init__(self, 배경색, 반지름=12, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._색 = Color(*배경색)
            self._배경 = RoundedRectangle(radius=[dp(반지름)])
        self.bind(pos=self._다시그리기, size=self._다시그리기)

    def _다시그리기(self, *args):
        self._배경.pos = self.pos
        self._배경.size = self.size


class _게이지(Widget):
    """HP/MP 막대 - 바탕 막대 위에 현재/최대 비율만큼 색을 채우고 글자를 얹는다."""

    def __init__(self, 이름, 현재, 최대, 색, **kwargs):
        super().__init__(**kwargs)
        self._비율 = max(0.0, min(1.0, 현재 / 최대)) if 최대 else 0.0
        with self.canvas.before:
            Color(*_게이지_바탕색)
            self._바탕 = RoundedRectangle(radius=[dp(4)])
            Color(*색)
            self._채움 = RoundedRectangle(radius=[dp(4)])
        self._글 = Label(text=f"{이름}  {현재} / {최대}", font_size="12sp", bold=True)
        self.add_widget(self._글)
        self.bind(pos=self._다시그리기, size=self._다시그리기)

    def _다시그리기(self, *args):
        self._바탕.pos = self.pos
        self._바탕.size = self.size
        self._채움.pos = self.pos
        self._채움.size = (self.width * self._비율, self.height)
        self._글.pos = self.pos
        self._글.size = self.size


def _평면버튼(글, 색, **kwargs):
    """기본 회색 입체 배경 대신 단색 배경 버튼."""
    return Button(
        text=글,
        background_normal="",
        background_disabled_normal="",
        background_color=색,
        **kwargs,
    )


# =====================================================
# 핸드폰 [뒤로] 키
# =====================================================
# 안드로이드 [뒤로] 키는 Kivy에 키코드 27로 들어오고, 그대로 두면 앱이
# 최소화된다. 대신 화면/팝업의 취소·닫기·뒤로 버튼을 누른 것과 같게
# 동작시키고, 그런 버튼이 없는 곳(메인메뉴, 마을, 던전, 전투, 꼭 골라야
# 하는 팝업)에서는 아무 일도 하지 않는다. 대상 버튼은 만들 때
# 뒤로키_버튼()으로 표시해 둔다. main.py가 창의 on_keyboard에 연결한다.


def 뒤로키_버튼(버튼):
    """[뒤로] 키를 누르면 이 버튼을 누른 것과 같게 동작하도록 표시한다."""
    버튼.뒤로키 = True
    return 버튼


def 닫기_버튼(팝업, **kwargs):
    """누르면(또는 [뒤로] 키) 팝업을 닫는 [닫기] 버튼. kwargs는 Button에 그대로 넘긴다."""
    버튼 = 뒤로키_버튼(Button(text="닫기", **kwargs))
    버튼.bind(on_release=lambda *_: 팝업.dismiss())
    return 버튼


def 확인_팝업(제목, 문구, 확인):
    """[예]/[아니요] 확인 창 - [예]를 누르면 닫고 확인()을 부른다. [아니요]와 [뒤로] 키는 그냥 닫는다."""
    본문 = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
    문구라벨 = Label(text=문구, halign="center", valign="middle")
    문구라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
    본문.add_widget(문구라벨)
    팝업 = Popup(title=제목, content=본문, size_hint=(0.85, None), height=dp(240))
    버튼줄 = BoxLayout(
        orientation="horizontal", size_hint=(1, None), height=dp(52), spacing=dp(8)
    )
    예 = Button(text="예")
    예.bind(on_release=lambda *_: (팝업.dismiss(), 확인()))
    아니요 = 뒤로키_버튼(Button(text="아니요"))
    아니요.bind(on_release=lambda *_: 팝업.dismiss())
    버튼줄.add_widget(예)
    버튼줄.add_widget(아니요)
    본문.add_widget(버튼줄)
    팝업.open()
    return 팝업


# 게임 중 [메뉴] - 마을과 던전이 같은 팝업을 쓴다. 저장/불러오기 목록과 설정의 [뒤로]는 연 화면으로 돌아간다.
_메뉴_진행경고 = "저장하지 않은 진행은 사라집니다.\n계속할까요?"


def 게임메뉴_열기(화면):
    """화면(마을/던전 Screen)에서 [메뉴]를 눌렀을 때의 팝업 - 저장하기/불러오기/도감/업적/설정/타이틀로 돌아가기."""
    매니저 = 화면.manager
    본문 = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
    팝업 = Popup(title="메뉴", content=본문, size_hint=(0.8, None), height=dp(540))

    def 이동(화면이름):
        팝업.dismiss()
        매니저.get_screen(화면이름).돌아갈화면 = 화면.name
        매니저.current = 화면이름

    def 메인메뉴로():
        팝업.dismiss()
        매니저.current = "메인메뉴"

    for 글, 동작 in (
        ("저장하기", lambda: 이동("저장목록")),
        (
            "불러오기",
            lambda: 확인_팝업("불러오기", _메뉴_진행경고, lambda: 이동("불러오기목록")),
        ),
        ("도감", lambda: 이동("도감")),
        ("업적", lambda: 이동("업적")),
        ("설정", lambda: 이동("설정")),
        (
            "타이틀로 돌아가기",
            lambda: 확인_팝업("타이틀로 돌아가기", _메뉴_진행경고, 메인메뉴로),
        ),
    ):
        버튼 = Button(text=글)
        버튼.bind(on_release=lambda *_, 동작=동작: 동작())
        본문.add_widget(버튼)
    본문.add_widget(닫기_버튼(팝업))
    팝업.open()
    return 팝업


def 스크롤_목록(높이비율, 간격=6):
    """세로로 쌓는 목록틀(내용 높이만큼 늘어남)과 그것을 감싼 ScrollView. (스크롤, 목록틀)을 돌려준다."""
    목록틀 = BoxLayout(orientation="vertical", size_hint_y=None, spacing=간격)
    목록틀.bind(minimum_height=목록틀.setter("height"))
    스크롤 = ScrollView(size_hint=(1, 높이비율))
    스크롤.add_widget(목록틀)
    return 스크롤, 목록틀


def 탭_줄(
    탭목록, 고르기, 고른탭=None, 높이=None, font_size="14sp", 그룹=None, 칸수=None
):
    """한 줄에 다 보이는 탭 버튼들(옆으로 밀어서 넘기지 않는다 - 폭을 똑같이 나눈다).
    누르면 그 탭만 눌린 상태가 되고 고르기(탭)를 부른다. 여러 줄을 한 묶음으로 쓰려면
    같은 그룹 이름과 칸수(줄마다 같은 폭)를 준다."""
    줄 = GridLayout(
        cols=max(1, 칸수 or len(탭목록)),
        size_hint=(1, None),
        height=높이 or dp(44),
        spacing=dp(4),
    )
    그룹 = 그룹 or f"탭줄{id(줄)}"
    for 탭 in 탭목록:
        버튼 = ToggleButton(
            text=탭,
            group=그룹,
            allow_no_selection=False,
            state="down" if 탭 == 고른탭 else "normal",
            font_size=font_size,
            shorten=True,
            shorten_from="right",
        )
        버튼.bind(size=lambda inst, sz: setattr(inst, "text_size", (sz[0], None)))
        버튼.halign = "center"
        버튼.bind(on_release=lambda inst, t=탭: 고르기(t))
        줄.add_widget(버튼)
    return 줄


# 아이템 이름 색 - 레어도별(2026-10-07 사용자 지정). "세트"는 커먼 방어구 세트 아이템
# (gameflow.아이템_색분류), "치트"는 글자마다 무지개색. 표에 없는 레어도는 흰색.
_레어도_색 = {
    "커먼": "ffffff",
    "언커먼": "4d8cff",
    "레어": "b36bff",
    "유니크": "ff3d9a",
    "레전더리": "ff9a2e",  # 주황 - 크로니클(빨강)과 다른 등급
    "크로니클": "ff4040",
    "에픽": "ffd633",
    "세트": "4dd65a",
}
_무지개_색 = ["ff4040", "ff9a2e", "ffd633", "4dd65a", "4d8cff", "6a5cff", "b36bff"]


def 아이템_이름_글(아이템, 글=None):
    """아이템 이름(또는 그 이름이 든 글)을 레어도 색 마크업으로. markup=True인 라벨에 쓴다."""
    글 = escape_markup(글 if 글 is not None else 아이템.get("이름", ""))
    분류 = gameflow.아이템_색분류(아이템)
    if 분류 == "치트":
        조각 = []
        i = 0
        for 글자 in 글:
            if 글자.isspace():
                조각.append(글자)
                continue
            조각.append(f"[color={_무지개_색[i % len(_무지개_색)]}]{글자}[/color]")
            i += 1
        return "".join(조각)
    return f"[color={_레어도_색.get(분류, 'ffffff')}]{글}[/color]"


def 아이템_이름_글_찾아서(게임상태, 이름, 글=None):
    """이름으로 아이템을 찾아 색을 입힌다(못 찾으면 글 그대로 - 골드/재료 줄 등)."""
    아이템 = gameflow.아이템_찾기(게임상태, 이름)
    if 아이템 is None:
        return escape_markup(글 if 글 is not None else 이름)
    return 아이템_이름_글(아이템, 글)


def _뒤로키_버튼_찾기(위젯):
    for 자식 in 위젯.walk(restrict=True):
        if getattr(자식, "뒤로키", False) and not 자식.disabled:
            return 자식
    return None


class _테두리박스(ButtonBehavior, BoxLayout):
    """테두리를 그리는 상자. 전투화면의 적/아군 상태 박스, 그래픽 박스,
    배경 틀(전투 배경 이미지는 아직 없어 빈 채로 둔다)에 공용으로 쓴다(screens_battle에서 옮김).
    현재턴_표시()로 테두리를 굵게 만들어 누구 턴인지 표시한다."""

    def __init__(self, 테두리색, 기본두께=1.5, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        super().__init__(**kwargs)
        self._기본두께 = 기본두께
        with self.canvas.before:
            Color(*테두리색)
            self._테두리 = Line(width=기본두께)
        self.bind(pos=self._다시그리기, size=self._다시그리기)

    def _다시그리기(self, *args):
        self._테두리.rectangle = (
            self.x + 1,
            self.y + 1,
            max(self.width - 2, 0),
            max(self.height - 2, 0),
        )

    def 현재턴_표시(self, 켜짐):
        self._테두리.width = self._기본두께 * 2.5 if 켜짐 else self._기본두께


# =====================================================
# 주/보조/약점스탯 고르기 판 - 새 게임 파티 구성과 주점 영입(2026-10-16 사용자 결정)
# =====================================================
# 능력치 6칸을 터치하면 역할이 주스탯 -> 보조스탯 -> 일반 -> 약점스탯 순서로 바뀐다
# (다른 칸이 이미 맡은 역할은 건너뜀 - 규칙은 gameflow.스탯역할_다음). 테두리 색이
# 역할을 보여 준다. 점수는 쓰는 쪽이 미리보기 캐릭터로 계산해 설정()으로 넣는다.
스탯역할_테두리색 = {
    "주스탯": (1, 0.82, 0.2, 1),  # 노랑
    "보조스탯": (0.35, 0.6, 1, 1),  # 파랑
    "약점스탯": (0.92, 0.3, 0.3, 1),  # 빨강
    "일반": (1, 1, 1, 1),  # 하양
}


class _스탯칸(ButtonBehavior, Label):
    def __init__(self, 스탯이름, **kwargs):
        super().__init__(markup=True, halign="center", valign="middle", **kwargs)
        self.스탯이름 = 스탯이름
        self.역할 = "일반"
        with self.canvas.before:
            self._테두리색 = Color(*스탯역할_테두리색["일반"])
            self._테두리 = Line(width=1.4)
        self.bind(pos=self._다시그리기, size=self._다시그리기)

    def _다시그리기(self, *args):
        self.text_size = self.size
        self._테두리.rectangle = (
            self.x + 2,
            self.y + 2,
            max(self.width - 4, 0),
            max(self.height - 4, 0),
        )

    def 역할_설정(self, 역할):
        self.역할 = 역할
        self._테두리색.rgba = 스탯역할_테두리색[역할]


class 스탯고르기판(GridLayout):
    """능력치 6칸(3x2). 칸을 터치하면 self.스탯구성이 바뀌고 바뀜(스탯구성)을 부른다."""

    능력치_목록 = ["근력", "민첩", "건강", "지능", "지혜", "매력"]

    def __init__(self, 바뀜=None, font_size="12sp", **kwargs):
        kwargs.setdefault("cols", 3)
        kwargs.setdefault("spacing", dp(3))
        super().__init__(**kwargs)
        self.스탯구성 = {}
        self._바뀜 = 바뀜
        self.칸 = {}
        for 이름 in self.능력치_목록:
            칸 = _스탯칸(이름, font_size=font_size)
            칸.bind(on_release=lambda inst: self.터치(inst.스탯이름))
            self.add_widget(칸)
            self.칸[이름] = 칸

    def 터치(self, 스탯이름):
        if self.disabled:
            return
        self.스탯구성 = gameflow.스탯역할_다음(self.스탯구성, 스탯이름)
        if self._바뀜 is not None:
            self._바뀜(self.스탯구성)

    def 설정(self, 스탯구성, 능력치):
        """역할(테두리)과 점수 글자를 다시 그린다. 능력치 = {이름: 값}."""
        self.스탯구성 = dict(스탯구성)
        for 이름, 칸 in self.칸.items():
            칸.역할_설정(gameflow.스탯역할(스탯구성, 이름))
            칸.text = f"[color=9ea6b3]{이름}[/color] {능력치[이름]}"


def 능력치역할_팝업(제목, 캐릭터, 기본구성, 확인콜백, 안내="", 취소콜백=None):
    """주/보조/약점 역할을 다시 고르는 팝업(#351 - 전직, 레테의 강물·눈물, 옛 세이브의 한 번 고르기).
    처음에는 기본구성이 골라져 있고, 칸을 누르면 역할이 바뀌며 점수는 역할끼리 값을 바꾼 미리보기
    (gameflow.능력치_역할_미리보기)로 다시 그린다. 확인콜백(스탯구성)은 셋을 다 골랐을 때만 부른다.
    취소콜백이 없으면 [취소]를 두지 않는다(옛 세이브의 한 번 고르기처럼 꼭 정해야 할 때)."""
    본문 = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
    if 안내:
        안내라벨 = Label(text=안내, size_hint=(1, None), height=dp(72), halign="center")
        안내라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        본문.add_widget(안내라벨)
    상태라벨 = Label(text="", size_hint=(1, None), height=dp(28), font_size="14sp")

    def 바뀜(스탯구성):
        판.설정(스탯구성, gameflow.능력치_역할_미리보기(캐릭터, 스탯구성))
        확인.disabled = any(
            스탯구성.get(r) is None for r in ("주스탯", "보조스탯", "약점스탯")
        )
        상태라벨.text = "" if not 확인.disabled else "주/보조/약점을 모두 골라 주세요."

    판 = 스탯고르기판(바뀜=바뀜, font_size="15sp", size_hint=(1, 1))
    본문.add_widget(판)
    본문.add_widget(상태라벨)
    버튼줄 = BoxLayout(size_hint=(1, None), height=dp(52), spacing=dp(8))
    확인 = Button(text="확인")
    버튼줄.add_widget(확인)
    팝업 = Popup(title=제목, content=본문, size_hint=(0.9, 0.6), auto_dismiss=False)
    if 취소콜백 is not None:
        취소 = 뒤로키_버튼(Button(text="취소"))

        def 취소하기(*_):
            팝업.dismiss()
            취소콜백()

        취소.bind(on_release=취소하기)
        버튼줄.add_widget(취소)
    본문.add_widget(버튼줄)

    def 확인하기(*_):
        팝업.dismiss()
        확인콜백(dict(판.스탯구성))

    확인.bind(on_release=확인하기)
    바뀜(dict(기본구성))
    팝업.능력치판 = 판
    팝업.open()
    return 팝업


# =====================================================
# 기준 화면 틀 - 화면은 사용자 폰(갤럭시 S24 세로, 1080x2340 픽셀) 하나를 기준으로
# 만든다. 비율이 다른 기기에서는 기준 화면 전체를 같은 배율로 줄이거나 키워 가운데에
# 두고, 남는 곳(더 길면 위아래, 더 넓으면 좌우)은 검정 여백으로 둔다. 터치 위치도
# 같은 배율로 바뀐다(ScatterLayout). 팝업은 창에 직접 뜨므로 창 가운데(= 기준 화면
# 가운데)에 뜨고, 크기 비율(size_hint)도 창이 아니라 기준 화면에 대한 비율이 되게 맞춘다.
# =====================================================
기준화면_폭 = 1080
기준화면_높이 = 2340


def 기준화면_배율(창폭, 창높이):
    """기준 화면을 창 안에 비율 그대로 다 들어가게 놓을 때의 배율."""
    return min(창폭 / 기준화면_폭, 창높이 / 기준화면_높이)


class 기준화면틀(Widget):
    """내용(화면 관리자)을 기준 화면 크기로 고정하고, 창에 맞춰 배율과 위치만 바꾼다."""

    def __init__(self, 내용, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 1)
            self._여백 = Rectangle()
        self.틀 = ScatterLayout(
            do_rotation=False,
            do_scale=False,
            do_translation=False,
            auto_bring_to_front=False,
            size_hint=(None, None),
            size=(기준화면_폭, 기준화면_높이),
        )
        self.틀.add_widget(내용)
        self.add_widget(self.틀)
        self.bind(pos=self._맞추기, size=self._맞추기)

    @property
    def 배율(self):
        return self.틀.scale

    def _맞추기(self, *args):
        self._여백.pos = self.pos
        self._여백.size = self.size
        배율 = 기준화면_배율(self.width, self.height)
        self.틀.scale = 배율
        self.틀.pos = (
            self.x + (self.width - 기준화면_폭 * 배율) / 2,
            self.y + (self.height - 기준화면_높이 * 배율) / 2,
        )

    def 팝업_맞추기(self, 창, 자식들):
        """창에 새로 뜬 팝업의 크기 비율을 기준 화면에 대한 비율로 바꾼다 - 넓은 기기에서
        팝업이 검정 여백까지 덮지 않게. 창.children에 묶어 부른다."""
        보이는폭 = 기준화면_폭 * self.배율
        보이는높이 = 기준화면_높이 * self.배율
        for 자식 in 자식들:
            if not isinstance(자식, ModalView):
                continue
            가로, 세로 = 자식.size_hint
            자식.size_hint_max = (
                None if 가로 is None else 가로 * 보이는폭,
                None if 세로 is None else 세로 * 보이는높이,
            )


# =====================================================
# 마을/던전/전투 화면 배치 - 상단 1170 + 하단 1170, 각각 4줄(기준 화면 픽셀, 2026-10-07
# 사용자 확정 - docs/game-rules.md "화면 배치"). 기준 화면 틀이 기기에 맞춰
# 통째로 줄이고 키우므로 여기 길이는 dp가 아니라 기준 화면 픽셀 그대로 쓴다.
# =====================================================
상단_높이 = 1170
하단_높이 = 1170
정사각형_크기 = 200  # 상단 1줄(파티원/적), 전투 4줄(파티원)
그림줄_높이 = 385  # 전투 2줄(몬스터 그림), 3줄(파티원 그림)
상단_그림_높이 = 상단_높이 - 정사각형_크기  # 마을 그림/던전 지도(2~4줄)
하단_첫줄_높이 = 290  # 마을명 / 위치·걸음수 / 전투 기록
하단_나머지_높이 = 하단_높이 - 하단_첫줄_높이  # 버튼 등(2~4줄)
하단_좌우여백 = 16


class 고른간격줄(Widget):
    """자식들을 양 끝과 사이가 모두 같은 간격이 되게 왼쪽부터 놓는다(칸 수가 바뀌면 간격이
    바뀐다). 자식 폭은 칸폭, 높이는 줄 높이. 넓힘이면 자식 폭을 칸폭 + 간격으로 늘린다 -
    칸 가운데는 같은 칸 수의 정사각형 줄과 맞는다(전투 그림 줄)."""

    def __init__(self, 칸폭=정사각형_크기, 넓힘=False, **kwargs):
        super().__init__(**kwargs)
        self.칸폭 = 칸폭
        self.넓힘 = 넓힘
        self.bind(pos=self._배치, size=self._배치, children=self._배치)

    def _배치(self, *args):
        자식들 = list(reversed(self.children))  # add_widget 순서 = 왼쪽부터
        n = len(자식들)
        if not n:
            return
        간격 = max(0, (self.width - n * self.칸폭) / (n + 1))
        폭 = self.칸폭 + (간격 if self.넓힘 else 0)
        for i, 자식 in enumerate(자식들):
            가운데 = self.x + 간격 * (i + 1) + self.칸폭 * i + self.칸폭 / 2
            자식.size_hint = (None, None)
            자식.size = (폭, self.height)
            자식.pos = (가운데 - 폭 / 2, self.y)


파티칸_틈 = 8  # 파티원 상자 사이 틈(양 끝은 하단_좌우여백)


class 파티칸줄(Widget):
    """파티원 상자 줄(마을/던전 상단 1줄, 전투 3~4줄) - 최대 인원(4명)이 양 끝 여백
    하단_좌우여백과 사이 틈 파티칸_틈만 남기고 줄 폭을 꽉 채우는 폭으로 놓는다.
    인원이 적으면 같은 폭 그대로 가운데에 모은다. 높이는 줄 높이(2026-10-09 사용자 요청)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.칸수 = (
            None  # 칸 폭 기준 인원(없으면 파티 최대인원 4) - 전투에 인형이 있으면 5
        )
        self.bind(pos=self._배치, size=self._배치, children=self._배치)

    def 칸폭(self):
        최대 = self.칸수 or gameflow.파티_최대인원
        return (self.width - 2 * 하단_좌우여백 - (최대 - 1) * 파티칸_틈) / 최대

    def _배치(self, *args):
        자식들 = list(reversed(self.children))  # add_widget 순서 = 왼쪽부터
        n = len(자식들)
        if not n:
            return
        폭 = self.칸폭()
        왼쪽 = self.x + (self.width - n * 폭 - (n - 1) * 파티칸_틈) / 2
        for i, 자식 in enumerate(자식들):
            자식.size_hint = (None, None)
            자식.size = (폭, self.height)
            자식.pos = (왼쪽 + i * (폭 + 파티칸_틈), self.y)


class 가로맞춤_라벨(Label):
    """한 줄 라벨 - 글이 라벨 폭보다 길면 글자 높이는 그대로 두고 가로로만 눌러 폭에 맞춘다
    (긴 직업명 "엘리멘탈마스터"가 정사각형에서 줄바꿈되지 않게). 짧으면 그대로."""

    여백 = 4

    def __init__(self, **kwargs):
        kwargs.setdefault("halign", "center")
        kwargs.setdefault("valign", "middle")
        super().__init__(**kwargs)
        self.bind(texture_size=self._맞추기, size=self._맞추기)

    def _맞추기(self, *args):
        if self.texture is None:
            return
        tw, th = self.texture.size
        # 폭이 바뀔 때마다 원래 글 폭에서 다시 정한다(처음 좁을 때 눌린 채 남지 않게)
        맞춤 = [min(tw, max(1, self.width - self.여백)), th]
        if list(self.texture_size) != 맞춤:
            self.texture_size = 맞춤


def 줄_상자_채우기(상자, 줄들, font_size="13sp", **kwargs):
    """상자를 비우고 글 줄마다 가로맞춤_라벨을 위에서 아래로 쌓는다(정사각형 칸 글)."""
    상자.clear_widgets()
    for 줄 in 줄들:
        상자.add_widget(가로맞춤_라벨(text=줄, font_size=font_size, **kwargs))


def 글자_높이(font_size="15sp", 여백=None):
    """그 글자 크기 한 줄이 들어가는 버튼/구역 높이 - 글자 줄 높이 + 위아래 여백."""
    return sp(float(str(font_size).rstrip("sp"))) * 1.25 + (
        dp(8) if 여백 is None else 여백
    )


def 가운데_라벨(글, font_size="13sp", **kwargs):
    라벨 = Label(
        text=글, font_size=font_size, halign="center", valign="middle", **kwargs
    )
    라벨.bind(size=lambda inst, sz: setattr(inst, "text_size", sz))
    return 라벨


def 파티원_정사각형_채우기(줄, 게임상태):
    """마을/던전 상단 1줄(고른간격줄)을 파티원마다 정사각형(이름, 레벨, HP, MP)으로 채운다."""
    줄.clear_widgets()
    for 캐릭터 in 게임상태["파티"]["파티원"]:
        상자 = _테두리박스((1, 1, 1, 1), padding=dp(4))
        줄_상자_채우기(
            상자,
            [
                캐릭터["캐릭터명"],
                f"Lv.{캐릭터['레벨']}",
                f"HP {캐릭터['현재HP']}/{gameflow.캐릭터_최대HP(게임상태, 캐릭터)}",
                f"MP {캐릭터['현재MP']}/{gameflow.캐릭터_최대MP(게임상태, 캐릭터)}",
            ],
            font_size="12sp",
        )
        줄.add_widget(상자)


def 뒤로키_처리(창, 키, *args):
    if 키 != 27:
        return False
    맨위 = 창.children[0] if 창.children else None
    if isinstance(맨위, DropDown):
        맨위.dismiss()
    elif isinstance(맨위, ModalView):
        # 표시된 버튼이 없는 팝업은, 바깥을 눌러 닫을 수 있는 것만 닫는다
        # (auto_dismiss=False이면서 취소 버튼도 없는 팝업은 꼭 골라야 하는 창).
        버튼 = _뒤로키_버튼_찾기(맨위)
        if 버튼 is not None:
            버튼.trigger_action(duration=0)
        elif 맨위.auto_dismiss:
            맨위.dismiss()
    else:
        버튼 = _뒤로키_버튼_찾기(App.get_running_app().매니저.current_screen)
        if 버튼 is not None:
            버튼.trigger_action(duration=0)
    return True
