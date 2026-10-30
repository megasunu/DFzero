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
            "이름": "불숨의 샐리온",
            "설명": "아몬 상층으로 가는 포탈을 지키는 보스. 이겨야 포탈로 갈 수 있다.",
            "발동방식": "말걸기",
            "타일": "asset_tile_prison_lorien.webp",  # 감옥 - 로리안
            "타일크기": 2,  # 2x2칸 크기로 칸 중심에 맞춰 그린다
            "전투몬스터": [
                {"이름": "불숨의 샐리온", "칭호": "보스"},
                {"이름": "세리말리온"},
                {"이름": "세리말리온"},
                {"이름": "세리말리온"},
                {"이름": "루스 세리말리온"},
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
            "연결맵": "dungeon_02A_D12_amon_upper",
            "진입좌표": (19, 18),
        },
    },
    "인카운트": {
        "출현그룹": [
            # 헤븐익스펠러
            {
                "그룹확률": 1.0,
                "출현몬스터": {
                    "카겔": 0.2,
                    "진흙 골렘": 0.1,
                    "세리말리온": 0.2,
                    "루스 세리말리온": 0.1,
                    "스톤 골렘": 0.1,
                    "진흙 인형사": 0.1,
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
