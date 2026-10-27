"""화면 스모크 테스트 - 실제 Kivy 앱을 띄워 주요 화면 동작을 호출하고 스크린샷을 남긴다.

    pip install kivy                       # 한 번
    xvfb-run -a -s "-screen 0 1080x2340x24" python tools/ui_smoke.py [스크린샷폴더]  # 리눅스(화면 없음)
    python tools/ui_smoke.py [스크린샷폴더]                                        # Windows/맥(창이 뜬다)

tests/는 kivy 없이 gameflow 이하만 검사한다. 화면(game/screens) 코드를 바꿨다면 이것을
돌려 확인한다(CLAUDE.md 완료 기준 3). 레벨 10 파티를 만들어 다음을 실제로 호출한다:
파티 구성 이름칸(6자 제한), 상점 구매/판매 목록, 능력치 배분 팝업, 장비 교체 팝업/상세보기, 파티원 포션/주류 사용(취기 표시), 뒤로 키, 전투 화면 스킬 팝업과 스킬별 실제 타겟(4직업 전 스킬),
적 대상 선택 팝업(일반공격, 취소), 전투 [아이템] 포션/버프포션/소환 아이템/주류(보조행동), 만취 아군 자동 행동, 적반복지정(썬더콜링) 선택 - 은신 대상 거부 포함, 행동 선택 팝업(쇼타임행동/일반행동), 도망(구속이면 막힘 팝업, 실패하면 턴 종료),
전투 종료 팝업(승리 전리품/없음, 도망, 패배)과 전투 보상(3칸 선택/빈칸 포기), 자동전투(켜기/중지/끝까지), 몬스터 크기 배율, 적 도망(황금 고블린),
기준 화면 틀(비율이 다른 창에서 검정 여백/터치/팝업 크기).
예외가 나면 종료코드 1.
스크린샷 기본 폴더: ui_smoke_shots/ (.gitignore에 들어 있다).
"""

import json
import re
import os
import shutil
import sys
import tempfile
import traceback
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
from kivy.animation import Animation  # noqa: E402
from kivy.app import App  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.uix.button import Button  # noqa: E402
from kivy.uix.label import Label  # noqa: E402
from kivy.metrics import dp  # noqa: E402
from kivy.uix.scrollview import ScrollView  # noqa: E402
from kivy.uix.togglebutton import ToggleButton  # noqa: E402

import gameflow as gf  # noqa: E402
from game.screens import screens_common, screens_party  # noqa: E402
from game.system import rng  # noqa: E402
from game.system import save_system, skill_system  # noqa: E402
from game.system.combat import flow  # noqa: E402
from tests import support  # noqa: E402

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
    기다린 뒤 상태를 바꾸면 느린 러너에서 그 적 턴과 겹쳐 반응 팝업이 남거나 종료 팝업이 꼬였다(#179).
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
    """떠 있는 스킬 팝업의 줄 버튼들(screens_battle._스킬_줄 - 버튼에 스킬이름이 붙어 있다)"""
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


def _확인_누르기():
    _팝업_버튼("확인").dispatch("on_release")


class 스모크앱(main.DnfMobileApp):
    def _세이브_폴더_준비(self):
        pass  # 이 스모크는 세이브를 임시 폴더로 바꿔서 쓴다(실제 앱 데이터 폴더를 건드리지 않는다)

    def on_start(self):
        self._단계 = self._단계들()
        Clock.schedule_once(self._다음, 1)

    def _다음(self, _dt):
        try:
            Clock.schedule_once(
                lambda _: self._애니메이션_기다리기(0), next(self._단계)
            )  # 단계 사이에 화면을 그리게 기다린다
        except StopIteration:
            self.stop()
        except Exception:  # noqa: BLE001
            결과["오류"] = traceback.format_exc()
            self.stop()

    def _애니메이션_기다리기(self, 기다린):
        """정해진 시간이 지나도 팝업 열기/닫기 애니메이션(kivy ModalView의 페이드)이 아직 돌면 끝날 때까지
        0.05초씩 더 기다린 뒤 다음 단계로(최대 5초). 느린 러너(CI Python 3.11)에서는 0.1초짜리 페이드가
        0.3초 뒤에도 안 끝나 닫히는 팝업이 남아 팝업 수를 2로 셌다(#231)."""
        if Animation._instances and 기다린 < 5:
            Clock.schedule_once(
                lambda _: self._애니메이션_기다리기(기다린 + 0.05), 0.05
            )
            return
        self._다음(0)

    def _단계들(self):
        rng.시드(
            0
        )  # 난수 흐름 분리(2026-10-20) 뒤 3은 행동 선택 단계에서 팝업이 남는다
        상태 = support.새게임(
            [("", "귀검사"), ("", "거너"), ("", "마법사"), ("", "프리스트")]
        )
        for c in 상태["파티"]["파티원"]:
            support.성장(상태, c, 10, 전직=전직[c["직업"]])
        gf.파티_최대치로_회복(상태)
        self.게임상태 = 상태
        매니저 = self.매니저

        yield from self._단계_파티생성(상태, 매니저)
        yield from self._단계_상점(상태, 매니저)
        yield from self._단계_파티관리_팝업(상태, 매니저)
        yield from self._단계_반응스킬_표시(상태, 매니저)
        전투 = yield from self._단계_장비_포션_뒤로키_전투팝업(상태, 매니저)
        yield from self._단계_전투종료_자동전투_주점(상태, 매니저, 전투)
        yield from self._단계_맵_타일(상태, 매니저)
        yield from self._단계_출입구_위(상태, 매니저)
        yield from self._단계_목록_스크롤(상태, 매니저)
        yield from self._단계_세이브(상태, 매니저)
        yield from self._단계_설정(매니저)
        yield from self._단계_화면_배치(상태, 매니저)
        yield from self._단계_던전목록(상태, 매니저)
        yield from self._단계_던전_스킬(상태, 매니저)
        yield from self._단계_마을_전환스킬(상태, 매니저)
        yield from self._단계_화면_틀(매니저)
        yield from self._단계_공격연출(상태, 매니저)
        yield from self._단계_감옥_대상팝업(상태, 매니저)
        yield from self._단계_프렌드_실드(상태, 매니저)
        yield from self._단계_인형(상태, 매니저)
        yield from self._단계_란마(상태, 매니저)
        yield from self._단계_축염포(상태, 매니저)
        yield from self._단계_연계_팝업(매니저)
        yield from self._단계_넨가드_채널링(매니저)
        yield from self._단계_합격(상태, 매니저)
        yield from self._단계_소지품(상태, 매니저)
        yield from self._단계_레테(상태, 매니저)
        yield from self._단계_도감_업적(상태, 매니저)
        yield from self._단계_메뉴(상태, 매니저)

    def _단계_파티생성(self, 상태, 매니저):
        """파티 구성 화면 - 이름칸(안내/글자 수 제한)과 이름 중복"""
        매니저.current = "파티생성"
        # 처음엔 네 칸 모두 참여, 직업은 귀검사/격투가/거너/마법사
        슬롯들 = 매니저.get_screen("파티생성").슬롯목록
        assert [s["직업스피너"].text for s in 슬롯들] == [
            "귀검사",
            "격투가",
            "거너",
            "마법사",
        ]
        assert all(s["참여토글"].state == "down" for s in 슬롯들[1:])
        assert all(not s["이름입력"].disabled for s in 슬롯들)
        이름칸 = 슬롯들[0]["이름입력"]
        assert 이름칸.hint_text == gf.캐릭터명_안내, 이름칸.hint_text
        yield 0.5
        _찍기("party_create_hint")
        이름칸.text = "가나다라마바사아"
        assert 이름칸.text == "가나다라마바", 이름칸.text
        이름칸.text = "abcdefghijklmnop"
        assert 이름칸.text == "abcdefghijkl", 이름칸.text
        이름칸.text = "가나다라마바"
        yield 0.3
        _찍기("party_create_name6")
        결과["단계"].append(
            "파티 구성 기본값(4명 참여, 귀검사/격투가/거너/마법사) + 이름칸(안내 문구, 한글 6자/영문 12자 제한)"
        )

        # 이름이 겹치면 시작하지 않고 안내 줄에 알린다(B4)
        파티생성 = 매니저.get_screen("파티생성")
        파티생성.슬롯목록[1]["참여토글"].state = "down"
        파티생성.슬롯목록[0]["이름입력"].text = "철수"
        파티생성.슬롯목록[1]["이름입력"].text = "철수"
        이전상태 = self.게임상태
        파티생성._시작()
        assert 매니저.current == "파티생성", 매니저.current
        assert "겹칩니다" in 파티생성.안내라벨.text, 파티생성.안내라벨.text
        assert self.게임상태 is 이전상태
        yield 0.3
        _찍기("party_create_duplicate")
        결과["단계"].append("파티 구성 이름 중복 -> 시작 안 함")
        yield from self._단계_스탯고르기(매니저)

    def _단계_스탯고르기(self, 매니저):
        """파티 구성 - 능력치 칸 터치로 주/보조/약점스탯 고르기(테두리 색, 점수 바로 반영)"""
        from game.screens.screens_common import 스탯역할_테두리색

        파티생성 = 매니저.get_screen("파티생성")
        for 남은슬롯 in 파티생성.슬롯목록:  # 앞 단계의 겹치는 이름("철수")을 지운다
            남은슬롯["이름입력"].text = ""
        슬롯 = 파티생성.슬롯목록[0]  # 귀검사: 주 근력 / 보조 민첩 / 약점 지능
        판 = 슬롯["능력치판"]

        def 칸(이름):
            return 판.칸[이름]

        assert tuple(칸("근력")._테두리색.rgba) == 스탯역할_테두리색["주스탯"]
        assert tuple(칸("민첩")._테두리색.rgba) == 스탯역할_테두리색["보조스탯"]
        assert tuple(칸("지능")._테두리색.rgba) == 스탯역할_테두리색["약점스탯"]
        assert tuple(칸("매력")._테두리색.rgba) == 스탯역할_테두리색["일반"]
        assert 칸("근력").text.endswith(" 14"), 칸("근력").text  # 13 + 귀수 1
        # 근력(주) 터치 -> 보조는 민첩이 가짐 -> 일반(10 + 귀수 1)
        칸("근력").dispatch("on_release")
        assert 슬롯["스탯구성"]["주스탯"] is None
        assert 칸("근력").text.endswith(" 11"), 칸("근력").text
        assert tuple(칸("근력")._테두리색.rgba) == 스탯역할_테두리색["일반"]
        # 덜 고르면 시작 안 함
        이전상태 = self.게임상태
        파티생성._시작()
        assert 매니저.current == "파티생성" and self.게임상태 is 이전상태
        assert "모두 골라" in 파티생성.안내라벨.text, 파티생성.안내라벨.text
        # 매력(일반) 터치 -> 약점은 지능이 가짐 -> 비어 있는 주
        칸("매력").dispatch("on_release")
        assert 슬롯["스탯구성"]["주스탯"] == "매력"
        assert 칸("매력").text.endswith(" 13"), 칸("매력").text
        assert tuple(칸("매력")._테두리색.rgba) == 스탯역할_테두리색["주스탯"]
        yield 0.3
        _찍기("party_create_stat_pick")
        # 직업을 바꾸면 그 직업 기본값으로 돌아간다
        슬롯["직업스피너"].text = "격투가"
        assert 슬롯["스탯구성"] == gf.기본_스탯구성("격투가")
        슬롯["직업스피너"].text = "귀검사"
        결과["단계"].append(
            "파티 구성 스탯 고르기(터치 순서·건너뛰기, 테두리 색, 점수 반영, 덜 고르면 시작 안 함)"
        )

    def _단계_상점(self, 상태, 매니저):
        """상점 - 구매/판매 목록, [전문직업] 장비해체(일괄해체 확인 팝업)와 봉인해제/봉인변환, 인형사"""
        yield from self._단계_상점_구매판매(상태, 매니저)
        yield from self._단계_상점_해체(상태, 매니저)
        yield from self._단계_봉인(상태, 매니저)
        yield from self._단계_인형사(상태, 매니저)

    def _단계_상점_구매판매(self, 상태, 매니저):
        """상점 구매 - 레어도 색, 장비 탭 2줄, 무기 직업군/종류 탭, 방어구 재질 탭, 판매 목록"""
        매니저.current = "상점"
        상점 = 매니저.get_screen("상점")
        상점._대분류_그리기("구매")
        상점._탭목록_그리기("구매", "장비")
        yield 0.5
        _찍기("shop_buy")
        from kivy.uix.togglebutton import ToggleButton

        def 탭들():
            return [
                w
                for w in 상점.내용틀.walk(restrict=True)
                if isinstance(w, ToggleButton)
            ]

        def 탭(글):
            return next(t for t in 탭들() if t.text == 글)

        def 목록이름():
            return [
                _글(w.text)
                for w in 상점._목록틀.walk(restrict=True)
                if isinstance(w, main.Label)
                and not isinstance(w, Button)
                and _글(w.text) in 상태["상점카탈로그"]["장비"].get(상점._현재탭, {})
            ]

        # 아이템 이름은 레어도 색: 언커먼 파랑, 치트는 글자마다 무지개
        이름글 = {
            _글(w.text): w.text
            for w in 상점._목록틀.walk(restrict=True)
            if isinstance(w, main.Label) and not isinstance(w, Button)
        }
        for 이름, 글 in 이름글.items():
            분류 = gf.아이템_찾기(상태, 이름) and gf.아이템_색분류(
                gf.아이템_찾기(상태, 이름)
            )
            if 분류 == "치트":
                assert 글.count("[color=") == len(이름.replace(" ", "")), 글
            elif 분류:
                assert 글.startswith(f"[color={screens_common._레어도_색[분류]}]"), 글
        assert screens_common.아이템_이름_글(
            gf.아이템_찾기(상태, "강철 소검")
        ).startswith("[color=4d8cff]")
        # 레전더리는 주황, 크로니클은 빨강(지금 데이터엔 없는 등급 - 표만 확인)
        for 레어도, 색 in (("레전더리", "ff9a2e"), ("크로니클", "ff4040")):
            assert screens_common.아이템_이름_글(
                {"이름": "가상", "레어도": 레어도}
            ).startswith(f"[color={색}]")
        # 부위 탭 2줄이 화면 안에 다 들어간다(밀어서 넘기지 않음)
        부위 = [t for t in 탭들() if t.group == 탭("무기").group]
        assert [t.text for t in 부위] == sum(gf.상점_탭줄("구매", "장비"), [])
        assert all(
            상점.내용틀.x - 1 <= t.x and t.right <= 상점.내용틀.right + 1 for t in 부위
        )
        assert len({t.y for t in 부위}) == 2  # 두 줄
        # 머리줄/뒤로 줄/탭/안내줄은 글자 높이에 맞춘 높이
        sc = screens_common
        assert all(abs(t.height - sc.글자_높이("14sp")) < 1 for t in 부위)
        뒤로 = next(
            w
            for w in 상점.내용틀.walk(restrict=True)
            if isinstance(w, Button) and w.text == "◀ 뒤로"
        )
        assert abs(뒤로.parent.height - sc.글자_높이()) < 1, 뒤로.parent.height
        assert abs(상점.골드라벨.parent.height - sc.글자_높이("20sp")) < 1
        assert abs(상점.안내라벨.height - sc.글자_높이()) < 1
        # 무기: 직업군 탭 -> 거너를 누르면 종류 탭 줄이 생기고 목록은 거너 무기만
        assert [t.text for t in 탭들() if t.text in gf.상점_무기_직업군탭(상태)][
            :6
        ] == gf.상점_무기_직업군탭(상태)
        탭("거너").trigger_action(duration=0)
        yield 0.3
        종류 = gf.상점_무기_종류탭(상태, "거너")
        assert all(any(t.text == k for t in 탭들()) for k in 종류[1:]), [
            t.text for t in 탭들()
        ]
        무기 = 상태["상점카탈로그"]["장비"]["무기"]
        이름들 = 목록이름()
        assert 이름들 and all(무기[n]["분류"] == "거너 무기" for n in 이름들), 이름들
        탭(종류[1]).trigger_action(duration=0)
        yield 0.3
        assert all(
            gf.상점_분류_일치("무기", 무기[n], None, 종류[1]) for n in 목록이름()
        ), 목록이름()
        _찍기("shop_buy_weapon_gunner")
        # 방어구: 재질 탭
        탭("상의").trigger_action(duration=0)
        yield 0.3
        탭("판금").trigger_action(duration=0)
        yield 0.3
        세트글 = [
            w.text
            for w in 상점._목록틀.walk(restrict=True)
            if isinstance(w, main.Label) and _글(w.text) == "티타늄 흉갑"
        ]
        assert 세트글 and 세트글[0].startswith("[color=4dd65a]"), (
            세트글
        )  # 커먼 방어구 세트 = 초록
        상의 = 상태["상점카탈로그"]["장비"]["상의"]
        assert all(상의[n]["재질"] == "판금" for n in 목록이름()), 목록이름()
        _찍기("shop_buy_top_plate")
        결과["단계"].append(
            "상점 장비 탭 2줄(한 화면) + 무기 직업군->종류 탭 + 방어구 재질 탭"
        )
        상점._탭목록_그리기("판매", "장비")
        yield 0.5
        assert len({t.y for t in 탭들() if t.group == 탭("무기").group}) == 2
        _찍기("shop_sell")
        결과["단계"].append("상점 구매/판매 목록")

    def _단계_상점_해체(self, 상태, 매니저):
        """[전문직업] 장비해체(상점에서 옮김) - 장비 -> 소울/큐브 조각, [전체] 탭, 일괄해체 확인 팝업"""
        매니저.get_screen("상점")._메인_그리기()
        assert not any(
            getattr(w, "text", "") == "해체"
            for w in 매니저.get_screen("상점").내용틀.walk(restrict=True)
        ), "상점에는 해체가 없다(전문직업으로 옮김)"
        매니저.current = "전문직업"
        yield 0.3
        상점 = 매니저.get_screen("전문직업")
        메뉴글 = [
            (w.text, w.disabled)
            for w in 상점.내용틀.walk(restrict=True)
            if isinstance(w, Button)
        ]
        assert 메뉴글[:6] == [
            ("장비강화 (미구현)", True),
            ("장비해체", False),
            ("마법부여 (미구현)", True),
            ("봉인해제", False),
            ("봉인변환", False),
            ("인형사", False),
        ], 메뉴글
        _찍기("profession_menu")
        # 장비해체: 장비 목록에서 해체하면 소울/큐브 조각이 재료로
        next(
            w
            for w in 상점.내용틀.walk(restrict=True)
            if isinstance(w, Button) and w.text == "장비해체"
        ).dispatch("on_release")
        yield 0.3
        상태["소지품"]["장비"]["찢어진 천갑 상의"] = (
            상태["소지품"]["장비"].get("찢어진 천갑 상의", 0) + 1
        )
        상점._탭목록_그리기("해체", "장비")
        탭 = next(
            w
            for w in 상점.내용틀.walk(restrict=True)
            if isinstance(w, Button) and w.text == "상의"
        )
        탭.dispatch("on_release")
        yield 0.3
        _찍기("shop_dismantle")
        해체버튼 = next(
            w
            for w in 상점.내용틀.walk(restrict=True)
            if isinstance(w, Button) and w.text == "해체"
        )
        소울전 = 상태["소지품"]["재료"].get("커먼 소울", 0)
        해체버튼.dispatch("on_release")
        yield 0.3
        assert "해체" in 상점.안내라벨.text and "커먼 소울" in 상점.안내라벨.text, (
            상점.안내라벨.text
        )
        assert 상태["소지품"]["재료"]["커먼 소울"] == 소울전 + 1
        _찍기("shop_dismantle_after")

        # [전체] 탭이 맨 앞, 일괄해체 기본 범위는 커먼 / 전체
        탭글 = [
            w.text
            for w in 상점.내용틀.walk(restrict=True)
            if isinstance(w, Button) and w.text in gf.상점_해체_탭목록
        ]
        assert 탭글[0] == "전체", 탭글
        assert (상점.일괄등급.text, 상점.일괄부위.text) == ("커먼", "전체")
        for 이름 in ("찢어진 천갑 하의", "조잡한 반지"):
            상태["소지품"]["장비"][이름] = 상태["소지품"]["장비"].get(이름, 0) + 1
        일괄 = next(
            w
            for w in 상점.내용틀.walk(restrict=True)
            if isinstance(w, Button) and w.text == "일괄해체"
        )
        일괄.dispatch("on_release")
        yield 0.5
        팝업 = list(Window.children)[0]
        assert 팝업.title == "일괄해체", 팝업
        _찍기("shop_dismantle_batch_confirm")
        next(
            w
            for w in 팝업.walk(restrict=True)
            if isinstance(w, Button) and w.text == "해체"
        ).dispatch("on_release")
        yield 0.3
        assert "해체:" in 상점.안내라벨.text and "커먼 소울" in 상점.안내라벨.text, (
            상점.안내라벨.text
        )
        assert not gf.상점_일괄해체_대상(상태, "커먼", "전체")
        _찍기("shop_dismantle_batch_after")
        결과["단계"].append(
            "전문직업 메뉴 6개(장비강화/마법부여 미구현), 상점에 해체 없음, "
            "장비해체(장비 -> 소울 + 큐브 조각, [전체] 탭, 일괄해체 커먼/전체 확인 팝업)"
        )

    def _단계_봉인(self, 상태, 매니저):
        """[전문직업] 봉인해제(소지품 + 장착 중) -> 마법의 장비, 봉인변환 -> 다른 능력, 돈/소울 부족"""
        화면 = 매니저.get_screen("전문직업")
        소지품 = 상태["소지품"]
        귀검사 = 상태["파티"]["파티원"][0]
        소지품["장비"]["마법으로 봉인된 소검"] = 2
        gf.장비_교체(상태, 귀검사, "무기", "마법으로 봉인된 소검")
        소지품["골드"] = 1000
        소지품["재료"]["레어 소울"] = 3

        def 실행버튼들(글):
            return [
                w
                for w in 화면._목록틀.walk(restrict=True)
                if isinstance(w, Button) and w.text == 글
            ]

        화면._메인_그리기()
        next(
            w
            for w in 화면.내용틀.walk(restrict=True)
            if isinstance(w, Button) and w.text == "봉인해제"
        ).dispatch("on_release")
        yield 0.3
        assert len(실행버튼들("봉인해제")) == 2  # 착용 1줄 + 소지품 1줄
        _찍기("profession_unseal_list")
        실행버튼들("봉인해제")[0].dispatch("on_release")  # 착용 중인 것
        yield 0.3
        새무기 = 귀검사["장착장비"]["무기"]
        assert 새무기.startswith("마법의 ") and 새무기.endswith(" 소검"), 새무기
        assert 새무기 in 화면.안내라벨.text, 화면.안내라벨.text
        assert (소지품["골드"], 소지품["재료"]["레어 소울"]) == (900, 2)
        _찍기("profession_unseal_done")

        # 봉인변환: 착용 중인 마법의 무기 -> 다른 능력
        화면._봉인_그리기("봉인변환")
        yield 0.3
        _찍기("profession_convert_list")
        실행버튼들("봉인변환")[0].dispatch("on_release")
        yield 0.3
        assert 귀검사["장착장비"]["무기"] not in (새무기, "마법으로 봉인된 소검")
        assert 귀검사["장착장비"]["무기"].endswith(" 소검")
        _찍기("profession_convert_done")

        # 레어 소울이 모자라면 바뀌지 않고 안내
        소지품["재료"].pop("레어 소울", None)
        화면._봉인_그리기("봉인해제")
        yield 0.3
        실행버튼들("봉인해제")[0].dispatch("on_release")
        yield 0.3
        assert "레어 소울" in 화면.안내라벨.text, 화면.안내라벨.text
        assert 소지품["장비"]["마법으로 봉인된 소검"] == 1
        화면._나가기()
        yield 0.3
        결과["단계"].append(
            "봉인해제(착용 중인 무기 -> 마법의 무기, 100G/레어 소울), 봉인변환(다른 능력), 소울 부족 안내"
        )

    def _단계_인형사(self, 상태, 매니저):
        """[전문직업] 인형사 - 인형제작 창(재료 보유/필요, 모자라면 [제작] 못 누름), [상세보기]
        (이름/HP·AC 수식/능력치/보너스/패턴 6개), [제작] -> 소지품 소모품 + 도감 "인형" """

        def 버튼(위젯, 글):
            return next(
                w
                for w in 위젯.walk(restrict=True)
                if isinstance(w, Button) and w.text == 글
            )

        def 팝업():
            return Window.children[0]

        매니저.current = "전문직업"
        yield 0.3
        화면 = 매니저.get_screen("전문직업")
        소지품 = 상태["소지품"]
        소지품["재료"].pop("레어 소울", None)
        화면._메인_그리기()
        버튼(화면.내용틀, "인형사").dispatch("on_release")
        yield 0.3
        행 = next(
            w.parent
            for w in 화면._목록틀.walk(restrict=True)
            if isinstance(w, Label) and w.text.startswith("28호")
        )
        assert "레어 소울 0/10" in 행.children[-1].text, 행.children[-1].text
        assert 버튼(행, "제작").disabled, "재료가 모자라면 제작 못 누름"
        _찍기("profession_doll_list_short")

        버튼(행, "상세보기").dispatch("on_release")
        yield 0.3
        assert 팝업().title == "28호"
        줄들 = [w.text for w in 팝업().walk(restrict=True) if isinstance(w, Label)]
        for 글 in (
            "이름: 28호",
            "직업스타일: 캐스터",
            "AC = 14 + 민첩보정",
            "무기: 세련된 너클 (바꿀 수 없음)",
            "6. 넨가드",
        ):
            assert 글 in 줄들, 줄들
        assert any(줄.startswith("HP = (6 + 건강보정)") for 줄 in 줄들), 줄들
        _찍기("profession_doll_detail")
        _팝업_닫기()
        yield 0.3

        소지품["재료"]["레어 소울"] = 10
        보유전 = 소지품["소모품"].get("28호", 0)
        화면._인형사_그리기()
        yield 0.3
        행 = next(
            w.parent
            for w in 화면._목록틀.walk(restrict=True)
            if isinstance(w, Label) and w.text.startswith("28호")
        )
        assert not 버튼(행, "제작").disabled
        버튼(행, "제작").dispatch("on_release")
        yield 0.3
        assert 소지품["소모품"]["28호"] == 보유전 + 1
        assert "레어 소울" not in 소지품["재료"]
        assert "28호" in 상태["진행도"]["도감"]["인형"]
        assert "28호" in 화면.안내라벨.text, 화면.안내라벨.text
        _찍기("profession_doll_crafted")
        소지품["소모품"]["28호"] -= 1  # 다음 단계(전투 [아이템])가 개수를 직접 둔다
        if not 소지품["소모품"]["28호"]:
            del 소지품["소모품"]["28호"]
        화면._나가기()
        yield 0.3
        결과["단계"].append(
            "인형사: 인형제작 창(레어 소울 0/10이면 제작 못 누름), 상세보기(직업스타일/수식/인형무기/패턴 6개), "
            "제작 -> 소지품 1개 + 도감 인형"
        )

    def _단계_파티관리_팝업(self, 상태, 매니저):
        """파티관리 - 능력치 배분, 스킬강화, 스킬습득 팝업"""
        매니저.current = "파티관리"
        매니저.get_screen("파티관리")._능력치배분_팝업(
            상태["파티"]["파티원"][0], 2, lambda 배분: None
        )
        yield 0.5
        _찍기("stat_popup")
        _팝업_닫기()
        결과["단계"].append("능력치 배분 팝업")

        # 전직 선택 팝업(레벨 5): 1차 전직이 전부 구현돼 모든 버튼을 누를 수 있다.
        # 따로 만든 게임에서 키우고 난수 상태를 되돌려 뒤 단계에 영향을 주지 않는다
        난수 = rng.상태()
        전직상태 = support.새게임([("", "귀검사")])
        전직귀검 = 전직상태["파티"]["파티원"][0]
        support.성장(전직상태, 전직귀검, 5)
        rng.상태_복원(난수)
        매니저.get_screen("파티관리")._전직선택_팝업(전직귀검)
        yield 0.5
        팝업 = Window.children[0]
        assert 팝업.title == "전직 선택"
        전직버튼 = [
            w
            for w in 팝업.walk(restrict=True)
            if isinstance(w, Button) and w.text in gf.전직_레지스트리["귀검사"]
        ]
        assert [b.text for b in 전직버튼] == list(gf.전직_레지스트리["귀검사"])
        assert len(전직버튼) == 5 and not any(b.disabled for b in 전직버튼)
        # 전직마다 추천 주/보조/약점 한 줄(#420)
        글들 = {w.text for w in 팝업.walk(restrict=True) if isinstance(w, Label)}
        for 전직 in gf.전직_레지스트리["귀검사"]:
            assert gf.전직_추천_문구(전직) in 글들, 전직
        _찍기("advancement_popup")
        _팝업_닫기()
        yield 0.3
        결과["단계"].append(
            "전직 선택 팝업(귀검사 전직 5개 모두 선택 가능, 추천 능력치 표시)"
        )

        # 격투가 전직(#403): 넨마스터를 누르면 능력치 다시 고르기 팝업이 뜬다
        # (전에는 표에 없어 전직_기본_스탯구성의 KeyError로 멈췄다 - 지금은 표에 있다, #420)
        난수 = rng.상태()
        전직상태 = support.새게임([("", "격투가")])
        전직격 = 전직상태["파티"]["파티원"][0]
        support.성장(전직상태, 전직격, 5)
        rng.상태_복원(난수)
        매니저.get_screen("파티관리")._전직선택_팝업(전직격)
        yield 0.5
        넨버튼 = next(
            w
            for w in Window.children[0].walk(restrict=True)
            if isinstance(w, Button) and w.text == "넨마스터"
        )
        넨버튼.dispatch("on_release")
        yield 0.5
        assert Window.children[0].title == "넨마스터 - 능력치 다시 고르기"
        _찍기("advancement_stat_popup")
        _팝업_닫기()
        yield 0.3
        assert (
            전직격.get("전직") is None and 전직격["레벨"] == 5
        )  # 닫으면 전직하지 않는다
        결과["단계"].append("격투가 전직(넨마스터)의 능력치 다시 고르기 팝업")

        # 마스터리 선택 팝업: 줄마다 이름 토글 + [상세보기](설명은 상세보기 창에만)
        from kivy.uix.togglebutton import ToggleButton

        귀검사 = gf.캐릭터_생성(
            "새귀검", "귀검사"
        )  # 레벨 1 - 다음 레벨업이 마스터리선택
        무기목록, 방어구목록 = gf.캐릭터_마스터리_선택지(귀검사)
        고른 = []
        매니저.get_screen("파티관리")._마스터리선택_팝업(
            귀검사, lambda 무기, 방어구: 고른.append((무기, 방어구))
        )
        yield 0.5
        팝업 = Window.children[0]
        토글 = [w for w in 팝업.walk(restrict=True) if isinstance(w, ToggleButton)]
        assert [t.text for t in 토글] == [n for n, _ in 무기목록 + 방어구목록]
        상세들 = [
            w
            for w in 팝업.walk(restrict=True)
            if isinstance(w, Button) and w.text == "상세보기"
        ]
        assert len(상세들) == len(토글)
        assert all(t.height < 50 * 2.8125 for t in 토글)  # 설명이 빠져 한 줄 높이
        _찍기("mastery_popup")
        상세들[0].trigger_action(duration=0)
        yield 0.5
        assert Window.children[0].title == "마스터리 상세보기"
        assert any(
            무기목록[0][1] in getattr(w, "text", "")
            for w in Window.children[0].walk(restrict=True)
        )
        _찍기("mastery_detail")
        Window.children[0].dismiss(animation=False)
        yield 0.3
        확인 = next(
            w
            for w in 팝업.walk(restrict=True)
            if isinstance(w, Button) and w.text == "확인"
        )
        assert 확인.disabled
        토글[0].trigger_action(duration=0)
        토글[len(무기목록)].trigger_action(duration=0)
        assert not 확인.disabled
        확인.trigger_action(duration=0)
        yield 0.6
        assert 고른 == [(무기목록[0][0], 방어구목록[0][0])], 고른
        결과["단계"].append(
            "마스터리 선택 팝업(이름 토글 + 상세보기, 무기/방어구 하나씩 골라 확인)"
        )

        # 레벨 12 [스킬강화] 팝업: 보유 스킬마다 버튼, 누르면 그 스킬로 확정
        고른 = []
        강화항목 = gf.전직_레지스트리["귀검사"]["웨펀마스터"]["레벨업테이블"][12]
        매니저.get_screen("파티관리")._스킬강화_팝업(
            상태["파티"]["파티원"][0], 강화항목, 고른.append
        )
        yield 0.5
        _찍기("skill_enhance_popup")
        팝업 = list(Window.children)[0]
        버튼들 = [
            w
            for w in 팝업.walk(restrict=True)
            if isinstance(w, Button) and w.text.startswith("귀참")
        ]
        assert len(버튼들) == 1, [getattr(w, "text", "") for w in 팝업.walk()]
        버튼들[0].dispatch("on_release")
        yield 0.6  # 팝업 닫힘 애니메이션이 끝날 때까지(0.3이면 가끔 아직 창에 남아 있었다)
        assert 고른 == ["귀참"] and len(Window.children) == 1, 고른
        결과["단계"].append("스킬강화 팝업(보유 스킬 버튼 -> 그 스킬로 확정)")

        # 훔쳐배우기(#365): 퍽이 아니라 [스킬습득]에서 다른 전직의 스킬을 5배 값(500골드)에 산다
        다른 = support.새게임([("", "귀검사")])
        버서커 = 다른["파티"]["파티원"][0]
        support.성장(다른, 버서커, 8, 전직="버서커")
        고른 = []
        매니저.get_screen("파티관리")._퍽선택_팝업(버서커, 고른.append)
        yield 0.5
        퍽글 = [getattr(w, "text", "") for w in list(Window.children)[0].walk()]
        assert not any(글.startswith("훔쳐배우기") for 글 in 퍽글), 퍽글
        _팝업_닫기()
        yield 0.3
        원래골드 = 상태["소지품"].get("골드", 0)
        상태["소지품"]["골드"] = 500
        매니저.get_screen("파티관리")._스킬습득_팝업(버서커)
        yield 0.5
        _찍기("steal_learn_popup")
        팝업 = list(Window.children)[0]
        [행] = [
            w.parent
            for w in 팝업.walk(restrict=True)
            if isinstance(w, Label) and w.text == "귀신 : 브레멘"
        ]
        [가격] = [w for w in 행.children if getattr(w, "text", "").endswith("골드")]
        assert 가격.text == "500골드" and not 가격.disabled, 가격.text
        가격.dispatch("on_release")
        yield 0.3
        assert "귀신 : 브레멘" in 버서커["보유스킬"] and 상태["소지품"]["골드"] == 0
        _팝업_닫기()
        yield 0.3
        상태["소지품"]["골드"] = 원래골드
        결과["단계"].append(
            "훔쳐배우기: 퍽 목록에 없음, [스킬습득]에서 다른 전직 스킬(귀신 : 브레멘)을 500골드에 삼"
        )

        # 퍽 "타입"(#289): 스탯획득 퍽(능력치향상)을 고르면 능력치 배분 팝업이 열린다
        매니저.get_screen("파티관리")._퍽선택_팝업(버서커, 고른.append)
        yield 0.5
        _팝업_버튼("능력치향상").dispatch("on_release")
        yield 0.6
        assert list(Window.children)[0].title == "능력치 배분", list(Window.children)
        list(Window.children)[0].dismiss()
        yield 0.6
        결과["단계"].append("능력치향상: 퍽 선택 -> 능력치 배분 팝업")

        # 못 고르는 퍽은 회색(이유와 함께, 누를 수 없음), 전직이 다른 퍽은 숨김(사용자 결정 2026-10-20)
        버서커["보유퍽"] = ["약점제거"]  # 배타묶음 "약점"
        버서커["보유특성"].append("약점제거")
        매니저.get_screen("파티관리")._퍽선택_팝업(버서커, 고른.append)
        yield 0.5
        _찍기("perk_gray")
        글들 = {
            w.text: w.disabled
            for w in list(Window.children)[0].walk(restrict=True)
            if isinstance(w, Button)
        }
        assert 글들.get("삼중극점 (3차수부터)") is True, 글들
        assert 글들.get("능력치향상") is False, 글들
        assert not any(t.startswith("약점제거") for t in 글들), 글들  # 이미 배움 - 숨김
        list(Window.children)[0].dismiss()
        yield 0.6
        결과["단계"].append("퍽 선택: 차수 미달 퍽은 회색(이유), 배운 퍽은 숨김")

        # 약점증가(사용자 결정 2026-10-20): 주스탯·보조스탯을 뺀 4개가 약점 - 배분 팝업에서 "(약점)"으로 못 올린다
        약점캐 = support.새게임([("", "귀검사")])["파티"]["파티원"][0]
        약점캐["보유특성"].append("약점증가")
        매니저.get_screen("파티관리")._능력치배분_팝업(약점캐, 2, 확인콜백=고른.append)
        yield 0.5
        _찍기("weak_up_alloc")
        라벨들 = [
            w.text
            for w in list(Window.children)[0].walk(restrict=True)
            if isinstance(w, Label) and w.text.endswith("(약점)")
        ]
        assert len(라벨들) == 4, 라벨들
        list(Window.children)[0].dismiss()
        yield 0.6
        결과["단계"].append(
            "약점증가: 능력치 배분에서 주스탯·보조스탯을 뺀 4개가 (약점)"
        )

        # 포켓몬(4차수): 퍽 선택 -> 특성 고르기 팝업 -> 고른 특성(마중물)을 얻는다
        포켓 = support.새게임([("", "귀검사")])
        포켓캐 = 포켓["파티"]["파티원"][0]
        support.성장(포켓, 포켓캐, 18, 전직="버서커")
        고른 = []
        매니저.get_screen("파티관리")._퍽선택_팝업(포켓캐, 고른.append)
        yield 0.5
        _팝업_버튼("포켓몬").dispatch("on_release")
        yield 0.6
        _찍기("pokemon_pick")
        버튼들 = [
            w
            for w in list(Window.children)[0].walk(restrict=True)
            if isinstance(w, Button) and w.text.startswith("마중물\n")
        ]
        assert len(버튼들) == 1, [getattr(w, "text", "") for w in Window.children]
        버튼들[0].dispatch("on_release")
        yield 0.6
        assert len(고른) == 1 and 고른[0]["선택특성"] == "마중물", 고른
        gf.캐릭터_레벨업_적용(포켓캐, **고른[0])
        assert "마중물" in 포켓캐["보유특성"]
        결과["단계"].append(
            "포켓몬: 퍽 선택 -> 특성 고르기 팝업 -> 고른 특성(마중물)을 얻음"
        )

        # [스킬습득] 팝업: 직업 계열 스킬 목록 + 비용, 골드가 모자라면 버튼 잠금, 누르면 배운다
        파티관리 = 매니저.get_screen("파티관리")
        파티관리.갱신()
        assert any(
            getattr(w, "text", "") == "스킬습득" for w in 파티관리.walk(restrict=True)
        ), "스킬습득 버튼 없음"
        yield 0.3
        # 카드 오른쪽 버튼 셋은 위에서 아래로 쌓이고, 능력치 칸은 "이름 값"이 한 줄에 다 들어간다
        from kivy.core.text.markup import MarkupLabel

        버튼y = {
            w.text: w.y
            for w in 파티관리.walk(restrict=True)
            if getattr(w, "text", "") in ("레벨업", "스킬습득", "상세보기")
        }
        assert 버튼y["레벨업"] > 버튼y["스킬습득"] > 버튼y["상세보기"], 버튼y
        능력치칸 = [
            w
            for w in 파티관리.walk(restrict=True)
            if isinstance(w, main.Label) and "[color=9ea6b3]" in w.text
        ]
        assert len(능력치칸) == 6 * len(상태["파티"]["파티원"]), len(능력치칸)
        for 칸 in 능력치칸:
            글 = MarkupLabel(text=칸.text, font_size=칸.font_size, markup=True)
            글.refresh()
            assert 글.texture.width <= 칸.width, (칸.text, 글.texture.width, 칸.width)
        _찍기("party_manage")
        귀검사 = 상태["파티"]["파티원"][0]
        상태["소지품"]["골드"] = 50
        파티관리._스킬습득_팝업(귀검사)
        yield 0.5
        _찍기("skill_learn_popup")
        팝업 = list(Window.children)[0]
        스킬버튼 = [
            w
            for w in 팝업.walk(restrict=True)
            if isinstance(w, Button) and w.text.endswith("골드")
        ]
        # 골드 50: 50골드(1차 계열) 스킬만 누를 수 있고 100골드(전직)·500골드(훔쳐배우기) 스킬은 잠김
        assert 스킬버튼 and all(b.disabled == (b.text != "50골드") for b in 스킬버튼), [
            (b.text, b.disabled) for b in 스킬버튼
        ]
        보유전 = list(귀검사["보유스킬"])
        스킬버튼[0].dispatch("on_release")
        yield 0.3
        새스킬 = [n for n in 귀검사["보유스킬"] if n not in 보유전]
        assert len(새스킬) == 1 and 상태["소지품"]["골드"] == 0, 새스킬
        남은버튼 = [
            w
            for w in 팝업.walk(restrict=True)
            if isinstance(w, Button) and w.text.endswith("골드")
        ]
        assert 남은버튼 and all(b.disabled for b in 남은버튼)  # 골드 0 -> 잠김
        _찍기("skill_learn_after")
        상세 = next(
            w
            for w in 팝업.walk(restrict=True)
            if isinstance(w, Button) and w.text == "상세보기"
        )
        상세.dispatch("on_release")
        yield 0.5
        assert list(Window.children)[0].title == "스킬 상세보기"
        _찍기("skill_learn_detail")
        _팝업_닫기()
        결과["단계"].append(
            "스킬습득 팝업(한 줄: 이름/가격/상세보기, 가격 누르면 배움, 모자라면 잠금, 상세 팝업)"
        )

    def _단계_반응스킬_표시(self, 상태, 매니저):
        """파티원 화면 [스킬과 특성] - 반응스킬은 스킬 탭에 "반응스킬"로, 특성 탭에는 없다"""
        거너 = next(c for c in 상태["파티"]["파티원"] if c["직업"] == "거너")
        assert "건가드" in 거너["보유스킬"] and "건가드" not in 거너["보유특성"]
        화면 = 매니저.get_screen("파티원")
        화면.캐릭터 = 거너
        화면.탭, 화면.하위탭 = "스킬과 특성", "스킬"
        매니저.current = "파티원"
        yield 0.5
        글들 = [_글(getattr(w, "text", "")) for w in 화면.walk(restrict=True)]
        assert any("건가드" in 글 for 글 in 글들), 글들
        assert any("반응스킬 · 반응행동" in 글 for 글 in 글들), 글들
        _찍기("party_member_reaction_skill")
        화면._하위탭_선택("특성")
        yield 0.3
        글들 = [_글(getattr(w, "text", "")) for w in 화면.walk(restrict=True)]
        assert not any("건가드" in 글 for 글 in 글들), 글들
        화면._하위탭_선택("스킬")
        화면.탭 = "장비와 스탯"
        결과["단계"].append("파티원 스킬 탭에 반응스킬 표시(특성 탭에는 없음)")

    def _단계_장비_포션_뒤로키_전투팝업(self, 상태, 매니저):
        """장비 교체/파티원 포션/뒤로 키, 전투 화면 팝업(스킬/대상/포션/행동 선택/도망)"""
        무기 = yield from self._단계_장비교체(상태, 매니저)
        yield from self._단계_파티원_포션_주류(상태, 매니저)
        yield from self._단계_뒤로키(상태, 매니저, 무기)
        전투 = yield from self._단계_전투_스킬_대상팝업(상태, 매니저)
        yield from self._단계_전투_아이템(상태, 전투)
        yield from self._단계_전투_반복지정_행동선택(상태, 전투)
        yield from self._단계_전투_도망_만취(상태, 전투)
        return 전투  # 다음 단계(전투 종료/자동전투)가 이어서 쓴다

    def _단계_장비교체(self, 상태, 매니저):
        """장비 교체 팝업(무기/상의) 분류 탭 + 상세보기. 뒤로 키 단계가 쓸 무기를 돌려준다"""
        # 장비 교체 팝업: 칸마다 이름 + 간단요약(무기 공격력/AC) + [상세보기]
        for 슬롯 in ("무기", "상의"):
            for 이름 in list(상태["상점카탈로그"]["장비"][슬롯])[:3]:
                상태["소지품"]["장비"][이름] = 상태["소지품"]["장비"].get(이름, 0) + 1
        귀검사 = 상태["파티"]["파티원"][0]
        매니저.current = "파티원"
        for 슬롯, 요약 in (("무기", "무기 공격력 "), ("상의", "AC ")):
            screens_party._장비교체_팝업(귀검사, 슬롯, lambda: None)
            yield 0.5
            _찍기(f"equip_swap_{슬롯}")
            팝업 = Window.children[0]
            글들 = [w.text for w in 팝업.walk(restrict=True) if hasattr(w, "text")]
            assert any(요약 in 글 for 글 in 글들), 글들
            assert 글들.count("상세보기") >= 2, 글들
            # 분류 탭: 무기는 [전체] + 귀검사 무기 종류, 상의는 [전체] + 재질 - 한 줄에 다 보인다
            from kivy.uix.togglebutton import ToggleButton

            탭들 = [w for w in 팝업.walk(restrict=True) if isinstance(w, ToggleButton)]
            assert [t.text for t in 탭들] == gf.장비_교체_탭목록(상태, 귀검사, 슬롯)
            assert 탭들[0].state == "down" and 탭들[0].text == "전체"
            assert all(t.right <= 탭들[0].parent.right + 1 for t in 탭들)
            # 다른 직업군 무기는 [전체]에도 없다
            if 슬롯 == "무기":
                assert not any("너클" in 글 or "빗자루" in 글 for 글 in 글들), 글들
            두번째 = 탭들[2]  # 무기 "도" / 상의 "가죽"
            두번째.trigger_action(duration=0)
            yield 0.3
            assert [t.text for t in 탭들 if t.state == "down"] == [두번째.text]
            이름들 = {
                i["이름"]
                for i, *_ in gf.장비_교체_후보(상태, 귀검사, 슬롯, 두번째.text)
            }
            글들 = [w.text for w in 팝업.walk(restrict=True) if hasattr(w, "text")]
            현재이름 = (gf.캐릭터_장착아이템(상태, 귀검사, 슬롯) or {}).get("이름")
            목록글 = [글 for 글 in 글들 if not 글.startswith("[color=9ea6b3]현재")]
            for n in 상태["상점카탈로그"]["장비"][슬롯]:
                if n not in 이름들 and n != 현재이름:
                    assert not any(n in 글 for 글 in 목록글), (두번째.text, n)
            _찍기(f"equip_swap_{슬롯}_tab")
            _팝업_닫기()
            yield 0.3
        결과["단계"].append(
            "장비 교체 팝업 분류 탭(무기 종류/방어구 재질, 다른 직업군 무기 숨김)"
        )
        무기 = next(iter(상태["상점카탈로그"]["장비"]["무기"].values()))
        screens_party._아이템_상세_팝업(무기)
        yield 0.5
        _찍기("equip_detail")
        _팝업_닫기()
        yield 0.3
        # 레어 무기(#437): 파티 상세보기와 상점 자세히 보기에 "설명"이 보이고, 효과 원소 칸은 그대로 안 보인다
        레어 = 상태["상점카탈로그"]["장비"]["무기"]["복수의 영혼도"]
        for 이름, 열기 in (
            ("equip_detail_rare", lambda: screens_party._아이템_상세_팝업(레어)),
            ("shop_detail_rare", lambda: 매니저.get_screen("상점")._자세히보기(레어)),
        ):
            열기()
            yield 0.5
            _찍기(이름)
            글들 = [
                w.text
                for w in Window.children[0].walk(restrict=True)
                if hasattr(w, "text")
            ]
            assert any(레어["설명"] in 글 for 글 in 글들), (이름, 글들)
            assert not any("고유효과" in 글 for 글 in 글들), (이름, 글들)
            if (
                이름 == "shop_detail_rare"
            ):  # 긴 설명 줄은 글 높이만큼 늘어나 윗줄과 겹치지 않는다
                [설명] = [
                    w
                    for w in Window.children[0].walk(restrict=True)
                    if isinstance(w, Label) and w.text.startswith("설명:")
                ]
                assert 설명.height + 1 >= 설명.texture_size[1] > dp(32), (
                    설명.height,
                    설명.texture_size,
                )
            _팝업_닫기()
            yield 0.3
        결과["단계"].append("장비 교체 팝업(무기/상의) + 상세보기(레어 무기 설명)")
        yield 0.3
        return 무기

    def _단계_파티원_포션_주류(self, 상태, 매니저):
        """파티원 화면 [포션 사용] 팝업 - 회복포션과 주류(취기)"""
        귀검사 = 상태["파티"]["파티원"][0]
        # 파티원 화면 [포션 사용]: 목록(가득 찬 MP 포션은 사유와 함께 비활성) -> 마시면 HP가 오른다
        상태["소지품"]["포션"] = {"초보자용 HP 포션": 2, "초보자용 MP 포션": 1}
        귀검사["현재HP"] = 1
        파티원 = 매니저.get_screen("파티원")
        파티원.캐릭터 = 귀검사
        파티원.갱신()
        파티원._포션_팝업(상태, 귀검사)
        yield 0.5
        버튼 = [
            w for w in Window.children[0].walk(restrict=True) if isinstance(w, Button)
        ]
        hp버튼 = next(b for b in 버튼 if b.text.startswith("초보자용 HP 포션 x2"))
        mp버튼 = next(b for b in 버튼 if b.text.startswith("초보자용 MP 포션"))
        assert mp버튼.disabled and "가득" in mp버튼.text, mp버튼.text
        hp버튼.trigger_action(duration=0)
        yield 0.5
        assert 귀검사["현재HP"] > 1, 귀검사["현재HP"]
        assert 상태["소지품"]["포션"]["초보자용 HP 포션"] == 1
        _찍기("party_potion_popup")
        _팝업_닫기()
        gf.파티_최대치로_회복(상태)
        결과["단계"].append(
            "파티원 포션 사용 팝업(가득 차면 비활성, 마시면 회복/개수 감소)"
        )
        yield 0.3

        # 같은 팝업의 주류: 마시면 취기가 쌓이고 스탯창에 [취기 N]이 보인다
        # (회복 굴림이 난수를 쓰므로 앞뒤로 난수 상태를 되돌려 뒤 단계의 굴림을 그대로 둔다)
        난수상태 = rng.상태()
        상태["소지품"]["소모품"]["맥주"] = 2
        귀검사["현재HP"] = 1
        파티원._포션_팝업(상태, 귀검사)
        yield 0.5
        버튼 = [
            w for w in Window.children[0].walk(restrict=True) if isinstance(w, Button)
        ]
        맥주버튼 = next(b for b in 버튼 if b.text.startswith("맥주 x2"))
        맥주버튼.trigger_action(duration=0)
        yield 0.5
        assert 귀검사["상태이상"] == [{"이름": "취기", "중첩": 1}], 귀검사["상태이상"]
        assert 상태["소지품"]["소모품"]["맥주"] == 1
        _찍기("party_drink_popup")
        _팝업_닫기()
        라벨들 = [
            w.text for w in 파티원.walk(restrict=True) if isinstance(w, main.Label)
        ]
        assert any("[취기 1]" in t for t in 라벨들), 라벨들
        귀검사["상태이상"] = []
        gf.파티_최대치로_회복(상태)
        rng.상태_복원(난수상태)
        결과["단계"].append("파티원 주류 사용(취기 1, 스탯창 [취기 1] 표시)")
        yield 0.3

    def _단계_뒤로키(self, 상태, 매니저, 무기):
        """핸드폰 [뒤로] 키 - 팝업 겹침/파티원/파티관리/마을/상점/메인메뉴"""
        귀검사 = 상태["파티"]["파티원"][0]
        # 핸드폰 [뒤로] 키(27): 맨 위 팝업의 취소/닫기 -> 화면의 뒤로/나가기 순
        screens_party._장비교체_팝업(귀검사, "무기", lambda: None)
        screens_party._아이템_상세_팝업(무기)
        yield 0.5
        assert _팝업수() == 2, _팝업수()
        _뒤로키()
        yield 0.5
        assert _팝업수() == 1, "상세보기만 닫혀야 한다"
        _뒤로키()
        yield 0.5
        assert _팝업수() == 0 and 매니저.current == "파티원", 매니저.current
        매니저.get_screen("파티원").복귀화면 = "파티관리"
        매니저.get_screen("파티관리").복귀화면 = "마을"
        _뒤로키()
        assert 매니저.current == "파티관리", 매니저.current
        _뒤로키()
        assert 매니저.current == "마을", 매니저.current
        _뒤로키()
        assert 매니저.current == "마을", "마을에서는 아무 일도 없어야 한다"
        상점 = 매니저.get_screen("상점")
        상점.복귀화면 = "마을"
        매니저.current = "상점"
        상점._대분류_그리기("구매")
        _뒤로키()
        글들 = [w.text for w in 상점.내용틀.walk(restrict=True) if hasattr(w, "text")]
        assert "나가기" in 글들 and 매니저.current == "상점", 글들
        _뒤로키()
        assert 매니저.current == "마을", 매니저.current
        매니저.current = "메인메뉴"
        _뒤로키()
        assert 매니저.current == "메인메뉴", 매니저.current
        결과["단계"].append("뒤로 키(팝업 겹침/파티원/파티관리/마을/상점/메인메뉴)")

    def _단계_전투_스킬_대상팝업(self, 상태, 매니저):
        """전투 시작 -> 직업별 스킬 팝업/실제 타겟, 일반공격 대상 팝업. 전투 화면을 돌려준다"""
        gf.전투_시작(상태, ["타우 아미", "고블린", "고블린"], 레벨=6, 차수=2)
        support.반응_처리(상태)
        _아군_차례로(상태)
        전투 = 매니저.get_screen("전투")
        전투.갱신(신규=True)
        매니저.current = "전투"
        전투상태 = 상태["전투상태"]
        for 이름 in ("마법사", "거너", "귀검사", "프리스트"):
            p = _차례(전투상태, 이름)
            _팝업_닫기()
            전투._스킬_버튼_클릭(p)
            yield 0.3  # 칸 너비가 정해진 뒤 잘림을 본다
            반응 = [
                n
                for n in p["원본"]["보유스킬"]
                if 상태["스킬데이터모음"][n]["분류"] == "반응스킬"
            ]
            if 이름 in ("거너", "마법사"):  # 레벨 3에 건가드/위상 변화
                assert 반응, p["원본"]["보유스킬"]
            # 한 줄 = 이름(왼쪽 정렬) | 남은 횟수 | MP | 행동, 반응스킬은 [반응]으로 비활성
            줄버튼 = _스킬줄_버튼들()
            assert [b.스킬이름 for b in 줄버튼] == p["원본"]["보유스킬"]
            for b in 줄버튼:
                줄 = gf.스킬_팝업_줄(상태, p, b.스킬이름)
                assert _스킬줄_글(b) == [줄["이름"], 줄["남은"], 줄["MP"], 줄["행동"]]
                assert _스킬줄_칸(b)[0].halign == "left"
                for 칸 in _스킬줄_칸(b)[1:]:  # 남은/MP/행동은 잘리지 않는다
                    칸.texture_update()
                    assert 칸.texture_size[0] <= 칸.width + 1, (b.스킬이름, 칸.text)
                assert b.disabled == (not 줄["가능"]), b.스킬이름
                if b.스킬이름 in 반응:
                    assert b.disabled and 줄["행동"] == "[반응]", b.스킬이름
            if 이름 == "거너":
                yield 0.5
                _찍기("battle_skill_popup_gunner")
            for 스킬 in p["원본"]["보유스킬"]:
                데이터 = 상태["스킬데이터모음"][스킬]
                assert 전투._실제_타겟(데이터) == gf.스킬_실제_타겟(상태, 데이터), 스킬
            결과["단계"].append(
                f"{이름} 스킬 팝업 {len(줄버튼)}줄(이름|남은|MP|행동, 반응스킬 {len(반응)}개 비활성)"
                "/실제 타겟"
            )
        yield 0.5
        _찍기("battle_skill_popup")
        _팝업_닫기()

        # 적 대상은 이름 목록 팝업에서 고른다 - 살아 있는 적 버튼 + 맨 아래 [취소]
        적 = [x for x in 전투상태["참가자"] if x["진영"] == "적" and x["생존"]]
        _차례(전투상태, "귀검사")
        전투._일반공격_클릭()
        yield 0.3
        글들 = [b.text for b in _대상버튼들()]
        assert len(글들) == len(적) + 1 and 글들[-1] == "취소", 글들
        # 버튼마다 "이름\nHP 현재/최대", 상단 적 칸에도 같은 HP 줄
        assert 글들[:-1] == [f"{p['이름']}\n{gf.적_HP표시(상태, p)}" for p in 적], 글들
        assert all("/" in g.split("\n")[1] for g in 글들[:-1]), 글들
        적칸글 = [
            w.text
            for w in 전투.적상태틀.walk(restrict=True)
            if isinstance(w, main.Label)
        ]
        assert all(any(gf.적_HP표시(상태, p) in t for t in 적칸글) for p in 적), 적칸글
        # 팝업 폭은 기준 화면의 0.7(전에는 0.35) - 긴 이름이 버튼 안에 들어간다
        assert abs(Window.children[0].width - 0.7 * Window.width) < 2
        _찍기("battle_target_popup")
        _뒤로키()
        yield 0.3
        assert _팝업수() == 0 and 전투.선택모드 is None, (
            "취소(뒤로 키)면 행동 없이 닫힌다"
        )
        로그수 = len(전투상태["로그"])
        전투._일반공격_클릭()
        yield 0.3
        _대상버튼들()[0].trigger_action(duration=0)
        yield 0.5
        assert _팝업수() == 0 and len(전투상태["로그"]) > 로그수, "고르면 바로 공격한다"
        결과["단계"].append("일반공격 대상 팝업(적 목록 + 취소/뒤로 키, 고르면 공격)")

        # 추가행동: 일반행동으로 일반공격한 귀검사(웨펀마스터, 추가공격 1)는 [일반공격]이 아직 눌리고
        # 일반공격취급 스킬(어퍼 슬래쉬)은 [추가]로 낸다
        귀검사 = gf.현재_턴_참가자(상태)
        assert 귀검사["행동자원"]["일반행동"] == 0 and gf.추가행동_남은수(귀검사) == 1
        전투.갱신()
        yield 0.3
        일반공격버튼 = next(
            w
            for w in 전투.액션틀.walk(restrict=True)
            if getattr(w, "text", None) == "일반공격"
        )
        assert not 일반공격버튼.disabled
        전투._스킬_버튼_클릭(귀검사)
        yield 0.5
        어퍼 = next(b for b in _스킬줄_버튼들() if b.스킬이름 == "어퍼 슬래쉬")
        assert _스킬줄_글(어퍼)[3] == "[추가]" and not 어퍼.disabled
        _찍기("battle_skill_popup_extra")
        _팝업_닫기()
        결과["단계"].append(
            "추가행동 - 일반공격 뒤 [일반공격] 활성, 어퍼 슬래쉬 [추가]"
        )
        return 전투

    def _단계_전투_아이템(self, 상태, 전투):
        """전투 [아이템] - 회복포션/주류/버프포션/소환 아이템/투척 아이템"""
        전투상태 = 상태["전투상태"]
        # [아이템]: 회복포션 팝업 -> 보조행동 1개로 자신만 회복, 로그에 남는다
        p = _차례(전투상태, "귀검사")
        p["현재HP"] = 1
        보조 = p["행동자원"]["보조행동"]
        전투._아이템_클릭()
        yield 0.3
        포션버튼 = [b for b in _대상버튼들() if b.text.startswith("초보자용 HP 포션")]
        assert 포션버튼 and not 포션버튼[0].disabled, [b.text for b in _대상버튼들()]
        _찍기("battle_potion_popup")
        포션버튼[0].trigger_action(duration=0)
        yield 0.5
        assert p["현재HP"] > 1 and p["행동자원"]["보조행동"] == 보조 - 1
        assert "초보자용 HP 포션 사용" in 전투상태["로그"][-1].get("행동", "")
        결과["단계"].append("전투 [아이템] 포션 팝업(보조행동 1, 자신 회복, 로그)")

        # [아이템]의 주류: 보조행동 1개, 취기가 쌓이고 아군 칸에 (취기 1)이 보인다
        난수상태 = rng.상태()
        p = _차례(전투상태, "귀검사")
        상태["소지품"]["소모품"]["맥주"] = 1
        전투._아이템_클릭()
        yield 0.3
        맥주버튼 = [b for b in _대상버튼들() if b.text.startswith("맥주")]
        assert 맥주버튼 and not 맥주버튼[0].disabled, [b.text for b in _대상버튼들()]
        맥주버튼[0].trigger_action(duration=0)
        yield 0.5
        assert p["상태이상"] == [{"이름": "취기", "중첩": 1}], p["상태이상"]
        assert "맥주 마심" in 전투상태["로그"][-1].get("행동", "")
        전투.갱신()
        yield 0.2
        라벨들 = [w.text for w in 전투.walk(restrict=True) if isinstance(w, main.Label)]
        assert any("(취기 1)" in t for t in 라벨들), 라벨들
        _찍기("battle_drink")
        p["상태이상"] = []
        rng.상태_복원(난수상태)
        결과["단계"].append("전투 [아이템] 주류(보조행동 1, 취기 1, 아군 칸 표시)")

        # [아이템]의 버프포션: 가속 포션은 보조행동 1개로 마신 턴에 바로 일반행동 +1
        p = _차례(전투상태, "귀검사")
        상태["소지품"].setdefault("포션", {})["가속 포션"] = 1
        보조 = p["행동자원"]["보조행동"]
        일반 = p["행동자원"]["일반행동"]
        전투._아이템_클릭()
        yield 0.3
        가속버튼 = [b for b in _대상버튼들() if b.text.startswith("가속 포션")]
        assert 가속버튼 and not 가속버튼[0].disabled, [b.text for b in _대상버튼들()]
        _찍기("battle_buff_potion_popup")
        가속버튼[0].trigger_action(duration=0)
        yield 0.5
        assert p["행동자원"]["보조행동"] == 보조 - 1, p["행동자원"]
        assert p["행동자원"]["일반행동"] == 일반 + 1, p["행동자원"]
        assert any(b["이름"] == "일반행동증가" for b in p["버프"]), p["버프"]
        assert "가속 포션 사용" in 전투상태["로그"][-1].get("행동", "")
        p["버프"] = [b for b in p["버프"] if b["이름"] != "일반행동증가"]
        결과["단계"].append(
            "전투 [아이템] 버프포션(가속 포션 - 보조행동 1, 일반행동 바로 +1)"
        )

        # [아이템]의 소환 아이템: 고블린 더스트 - 보조행동 1개, 고블린 소환, 턴이 끝나면 고블린이 공격
        p = _차례(전투상태, "귀검사")
        상태["소지품"]["소모품"]["고블린 더스트"] = 1
        보조 = p["행동자원"]["보조행동"]
        전투._아이템_클릭()
        yield 0.3
        더스트버튼 = [b for b in _대상버튼들() if b.text.startswith("고블린 더스트")]
        assert 더스트버튼 and not 더스트버튼[0].disabled, [
            b.text for b in _대상버튼들()
        ]
        _찍기("battle_summon_item_popup")
        더스트버튼[0].trigger_action(duration=0)
        yield 0.5
        assert p["행동자원"]["보조행동"] == 보조 - 1, p["행동자원"]
        assert "고블린" in p.get("소환수", []), p.get("소환수")
        assert "고블린 더스트 사용" in 전투상태["로그"][-1].get("행동", "")
        p["버프"] = [b for b in p["버프"] if b["이름"] != "고블린소환"]
        p["소환수"] = [x for x in p.get("소환수", []) if x != "고블린"]
        결과["단계"].append(
            "전투 [아이템] 소환 아이템(고블린 더스트 - 보조행동 1, 고블린 소환)"
        )

        # [아이템]의 투척 아이템: 폭탄 - 일반행동 1개, 중심 대상 팝업에서 고르면 양옆까지 맞는다
        p = _차례(전투상태, "귀검사")
        난수상태 = rng.상태()  # 뒤 단계의 굴림이 달라지지 않게
        상태["소지품"]["소모품"]["폭탄"] = 1
        # 폭탄에 적이 쓰러져 전투가 끝나지 않게 HP를 넉넉히 올렸다가 되돌린다(뒤 단계가 쓴다)
        적HP = {
            id(x): x["현재HP"]
            for x in 전투상태["참가자"]
            if x["진영"] == "적" and x["생존"]
        }
        일반 = p["행동자원"]["일반행동"]
        전투._아이템_클릭()
        yield 0.3
        폭탄버튼 = [b for b in _대상버튼들() if b.text.startswith("폭탄")]
        assert 폭탄버튼 and not 폭탄버튼[0].disabled, [b.text for b in _대상버튼들()]
        assert "(일반행동)" in 폭탄버튼[0].text, 폭탄버튼[0].text
        폭탄버튼[0].trigger_action(duration=0)
        yield 0.3
        assert 전투.선택모드 == ("투척", "폭탄"), 전투.선택모드
        assert "양옆" in 전투.안내라벨.text, 전투.안내라벨.text
        _찍기("battle_throw_target_popup")
        for x in 전투상태["참가자"]:
            if id(x) in 적HP:
                x["현재HP"] = 999
        _대상버튼들()[0].trigger_action(duration=0)
        yield 0.5
        assert p["행동자원"]["일반행동"] == 일반 - 1, p["행동자원"]
        assert "폭탄" not in 상태["소지품"]["소모품"], 상태["소지품"]["소모품"]
        assert any(x.get("스킬") == "폭탄" for x in 전투상태["로그"][-3:]), 전투상태[
            "로그"
        ][-3:]
        for x in 전투상태["참가자"]:
            if id(x) in 적HP:
                x["현재HP"] = 적HP[id(x)]
        rng.상태_복원(난수상태)
        결과["단계"].append(
            "전투 [아이템] 투척 아이템(폭탄 - 일반행동 1, 중심 대상 팝업, 범위 공격)"
        )

    def _단계_전투_반복지정_행동선택(self, 상태, 전투):
        """썬더콜링 반복지정(은신 대상 거부, 캐스팅), 하급마법 쇼타임행동/일반행동 선택 팝업"""
        전투상태 = 상태["전투상태"]
        _차례(전투상태, "마법사")
        yield 0.3
        전투._스킬_클릭("썬더콜링", 상태["스킬데이터모음"]["썬더콜링"])
        assert 전투.선택모드[0] == "반복지정", 전투.선택모드
        적 = [x for x in 전투상태["참가자"] if x["진영"] == "적" and x["생존"]]
        skill_system.상태이상_부여(전투상태, 적[1], "은신", 3, None)
        yield 0.3
        _찍기("battle_target_popup_repeat")
        _대상버튼들()[1].trigger_action(duration=0)
        assert "지정할 수 없는" in 전투.안내라벨.text, 전투.안내라벨.text
        while 전투.선택모드 and 전투.선택모드[0] == "반복지정":
            _대상버튼들()[0].trigger_action(duration=0)
        assert _팝업수() == 0, _팝업수()
        # 상급마법은 캐스팅 - 쓰면 턴이 끝나고(화면이 바로 넘긴다) 밀린 차례에 쏜다(2026-10-22)
        비고들 = [
            str(x.get("비고", "")) for x in 전투상태["로그"] if isinstance(x, dict)
        ]
        assert any("썬더콜링 캐스팅을 시작했다" in b for b in 비고들), 비고들[-5:]
        결과["단계"].append(
            "썬더콜링 반복지정 - 대상 팝업을 다시 열며 선택(은신 대상 거부 포함), 캐스팅 시작"
        )
        yield 0.5
        _찍기("battle_after_thundercalling")

        # 쇼타임행동이 있으면 하급마법을 쇼타임행동/일반행동 중 골라 쓴다 - 행동 선택 팝업
        p = _차례(전투상태, "마법사")
        하급 = next(
            n
            for n, d in 상태["스킬데이터모음"].items()
            if "하급마법" in d.get("타입", []) and d.get("타겟") == "적단일"
        )
        if 하급 not in p["원본"]["보유스킬"]:
            p["원본"]["보유스킬"].append(하급)
        p["행동자원"].update(일반행동=1, 보조행동=1)
        p.setdefault("기타행동", {})["쇼타임행동"] = 1
        p["현재MP"] = 999
        전투._스킬_클릭(하급, 상태["스킬데이터모음"][하급])
        yield 0.3
        글들 = [b.text for b in _대상버튼들()]
        assert 글들 == ["쇼타임행동 (남은 1)", "일반행동 (남은 1)", "취소"], 글들
        _찍기("battle_action_choice_popup")
        _대상버튼들()[0].trigger_action(duration=0)  # 쇼타임행동
        yield 0.3
        # 위에서 은신을 건 적은 고를 수 없다 - 살아 있고 은신이 아닌 적을 이름으로 고른다
        # (앞 단계에서 어느 적이 쓰러지는지는 굴림에 따라 다르다)
        대상 = next(
            x["이름"]
            for x in 전투상태["참가자"]
            if x["진영"] == "적"
            and x["생존"]
            and not any(i["이름"] == "은신" for i in x["상태이상"])
        )
        next(b for b in _대상버튼들() if 대상 in b.text).trigger_action(duration=0)
        yield 0.5
        assert _팝업수() == 0, _팝업수()
        assert (p["행동자원"]["일반행동"], p["기타행동"]["쇼타임행동"]) == (1, 0)
        # 수단이 하나뿐이면 팝업 없이 바로 대상 선택으로 간다
        전투._스킬_클릭(하급, 상태["스킬데이터모음"][하급])
        yield 0.3
        assert 전투.선택모드 == ("스킬", 하급), 전투.선택모드
        _팝업_닫기()
        전투._대상선택_취소()
        결과["단계"].append(
            "행동 선택 팝업(하급마법 - 쇼타임행동/일반행동, 하나면 생략)"
        )

    def _단계_전투_도망_만취(self, 상태, 전투):
        """도망 불가(구속) 팝업, 도망 실패 -> 턴 종료, 만취 아군 차례 자동 진행"""
        전투상태 = 상태["전투상태"]
        # 도망: 파티 중 한 명이라도 구속이면 [도망]이 판정 없이 막힘 팝업을 띄운다
        현재 = _차례(전투상태, "귀검사")
        거너 = next(
            x for x in 전투상태["참가자"] if (x.get("원본") or {}).get("직업") == "거너"
        )
        skill_system.상태이상_부여(전투상태, 거너, "구속", 3, None)
        로그수 = len(전투상태["로그"])
        전투._도망_클릭()
        yield 0.5
        글들 = [
            w.text
            for 팝업 in list(Window.children)[:-1]
            for w in 팝업.walk(restrict=True)
            if hasattr(w, "text")
        ]
        assert (
            f"도망 칠 수 없습니다.\n대상 : {거너['이름']}\n상태이상 : 구속" in 글들
        ), 글들
        assert "확인" in 글들, 글들
        _찍기("battle_flee_blocked")
        _뒤로키()
        yield 0.6  # 닫힘 애니메이션까지
        assert _팝업수() == 0, "확인(뒤로 키)으로 닫혀야 한다"
        assert (
            len(전투상태["로그"]) == 로그수
            and 전투상태["참가자"][전투상태["현재턴"]] is 현재
        ), "막히면 굴림도 턴 변화도 없다"
        결과["단계"].append("구속이면 도망 불가 팝업(대상/상태이상/확인)")

        # 구속이 풀리면 확인 팝업 -> 실패 시 현재 캐릭터의 턴이 끝난다
        거너["상태이상"] = [i for i in 거너["상태이상"] if i["이름"] != "구속"]
        전투._도망_클릭()
        yield 0.3
        예버튼 = next(
            w
            for 팝업 in list(Window.children)[:-1]
            for w in 팝업.walk(restrict=True)
            if getattr(w, "text", None) == "예"
        )
        원래 = rng.주사위.randint
        rng.주사위.randint = lambda a, b: 1
        try:
            예버튼.dispatch("on_release")
            yield 1.0
        finally:
            rng.주사위.randint = 원래
        assert (
            전투상태["종료"] is not None
            or 전투상태["참가자"][전투상태["현재턴"]] is not 현재
        ), "도망에 실패하면 턴이 넘어가야 한다"
        결과["단계"].append("도망 실패 -> 현재 캐릭터 턴 종료")

        # 만취 아군의 차례는 조종하지 않고 화면이 자동으로 넘긴다(만취 행동 로그)
        p = _차례(전투상태, "귀검사")
        p["상태이상"] = [{"이름": "만취"}]
        로그수 = len(전투상태["로그"])
        전투.갱신()
        for _ in range(20):
            yield 0.2
            if any(
                str(x.get("행동", "")).startswith("만취 - ")
                for x in 전투상태["로그"][로그수:]
            ):
                break
        assert any(
            str(x.get("행동", "")).startswith("만취 - ")
            for x in 전투상태["로그"][로그수:]
        ), 전투상태["로그"][로그수:]
        p["상태이상"] = []
        # 만취 행동 뒤 화면이 이어서 돌리는 적 차례가 반응 팝업을 띄울 수 있다 - 쓰지 않고 엔진이 멈출 때까지
        # 기다린다(남겨 두면 다음 단계의 전투가 막힌다. 어느 적이 누구를 치는지는 굴림에 따라 다르다)
        for _ in range(50):
            if not 전투._엔진중:
                break
            if "사용 안 함" in _팝업글():
                _팝업_버튼("사용 안 함").dispatch("on_release")
            yield 0.2
        assert not 전투._엔진중, _팝업글()
        결과["단계"].append("만취 아군 차례 자동 진행(조종 불가, 만취 행동 로그)")

    def _단계_전투종료_자동전투_주점(self, 상태, 매니저, 전투):
        """전투 종료/보상, 자동전투, 몬스터 크기, 황금 고블린 도망, 주점"""
        yield from self._단계_전투종료_보상(상태, 매니저, 전투)
        yield from self._단계_자동전투(상태, 매니저, 전투)
        yield from self._단계_몬스터_크기(상태, 매니저, 전투)
        yield from self._단계_황금고블린_도망(상태, 매니저, 전투)
        yield from self._단계_주점(매니저)

    def _단계_전투종료_보상(self, 상태, 매니저, 전투):
        """전투 종료 팝업(승리 전리품/없음, 도망, 패배) + 전투 보상 선택/포기"""
        _찍기("battle_after_flee_fail")

        # 전투 종료 팝업: 승리(전리품) -> 던전, 도망 -> 던전, 패배 -> 마을
        _팝업_닫기()
        gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
        for 몬스터들, 끝내기, 첫줄, 전리품줄, 도착, 사진 in (
            (
                ["고블린", "겁쟁이 고블린"],
                support.강제_승리,
                "전투 승리!",
                True,
                "던전",
                "battle_end_win",
            ),
            (["힐가브"], support.강제_승리, "전투 승리!", False, "던전", None),
            (
                ["타우 아미"],
                lambda s: flow.전투이탈_시도(s["전투상태"], gf.아군_목록(s)[0]),
                "도망쳤다!",
                None,
                "던전",
                None,
            ),
            (
                ["타우 아미"],
                support.강제_패배,
                "전투 패배!",
                None,
                "마을",
                "battle_end_lose",
            ),
        ):
            원래맵 = 상태["던전상태"]["맵정보"]
            if 전리품줄 is False:
                # "전리품 없음": 던전 공용 드랍도, 골드도 없는 전투로 만든다
                상태["던전상태"]["맵정보"] = {**원래맵, "드랍표": []}
            gf.전투_시작(상태, 몬스터들, 레벨=6, 차수=2)  # 시작 반응에 안 쓰러지게
            if 전리품줄 is False:
                for 적 in gf.적_목록(상태):
                    적["원본"]["획득골드"] = "미정"
                    적["원본"][
                        "드랍표"
                    ] = []  # 몬스터 개인 드랍(monster_drop.py)도 없앤다
            support.반응_처리(상태)
            _아군_차례로(상태)
            매니저.current = "전투"
            전투.갱신(신규=True)
            yield 0.3
            # 체력 1 몬스터(힐가브)는 전투시작 반응에 쓰러져 이미 팝업이 떠 있을 수 있다
            if 상태["전투상태"] is not None:
                if 첫줄 == "도망쳤다!":
                    원래 = rng.주사위.randint
                    rng.주사위.randint = lambda a, b: 20
                    try:
                        끝내기(상태)
                    finally:
                        rng.주사위.randint = 원래
                else:
                    끝내기(상태)
                전투.갱신()
            yield 0.5
            글 = next(
                t
                for t in _팝업글()
                if t.split("\n")[0] in ("전투 승리!", "도망쳤다!", "전투 패배!")
            )
            줄들 = 글.split("\n")
            assert 줄들[0] == 첫줄, 글
            if 전리품줄 is True:
                assert 줄들[1] == "전리품" and len(줄들) >= 3 and "없음" not in 줄들, 글
            elif 전리품줄 is False:
                assert 줄들[1:3] == ["전리품", "없음"], 글
            else:
                assert "전리품" not in 줄들, 글
            if 사진:
                _찍기(사진)
            if 상태.get("던전상태"):
                상태["던전상태"]["맵정보"] = 원래맵
            if 첫줄 == "전투 승리!":
                # [확인]은 전투 보상을 받거나 포기하기 전까지 잠겨 있다
                assert (
                    _팝업_버튼("확인").disabled and not _팝업_버튼("전투 보상").disabled
                )
                칸 = gf.전투_보상_칸(상태)
                if all(칸) and 칸[0] != 칸[1]:
                    # 첫 칸 아이템은 소지품에 하나 넣어 둔다 - "보유 1" 줄이 그려지는지 보려고
                    장비칸 = 상태["소지품"]["장비"]
                    장비칸[칸[0]] = 장비칸.get(칸[0], 0) + 1
                _팝업_버튼("전투 보상").dispatch("on_release")
                yield 0.5
                assert _팝업_버튼("선택").disabled  # 박스를 누르기 전
                if 전리품줄 is True:  # 고블린들 - 후보가 있다
                    assert all(칸), 칸
                    보유 = 상태["소지품"]["장비"].get(칸[1], 0)
                    박스 = next(
                        w
                        for 팝업 in list(Window.children)[:-1]
                        for w in 팝업.walk(restrict=True)
                        if _글(getattr(w, "text", None)).split("\n")[0] == 칸[1]
                    ).parent.parent  # 이름 라벨 -> 줄 묶음 -> 보상 칸
                    박스.dispatch("on_release")
                    yield 0.3
                    # 칸마다 세 줄: 이름 / 부위 / 보유·착용, 칸 높이는 세 줄에 맞춤
                    sc = screens_common
                    for 이름칸 in 칸:
                        박스_ = next(
                            w.parent
                            for 팝업 in list(Window.children)[:-1]
                            for w in 팝업.walk(restrict=True)
                            if isinstance(w, sc.가로맞춤_라벨) and _글(w.text) == 이름칸
                        )
                        묶음 = 박스_
                        박스_ = 묶음.parent
                        줄글 = [_글(w.text) for w in reversed(묶음.children)]
                        개수글 = gf.전투_보상_보유표시(상태, 이름칸)
                        # 보유·착용이 없으면 두 줄, 줄 묶음은 칸 가운데
                        assert 줄글 == [
                            이름칸,
                            gf.전투_보상_부위(상태, 이름칸),
                        ] + ([개수글] if 개수글 else []), 줄글
                        assert abs(묶음.center_y - 박스_.center_y) < 2, (
                            묶음.center_y,
                            박스_.center_y,
                        )
                        if 이름칸 == 칸[0] and 칸[0] != 칸[1]:
                            assert 개수글.startswith("보유 "), 개수글
                        assert 박스_.height < 3 * sc.글자_높이("15sp") + 60, (
                            박스_.height
                        )
                        for w in 묶음.children:
                            assert w.texture_size[0] <= w.width, (w.text, w.width)
                    포기 = _팝업_버튼("포기하기(10골드)")
                    assert 포기.width > 박스_.parent.width * 0.6, 포기.width
                    _찍기("battle_reward")
                    _팝업_버튼("선택").dispatch("on_release")
                    yield 0.3
                    assert 상태["소지품"]["장비"][칸[1]] == 보유 + 1
                    # 받은 아이템이 전투 종료 팝업의 전리품 줄에 더해진다
                    새글 = _글(next(t for t in _팝업글() if t.startswith("전투 승리!")))
                    assert 새글 == "\n".join(
                        gf.전투_종료_문구(상태, "아군승리")
                    ) and any(줄.startswith(칸[1]) for 줄 in 새글.split("\n")[2:]), 새글
                    _찍기("battle_end_win_reward")
                else:  # 힐가브 - 후보 없음, 세 칸 모두 빈칸
                    assert 칸 == [None, None, None], 칸
                    _찍기("battle_reward_empty")
                    골드 = 상태["소지품"]["골드"]
                    _팝업_버튼("포기하기(10골드)").dispatch("on_release")
                    yield 0.3
                    assert 상태["소지품"]["골드"] == 골드 + 10
                assert not gf.전투_보상_대기중(상태)
                assert (
                    not _팝업_버튼("확인").disabled and _팝업_버튼("전투 보상").disabled
                )
            _확인_누르기()
            yield 0.5
            assert 매니저.current == 도착, 매니저.current
            if 도착 == "마을":
                gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
        결과["단계"].append(
            "전투 종료 팝업(승리 전리품/없음, 도망, 패배) + 전투 보상 선택/포기"
        )

    def _단계_자동전투(self, 상태, 매니저, 전투):
        """자동전투 켜기 -> 버튼 잠금 -> 중지, 다시 켜면 전투 끝까지"""

        # 자동전투: 켜면 [자동전투 중지]로 바뀌고 다른 행동 버튼은 잠긴다. 중지하면 풀린다.
        def 버튼(글):
            return next(
                w
                for w in 전투.액션틀.walk(restrict=True)
                if getattr(w, "text", None) == 글
            )

        def 아군_차례로_맞추기():
            p = next(x for x in gf.아군_목록(상태) if x["생존"])
            상태["전투상태"]["현재턴"] = 상태["전투상태"]["참가자"].index(p)
            flow.턴_시작_처리(상태["전투상태"], p)

        gf.전투_시작(상태, ["타우 아미", "타우 아미"], 레벨=6, 차수=2)
        support.반응_처리(상태)
        매니저.current = "전투"
        아군_차례로_맞추기()
        전투.갱신(신규=True)
        yield 0.3
        버튼("자동전투").dispatch("on_release")
        assert 전투.자동전투
        중지 = 버튼("자동전투 중지")
        assert all(
            버튼(글).disabled
            for 글 in ("일반공격", "스킬", "아이템", "도망", "턴 넘기기")
        )
        중지.dispatch("on_release")  # 첫 턴이 돌기 전에(0초 예약) 중지
        yield 0.3
        assert not 전투.자동전투 and 버튼("자동전투")
        if not gf.전투_종료됨(상태) and 상태["전투상태"] is not None:
            assert not 버튼("일반공격").disabled or not gf.아군_차례인가(상태)
        결과["단계"].append("자동전투 켜기 -> 버튼 잠금 -> 중지")

        # 다시 켜면 전투가 끝날 때까지 스스로 진행한다(결과 팝업이 뜬다)
        if 상태["전투상태"] is not None:
            버튼("자동전투").dispatch("on_release")
            for _ in range(100):
                if 상태["전투상태"] is None:
                    break
                yield 0.2
            assert 상태["전투상태"] is None, "자동전투가 전투를 끝내지 못했다"
            assert not 전투.자동전투
            _찍기("battle_auto_end")
            _팝업_닫기()
        결과["단계"].append("자동전투로 전투 끝까지 진행 -> 결과 팝업")

    def _단계_몬스터_크기(self, 상태, 매니저, 전투):
        """몬스터 크기 배율/발바닥 맞춤/그리는 순서, 아군 그림 크기"""
        # 몬스터 크기: 소형 1/2 / 중형 3/4 / 대형 1배(칸 전체), 칸 바닥(발바닥) 맞춤, 대형이 뒤(먼저 그림)
        from kivy.graphics import Rectangle

        gf.전투_시작(상태, ["고블린", "타우 비스트", "타우 아미"], 레벨=6, 차수=2)
        support.반응_처리(상태)
        _아군_차례로(상태)
        매니저.current = "전투"
        전투.갱신(신규=True)
        yield 0.6
        적 = gf.적_목록(상태)
        사각형 = [
            c for c in 전투.적그래픽행.canvas.after.children if isinstance(c, Rectangle)
        ]
        assert len(사각형) == 3, len(사각형)
        칸들 = [칸 for 칸, _, _ in 전투._적그림목록]
        for 사각, (칸, 경로, 배율), (_, p) in zip(
            사각형, 전투._적그림목록, gf.적_그리기_순서(적)
        ):
            tw, th = 사각.texture.size
            맞춤 = min(칸.width / tw, 칸.height / th)
            assert abs(사각.size[1] - th * 맞춤 * 배율) < 1, (p["이름"], 사각.size)
            assert abs(사각.pos[1] - 칸.y) < 1  # 발바닥 = 칸 바닥
            assert abs(사각.pos[0] + 사각.size[0] / 2 - 칸.center_x) < 1
        assert [p["원본"]["몬스터명"] for _, p in gf.적_그리기_순서(적)][
            0
        ] == "타우 비스트"
        assert len(set(칸들)) == 3
        # 아군 그림: 칸에 꽉 맞춘 크기의 2/3, 칸 바닥 가운데
        from kivy.uix.image import Image as 그림

        아군그림 = [
            w for w in 전투.아군그래픽행.walk(restrict=True) if isinstance(w, 그림)
        ]
        assert 아군그림, "아군 그림 없음"
        for 이미지 in 아군그림:
            틀 = 이미지.parent
            tw, th = 이미지.texture_size
            맞춤 = min(틀.width / tw, 틀.height / th) * 2 / 3
            assert abs(이미지.height - th * 맞춤) < 1, (이미지.size, 틀.size)
            assert abs(이미지.y - 틀.y) < 1 and abs(이미지.center_x - 틀.center_x) < 1
        _찍기("battle_monster_size")
        결과["단계"].append(
            "몬스터 크기 배율(소 1/2, 중 3/4, 대 1) + 발바닥 맞춤 + 대형이 뒤, 아군 그림 2/3 바닥 맞춤"
        )

    def _단계_황금고블린_도망(self, 상태, 매니저, 전투):
        """황금 고블린 도망 -> (도망) 표시, 그림 없음, 적이 도망쳤다! -> 던전"""
        # 황금 고블린(도망턴 5): 자기 턴이 5번 끝나면 도망 -> 이름표 "(도망)", 그림 없음,
        # 적이 모두 도망쳤으면 "적이 도망쳤다!" 팝업 -> [확인] -> 던전
        _팝업_닫기()
        gf.전투_시작(상태, ["황금 고블린"], 레벨=3, 차수=1)
        support.반응_처리(상태)
        매니저.current = "전투"
        황금 = gf.적_목록(상태)[0]
        황금["끝난턴수"] = 4
        상태["전투상태"]["현재턴"] = 상태["전투상태"]["참가자"].index(황금)
        상태["전투상태"]["현재턴_행동완료"] = True
        gf.턴_넘기기(상태)
        assert 황금["도망"] and 상태["전투상태"]["종료"] == "적도망"
        전투.갱신(신규=True)
        yield 0.6
        이름표 = [
            w.text for w in 전투.적상태틀.walk(restrict=True) if hasattr(w, "text")
        ]
        assert any("(도망)" in t for t in 이름표), 이름표
        assert all(경로 is None for _, 경로, _ in 전투._적그림목록)
        글 = next(t for t in _팝업글() if t.startswith("적이 도망쳤다!"))
        assert 글 == "적이 도망쳤다!", 글
        _찍기("battle_enemy_fled")
        _확인_누르기()
        yield 0.5
        assert 매니저.current == "던전", 매니저.current
        _팝업_닫기()
        yield 0.3
        _찍기(
            "dungeon_map"
        )  # 던전 지도(바닥/나무·게이트/플레이어) - 그리기 변경 전후 비교용
        결과["단계"].append(
            "황금 고블린 도망 -> (도망) 표시, 그림 없음, 적이 도망쳤다! -> 던전"
        )

    def _단계_주점(self, 매니저):
        """주점 - 영입(숙소로)/대기/합류/추방 확인 팝업"""
        # 주점: 영입(파티가 꽉 차 있으면 숙소로) -> 대기 -> 합류 -> 추방(확인 팝업)
        _팝업_닫기()
        매니저.current = "마을"
        yield 0.3
        assert any(
            getattr(w, "text", "") == "주점"
            for w in 매니저.get_screen("마을").walk(restrict=True)
        ), "마을에 주점 버튼 없음"
        매니저.current = "주점"
        주점 = 매니저.get_screen("주점")
        상태 = self.게임상태
        상태["소지품"]["골드"] = 1000
        주점.갱신()
        yield 0.3
        _찍기("tavern")

        def 팝업버튼(글):
            팝업 = list(Window.children)[0]
            return next(
                w
                for w in 팝업.walk(restrict=True)
                if isinstance(w, Button) and w.text.startswith(글)
            )

        주점._영입_팝업()
        yield 0.5
        _찍기("tavern_recruit")
        이름칸 = next(
            w
            for w in list(Window.children)[0].walk(restrict=True)
            if w.__class__.__name__ == "TextInput"
        )
        이름칸.text = "새동료"
        # 영입 팝업에서도 능력치 칸 터치로 주/보조/약점스탯을 고른다(귀검사 기본값에서
        # 근력 주 -> 일반, 건강 일반 -> 주)
        스탯판 = next(
            w
            for w in list(Window.children)[0].walk(restrict=True)
            if w.__class__.__name__ == "스탯고르기판"
        )
        스탯판.칸["근력"].dispatch("on_release")
        스탯판.칸["건강"].dispatch("on_release")
        assert 스탯판.칸["건강"].text.endswith(" 13"), 스탯판.칸["건강"].text
        yield 0.3
        _찍기("tavern_recruit_stat_pick")
        팝업버튼("영입").dispatch("on_release")
        yield 0.3
        숙소 = gf.숙소_목록(상태)
        assert [c["캐릭터명"] for c in 숙소] == ["새동료"], 주점.안내라벨.text
        assert (숙소[0]["주스탯"], 숙소[0]["건강"]) == ("건강", 13)
        결과["단계"].append(
            "주점 영입 스탯 고르기(터치로 주스탯 변경 -> 영입 캐릭터에 반영)"
        )
        assert 상태["소지품"]["골드"] == 1000 - gf.영입_비용

        파티 = 상태["파티"]["파티원"]
        첫째 = 파티[0]
        주점._대기_팝업()
        yield 0.3
        팝업버튼(첫째["캐릭터명"]).dispatch("on_release")
        yield 0.3
        assert 첫째 in 숙소 and 첫째 not in 파티 and len(Window.children) == 1

        주점._합류_팝업()
        yield 0.3
        _찍기("tavern_join")
        팝업버튼(첫째["캐릭터명"]).dispatch("on_release")
        yield 0.3
        assert 첫째 in 파티 and 첫째 not in 숙소

        새동료 = 숙소[0]
        주점._추방_팝업()
        yield 0.3
        팝업버튼("새동료").dispatch("on_release")
        yield 0.3
        assert list(Window.children)[0].title == "파티원 추방"
        _찍기("tavern_expel_confirm")
        팝업버튼("추방").dispatch("on_release")
        yield 0.3
        assert 새동료 not in 숙소 and len(Window.children) == 1
        assert "추방했습니다" in 주점.안내라벨.text, 주점.안내라벨.text
        _찍기("tavern_after")
        결과["단계"].append("주점(영입 -> 숙소, 대기, 합류, 추방 확인 팝업)")

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
        결과["단계"].append(
            "감옥 보스전은 한 번 클리어하면 보스 칭호 몬스터 그림(1칸)으로"
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

    def _단계_세이브(self, 상태, 매니저):
        """세이브 슬롯(새버전/손상/복구본)과 앱 시작 때 세이브 폴더 이전"""
        # 세이브 슬롯: 슬롯 하나가 망가져도 메인 메뉴/슬롯 목록이 열린다(구조 점검 W-1).
        # 실제 game/saves/ 대신 임시 폴더를 쓴다.
        세이브폴더 = tempfile.mkdtemp(prefix="ui_smoke_saves_")
        원래폴더 = save_system._세이브_폴더
        save_system._세이브_폴더 = lambda: 세이브폴더
        try:
            self.게임상태 = 상태
            gf.게임_저장(상태, 1)
            경로1 = os.path.join(세이브폴더, "slot_1.json")
            with open(경로1, encoding="utf-8") as f:
                저장1 = json.load(f)
            저장1["버전"] = save_system.세이브_버전 + 1  # 더 새로운 앱이 저장한 세이브
            with open(경로1, "w", encoding="utf-8") as f:
                json.dump(저장1, f, ensure_ascii=False)
            gf.게임_저장(상태, 3)
            gf.게임_저장(상태, 3)  # 두 번째 저장이 .bak을 만든다
            with open(
                os.path.join(세이브폴더, "slot_2.json"), "w", encoding="utf-8"
            ) as f:
                f.write('{"플레이어": {"파')  # 쓰다 끊긴 파일, 백업 없음 -> 손상
            with open(
                os.path.join(세이브폴더, "slot_3.json"), "w", encoding="utf-8"
            ) as f:
                f.write('{"플레이어": {"파')  # 본 파일만 끊김, .bak이 있음 -> 복구본
            매니저.current = "메인메뉴"
            yield 0.3
            assert not 매니저.get_screen("메인메뉴").불러오기버튼.disabled
            매니저.current = "불러오기목록"
            yield 0.4
            _찍기("save_slots_corrupt")
            불러오기 = 매니저.get_screen("불러오기목록")
            줄들 = list(reversed(불러오기.목록틀.children))  # 위에서 아래(슬롯 1, 2, 3)

            def 줄_글(줄):
                return next(
                    w.text for w in 줄.children if w.__class__.__name__ == "Label"
                )

            def 줄_버튼(줄):
                return next(w for w in 줄.children if isinstance(w, Button))

            assert "(손상됨" in 줄_글(줄들[1]), 줄_글(줄들[1])
            assert "[백업]" in 줄_글(줄들[2]), 줄_글(줄들[2])
            assert "더 새로운 버전" in 줄_글(줄들[0]), 줄_글(줄들[0])
            assert 줄_버튼(줄들[0]).disabled and not 줄_버튼(줄들[2]).disabled
            assert 줄_버튼(줄들[1]).disabled, "손상 슬롯은 불러올 수 없다"

            불러오기._선택(2)  # 막혀 있어도 호출되면 앱이 죽지 않고 안내만 한다
            assert 매니저.current == "불러오기목록" and "손상" in 불러오기.안내라벨.text
            불러오기._선택(3)  # 백업으로 불러온다
            assert 매니저.current == "마을"

            self.게임상태 = 상태
            매니저.current = "저장목록"
            yield 0.3
            매니저.get_screen("저장목록")._선택(2)  # 손상 슬롯 덮어쓰기
            yield 0.2
            assert save_system.세이브_요약(2).get("손상") is None
            assert "저장했습니다" in 매니저.get_screen("저장목록").안내라벨.text
            결과["단계"].append(
                "세이브 슬롯(새버전/손상/복구본 표시, 메인 메뉴 정상, 손상 슬롯 덮어쓰기)"
            )

            # 앱 시작 때 세이브 폴더를 앱 데이터 폴더로 옮기고 옛 세이브를 한 번 가져온다(임시 폴더만 씀)
            앱데이터 = tempfile.mkdtemp(prefix="ui_smoke_appdata_")
            옛위치 = tempfile.mkdtemp(prefix="ui_smoke_legacy_")
            with open(os.path.join(옛위치, "slot_2.json"), "w", encoding="utf-8") as f:
                f.write("{}")

            # App을 하나 더 만들면 App.get_running_app()이 바뀌므로 자리표시 객체로 부른다
            임시앱 = types.SimpleNamespace(user_data_dir=앱데이터)

            save_system._세이브_폴더 = 원래폴더  # 임시 폴더 바꿔치기를 잠깐 푼다
            기본폴더 = save_system._기본_세이브_폴더
            save_system._기본_세이브_폴더 = lambda: 옛위치
            try:
                main.DnfMobileApp._세이브_폴더_준비(임시앱)
                assert save_system._세이브_폴더() == os.path.join(앱데이터, "saves")
                assert os.path.isfile(os.path.join(앱데이터, "saves", "slot_2.json"))
                assert os.path.isfile(os.path.join(옛위치, "slot_2.json")), (
                    "옛 파일은 남는다"
                )
            finally:
                save_system._기본_세이브_폴더 = 기본폴더
                save_system._폴더_재정의 = None
                save_system._세이브_폴더 = lambda: 세이브폴더
                shutil.rmtree(앱데이터, ignore_errors=True)
                shutil.rmtree(옛위치, ignore_errors=True)
            결과["단계"].append(
                "앱 시작 시 세이브 폴더를 앱 데이터 폴더로(옛 세이브 한 번 복사)"
            )
        finally:
            save_system._세이브_폴더 = 원래폴더
            shutil.rmtree(세이브폴더, ignore_errors=True)
            매니저.current = "마을"

    def _단계_설정(self, 매니저):
        """설정 파일이 없거나 깨졌거나 쓸 수 없어도 설정 화면/설정 저장이 죽지 않는다"""
        폴더 = tempfile.mkdtemp(prefix="ui_smoke_settings_")
        경로 = os.path.join(폴더, "설정.json")
        원래경로 = screens_common._설정_경로
        원래반응 = gf.반응_자동_여부()
        원래연계 = gf.연계_자동_여부()
        screens_common._설정_경로 = lambda: 경로
        try:
            assert screens_common.설정_불러오기() == {}  # 파일 없음
            for 내용 in (
                '{"반응자',
                "[1, 2]",
                "\udcff",
            ):  # 끊긴 JSON, 딕셔너리 아님, 깨진 글자
                with open(경로, "w", encoding="utf-8", errors="surrogateescape") as f:
                    f.write(내용)
                assert screens_common.설정_불러오기() == {}, 내용
            screens_common.설정_저장(
                "반응자동", True
            )  # 깨진 파일을 새 설정으로 덮어쓴다
            with open(경로, encoding="utf-8") as f:
                assert json.load(f) == {"반응자동": True}
            assert screens_common.설정_불러오기() == {"반응자동": True}
            assert gf.반응_자동_여부()
            screens_common._설정_경로 = lambda: (
                폴더
            )  # 폴더라 쓸 수 없다 -> 조용히 넘어간다
            screens_common.설정_저장("반응자동", False)
            screens_common._설정_경로 = lambda: 경로
            매니저.current = "설정"
            yield 0.3
            _찍기("settings")
            # 줄마다 체크박스 두 개 중 하나 - 고르면 컨트롤러 값과 설정 파일에 들어간다
            설정 = 매니저.get_screen("설정")
            for 키, 값, 읽기 in (
                ("자동전투방식", "전력전투", gf.자동전투_방식),
                ("자동전투포션", True, gf.자동전투_포션_여부),
                ("전투로그방식", "자세하게", gf.전투로그_방식),
                ("반응자동", True, gf.반응_자동_여부),
                ("연계자동", False, gf.연계_자동_여부),
            ):
                설정.체크박스[(키, 값)].active = True
                yield 0.1
                assert 읽기() == 값, (키, 읽기())
                with open(경로, encoding="utf-8") as f:
                    assert json.load(f)[키] == 값, 키
                같은줄 = [c for (k, _), c in 설정.체크박스.items() if k == 키]
                assert sum(c.active for c in 같은줄) == 1, 키  # 한 줄에 하나만
            _찍기("settings_checked")
            결과["단계"].append(
                "설정 파일(없음/깨짐/딕셔너리 아님/쓰기 실패) - 기본값으로 계속, "
                "설정 화면 체크박스(반응 자동/연계 자동/자동전투/자동전투 포션/전투로그) 하나씩 골라 저장"
            )
        finally:
            screens_common._설정_경로 = 원래경로
            gf.반응_자동_설정(원래반응)
            gf.연계_자동_설정(원래연계)
            gf.자동전투_방식_설정("일반공격")
            gf.자동전투_포션_설정(False)
            gf.전투로그_방식_설정("간략하게")
            shutil.rmtree(폴더, ignore_errors=True)
            매니저.current = "마을"

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

        # 던전: 1줄 파티원 상자, 2~4줄 지도 970, 하단 1줄 위치/걸음수
        gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
        매니저.current = "던전"
        던전 = 매니저.get_screen("던전")
        던전.갱신()
        yield 0.4
        파티칸(던전.파티줄, 파티수)
        assert abs(던전.지도위젯.height - sc.상단_그림_높이) < 1
        assert abs(던전.지도위젯.y - sc.하단_높이) < 1
        assert 던전.상태라벨.text.startswith("위치"), 던전.상태라벨.text
        _찍기("layout_dungeon")

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
        """던전 이동 목록 - 바로 앞 번호 던전 보스를 안 깬 던전은 비활성"""
        진행도 = 상태["진행도"]
        원래 = (진행도["현재마을"], set(진행도.get("클리어한던전", set())))
        try:
            진행도["클리어한던전"] = {
                "dungeon_01A_D01_Lorien",
                "dungeon_01A_D02_Hollow_Lorien",
            }
            진행도["현재마을"] = "헨돈마이어"
            매니저.current = "던전목록"
            yield 0.4
            버튼 = {
                w.text: w.disabled
                for w in 매니저.current_screen.목록틀.walk(restrict=True)
                if isinstance(w, Button)
            }
            assert 버튼 == {"머크우드": False, "선더랜드": True, "그락카락": True}, 버튼
            _찍기("dungeon_list_locked")
            진행도["클리어한던전"].add("dungeon_01A_D04_Hollow_mirkwood")
            매니저.current_screen.갱신()
            yield 0.3
            버튼 = {
                w.text: w.disabled
                for w in 매니저.current_screen.목록틀.walk(restrict=True)
                if isinstance(w, Button)
            }
            assert 버튼["선더랜드"] is False and 버튼["그락카락"] is True, 버튼
            결과["단계"].append("던전 이동 목록 - 앞 던전 보스 전엔 비활성, 깨면 활성")
        finally:
            진행도["현재마을"], 진행도["클리어한던전"] = 원래
            매니저.current = "마을"

    def _단계_던전_스킬(self, 상태, 매니저):
        """던전 화면 [스킬](사용자 지정 2026-10-19 - 유루캠 "던전 캠핑"): 방향판 오른쪽 아래 칸.
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
            # 전환스킬 프렌지(버서커 퍽 광기 #247): 줄 끝이 (꺼짐) -> 누르면 켜지고 다시 열면 (켜짐)
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
            # 전환스킬 나선의 넨(넨마스터 골드 스킬 #280): 던전에서는 MP 없이 켠다
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
        """마을 [스킬](#283): 전환스킬 줄 "이름 - 스킬  (꺼짐)"을 누르면 MP 없이 켜지고 다시 열면 (켜짐),
        한 번 더 누르면 꺼진다. 전환스킬이 없으면 팝업 없이 안내 문구."""
        귀검사 = next(c for c in 상태["파티"]["파티원"] if c["직업"] == "귀검사")
        원래 = list(귀검사["보유스킬"])
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
            결과["단계"].append(
                "마을 [스킬]: 전환스킬이 없으면 안내 문구. 나선의 넨 (꺼짐) -> MP 없이 켜짐, "
                "다시 열면 (켜짐) -> 누르면 꺼짐"
            )
        finally:
            _팝업_닫기()
            귀검사["보유스킬"][:] = 원래
            귀검사.pop("켜진특성", None)
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

    def _단계_감옥_대상팝업(self, 상태, 매니저):
        """케라하의 얼음감옥(사용자 지정 2026-10-14): 감옥은 적 그림 칸에는 없고 대상 고르기 팝업에만
        나온다. 다른 아군이 팝업에서 감옥을 골라 때릴 수 있다."""
        from game.system.combat import monster_actions

        gf.전투_시작(상태, ["결빙의 케라하"], 레벨=4, 차수=1)
        support.반응_처리(상태)
        전투상태 = 상태["전투상태"]
        케라하 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
        귀검사 = next(
            p
            for p in 전투상태["참가자"]
            if (p.get("원본") or {}).get("직업") == "귀검사"
        )
        얼음감옥 = gf.몬스터목록["결빙의 케라하"]["패턴"][5]
        monster_actions.감옥_걸기(전투상태, 케라하, 귀검사, 얼음감옥, "'얼음감옥' 패턴")
        감옥 = next(p for p in 전투상태["참가자"] if p.get("감옥"))
        p = _차례(전투상태, "거너")
        전투 = 매니저.get_screen("전투")
        전투.갱신(신규=True)
        매니저.current = "전투"
        yield 0.5
        _팝업_닫기()
        적칸글 = [
            w.text
            for w in 전투.적상태틀.walk(restrict=True)
            if isinstance(w, main.Label)
        ]
        assert not any(감옥["이름"] in t for t in 적칸글), 적칸글  # 적 그림 칸에는 없다
        # 갇힌 귀검사 그림 칸: 얼음감옥(뒤) -> 캐릭터 -> 얼음감옥(앞) 순으로 겹친다(뒤가 먼저 그려진다)
        틀 = next(
            w
            for w in 전투._그림칸[귀검사["id"]].walk(restrict=True)
            if w.__class__.__name__ == "FloatLayout"
        )
        겹침 = [getattr(w, "감옥그림", "캐릭터") for w in reversed(틀.children)]
        assert 겹침 == [
            "asset_monster_ice_prison_back.webp",
            "캐릭터",
            "asset_monster_ice_prison_front.webp",
        ], 겹침
        뒤, 캐릭터, 앞 = reversed(틀.children)
        assert 뒤.y == 틀.y and 앞.y == 틀.y and 캐릭터.y == 틀.y  # 같은 바닥
        assert 뒤.width <= 틀.width + 1 and 앞.width <= 틀.width + 1
        다른칸 = [
            w
            for k, 칸 in 전투._그림칸.items()
            if k != 귀검사["id"]
            for w in 칸.walk(restrict=True)
            if hasattr(w, "감옥그림")
        ]
        assert not 다른칸, "갇히지 않은 아군 칸에는 감옥 그림이 없다"
        _찍기("battle_prison_images")
        전투._일반공격_클릭()
        yield 0.3
        글들 = [b.text for b in _대상버튼들()]
        assert f"{감옥['이름']}\n{gf.적_HP표시(상태, 감옥)}" in 글들, 글들
        assert 글들[-1] == "취소", 글들
        _찍기("battle_prison_popup")
        감옥HP = 감옥["현재HP"]
        버튼 = next(b for b in _대상버튼들() if b.text.startswith(감옥["이름"]))
        버튼.trigger_action(duration=0)
        for _ in range(20):
            yield 0.05
            if _팝업수() == 0 and any(
                isinstance(x, dict) and x.get("대상") == 감옥["이름"]
                for x in 전투상태["로그"]
            ):
                break
        assert any(
            isinstance(x, dict)
            and x.get("공격자") == p["이름"]
            and x.get("대상") == 감옥["이름"]
            for x in 전투상태["로그"]
        ), "팝업에서 고른 감옥을 공격한다"
        assert 감옥["현재HP"] <= 감옥HP
        # 운석은 뒤 그림만 - 크루세이더(프리스트)에게 건다
        프리스트 = next(
            p
            for p in 전투상태["참가자"]
            if (p.get("원본") or {}).get("직업") == "프리스트"
        )
        운석폭발 = gf.몬스터목록["화염의 비노슈"]["패턴"][5]
        monster_actions.감옥_걸기(
            전투상태, 케라하, 프리스트, 운석폭발, "'운석폭발' 패턴"
        )
        전투.갱신()
        yield 0.5
        틀 = next(
            w
            for w in 전투._그림칸[프리스트["id"]].walk(restrict=True)
            if w.__class__.__name__ == "FloatLayout"
        )
        겹침 = [getattr(w, "감옥그림", "캐릭터") for w in reversed(틀.children)]
        assert 겹침 == ["asset_monster_meteor_prison.webp", "캐릭터"], 겹침
        _찍기("battle_prison_meteor")
        결과["단계"].append(
            "얼음감옥: 갇힌 아군 칸에 뒤/앞 그림, 적 칸에는 없고 대상 팝업에 나오며 골라서 공격. 운석은 뒤 그림만"
        )

    def _단계_프렌드_실드(self, 상태, 매니저):
        """프렌드 실드(#310): 반응 자동이 꺼져 있으면 적의 단일 공격 대상이 될 때 반응 팝업에 살아 있는
        아군이 한 명당 한 줄("프렌드 실드 → 이름")로 나오고(쓰러진 아군은 없다), 고른 아군이 대신 맞는다."""
        from game.system import monster_ai
        from game.system.combat import monster_actions

        gf.전투_시작(
            상태, ["결빙의 케라하"], 레벨=4, 차수=1
        )  # 고블린은 시작 반응에 쓰러진다
        support.반응_처리(상태)
        전투상태 = 상태["전투상태"]
        고블린 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
        아군 = [p for p in 전투상태["참가자"] if p["진영"] == "아군"]
        귀검사 = next(p for p in 아군 if p["원본"]["직업"] == "귀검사")
        격투가, 거너 = [p for p in 아군 if p is not 귀검사][
            :2
        ]  # 받을 아군, 쓰러진 아군
        귀검사["원본"]["보유스킬"].append("프렌드 실드")
        귀검사["행동자원"]["반응행동"] = 1
        거너["생존"] = False  # 쓰러진 아군은 고를 수 없다
        _아군_차례로(상태)
        전투 = 매니저.get_screen("전투")
        전투.갱신(신규=True)
        매니저.current = "전투"
        yield 0.5
        _팝업_닫기()
        패턴 = {"이름": "시험", "타겟": "적단일", "명중률": "근력판정", "데미지": "1"}
        원래 = (monster_ai.행동_선택, monster_ai.타겟_선택, gf.반응_자동_여부())
        monster_ai.행동_선택 = lambda m: 패턴
        monster_ai.타겟_선택 = lambda *a, **k: 귀검사
        gf.반응_자동_설정(False)
        try:
            전투._엔진_실행(lambda: monster_actions.몬스터_턴_실행(전투상태, 고블린))
            for _ in range(40):
                yield 0.05
                if _팝업수() == 1:
                    break
            글들 = [b.text for b in _대상버튼들()]
            줄 = [t for t in 글들 if t.startswith("프렌드 실드 → ")]
            assert any(격투가["이름"] in t for t in 줄), 글들
            assert not any(거너["이름"] in t for t in 줄), 글들
            assert 글들[-1] == "사용 안 함", 글들
            _찍기("battle_friend_shield_popup")
            버튼 = next(b for b in _대상버튼들() if 격투가["이름"] in b.text)
            버튼.trigger_action(duration=0)
            for _ in range(40):
                yield 0.05
                if not 전투._엔진중:
                    break
        finally:
            monster_ai.행동_선택, monster_ai.타겟_선택 = 원래[:2]
            gf.반응_자동_설정(원래[2])
            거너["생존"] = True
        assert not 전투._엔진중
        타격 = [
            x
            for x in 전투상태["로그"]
            if isinstance(x, dict) and x.get("공격자") == 고블린["이름"] and "대상" in x
        ]
        assert 타격 and 타격[-1]["대상"] == 격투가["이름"], 타격
        assert 귀검사["행동자원"]["반응행동"] == 0
        결과["단계"].append(
            "프렌드 실드: 단일 공격 대상이 되면 반응 팝업에 살아 있는 아군만 한 줄씩, 고른 아군이 대신 맞음"
        )

    def _단계_인형(self, 상태, 매니저):
        """인형사(사용자 지정 2026-10-19): 전투 [아이템]에서 인형을 쓰면(행동 없음) 아군 칸이 4개에서
        5개가 되고 맨 오른쪽 칸에 인형 이름과 HP(MP 없음), 그림 칸은 비어 있다."""
        gf.전투_시작(상태, ["고블린"], 레벨=2, 차수=1)
        support.반응_처리(상태)
        전투상태 = 상태["전투상태"]
        p = _차례(전투상태, "귀검사")
        상태["소지품"]["소모품"]["28호"] = 1
        전투 = 매니저.get_screen("전투")
        전투.갱신(신규=True)
        매니저.current = "전투"
        yield 0.5
        _팝업_닫기()
        assert len(전투.아군상태틀.children) == 4, len(전투.아군상태틀.children)
        행동 = dict(p["행동자원"])
        전투._아이템_클릭()
        yield 0.3
        버튼 = [b for b in _대상버튼들() if b.text.startswith("28호")]
        assert 버튼 and "(행동 없음)" in 버튼[0].text, [b.text for b in _대상버튼들()]
        _찍기("battle_doll_popup")
        버튼[0].trigger_action(duration=0)
        yield 0.5
        assert p["행동자원"] == 행동, p["행동자원"]
        전투.갱신()
        yield 0.3
        상태칸 = list(reversed(전투.아군상태틀.children))
        그림칸 = list(reversed(전투.아군그래픽행.children))
        assert len(상태칸) == 5 and len(그림칸) == 5, (len(상태칸), len(그림칸))
        글 = [
            w.text for w in 상태칸[-1].walk(restrict=True) if isinstance(w, main.Label)
        ]
        assert 글[0] == "28호" and 글[1].startswith("HP ") and len(글) == 2, (
            글
        )  # MP 줄 없음
        # 5칸이 같은 폭으로 한 줄 안에 들어간다
        assert len({round(c.width) for c in 상태칸}) == 1
        assert 상태칸[-1].right <= 전투.아군상태틀.right + 1
        assert 상태칸[0].x >= 전투.아군상태틀.x - 1
        인형칸 = 전투._그림칸[
            next(q["id"] for q in gf.아군_목록(상태) if q.get("인형"))
        ]
        assert 인형칸 is 그림칸[-1]
        _찍기("battle_doll")
        상태["파티"]["인형"] = None  # 다음 단계 전투에 끼지 않게
        결과["단계"].append(
            "인형: 전투 [아이템] 28호(행동 없음) -> 아군 칸 5개, 맨 오른쪽에 이름/HP(MP 없음), 그림 칸 비움"
        )

    def _단계_란마(self, 상태, 매니저):
        """란마 1/2(사용자 지정 2026-10-19): 수속성 공격에 맞으면 전투 화면 그림이 여성 그림(011m -> 011f)으로,
        화속성에 맞으면 남성 그림으로 돌아온다. 반대 성별 그림이 없는 캐릭터는 그림만 그대로다."""
        from game.data.ability.job_ability_0000 import 특성목록 as 공용특성
        from game.system import effect_engine
        from game.system.combat import damage

        귀검사 = next(c for c in 상태["파티"]["파티원"] if c["직업"] == "귀검사")
        원래 = (list(귀검사["보유특성"]), 귀검사.get("성별"))
        try:
            귀검사["성별"] = "m"
            for 이름 in ("낭익천", "남익천"):
                effect_engine.특성_부여(귀검사, 이름, 공용특성[이름])
            gf.전투_시작(상태, ["고블린"], 레벨=2, 차수=1)
            전투상태 = 상태["전투상태"]
            p = next(x for x in 전투상태["참가자"] if x.get("원본") is 귀검사)
            적 = next(x for x in 전투상태["참가자"] if x["진영"] == "적")
            # 반응 사격(패스티스트 건) 굴림에 고블린이 쓰러져 전투가 끝나면 그림이 바뀌지 않는다 - 굴림과 무관하게
            적["현재HP"] = 적["최대HP"] = 999
            support.반응_처리(상태)
            _아군_차례로(상태)
            전투 = 매니저.get_screen("전투")
            전투.갱신(신규=True)
            매니저.current = "전투"
            yield 0.5
            _팝업_닫기()

            def 그림():
                return next(
                    w.source
                    for w in 전투._그림칸[p["id"]].walk(restrict=True)
                    if "asset_sd_character" in (getattr(w, "source", "") or "")
                )

            assert 그림().endswith("011m.webp"), 그림()
            판정 = {"성공": True, "자연눈": 10, "치명타": False, "자동실패": False}
            damage.피격_처리(전투상태, 적, p, 판정, 속성="수속성")
            전투.갱신()
            yield 0.4
            assert 귀검사["란마성별"] == "f" and 그림().endswith("011f.webp"), 그림()
            _찍기("battle_ranma_female")
            damage.피격_처리(전투상태, 적, p, 판정, 속성="화속성")
            전투.갱신()
            yield 0.3
            assert 그림().endswith("011m.webp"), 그림()
            결과["단계"].append(
                "란마 1/2: 수속성에 맞으면 전투 그림 011m -> 011f, 화속성에 맞으면 011m"
            )
        finally:
            귀검사["보유특성"][:] = 원래[0]
            귀검사["성별"] = 원래[1]
            귀검사.pop("란마성별", None)
            상태["전투상태"] = None
            매니저.current = "마을"

    def _단계_축염포(self, 상태, 매니저):
        """축염포(넨마스터 #280): 스킬을 쓰면 턴이 바로 끝나고, 남은 순서가 돈 뒤 밀린 차례에 발사되어
        넨마스터 차례로 돌아온다(캐스팅 표시가 사라지고 보조행동이 남아 있다)."""
        다른 = support.새게임([("", "격투가"), ("", "귀검사")])
        nm = 다른["파티"]["파티원"][0]
        for c in 다른["파티"]["파티원"]:
            support.성장(
                다른,
                c,
                8,
                전직={"격투가": "넨마스터", "귀검사": "웨펀마스터"}[c["직업"]],
            )
        원래 = self.게임상태
        try:
            self.게임상태 = 다른
            gf.전투_시작(다른, ["고블린", "고블린", "고블린"], 레벨=2, 차수=1)
            support.반응_처리(다른)
            전투상태 = 다른["전투상태"]
            for e in 전투상태["참가자"]:
                if e["진영"] == "적":
                    e["현재HP"] = e["최대HP"] = 999
            n = next(p for p in 전투상태["참가자"] if p["원본"] is nm)
            for _ in range(40):
                if gf.현재_턴_참가자(다른) is n:
                    break
                gf.턴_넘기기(다른)
            assert gf.현재_턴_참가자(다른) is n
            n["현재MP"] = 50
            전투 = 매니저.get_screen("전투")
            전투.갱신(신규=True)
            매니저.current = "전투"
            yield 0.5
            _팝업_닫기()
            적 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
            전투._스킬_실행("축염포", 적)
            yield 1.0
            for _ in range(10):  # 밀린 차례 전에 아군(웨펀마스터) 차례가 오면 넘긴다
                if gf.현재_턴_참가자(다른) is n:
                    break
                gf.턴_넘기기(다른)
            로그 = [e for e in 전투상태["로그"] if isinstance(e, dict)]
            assert any("캐스팅을 시작" in str(e.get("비고", "")) for e in 로그)
            assert any(e.get("스킬") == "축염포" and "타격" in e for e in 로그), 로그[
                -3:
            ]
            assert gf.현재_턴_참가자(다른) is n
            assert not any(s["이름"] == "캐스팅" for s in n["상태이상"])
            assert n["행동자원"].get("보조행동", 0) >= 1
            _찍기("battle_charged_blast")
            결과["단계"].append(
                "축염포: 쓰면 턴이 끝나고 밀린 차례에 발사, 넨마스터 차례로 돌아와 보조행동이 남음"
            )
        finally:
            self.게임상태 = 원래
            매니저.current = "마을"

    def _단계_연계_팝업(self, 매니저):
        """연계스킬(2026-10-22): 연계 자동을 끄면 수플렉스가 맞았을 때 "연계 - 이름" 팝업이 뜨고, 수플렉스
        썬더를 고르면 보조행동을 써서 같은 적에게 이어 친다."""
        다른 = support.새게임([("", "격투가"), ("", "귀검사")])
        nm = 다른["파티"]["파티원"][0]
        for c in 다른["파티"]["파티원"]:
            support.성장(
                다른,
                c,
                8,
                전직={"격투가": "넨마스터", "귀검사": "웨펀마스터"}[c["직업"]],
                스킬습득=c is nm,
            )
        원래 = (self.게임상태, gf.연계_자동_여부(), rng.주사위.randint)
        try:
            self.게임상태 = 다른
            gf.전투_시작(다른, ["고블린", "고블린", "고블린"], 레벨=2, 차수=1)
            support.반응_처리(다른)
            전투상태 = 다른["전투상태"]
            for e in 전투상태["참가자"]:
                if e["진영"] == "적":
                    e["현재HP"] = e["최대HP"] = 999
            n = next(p for p in 전투상태["참가자"] if p["원본"] is nm)
            for _ in range(40):
                if gf.현재_턴_참가자(다른) is n:
                    break
                gf.턴_넘기기(다른)
            assert gf.현재_턴_참가자(다른) is n
            n["현재MP"] = 50
            전투 = 매니저.get_screen("전투")
            전투.갱신(신규=True)
            매니저.current = "전투"
            yield 0.5
            _팝업_닫기()
            gf.연계_자동_설정(False)
            rng.주사위.randint = lambda a, b: min(max(15, a), b)  # 수플렉스가 맞게
            적 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
            전투._스킬_실행("수플렉스", 적)
            for _ in range(40):
                yield 0.05
                if _팝업수() == 1:
                    break
            팝업 = Window.children[0]
            assert 팝업.title.startswith("연계 - "), 팝업.title
            글들 = [b.text for b in _대상버튼들()]
            assert 글들[0].startswith("수플렉스 썬더") and 글들[-1] == "사용 안 함", (
                글들
            )
            _찍기("battle_chain_skill_popup")
            _대상버튼들()[0].trigger_action(duration=0)
            for _ in range(40):
                yield 0.05
                if not 전투._엔진중:
                    break
            assert not 전투._엔진중
            로그 = [e for e in 전투상태["로그"] if isinstance(e, dict)]
            assert any(e.get("스킬") == "수플렉스 썬더" and "타격" in e for e in 로그)
            assert n["행동자원"]["보조행동"] == 0
            결과["단계"].append(
                "연계 팝업: 연계 자동을 끄면 수플렉스 명중 뒤 '연계' 팝업, 고르면 수플렉스 썬더가 보조행동으로 나감"
            )
        finally:
            self.게임상태, 연계, rng.주사위.randint = 원래
            gf.연계_자동_설정(연계)
            매니저.current = "마을"

    def _단계_넨가드_채널링(self, 매니저):
        """넨가드(채널링, 2026-10-22): 쓴 다음 자기 턴이 오면 "채널링 - 이름" 팝업이 뜨고 [유지]/[해제]를 고른다.
        [해제]를 누르면 넨가드가 바로 사라진다."""
        다른 = support.새게임([("", "격투가"), ("", "귀검사")])
        nm = 다른["파티"]["파티원"][0]
        for c in 다른["파티"]["파티원"]:
            support.성장(
                다른,
                c,
                8,
                전직={"격투가": "넨마스터", "귀검사": "웨펀마스터"}[c["직업"]],
                스킬습득=c is nm,
            )
        원래 = self.게임상태
        try:
            self.게임상태 = 다른
            gf.전투_시작(다른, ["고블린", "고블린", "고블린"], 레벨=2, 차수=1)
            support.반응_처리(다른)
            전투상태 = 다른["전투상태"]
            for e in 전투상태["참가자"]:
                if e["진영"] == "적":
                    e["현재HP"] = e["최대HP"] = 999
            n = next(p for p in 전투상태["참가자"] if p["원본"] is nm)

            def n의_차례():
                for _ in range(40):
                    if gf.현재_턴_참가자(다른) is n:
                        return
                    gf.턴_넘기기(다른)
                raise AssertionError("넨마스터 차례가 오지 않았다")

            n의_차례()
            n["현재MP"] = 50
            gf.아군_스킬사용(다른, "넨가드")
            gf.턴_넘기기(다른)
            n의_차례()
            assert any(b["이름"] == "넨가드" for b in n["버프"])
            전투 = 매니저.get_screen("전투")
            _팝업_닫기()
            전투.갱신(신규=True)
            매니저.current = "전투"
            for _ in range(20):
                yield 0.05
                if _팝업수() == 1:
                    break
            팝업 = Window.children[0]
            assert 팝업.title.startswith("채널링 - "), 팝업.title
            글들 = [b.text for b in _대상버튼들()]
            assert 글들 == ["유지", "해제"], 글들
            _찍기("battle_channeling_popup")
            _대상버튼들()[1].trigger_action(duration=0)
            yield 0.3
            assert _팝업수() == 0, _팝업수()
            assert not any(b["이름"] == "넨가드" for b in n["버프"])
            결과["단계"].append(
                "넨가드 채널링: 쓴 다음 자기 턴에 '채널링' 팝업(유지/해제), 해제를 누르면 넨가드가 사라짐"
            )
        finally:
            self.게임상태 = 원래
            매니저.current = "마을"

    def _단계_합격(self, 상태, 매니저):
        """합격(검귀 #332): 원귀(회천)를 쓰면 스킬 목록의 합격이 "합격 : 월령참"으로 보이고, 누르면 대상을
        고르지 않고 적 전체를 친다(원귀 상태가 사라진다)."""
        다른 = support.새게임([("", "귀검사")])
        c = 다른["파티"]["파티원"][0]
        support.성장(다른, c, 8, 전직="검귀", 스킬습득=True)
        원래 = self.게임상태
        원래선택 = rng.대상.choice
        try:
            self.게임상태 = 다른
            gf.전투_시작(다른, ["고블린", "고블린", "고블린"], 레벨=2, 차수=1)
            support.반응_처리(다른)
            전투상태 = 다른["전투상태"]
            for e in 전투상태["참가자"]:
                if e["진영"] == "적":
                    e["현재HP"] = e["최대HP"] = 999
            g = next(p for p in 전투상태["참가자"] if p["원본"] is c)
            for _ in range(40):
                if gf.현재_턴_참가자(다른) is g:
                    break
                gf.턴_넘기기(다른)
            assert gf.현재_턴_참가자(다른) is g
            g["현재MP"] = 50
            전투 = 매니저.get_screen("전투")
            전투.갱신(신규=True)
            매니저.current = "전투"
            yield 0.5
            _팝업_닫기()
            적 = next(p for p in 전투상태["참가자"] if p["진영"] == "적")
            rng.대상.choice = lambda 목록: "회천"
            전투._스킬_실행("원귀", 적)
            rng.대상.choice = 원래선택
            yield 0.5
            전투._스킬_버튼_클릭(g)
            yield 0.5
            합격 = next(b for b in _스킬줄_버튼들() if b.스킬이름 == "합격")
            assert _스킬줄_글(합격)[0] == "합격 : 월령참" and not 합격.disabled
            for w in Window.children[0].walk(
                restrict=True
            ):  # 합격 줄이 보이게 맨 아래로
                if isinstance(w, ScrollView):
                    w.scroll_y = 0
            yield 0.3
            _찍기("battle_skill_popup_hapgyeok")
            로그수 = len(전투상태["로그"])
            합격.trigger_action(duration=0)
            yield 0.5
            assert _팝업수() == 0, "월령참은 대상을 고르지 않는다"
            새로그 = [e for e in 전투상태["로그"][로그수:] if isinstance(e, dict)]
            [타격] = [e for e in 새로그 if e.get("스킬") == "합격 : 월령참"]
            assert len({t["대상"] for t in 타격["타격"]}) == 3
            assert not any(b["이름"] == "원귀" for b in g["버프"])
            결과["단계"].append(
                "합격: 원귀(회천) 뒤 스킬 목록에 '합격 : 월령참', 누르면 대상 없이 적 전체"
            )
        finally:
            rng.대상.choice = 원래선택
            self.게임상태 = 원래
            매니저.current = "마을"

    def _단계_공격연출(self, 상태, 매니저):
        """공격하면 대상 그림 칸 위에 공격 종류 그림이 떴다가 0.5초 뒤 사라진다(아군/적 모두)"""
        gf.전투_시작(상태, ["타우 아미", "타우 아미"], 레벨=6, 차수=2)
        support.반응_처리(상태)
        전투상태 = 상태["전투상태"]
        귀검사 = next(
            p
            for p in 전투상태["참가자"]
            if (p.get("원본") or {}).get("직업") == "귀검사"
        )
        # 첫 차례를 귀검사로 고정한다 - 적 차례면 화면이 저절로 진행해 그 연출이 점검 중에 뜬다
        전투상태["현재턴"] = 전투상태["참가자"].index(귀검사)
        flow.턴_시작_처리(전투상태, 귀검사)
        gf.새_공격연출_가져오기(상태)  # 전투 시작 반응(선제 공격)이 남긴 것
        전투 = 매니저.get_screen("전투")
        전투.갱신(신규=True)
        매니저.current = "전투"
        yield 0.8  # 앞 단계에서 남은 연출이 있었다면 사라질 때까지

        def 연출들():
            return [w for w in 전투.children if hasattr(w, "공격연출")]

        def 칸_위인가(그림, 참가자):
            """칸 가로 가운데, 대상 크기 그림의 세로 가운데(칸 바닥 아래로는 안 감 - 사용자 지정 10-14)."""
            칸 = 전투._그림칸[참가자["id"]]
            cx, cy = 그림.to_window(*그림.center)
            gy = 그림.to_window(*그림.pos)[1]
            x, y = 칸.to_window(*칸.pos)
            배율 = gf.공격연출_크기배율(상태, 참가자["id"])
            기대 = y + gf.공격연출_바닥(칸.height, 그림.height, 배율)
            return (
                x <= cx <= x + 칸.width
                and y <= cy <= y + 칸.height
                and abs(gy - 기대) < 1
                and abs(cx - (x + 칸.width / 2)) < 1
            )

        assert 연출들() == [], [w.공격연출 for w in 연출들()]
        적 = next(p for p in 전투상태["참가자"] if p["진영"] == "적" and p["생존"])
        전투._일반공격_실행(적)  # 명중이면 무기 종류, 빗나가면 실패
        # 반응 자동 사용이 꺼져 있으면 공격이 작업 스레드에서 돌고 끝난 뒤에야 화면이 연출을
        # 예약한다 - 정한 시간 한 번이 아니라 뜰 때까지(최대 3초 - 느린 CI 실행기) 기다린다
        for _ in range(60):
            yield 0.05
            if 연출들():
                break
        그림들 = 연출들()
        # 귀검사 녹슨 소검(공격타입 참격, 무속성): 명중이면 참격:무, 빗나가면 실패
        assert len(그림들) == 1 and 그림들[0].공격연출 in ("참격:무", "실패"), (
            그림들,
            [type(w).__name__ for w in Window.children],
            getattr(전투, "_엔진중", None),
            전투상태["로그"][-3:],
        )
        assert 칸_위인가(그림들[0], 적), "적 그림 칸 위에 뜬다"
        # 전투 기록 칸: "공격자의 일반공격!!" / "명중 값 vs AC 값, 결과!" / 결과 줄(gameflow.로그_문장들)
        기록 = 전투.로그라벨.text.strip().split("\n")[-3:]
        assert 기록[0].endswith("의 일반공격!!"), 기록
        assert re.fullmatch(
            r"명중 -?\d+ vs AC [\d.]+, (성공|실패|치명타|대실패)!", 기록[1]
        ), 기록
        assert 기록[2].endswith(("데미지를 받았다.", "공격을 피했다.", "쓰러졌다!")), (
            기록
        )
        _찍기("battle_attack_effect_enemy")
        yield 0.5
        assert 연출들() == [], "0.5초 뒤 사라진다"

        # 적이 아군을 공격한 연출(속성 공격 다음 빗나감)은 아군 그림 칸 위에 차례로 뜨고,
        # 같은 대상의 다음 연출이 뜨면 앞의 것을 바꾼다(겹치지 않는다)
        assert not 전투상태["종료"], 전투상태["종료"]
        # (짧은 시간 간격에 기대지 않도록 하나씩 직접 띄운다 - 차례 간격은 _공격연출_띄우기의 일)
        전투._공격연출_하나({"대상id": 귀검사["id"], "종류": "마법:화"})
        그림들 = 연출들()
        assert [w.공격연출 for w in 그림들] == ["마법:화"], 그림들
        assert 칸_위인가(그림들[0], 귀검사), "아군 그림 칸 위에 뜬다"
        yield 0.1
        _찍기("battle_attack_effect_ally")
        전투._공격연출_하나({"대상id": 귀검사["id"], "종류": "실패"})
        assert [w.공격연출 for w in 연출들()] == ["실패"], 연출들()
        # 크기(소형/중형/대형)마다 높이가 다르다 - 아군도 버프로 크기가 바뀔 수 있다(사용자 지정 10-14)
        원본 = 귀검사["원본"]
        높이 = {}
        for 크기 in ("소형", "중형", "대형"):
            귀검사["원본"] = dict(원본, 크기=크기)
            전투._공격연출_하나({"대상id": 귀검사["id"], "종류": "타격:무"})
            그림 = 연출들()[0]
            assert 칸_위인가(그림, 귀검사), 크기
            높이[크기] = 그림.y
        귀검사["원본"] = 원본
        assert 높이["소형"] <= 높이["중형"] < 높이["대형"], 높이
        yield 0.8
        assert 연출들() == [], "0.5초 뒤 사라진다"
        # [설정] 전투로그 "자세하게": 명중/AC/피해 계산 줄이 판정 줄 앞뒤에 붙는다
        gf.전투로그_방식_설정("자세하게")
        try:
            gf.전투_시작(상태, ["타우 아미", "타우 아미"], 레벨=6, 차수=2)
            support.반응_처리(상태)
            전투상태 = 상태["전투상태"]
            검사 = next(
                p
                for p in 전투상태["참가자"]
                if (p.get("원본") or {}).get("직업") == "귀검사"
            )
            전투상태["현재턴"] = 전투상태["참가자"].index(검사)
            flow.턴_시작_처리(전투상태, 검사)
            gf.새_공격연출_가져오기(상태)
            전투.로그라벨.text = ""
            전투.갱신(신규=True)
            yield 0.5
            적 = next(p for p in 전투상태["참가자"] if p["진영"] == "적" and p["생존"])
            전투._일반공격_실행(적)
            for _ in range(20):
                yield 0.05
                if "AC 계산: " in 전투.로그라벨.text:
                    break
            assert "AC 계산: " in 전투.로그라벨.text, 전투.로그라벨.text[-300:]
            assert "\n주사위(" in 전투.로그라벨.text, 전투.로그라벨.text[-300:]
            yield 0.6
            _찍기("battle_log_detailed")
        finally:
            gf.전투로그_방식_설정("간략하게")
        결과["단계"].append(
            "공격 연출(적/아군 그림 칸 위에 종류 그림, 0.5초 뒤 사라짐), 자세하게 계산 줄"
        )
        상태["전투상태"] = None
        매니저.current = "마을"

    def _단계_소지품(self, 상태, 매니저):
        """마을 [소지품/창고] 팝업(창고는 못 누름) -> 소지품 화면: 항아리 [사용] -> 결과 팝업,
        데이터 없는 항아리는 소모 안 함, 음식 [사용] -> 파티원 고르기 -> 회복, [상세보기], 던전 [소지품]"""
        앱 = App.get_running_app()
        앱.게임상태 = 상태
        상태["전투상태"] = None
        상태["던전상태"] = None

        def 버튼(위젯, 글):
            return next(
                w
                for w in 위젯.walk(restrict=True)
                if isinstance(w, Button) and w.text == 글
            )

        def 팝업():
            return Window.children[0]

        def 팝업_글():
            return " ".join(
                _글(w.text) for w in 팝업().walk(restrict=True) if isinstance(w, Label)
            )

        상태["소지품"]["골드"] = 상태["소지품"].get("골드", 0) + 200
        gf.상점_구매(상태, "소모품", "항아리", "만진의 항아리", 1)
        상태["소지품"]["소모품"]["카딘의 항아리"] = 1
        상태["소지품"]["소모품"]["칸나의 수제빵"] = 1

        매니저.get_screen("마을").갱신()
        매니저.current = "마을"
        yield 0.3
        버튼(매니저.current_screen, "소지품/창고").trigger_action(duration=0)
        yield 0.3
        assert 버튼(팝업(), "창고 (미구현)").disabled, "창고는 못 누른다"
        _찍기("inventory_choice")
        버튼(팝업(), "소지품").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "소지품", 매니저.current
        화면 = 매니저.current_screen
        버튼(화면, "소모품").trigger_action(duration=0)
        yield 0.3
        버튼(화면, "항아리").trigger_action(duration=0)
        yield 0.3
        _찍기("inventory_jars")

        def 행(이름):
            return next(
                w.parent
                for w in 화면._목록틀.walk(restrict=True)
                if isinstance(w, Label) and _글(w.text) == 이름
            )

        장비전 = sum(상태["소지품"]["장비"].values())
        버튼(행("만진의 항아리"), "사용").trigger_action(duration=0)
        yield 0.3
        assert "나왔습니다" in 팝업_글(), 팝업_글()
        _찍기("inventory_jar_result")
        assert sum(상태["소지품"]["장비"].values()) == 장비전 + 1
        assert "만진의 항아리" not in 상태["소지품"]["소모품"]
        _팝업_닫기()
        yield 0.3
        버튼(행("카딘의 항아리"), "사용").trigger_action(duration=0)
        yield 0.3
        assert "데이터 없음" in 팝업_글(), 팝업_글()
        assert 상태["소지품"]["소모품"]["카딘의 항아리"] == 1
        _팝업_닫기()
        yield 0.3
        버튼(행("카딘의 항아리"), "상세보기").trigger_action(duration=0)
        yield 0.3
        assert "크로니클 등급 장비" in 팝업_글(), 팝업_글()
        _팝업_닫기()
        yield 0.3

        버튼(화면, "음식").trigger_action(duration=0)
        yield 0.3
        버튼(행("칸나의 수제빵"), "상세보기").trigger_action(duration=0)
        yield 0.3
        assert "HP 최대치의 50%" in 팝업_글(), 팝업_글()
        _팝업_닫기()
        yield 0.3
        귀검사 = 상태["파티"]["파티원"][0]
        귀검사["현재HP"] = 1
        버튼(행("칸나의 수제빵"), "사용").trigger_action(duration=0)
        yield 0.3
        _찍기("inventory_target")
        next(
            w
            for w in 팝업().walk(restrict=True)
            if isinstance(w, Button) and w.text.startswith(귀검사["캐릭터명"] + " ")
        ).trigger_action(duration=0)
        yield 0.3
        assert 귀검사["현재HP"] > 1, 귀검사["현재HP"]
        assert "회복" in 화면.안내라벨.text, 화면.안내라벨.text
        assert "칸나의 수제빵" not in 상태["소지품"]["소모품"]

        # 나가기 -> 마을, 던전 [소지품] -> 나가기 -> 던전
        버튼(화면, "◀ 뒤로").trigger_action(duration=0)
        yield 0.3
        버튼(화면, "◀ 나가기").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "마을", 매니저.current
        gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
        매니저.get_screen("던전").갱신()
        매니저.current = "던전"
        yield 0.3
        버튼(매니저.current_screen, "소지품").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "소지품", 매니저.current
        버튼(매니저.current_screen, "◀ 나가기").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "던전", 매니저.current
        상태["던전상태"] = None
        결과["단계"].append(
            "소지품 - 마을 [소지품/창고](창고 못 누름), 항아리 [사용] 결과 팝업/데이터 없음은 그대로, "
            "[상세보기], 음식 [사용] -> 파티원 고르기 -> 회복, 던전 [소지품] -> 나가기 -> 던전"
        )

    def _단계_레테(self, 상태, 매니저):
        """능력치 역할 다시 고르기(#351): 전직 -> (스타일) -> 능력치 팝업(전직별 표가 골라져 있음) -> 확인,
        마을 소지품 [특수] 레테의 눈물 [사용] -> 파티원 -> 능력치판 터치 -> 확인, 레테의 강물 -> 확인 -> [예]
        -> 레벨 1·골드 환급, 던전 소지품에는 [사용] 없음, 옛 세이브의 한 번 고르기(마을 화면, [취소] 없음)"""
        import copy as _copy

        앱 = App.get_running_app()
        앱.게임상태 = 상태
        상태["전투상태"] = None
        상태["던전상태"] = None

        def 버튼(위젯, 글):
            return next(
                w
                for w in 위젯.walk(restrict=True)
                if isinstance(w, Button) and _글(w.text) == 글
            )

        def 팝업():
            return Window.children[0]

        # 1) 전직 - 따로 만든 레벨 5 귀검사(난수는 되돌린다)
        난수 = rng.상태()
        전직상태 = support.새게임([("", "귀검사")])
        귀검 = 전직상태["파티"]["파티원"][0]
        support.성장(전직상태, 귀검, 5)
        rng.상태_복원(난수)
        매니저.current = "파티관리"
        yield 0.3
        매니저.get_screen("파티관리")._전직선택_팝업(귀검)
        yield 0.3
        버튼(팝업(), "소울브링어").trigger_action(duration=0)
        yield 0.3
        if "스타일 선택" in 팝업().title:
            next(
                w
                for w in 팝업().walk(restrict=True)
                if isinstance(w, Button) and _글(w.text) != "취소"
            ).trigger_action(duration=0)
            yield 0.3
        assert 팝업().title == "소울브링어 - 능력치 다시 고르기", 팝업().title
        판 = 팝업().능력치판
        assert 판.스탯구성 == gf.전직_기본_스탯구성("소울브링어"), 판.스탯구성
        _찍기("lethe_advancement_stats")
        버튼(팝업(), "확인").trigger_action(duration=0)
        yield 0.3
        assert (귀검["전직"], 귀검["주스탯"]) == ("소울브링어", "지능"), 귀검["주스탯"]
        결과["단계"].append(
            "전직 -> 스타일 -> 능력치 다시 고르기(전직별 표가 골라져 있음) -> 확인 -> 주스탯 지능"
        )

        # 2) 마을 소지품 [특수] - 레테의 눈물/강물 (끝나면 캐릭터·소지품을 되돌린다)
        c = 상태["파티"]["파티원"][0]
        원래 = _copy.deepcopy(c)
        원래소지품 = _copy.deepcopy(상태["소지품"])
        상태["소지품"].setdefault("소모품", {}).update(
            {"레테의 눈물": 1, "레테의 강물": 1}
        )
        매니저.current = "마을"
        yield 0.3
        버튼(매니저.current_screen, "소지품/창고").trigger_action(duration=0)
        yield 0.3
        버튼(팝업(), "소지품").trigger_action(duration=0)
        yield 0.3
        화면 = 매니저.current_screen
        버튼(화면, "소모품").trigger_action(duration=0)
        yield 0.3
        버튼(화면, "특수").trigger_action(duration=0)
        yield 0.3
        _찍기("lethe_inventory")

        def 행(이름):
            return next(
                w.parent
                for w in 화면._목록틀.walk(restrict=True)
                if isinstance(w, Label) and _글(w.text) == 이름
            )

        def 소지품_나가기(화면):
            for _ in range(3):  # [뒤로]로 대분류까지, [나가기]로 연 화면
                if 매니저.current != "소지품":
                    return
                글들 = {
                    _글(w.text)
                    for w in 화면.walk(restrict=True)
                    if isinstance(w, Button)
                }
                뒤로 = "◀ 뒤로" if "◀ 뒤로" in 글들 else "◀ 나가기"
                버튼(화면, 뒤로).trigger_action(duration=0)
                yield 0.3

        def 파티원_고르기():
            next(
                w
                for w in 팝업().walk(restrict=True)
                if isinstance(w, Button) and w.text.startswith(c["캐릭터명"] + " ")
            ).trigger_action(duration=0)

        버튼(행("레테의 눈물"), "사용").trigger_action(duration=0)
        yield 0.3
        파티원_고르기()
        yield 0.3
        판 = 팝업().능력치판
        assert 판.스탯구성 == gf.능력치재선택_기본구성(c), 판.스탯구성
        새주 = next(n for n in 판.능력치_목록 if gf.스탯역할(판.스탯구성, n) == "일반")
        옛주 = 판.스탯구성["주스탯"]
        판.터치(옛주)  # 주 -> (보조는 다른 칸이 맡아 건너뜀) 일반
        판.터치(새주)  # 일반 -> 비어 있는 주
        yield 0.2
        _찍기("lethe_tears_board")
        if any(판.스탯구성.get(r) is None for r in ("주스탯", "보조스탯", "약점스탯")):
            판.터치(옛주)
            yield 0.2
        확인 = 버튼(팝업(), "확인")
        assert not 확인.disabled, 판.스탯구성
        구성 = dict(판.스탯구성)
        확인.trigger_action(duration=0)
        yield 0.3
        assert {r: c[r] for r in 구성} == 구성, (구성, c["주스탯"])
        assert "다시 골랐습니다" in 화면.안내라벨.text, 화면.안내라벨.text
        assert "레테의 눈물" not in 상태["소지품"]["소모품"]

        레벨전, 골드전 = c["레벨"], 상태["소지품"]["골드"]
        환급 = gf.레테_환급골드(c)
        버튼(행("레테의 강물"), "사용").trigger_action(duration=0)
        yield 0.3
        파티원_고르기()
        yield 0.3
        버튼(팝업(), "확인").trigger_action(duration=0)
        yield 0.3
        assert "레벨 1로 되돌립니다" in " ".join(
            _글(w.text) for w in 팝업().walk(restrict=True) if isinstance(w, Label)
        )
        _찍기("lethe_river_confirm")
        버튼(팝업(), "예").trigger_action(duration=0)
        yield 0.3
        assert 레벨전 > 1 and c["레벨"] == 1 and c["전직"] is None, c["레벨"]
        assert 상태["소지품"]["골드"] == 골드전 + 환급
        assert "레벨 1로 돌아갔습니다" in 화면.안내라벨.text, 화면.안내라벨.text

        # 던전 소지품에서는 [사용]이 없다
        상태["소지품"]["소모품"]["레테의 눈물"] = 1
        yield from 소지품_나가기(화면)
        assert 매니저.current == "마을", 매니저.current
        gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
        매니저.get_screen("던전").갱신()
        매니저.current = "던전"
        yield 0.3
        버튼(매니저.current_screen, "소지품").trigger_action(duration=0)
        yield 0.3
        화면 = 매니저.current_screen
        버튼(화면, "소모품").trigger_action(duration=0)
        yield 0.3
        버튼(화면, "특수").trigger_action(duration=0)
        yield 0.3
        assert not any(
            isinstance(w, Button) and _글(w.text) == "사용"
            for w in 행("레테의 눈물").walk(restrict=True)
        ), "던전에서는 레테를 못 쓴다"
        yield from 소지품_나가기(화면)
        assert 매니저.current == "던전", 매니저.current
        상태["던전상태"] = None

        # 3) 옛 세이브의 한 번 고르기 - 마을에 들어가면 묻는다([취소] 없음)
        c.clear()
        c.update(원래)
        상태["소지품"] = 원래소지품
        c["능력치재선택"] = True
        매니저.get_screen("마을").갱신()
        매니저.current = "마을"
        yield 0.5
        assert 팝업().title.endswith("능력치 다시 고르기"), 팝업().title
        assert not any(
            isinstance(w, Button) and _글(w.text) == "취소"
            for w in 팝업().walk(restrict=True)
        )
        _찍기("lethe_old_save_repick")
        버튼(팝업(), "확인").trigger_action(duration=0)
        yield 0.3
        assert "능력치재선택" not in c and gf.능력치재선택_대기(상태) == []
        assert {k: c[k] for k in 원래 if k in ("근력", "지능", "주스탯")} == {
            k: 원래[k] for k in ("근력", "지능", "주스탯")
        }  # 지금 역할 그대로 확인하면 바뀌지 않는다
        결과["단계"].append(
            "레테: 마을 소지품 [특수] 눈물 -> 파티원 -> 능력치판 -> 확인, 강물 -> 확인 -> [예] -> 레벨 1·환급, "
            "던전 소지품에는 [사용] 없음, 옛 세이브는 마을에서 한 번 묻기([취소] 없음)"
        )

    def _단계_도감_업적(self, 상태, 매니저):
        """[메뉴] -> [도감]: 대분류 등록 수, 몬스터 종족 탭(미등록은 어둡고 [상세보기] 못 누름, 몬스터 상세),
        장비 고르는 상자 4개(상위/중위/하위분류, 레어도), 나가기 -> 연 화면. [메뉴] -> [업적]: 분류 4개, 달성 전 [보상받기]는
        못 누름, [보상받기] -> 골드 +10/받음, [보상 전부 받기]"""
        앱 = App.get_running_app()
        앱.게임상태 = 상태
        상태["전투상태"] = None
        상태["던전상태"] = None

        def 버튼(위젯, 글):
            return next(
                w
                for w in 위젯.walk(restrict=True)
                if isinstance(w, Button) and _글(w.text) == 글
            )

        def 팝업():
            return Window.children[0]

        def 메뉴_열기():
            버튼(매니저.get_screen("마을"), "메뉴").trigger_action(duration=0)

        도감 = 상태["진행도"]["도감"]
        for 이름 in ("고블린", "고블린 투척병"):
            if 이름 not in 도감["몬스터"]:
                도감["몬스터"].append(이름)
        매니저.get_screen("마을").갱신()
        매니저.current = "마을"
        yield 0.3
        메뉴_열기()
        yield 0.3
        버튼(팝업(), "도감").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "도감", 매니저.current
        화면 = 매니저.current_screen
        assert 화면.골드라벨.text.startswith("등록 "), 화면.골드라벨.text
        몬스터버튼 = next(
            w
            for w in 화면.내용틀.walk(restrict=True)
            if isinstance(w, Button) and w.text.startswith("몬스터 (")
        )
        등록, 전체 = gf.도감_등록현황(상태, "몬스터")
        assert 몬스터버튼.text == f"몬스터 ({등록}/{전체})", 몬스터버튼.text
        몬스터버튼.trigger_action(duration=0)
        yield 0.3

        def 행(이름):
            return next(
                w.parent
                for w in 화면._목록틀.walk(restrict=True)
                if isinstance(w, Label) and _글(w.text) == 이름
            )

        assert "미등록" not in _글(
            " ".join(w.text for w in 행("고블린").children if isinstance(w, Label))
        )
        assert not 버튼(행("고블린"), "상세보기").disabled
        assert 버튼(행("프라그"), "상세보기").disabled, "미등록은 상세보기 못 누름"
        _찍기("collection_monster")
        버튼(행("고블린"), "상세보기").trigger_action(duration=0)
        yield 0.3
        assert 팝업().title == "고블린"
        _찍기("collection_monster_detail")
        _팝업_닫기()
        yield 0.3

        버튼(화면, "◀ 뒤로").trigger_action(duration=0)
        yield 0.3
        next(
            w
            for w in 화면.내용틀.walk(restrict=True)
            if isinstance(w, Button) and w.text.startswith("장비 (")
        ).trigger_action(duration=0)
        yield 0.3
        # 장비 도감은 고르는 상자 4개 - 모두 [전체]로 시작, 상위가 전체면 중위/하위는 못 누른다
        상자 = 화면.장비필터상자
        assert {k: w.text for k, w in 상자.items()} == dict(gf.도감_장비필터_기본)
        assert 상자["중위"].disabled and 상자["하위"].disabled
        assert not 상자["상위"].disabled and not 상자["레어도"].disabled
        assert 상자["레어도"].values[-4:] == ["유니크", "크로니클", "레전더리", "에픽"]

        def 이름들():
            return [
                _글(w.text)
                for w in 화면._목록틀.walk(restrict=True)
                if isinstance(w, Label) and w.text and w.size_hint_x == 0.56
            ]

        assert len(이름들()) == len(gf.도감_장비필터_목록(상태, gf.도감_장비필터_기본))
        상자["상위"].is_open = True  # 누르면 목록이 펼쳐진다
        yield 0.3
        _찍기("collection_equipment_dropdown")
        상자["상위"].is_open = False
        상자["상위"].text = "무기"
        yield 0.3
        상자 = 화면.장비필터상자
        assert not 상자["중위"].disabled and "귀검사" in 상자["중위"].values
        상자["중위"].text = "귀검사"
        yield 0.3
        상자 = 화면.장비필터상자
        assert 상자["하위"].values == ["전체", "소검", "도", "둔기", "대검", "광검"]
        상자["레어도"].text = "언커먼"
        yield 0.3
        무기 = {a["이름"]: a for a, _ in gf.도감_목록(상태, "장비", "무기")}
        보인것 = 이름들()
        assert 보인것 and all(
            무기[n]["레어도"] == "언커먼" and 무기[n]["분류"] == "귀검사 무기"
            for n in 보인것
        ), 보인것
        for w in 화면.장비필터상자.values():
            x, _ = w.to_window(w.right, w.y)
            assert w.width > 0 and x <= Window.width + 1, (w.text, x, Window.width)
        _찍기("collection_equipment")
        # 상세보기 글: 무기 "장비효과"는 "최대MP +10", 봉인 무기 "타입"은 "소검, 마법봉인"
        산들바람 = 상태["상점카탈로그"]["장비"]["무기"]["산들바람"]
        assert 화면._값_문자열(산들바람["장비효과"]) == "최대MP +10"
        봉인소검 = 상태["상점카탈로그"]["장비"]["무기"]["마법으로 봉인된 소검"]
        assert 화면._값_문자열(봉인소검["타입"]) == "소검, 마법봉인"
        상자["상위"].text = "전체"  # 위를 바꾸면 아래는 전체로, 레어도는 그대로
        yield 0.3
        상자 = 화면.장비필터상자
        assert (상자["중위"].text, 상자["하위"].text) == ("전체", "전체")
        assert 상자["중위"].disabled and 상자["레어도"].text == "언커먼"
        버튼(화면, "◀ 뒤로").trigger_action(duration=0)
        yield 0.3
        버튼(화면, "◀ 나가기").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "마을", "도감의 나가기는 메뉴를 연 화면으로"

        상태["진행도"]["업적기록"]["일반전투승리"] = max(
            5, 상태["진행도"]["업적기록"]["일반전투승리"]
        )
        상태["진행도"]["받은업적"] = []
        메뉴_열기()
        yield 0.3
        버튼(팝업(), "업적").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "업적", 매니저.current
        화면 = 매니저.current_screen
        분류 = [w.text for w in 화면.walk(restrict=True) if isinstance(w, ToggleButton)]
        assert 분류 == ["레벨업적", "도감업적", "전투업적", "특수업적"], 분류
        받기버튼 = [
            w
            for w in 화면._목록틀.walk(restrict=True)
            if isinstance(w, Button) and hasattr(w, "업적ID")
        ]
        assert len(받기버튼) == 20
        레벨 = 상태["진행도"]["플레이어레벨"]
        for w in 받기버튼:
            달성 = int(w.업적ID.split("_")[1]) <= 레벨
            assert w.disabled == (not 달성), (w.업적ID, w.disabled)
        assert not 화면.전부받기버튼.disabled
        _찍기("achievements")
        골드 = 상태["소지품"]["골드"]
        next(w for w in 받기버튼 if w.업적ID == "레벨_1").trigger_action(duration=0)
        yield 0.3
        assert 상태["소지품"]["골드"] == 골드 + 10
        첫줄 = next(
            w
            for w in 화면._목록틀.walk(restrict=True)
            if getattr(w, "업적ID", None) == "레벨_1"
        )
        assert 첫줄.text == "받음" and 첫줄.disabled
        # 특수업적: 세리아 구출 -> [보상받기] = 랜덤 레어 무기(마법으로 봉인된 무기 하나)
        상태["진행도"]["클리어한오브젝트"].add(("dungeon_01A_D01_Lorien", (15, 3)))
        버튼(화면, "특수업적").trigger_action(duration=0)
        yield 0.3
        세리아 = next(
            w
            for w in 화면._목록틀.walk(restrict=True)
            if getattr(w, "업적ID", None) == "세리아_구출"
        )
        assert not 세리아.disabled
        장비전 = dict(상태["소지품"]["장비"])
        세리아.trigger_action(duration=0)
        yield 0.3
        새장비 = [
            n
            for n in 상태["소지품"]["장비"]
            if 상태["소지품"]["장비"][n] > 장비전.get(n, 0)
        ]
        assert len(새장비) == 1 and 새장비[0].startswith("마법으로 봉인된 "), 새장비
        assert 새장비[0] in 화면.안내라벨.text, 화면.안내라벨.text
        _찍기("achievements_special")
        버튼(화면, "전투업적").trigger_action(duration=0)
        yield 0.3
        _찍기("achievements_battle")
        남은 = gf.업적_받을_보상_수(상태)
        화면.전부받기버튼.trigger_action(duration=0)
        yield 0.3
        assert 상태["소지품"]["골드"] == 골드 + 10 + 남은 * 10
        assert 화면.전부받기버튼.disabled and gf.업적_받을_보상_수(상태) == 0
        버튼(화면, "◀ 나가기").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "마을"
        결과["단계"].append(
            "도감/업적 - [메뉴] -> [도감] 등록 수, 몬스터(미등록 어둡게/상세보기 못 누름, 상세 팝업), "
            "장비 고르는 상자 4개(전체 시작, 상위 전체면 중위·하위 못 누름, 무기 -> 귀검사 -> 언커먼), 나가기 -> 마을. [메뉴] -> [업적] 분류 4개, 달성 전 못 누름, 보상받기/전부 받기, "
            "특수업적 보상받기(봉인 레어 무기와 안내 글)"
        )

    def _단계_메뉴(self, 상태, 매니저):
        """마을/던전 [메뉴] 팝업 - 저장하기/불러오기/설정/메인메뉴로(확인 창), 던전 안 저장 -> 같은 위치로"""
        앱 = App.get_running_app()
        앱.게임상태 = 상태
        상태["전투상태"] = None
        상태["던전상태"] = None

        def 버튼(위젯, 글):
            return next(
                w
                for w in 위젯.walk(restrict=True)
                if isinstance(w, Button) and w.text == 글
            )

        def 팝업():
            return Window.children[0]

        def 메뉴_열기(화면이름):
            버튼(매니저.get_screen(화면이름), "메뉴").trigger_action(duration=0)

        매니저.get_screen("마을").갱신()
        매니저.current = "마을"
        yield 0.3
        메뉴_열기("마을")
        yield 0.3
        글들 = [w.text for w in 팝업().walk(restrict=True) if isinstance(w, Button)]
        assert 글들 == [
            "저장하기",
            "불러오기",
            "도감",
            "업적",
            "설정",
            "타이틀로 돌아가기",
            "닫기",
        ], 글들
        _찍기("menu_popup")
        버튼(팝업(), "저장하기").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "저장목록", 매니저.current
        버튼(매니저.current_screen, "뒤로").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "마을", "저장 목록의 [뒤로]는 메뉴를 연 마을로"

        # 던전에서: 설정 갔다 돌아오기, 저장 -> 불러오기(확인 창) -> 같은 던전 같은 위치
        gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
        매니저.get_screen("던전").갱신()
        매니저.current = "던전"
        yield 0.3
        메뉴_열기("던전")
        yield 0.3
        버튼(팝업(), "설정").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "설정"
        버튼(매니저.current_screen, "뒤로").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "던전", "설정의 [뒤로]는 메뉴를 연 던전으로"
        위치 = tuple(상태["던전상태"]["위치"])
        메뉴_열기("던전")
        yield 0.3
        버튼(팝업(), "저장하기").trigger_action(duration=0)
        yield 0.3
        매니저.current_screen._선택(3)
        yield 0.3
        요약 = next(s for s in gf.전체_세이브_요약() if s["슬롯번호"] == 3)
        assert 요약.get("던전파일명") == "dungeon_01A_D01_Lorien", 요약
        버튼(매니저.current_screen, "뒤로").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "던전"
        메뉴_열기("던전")
        yield 0.3
        버튼(팝업(), "불러오기").trigger_action(duration=0)
        yield 0.3
        _찍기("menu_confirm")
        버튼(팝업(), "예").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "불러오기목록", 매니저.current
        매니저.current_screen._선택(3)
        yield 0.3
        assert 매니저.current == "던전", "던전에서 저장한 세이브는 던전으로"
        assert tuple(앱.게임상태["던전상태"]["위치"]) == 위치
        # 타이틀로 돌아가기: [아니요]면 그대로, [예]면 메인메뉴
        메뉴_열기("던전")
        yield 0.3
        버튼(팝업(), "타이틀로 돌아가기").trigger_action(duration=0)
        yield 0.3
        버튼(팝업(), "아니요").trigger_action(duration=0)
        yield 0.3
        _팝업_닫기()
        yield 0.3
        assert 매니저.current == "던전"
        메뉴_열기("던전")
        yield 0.3
        버튼(팝업(), "타이틀로 돌아가기").trigger_action(duration=0)
        yield 0.3
        버튼(팝업(), "예").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "메인메뉴", 매니저.current
        결과["단계"].append(
            "메뉴 팝업(마을/던전 같음) - 저장/설정 갔다 돌아오기, 던전 안 저장 -> 불러오기(확인 창) "
            "-> 같은 위치, 타이틀로(아니요/예)"
        )


if __name__ == "__main__":
    # Windows에서 리디렉션된 출력은 cp1252라 한글 print가 죽는다(#200) - 콘솔 인코딩과 상관없이 UTF-8로.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    스모크앱().run()
    for 단계 in 결과["단계"]:
        print("OK  ", 단계)
    if 결과["오류"]:
        print(결과["오류"])
    print(
        json.dumps(
            {"스크린샷": 스크린샷폴더, "성공": 결과["오류"] is None}, ensure_ascii=False
        )
    )
    sys.exit(1 if 결과["오류"] else 0)
