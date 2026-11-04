"""NPC와 퀘스트 - 마을에서 대화할 수 있는 NPC, 퀘스트 수락/완료 판정(2026-11-04).

데이터는 game/data/npc/npc_<이름>.py(NPC마다 한 파일 - 대사, 퀘스트 내용, 양식은 npc_format.py). 규칙은 docs/game-rules.md "NPC / 퀘스트".
퀘스트 상태는 진행도["퀘스트"] = {퀘스트 ID: "진행중" | "완료"}에 남고(세이브 버전 17),
목록에 없는 퀘스트는 "수락전", 진행중인데 조건을 채웠으면 "완료가능"으로 본다.
"""

from game.data.npc.npc_linus import NPC정보 as _라이너스
from game.data.npc.npc_seria import NPC정보 as _세리아

# 새 NPC 파일을 만들면 여기에 import + 추가한다(순서 = [NPC] 화면 순서)
NPC_목록 = [_라이너스, _세리아]
퀘스트_목록 = [퀘스트 for NPC in NPC_목록 for 퀘스트 in NPC["퀘스트"]]

조건_타입 = ("던전클리어",)
모든마을 = "모든마을"


def 빈_진행기록():
    """새 게임 진행도에 더할 퀘스트 칸."""
    return {"퀘스트": {}}


def 조건만족(조건, 진행도):
    """대화조건/완료조건 판정. None이면 항상 참."""
    if 조건 is None:
        return True
    if 조건["타입"] == "던전클리어":
        return 조건["대상"] in 진행도.get("클리어한던전", set())
    return False


def NPC_찾기(이름):
    return next((n for n in NPC_목록 if n["이름"] == 이름), None)


def 퀘스트_찾기(ID):
    return next((q for q in 퀘스트_목록 if q["ID"] == ID), None)


def 대화가능(NPC, 마을명, 진행도):
    있는마을 = NPC["마을"] == 모든마을 or 마을명 in NPC["마을"]
    return 있는마을 and 조건만족(NPC["대화조건"], 진행도)


def 대화가능_NPC(마을명, 진행도):
    """그 마을에서 지금 대화할 수 있는 NPC들(목록 순서)."""
    return [n for n in NPC_목록 if 대화가능(n, 마을명, 진행도)]


def _기록(진행도):
    return 진행도.setdefault("퀘스트", {})


def 퀘스트_상태(진행도, ID):
    """ "수락전" | "진행중" | "완료가능" | "완료"."""
    상태 = _기록(진행도).get(ID)
    if 상태 is None:
        return "수락전"
    if 상태 == "진행중" and 조건만족(퀘스트_찾기(ID)["조건"], 진행도):
        return "완료가능"
    return 상태


def NPC_대사(NPC, 진행도):
    """퀘스트를 전부 끝냈으면 "완료후대화"(있을 때), 아니면 "대화"."""
    끝 = NPC["퀘스트"] and all(
        퀘스트_상태(진행도, q["ID"]) == "완료" for q in NPC["퀘스트"]
    )
    if 끝 and NPC.get("완료후대화"):
        return NPC["완료후대화"]
    return NPC["대화"]


def 퀘스트_수락(진행도, ID):
    if 퀘스트_찾기(ID) is None:
        raise ValueError(f"'{ID}' 퀘스트는 없다.")
    if 퀘스트_상태(진행도, ID) != "수락전":
        raise ValueError(f"'{ID}' 퀘스트는 이미 받았다.")
    _기록(진행도)[ID] = "진행중"


def 퀘스트_완료(진행도, ID):
    """완료가능한 퀘스트를 완료로 바꾸고 보상 딕셔너리를 돌려준다(주는 것은 부르는 쪽)."""
    if 퀘스트_찾기(ID) is None:
        raise ValueError(f"'{ID}' 퀘스트는 없다.")
    if 퀘스트_상태(진행도, ID) != "완료가능":
        raise ValueError(f"'{ID}' 퀘스트는 아직 완료할 수 없다.")
    _기록(진행도)[ID] = "완료"
    return dict(퀘스트_찾기(ID)["보상"])


def 보상_문구(보상):
    """{"골드": 10} -> "10G"."""
    return f"{보상.get('골드', 0)}G"
