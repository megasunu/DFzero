"""데이터 무결성 - 데이터에 적힌 키와 특성이 게임 코드(엔진)에서 실제로 쓰이는지 검사한다.

test_data_integrity.py에서 갈라져 나왔다. 설명용 키·다른 키로 구현된 키·미구현 키는 목록에 이유와 함께 적는다."""

import ast
import collections
import importlib
import pathlib
import pkgutil
import game.data as 데이터패키지

루트 = pathlib.Path(__file__).resolve().parents[2]


def _데이터_모듈들():
    for 정보 in pkgutil.walk_packages(데이터패키지.__path__, "game.data."):
        yield importlib.import_module(정보.name)


# ---------------------------------------------------------------- 엔진이 읽지 않는 데이터 키
# 데이터 키는 게임 코드(game/system·controller·screens, gameflow.py)가 문자열로 읽거나 아래 셋 중 하나에 있다.
# 엔진은 모르는 키를 조용히 무시하므로, 새 키가 효과를 뜻하는데 읽히지 않으면 이 검사가 알린다.
# 이름 표(값이 모두 dict인 dict - 버프목록, 스킬 "패턴" 등의 키)와 맨 위의 값 표(값이 모두 스칼라인 dict -
# common_names 등)의 키는 이름이라 세지 않는다. 분류표는 댓글.

# 사람이 읽는 설명 - 지워도 동작이 같다
_설명용_키 = {
    "클래스": "job_level - 직업은 파일과 레지스트리(ctl_registry)로 정해진다",
    "상세지역": "던전 위치 설명 - 화면에 나오지 않는다",
    "등급": "방어구·장신구 세트 - 세트 효과는 구성품만 본다",
    "권장AC": "monster_format 차수별_AC기준 - 몬스터 AC 설계 기준표(머리말 주석)",
    "격차": "monster_format 차수별_AC기준 - 무기 기대피해 격차(설계 기록)",
    "발동조건_주체": "발동조건을 풀어 쓴 설명",
    "발동조건_상황": "발동조건을 풀어 쓴 설명",
    "발동조건_변수설명": "프리스트 스킬 발동조건 변수의 설명",
    "적명중결과": "발동조건_변수설명 안의 변수 설명",
    "집중유지": "상태이상 집중 - 걸려 있는 것 자체가 집중이다(해제는 해제조건)",
}

# 뜻은 구현됐는데 엔진은 다른 키나 고정 규칙으로 처리한다 - 지워도 동작이 같다(값을 바꾸면 무시된다)
_다른_키로_구현된_키 = {
    "발동방식": "던전 오브젝트 - 칸으로 걸어 들어가면 발동(dungeon_system 이동), 값은 '말걸기' 하나뿐",
    "습득퍽": "스킬 쪽 역참조 - 퍽의 '획득스킬'이 실제로 준다",
    "지속": "소환수 - 수명은 소환 버프의 지속턴",
    "능력치참조": "소환수 - 늘 시전자 능력치(monster_actions 소환수 행동)",
    "행동시점": "효도르 - 시전자 턴 종료에 행동(skill_run 소환수 행동)",
    "적용대상": "기술효과는 거는 스킬의 '타겟' - 호신연격(job_ability_020f) 것은 미구현(#575)",
    "범위공격피격": "은신 - '지정불가'는 단일 지정만 막는다(skill 타겟_확장)",
    "사용가능기술": "파생기 스킬의 '자원소모'(류심자세/원귀)가 사용을 막는다",
    "조건부보너스": "류심 파생기의 '조건부효과'(조건값 강화류심)",
    "보유클래스": "클래스자원 - '사용태그'(resources.클래스자원_채우기)",
    "사용스킬": "클래스자원 - '사용태그'",
    "공격단계2": "분할공격 - skill_attack.공격단계_키들이 '공격단계'+번호로 읽는다",
}

# 효과를 뜻하는데 엔진이 읽지 않는다 - 구현하면 여기서 뺀다(알려진 예외)
_미구현_키 = {
    "재굴림": "#575 이중극점·삼중극점 - 재굴림은 늘 d20(hit.극점_판정)",
    "종료시스택소모": '#575 호신연격스택 - 턴 끝 소모는 "버프종료":"턴종료"가 한다',
    "기존": "#158 무기주사위대체 안",
    "변경": "#158 무기주사위대체 안",
}

_게임_코드_경로 = ("game/system", "game/controller", "game/screens")


def _게임_코드_문자열():
    파일들 = [루트 / "gameflow.py"]
    for 경로 in _게임_코드_경로:
        파일들 += sorted((루트 / 경로).rglob("*.py"))
    return {
        마디.value
        for 파일 in 파일들
        for 마디 in ast.walk(ast.parse(파일.read_text(encoding="utf-8")))
        if isinstance(마디, ast.Constant) and isinstance(마디.value, str)
    }


def _데이터_키_모으기():
    """({키: {모듈이름}}, 이름들) - 이름 표와 맨 위 값 표의 키는 키로 세지 않고 이름으로 모은다.
    이름(몬스터·스킬·버프 ...)이 다른 표(던전 출현 확률 등)의 키로 쓰이면 그것도 이름이다."""
    키들 = collections.defaultdict(set)
    이름들 = set()

    def 걷기(값, 모듈):
        if isinstance(값, dict):
            이름표 = bool(값) and all(isinstance(v, dict) for v in 값.values())
            for k, v in 값.items():
                if isinstance(k, str):
                    (이름들 if 이름표 else 키들[k]).add(k if 이름표 else 모듈)
                if k == "이름" and isinstance(v, str):
                    이름들.add(v)
                걷기(v, 모듈)
        elif isinstance(값, (list, tuple)):
            for v in 값:
                걷기(v, 모듈)

    for 모듈 in _데이터_모듈들():
        for 이름, 값 in vars(모듈).items():
            if 이름.startswith("_") or not isinstance(값, (dict, list)):
                continue
            if isinstance(값, dict) and all(
                not isinstance(v, (dict, list)) for v in 값.values()
            ):
                이름들.update(값)  # 맨 위 값 표(속성_정식명 등) - 키가 이름이다
                continue
            걷기(값, 모듈.__name__)
    return 키들, 이름들


def test_데이터_키는_게임_코드가_읽거나_이유가_적힌_목록에_있다():
    """새 데이터 키를 엔진이 읽지 않으면 조용히 무시된다. 읽지 않는 키는 설명용/다른 키로 구현됨/미구현 중 하나로
    이유와 함께 둔다. 목록의 키를 코드가 읽게 되거나 데이터에서 사라지면 목록에서 뺀다."""
    목록들 = (_설명용_키, _다른_키로_구현된_키, _미구현_키)
    겹침 = [
        k for i, a in enumerate(목록들) for b in 목록들[i + 1 :] for k in a if k in b
    ]
    assert 겹침 == [], "한 키는 한 분류에만 둔다"
    읽음 = _게임_코드_문자열()
    키들, 이름들 = _데이터_키_모으기()
    안읽힘 = {
        k: sorted(m) for k, m in 키들.items() if k not in 읽음 and k not in 이름들
    }
    목록 = set(_설명용_키) | set(_다른_키로_구현된_키) | set(_미구현_키)
    새로_생김 = {k: m for k, m in 안읽힘.items() if k not in 목록}
    assert 새로_생김 == {}, (
        "게임 코드가 읽지 않는 데이터 키 - 구현하거나 이유와 함께 목록에 둔다"
    )
    assert 목록 - set(안읽힘) == set(), "이제 읽히거나 데이터에 없는 키는 목록에서 뺀다"


def _직업특성_전체():
    """game/data/ability/job_ability_*.py 의 특성목록 (모듈이름, 특성이름, 정의)."""
    import game.data.ability as 특성패키지

    for 정보 in pkgutil.iter_modules(특성패키지.__path__):
        if not 정보.name.startswith("job_ability_"):
            continue
        모듈 = importlib.import_module(f"game.data.ability.{정보.name}")
        for 이름, 정의 in getattr(모듈, "특성목록", {}).items():
            yield 정보.name, 이름, 정의


def test_상시_일반특성의_효과는_변동대상_목록이다():
    """발동조건이 없는 일반특성의 "효과"는 None이거나 {"변동대상", "변동값"} 원소의 목록이다.
    트리거형(발동조건이 있는 것)은 damage.py가 사전으로 읽으므로 대상이 아니다."""
    어긋남 = []
    for 모듈, 이름, 정의 in _직업특성_전체():
        if 정의.get("분류") != "일반특성" or 정의.get("발동조건") is not None:
            continue
        효과 = 정의.get("효과")
        if 효과 is None:
            continue
        if not isinstance(효과, list) or not all(
            isinstance(원소, dict) and "변동대상" in 원소 for 원소 in 효과
        ):
            어긋남.append(f"{모듈}.{이름}")
    assert 어긋남 == [], "변동대상 목록이 아닌 효과:\n" + "\n".join(어긋남)


def test_모든_직업특성에_타입이_있다():
    없음 = [
        f"{모듈}.{이름}"
        for 모듈, 이름, 정의 in _직업특성_전체()
        if not 정의.get("타입")
    ]
    assert 없음 == [], f"타입 없는 특성 {len(없음)}개:\n" + "\n".join(없음)
