# =====================
# 미들오션 심해 (소형지도)
# =====================
# dungeon_format.py 양식을 따른다.

맵정보 = {
    "지도명": "미들오션 심해",
    "상세지역": ["아라드", "벨마이어 공국 남부"],
    "지도": [
        "XXXXXXXXXXXXXXXXX",
        "XOOOXOXXXXXOOOOOX",
        "XOXOOOXXXXXXXOOOX",
        "#OOOOOOOOOOOOOOOX",
        "XOOOOXXXXXXOOOOOX",
        "XOXXOOXXXXXXOXOXX",
        "XXXXXXXXXXXXXXXXX",
    ],
    "입장좌표": (1, 3),
    "오브젝트": {},
    # 이 던전에서 쓰러뜨린 몬스터마다 굴리는 공용 드랍(몬스터 개인 드랍과 별개) - 하늘성
    "드랍표": [
        {"이름": "커먼장비군", "발동확률": 0.3},
        {"이름": "언커먼장비군", "발동확률": 0.3},
    ],
    "연결지역": {
        (0, 3): {
            "연결맵": "dungeon_02A_D15_middleocean_shallow",
            "진입좌표": (15, 3),
        },
    },
}
