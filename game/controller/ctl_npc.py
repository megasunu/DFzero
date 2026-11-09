# 컨트롤러 - 마을 [NPC]: 대화할 수 있는 NPC, 대화, 퀘스트 수락/보고
# (화면은 gameflow.py 창구만 부른다. 규칙은 docs/game-rules.md "NPC / 퀘스트")

from game.system import quest_system

__all__ = [
    "마을_NPC_목록",
    "NPC_대화",
    "NPC_말걸기",
    "퀘스트_수락",
    "퀘스트_완료_보고",
]


def 마을_NPC_목록(게임상태):
    """지금 마을에서 대화할 수 있는 NPC 이름들(화면 순서)."""
    진행도 = 게임상태["진행도"]
    return [n["이름"] for n in quest_system.대화가능_NPC(진행도["현재마을"], 진행도)]


def NPC_대화(게임상태, 이름):
    """NPC 메뉴/퀘스트 팝업용 - 대사는 없다(대사는 NPC_말걸기). {"이름", "메뉴", "일러스트", "상점판매목록", "퀘스트": [{"ID", "이름", "설명", "상태", "보상"}]}.
    메뉴는 NPC 메뉴 팝업의 버튼들("대화"/"퀘스트"/"상점"), 일러스트는 game/assets/npc/ 파일명("미정"이면 그림 없음),
    일러스트장면은 그 그림의 장면 정보(quest_system.일러스트_장면, 없으면 None).
    지금 마을에서 대화할 수 없는 NPC면 ValueError."""
    진행도 = 게임상태["진행도"]
    NPC = quest_system.NPC_찾기(이름)
    if NPC is None or not quest_system.대화가능(NPC, 진행도["현재마을"], 진행도):
        raise ValueError(f"'{이름}'와(과) 지금은 대화할 수 없다.")
    퀘스트들 = []
    for 퀘스트 in NPC["퀘스트"]:
        퀘스트들.append(
            {
                "ID": 퀘스트["ID"],
                "이름": 퀘스트["이름"],
                "설명": 퀘스트["설명"],
                "상태": quest_system.퀘스트_상태(진행도, 퀘스트["ID"]),
                "보상": quest_system.보상_문구(퀘스트["보상"]),
            }
        )
    return {
        "이름": 이름,
        "메뉴": quest_system.NPC_메뉴(NPC),
        "일러스트": NPC["일러스트"],
        "일러스트장면": quest_system.일러스트_장면(NPC["일러스트"]),
        "상점판매목록": list(NPC.get("상점판매목록") or []),
        "퀘스트": 퀘스트들,
    }


def NPC_말걸기(게임상태, 이름):
    """[대화] - {"이름", "대사", "일러스트", "일러스트장면"}. 첫 대화면 그 NPC의 첫 대화를 마쳤다고 남긴다.
    지금 마을에서 대화할 수 없는 NPC면 ValueError."""
    진행도 = 게임상태["진행도"]
    NPC = quest_system.NPC_찾기(이름)
    if NPC is None or not quest_system.대화가능(NPC, 진행도["현재마을"], 진행도):
        raise ValueError(f"'{이름}'와(과) 지금은 대화할 수 없다.")
    return {
        "이름": 이름,
        "대사": quest_system.말걸기(NPC, 진행도),
        "일러스트": NPC["일러스트"],
        "일러스트장면": quest_system.일러스트_장면(NPC["일러스트"]),
    }


def 퀘스트_수락(게임상태, ID):
    quest_system.퀘스트_수락(게임상태["진행도"], ID)


def 퀘스트_완료_보고(게임상태, ID):
    """완료가능한 퀘스트를 보고하고 보상을 소지품에 넣는다. 받은 보상을 돌려준다."""
    보상 = quest_system.퀘스트_완료(게임상태["진행도"], ID)
    게임상태["소지품"]["골드"] += 보상.get("골드", 0)
    return 보상
