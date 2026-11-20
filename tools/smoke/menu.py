"""화면 스모크 단계 - 세이브·자동 저장·설정·도감·업적·메뉴 팝업·보스 귀환."""

# common을 먼저 불러 kivy 창 설정을 끝낸다.
from tools.smoke.common import (
    _글,
    _마을_메뉴_열기,
    _위젯_버튼,
    _찍기,
    _팝업_닫기,
    결과,
)
import main
import copy
import json
import os
import shutil
import tempfile
import types
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
import gameflow as gf
from game.screens import screens_common
from game.system import save_system


class 메뉴단계:
    def _단계_세이브(self, 상태, 매니저):
        """세이브 슬롯(새버전/손상/복구본)과 앱 시작 때 세이브 폴더 이전"""
        # 세이브 슬롯: 슬롯 하나가 망가져도 메인 메뉴/슬롯 목록이 열린다(구조 점검 W-1).
        # 실제 game/saves/ 대신 임시 폴더를 쓴다.
        세이브폴더 = tempfile.mkdtemp(prefix="ui_smoke_saves_")
        원래폴더 = save_system._세이브_폴더
        원래재정의 = save_system._폴더_재정의  # 스모크 전체가 쓰는 임시 폴더
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
            # 위에서 아래(맨 위 자동 저장 칸을 빼면 슬롯 1, 2, 3)
            자동칸, *줄들 = list(reversed(불러오기.목록틀.children))

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
            assert 줄_글(자동칸) == "자동 저장 - (비어 있음)", 줄_글(자동칸)
            assert 줄_버튼(자동칸).disabled, "빈 자동 저장 칸은 불러올 수 없다"

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
                save_system._폴더_재정의 = 원래재정의
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

    def _단계_자동저장(self, 상태, 매니저):
        """자동 저장 칸 - 새 게임 시작/패배 귀환/마을 이동 화면에서 0번 칸에 덮어쓰고,
        저장하기 목록에서는 고를 수 없고 불러오기 목록에서는 불러올 수 있다"""
        세이브폴더 = tempfile.mkdtemp(prefix="ui_smoke_autosave_")
        원래폴더 = save_system._세이브_폴더
        save_system._세이브_폴더 = lambda: 세이브폴더
        자동 = gf.자동저장슬롯

        def 저장본():
            with open(
                os.path.join(세이브폴더, f"slot_{자동}.json"), encoding="utf-8"
            ) as f:
                return json.load(f)

        try:
            # 새 게임 시작 -> 마을, 자동 저장 칸이 채워진다
            파티생성 = 매니저.get_screen("파티생성")
            for 칸 in 파티생성.슬롯목록:
                칸["이름입력"].text = ""
            매니저.current = "파티생성"
            yield 0.3
            파티생성._시작()
            assert 매니저.current == "마을", 매니저.current
            assert gf.세이브_존재(자동), "새 게임 시작은 자동 저장한다"
            새파티 = [c["캐릭터명"] for c in self.게임상태["파티"]["파티원"]]
            assert [
                c["캐릭터명"] for c in 저장본()["플레이어"]["파티"]["파티원"]
            ] == 새파티
            yield 0.3

            # 전투에서 져서 마을로 -> 휴식한 상태로 덮어쓴다(공용 상태는 건드리지 않게 복사본)
            self.게임상태 = 사본 = copy.deepcopy(상태)
            for c in 사본["파티"]["파티원"]:
                c["현재HP"] = 0
            매니저.get_screen("전투")._전투종료_이동("적승리")
            assert 매니저.current == "마을", 매니저.current
            저장 = 저장본()
            assert all(c["현재HP"] > 0 for c in 저장["플레이어"]["파티"]["파티원"])
            assert [c["캐릭터명"] for c in 저장["플레이어"]["파티"]["파티원"]] == [
                c["캐릭터명"] for c in 상태["파티"]["파티원"]
            ]
            yield 0.3

            # 다른 마을로 이동 -> 그 마을로 덮어쓴다
            사본["진행도"]["클리어한던전"].update(gf.던전_레지스트리)
            목표 = gf.이동가능마을목록(사본)[0]["마을명"]
            매니저.get_screen("마을이동목록")._선택(목표)
            assert 매니저.current == "마을"
            assert 저장본()["진행도"]["현재마을"] == 목표
            yield 0.3

            # 저장하기 목록: 맨 위 "자동 저장" 칸은 고를 수 없다
            매니저.current = "저장목록"
            yield 0.4
            _찍기("save_slots_autosave")
            저장목록 = 매니저.get_screen("저장목록")
            맨위 = list(reversed(저장목록.목록틀.children))[0]
            글 = next(w.text for w in 맨위.children if type(w) is Label)
            assert 글.startswith("자동 저장 - ") and 목표 in 글, 글
            assert next(w for w in 맨위.children if isinstance(w, Button)).disabled
            이전 = (저장본(), 저장목록.안내라벨.text)
            저장목록._선택(자동)  # 막혀 있어도 호출되면 아무것도 하지 않는다
            assert (저장본(), 저장목록.안내라벨.text) == 이전

            # 불러오기 목록: 자동 저장 칸을 불러와 마을로(불러오기는 자동 저장하지 않는다)
            매니저.current = "불러오기목록"
            yield 0.3
            불러오기 = 매니저.get_screen("불러오기목록")
            맨위 = list(reversed(불러오기.목록틀.children))[0]
            assert not next(w for w in 맨위.children if isinstance(w, Button)).disabled
            불러오기._선택(자동)
            assert 매니저.current == "마을"
            assert self.게임상태["진행도"]["현재마을"] == 목표
            결과["단계"].append(
                "자동 저장 칸(새 게임/패배 귀환/마을 이동에서 덮어씀, 저장하기 목록에서 막힘, 불러오기 됨)"
            )
        finally:
            save_system._세이브_폴더 = 원래폴더
            shutil.rmtree(세이브폴더, ignore_errors=True)
            self.게임상태 = 상태
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
                (
                    "자동전투방식",
                    "기본전투",
                    gf.자동전투_방식,
                ),  # 자동전투 줄은 셋(#761)
                ("자동전투방식", "자동전투", gf.자동전투_방식),
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
                "설정 화면 체크박스(반응 자동/연계 자동/자동전투 셋/자동전투 포션/전투로그) 하나씩 골라 저장"
            )
        finally:
            screens_common._설정_경로 = 원래경로
            gf.반응_자동_설정(원래반응)
            gf.연계_자동_설정(원래연계)
            gf.자동전투_방식_설정("기본전투")
            gf.자동전투_포션_설정(False)
            gf.전투로그_방식_설정("간략하게")
            shutil.rmtree(폴더, ignore_errors=True)
            매니저.current = "마을"

    def _단계_도감_업적(self, 상태, 매니저):
        """[메뉴] -> [도감]: 대분류 등록 수, 몬스터 종족 탭(미등록은 어둡고 [상세보기] 못 누름, 몬스터 상세),
        장비 고르는 상자 4개(상위/중위/하위분류, 레어도), 나가기 -> 연 화면. [메뉴] -> [업적]: 분류 4개, 달성 전 [보상받기]는
        못 누름, [보상받기] -> 골드 +10/받음, [보상 전부 받기]"""
        앱 = App.get_running_app()
        앱.게임상태 = 상태
        상태["전투상태"] = None
        상태["던전상태"] = None
        yield from self._단계_도감_몬스터(상태, 매니저)
        yield from self._단계_도감_장비(상태, 매니저)
        yield from self._단계_업적(상태, 매니저)
        결과["단계"].append(
            "도감/업적 - [메뉴] -> [도감] 등록 수, 몬스터(미등록 어둡게/상세보기 못 누름, 상세 팝업), "
            "장비 고르는 상자 4개(전체 시작, 상위 전체면 중위·하위 못 누름, 무기 -> 귀검사 -> 언커먼), 나가기 -> 마을. [메뉴] -> [업적] 분류 4개, 달성 전 못 누름, 보상받기/전부 받기, "
            "특수업적 보상받기(봉인 레어 무기와 안내 글)"
        )

    def _단계_도감_몬스터(self, 상태, 매니저):
        """[메뉴] -> [도감] 등록 수, 몬스터 종족 탭(미등록은 [상세보기] 못 누름, 몬스터 상세)"""
        도감 = 상태["진행도"]["도감"]
        for 이름 in ("고블린", "고블린 투척병"):
            if 이름 not in 도감["몬스터"]:
                도감["몬스터"].append(이름)
        매니저.get_screen("마을").갱신()
        매니저.current = "마을"
        yield 0.3
        _마을_메뉴_열기(매니저)
        yield 0.3
        _위젯_버튼(Window.children[0], "도감").trigger_action(duration=0)
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
        assert not _위젯_버튼(행("고블린"), "상세보기").disabled
        assert _위젯_버튼(행("프라그"), "상세보기").disabled, (
            "미등록은 상세보기 못 누름"
        )
        _찍기("collection_monster")
        _위젯_버튼(행("고블린"), "상세보기").trigger_action(duration=0)
        yield 0.3
        assert Window.children[0].title == "고블린"
        _찍기("collection_monster_detail")
        _팝업_닫기()
        yield 0.3

    def _단계_도감_장비(self, 상태, 매니저):
        """장비 도감 고르는 상자 4개(상위/중위/하위분류, 레어도), 상세 글, 나가기 -> 연 화면"""
        화면 = 매니저.current_screen
        _위젯_버튼(화면, "◀ 뒤로").trigger_action(duration=0)
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
        # 오라 원소의 정식 이름 "속도보너스"는 화면에 지금 문구 "속도"로
        마젠타 = 상태["상점카탈로그"]["장비"]["무기"]["마젠타"]
        assert 화면._값_문자열(마젠타["오라"]) == "속도 +3"
        상자["상위"].text = "전체"  # 위를 바꾸면 아래는 전체로, 레어도는 그대로
        yield 0.3
        상자 = 화면.장비필터상자
        assert (상자["중위"].text, 상자["하위"].text) == ("전체", "전체")
        assert 상자["중위"].disabled and 상자["레어도"].text == "언커먼"
        _위젯_버튼(화면, "◀ 뒤로").trigger_action(duration=0)
        yield 0.3
        _위젯_버튼(화면, "◀ 나가기").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "마을", "도감의 나가기는 메뉴를 연 화면으로"

    def _단계_업적(self, 상태, 매니저):
        """[메뉴] -> [업적] 분류 4개, 달성 전 못 누름, 보상받기/특수업적/전부 받기"""
        상태["진행도"]["업적기록"]["일반전투승리"] = max(
            5, 상태["진행도"]["업적기록"]["일반전투승리"]
        )
        상태["진행도"]["받은업적"] = []
        _마을_메뉴_열기(매니저)
        yield 0.3
        _위젯_버튼(Window.children[0], "업적").trigger_action(duration=0)
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
        _위젯_버튼(화면, "특수업적").trigger_action(duration=0)
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
        _위젯_버튼(화면, "전투업적").trigger_action(duration=0)
        yield 0.3
        _찍기("achievements_battle")
        남은 = gf.업적_받을_보상_수(상태)
        화면.전부받기버튼.trigger_action(duration=0)
        yield 0.3
        assert 상태["소지품"]["골드"] == 골드 + 10 + 남은 * 10
        assert 화면.전부받기버튼.disabled and gf.업적_받을_보상_수(상태) == 0
        _위젯_버튼(화면, "◀ 나가기").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "마을"

    def _단계_보스_귀환(self, 상태, 매니저):
        """보스를 이긴 맵의 [귀환] - 이기기 전에는 꺼진 [상호작용], 이긴 뒤에는 [귀환] ->
        "귀환하시겠습니까?" [아니요]면 던전 그대로, [예]면 마을. 오브젝트 앞에서는 [상호작용]."""
        from game.system import town_system

        앱 = App.get_running_app()
        앱.게임상태 = 상태
        상태["전투상태"] = None
        _팝업_닫기()
        던전 = 매니저.get_screen("던전")
        gf.던전_진입(상태, "dungeon_01A_D02_Hollow_Lorien")
        상태["던전상태"]["위치"] = (12, 3)
        매니저.current = "던전"
        던전.갱신()
        yield 0.3
        버튼 = 던전.상호작용버튼
        assert 버튼.text == "상호작용" and 버튼.disabled, (버튼.text, 버튼.disabled)
        town_system.오브젝트_클리어_기록(
            상태["진행도"], "dungeon_01A_D02_Hollow_Lorien", (15, 3)
        )
        던전.갱신()
        yield 0.3
        assert 버튼.text == "귀환" and not 버튼.disabled, (버튼.text, 버튼.disabled)
        _찍기("dungeon_return_button")
        버튼.trigger_action(duration=0)
        yield 0.3
        팝업 = Window.children[0]
        글들 = [w.text for w in 팝업.walk(restrict=True) if isinstance(w, Label)]
        assert "귀환하시겠습니까?" in 글들, 글들
        _찍기("dungeon_return_confirm")
        next(
            w
            for w in 팝업.walk(restrict=True)
            if isinstance(w, Button) and w.text == "아니요"
        ).trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "던전" and 상태["던전상태"] is not None
        # 보스(15,3) 왼쪽 칸에서 보스 쪽으로 - 오브젝트 앞에서는 [상호작용]
        상태["던전상태"]["위치"] = (14, 3)
        던전.갱신()
        던전._이동("오른쪽")
        yield 0.3
        assert 버튼.text == "상호작용" and not 버튼.disabled, 버튼.text
        던전.갱신()
        yield 0.3
        버튼.trigger_action(duration=0)
        yield 0.3
        팝업 = Window.children[0]
        next(
            w
            for w in 팝업.walk(restrict=True)
            if isinstance(w, Button) and w.text == "예"
        ).trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "마을", 매니저.current
        assert 상태["던전상태"] is None
        상태["진행도"]["클리어한오브젝트"].discard(
            ("dungeon_01A_D02_Hollow_Lorien", (15, 3))
        )
        결과["단계"].append(
            "보스를 이긴 맵의 [귀환] - 이기기 전 꺼짐, 이긴 뒤 [귀환] -> 확인 창(아니요/예 -> 마을), 오브젝트 앞은 [상호작용]"
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
        문구 = [w.text for w in 팝업().walk(restrict=True) if isinstance(w, Label)]
        assert (
            "저장되지 않은 데이터는 삭제됩니다.\n타이틀로 돌아가시겠습니까?" in 문구
        ), 문구
        _찍기("menu_title_confirm")
        버튼(팝업(), "예").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "메인메뉴", 매니저.current
        # 메인 화면 제목은 "던파Zero" - 화면 폭 안에 들어간다
        제목 = next(
            w
            for w in 매니저.current_screen.walk(restrict=True)
            if isinstance(w, Label) and w.text == "던파Zero"
        )
        assert 제목.texture_size[0] <= 매니저.current_screen.width, 제목.texture_size
        _찍기("main_menu_title")
        # 마을 화면 아래 [타이틀로 돌아가기]도 확인 창 - [아니요]면 마을 그대로, [예]면 메인메뉴
        매니저.get_screen("마을").갱신()
        매니저.current = "마을"
        yield 0.3
        버튼(매니저.get_screen("마을"), "타이틀로 돌아가기").trigger_action(duration=0)
        yield 0.3
        버튼(팝업(), "아니요").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "마을", "확인 창 없이 타이틀로 갔다"
        버튼(매니저.get_screen("마을"), "타이틀로 돌아가기").trigger_action(duration=0)
        yield 0.3
        버튼(팝업(), "예").trigger_action(duration=0)
        yield 0.3
        assert 매니저.current == "메인메뉴", 매니저.current
        결과["단계"].append(
            "메뉴 팝업(마을/던전 같음) - 저장/설정 갔다 돌아오기, 던전 안 저장 -> 불러오기(확인 창) "
            "-> 같은 위치, 타이틀로(아니요/예, 주인 지정 문구), 마을 아래 타이틀 버튼도 확인 창, 제목 던파Zero"
        )
