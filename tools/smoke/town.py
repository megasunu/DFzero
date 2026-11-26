"""화면 스모크 단계 - 상점(구매·판매·해체)·봉인·강화·마법부여·인형사·연금술·주점·소지품·레테·스프레이."""

# common을 먼저 불러 kivy 창 설정을 끝낸다.
from tools.smoke.common import (
    _글,
    _상점_목록이름,
    _상점_탭,
    _상점_탭들,
    _찍기,
    _팝업_닫기,
    결과,
)
import main
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
import gameflow as gf
from game.screens import screens_common, screens_member
from game.system import rng
from tests import support


class 마을단계:
    def _단계_상점(self, 상태, 매니저):
        """상점 - 구매/판매 목록, [전문직업] 장비해체(일괄해체 확인 팝업)와 봉인해제/봉인변환, 인형사"""
        yield from self._단계_상점_구매판매(상태, 매니저)
        yield from self._단계_상점_해체(상태, 매니저)
        yield from self._단계_봉인(상태, 매니저)
        yield from self._단계_장비강화(상태, 매니저)
        yield from self._단계_마법부여(상태, 매니저)
        yield from self._단계_인형사(상태, 매니저)
        yield from self._단계_연금술(상태, 매니저)

    def _단계_상점_구매판매(self, 상태, 매니저):
        """상점 구매 - 레어도 색, 장비 탭 2줄, 무기 직업군/종류 탭, 방어구 재질 탭, 판매 목록"""
        yield from self._단계_상점_레어도색(상태, 매니저)
        yield from self._단계_상점_장비탭(상태, 매니저)
        yield from self._단계_상점_인형탭(상태, 매니저)
        yield from self._단계_상점_판매목록(상태, 매니저)

    def _단계_상점_레어도색(self, 상태, 매니저):
        """상점 구매 장비 목록 - 아이템 이름의 레어도 색"""
        매니저.current = "상점"
        상점 = 매니저.get_screen("상점")
        상점._대분류_그리기("구매")
        상점._탭목록_그리기("구매", "장비")
        yield 0.5
        _찍기("shop_buy")
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

    def _단계_상점_장비탭(self, 상태, 매니저):
        """상점 장비 탭 2줄, 무기 직업군/종류 탭, 방어구 재질 탭"""
        상점 = 매니저.get_screen("상점")
        # 부위 탭 2줄이 화면 안에 다 들어간다(밀어서 넘기지 않음)
        부위 = [t for t in _상점_탭들(상점) if t.group == _상점_탭(상점, "무기").group]
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
        assert [
            t.text for t in _상점_탭들(상점) if t.text in gf.상점_무기_직업군탭(상태)
        ][:6] == gf.상점_무기_직업군탭(상태)
        _상점_탭(상점, "거너").trigger_action(duration=0)
        yield 0.3
        종류 = gf.상점_무기_종류탭(상태, "거너")
        assert all(any(t.text == k for t in _상점_탭들(상점)) for k in 종류[1:]), [
            t.text for t in _상점_탭들(상점)
        ]
        무기 = 상태["상점카탈로그"]["장비"]["무기"]
        이름들 = _상점_목록이름(상점, 상태)
        assert 이름들 and all(무기[n]["분류"] == "거너 무기" for n in 이름들), 이름들
        _상점_탭(상점, 종류[1]).trigger_action(duration=0)
        yield 0.3
        assert all(
            gf.상점_분류_일치("무기", 무기[n], None, 종류[1])
            for n in _상점_목록이름(상점, 상태)
        ), _상점_목록이름(상점, 상태)
        _찍기("shop_buy_weapon_gunner")
        # 방어구: 재질 탭
        _상점_탭(상점, "상의").trigger_action(duration=0)
        yield 0.3
        _상점_탭(상점, "판금").trigger_action(duration=0)
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
        assert all(상의[n]["재질"] == "판금" for n in _상점_목록이름(상점, 상태)), (
            _상점_목록이름(상점, 상태)
        )
        _찍기("shop_buy_top_plate")
        결과["단계"].append(
            "상점 장비 탭 2줄(한 화면) + 무기 직업군->종류 탭 + 방어구 재질 탭"
        )

    def _단계_상점_인형탭(self, 상태, 매니저):
        """상점 소모품 인형 탭 - 상점 인형 5종"""
        상점 = 매니저.get_screen("상점")
        # 소모품 "인형" 탭 - 상점 인형 5종만(28호는 팔지 않는다)
        상점._탭목록_그리기("구매", "소모품")
        yield 0.3
        _상점_탭(상점, "인형").trigger_action(duration=0)
        yield 0.3
        인형글 = [
            _글(w.text)
            for w in 상점._목록틀.walk(restrict=True)
            if isinstance(w, main.Label)
            and not isinstance(w, Button)
            and _글(w.text) in 상태["상점카탈로그"]["소모품"]["인형"]
        ]
        assert 인형글 == [
            f"아라드의 흔한 {직업}"
            for 직업 in ("귀검사", "격투가", "거너", "마법사", "프리스트")
        ], 인형글
        _찍기("shop_buy_doll")
        결과["단계"].append("상점 소모품 인형 탭(상점 인형 5종, 28호 없음)")

    def _단계_상점_판매목록(self, 상태, 매니저):
        """상점 판매 장비 목록 - 탭 2줄"""
        상점 = 매니저.get_screen("상점")
        상점._탭목록_그리기("판매", "장비")
        yield 0.5
        assert (
            len(
                {
                    t.y
                    for t in _상점_탭들(상점)
                    if t.group == _상점_탭(상점, "무기").group
                }
            )
            == 2
        )
        _찍기("shop_sell")
        # 체크박스 판매: 줄 높이 1.5배, 줄마다 [판매] 대신 체크박스, 아래 [일괄해제][일괄선택][판매]
        from kivy.uix.checkbox import CheckBox

        상의 = [
            n
            for n, a in 상태["상점카탈로그"]["장비"]["상의"].items()
            if a.get("레어도") == "커먼"
        ][:2]
        for n in 상의:
            상태["소지품"]["장비"][n] = 상태["소지품"]["장비"].get(n, 0) + 1
        _상점_탭(상점, "상의").trigger_action(duration=0)
        yield 0.4
        체크들 = [
            w for w in 상점._목록틀.walk(restrict=True) if isinstance(w, CheckBox)
        ]
        assert len(체크들) == len(gf.상점_판매목록(상태, "장비", "상의")) >= 2, len(
            체크들
        )
        assert all(abs(c.parent.height - 84) < 1 for c in 체크들), [
            c.parent.height for c in 체크들
        ]
        assert not any(
            isinstance(w, Button) and w.text == "판매"
            for w in 상점._목록틀.walk(restrict=True)
        ), "줄마다 [판매]가 남았다"
        아래 = {
            w.text: w
            for w in 상점.내용틀.walk(restrict=True)
            if isinstance(w, Button) and w.text in ("일괄해제", "일괄선택", "판매")
        }
        assert set(아래) == {"일괄해제", "일괄선택", "판매"}, set(아래)
        assert 아래["판매"].x >= 아래["일괄선택"].right - 1, "판매는 오른쪽"
        아래["일괄선택"].trigger_action(duration=0)
        assert all(c.active for c in 체크들)
        아래["일괄해제"].trigger_action(duration=0)
        assert not any(c.active for c in 체크들)
        체크들[0].active = True
        _찍기("shop_sell_check")
        골드 = 상태["소지품"]["골드"]
        판매전 = len(gf.상점_판매목록(상태, "장비", "상의"))
        아래["판매"].trigger_action(duration=0)
        yield 0.3
        assert 상태["소지품"]["골드"] > 골드, "체크한 것을 팔지 않았다"
        assert len(gf.상점_판매목록(상태, "장비", "상의")) == 판매전 - 1
        결과["단계"].append(
            "상점 구매/판매 목록, 판매는 체크박스(1.5배 줄, 일괄해제/일괄선택/판매 -> 체크한 것만 팔림)"
        )

    def _단계_상점_해체(self, 상태, 매니저):
        """[전문직업] 장비해체 - 장비 -> 소울/큐브 조각, [전체] 탭, 일괄해체 확인 팝업"""
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
        assert 메뉴글[:7] == [
            ("장비강화", False),
            ("장비해체", False),
            ("마법부여", False),
            ("봉인해제", False),
            ("봉인변환", False),
            ("인형사", False),
            ("연금술", False),
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
            "전문직업 메뉴 7개, 상점에 해체 없음, "
            "장비해체(장비 -> 소울 + 큐브 조각, [전체] 탭, 일괄해체 커먼/전체 확인 팝업)"
        )

    def _단계_봉인(self, 상태, 매니저):
        """[전문직업] 봉인해제(소지품 + 장착 중, 이름의 [ ]는 글자로) -> 마법의 장비, 봉인변환 -> 다른 능력, 돈/소울 부족"""
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

        def 봉인해제_목록():
            화면._메인_그리기()
            next(
                w
                for w in 화면.내용틀.walk(restrict=True)
                if isinstance(w, Button) and w.text == "봉인해제"
            ).dispatch("on_release")

        # 이름의 [ ]는 마크업이 아니라 글자로 보여야 한다(#847) - 이름을 잠깐 바꿔 목록을 그려 본다
        원래이름 = 귀검사["캐릭터명"]
        귀검사["캐릭터명"] = "[i]귀검"
        봉인해제_목록()
        yield 0.3
        착용줄 = [
            w.text
            for w in 화면._목록틀.walk(restrict=True)
            if isinstance(w, Label) and "귀검 착용" in w.text
        ]
        귀검사["캐릭터명"] = 원래이름
        assert 착용줄 and all("&bl;i&br;귀검" in t for t in 착용줄), 착용줄
        봉인해제_목록()
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

    def _단계_장비강화(self, 상태, 매니저):
        """[전문직업] 장비강화 - 여섯 선택지, 착용 중인 무기 강화((착용중) 표시), 강화한 무기는 증폭 못 함"""
        화면 = 매니저.get_screen("전문직업")
        소지품 = 상태["소지품"]
        귀검사 = 상태["파티"]["파티원"][0]
        소지품["장비"]["강철 소검"] = 소지품["장비"].get("강철 소검", 0) + 1
        gf.장비_교체(상태, 귀검사, "무기", "강철 소검")
        소지품["골드"] = 1000
        소지품["재료"]["언커먼 소울"] = 3
        소지품["재료"]["라이언 코크스"] = 3

        def 버튼들(틀, 글):
            return [
                w
                for w in 틀.walk(restrict=True)
                if isinstance(w, Button) and w.text == 글
            ]

        매니저.current = "전문직업"
        yield 0.3
        화면._메인_그리기()
        버튼들(화면.내용틀, "장비강화")[0].dispatch("on_release")
        yield 0.3
        선택지 = [
            w.text for w in 화면._목록틀.walk(restrict=True) if isinstance(w, Button)
        ]
        assert 선택지 == gf.장비강화_메뉴, 선택지
        _찍기("profession_enhance_menu")
        버튼들(화면._목록틀, "무기강화")[0].dispatch("on_release")
        yield 0.3

        def 줄_버튼(이름, 버튼글):
            """이름 글(과 "(착용중)")이 든 줄의 실행 버튼 - 목록에는 다른 장비 줄도 있다."""
            행 = next(
                행
                for 행 in 화면._목록틀.children
                if any(
                    isinstance(w, Label) and 이름 in w.text and "(착용중)" in w.text
                    for w in 행.walk(restrict=True)
                )
            )
            return 버튼들(행, 버튼글)[0]

        _찍기("profession_enhance_list")
        줄_버튼("강철 소검", "강화").dispatch("on_release")
        yield 0.3
        assert 귀검사["장착장비"]["무기"] == "+1강 강철 소검", 귀검사["장착장비"]
        assert "+1강 강철 소검" in 화면.안내라벨.text, 화면.안내라벨.text
        assert 소지품["골드"] == 900 and 소지품["재료"]["언커먼 소울"] == 2
        assert 소지품["재료"]["라이언 코크스"] == 2
        _찍기("profession_enhance_done")
        # 강화한 무기는 증폭할 수 없다(버튼이 꺼진다), [◀ 뒤로]는 장비강화 선택지로
        화면._강화_그리기("무기증폭")
        yield 0.3
        assert 줄_버튼("+1강 강철 소검", "증폭").disabled
        버튼들(화면.내용틀, "◀ 뒤로")[0].dispatch("on_release")
        yield 0.3
        assert 버튼들(화면._목록틀, "특수장비증폭")
        화면._나가기()
        yield 0.3
        결과["단계"].append(
            "장비강화(선택지 6개, 착용 중인 무기 강화 (착용중)/100G+언커먼 소울+라이언 코크스, 강화한 무기 증폭 불가, 뒤로)"
        )

    def _단계_마법부여(self, 상태, 매니저):
        """[전문직업] 마법부여 - 부위 탭 2줄, 착용 중인 무기 [선택] -> 비노슈 [부여](100G, 화속성),
        같은 것은 다시 못 건다, 무기가 아닌 부위는 [선택]이 꺼진다"""
        화면 = 매니저.get_screen("전문직업")
        소지품 = 상태["소지품"]
        귀검사 = 상태["파티"]["파티원"][0]
        무기 = 귀검사["장착장비"]["무기"]  # 장비강화 단계가 남긴 +1강 강철 소검
        소지품["골드"] = 1000

        def 버튼들(틀, 글):
            return [
                w
                for w in 틀.walk(restrict=True)
                if isinstance(w, (Button, ToggleButton)) and w.text == 글
            ]

        def 줄_버튼(이름, 버튼글):
            행 = next(
                행
                for 행 in 화면._목록틀.children
                if any(
                    isinstance(w, Label) and 이름 in w.text and "(착용중)" in w.text
                    for w in 행.walk(restrict=True)
                )
            )
            return 버튼들(행, 버튼글)[0]

        매니저.current = "전문직업"
        yield 0.3
        화면._메인_그리기()
        버튼들(화면.내용틀, "마법부여")[0].dispatch("on_release")
        yield 0.3
        탭들 = [
            w.text
            for w in 화면.내용틀.walk(restrict=True)
            if isinstance(w, ToggleButton)
        ]
        assert 탭들 == [t for 줄 in gf.마법부여_탭줄() for t in 줄], 탭들
        _찍기("profession_enchant_list")
        줄_버튼(무기, "선택").dispatch("on_release")
        yield 0.3
        _찍기("profession_enchant_choices")
        부여버튼 = 버튼들(화면._목록틀, "부여")  # 비노슈/케라하/지크프리트
        assert len(부여버튼) == 3 and not any(b.disabled for b in 부여버튼)
        부여버튼[0].dispatch("on_release")
        yield 0.3
        새이름 = f"{무기} [비노슈]"
        assert 귀검사["장착장비"]["무기"] == 새이름, 귀검사["장착장비"]
        assert 소지품["골드"] == 900, 소지품["골드"]
        assert 새이름 in 화면.안내라벨.text, 화면.안내라벨.text
        무기데이터 = 상태["장비데이터모음"][귀검사["캐릭터명"]]["무기"]
        assert 무기데이터["마법부여"]["속성"] == "화속성", 무기데이터
        _찍기("profession_enchant_done")
        # 상세보기 맨 아래에 마법부여 효과를 따로 적는다
        screens_member._아이템_상세_팝업(무기데이터)
        yield 0.5
        글 = " ".join(
            w.text
            for w in Window.children[0].walk(restrict=True)
            if isinstance(w, Label)
        )
        글 = 글.replace("&bl;", "[").replace("&br;", "]")
        assert "[b][마법부여] 비노슈[/b]\n무기에 화속성을 부여한다." in 글, 글
        assert 글.index("무기 공격력") < 글.index("[마법부여]"), 글  # 원래 효과 아래
        _찍기("profession_enchant_detail")
        _팝업_닫기()
        yield 0.3
        # 같은 것은 다시 못 건다(라벨 글은 대괄호가 마크업 회피 글자라 이름 앞부분으로 찾는다)
        줄_버튼("강철 소검", "선택").dispatch("on_release")
        yield 0.3
        assert 버튼들(화면._목록틀, "부여")[0].disabled
        assert any(
            isinstance(w, Label) and "이미 부여됨" in w.text
            for w in 화면._목록틀.walk(restrict=True)
        )
        버튼들(화면.내용틀, "◀ 뒤로")[0].dispatch("on_release")
        yield 0.3
        # 특수장비(귀걸이)는 걸 수 있는 것이 없다
        소지품["장비"]["망가진 귀걸이"] = 1
        버튼들(화면.내용틀, "귀걸이")[0].dispatch("on_release")
        yield 0.3
        선택들 = 버튼들(화면._목록틀, "선택")
        assert 선택들 and all(b.disabled for b in 선택들)
        # 상의는 타우 가드를 걸 수 있다
        버튼들(화면.내용틀, "상의")[0].dispatch("on_release")
        yield 0.3
        assert any(not b.disabled for b in 버튼들(화면._목록틀, "선택"))
        # 뒤 단계(공격 연출 등)는 무속성 무기를 기대한다 - 부여 전 무기로 돌려 끼운다
        소지품["장비"][무기] = 소지품["장비"].get(무기, 0) + 1
        gf.장비_교체(상태, 귀검사, "무기", 무기)
        화면._나가기()
        yield 0.3
        결과["단계"].append(
            "마법부여(부위 탭 12개, 착용 중인 +1강 무기 선택 -> 비노슈 100G 화속성, 상세보기 맨 아래 마법부여, 이미 부여됨, 귀걸이는 선택 꺼짐, 상의는 켜짐)"
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

    def _단계_연금술(self, 상태, 매니저):
        """[전문직업] 연금술 - 탭 전체/재료/소모품, 라이언 코크스 -> 강렬한 기운, 무색 큐브 조각 -> 포션,
        재료가 모자라면 [제작] 못 누름"""

        def 버튼(위젯, 글):
            return next(
                w
                for w in 위젯.walk(restrict=True)
                if isinstance(w, Button) and w.text == 글
            )

        def 행(화면, 이름):
            return next(
                w.parent
                for w in 화면._목록틀.walk(restrict=True)
                if isinstance(w, Label) and w.text.startswith(이름 + "  (")
            )

        매니저.current = "전문직업"
        yield 0.3
        화면 = 매니저.get_screen("전문직업")
        재료 = 상태["소지품"]["재료"]
        재료["라이언 코크스"] = 1
        재료["무색 큐브 조각"] = 10
        화면._메인_그리기()
        버튼(화면.내용틀, "연금술").dispatch("on_release")
        yield 0.3
        탭들 = [
            w.text
            for w in 화면.내용틀.walk(restrict=True)
            if isinstance(w, ToggleButton)
        ]
        assert 탭들 == ["전체", "재료", "소모품"], 탭들
        _찍기("profession_alchemy_all")
        버튼(화면.내용틀, "재료").dispatch("on_release")
        yield 0.3
        assert "라이언 코크스 1/1" in 행(화면, "강렬한 기운").children[-1].text
        버튼(행(화면, "강렬한 기운"), "제작").dispatch("on_release")
        yield 0.3
        assert 재료["강렬한 기운"] == 1 and "라이언 코크스" not in 재료, 재료
        assert 버튼(행(화면, "모순의 결정체"), "제작").disabled, (
            "코크스가 없으면 못 만듦"
        )
        _찍기("profession_alchemy_material")
        버튼(화면.내용틀, "소모품").dispatch("on_release")
        yield 0.3
        assert 버튼(행(화면, "입문자용 HP 포션"), "제작").disabled  # 조각 10 < 20
        보유전 = 상태["소지품"].get("포션", {}).get("초보자용 HP 포션", 0)
        버튼(행(화면, "초보자용 HP 포션"), "제작").dispatch("on_release")
        yield 0.3
        assert 상태["소지품"]["포션"]["초보자용 HP 포션"] == 보유전 + 1
        assert "무색 큐브 조각" not in 재료, 재료
        _찍기("profession_alchemy_potion")
        재료.pop("강렬한 기운")
        화면._나가기()
        yield 0.3
        결과["단계"].append(
            "연금술: 탭 전체/재료/소모품, 라이언 코크스 1 -> 강렬한 기운(코크스 없으면 제작 못 누름), "
            "무색 큐브 조각 10 -> 초보자용 HP 포션(입문자용은 못 누름)"
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
        """능력치 역할 다시 고르기: 전직 -> (스타일) -> 능력치 팝업(전직별 표가 골라져 있음) -> 확인,
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

    def _단계_스프레이_플라스크(self, 상태, 매니저):
        """스프레이·속성 플라스크: 마을 소지품 [스프레이]에는 [사용] 없음, 던전 소지품 [스프레이] [사용]
        -> 결과 팝업 -> 던전 상태줄 "스프레이 10", [부여] [사용] -> 파티원 -> 무기에 화속성"""
        import copy as _copy

        앱 = App.get_running_app()
        앱.게임상태 = 상태
        상태["전투상태"] = None
        상태["던전상태"] = None
        원래소지품 = _copy.deepcopy(상태["소지품"])
        상태["소지품"].setdefault("소모품", {}).update(
            {"벌레퇴치 스프레이": 1, "샐러맨더 플라스크": 1}
        )

        def 버튼(위젯, 글):
            return next(
                w
                for w in 위젯.walk(restrict=True)
                if isinstance(w, Button) and _글(w.text) == 글
            )

        def 팝업():
            return Window.children[0]

        def 사용버튼(화면, 이름):
            행 = next(
                w.parent
                for w in 화면._목록틀.walk(restrict=True)
                if isinstance(w, Label) and _글(w.text) == 이름
            )
            return next(
                (
                    w
                    for w in 행.walk(restrict=True)
                    if isinstance(w, Button) and _글(w.text) == "사용"
                ),
                None,
            )

        def 탭_열기(화면, 탭):
            버튼(화면, 탭).trigger_action(duration=0)

        # 마을 소지품 - 스프레이는 [사용]이 없다
        매니저.current = "마을"
        yield 0.3
        버튼(매니저.current_screen, "소지품/창고").trigger_action(duration=0)
        yield 0.3
        버튼(팝업(), "소지품").trigger_action(duration=0)
        yield 0.3
        화면 = 매니저.current_screen
        버튼(화면, "소모품").trigger_action(duration=0)
        yield 0.3
        _찍기("spray_tabs")
        탭_열기(화면, "스프레이")
        yield 0.3
        assert 사용버튼(화면, "벌레퇴치 스프레이") is None, (
            "마을에서는 스프레이를 못 쓴다"
        )
        버튼(화면, "◀ 뒤로").trigger_action(duration=0)
        yield 0.3
        버튼(화면, "◀ 나가기").trigger_action(duration=0)
        yield 0.3

        # 던전 소지품 - 스프레이 [사용] -> 결과 팝업 -> 상태줄
        gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
        던전 = 매니저.get_screen("던전")
        던전.갱신()
        매니저.current = "던전"
        yield 0.3
        버튼(던전, "소지품").trigger_action(duration=0)
        yield 0.3
        화면 = 매니저.current_screen
        버튼(화면, "소모품").trigger_action(duration=0)
        yield 0.3
        탭_열기(화면, "스프레이")
        yield 0.3
        사용버튼(화면, "벌레퇴치 스프레이").trigger_action(duration=0)
        yield 0.3
        글들 = [_글(w.text) for w in 팝업().walk(restrict=True) if isinstance(w, Label)]
        assert any("10걸음" in t for t in 글들), 글들
        _찍기("spray_used")
        _팝업_닫기()
        yield 0.2
        assert gf.스프레이_남은걸음(상태) == 10

        # [부여] [사용] -> 파티원 고르기 -> 무기에 화속성
        탭_열기(화면, "부여")
        yield 0.3
        사용버튼(화면, "샐러맨더 플라스크").trigger_action(duration=0)
        yield 0.3
        c = 상태["파티"]["파티원"][0]
        next(
            w
            for w in 팝업().walk(restrict=True)
            if isinstance(w, Button) and _글(w.text).startswith(c["캐릭터명"])
        ).trigger_action(duration=0)
        yield 0.3
        assert c.get("무기속성부여") == ["화속성"], c.get("무기속성부여")
        assert "화속성" in 화면.안내라벨.text, 화면.안내라벨.text
        _찍기("flask_used")
        for _ in range(3):
            if 매니저.current != "소지품":
                break
            글들 = {
                _글(w.text) for w in 화면.walk(restrict=True) if isinstance(w, Button)
            }
            버튼(화면, "◀ 뒤로" if "◀ 뒤로" in 글들 else "◀ 나가기").trigger_action(
                duration=0
            )
            yield 0.3
        assert 매니저.current == "던전", 매니저.current
        던전.갱신()
        yield 0.2
        assert "스프레이 10" in 던전.상태라벨.text, 던전.상태라벨.text
        _찍기("spray_dungeon_status")

        c.pop("무기속성부여", None)
        상태["소지품"] = 원래소지품
        상태["던전상태"] = None
        결과["단계"].append(
            "스프레이·플라스크(#506): 마을 [스프레이]는 [사용] 없음, 던전 [사용] -> 팝업 -> 상태줄 스프레이 10, "
            "[부여] [사용] -> 파티원 -> 무기에 화속성"
        )
