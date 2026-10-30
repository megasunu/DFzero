"""몬스터 전수 특성 테스트 - 29종 몬스터의 서로 다른 패턴을 하나씩 강제로 실행한다.

패턴마다 새 전투(시드 고정)를 열고, 그 몬스터의 턴에 monster_ai.행동_선택이 그
패턴을 고르게 한 뒤 몬스터_턴_실행 -> 1라운드 더 진행한다(버프 지속, 소환수 행동,
지속피해, 아군의 반응스킬). 칭호("보스") 유무에 따른 시작 능력치도 고정한다.
결과는 종족 파일별 골든.
"""

import json

import pytest

from game.system import rng
import gameflow as gf
from game.system.combat import flow, monster_actions, stats, traits
from game.system import monster_ai
from tests import support
from tests.test_combat_skills import 정리, 참가자_요약

파티 = [("", "귀검사"), ("", "격투가"), ("", "거너"), ("", "프리스트")]
전직 = {
    "귀검사": "웨펀마스터",
    "격투가": "스트라이커",
    "거너": "레인저",
    "프리스트": "크루세이더",
}
종족파일 = dict(gf._몬스터파일목록)


def _고유_패턴(몬스터):
    """내용이 같은 패턴(몽둥이질 1~5 등)은 한 번만. 조건부행동은 두 갈래를 각각 돈다."""
    본것, 결과 = set(), []
    펼친것 = []
    for 키, 패턴 in sorted((몬스터.get("패턴") or {}).items()):
        if 패턴.get("이름") == "조건부행동":
            펼친것 += [
                (키, 패턴[갈래])
                for 갈래 in ("조건미충족시", "조건충족시")
                if isinstance(패턴.get(갈래), dict)
            ]
        else:
            펼친것.append((키, 패턴))
    for 키, 패턴 in 펼친것:
        지문 = json.dumps(패턴, ensure_ascii=False, sort_keys=True, default=str)
        if 지문 not in 본것:
            본것.add(지문)
            결과.append((키, 패턴))
    return 결과


def _전투(이름, 시드, 칭호=None):
    rng.시드(시드)
    상태 = support.새게임(파티)
    for c in 상태["파티"]["파티원"]:
        support.성장(상태, c, 10, 전직=전직[c["직업"]], 스킬습득=True)
    gf.파티_최대치로_회복(상태)
    gf.전투_시작(상태, [{"이름": 이름, "칭호": 칭호}, "고블린"], 레벨=6, 차수=2)
    support.반응_처리(상태)
    return 상태


def _적(전투상태, 대형위치):
    """참가자 목록은 이니셔티브 순이라, 대형위치(몬스터원본목록 순서)로 찾는다."""
    return next(
        p for p in 전투상태["참가자"] if p["진영"] == "적" and p["대형위치"] == 대형위치
    )


def 패턴_시나리오(monkeypatch, 이름, 패턴키, 패턴):
    상태 = _전투(이름, 시드=21)
    전투상태 = 상태["전투상태"]
    몬스터, 동료 = _적(전투상태, 0), _적(전투상태, 1)
    # 회복/버프 패턴이 할 일이 있게 적 둘을 다치게 한다
    몬스터["현재HP"] = max(1, 몬스터["현재HP"] // 2)
    동료["현재HP"] = max(1, 동료["현재HP"] // 3)
    # 반피 아래라 인형사가 패턴 대신 골렘 소환 캐스팅을 하지 않게(소환은 test_golem_summon.py가 본다)
    몬스터["소환사용"] = 동료["소환사용"] = True
    # 석상(익스펠러)은 패턴 대신 쉬므로 풀린 상태로 본다(석상은 test_expeller.py가 본다)
    for p in (몬스터, 동료):
        p["상태이상"] = [s for s in p["상태이상"] if s["이름"] != "석상"]
    전 = [참가자_요약(p) for p in 전투상태["참가자"]]

    원래 = monster_ai.행동_선택
    monkeypatch.setattr(
        monster_ai, "행동_선택", lambda p: 패턴 if p is 몬스터 else 원래(p)
    )
    기록 = {"시작로그": 정리(전투상태["로그"])}
    전투상태["현재턴"] = 전투상태["참가자"].index(몬스터)
    flow.턴_시작_처리(전투상태, 몬스터)
    로그시작 = len(전투상태["로그"])
    try:
        monster_actions.몬스터_턴_실행(전투상태, 몬스터)
    except Exception as e:  # noqa: BLE001
        기록["예외"] = f"{type(e).__name__}: {e}"
    기록["로그"] = 정리(전투상태["로그"][로그시작:])
    직후 = [참가자_요약(p) for p in 전투상태["참가자"]]
    기록["직후"] = support.참가자_변화(전, 직후)
    로그시작 = len(전투상태["로그"])
    for _ in range(len(전투상태["참가자"])):
        if gf.전투_종료됨(상태):
            break
        gf.턴_넘기기(상태)
    기록 |= support.뒤_라운드_기록(
        기록["직후"],
        직후,
        [참가자_요약(p) for p in 전투상태["참가자"]],
        정리(전투상태["로그"][로그시작:]),
    )
    monkeypatch.setattr(monster_ai, "행동_선택", 원래)
    return 기록, 전


def 칭호_비교(이름):
    결과 = {}
    for 칭호 in (None, "보스"):
        상태 = _전투(이름, 시드=5, 칭호=칭호)
        전투상태 = 상태["전투상태"]
        m = _적(전투상태, 0)
        결과[str(칭호)] = {
            "HP": m["현재HP"],
            "최대HP": stats.유효_최대HP(전투상태, m),
            "AC": stats.최종AC(전투상태, m),
            "방어력": stats.유효_방어력(전투상태, m),
            "보호률": stats.유효_보호률(전투상태, m),
            "이니셔티브": m["이니셔티브"],
            "우선도": m["우선도"],
            "데미지보너스": monster_actions.몬스터_데미지보너스(전투상태, m),
            "칭호_데미지배율": traits.칭호_배율(전투상태, m, "데미지"),
            "시작로그": 정리(전투상태["로그"]),
        }
    # 보스는 칭호 없는 쪽과 다른 칸만 싣는다
    결과["보스"] = support.수치_변화(결과["None"], 결과["보스"])
    return 결과


@pytest.mark.parametrize("종족", list(종족파일))
def test_몬스터_패턴_전수(monkeypatch, 종족, golden):
    결과 = {}
    for 이름 in 종족파일[종족]:
        시작, 패턴들 = None, {}
        for 키, 패턴 in _고유_패턴(gf.몬스터목록[이름]):
            패턴들[f"{키}:{패턴.get('이름')}"], 전 = 패턴_시나리오(
                monkeypatch, 이름, 키, 패턴
            )
            # 패턴을 쓰기 전 전장은 패턴마다 같다 - 한 번만 싣고, 패턴마다는 바뀐 것만 싣는다
            시작 = 시작 or 전
            assert 전 == 시작, 키
        결과[이름] = {"칭호": 칭호_비교(이름), "시작": 시작, "패턴": 패턴들}
    golden(f"combat_monsters_{종족}", 결과)


def test_몬스터는_63종():
    # 시험용 거대 누골 포함(2026-10-21), 인형사 4종(2026-10-28), 골렘 7종·익스펠러 3종·용인족 3종(2026-10-29),
    # 하늘성 7종(틴소드맨·레기온·악시온·불스아이·야시경 카겔·이블아이 두 눈, 2026-10-30 #483),
    # 얼음인형 샤레도·빛의 성주 지그하르트(2026-10-30 #487), 공어·대공어(미들오션 배치로 등록, 2026-10-30)
    assert len(gf.몬스터목록) == 63
    assert sum(len(v) for v in 종족파일.values()) == 63
