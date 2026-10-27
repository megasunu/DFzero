# 전투 시스템 - 수식 평가 - 데미지 문법/다이스/무기공격력.
# (combat 패키지에서 분리 - R4. 전체 설계 설명은 game/system/combat/__init__.py)

import ast
import functools
import math
import operator
import re

from game.system import dice_utils

# =====================================================
# 수식 평가
# =====================================================

_다이스_패턴 = re.compile(r"(\d+|\([^()]*\))d(\d+|\([^()]*\))")

# 계산식에 쓸 수 있는 글자: 숫자, + - * / ( ) . 공백, 올림 함수. 이 밖의 표현은 평가하지 않는다.
_허용_식 = re.compile(r"(?:[0-9+\-*/(). ]|_올림)+")

_이항연산 = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Pow: operator.pow,
}
_단항연산 = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_최대_지수 = 64  # 2**9999999 같은 식이 계산을 붙잡지 못하게


def _노드_평가(노드):
    """허용한 노드(숫자, 사칙/거듭제곱, 부호, _올림(...))만 계산한다. eval을 쓰지 않는다."""
    if isinstance(노드, ast.Expression):
        return _노드_평가(노드.body)
    if isinstance(노드, ast.Constant) and type(노드.value) in (int, float):
        return 노드.value
    if isinstance(노드, ast.BinOp) and type(노드.op) in _이항연산:
        왼, 오 = _노드_평가(노드.left), _노드_평가(노드.right)
        if isinstance(노드.op, ast.Pow) and abs(오) > _최대_지수:
            raise ValueError(f"지수가 너무 크다: {오}")
        return _이항연산[type(노드.op)](왼, 오)
    if isinstance(노드, ast.UnaryOp) and type(노드.op) in _단항연산:
        return _단항연산[type(노드.op)](_노드_평가(노드.operand))
    if (
        isinstance(노드, ast.Call)
        and isinstance(노드.func, ast.Name)
        and 노드.func.id == "_올림"
        and len(노드.args) == 1
        and not 노드.keywords
    ):
        return math.ceil(_노드_평가(노드.args[0]))
    raise ValueError(f"수식에 쓸 수 없는 표현: {ast.dump(노드)}")


def 올림(값):
    """소수점은 항상 올림한다(게임 전체 규칙, 2026-10-20 사용자 결정 #247). 정수는 그대로,
    부동소수 오차(0.1x3x10 = 3.0000000000000004)는 올리지 않는다. 능력치 보정치
    (능력치-10)//2는 D&D 보정치 표라 이 규칙 밖이다."""
    if isinstance(값, int):
        return 값
    return math.ceil(round(값, 9))


@functools.lru_cache(maxsize=4096)
def _계산(식):
    # eval처럼 앞뒤 공백은 무시한다. 순수 함수라(같은 문자열 -> 같은 값) 결과를 캐시한다.
    return _노드_평가(ast.parse(식.strip(), mode="eval"))


def 안전_평가(식):
    """숫자/사칙연산/괄호/올림만 든 계산식을 계산한다. 그 밖의 글자나 표현이 있으면 ValueError,
    문법이 틀리면 SyntaxError, 0으로 나누면 ZeroDivisionError. eval을 쓰지 않는다(구조 점검 W-2).
    수식_평가가 키워드/다이스를 숫자로 바꾼 뒤 마지막에 부르고, 장비 데이터의 숫자 수식도 쓴다."""
    if not _허용_식.fullmatch(식):
        raise ValueError(f"계산식에 쓸 수 없는 글자가 있다: {식!r}")
    return _계산(식)


def _다이스_치환(match, 치명타=False, 평균=False):
    개수식, 면수식 = match.group(1), match.group(2)
    개수 = 올림(안전_평가(개수식))
    면수 = 올림(안전_평가(면수식))
    if 개수 <= 0 or 면수 <= 0:  # 0개 항은 치명타여도 0 (귀신 0개인 귀참의 d8 등)
        return "0"
    개수 += int(치명타)  # True=1개, 정수면 그만큼(치명타주사위)
    if 평균:  # 굴리지 않고 기대값(NdM = N x (M+1)/2)
        return str(개수 * (면수 + 1) / 2)
    return str(dice_utils.주사위_합(개수, 면수))


def _무기_주사위항(무기공격력_수식):
    """무기공격력 수식을 [(개수, 면수)]로 - "1d6" 하나 또는 "1d12+1d6"처럼 "+"로 이은 여럿(광창 브류나크 #437)."""
    항들 = []
    for 항 in 무기공격력_수식.split("+"):
        match = re.fullmatch(r"(\d+)d(\d+)", 항.strip())
        if not match:
            raise ValueError(f"알 수 없는 무기공격력 표기: {무기공격력_수식!r}")
        항들.append((int(match.group(1)), int(match.group(2))))
    return 항들


def 무기공격력_평균(무기공격력_수식):
    """무기공격력 수식(예: "1d6")의 기대값 - 굴리지 않는다(전력전투의 기대 피해 비교)."""
    return sum(개수 * (면수 + 1) / 2 for 개수, 면수 in _무기_주사위항(무기공격력_수식))


def 무기공격력_굴림(무기공격력_수식, 치명타=False):
    """무기공격력 수식(예: "1d6")을 굴린다. 치명타면 주사위 개수를
    1개 추가한다(표준 D&D처럼 2배가 아님) - 보정치/데미지보너스는
    그대로 1회분. 치명타가 정수면 그 개수만큼 추가한다(stats.피해_굴림).
    주사위 항이 여럿이면("1d12+1d6") 치명타 주사위는 첫 항에만 붙는다."""
    return sum(
        dice_utils.주사위_합(개수 + (int(치명타) if 순번 == 0 else 0), 면수)
        for 순번, (개수, 면수) in enumerate(_무기_주사위항(무기공격력_수식))
    )


def 평타_보정치(컨텍스트):
    """컨텍스트의 "보정치" - stats.기본_컨텍스트는 쓸 때 계산하는 함수로, 다른 곳은 숫자로 넣는다."""
    값 = 컨텍스트.get("보정치", 0)
    return 값() if callable(값) else 값


def _무기공격력값(컨텍스트, 치명타, 평균):
    """수식의 "무기공격력" 값 - 무기 주사위(치명타면 주사위가 는다)에 무기 공격에 더 들어가는 평타
    보정치("무기보정치추가" - 귀혼일체/검귀의 도 마스터리 #330)를 더한다. "치명타보정치대체"(청혈투귀)면
    치명타 때 무기 주사위 대신 치명타 주사위마다 보정치를 더한다(stats.무기_보정치_효과)."""
    무기식 = 컨텍스트.get("무기공격력", "1d1")
    if 평균:
        값 = 무기공격력_평균(무기식)
    elif 컨텍스트.get("치명타보정치대체"):
        값 = 무기공격력_굴림(무기식) + int(치명타) * 평타_보정치(컨텍스트)
    else:
        값 = 무기공격력_굴림(무기식, 치명타=치명타)
    추가 = 컨텍스트.get("무기보정치추가", 0)
    return 값 + (추가 * 평타_보정치(컨텍스트) if 추가 else 0)


def _무기_치환(식, 컨텍스트, 치명타, 평균):
    """식의 "보정공격력"(무기공격력 + 평타 보정치)과 "무기공격력"을 한 번 굴린 값으로 바꾼다."""
    무기공격력값 = _무기공격력값(컨텍스트, 치명타, 평균)
    if "보정공격력" in 식:
        식 = 식.replace("보정공격력", str(무기공격력값 + 평타_보정치(컨텍스트)))
    return 식.replace("무기공격력", str(무기공격력값))


def 수식_평가(수식, 컨텍스트, 치명타=False, 평균=False):
    """job_skill_format.py <데미지 문법> / buff.py 수식 표기를 계산해서
    숫자로 만든다. 컨텍스트에는 필요한 값만 넣으면 된다: "차수",
    "추가공격", "보정치", "주문시전보정치", "무기공격력"(예: "1d6"),
    "능력치"({"근력": 12, ...} - "민첩보정치" 등 특정 능력치 보정치
    키워드를 쓸 때 여기서 계산해 꺼낸다).

    다이스 표기는 매번 새로 굴린다 - 같은 수식을 두 번 평가하면 결과가
    달라진다. 치명타면 다이스 개수를 늘려 굴린다(True=1개, 정수=그 개수 -
    stats.치명타_주사위수. 표준 D&D의 "다이스 2배"가 아니라 "다이스 추가").
    무기 주사위(무기공격력/보정공격력)가 있는 수식은 무기 주사위만 늘고 나머지
    "NdM"은 그대로다(귀참의 귀신 d8 등). 무기 주사위가 없는 수식(주문 등)은
    "NdM" 항마다 는다. 개수 0인 항은 치명타여도 0. 차수/보정치 등 고정 값은
    그대로 1회분만 반영된다. 평균=True면 주사위를 굴리지 않고 기대값을 넣는다(무작위 수를 안 쓴다)."""
    if isinstance(수식, (int, float)):
        return 수식

    식 = 수식

    # "2차수"처럼 숫자와 키워드가 붙어 있으면 곱셈으로 해석한다
    # (status_effects.py "1d(2+2차수)" 참고) - 문자열 치환만 하면
    # "22"처럼 이어 붙는 것을 막기 위함. "추가공격"은 항상 덧셈으로만
    # 붙으므로 이 대상에는 넣지 않는다.
    for 키워드 in (
        "스타일성장횟수",
        "주문시전보정치",
        "근력보정치",
        "민첩보정치",
        "건강보정치",
        "지능보정치",
        "지혜보정치",
        "매력보정치",
        "보정치",
        "차수",
        "레벨",
    ):
        식 = re.sub(rf"(\d)({키워드})", r"\1*\2", 식)

    # 긴 키워드부터 치환해야 "보정치"가 "주문시전보정치"/"근력보정치" 등
    # 안에서 먼저 걸리는 일이 없다.
    if "스타일성장횟수" in 식:
        식 = 식.replace("스타일성장횟수", str(컨텍스트.get("스타일성장횟수", 0)))

    # 개수 변수 - 없으면 0개(귀참의 귀신 d8, 일발화약성의 대상 상태이상 d8 #398)
    for 키워드 in ("귀신보유수", "대상상태이상수"):
        식 = 식.replace(키워드, str(컨텍스트.get(키워드, 0)))

    if "주문시전보정치" in 식:
        식 = 식.replace("주문시전보정치", str(컨텍스트.get("주문시전보정치", 0)))

    능력치딕셔너리 = 컨텍스트.get("능력치", {})
    for 능력치이름 in ("근력", "민첩", "건강", "지능", "지혜", "매력"):
        키워드 = f"{능력치이름}보정치"
        if 키워드 in 식:
            보정치표 = 컨텍스트.get("능력치보정치") or {}
            if (
                능력치이름 in 보정치표
            ):  # 약점증가의 1당 1 등 - stats.기본_컨텍스트가 넣는다
                식 = 식.replace(키워드, str(보정치표[능력치이름]))
                continue
            원값 = 능력치딕셔너리.get(능력치이름, 10)
            if not isinstance(원값, (int, float)):
                원값 = 10
            식 = 식.replace(키워드, str((원값 - 10) // 2))

    if "보정치" in 식:
        식 = 식.replace("보정치", str(평타_보정치(컨텍스트)))
    if "보정공격력" in 식 or "무기공격력" in 식:
        식 = _무기_치환(식, 컨텍스트, 치명타, 평균)
    if "추가공격" in 식:
        식 = 식.replace("추가공격", str(컨텍스트.get("추가공격", 0)))
    if "차수" in 식:
        식 = 식.replace("차수", str(컨텍스트.get("차수", 1)))
    if "레벨" in 식:
        식 = 식.replace("레벨", str(컨텍스트.get("레벨", 1)))

    # 무기 주사위가 있으면 치명타 주사위는 무기 주사위에만(위에서 이미 반영)
    항_치명타 = 0 if ("보정공격력" in 수식 or "무기공격력" in 수식) else 치명타
    식 = _다이스_패턴.sub(lambda match: _다이스_치환(match, 항_치명타, 평균), 식)
    # "×"(몬스터 최대HP/AC 수식 등)와 "÷"도 각각 곱셈/나눗셈 기호로 취급한다.
    식 = 식.replace("x", "*").replace("X", "*").replace("×", "*").replace("÷", "/")

    # "올림(...)"(몬스터 최대HP 공식) - 괄호 안을 계산해 올린다.
    식 = 식.replace("올림", "_올림")
    if not _허용_식.fullmatch(식):
        raise ValueError(
            f"수식_평가가 처리할 수 없는 표현이 남았다: {수식!r} -> {식!r} "
            f"(예: 전투 중 상태를 참조하는 동적 변수는 아직 미지원)"
        )

    return _계산(식)
