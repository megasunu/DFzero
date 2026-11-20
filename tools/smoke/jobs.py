"""화면 스모크 단계 - 직업별 스킬 화면 - 감옥·소환(골렘·정령)·프렌드 실드·인형·란마·축염포·연계·넨가드·합격·공격 연출."""

# common을 먼저 불러 kivy 창 설정을 끝낸다.
from tools.smoke.common import (
    _대상버튼들,
    _스킬줄_글,
    _스킬줄_버튼들,
    _아군_차례로,
    _찍기,
    _차례,
    _팝업_닫기,
    _팝업수,
    결과,
)
import main
import re
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView
import gameflow as gf
from game.system import rng
from game.system.combat import flow
from tests import support


class 직업스킬단계:
    def _단계_감옥_대상팝업(self, 상태, 매니저):
        """케라하의 얼음감옥: 감옥은 적 그림 칸에는 없고 대상 고르기 팝업에만
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

    def _단계_골렘_소환(self, 상태, 매니저):
        """인형사의 골렘 소환: 적 칸이 다섯 다 찼으면 부른 골렘이 쓰러진 적의 칸을 넘겨받아 칸은 다섯 그대로,
        골렘 그림과 이름이 그 칸에 뜨고 쓰러진 적은 칸에서 빠진다."""
        from game.system.combat import damage, monster_actions, stats
        from game.system.skill import skill_turn

        gf.전투_시작(상태, ["진흙 인형사"] + ["고블린"] * 4, 레벨=3, 차수=1)
        support.반응_처리(상태)
        전투상태 = 상태["전투상태"]
        for x in 전투상태["참가자"]:
            if x["진영"] == "아군":
                x["현재HP"] = 999
        인형사 = next(x for x in 전투상태["참가자"] if x["이름"] == "진흙 인형사")
        쓰러진 = next(x for x in gf.적_목록(상태) if x is not 인형사)
        damage.피해_적용(전투상태, 쓰러진, 10**6, 피해감소무시=True)
        인형사["현재HP"] = (int(stats.유효_최대HP(전투상태, 인형사)) - 1) // 2
        전투상태["현재턴"] = 전투상태["참가자"].index(인형사)
        monster_actions.몬스터_턴_실행(전투상태, 인형사)
        for _ in range(40):
            다음 = skill_turn.다음_턴(전투상태)
            if 다음 is 인형사:
                break
            if 다음["진영"] == "적":
                monster_actions.몬스터_턴_실행(전투상태, 다음)
        monster_actions.몬스터_턴_실행(전투상태, 인형사)
        assert any(x["이름"] == "진흙 골렘" for x in 전투상태["참가자"])
        _차례(전투상태, "거너")
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
        assert any("진흙 골렘" in t for t in 적칸글), 적칸글
        assert not any(쓰러진["이름"] in t for t in 적칸글), 적칸글
        그림들 = [str(그림) for _, 그림, _ in 전투._적그림목록]
        assert sum("asset_monster_mud_golem.webp" in g for g in 그림들) == 1, 그림들
        assert len(전투._적그림목록) == 5, 그림들
        _찍기("battle_golem_summon")

    def _단계_정령_소환(self, 상태, 매니저):
        """케라하의 4번 패턴 나이아스 소환: 빈 칸에 그림 없는 정령이 이름과 함께 뜬다."""
        from game.system import monster_ai
        from game.system.combat import monster_actions

        난수상태 = rng.상태()  # 뒤 단계의 굴림이 달라지지 않게
        gf.전투_시작(상태, ["결빙의 케라하"], 레벨=4, 차수=1)
        support.반응_처리(상태)
        전투상태 = 상태["전투상태"]
        마녀 = next(x for x in 전투상태["참가자"] if x["이름"] == "결빙의 케라하")
        원래 = monster_ai.행동_선택
        monster_ai.행동_선택 = lambda p: p["원본"]["패턴"][4]
        try:
            전투상태["현재턴"] = 전투상태["참가자"].index(마녀)
            monster_actions.몬스터_턴_실행(전투상태, 마녀)
        finally:
            monster_ai.행동_선택 = 원래
        assert any(x["이름"] == "나이아스" for x in 전투상태["참가자"]), 전투상태[
            "참가자"
        ]
        _차례(전투상태, "거너")
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
        assert any("나이아스" in t for t in 적칸글), 적칸글
        assert len(전투._적그림목록) == 2, 전투._적그림목록
        _찍기("battle_naias_summon")
        rng.상태_복원(난수상태)

    def _단계_프렌드_실드(self, 상태, 매니저):
        """프렌드 실드: 반응 자동이 꺼져 있으면 적의 단일 공격 대상이 될 때 반응 팝업에 살아 있는
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
        """인형사: 전투 [아이템]에서 인형을 쓰면(행동 없음) 아군 칸이 4개에서
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
        그림칸 = sorted(전투.아군그래픽행.children, key=lambda w: w.x)  # 왼쪽부터
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
        """란마 1/2: 수속성 공격에 맞으면 전투 화면 그림이 여성 그림(011m -> 011f)으로,
        화속성에 맞으면 남성 그림으로 돌아온다. 반대 성별 그림이 없는 캐릭터는 그림만 그대로다."""
        from game.data.ability.job_ability_0000 import 특성목록 as 공용특성
        from game.system import effect_engine
        from game.system.combat import hit_effects

        귀검사 = next(c for c in 상태["파티"]["파티원"] if c["직업"] == "귀검사")
        원래 = (list(귀검사["보유특성"]), 귀검사.get("성별"))
        try:
            귀검사["성별"] = "m"
            effect_engine.특성_부여(귀검사, "야빠빠 야빠빠", 공용특성["야빠빠 야빠빠"])
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
            hit_effects.피격_처리(전투상태, 적, p, 판정, 속성="수속성")
            전투.갱신()
            yield 0.4
            assert 귀검사["란마성별"] == "f" and 그림().endswith("011f.webp"), 그림()
            _찍기("battle_ranma_female")
            hit_effects.피격_처리(전투상태, 적, p, 판정, 속성="화속성")
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
        """축염포(넨마스터): 스킬을 쓰면 턴이 바로 끝나고, 남은 순서가 돈 뒤 밀린 차례에 발사되어
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
        """연계스킬: 연계 자동을 끄면 수플렉스가 맞았을 때 "연계 - 이름" 팝업이 뜨고, 수플렉스
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
        """넨가드(채널링): 쓴 다음 자기 턴이 오면 "채널링 - 이름" 팝업이 뜨고 [유지]/[해제]를 고른다.
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
        """합격(검귀): 원귀(회천)를 쓰면 스킬 목록의 합격이 "합격 : 월령참"으로 보이고, 누르면 대상을
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
        """공격하면 대상 그림 칸 위에 공격 종류 그림(칸에 맞춘 크기의 3배)이 떴다가 1초 뒤 사라진다(아군/적 모두)"""
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
        yield 1.3  # 앞 단계에서 남은 연출이 있었다면 사라질 때까지

        def 연출들():
            return [w for w in 전투.children if hasattr(w, "공격연출")]

        def 칸_위인가(그림, 참가자):
            """칸 가로 가운데, 대상 크기 그림의 세로 가운데(칸 바닥 아래로는 안 감).
            3배 크기라 칸 위로는 넘친다 - 세로는 바닥 위치만 본다."""
            칸 = 전투._그림칸[참가자["id"]]
            cx, _ = 그림.to_window(*그림.center)
            gy = 그림.to_window(*그림.pos)[1]
            x, y = 칸.to_window(*칸.pos)
            배율 = gf.공격연출_크기배율(상태, 참가자["id"])
            기대 = y + gf.공격연출_바닥(칸.height, 그림.height, 배율)
            return (
                x <= cx <= x + 칸.width
                and abs(gy - 기대) < 1
                and abs(cx - (x + 칸.width / 2)) < 1
            )

        assert 연출들() == [], [w.공격연출 for w in 연출들()]
        적 = next(p for p in 전투상태["참가자"] if p["진영"] == "적" and p["생존"])
        # 연출이 뜨는 순간을 기록한다 - 느린 CI 실행기에서는 화면 한 장 사이에 0.5초 연출이 떴다가
        # 사라져 나중에 훑어보면 없다. 뜬 그림의 종류와 칸 위인지는 뜬 그 자리에서 잰다.
        띄운 = []

        def 기록하며_띄우기(연출, 원래=전투._공격연출_하나):
            원래(연출)
            그림 = 전투._떠있는_연출.get(연출["대상id"])
            띄운.append(
                (
                    연출["종류"],
                    getattr(그림, "공격연출", None),
                    그림 is not None and 칸_위인가(그림, 적),
                )
            )

        전투._공격연출_하나 = 기록하며_띄우기
        전투._일반공격_실행(적)  # 명중이면 무기 종류, 빗나가면 실패
        # 반응 자동 사용이 꺼져 있으면 공격이 작업 스레드에서 돌고 끝난 뒤에야 화면이 연출을
        # 예약한다 - 정한 시간 한 번이 아니라 뜰 때까지(최대 3초) 기다린다
        for _ in range(60):
            yield 0.05
            if 띄운:
                break
        del 전투._공격연출_하나  # 클래스의 원래 함수로 되돌린다
        # 귀검사 녹슨 소검(공격타입 참격, 무속성): 명중이면 참격:무, 빗나가면 실패
        assert len(띄운) == 1 and 띄운[0][0] in ("참격:무", "실패"), (
            띄운,
            getattr(전투, "_엔진중", None),
            전투상태["로그"][-3:],
        )
        assert 띄운[0][1] == 띄운[0][0], ("그림이 떴다", 띄운)
        assert 띄운[0][2], "적 그림 칸 위에 뜬다"
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
        그림 = 연출들()[0] if 연출들() else None
        if 그림 is not None:  # 3배 크기 - 칸 폭의 0.9배에 맞춘 것보다 크다
            assert 그림.width > 전투._그림칸[적["id"]].width, 그림.size
        yield 1.3
        assert 연출들() == [], "1초 뒤 사라진다"

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
        # 크기(소형/중형/대형)마다 높이가 다르다 - 아군도 버프로 크기가 바뀔 수 있다
        원본 = 귀검사["원본"]
        높이 = {}
        for 크기 in ("소형", "중형", "대형"):
            귀검사["원본"] = dict(원본, 크기=크기)
            전투._공격연출_하나({"대상id": 귀검사["id"], "종류": "타격:무"})
            그림 = 연출들()[0]
            assert 칸_위인가(그림, 귀검사), 크기
            높이[크기] = 그림.y
        귀검사["원본"] = 원본
        # 3배 크기라 중형·대형도 칸 바닥에 붙을 수 있다 - 큰 대상일수록 낮아지지는 않는다
        assert 높이["소형"] <= 높이["중형"] <= 높이["대형"], 높이
        yield 1.3
        assert 연출들() == [], "1초 뒤 사라진다"
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
            "공격 연출(적/아군 그림 칸 위에 종류 그림 3배, 1초 뒤 사라짐), 자세하게 계산 줄"
        )
        상태["전투상태"] = None
        매니저.current = "마을"
