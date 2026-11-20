"""화면 스모크 공통 - 창 크기·밀도 설정, kivy/게임 import, 단계들이 같이 쓰는 도우미와 결과 표.

tools/ui_smoke.py가 맨 먼저 불러 kivy 창 설정을 마친다(창을 만들기 전에 정해야 한다).
단계는 주제별 모듈(party/town/battle/world/jobs/menu)의 믹스인 클래스에 있다.
"""

import re
import os
import pathlib
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.setdefault("KIVY_NO_ARGS", "1")

# 창 크기는 사용자 휴대폰(갤럭시 S24, 세로 1080x2340)에 맞춘다 - 창을 만들기 전에 정해야 한다.
# 화면 밀도도 S24 기본값(450dpi = 2.8125, 가로 384dp)으로 - dp/sp 크기가 폰과 같게 보인다
# (데스크톱 기본 밀도 1이면 글자가 폰보다 훨씬 작게 찍힌다).
os.environ.setdefault("KIVY_METRICS_DENSITY", "2.8125")
from kivy.config import Config  # noqa: E402

Config.set("graphics", "width", "1080")
Config.set("graphics", "height", "2340")
Config.set("graphics", "resizable", "0")

import main  # noqa: E402 - 크래시 로그 훅/폰트 등록 등 앱 초기화를 그대로 쓴다
from kivy.core.window import Window  # noqa: E402
from kivy.uix.button import Button  # noqa: E402
from kivy.uix.togglebutton import ToggleButton  # noqa: E402

import gameflow as gf  # noqa: E402
from game.system.combat import flow  # noqa: E402

_NPC그림폴더 = pathlib.Path(__file__).resolve().parents[2] / "game" / "assets" / "npc"
스크린샷폴더 = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "ui_smoke_shots")
결과 = {"단계": [], "오류": None}
전직 = {
    "귀검사": "웨펀마스터",
    "거너": "레인저",
    "마법사": "엘리멘탈마스터",
    "프리스트": "크루세이더",
}


def _글(t):
    """라벨 글에서 색/굵기 마크업을 뺀 글(아이템 이름은 레어도 색으로 칠해져 있다)."""
    return re.sub(r"\[/?(color|b|size)[^\]]*\]", "", t or "")


def _찍기(이름):
    os.makedirs(스크린샷폴더, exist_ok=True)
    Window.screenshot(name=os.path.join(스크린샷폴더, 이름 + ".png"))


def _스크롤_확인(스크롤, 이름):
    """목록이 화면보다 길고, 손가락으로 끌어 올리면 내려가며, 맨 아래 항목까지 보이는지.
    제너레이터 - 단계 안에서 yield from 으로 부른다."""
    from kivy.tests.common import UnitTestTouch

    내용 = 스크롤.children[0]
    assert 내용.height > 스크롤.height + 10, (이름, 내용.height, 스크롤.height)
    스크롤.scroll_y = 1
    yield 0.2
    x, y = 스크롤.to_window(스크롤.center_x, 스크롤.center_y)
    손 = UnitTestTouch(x, y - 스크롤.height * 0.3)
    손.touch_down()
    for i in range(1, 13):
        손.touch_move(x, y - 스크롤.height * 0.3 + i * 25)
    손.touch_up()
    yield 0.6
    assert 스크롤.scroll_y < 0.99, (이름, "끌어도 안 내려감", 스크롤.scroll_y)
    # 맨 아래로 옮긴다. scroll_y만 바꾸면 스크롤 효과(effect_y)가 들고 있는 위치값은 그대로
    # 남아, 효과가 다음에 갱신될 때 scroll_y를 그 값으로 되돌린다(관성이 남아 있을 때 실패가
    # 실행마다 달랐던 원인). 효과의 위치값을 맨 아래로 옮기면 scroll_y도 따라간다 - kivy는
    # scroll_y = -위치값 / (내용 높이 - 창 높이)라 맨 아래는 위치값 0이다.
    yield 1.5  # 끌고 난 뒤 관성 스크롤이 멈출 때까지
    스크롤.effect_y.velocity = 0  # 남은 관성 버리기(cancel은 남은 속도로 계속 움직인다)
    스크롤.effect_y.cancel()
    스크롤.effect_y.value = 0
    yield 0.8
    assert 스크롤.scroll_y == 0, (이름, "맨 아래로 못 옮김", 스크롤.scroll_y)
    마지막 = 내용.children[0]  # BoxLayout은 마지막에 넣은 위젯이 children[0]
    _, 아래 = 마지막.to_window(*마지막.pos)
    _, 바닥 = 스크롤.to_window(*스크롤.pos)
    assert 바닥 - 4 <= 아래 <= 바닥 + 스크롤.height, (이름, 아래, 바닥)


def _팝업_닫기():
    # 애니메이션 없이 바로 닫는다 - 닫히는 도중에 다음 팝업 개수를 세면 2개로 세어졌다
    for 위젯 in list(Window.children)[:-1]:
        if hasattr(위젯, "dismiss"):
            위젯.dismiss(animation=False)


def _뒤로키():
    """핸드폰 [뒤로] 키(27): 맨 위 팝업의 취소/닫기 -> 화면의 뒤로/나가기 순"""
    Window.dispatch("on_keyboard", 27, 0, None, [])


def _팝업수():
    return sum(hasattr(w, "dismiss") for w in Window.children)


def _대상버튼들():
    """떠 있는 팝업 하나(대상/아이템/행동 선택)의 버튼들"""
    assert _팝업수() == 1, _팝업수()
    return [w for w in Window.children[0].walk(restrict=True) if isinstance(w, Button)]


def _차례(전투상태, 이름):
    """그 참가자의 턴으로 맞춘다. 이름 없이 만든 캐릭터는 전직명이 되므로 1차 직업으로도 찾는다"""
    p = next(
        x
        for x in 전투상태["참가자"]
        if 이름 in (x["이름"], (x.get("원본") or {}).get("직업"))
    )
    전투상태["현재턴"] = 전투상태["참가자"].index(p)
    flow.턴_시작_처리(전투상태, p)
    return p


def _아군_차례로(상태):
    """전투 화면을 열기 전에, 선공이 적(조종 못 하는 차례)이면 살아 있는 첫 아군의 차례로 맞춘다.
    적 차례에 화면을 열면 갱신()이 0.4초 뒤 적 턴을 작업 스레드로 돌리는데(_자동진행), 스모크가 0.3초쯤
    기다린 뒤 상태를 바꾸면 느린 러너에서 그 적 턴과 겹쳐 반응 팝업이 남거나 종료 팝업이 꼬였다.
    누가 선공인지는 굴림이라 앞 단계의 난수 소비가 바뀌면 뒤집힌다 - 아군 차례면 그대로 둔다."""
    if gf.아군_차례인가(상태):
        return
    전투상태 = 상태["전투상태"]
    p = next(
        x
        for x in 전투상태["참가자"]
        if x["진영"] == "아군" and x["생존"] and not x.get("인형")
    )
    전투상태["현재턴"] = 전투상태["참가자"].index(p)
    flow.턴_시작_처리(전투상태, p)


def _팝업글():
    """떠 있는 팝업들의 글(마크업 뺀 것)"""
    return [
        _글(w.text)
        for 팝업 in list(Window.children)[:-1]
        for w in 팝업.walk(restrict=True)
        if hasattr(w, "text")
    ]


def _스킬줄_버튼들():
    """떠 있는 스킬 팝업의 줄 버튼들(screens_battle_popups._스킬_줄 - 버튼에 스킬이름이 붙어 있다)"""
    return [w for w in Window.children[0].walk(restrict=True) if hasattr(w, "스킬이름")]


def _스킬줄_칸(버튼):
    """줄 버튼 위에 겹친 글 칸 4개(이름 | 남은 횟수 | MP | 행동)"""
    칸틀 = [w for w in 버튼.parent.children if w is not 버튼][0]
    return list(reversed(칸틀.children))


def _스킬줄_글(버튼):
    return [칸.text for 칸 in _스킬줄_칸(버튼)]


def _팝업_버튼(글):
    return next(
        w
        for 팝업 in list(Window.children)[:-1]
        for w in 팝업.walk(restrict=True)
        if getattr(w, "text", None) == 글
    )


def _상점_탭들(상점):
    return [w for w in 상점.내용틀.walk(restrict=True) if isinstance(w, ToggleButton)]


def _상점_탭(상점, 글):
    return next(t for t in _상점_탭들(상점) if t.text == 글)


def _상점_목록이름(상점, 상태):
    """상점 목록에 보이는 현재 장비 탭의 아이템 이름"""
    return [
        _글(w.text)
        for w in 상점._목록틀.walk(restrict=True)
        if isinstance(w, main.Label)
        and not isinstance(w, Button)
        and _글(w.text) in 상태["상점카탈로그"]["장비"].get(상점._현재탭, {})
    ]


def _위젯_버튼(위젯, 글):
    return next(
        w
        for w in 위젯.walk(restrict=True)
        if isinstance(w, Button) and _글(w.text) == 글
    )


def _마을_메뉴_열기(매니저):
    _위젯_버튼(매니저.get_screen("마을"), "메뉴").trigger_action(duration=0)


def _확인_누르기():
    _팝업_버튼("확인").dispatch("on_release")
