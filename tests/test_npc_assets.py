"""엔피시 그림 - game/assets/npc/의 파일 이름 규칙과 장수를 지킨다.

규칙: asset_npc_<영문이름>_<두 자리 번호>.webp. 01번이 기본 그림이고 02번부터는 업적 등으로 얻는 그림이다.
게임(키비의 SDL2 그림 읽기)은 움직이는 웹피를 열지 못한다. 그래서 장면을 격자로 이어 붙인 무손실 정지 웹피로 넣고,
장면 크기와 장면별 시간은 game/data/npc/npc_illust_frames.py에 둔다(만드는 도구: tools/npc_sheet.py).
"""

import pathlib
import re

from game.data.npc.npc_illust_frames import 장면정보
from game.system import quest_system

_폴더 = pathlib.Path(__file__).resolve().parents[1] / "game" / "assets" / "npc"
_이름규칙 = re.compile(r"^asset_npc_([a-z]+)_(\d{2})\.webp$")

_장수 = {
    "seria": 13,  # 세리아
    "linus": 1,  # 라이너스
    "matilda": 1,  # 마틸다
    "kanna": 1,  # 칸나
    "kiri": 2,  # 키리
    "minet": 4,  # 미네트
    "sinda": 1,  # 신다
    "shylock": 1,  # 샤일록
    "michelle": 6,  # 미쉘 모나헌
    "shusia": 4,  # 슈시아
    "oran": 1,  # 오란 할머니
    "lorian": 2,  # 로리안
    "sharan": 3,  # 샤란
    "ophelia": 6,  # 오필리아 베이그란스
    "paris": 2,  # 패리스
    "mintai": 2,  # 민타이
    "becky": 1,  # 베키
}


def test_파일이름이_규칙을_따르고_번호가_01부터_빈틈없다():
    찾은 = {}
    for 파일 in _폴더.iterdir():
        맞음 = _이름규칙.match(파일.name)
        assert 맞음, 파일.name
        찾은.setdefault(맞음.group(1), []).append(int(맞음.group(2)))
    assert {이름: sorted(번호) for 이름, 번호 in 찾은.items()} == {
        이름: list(range(1, 장수 + 1)) for 이름, 장수 in _장수.items()
    }


def _웹피_크기(파일):
    """정지 웹피의 (가로, 세로) - CI에는 그림 라이브러리가 없어 머리를 직접 읽는다. 움직이는 웹피면 None."""
    내용 = 파일.read_bytes()
    assert 내용[:4] == b"RIFF" and 내용[8:12] == b"WEBP", 파일.name
    assert int.from_bytes(내용[4:8], "little") + 8 == len(내용), 파일.name
    if 내용[12:16] == b"VP8L":  # 무손실 단순 형식: 서명 0x2f 뒤 14비트씩 가로-1, 세로-1
        assert 내용[20] == 0x2F, 파일.name
        비트 = int.from_bytes(내용[21:25], "little")
        return (비트 & 0x3FFF) + 1, ((비트 >> 14) & 0x3FFF) + 1
    assert 내용[12:16] == b"VP8X", 파일.name
    if 내용[20] & 0x02 or b"ANMF" in 내용:
        return None
    return int.from_bytes(내용[24:27], "little") + 1, int.from_bytes(
        내용[27:30], "little"
    ) + 1


def test_모든_그림이_장면을_이어붙인_정지_웹피이고_장면정보와_맞다():
    파일들 = sorted(_폴더.glob("*.webp"))
    assert {파일.name for 파일 in 파일들} == set(장면정보)
    for 파일 in 파일들:
        정보 = 장면정보[파일.name]
        크기 = _웹피_크기(파일)
        assert 크기 is not None, f"{파일.name}: 움직이는 웹피는 게임이 열지 못한다"
        시간 = 정보["시간"]
        assert 시간 and all(isinstance(t, int) and t > 0 for t in 시간), 파일.name
        열 = quest_system.장면_열수(정보["가로"], len(시간))
        줄 = -(-len(시간) // 열)
        assert 크기 == (정보["가로"] * 열, 정보["세로"] * 줄), 파일.name
        assert max(크기) <= quest_system.장면그림_최대크기, 파일.name


def test_장면은_최대크기_안에서_줄을_바꿔_붙인다():
    assert quest_system.장면_열수(49, 62) == 41  # 2048 // 49
    assert (
        quest_system.장면_열수(89, 50) == 23
    )  # 한 줄이면 4450칸 - 휴대폰 그래픽 장치가 못 띄울 수 있다
    assert quest_system.장면_열수(56, 6) == 6  # 장수가 적으면 한 줄
