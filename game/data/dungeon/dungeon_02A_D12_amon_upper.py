# =====================
# 아몬 상층 (소형지도)
# =====================
# dungeon_format.py 양식을 따른다.

맵정보 = {
    "지도명": "아몬 상층",
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
            "이름": "마스터 도그리",
            "설명": "마을로 가는 포탈을 지키는 보스. 이겨야 포탈로 갈 수 있다.",
            "발동방식": "말걸기",
            "전투몬스터": [
                {"이름": "마스터 도그리", "칭호": "보스"},
                {"이름": "진흙 인형사"},
                {"이름": "진흙 인형사"},
                {"이름": "돌 인형사"},
                {"이름": "강철 인형사"},
            ],
            "레벨": 6,
            "차수": 3,
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
            "연결맵": "dungeon_02A_D11_amon_lower",
            "진입좌표": (19, 2),
        },
    },
    "인카운트": {
        "출현그룹": [
            # 아몬 상층
            {
                "그룹확률": 1.0,
                "출현몬스터": {
                    "카겔": 0.1,
                    "봄 카겔": 0.1,
                    "진흙 골렘": 0.1,
                    "스톤 골렘": 0.1,
                    "진흙 인형사": 0.3,
                    "돌 인형사": 0.2,
                    "강철 인형사": 0.1,
                },
            },
        ],
        "출현마리수": (2, 4),
        "레벨": 6,
        "차수": 3,
        "인카운트확률": {
            "안전걸음": 5,
            "걸음당증가율": 0.1,
        },
    },
}
