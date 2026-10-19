# =====================
# 아몬 하층 (소형지도)
# =====================
# dungeon_format.py 양식을 따른다.

맵정보 = {
    "지도명": "아몬 하층",
    "상세지역": ["아라드", "벨마이어 공국 남부"],
    "지도": [
        "YXX#XXXXXXXXXXXXXXX#XXY",
        "YXOOOXXXXXXXXXXXXXO@OXY",
        "YXOOOXXXXXXXXXXXXXOOOXY",
        "YXOOOOXXXXXXXXXXXOOOOXY",
        "YXOOOOXXXXXXXXXXXOOOOXY",
        "YXXOOOOXXXXXXXXXOOOOXXY",
        "YXXXOOOOXXXXXXXOOOOXXXY",
        "YXXXXOOOOOXXXOOOOOXXXXY",
        "YXXXXXOOOOOOOOOOOXXXXXY",
        "YXXXXXXOOOOOOOOOXXXXXXY",
        "YXXXXXXXOOOOOOOXXXXXXXY",
        "YXXXXXXXXXOOOXXXXXXXXXY",
        "YXXXXXXXXXXXXXXXXXXXXXY",
        "YXXXXXXXXXXXXXXXXXXXXXY",
        "YXXXXXXXXXXXXXXXXXXXXXY",
        "YXXXXXXXXXXXXXXXXXXXXXY",
        "YXXXXXXXXXXXXXXXXXXXXXY",
        "YXXXXXXXXXXXXXXXXXXXXXY",
        "YXXXXXXXXXXXXXXXXXXXXXY",
        "YXXXXXXXXXXXXXXXXXXXXXY",
    ],
    "타일": {
        "O": "asset_tile_emerald.webp",
        "X": "asset_tile_skycastlewall.webp",
        "Y": "asset_tile_skyyellow.webp",
        "#": [
            "asset_tile_skycastlewall.webp",
            "asset_tile_gate_skycastle.webp",
        ],
    },
    "입장좌표": (3, 1),
    "오브젝트": {
        (19, 1): {
            "분류": "이벤트",
            "타입": "보스전투",
            "이름": "아몬 하층 보스",  # 미정 - 몬스터를 정할 때 바꾼다
            "설명": "아몬 상층으로 가는 포탈을 지키는 보스. 이겨야 포탈로 갈 수 있다.",
            "발동방식": "말걸기",
            "타일": "asset_tile_prison_lorien.webp",  # 감옥 - 로리안
            "타일크기": 2,  # 2x2칸 크기로 칸 중심에 맞춰 그린다
            "전투몬스터": [],  # 미정 - 몬스터를 정할 때 채운다(레벨/차수도)
            "클리어시": "통행가능화",
        },
    },
    # 이 던전에서 쓰러뜨린 몬스터마다 굴리는 공용 드랍(몬스터 개인 드랍과 별개) - 하늘성
    "드랍표": [
        {"이름": "커먼장비군", "발동확률": 0.3},
        {"이름": "언커먼장비군", "발동확률": 0.3},
    ],
    "연결지역": {
        (3, 0): {
            "연결맵": "town_02A_T03_westcoast",
            "진입좌표": None,  # 마을은 화면(선택지) 형태라 좌표 개념이 없음
        },
        (19, 0): {
            "연결맵": "dungeon_02A_D12_amon_upper",
            "진입좌표": (19, 18),
        },
    },
}
