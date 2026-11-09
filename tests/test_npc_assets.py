"""엔피시 그림 - game/assets/npc/의 파일 이름 규칙과 장수를 지킨다.

규칙: asset_npc_<영문이름>_<두 자리 번호>.webp. 01번이 기본 그림이고 02번부터는 업적 등으로 얻는 그림이다.
원본은 움직이는 그림이라 프레임을 모두 담은 무손실 웹피로 넣었다.
"""

import pathlib
import re

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


def test_모든_그림이_움직이는_웹피다():
    # CI에는 그림 라이브러리가 없어 웹피 머리를 직접 읽는다: RIFF/WEBP, VP8X(캔버스 크기·움직임 표시), 프레임(ANMF).
    for 파일 in sorted(_폴더.glob("*.webp")):
        내용 = 파일.read_bytes()
        assert 내용[:4] == b"RIFF" and 내용[8:12] == b"WEBP", 파일.name
        assert int.from_bytes(내용[4:8], "little") + 8 == len(내용), 파일.name
        assert 내용[12:16] == b"VP8X", 파일.name
        assert 내용[20] & 0x02, 파일.name  # 움직임 표시
        너비 = int.from_bytes(내용[24:27], "little") + 1
        높이 = int.from_bytes(내용[27:30], "little") + 1
        assert 0 < 너비 < 400 and 0 < 높이 < 400, 파일.name
        assert b"ANMF" in 내용, 파일.name
