"""화면 스모크 단계 - 전투 화면(스킬·대상·아이템·도망)·전투 종료와 보상·자동전투·몬스터 표시."""

# common을 먼저 불러 kivy 창 설정을 끝낸다.
from tools.smoke.common import (
    _글,
    _대상버튼들,
    _뒤로키,
    _스킬줄_글,
    _스킬줄_버튼들,
    _스킬줄_칸,
    _아군_차례로,
    _찍기,
    _차례,
    _팝업_닫기,
    _팝업_버튼,
    _팝업글,
    _팝업수,
    _확인_누르기,
    결과,
)
import main
from kivy.core.window import Window
import gameflow as gf
from game.screens import screens_common
from game.system import rng
from game.system import skill_system
from game.system.combat import flow
from tests import support


class 전투단계:
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
        # 팝업 폭은 기준 화면의 0.7 - 긴 이름이 버튼 안에 들어간다
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

        # [아이템]의 속성 플라스크: 보조행동 1개로 자기 무기에 속성, 로그에 남는다
        p = _차례(전투상태, "귀검사")
        상태["소지품"]["소모품"]["잭프로스트 플라스크"] = 1
        보조 = p["행동자원"]["보조행동"]
        전투._아이템_클릭()
        yield 0.3
        플라스크버튼 = [
            b for b in _대상버튼들() if b.text.startswith("잭프로스트 플라스크")
        ]
        assert 플라스크버튼 and not 플라스크버튼[0].disabled, [
            b.text for b in _대상버튼들()
        ]
        플라스크버튼[0].trigger_action(duration=0)
        yield 0.5
        assert p["행동자원"]["보조행동"] == 보조 - 1, p["행동자원"]
        assert p["원본"].get("무기속성부여") == ["수속성"], p["원본"]
        assert "잭프로스트 플라스크 사용" in 전투상태["로그"][-1].get("행동", "")
        p["원본"].pop("무기속성부여", None)
        결과["단계"].append("전투 [아이템] 속성 플라스크(보조행동 1, 무기에 수속성)")

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
        # 스킬은 작업 스레드에서 돈다 - 엔진이 멈출 때까지 기다린 뒤 로그를 본다(CI에서 기다리지 않아
        # 로그가 아직 비어 한 번 실패했다). 이어지는 적 차례의 반응 팝업은 쓰지 않는다
        for _ in range(50):
            if not 전투._엔진중:
                break
            if "사용 안 함" in _팝업글():
                _팝업_버튼("사용 안 함").dispatch("on_release")
            yield 0.2
        assert not 전투._엔진중, _팝업글()
        # 상급마법은 캐스팅 - 쓰면 턴이 끝나고(화면이 바로 넘긴다) 밀린 차례에 쏜다
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
        """전투 종료/보상, 자동전투, 몬스터 크기, 챔피언 이름표, 황금 고블린 도망, 주점"""
        yield from self._단계_전투종료_보상(상태, 매니저, 전투)
        yield from self._단계_공어_연속전투(상태, 매니저, 전투)
        yield from self._단계_자동전투(상태, 매니저, 전투)
        yield from self._단계_몬스터_크기(상태, 매니저, 전투)
        yield from self._단계_익스펠러_석상(상태, 매니저, 전투)
        yield from self._단계_챔피언_이름표(상태, 매니저, 전투)
        yield from self._단계_챔피언_버프칸(상태, 매니저, 전투)
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
            yield from self._단계_전투종료_한판(
                상태, 매니저, 전투, 몬스터들, 끝내기, 첫줄, 전리품줄, 도착, 사진
            )
        결과["단계"].append(
            "전투 종료 팝업(승리 전리품/없음, 도망, 패배) + 전투 보상 선택/포기"
        )

    def _단계_전투종료_한판(
        self, 상태, 매니저, 전투, 몬스터들, 끝내기, 첫줄, 전리품줄, 도착, 사진
    ):
        """전투 하나를 끝내 종료 팝업의 첫 줄·전리품 줄을 확인하고, 승리면 전투 보상, [확인] 뒤 도착 화면"""
        원래맵 = 상태["던전상태"]["맵정보"]
        if 전리품줄 is False:
            # "전리품 없음": 던전 공용 드랍도, 골드도 없는 전투로 만든다
            상태["던전상태"]["맵정보"] = {**원래맵, "드랍표": []}
        gf.전투_시작(상태, 몬스터들, 레벨=6, 차수=2)  # 시작 반응에 안 쓰러지게
        if 전리품줄 is False:
            for 적 in gf.적_목록(상태):
                적["원본"]["획득골드"] = "미정"
                적["원본"]["드랍표"] = []  # 몬스터 개인 드랍(monster_drop.py)도 없앤다
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
            yield from self._단계_전투보상(상태, 전리품줄)
        _확인_누르기()
        yield 0.5
        assert 매니저.current == 도착, 매니저.current
        if 도착 == "마을":
            assert 상태["던전상태"] is None, "패배 귀환 뒤에도 던전 안이다(#671)"
            gf.던전_진입(상태, "dungeon_01A_D01_Lorien")

    def _단계_전투보상(self, 상태, 전리품줄):
        """승리 팝업의 [전투 보상] - [확인]은 받거나 포기하기 전까지 잠김"""
        # [확인]은 전투 보상을 받거나 포기하기 전까지 잠겨 있다
        assert _팝업_버튼("확인").disabled and not _팝업_버튼("전투 보상").disabled
        칸 = gf.전투_보상_칸(상태)
        if all(칸) and 칸[0] != 칸[1]:
            # 첫 칸 아이템은 소지품에 하나 넣어 둔다 - "보유 1" 줄이 그려지는지 보려고
            장비칸 = 상태["소지품"]["장비"]
            장비칸[칸[0]] = 장비칸.get(칸[0], 0) + 1
        _팝업_버튼("전투 보상").dispatch("on_release")
        yield 0.5
        assert _팝업_버튼("선택").disabled  # 박스를 누르기 전
        if 전리품줄 is True:  # 고블린들 - 후보가 있다
            yield from self._단계_전투보상_받기(상태, 칸)
        else:  # 힐가브 - 후보 없음
            yield from self._단계_전투보상_포기(상태, 칸)
        assert not gf.전투_보상_대기중(상태)
        assert not _팝업_버튼("확인").disabled and _팝업_버튼("전투 보상").disabled

    def _단계_전투보상_받기(self, 상태, 칸):
        """후보가 있는 보상 - 칸마다 이름/부위/보유 줄, 고르면 소지품과 전리품 줄에 더해진다"""
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
            assert 박스_.height < 3 * sc.글자_높이("15sp") + 60, 박스_.height
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
        assert 새글 == "\n".join(gf.전투_종료_문구(상태, "아군승리")) and any(
            줄.startswith(칸[1]) for 줄 in 새글.split("\n")[2:]
        ), 새글
        _찍기("battle_end_win_reward")

    def _단계_전투보상_포기(self, 상태, 칸):
        """후보 없는 보상(힐가브) - 세 칸 모두 빈칸, 포기하면 10골드"""
        assert 칸 == [None, None, None], 칸
        _찍기("battle_reward_empty")
        골드 = 상태["소지품"]["골드"]
        _팝업_버튼("포기하기(10골드)").dispatch("on_release")
        yield 0.3
        assert 상태["소지품"]["골드"] == 골드 + 10

    def _단계_공어_연속전투(self, 상태, 매니저, 전투):
        """공어 연속전투: 이긴 뒤 [연속전투] 팝업 -> [전투 시작]으로 공왕 크로쿠타 전투 -> 이기면 보상 두 번"""
        gf.던전_진입(상태, "dungeon_02A_D15_middleocean_shallow")
        gf.파티_최대치로_회복(상태)
        gf.전투_시작(상태, ["공어"], 레벨=8, 차수=2)
        support.반응_처리(상태)
        _아군_차례로(상태)
        매니저.current = "전투"
        전투.갱신(신규=True)
        yield 0.3
        원래 = rng.던전.random
        rng.던전.random = lambda: 0.0  # 연속전투 판정이 반드시 걸리게
        try:
            if 상태["전투상태"] is not None:
                support.강제_승리(상태)
                전투.갱신()
            yield 0.5
        finally:
            rng.던전.random = 원래
        글 = next(t for t in _팝업글() if "공왕 크로쿠타가 나타났다!" in t)
        assert 글.split("\n") == ["전투 승리!", "공왕 크로쿠타가 나타났다!"], 글
        assert not gf.전투_보상_대기중(상태)  # 보상은 두 전투가 끝난 뒤
        _찍기("battle_chain_popup")
        _팝업_버튼("전투 시작").dispatch("on_release")
        yield 0.8
        # 전투시작 반응·적 차례를 엔진이 돌리는 동안은 기다린다(반응 팝업은 쓰지 않는다)
        for _ in range(50):
            if not 전투._엔진중:
                break
            if "사용 안 함" in _팝업글():
                _팝업_버튼("사용 안 함").dispatch("on_release")
            yield 0.2
        assert not 전투._엔진중, _팝업글()
        이름들 = sorted(p["원본"]["몬스터명"] for p in gf.적_목록(상태))
        assert 이름들 == sorted(
            ["공왕 크로쿠타", "대공어", "대공어", "공어", "공어"]
        ), 이름들
        assert 매니저.current == "전투"
        _찍기("battle_chain_crocuta")
        if 상태["전투상태"] is not None:
            support.강제_승리(상태)
            전투.갱신()
        yield 0.5
        assert next(t for t in _팝업글() if t.startswith("전투 승리!"))
        for 차례 in (1, 2):  # 첫 전투 보상, 크로쿠타 전투 보상
            assert _팝업_버튼("확인").disabled, 차례
            assert not _팝업_버튼("전투 보상").disabled, 차례
            _팝업_버튼("전투 보상").dispatch("on_release")
            yield 0.5
            _팝업_버튼("포기하기(10골드)").dispatch("on_release")
            yield 0.3
        assert not gf.전투_보상_대기중(상태)
        assert not _팝업_버튼("확인").disabled and _팝업_버튼("전투 보상").disabled
        _확인_누르기()
        yield 0.5
        assert 매니저.current == "던전", 매니저.current
        # 크로쿠타를 이겨 업적 "공왕 크로쿠타 처치"가 열렸다 - 뒤의 도감·업적 단계는 골드 업적만 세므로 기록을 지운다
        assert "공왕 크로쿠타" in 상태["진행도"]["업적기록"]["승리처치"]
        del 상태["진행도"]["업적기록"]["승리처치"]
        # 다음 단계들은 로리엔에서, 다 회복한 파티로 시작한다
        gf.던전_진입(상태, "dungeon_01A_D01_Lorien")
        gf.파티_최대치로_회복(상태)
        결과["단계"].append(
            "공어 연속전투 팝업 -> 공왕 크로쿠타 전투 -> 보상 두 번(포기)"
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

        # 100라운드가 지나도 끝나지 않으면 자동전투가 패배로 끝낸다 -> 패배 팝업. [확인] -> 마을(패배 귀환)은
        # _단계_전투종료_보상의 패배 판이 보고, 여기서 귀환하면 뒤 단계의 상태가 바뀌어 팝업만 닫는다.
        # 이 판이 쓴 굴림은 되돌린다 - 뒤 단계(프렌드 실드의 결빙의 케라하 등)가 굴림 순서에 기대고 있다
        난수 = rng.상태()
        gf.전투_시작(상태, ["타우 아미"], 레벨=6, 차수=2)
        support.반응_처리(상태)
        for 적 in gf.적_목록(상태):
            적["현재HP"] = 999
        상태["전투상태"]["라운드"] = gf.자동전투_최대라운드 + 1
        매니저.current = "전투"
        아군_차례로_맞추기()
        전투.갱신(신규=True)
        yield 0.3
        버튼("자동전투").dispatch("on_release")
        for _ in range(50):
            if 상태["전투상태"] is None:
                break
            yield 0.2
        assert 상태["전투상태"] is None, "100라운드 넘은 자동전투가 끝나지 않았다"
        yield 0.3
        글 = next(t for t in _팝업글() if t.split("\n")[0] == "전투 패배!")
        assert 글.split("\n")[0] == "전투 패배!", 글
        assert not 전투.자동전투
        _찍기("battle_auto_round_limit")
        _팝업_닫기()
        rng.상태_복원(난수)
        결과["단계"].append("자동전투 100라운드 넘김(#670) -> 패배 팝업")

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
        # 아군 그림: 모든 직업이 같은 정수 도트 배율(보통 크기 그림이 칸에 맞는 크기의 2/3), 칸 바닥 가운데.
        # 칸을 넘는 넓은 그림은 이웃보다 먼저(뒤에) 그린다 - 자리는 그대로
        from kivy.uix.image import Image as 그림

        아군그림 = [
            w
            for w in 전투.아군그래픽행.walk(restrict=True)
            if isinstance(w, 그림) and not getattr(w, "감옥그림", None) and w.texture
        ]
        assert len(아군그림) >= 2, "아군 그림 부족"
        assert len({tuple(w.texture_size) for w in 아군그림}) >= 2, "크기가 같은 그림뿐"
        도트들 = set()
        for 이미지 in 아군그림:
            틀 = 이미지.parent
            tw, th = 이미지.texture_size
            도트 = gf.캐릭터_도트배율(틀.width, 틀.height, 2 / 3)
            assert abs(이미지.width - tw * 도트) < 1, (이미지.size, 틀.size)
            assert abs(이미지.height - th * 도트) < 1, (이미지.size, 틀.size)
            assert abs(이미지.y - 틀.y) < 1 and abs(이미지.center_x - 틀.center_x) < 1
            도트들.add(도트)
        assert len(도트들) == 1, 도트들
        박스들 = list(reversed(전투.아군그래픽행.children))  # 그리는 순서(뒤 -> 앞)
        assert [b.그림폭 for b in 박스들] == sorted(
            (b.그림폭 for b in 박스들), reverse=True
        )
        assert sorted(박스들, key=lambda b: b.x) == sorted(
            박스들, key=lambda b: b.칸번호
        )
        _찍기("battle_monster_size")
        결과["단계"].append(
            "몬스터 크기 배율(소 1/2, 중 3/4, 대 1) + 발바닥 맞춤 + 대형이 뒤, 아군 그림 같은 도트 배율(보통 그림 기준 2/3) 바닥 맞춤 + 넓은 그림이 뒤"
        )

    def _단계_익스펠러_석상(self, 상태, 매니저, 전투):
        """익스펠러는 석상(기사석상 그림)으로 등장하고, 석상이 풀리면 본래 그림으로 그린다"""
        gf.전투_시작(상태, ["헤븐 익스펠러"], 레벨=6, 차수=2)
        support.반응_처리(상태)
        _아군_차례로(상태)
        매니저.current = "전투"
        헤븐 = gf.적_목록(상태)[0]
        헤븐["상태이상"] = [s for s in 헤븐["상태이상"] if s["이름"] != "석상"]
        헤븐["상태이상"].append({"이름": "석상", "지속턴": None})
        전투.갱신(신규=True)
        yield 1.2  # 0.6이면 앞 단계 그림이 찍힌다(화면이 아직 다시 그려지기 전)
        assert 전투._적그림목록[0][1].endswith("asset_monster_knight_statue.webp")
        _찍기("battle_expeller_statue")
        헤븐["상태이상"] = [s for s in 헤븐["상태이상"] if s["이름"] != "석상"]
        전투.갱신()
        yield 1.2
        assert 전투._적그림목록[0][1].endswith("asset_monster_heaven_expeller.webp")
        _찍기("battle_expeller")
        결과["단계"].append("익스펠러 석상 -> 기사석상 그림, 풀리면 본래 그림")

    def _단계_챔피언_이름표(self, 상태, 매니저, 전투):
        """챔피언·보스 칭호 이름표 - 칭호가 첫 줄: "[저주받은 챔피언]"/"쿠로가루", "[보스]"/"고블린" """
        _팝업_닫기()
        gf.전투_시작(
            상태,
            [
                {
                    "이름": "쿠로가루",
                    "칭호": "챔피언",
                    "돌연변이": "저주받은",
                    "챔피언버프": ["경화", "불멸의", "가속-히트커버리"],
                },
                {"이름": "고블린", "칭호": "보스"},
            ],
            레벨=3,
            차수=1,
        )
        support.반응_처리(상태)
        매니저.current = "전투"
        전투.갱신(신규=True)
        yield 0.6
        이름표 = [
            w.text for w in 전투.적상태틀.walk(restrict=True) if hasattr(w, "text")
        ]
        for 줄 in ("[저주받은 챔피언]", "쿠로가루", "[보스]", "고블린"):
            assert 줄 in 이름표, 이름표  # 상태칸은 줄마다 라벨 하나
        assert not any("-쿠로가루" in t for t in 이름표), 이름표
        _찍기("battle_champion_names")
        결과["단계"].append(
            "챔피언·보스 칭호 이름표 -> 첫 줄 [저주받은 챔피언]/[보스], 둘째 줄 이름"
        )

    def _단계_챔피언_버프칸(self, 상태, 매니저, 전투):
        """챔피언 버프 나열 - 그림 칸 위쪽부터 한 줄에 하나씩 가운데 정렬, 큰 몬스터 그림 위에도 보이고
        (그림보다 나중에 그림), 칸 오른쪽 아래(상태 아이콘 자리)는 비어 있다. 챔피언이 아니면 글이 없다."""
        _팝업_닫기()
        버프 = ["경화", "불멸의", "가속-히트커버리", "공격시 출혈", "이뮨-화속성"]
        gf.전투_시작(
            상태,
            [
                {
                    "이름": "쿠로가루",
                    "칭호": "챔피언",
                    "돌연변이": "저주받은",
                    "챔피언버프": 버프,
                },
                {
                    "이름": "타우 비스트",
                    "칭호": "챔피언",
                    "돌연변이": "불타는",
                    "챔피언버프": ["강화-공격력", "흡혈"],
                },
                "고블린",
            ],
            레벨=6,
            차수=2,
        )
        support.반응_처리(상태)
        매니저.current = "전투"
        전투.갱신(신규=True)
        yield 0.6
        칸 = {적["원본"]["몬스터명"]: 전투._그림칸[적["id"]] for 적 in gf.적_목록(상태)}
        그린 = 전투._그린_칸글
        for 몬스터, 기대 in (
            ("쿠로가루", 버프),
            ("타우 비스트", ["강화-공격력", "흡혈"]),
            ("고블린", []),
        ):
            줄 = [(글, 자리) for c, 글, 자리 in 그린 if c is 칸[몬스터]]
            assert [글 for 글, _ in 줄] == 기대, (몬스터, 줄)
            박스 = 칸[몬스터]
            이전_y = 박스.top
            for 글, (x, y, w, h) in 줄:
                assert y + h <= 이전_y + 0.5, (몬스터, 글, "위에서 아래로가 아님")
                assert abs(x + w / 2 - 박스.center_x) < 1, (몬스터, 글, "가운데 아님")
                assert 박스.x <= x and x + w <= 박스.right, (몬스터, 글, "칸 밖")
                assert y >= 박스.center_y, (몬스터, 글, "칸 아래 절반 침범")
                이전_y = y
        # 글은 몬스터 그림(같은 층의 그림 사각형)보다 나중에 그려 위에 보인다
        from kivy.graphics import Rectangle

        사각형 = [
            c for c in 전투.적그래픽행.canvas.after.children if isinstance(c, Rectangle)
        ]
        assert len(사각형) == 3 + len(버프) + 2, len(사각형)
        _찍기("battle_champion_buffs")
        결과["단계"].append(
            "챔피언 버프 나열 -> 그림 칸 위쪽부터 가운데 정렬, 그림 위, 아래 절반 비움, 챔피언 아니면 없음"
        )
        yield from self._단계_상태아이콘(상태, 전투)

    def _단계_상태아이콘(self, 상태, 전투):
        """상태 아이콘 - 그림 칸 오른쪽 아래부터 위로 10개, 넘치면 왼쪽 줄, 원본 크기(19x19).
        아이콘 없는 상태(도발)는 그리지 않고, 챔피언 버프 글과 겹치지 않는다. 적은 그림 위층, 아군은
        캐릭터 그림 위층에 그린다. (앞 단계의 챔피언 전투를 그대로 쓴다)"""
        적 = {p["원본"]["몬스터명"]: p for p in gf.적_목록(상태)}
        쿠로 = 적["쿠로가루"]
        쿠로["상태이상"].append({"이름": "출혈", "지속턴": 3, "중첩": 2})
        쿠로["디버프"].append({"이름": "방어감소", "지속턴": 3})
        쿠로["버프"].append({"이름": "일반행동증가", "지속턴": 3})
        아군 = gf.아군_목록(상태)
        열둘 = [
            "출혈",
            "화상",
            "감전",
            "중독",
            "암흑",
            "기절",
            "석화",
            "빙결",
            "수면",
            "혼란",
            "구속",
            "둔화",
        ]
        아군[0]["상태이상"] += [{"이름": 이름, "지속턴": 3} for 이름 in 열둘]
        아군[1]["상태이상"] += [
            {"이름": "무적", "지속턴": 2},
            {"이름": "도발", "지속턴": 2},
        ]
        전투.갱신()
        yield 0.6
        칸 = {이름: 전투._그림칸[p["id"]] for 이름, p in 적.items()}

        def 아이콘(그린, 박스):
            return [(이름, 자리) for c, 이름, 자리 in 그린 if c is 박스]

        from game.screens.screens_battle import _아이콘_간격 as 간격
        from game.screens.screens_battle import _아이콘_한줄개 as 한줄개

        def 쌓임(박스, 줄):
            첫x, 첫y, w, h = 줄[0][1]
            assert (w, h) == (19, 19), ("원본 크기 아님", w, h)
            assert abs(첫x + w - 박스.right) < 12 and abs(첫y - 박스.y) < 12, (
                "오른쪽 아래가 아님",
                줄[0],
                박스.pos,
                박스.size,
            )
            for 번호, (이름, (x, y, _w, _h)) in enumerate(줄):
                줄번호, 단 = divmod(번호, 한줄개)
                assert abs(x - (첫x - 줄번호 * (w + 간격))) < 2, (이름, "열 어긋남")
                assert abs(y - (첫y + 단 * (h + 간격))) < 2, (이름, "위로 쌓이지 않음")

        쿠로칸 = 칸["쿠로가루"]
        쿠로줄 = 아이콘(전투._그린_적아이콘, 쿠로칸)
        assert [이름 for 이름, _ in 쿠로줄] == ["출혈", "가속", "방어감소"], 쿠로줄
        쌓임(쿠로칸, 쿠로줄)
        assert not 아이콘(전투._그린_적아이콘, 칸["고블린"])
        # 챔피언 버프 글과 겹치지 않는다
        for _, (x, y, w, h) in 쿠로줄:
            for c, 글, (gx, gy, gw, gh) in 전투._그린_칸글:
                if c is 쿠로칸:
                    겹침 = x < gx + gw and gx < x + w and y < gy + gh and gy < y + h
                    assert not 겹침, ("챔피언 버프 글과 겹침", 글)
        아군칸 = [전투._그림칸[a["id"]] for a in 아군[:2]]
        첫줄 = 아이콘(전투._그린_아군아이콘, 아군칸[0])
        assert [이름 for 이름, _ in 첫줄] == 열둘  # 10개 뒤 2개는 왼쪽 줄
        쌓임(아군칸[0], 첫줄)
        assert [이름 for 이름, _ in 아이콘(전투._그린_아군아이콘, 아군칸[1])] == [
            "무적"
        ]
        _찍기("battle_status_icons")
        결과["단계"].append(
            "상태 아이콘 -> 칸 오른쪽 아래부터 위로 10개 뒤 왼쪽 줄, 19x19, 아이콘 없는 상태 제외, 챔피언 글과 안 겹침"
        )
        yield from self._단계_효과목록(상태, 전투, 칸, 아군칸)

    def _단계_효과목록(self, 상태, 전투, 칸, 아군칸):
        """효과 목록 팝업 - 그림 칸(적·아군)이나 이름 칸을 실제로 누르면 걸린 것 전부(아이콘 없는
        도발 포함)가 남은 턴·중첩과 함께, 챔피언 버프는 따로 나열된다. 아군 이름 칸은 대상을 고르는 중이면
        열리지 않는다. (앞 단계의 상태를 그대로 쓴다)"""
        from kivy.tests.common import UnitTestTouch

        def 누르기(박스):
            손 = UnitTestTouch(*박스.to_window(*박스.center))
            손.touch_down()
            손.touch_up()

        def 열린_글(박스):
            누르기(박스)
            yield 0.3
            assert _팝업수() == 1, ("효과 목록이 안 열림", _팝업수())
            글 = 전투._효과목록팝업.글
            _뒤로키()
            yield 0.2
            assert _팝업수() == 0, "뒤로 키로 안 닫힘"
            return 글

        _팝업_닫기()
        yield 0.2
        전투.선택모드 = None
        누르기(칸["쿠로가루"])
        yield 0.3
        assert _팝업수() == 1, "적 그림 칸을 눌러도 효과 목록이 안 열림"
        글 = 전투._효과목록팝업.글
        for 줄 in (
            "[b][상태이상][/b]",
            "출혈 (3턴, 2중첩)",
            "방어감소 (3턴)",
            "일반행동증가 (3턴)",
            "[b][챔피언 버프][/b]",
        ):
            assert 줄 in 글.split("\n"), (줄, 글)
        _찍기("battle_status_list")
        _뒤로키()
        yield 0.2
        assert _팝업수() == 0
        # 적 이름 칸 - 고블린(아무것도 안 걸었으면 "없음")
        고블린 = next(p for p in gf.적_목록(상태) if p["원본"]["몬스터명"] == "고블린")
        이름칸 = list(reversed(전투.적상태틀.children))[
            gf.적_칸_목록(상태).index(고블린)
        ]
        글 = yield from 열린_글(이름칸)
        assert (글 == "적용 중인 효과 없음") == (not gf.상태_목록(상태, 고블린)), 글
        # 아군 그림 칸 - 아이콘 없는 도발도 나온다
        글 = yield from 열린_글(아군칸[1])
        assert {"무적 (2턴)", "도발 (2턴)"} <= set(글.split("\n")), 글
        # 아군 이름 칸 - 대상을 고르는 중이 아니면 열리고, 고르는 중이면 안 열린다
        아군이름칸 = list(reversed(전투.아군상태틀.children))[0]
        글 = yield from 열린_글(아군이름칸)
        assert "출혈 (3턴)" in 글.split("\n"), 글
        전투.선택모드 = ("일반공격",)
        누르기(아군이름칸)
        yield 0.3
        assert _팝업수() == 0, "대상 고르는 중에 효과 목록이 열림"
        전투.선택모드 = None
        결과["단계"].append(
            "효과 목록 -> 적·아군 그림 칸/이름 칸 누르면 걸린 것 전부(턴·중첩, 챔피언 버프), 대상 고르는 중엔 이름 칸 안 열림"
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
