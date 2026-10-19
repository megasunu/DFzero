# =====================
# 세피로타 상층 (소형지도)
# =====================
# dungeon_format.py 양식을 따른다.

맵정보 = {
    "지도명": "세피로타 상층",
    "상세지역": ["아라드", "벨마이어 공국 남부"],
    "지도": [
        "YYYYYYYYYYYYYYYYYYYYYYY",
        "YYYYYYYYYYYYYYYYYYYYYYY",
        "YYYYYYYYYYYYYYYYYYYYYYY",
        "YYYYYYYYYYYYYYYYYYYYYYY",
        "YYYYYYYYYYYYYYYYYYYYYYY",
        "YYYYYYYYYYYYYYYYYYYYYYY",
        "YYYYYYYYYYYYYYYYYYYYYYY",
        "YYYYYYYYYXXXXXYYYYYYYYY",
        "YYYYYYYXXXOOOXXXYYYYYYY",
        "YYYYYYXXOOOOOOOXXYYYYYY",
        "YYYYYXXOOOOOOOOOXXYYYYY",
        "YYYYXXOOOOOOOOOOOXXXYYY",
        "YYYXXOOOOOXXXOOOOOXXYYY",
        "YYXXOOOOXXXXXXXOOOOXXYY",
        "YXXOOOOXXXXXXXXXOOOOXXY",
        "YXOOOOXXXXXXXXXXXOOOOXY",
        "YXOOOOXXXXXXXXXXXOOOOXY",
        "YXOOOXXXXXXXXXXXXXOOOXY",
        "YXO@OXXXXXXXXXXXXXOOOXY",
        "YXX#XXXXXXXXXXXXXXX#XXY",
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
    "입장좌표": (19, 18),
    "오브젝트": {
        (3, 18): {
            "분류": "이벤트",
            "타입": "보스전투",
            "이름": "세피로타 상층 보스",  # 미정 - 몬스터를 정할 때 바꾼다
            "설명": "마을로 가는 포탈을 지키는 보스. 이겨야 포탈로 갈 수 있다.",
            "발동방식": "말걸기",
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
        (3, 19): {
            "연결맵": "town_02A_T03_westcoast",
            "진입좌표": None,  # 마을은 화면(선택지) 형태라 좌표 개념이 없음
        },
        (19, 19): {
            "연결맵": "dungeon_02A_D13_sephiroth_lower",
            "진입좌표": (19, 2),
        },
    },
}
