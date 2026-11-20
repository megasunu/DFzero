# =====================
# Kivy 앱 진입점
# =====================
import os
import sys
import traceback
import datetime


# -----------------------------------------------------
# 임시 디버그용: 화면(Loading...)이 뜨자마자 바로 꺼지는 건, 앱이 아직
# Kivy 화면을 띄우기도 전 - 즉 아래 import/초기화 단계에서 예외가 나서
# 죽는 경우다. 이 시점의 예외는 Kivy의 ExceptionManager(이 파일 아래쪽)로는
# 못 잡는다(그건 화면이 뜬 다음, 이벤트 루프 안에서 난 예외만 잡음).
# 대신 파이썬이 처리 못 한 예외를 마지막에 항상 거치는 sys.excepthook을
# 덮어써서, 어떤 단계에서 죽든 오류 내용을 폰 Download 폴더에 파일로
# 남긴다. USB/adb 없이(회사 PC라 연결 불가) 원인을 확인하기 위한
# 안전장치이며, 원인이 확인되면 이 블록은 제거해도 된다.
def _크래시로그_저장(exc_type, exc_value, exc_tb):
    오류내용 = (
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        + "\n"
        + "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    )
    print(오류내용)
    try:
        저장경로 = "/storage/emulated/0/Download/dnf_crash_log.txt"
        with open(저장경로, "w", encoding="utf-8") as f:
            f.write(오류내용)
    except Exception:  # 크래시 처리 중이다 - 로그 저장 실패로 원래 오류를 가리지 않는다
        pass


sys.excepthook = _크래시로그_저장

from kivy.app import App
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import ScreenManager, NoTransition

# Kivy 기본 폰트(Roboto)에는 한글 글자가 없어서 화면에 네모(□)로 깨져
# 보이는 문제가 있다. 기기의 시스템 한글 폰트는 기기마다 경로가 달라
# 믿을 수 없으므로, 나눔고딕을 fontTools로 다이어트(힌팅/GSUB/GPOS/DSIG 등
# 렌더링에 불필요한 테이블만 제거, 글자 커버리지는 원본과 동일하게 유지)
# 시킨 단일 폰트 파일 하나(game/assets/font/NanumGothic-Diet.ttf, 약
# 1.3MB - 원본 나눔고딕 Regular 약 2.0MB 대비 축소)를 앱에 직접 담아
# "Roboto" 별칭을 덮어쓴다.
#
# 볼드체 파일은 따로 안 담았다 - fn_bold를 생략하면 Kivy가 볼드 스타일
# 텍스트에도 자동으로 fn_regular를 대신 쓴다(볼드 느낌은 안 나지만 글자는
# 정상 표시된다).
_폰트_경로 = os.path.join(
    os.path.dirname(__file__),
    "game",
    "assets",
    "font",
    "NanumGothic-Diet.ttf",
)
LabelBase.register(name="Roboto", fn_regular=_폰트_경로)

# -----------------------------------------------------
# 임시 디버그용: 버튼 클릭 등 이벤트 처리 중 예외가 나도 앱이 그냥
# 종료되지 않고, 오류 내용을 화면에 팝업으로 띄운다. USB/adb 없이도
# (회사 PC라 USB 연결이 안 되는 환경) 크래시 원인을 스크린샷으로
# 공유받기 위한 안전장치다 - 원인이 확인되면 이 블록은 제거해도 된다.
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.core.clipboard import Clipboard
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button


def _오류_팝업_띄우기(내용):
    라벨 = Label(
        text=내용,
        size_hint_y=None,
        halign="left",
        valign="top",
        font_size="11sp",
    )
    라벨.bind(
        texture_size=lambda inst, size: setattr(inst, "height", size[1]),
        width=lambda inst, w: setattr(inst, "text_size", (w, None)),
    )
    스크롤 = ScrollView()
    스크롤.add_widget(라벨)

    복사버튼 = Button(text="오류 내용 복사하기", size_hint=(1, 0.12))

    def _복사(*args):
        Clipboard.copy(내용)
        복사버튼.text = "복사됨! (대화창에 붙여넣기)"

    복사버튼.bind(on_release=_복사)

    본문 = BoxLayout(orientation="vertical", spacing=8)
    본문.add_widget(스크롤)
    본문.add_widget(복사버튼)

    Popup(
        title="오류 발생 - 아래 버튼으로 복사해서 공유해 주세요",
        content=본문,
        size_hint=(0.95, 0.9),
    ).open()


class _오류처리기(ExceptionHandler):
    def handle_exception(self, inst):
        내용 = "".join(traceback.format_exception(type(inst), inst, inst.__traceback__))
        print(내용)
        try:
            _오류_팝업_띄우기(내용)
        except Exception:  # 오류 팝업이 또 실패해도 원래 오류 처리는 계속한다
            pass
        return ExceptionManager.PASS


ExceptionManager.add_handler(_오류처리기())

# 화면은 game/screens/ 아래 7개 파일로 나뉘어 있다.
from game.screens.screens_menu import (
    메인메뉴화면,
    파티생성화면,
    불러오기목록화면,
    저장목록화면,
    설정화면,
)
from game.screens.screens_town import (
    마을화면,
    마을이동목록화면,
    모험단화면,
    주점화면,
)
from game.screens.screens_shop import 상점화면, 소지품화면, 전문직업화면
from game.screens.screens_dungeon import 던전목록화면, 던전화면
from game.screens.screens_battle import 전투화면
from game.screens.screens_party import 파티관리화면
from game.screens.screens_member import 파티원화면
from game.screens.screens_collection import 도감화면, 업적화면
from game.screens.screens_common import 뒤로키_처리, 기준화면틀
import gameflow


class DnfMobileApp(App):
    title = "던전앤파이터 모바일 프로토타입"

    def _세이브_폴더_준비(self):
        """세이브를 앱 소스 폴더(업데이트하면 사라질 수 있다) 대신 앱 데이터 폴더에 둔다.
        옛 위치의 세이브는 처음 한 번 복사해 온다. 폴더를 못 만들면 옛 위치를 그대로 쓴다."""
        try:
            가져옴 = gameflow.세이브_폴더_설정(
                os.path.join(self.user_data_dir, "saves")
            )
            if 가져옴:
                print("옛 세이브를 가져왔다:", ", ".join(가져옴))
        except OSError as 오류:
            print("세이브 폴더를 앱 데이터 폴더로 옮기지 못했다:", 오류)

    def build(self):
        self._세이브_폴더_준비()
        self.게임상태 = None

        매니저 = ScreenManager(transition=NoTransition())
        매니저.add_widget(메인메뉴화면(name="메인메뉴"))
        매니저.add_widget(파티생성화면(name="파티생성"))
        매니저.add_widget(불러오기목록화면(name="불러오기목록"))
        매니저.add_widget(저장목록화면(name="저장목록"))
        매니저.add_widget(설정화면(name="설정"))
        매니저.add_widget(마을화면(name="마을"))
        매니저.add_widget(마을이동목록화면(name="마을이동목록"))
        매니저.add_widget(파티관리화면(name="파티관리"))
        매니저.add_widget(파티원화면(name="파티원"))
        매니저.add_widget(던전목록화면(name="던전목록"))
        매니저.add_widget(던전화면(name="던전"))
        매니저.add_widget(상점화면(name="상점"))
        매니저.add_widget(소지품화면(name="소지품"))
        매니저.add_widget(전문직업화면(name="전문직업"))
        매니저.add_widget(전투화면(name="전투"))
        매니저.add_widget(모험단화면(name="모험단"))
        매니저.add_widget(주점화면(name="주점"))
        매니저.add_widget(도감화면(name="도감"))
        매니저.add_widget(업적화면(name="업적"))
        매니저.current = "메인메뉴"
        self.매니저 = 매니저
        # 핸드폰 [뒤로] 키 - 앱을 최소화하지 않고 취소/닫기/뒤로로 쓴다.
        from kivy.core.window import Window

        Window.bind(on_keyboard=뒤로키_처리)
        # 화면은 1080x2340 기준 화면 안에 그리고, 비율이 다른 기기에서는 검정 여백을 둔다.
        틀 = 기준화면틀(매니저)
        Window.bind(children=틀.팝업_맞추기)
        return 틀


if __name__ == "__main__":
    DnfMobileApp().run()
