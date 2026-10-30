# =====================
# 세피로타 하층 (소형지도)
# =====================
# dungeon_format.py 양식을 따른다.

맵정보 = {
    "지도명": "세피로타 하층",
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
            "이름": "헤븐 익스펠러",
            "설명": "세피로타 상층으로 가는 포탈을 지키는 보스. 이겨야 포탈로 갈 수 있다.",
            "발동방식": "말걸기",
            "전투몬스터": [
                {"이름": "헤븐 익스펠러", "칭호": "보스"},
                {"이름": "엑스 익스펠러"},
                {"이름": "익스펠러"},
                {"이름": "익스펠러"},
                {"이름": "카겔"},
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
        (3, 0): {
            "연결맵": "town_02A_T03_westcoast",
            "진입좌표": None,  # 마을은 화면(선택지) 형태라 좌표 개념이 없음
        },
        (19, 0): {
            "연결맵": "dungeon_02A_D14_sephiroth_upper",
            "진입좌표": (19, 18),
        },
    },
    "인카운트": {
        "출현그룹": [
            # 세리말리온군
            {
                "그룹확률": 0.3,
                "출현몬스터": {
                    "세리말리온": 0.6,
                    "루스 세리말리온": 0.3,
                    "카겔": 0.1,
                },
            },
            # 골렘군
            {
                "그룹확률": 0.2,
                "출현몬스터": {
                    "진흙 골렘": 0.3,
                    "스톤 골렘": 0.2,
                    "청동 골렘": 0.1,
                    "봄 카겔": 0.1,
                },
            },
            # 익스펠러군
            {
                "그룹확률": 0.5,
                "출현몬스터": {
                    "익스펠러": 0.6,
                    "엑스 익스펠러": 0.3,
                    "카겔": 0.2,
                    "봄 카겔": 0.1,
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
