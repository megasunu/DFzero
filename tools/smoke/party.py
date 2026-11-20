"""화면 스모크 단계 - 파티 구성·성장 팝업(능력치·전직·마스터리·스킬·퍽)·장비 교체·파티원 포션·뒤로 키."""

# common을 먼저 불러 kivy 창 설정을 끝낸다.
from tools.smoke.common import (
    _글,
    _뒤로키,
    _찍기,
    _팝업_닫기,
    _팝업_버튼,
    _팝업수,
    결과,
)
import main
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.uix.togglebutton import ToggleButton
import gameflow as gf
from game.screens import screens_member
from game.system import rng
from tests import support


class 파티단계:
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

    def _단계_파티관리_팝업(self, 상태, 매니저):
        """파티관리 - 능력치 배분, 전직, 마스터리, 스킬강화, 퍽, 스킬습득 팝업(주제별 단계로 나눔)"""
        yield from self._단계_능력치배분_팝업(상태, 매니저)
        yield from self._단계_전직선택_팝업(매니저)
        yield from self._단계_마스터리선택_팝업(매니저)
        yield from self._단계_스킬강화_팝업(상태, 매니저)
        버서커 = yield from self._단계_훔쳐배우기(상태, 매니저)
        yield from self._단계_퍽선택_팝업(매니저, 버서커)
        yield from self._단계_약점증가_배분(매니저)
        yield from self._단계_포켓몬_특성(매니저)
        yield from self._단계_스킬습득_팝업(상태, 매니저)

    def _단계_능력치배분_팝업(self, 상태, 매니저):
        """파티관리 - 능력치 배분 팝업"""
        매니저.current = "파티관리"
        매니저.get_screen("파티관리")._능력치배분_팝업(
            상태["파티"]["파티원"][0], 2, lambda 배분: None
        )
        yield 0.5
        _찍기("stat_popup")
        _팝업_닫기()
        결과["단계"].append("능력치 배분 팝업")

    def _단계_전직선택_팝업(self, 매니저):
        """전직 선택 팝업 - 귀검사 전직 5개, 격투가 넨마스터의 능력치 다시 고르기"""
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
        # 전직마다 추천 주/보조/약점 한 줄
        글들 = {w.text for w in 팝업.walk(restrict=True) if isinstance(w, Label)}
        for 전직 in gf.전직_레지스트리["귀검사"]:
            assert gf.전직_추천_문구(전직) in 글들, 전직
        _찍기("advancement_popup")
        _팝업_닫기()
        yield 0.3
        결과["단계"].append(
            "전직 선택 팝업(귀검사 전직 5개 모두 선택 가능, 추천 능력치 표시)"
        )

        # 격투가 전직: 넨마스터를 누르면 능력치 다시 고르기 팝업이 뜬다
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

    def _단계_마스터리선택_팝업(self, 매니저):
        """마스터리 선택 팝업 - 이름 토글 + 상세보기"""
        # 마스터리 선택 팝업: 줄마다 이름 토글 + [상세보기](설명은 상세보기 창에만)

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

    def _단계_스킬강화_팝업(self, 상태, 매니저):
        """레벨 12 스킬강화 팝업"""
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

    def _단계_훔쳐배우기(self, 상태, 매니저):
        """훔쳐배우기 - 퍽 목록에 없고 [스킬습득]에서 산다. 키운 버서커를 돌려준다"""
        # 훔쳐배우기: 퍽이 아니라 [스킬습득]에서 다른 전직의 스킬을 5배 값(500골드)에 산다
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
        return 버서커

    def _단계_퍽선택_팝업(self, 매니저, 버서커):
        """퍽 선택 팝업 - 능력치향상 -> 배분 팝업, 못 고르는 퍽 회색, 배운 퍽 숨김"""
        고른 = []
        # 퍽 "타입": 스탯획득 퍽(능력치향상)을 고르면 능력치 배분 팝업이 열린다
        매니저.get_screen("파티관리")._퍽선택_팝업(버서커, 고른.append)
        yield 0.5
        _팝업_버튼("능력치향상").dispatch("on_release")
        yield 0.6
        assert list(Window.children)[0].title == "능력치 배분", list(Window.children)
        list(Window.children)[0].dismiss()
        yield 0.6
        결과["단계"].append("능력치향상: 퍽 선택 -> 능력치 배분 팝업")

        # 못 고르는 퍽은 회색(이유와 함께, 누를 수 없음), 전직이 다른 퍽은 숨김
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
        # 퍽마다 [상세보기] - 설명 줄이 다음 버튼과 겹치지 않는다(줄 사이 겹침 없음)
        퍽팝업 = list(Window.children)[0]
        퍽버튼 = next(
            w
            for w in 퍽팝업.walk(restrict=True)
            if isinstance(w, Button) and w.text == "능력치향상"
        )
        행들 = sorted(
            {
                id(b.parent): b.parent
                for b in 퍽팝업.walk(restrict=True)
                if isinstance(b, Button) and b.text == "상세보기"
            }.values(),
            key=lambda w: -w.y,
        )
        assert len(행들) >= 2 and all(
            a.y >= b.top - 1 for a, b in zip(행들, 행들[1:])
        ), "퍽 줄이 겹친다"
        상세 = next(
            w
            for w in 퍽버튼.parent.children
            if isinstance(w, Button) and w.text == "상세보기"
        )
        상세.trigger_action(duration=0)
        yield 0.5
        상세팝업 = list(Window.children)[0]
        assert 상세팝업.title == "퍽 상세보기", 상세팝업.title
        _찍기("perk_detail")
        상세팝업.dismiss()
        yield 0.3
        list(Window.children)[0].dismiss()
        yield 0.6
        결과["단계"].append(
            "퍽 선택: 차수 미달 퍽은 회색(이유), 배운 퍽은 숨김, 퍽마다 [상세보기]"
        )

    def _단계_약점증가_배분(self, 매니저):
        """약점증가 - 배분 팝업에서 약점 4개"""
        # 약점증가: 주스탯·보조스탯을 뺀 4개가 약점 - 배분 팝업에서 "(약점)"으로 못 올린다
        고른 = []
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

    def _단계_포켓몬_특성(self, 매니저):
        """포켓몬 - 퍽 선택 -> 특성 고르기 팝업"""
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

    def _단계_스킬습득_팝업(self, 상태, 매니저):
        """파티관리 화면 배치와 [스킬습득] 팝업"""
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
        # 항목마다 테두리 상자 - 상자끼리 겹치지 않는다
        상자들 = [w for w in 화면.walk(restrict=True) if getattr(w, "항목상자", False)]
        assert len(상자들) == len(gf.캐릭터_스킬목록(상태, 거너)), len(상자들)
        상자들.sort(key=lambda w: -w.y)
        assert all(a.y >= b.top - 1 for a, b in zip(상자들, 상자들[1:])), (
            "상자가 겹친다"
        )
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
            screens_member._장비교체_팝업(귀검사, 슬롯, lambda: None)
            yield 0.5
            _찍기(f"equip_swap_{슬롯}")
            팝업 = Window.children[0]
            글들 = [w.text for w in 팝업.walk(restrict=True) if hasattr(w, "text")]
            assert any(요약 in 글 for 글 in 글들), 글들
            assert 글들.count("상세보기") >= 2, 글들
            # 분류 탭: 무기는 [전체] + 귀검사 무기 종류, 상의는 [전체] + 재질 - 한 줄에 다 보인다

            탭들 = [w for w in 팝업.walk(restrict=True) if isinstance(w, ToggleButton)]
            assert [t.text for t in 탭들] == gf.장비_교체_탭목록(상태, 귀검사, 슬롯)
            # 처음 탭: 무기는 [전체], 방어구는 숙련 재질(없으면 [전체])
            처음 = gf.장비_교체_처음탭(상태, 귀검사, 슬롯)
            assert [t.text for t in 탭들 if t.state == "down"] == [처음], 처음
            assert all(t.right <= 탭들[0].parent.right + 1 for t in 탭들)
            # 장비 칸은 글 줄 수만큼 낮다
            칸들 = [
                w
                for w in 팝업.walk(restrict=True)
                if isinstance(w, screens_member._테두리상자)
            ]
            assert 칸들 and max(w.height for w in 칸들) <= dp(84) + 1, [
                w.height for w in 칸들
            ]
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
        # 숙련이 있으면 방어구 교체 창은 그 재질 탭으로 연다
        원래특성 = list(귀검사["보유특성"])
        귀검사["보유특성"] = [t for t in 원래특성 if not t.endswith("숙련")] + [
            "판금숙련"
        ]
        screens_member._장비교체_팝업(귀검사, "상의", lambda: None)
        yield 0.5
        탭들 = [
            w
            for w in Window.children[0].walk(restrict=True)
            if isinstance(w, ToggleButton)
        ]
        assert [t.text for t in 탭들 if t.state == "down"] == ["판금"], [
            t.text for t in 탭들 if t.state == "down"
        ]
        _찍기("equip_swap_mastery_tab")
        _팝업_닫기()
        yield 0.3
        귀검사["보유특성"] = 원래특성
        # 세트 장비 상세보기: 세트 이름·구성·효과
        screens_member._아이템_상세_팝업(
            상태["상점카탈로그"]["장비"]["신발"]["브론델의 신발"]
        )
        yield 0.5
        글 = " ".join(
            w.text
            for w in Window.children[0].walk(restrict=True)
            if isinstance(w, Label)
        )
        for 조각 in (
            "브론델의 세트",
            "브론델의 흉갑",
            "브론델의 각반",
            "세트 효과: AC +1",
        ):
            assert 조각 in 글, (조각, 글)
        _찍기("equip_detail_set")
        _팝업_닫기()
        yield 0.3
        결과["단계"].append(
            "장비 교체 팝업 분류 탭(무기 종류/방어구 재질, 다른 직업군 무기 숨김), 줄 높이, "
            "숙련 재질 탭으로 열기, 세트 상세(구성·효과)"
        )
        무기 = next(iter(상태["상점카탈로그"]["장비"]["무기"].values()))
        screens_member._아이템_상세_팝업(무기)
        yield 0.5
        _찍기("equip_detail")
        _팝업_닫기()
        yield 0.3
        # 레어 무기: 파티 상세보기와 상점 자세히 보기에 "설명"이 보이고, 효과 원소 칸은 그대로 안 보인다
        레어 = 상태["상점카탈로그"]["장비"]["무기"]["복수의 영혼도"]
        for 이름, 열기 in (
            ("equip_detail_rare", lambda: screens_member._아이템_상세_팝업(레어)),
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
        # 악세서리 세트: 은도금 3종을 끼면 상세 정보 "장비 보너스 합계"에 세트 이름과 HP재생이 뜬다
        for 슬롯 in ("목걸이", "반지", "팔찌"):
            상태["소지품"]["장비"][f"은도금 {슬롯}"] = 1
            gf.장비_교체(상태, 귀검사, 슬롯, f"은도금 {슬롯}")
        매니저.get_screen("파티원")._상세정보_팝업(상태, 귀검사)
        yield 0.5
        _찍기("char_detail_accessory_set")
        글 = "\n".join(
            w.text for w in Window.children[0].walk(restrict=True) if hasattr(w, "text")
        )
        assert "세트효과: 은도금 세트" in 글 and "HP재생 +1" in 글, 글
        _팝업_닫기()
        yield 0.3
        for 슬롯 in ("목걸이", "반지", "팔찌"):
            gf.장비_해제(상태, 귀검사, 슬롯)
        결과["단계"].append(
            "장비 교체 팝업(무기/상의) + 상세보기(레어 무기 설명) + 악세서리 세트 상세 정보"
        )
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
        screens_member._장비교체_팝업(귀검사, "무기", lambda: None)
        screens_member._아이템_상세_팝업(무기)
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
