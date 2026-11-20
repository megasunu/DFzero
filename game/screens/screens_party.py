# =====================
# 파티 화면 - 파티관리(레벨업/전직/능력치 배분/퍽 선택/스킬습득), 파티원(장비·스탯 /
# 스킬·특성·퍽), 장비 교체 팝업
# =====================
# main.py가 game/screens/ 여섯 파일의 화면을 ScreenManager에 등록한다.

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
from kivy.utils import escape_markup

import gameflow
from game.screens.screens_common import (
    _HP색,
    _MP색,
    _강조색,
    _게이지,
    _둥근상자,
    _카드_배경색,
    _카드_쓰러짐색,
    _캐릭터이미지_경로,
    _평면버튼,
    _흐린글자색,
    뒤로키_버튼,
    능력치역할_팝업,
    스크롤_목록,
    닫기_버튼,
)


# =====================================================
# 5-1. 파티관리 화면 (캐릭터별 레벨업)
# =====================================================
# 캐릭터 레벨은 몬스터 처치 경험치가 아니라 "플레이어 레벨"(던전 보스
# 첫 클리어 시 gameflow.전투_결과_정리()가 올림) 한도 안에서, 캐릭터별로
# 이 화면의 [레벨업] 버튼을 하나씩 눌러야 오른다. 마을화면/
# 던전화면의 "파티" 버튼이 여기로 연결되고, self.복귀화면에 어디서
# 들어왔는지("마을"/"던전")를 담아 뒤로가기 때 그리로 돌아간다.


class 파티관리화면(Screen):
    _능력치_목록 = gameflow.능력치_목록

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.복귀화면 = "마을"

        루트 = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))

        머리 = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(52))
        제목 = Label(
            text="파티", font_size="26sp", bold=True, halign="left", valign="middle"
        )
        제목.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        머리.add_widget(제목)
        레벨틀 = _둥근상자(
            _카드_배경색,
            반지름=16,
            size_hint=(None, None),
            size=(dp(150), dp(36)),
            pos_hint={"center_y": 0.5},
        )
        self.플레이어레벨라벨 = Label(text="", font_size="14sp")
        레벨틀.add_widget(self.플레이어레벨라벨)
        머리.add_widget(레벨틀)
        루트.add_widget(머리)

        self.목록틀 = BoxLayout(orientation="vertical", spacing=dp(10))
        루트.add_widget(self.목록틀)

        self.안내라벨 = Label(
            text="",
            size_hint=(1, None),
            height=dp(28),
            font_size="13sp",
            color=_흐린글자색,
        )
        루트.add_widget(self.안내라벨)

        뒤로버튼 = _평면버튼(
            "뒤로",
            (0.3, 0.31, 0.35, 1),
            size_hint=(1, None),
            height=dp(56),
            font_size="16sp",
        )
        뒤로키_버튼(뒤로버튼)
        뒤로버튼.bind(on_release=self._뒤로_클릭)
        루트.add_widget(뒤로버튼)

        self.add_widget(루트)

    def on_pre_enter(self, *args):
        self.갱신()

    def 갱신(self):
        앱 = App.get_running_app()
        게임상태 = 앱.게임상태
        if 게임상태 is None:
            return

        self.플레이어레벨라벨.text = (
            f"플레이어 레벨 {게임상태['진행도']['플레이어레벨']}"
        )

        self.목록틀.clear_widgets()
        for 캐릭터 in 게임상태["파티"]["파티원"]:
            self.목록틀.add_widget(self._행_생성(게임상태, 캐릭터))

    def _행_생성(self, 게임상태, 캐릭터):
        생존 = 캐릭터["현재HP"] > 0
        카드 = _둥근상자(
            _카드_배경색 if 생존 else _카드_쓰러짐색,
            orientation="horizontal",
            padding=dp(10),
            spacing=dp(10),
        )

        # 왼쪽: 초상화
        초상틀 = _둥근상자(
            (0.2, 0.21, 0.25, 1), 반지름=10, size_hint=(0.2, 1), padding=dp(4)
        )
        초상틀.add_widget(
            Image(
                allow_stretch=True,
                keep_ratio=True,
                source=_캐릭터이미지_경로(gameflow.초상화_코드(캐릭터)),
                color=(1, 1, 1, 1) if 생존 else (0.45, 0.45, 0.45, 1),
            )
        )
        카드.add_widget(초상틀)

        # 가운데: 이름/직업/레벨, HP·MP 게이지, 능력치
        가운데 = BoxLayout(orientation="vertical", size_hint=(0.6, 1), spacing=dp(4))
        이름글 = f"[b]{escape_markup(캐릭터['캐릭터명'])}[/b]"
        if not 생존:
            이름글 += "  [color=e05555][size=12sp]쓰러짐[/size][/color]"
        이름라벨 = Label(
            text=이름글,
            markup=True,
            font_size="17sp",
            halign="left",
            valign="bottom",
            size_hint=(1, 0.2),
            shorten=True,
            shorten_from="right",
        )
        이름라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        가운데.add_widget(이름라벨)
        직업라벨 = Label(
            text=f"{gameflow.캐릭터_직업표시(캐릭터)}  ·  Lv.{캐릭터['레벨']}",
            font_size="13sp",
            color=_흐린글자색,
            halign="left",
            valign="top",
            size_hint=(1, 0.16),
        )
        직업라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        가운데.add_widget(직업라벨)
        가운데.add_widget(
            _게이지(
                "HP",
                캐릭터["현재HP"],
                gameflow.캐릭터_최대HP(게임상태, 캐릭터),
                _HP색,
                size_hint=(1, 0.15),
            )
        )
        가운데.add_widget(
            _게이지(
                "MP",
                캐릭터["현재MP"],
                gameflow.캐릭터_최대MP(게임상태, 캐릭터),
                _MP색,
                size_hint=(1, 0.15),
            )
        )
        # 장비(+세트) 스탯 반영 능력치 - 장비로 오른 값은 괄호로 표시.
        # 두 칸 x 세 줄 - 세 칸이면 "지혜 18 (+12)"처럼 괄호가 붙을 때 한 칸에 안 들어가
        # 글자가 줄바꿈되며 이름이 잘린다.
        유효능력치 = gameflow.캐릭터_유효능력치(게임상태, 캐릭터)
        능력치판 = GridLayout(cols=2, size_hint=(1, 0.34))
        for 이름 in self._능력치_목록:
            값 = 유효능력치[이름]
            차이 = 값 - 캐릭터[이름]
            꼬리 = f" [color=6fb3ff]({차이:+d})[/color]" if 차이 else ""
            칸 = Label(
                text=f"[color=9ea6b3]{이름}[/color] {값}{꼬리}",
                markup=True,
                font_size="12sp",
                halign="left",
                valign="middle",
            )
            칸.bind(size=lambda inst, size: setattr(inst, "text_size", size))
            능력치판.add_widget(칸)
        가운데.add_widget(능력치판)
        카드.add_widget(가운데)

        # 오른쪽: 버튼 세 개를 위에서 아래로(레벨업 가능하면 강조색)
        오른쪽 = BoxLayout(orientation="vertical", size_hint=(0.2, 1), spacing=dp(6))
        버튼크기 = {"size_hint": (1, 1)}
        가능 = gameflow.캐릭터_레벨업_가능(게임상태, 캐릭터)
        레벨업버튼 = _평면버튼(
            "레벨업",
            _강조색 if 가능 else (0.2, 0.21, 0.25, 1),
            font_size="14sp",
            bold=가능,
            disabled=not 가능,
            disabled_color=(0.45, 0.47, 0.52, 1),
            **버튼크기,
        )
        레벨업버튼.bind(on_release=lambda inst, c=캐릭터: self._레벨업_클릭(c))
        오른쪽.add_widget(레벨업버튼)

        스킬습득버튼 = _평면버튼(
            "스킬습득", (0.3, 0.31, 0.35, 1), font_size="14sp", **버튼크기
        )
        스킬습득버튼.bind(on_release=lambda inst, c=캐릭터: self._스킬습득_팝업(c))
        오른쪽.add_widget(스킬습득버튼)

        # 파티원 화면(장비·스탯 / 스킬·특성).
        상세버튼 = _평면버튼(
            "상세보기", (0.3, 0.31, 0.35, 1), font_size="14sp", **버튼크기
        )
        상세버튼.bind(on_release=lambda inst, c=캐릭터: self._상세보기_클릭(c))
        오른쪽.add_widget(상세버튼)
        카드.add_widget(오른쪽)

        return 카드

    def _상세보기_클릭(self, 캐릭터):
        화면 = self.manager.get_screen("파티원")
        화면.캐릭터 = 캐릭터
        화면.복귀화면 = "파티관리"
        self.manager.current = "파티원"

    # -------------------------------------------------
    # 레벨업 - 타입별 분기
    # -------------------------------------------------

    def _레벨업_클릭(self, 캐릭터):
        if gameflow.캐릭터_전직_필요(캐릭터):
            self._전직선택_팝업(캐릭터)
            return
        항목 = gameflow.캐릭터_다음_레벨업_항목(캐릭터)
        if 항목 is None:
            return
        타입 = 항목["타입"]

        # 스킬개화(레벨 17)는 선택지가 아직 미정이라 바로 확정한다
        if 타입 in (
            "특성획득",
            "스킬획득",
            "행동획득",
            "미정",
            "스타일강화",
            "스킬개화",
        ):
            self._레벨업_확정(캐릭터)
        elif 타입 == "스탯획득":
            배분점수 = 항목["획득"]["배분점수"]
            self._능력치배분_팝업(
                캐릭터,
                배분점수,
                확인콜백=lambda 배분: self._레벨업_확정(캐릭터, 배분=배분),
            )
        elif 타입 == "마스터리선택":
            self._마스터리선택_팝업(
                캐릭터,
                확인콜백=lambda 무기, 방어구: self._레벨업_확정(
                    캐릭터, 무기마스터리=무기, 방어구마스터리=방어구
                ),
            )
        elif 타입 == "스타일선택":
            self._스타일선택_팝업(
                캐릭터,
                항목["획득"],
                확인콜백=lambda 스타일: self._레벨업_확정(캐릭터, 스타일=스타일),
            )
        elif 타입 == "스탯성장":
            획득 = 항목["획득"]
            self._능력치배분_팝업(
                캐릭터,
                획득["배분점수"],
                확인콜백=lambda 배분: self._레벨업_확정(캐릭터, 배분=배분),
                스탯당최대=획득["스탯당최대"],
                약점제외=True,
            )
        elif 타입 == "스킬강화":
            self._스킬강화_팝업(
                캐릭터,
                항목,
                확인콜백=lambda 스킬: self._레벨업_확정(캐릭터, 강화스킬=스킬),
            )
        elif 타입 == "퍽획득":
            self._퍽선택_팝업(
                캐릭터,
                확인콜백=lambda 선택결과: self._레벨업_확정(캐릭터, **선택결과),
            )

    def _레벨업_확정(self, 캐릭터, **선택):
        gameflow.캐릭터_레벨업_확정(
            App.get_running_app().게임상태, 캐릭터, **선택
        )  # 적용 + 자동 저장
        self.안내라벨.text = (
            f"{캐릭터['캐릭터명']}이(가) 레벨 {캐릭터['레벨']}이(가) 되었습니다."
        )
        if 선택.get("전직"):
            self.안내라벨.text = (
                f"{캐릭터['캐릭터명']}이(가) {선택['전직']}(으)로 전직해 "
                f"레벨 {캐릭터['레벨']}이(가) 되었습니다."
            )
        self.갱신()

    # -------------------------------------------------
    # 전직 선택 팝업 (레벨 5 → 6)
    # -------------------------------------------------

    def _전직선택_팝업(self, 캐릭터):
        목록 = gameflow.선택가능_전직목록(캐릭터)

        본문 = BoxLayout(orientation="vertical", spacing=8, padding=12)
        본문.add_widget(Label(text="전직할 직업을 선택하세요.", size_hint=(1, 0.1)))

        스크롤, 목록틀 = 스크롤_목록(0.76)
        본문.add_widget(스크롤)

        팝업 = Popup(
            title="전직 선택",
            content=본문,
            size_hint=(0.9, 0.85),
            auto_dismiss=False,
        )

        def 능력치_고르기(전직명, **선택):
            # 전직하며 주/보조/약점을 다시 고른다 - 처음엔 전직별 표가 골라져 있다
            능력치역할_팝업(
                f"{전직명} - 능력치 다시 고르기",
                캐릭터,
                gameflow.전직_기본_스탯구성(전직명, 캐릭터),
                확인콜백=lambda 구성: self._레벨업_확정(
                    캐릭터, 전직=전직명, 스탯구성=구성, **선택
                ),
                안내="주/보조/약점 능력치를 다시 고른다.\n값은 역할끼리 바뀐다"
                "(특성이 올린 값은 그 능력치에 남는다).",
                취소콜백=lambda: None,
            )

        def 선택(전직명):
            팝업.dismiss()
            항목 = gameflow.캐릭터_다음_레벨업_항목(캐릭터, 전직명)
            if 항목 and 항목.get("스타일선택지"):
                # 전직 레벨은 전투 스타일도 다시 고른다(기존 스타일과 교체)
                self._스타일선택_팝업(
                    캐릭터,
                    {
                        "선택지": 항목["스타일선택지"],
                        "설명": f"{전직명}(으)로 전직하며 전투 스타일을 다시 "
                        "고른다. 기존 스타일과 교체된다.",
                    },
                    확인콜백=lambda 스타일: 능력치_고르기(전직명, 스타일=스타일),
                )
                return
            능력치_고르기(전직명)

        for 전직명, 설명, 구현 in 목록:
            행 = BoxLayout(
                orientation="vertical", size_hint=(1, None), height=dp(90), spacing=2
            )
            # 미구현 전직은 목록에는 보이되 누를 수 없다.
            버튼 = Button(
                text=전직명 if 구현 else f"{전직명} (미구현)",
                size_hint=(1, None),
                height=dp(40),
                disabled=not 구현,
            )
            버튼.bind(on_release=lambda inst, n=전직명: 선택(n))
            행.add_widget(버튼)
            설명라벨 = Label(
                text=설명,
                font_size="15sp",
                size_hint=(1, None),
                height=dp(24),
                halign="left",
            )
            설명라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
            행.add_widget(설명라벨)
            # 전직하기 전에 추천 주/보조/약점을 보여 준다
            추천라벨 = Label(
                text=gameflow.전직_추천_문구(전직명),
                font_size="14sp",
                size_hint=(1, None),
                height=dp(22),
                halign="left",
            )
            추천라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
            행.add_widget(추천라벨)
            목록틀.add_widget(행)

        닫기버튼 = Button(text="취소", size_hint=(1, 0.1))
        뒤로키_버튼(닫기버튼)
        닫기버튼.bind(on_release=lambda *_: 팝업.dismiss())
        본문.add_widget(닫기버튼)
        팝업.open()

    # -------------------------------------------------
    # 능력치 배분 팝업 ("스탯획득" 타입 / "능력치향상" 퍽 공용)
    # -------------------------------------------------

    def _능력치배분_팝업(
        self, 캐릭터, 배분점수, 확인콜백, 스탯당최대=None, 약점제외=False
    ):
        """스탯당최대: 한 능력치에 넣을 수 있는 최대 점수(None이면 제한 없음).
        약점제외: 약점제거 특성이 있어도 약점스탯에는 못 넣는다("스탯성장")."""
        배분 = {이름: 0 for 이름 in self._능력치_목록}
        투자가능 = {
            이름: gameflow.약점스탯_투자가능(캐릭터, 이름)
            and not (약점제외 and 이름 in gameflow.성장불가_스탯(캐릭터))
            for 이름 in self._능력치_목록
        }
        한도 = 배분점수 if 스탯당최대 is None else 스탯당최대

        본문 = BoxLayout(orientation="vertical", spacing=6, padding=12)
        남은점수라벨 = Label(text="", size_hint=(1, 0.12))
        본문.add_widget(남은점수라벨)

        행위젯 = {}
        for 이름 in self._능력치_목록:
            행 = BoxLayout(orientation="horizontal", size_hint=(1, None), height=dp(40))
            표시 = 이름 + ("" if 투자가능[이름] else " (약점)")
            행.add_widget(Label(text=표시, size_hint=(0.4, 1)))
            감소버튼 = Button(text="-", size_hint=(0.2, 1))
            값라벨 = Label(text="0", size_hint=(0.2, 1))
            증가버튼 = Button(text="+", size_hint=(0.2, 1))
            행.add_widget(감소버튼)
            행.add_widget(값라벨)
            행.add_widget(증가버튼)
            본문.add_widget(행)
            행위젯[이름] = (감소버튼, 값라벨, 증가버튼)

        확인버튼 = Button(text="확인", size_hint=(1, 0.14), disabled=True)
        본문.add_widget(확인버튼)

        팝업 = Popup(
            title="능력치 배분",
            content=본문,
            size_hint=(0.85, 0.8),
            auto_dismiss=False,
        )

        def 갱신(*args):
            남은 = 배분점수 - sum(배분.values())
            남은점수라벨.text = f"남은 점수: {남은} / {배분점수}"
            for 이름, (감소버튼, 값라벨, 증가버튼) in 행위젯.items():
                값라벨.text = str(배분[이름])
                감소버튼.disabled = 배분[이름] <= 0
                증가버튼.disabled = not (
                    투자가능[이름] and 남은 > 0 and 배분[이름] < 한도
                )
            확인버튼.disabled = 남은 != 0

        def 증감(이름, 증감값):
            if 증감값 > 0:
                if not 투자가능[이름] or (배분점수 - sum(배분.values())) <= 0:
                    return
                if 배분[이름] >= 한도:
                    return
            elif 배분[이름] <= 0:
                return
            배분[이름] += 증감값
            갱신()

        for 이름, (감소버튼, 값라벨, 증가버튼) in 행위젯.items():
            감소버튼.bind(on_release=lambda inst, n=이름: 증감(n, -1))
            증가버튼.bind(on_release=lambda inst, n=이름: 증감(n, 1))

        def 확인_클릭(*args):
            결과 = {이름: 값 for 이름, 값 in 배분.items() if 값 > 0}
            팝업.dismiss()
            확인콜백(결과)

        확인버튼.bind(on_release=확인_클릭)
        갱신()
        팝업.open()

    # -------------------------------------------------
    # 퍽 선택 팝업 ("퍽획득" 타입)
    # -------------------------------------------------

    def _마스터리선택_팝업(self, 캐릭터, 확인콜백):
        """레벨 2 "마스터리선택" - 무기 마스터리/방어구 숙련을 하나씩 골라(토글) [확인].
        줄마다 이름 토글 + [상세보기](설명은 상세보기 창에서만)."""
        무기목록, 방어구목록 = gameflow.캐릭터_마스터리_선택지(캐릭터)
        고른 = {"무기": None, "방어구": None}

        본문 = BoxLayout(orientation="vertical", spacing=6, padding=10)
        스크롤, 목록틀 = 스크롤_목록(1, 간격=4)
        본문.add_widget(스크롤)
        확인 = Button(text="확인", size_hint=(1, None), height=dp(48), disabled=True)

        def 고르기(종류, 이름):
            고른[종류] = 이름
            확인.disabled = None in 고른.values()

        for 종류, 목록 in (("무기", 무기목록), ("방어구", 방어구목록)):
            목록틀.add_widget(
                Label(text=f"{종류} 마스터리", size_hint=(1, None), height=dp(32))
            )
            for 이름, 설명 in 목록:
                줄 = BoxLayout(
                    orientation="horizontal",
                    size_hint=(1, None),
                    height=dp(40),
                    spacing=dp(6),
                )
                버튼 = ToggleButton(
                    text=이름,
                    group=f"마스터리_{종류}",
                    font_size="14sp",
                    size_hint=(0.7, 1),
                )
                버튼.bind(
                    on_release=lambda inst, k=종류, n=이름: 고르기(
                        k, n if inst.state == "down" else None
                    )
                )
                줄.add_widget(버튼)
                상세 = Button(text="상세보기", font_size="13sp", size_hint=(0.3, 1))
                상세.bind(
                    on_release=lambda inst, n=이름, d=설명: _스킬_상세_팝업(
                        n, d, 제목="마스터리 상세보기"
                    )
                )
                줄.add_widget(상세)
                목록틀.add_widget(줄)

        팝업 = Popup(
            title=f"{캐릭터['캐릭터명']} 마스터리 선택",
            content=본문,
            size_hint=(0.92, 0.9),
            auto_dismiss=False,
        )

        def 확인_클릭(*_):
            팝업.dismiss()
            확인콜백(고른["무기"], 고른["방어구"])

        확인.bind(on_release=확인_클릭)
        본문.add_widget(확인)
        취소 = Button(text="취소", size_hint=(1, None), height=dp(48))
        뒤로키_버튼(취소)
        취소.bind(on_release=lambda *_: 팝업.dismiss())
        본문.add_widget(취소)
        팝업.open()

    def _스타일선택_팝업(self, 캐릭터, 획득, 확인콜백):
        """레벨 2 "스타일선택" - 스타일마다 이름+설명 버튼, 맨 아래 [취소]."""
        본문 = BoxLayout(orientation="vertical", spacing=8, padding=12)
        본문.add_widget(_줄바꿈_라벨(획득["설명"]))
        팝업 = Popup(
            title=f"{캐릭터['캐릭터명']} 스타일 선택",
            content=본문,
            size_hint=(0.9, 0.85),
            auto_dismiss=False,
        )

        def 고르기(스타일):
            팝업.dismiss()
            확인콜백(스타일)

        설명 = dict(gameflow.전투스타일_목록())
        for 스타일 in 획득["선택지"]:
            버튼 = Button(
                text=f"{스타일}\n{설명.get(스타일, '')}",
                size_hint=(1, None),
                height=dp(64),
                halign="center",
                font_size="13sp",
            )
            버튼.bind(
                size=lambda inst, sz: setattr(inst, "text_size", (sz[0] - 12, None))
            )
            버튼.bind(on_release=lambda inst, s=스타일: 고르기(s))
            본문.add_widget(버튼)
        취소 = Button(text="취소", size_hint=(1, None), height=dp(44))
        뒤로키_버튼(취소)
        취소.bind(on_release=lambda *_: 팝업.dismiss())
        본문.add_widget(취소)
        팝업.open()

    def _스킬강화_팝업(self, 캐릭터, 항목, 확인콜백):
        """레벨 12 "스킬강화" - 고를 수 있는 보유 스킬마다 이름+설명 버튼, 맨 아래 [취소]."""
        목록 = gameflow.스킬강화_선택지(캐릭터, 항목)
        본문 = BoxLayout(orientation="vertical", spacing=8, padding=12)
        본문.add_widget(_줄바꿈_라벨(항목["획득"]["설명"]))
        스크롤, 목록틀 = 스크롤_목록(1)
        본문.add_widget(스크롤)
        팝업 = Popup(
            title=f"{캐릭터['캐릭터명']} 스킬 강화",
            content=본문,
            size_hint=(0.9, 0.85),
            auto_dismiss=False,
        )

        def 고르기(스킬):
            팝업.dismiss()
            확인콜백(스킬)

        if not 목록:
            목록틀.add_widget(
                Label(
                    text="(강화할 수 있는 스킬이 없습니다)",
                    size_hint=(1, None),
                    height=dp(40),
                )
            )
        for 스킬, 설명 in 목록:
            버튼 = Button(
                text=f"{스킬}\n{설명}",
                size_hint=(1, None),
                height=dp(72),
                halign="center",
                font_size="13sp",
            )
            버튼.bind(
                size=lambda inst, sz: setattr(inst, "text_size", (sz[0] - 12, None))
            )
            버튼.bind(on_release=lambda inst, n=스킬: 고르기(n))
            목록틀.add_widget(버튼)
        취소 = Button(text="취소", size_hint=(1, None), height=dp(44))
        뒤로키_버튼(취소)
        취소.bind(on_release=lambda *_: 팝업.dismiss())
        본문.add_widget(취소)
        팝업.open()

    def _퍽선택_팝업(self, 캐릭터, 확인콜백):
        목록 = gameflow.퍽_표시목록(캐릭터)

        본문 = BoxLayout(orientation="vertical", spacing=8, padding=12)
        본문.add_widget(Label(text="퍽을 하나 선택하세요.", size_hint=(1, 0.1)))

        스크롤, 목록틀 = 스크롤_목록(0.76)
        본문.add_widget(스크롤)

        팝업 = Popup(
            title="퍽 선택",
            content=본문,
            size_hint=(0.9, 0.85),
            auto_dismiss=False,
        )

        if not any(not 이유 for _, _, 이유 in 목록):
            목록틀.add_widget(
                Label(
                    text="(지금 고를 수 있는 퍽이 없습니다)",
                    size_hint=(1, None),
                    height=dp(40),
                )
            )

        for 퍽이름, 퍽정의, 이유 in 목록:
            # 퍽 버튼 + [상세보기]
            행 = BoxLayout(
                orientation="horizontal", size_hint=(1, None), height=dp(52), spacing=6
            )
            # 못 고르는 퍽은 회색(누를 수 없음)으로 이유와 함께 보인다
            버튼 = Button(
                text=f"{퍽이름} ({이유})" if 이유 else 퍽이름,
                size_hint=(0.72, 1),
                disabled=bool(이유),
                halign="center",
            )
            버튼.bind(
                size=lambda inst, size: setattr(
                    inst, "text_size", (size[0] - dp(8), None)
                )
            )
            버튼.bind(
                on_release=(
                    lambda inst, n=퍽이름, d=퍽정의: self._퍽_클릭(
                        캐릭터, n, d, 확인콜백, 팝업
                    )
                )
            )
            행.add_widget(버튼)
            상세 = Button(text="상세보기", font_size="14sp", size_hint=(0.28, 1))
            상세.bind(
                on_release=lambda inst, n=퍽이름, d=퍽정의: _스킬_상세_팝업(
                    n,
                    "\n\n".join(
                        f"[{제목}]\n{설명}" if 번호 else 설명
                        for 번호, (제목, 설명) in enumerate(
                            gameflow.퍽_상세(캐릭터, n, d)
                        )
                    ),
                    제목="퍽 상세보기",
                )
            )
            행.add_widget(상세)
            목록틀.add_widget(행)

        닫기버튼 = Button(text="취소", size_hint=(1, 0.1))
        뒤로키_버튼(닫기버튼)
        닫기버튼.bind(on_release=lambda *_: 팝업.dismiss())
        본문.add_widget(닫기버튼)

        팝업.open()

    def _퍽_클릭(self, 캐릭터, 퍽이름, 퍽정의, 확인콜백, 팝업):
        if gameflow.퍽_처리타입(퍽정의) == "스탯획득" and "획득스탯포인트" in 퍽정의:
            팝업.dismiss()
            self._능력치배분_팝업(
                캐릭터,
                퍽정의["획득스탯포인트"],
                확인콜백=lambda 배분: 확인콜백(
                    {"퍽이름": 퍽이름, "퍽정의": 퍽정의, "배분": 배분}
                ),
            )
            return

        if gameflow.특성선택_퍽인가(퍽정의):
            팝업.dismiss()
            self._특성선택_팝업(
                캐릭터,
                퍽이름,
                퍽정의,
                확인콜백=lambda 이름: 확인콜백(
                    {"퍽이름": 퍽이름, "퍽정의": 퍽정의, "선택특성": 이름}
                ),
            )
            return

        특성정의 = gameflow.퍽_특성정의_찾기(캐릭터, 퍽정의)
        팝업.dismiss()
        확인콜백({"퍽이름": 퍽이름, "퍽정의": 퍽정의, "특성정의": 특성정의})

    def _특성선택_팝업(self, 캐릭터, 퍽이름, 퍽정의, 확인콜백):
        """특성을 골라 얻는 퍽(포켓몬) - 아직 없는 특성마다 버튼(이름과 설명), 맨 아래 [취소]."""
        본문 = BoxLayout(orientation="vertical", spacing=8, padding=12)
        본문.add_widget(_줄바꿈_라벨("얻을 특성을 하나 고릅니다."))
        스크롤, 목록틀 = 스크롤_목록(1)
        본문.add_widget(스크롤)
        팝업 = Popup(
            title=f"{캐릭터['캐릭터명']} {퍽이름}",
            content=본문,
            size_hint=(0.9, 0.85),
            auto_dismiss=False,
        )

        def 고르기(이름):
            팝업.dismiss()
            확인콜백(이름)

        for 후보 in gameflow.퍽_선택특성_후보(캐릭터, 퍽정의):
            버튼 = Button(
                text=f"{후보['이름']}\n{후보['설명']}",
                size_hint=(1, None),
                height=dp(72),
                halign="center",
                font_size="13sp",
            )
            버튼.bind(
                size=lambda inst, sz: setattr(inst, "text_size", (sz[0] - 12, None))
            )
            버튼.bind(on_release=lambda inst, n=후보["이름"]: 고르기(n))
            목록틀.add_widget(버튼)
        취소 = Button(text="취소", size_hint=(1, None), height=dp(44))
        뒤로키_버튼(취소)
        취소.bind(on_release=lambda *_: 팝업.dismiss())
        본문.add_widget(취소)
        팝업.open()

    # -------------------------------------------------
    # 스킬습득 팝업 - 지금 직업 계열 스킬을 골드(50 x 차수)로 배운다
    # -------------------------------------------------

    def _스킬습득_팝업(self, 캐릭터):
        본문 = BoxLayout(orientation="vertical", spacing=8, padding=12)
        골드라벨 = Label(size_hint=(1, 0.1))
        본문.add_widget(골드라벨)

        스크롤, 목록틀 = 스크롤_목록(0.76)
        본문.add_widget(스크롤)

        팝업 = Popup(
            title=f"{캐릭터['캐릭터명']} 스킬습득",
            content=본문,
            size_hint=(0.9, 0.85),
            auto_dismiss=False,
        )

        def 다시그리기():
            게임상태 = App.get_running_app().게임상태
            골드 = gameflow.상점_보유골드(게임상태)
            골드라벨.text = f"보유 골드 {골드}"
            목록틀.clear_widgets()
            목록 = gameflow.캐릭터_습득가능_스킬(캐릭터)
            if not 목록:
                목록틀.add_widget(
                    Label(
                        text="(지금 배울 수 있는 스킬이 없습니다)",
                        size_hint=(1, None),
                        height=dp(40),
                    )
                )
            for 이름, 비용, 상세글 in 목록:
                # 한 줄: 스킬이름 / 가격(누르면 배운다) / 상세보기
                행 = BoxLayout(
                    orientation="horizontal",
                    size_hint=(1, None),
                    height=dp(44),
                    spacing=dp(6),
                )
                이름라벨 = Label(
                    text=이름,
                    font_size="15sp",
                    size_hint=(0.5, 1),
                    halign="left",
                    valign="middle",
                    shorten=True,
                    shorten_from="right",
                )
                이름라벨.bind(size=lambda inst, size: setattr(inst, "text_size", size))
                행.add_widget(이름라벨)
                가격버튼 = _평면버튼(
                    f"{비용}골드",
                    _강조색 if 골드 >= 비용 else (0.2, 0.21, 0.25, 1),
                    font_size="14sp",
                    size_hint=(0.25, 1),
                    disabled=골드 < 비용,
                    disabled_color=(0.45, 0.47, 0.52, 1),
                )
                가격버튼.bind(on_release=lambda inst, n=이름: 배우기(n))
                행.add_widget(가격버튼)
                상세버튼 = _평면버튼(
                    "상세보기",
                    (0.3, 0.31, 0.35, 1),
                    font_size="14sp",
                    size_hint=(0.25, 1),
                )
                상세버튼.bind(
                    on_release=lambda inst, n=이름, 글=상세글: _스킬_상세_팝업(n, 글)
                )
                행.add_widget(상세버튼)
                목록틀.add_widget(행)

        def 배우기(이름):
            게임상태 = App.get_running_app().게임상태
            try:
                비용 = gameflow.캐릭터_스킬_습득(게임상태, 캐릭터, 이름)
            except ValueError as 오류:
                self.안내라벨.text = str(오류)
                return
            self.안내라벨.text = (
                f"{캐릭터['캐릭터명']}이(가) {이름}을(를) 배웠습니다(-{비용}골드)."
            )
            다시그리기()

        다시그리기()
        닫기버튼 = 닫기_버튼(팝업, size_hint=(1, 0.1))
        본문.add_widget(닫기버튼)

        팝업.open()

    # -------------------------------------------------

    def _뒤로_클릭(self, *args):
        self.manager.current = self.복귀화면


# =====================================================
# 파티원 화면
# =====================================================
# 파티관리 [상세보기] -> 파티원 화면. 최상단 우측 버튼으로 두 탭을 바꾼다.
#   "장비와 스탯": 상단 장비창(던파식 - 왼쪽 방어구 5종, 가운데 캐릭터,
#                  오른쪽 무기/칭호/악세/특수장비, 칸을 누르면 교체) +
#                  하단 스탯창(레벨/HP/MP/능력치 6종, [상세보기] 팝업)
#   "스킬과 특성": 상단 하위 탭 [스킬][특성][퍽] + 하단 목록
# 칭호 칸은 캐릭터 장비 슬롯이 아직 없어 자리만 둔다(미구현, 누를 수 없음).


def _스킬_상세_팝업(이름, 상세글, 제목="스킬 상세보기"):
    글 = f"[b]{escape_markup(이름)}[/b]\n\n{escape_markup(상세글 or '(설명 없음)')}"
    본문 = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(10))
    스크롤 = ScrollView(size_hint=(1, 1))
    스크롤.add_widget(_줄바꿈_라벨(글, font_size="15sp", line_height=1.4))
    본문.add_widget(스크롤)
    닫기 = Button(text="닫기", size_hint=(1, None), height=dp(48))
    뒤로키_버튼(닫기)
    본문.add_widget(닫기)
    팝업 = Popup(title=제목, content=본문, size_hint=(0.9, 0.8))
    닫기.bind(on_release=lambda *_: 팝업.dismiss())
    팝업.open()


def _줄바꿈_라벨(글, **kwargs):
    """너비에 맞춰 줄바꿈하고 높이를 글 길이에 맞추는 라벨(스크롤 목록용)."""
    라벨 = Label(
        text=글, markup=True, size_hint_y=None, halign="left", valign="top", **kwargs
    )
    라벨.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
    라벨.bind(texture_size=lambda inst, ts: setattr(inst, "height", ts[1] + 10))
    return 라벨
