"""움직이는 NPC 그림(움직이는 웹피·GIF)을 게임이 여는 장면 그림으로 바꾼다.

게임(키비의 SDL2 그림 읽기)은 움직이는 웹피를 열지 못한다. 그래서 장면을 격자로 이어 붙인 무손실 정지 웹피를
game/assets/npc/<원본 이름>.webp로 쓰고, 장면 크기와 장면별 시간(밀리초)을 game/data/npc/npc_illust_frames.py에 적는다.
한 줄에 붙이는 장면 수는 quest_system.장면_열수(화면이 같은 규칙으로 잘라 쓴다).

    python tools/npc_sheet.py <원본 그림> [...]     # 그림 라이브러리(필로)가 필요하다 - 게임과 테스트는 쓰지 않는다
    python -m ruff format game/data/npc/npc_illust_frames.py   # 그다음 서식을 맞춘다

원본 이름은 asset_npc_<영문이름>_<두 자리 번호>(tests/test_npc_assets.py가 이름 규칙과 장수를 지킨다).
"""

import pathlib
import sys

_루트 = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_루트))

from game.system import quest_system  # noqa: E402

_그림폴더 = _루트 / "game" / "assets" / "npc"
_데이터 = _루트 / "game" / "data" / "npc" / "npc_illust_frames.py"
_머리말 = '''"""NPC 일러스트의 장면 정보 - tools/npc_sheet.py가 만든다(손으로 고치지 않는다).

{그림 파일명: {"가로": 장면 가로, "세로": 장면 세로, "시간": [장면별 표시 시간(밀리초), ...]}}
그림은 장면을 격자로 이어 붙인 정지 웹피다(한 줄의 장면 수는 quest_system.장면_열수).
"""

'''


def 장면들_읽기(경로):
    """원본 움직이는 그림의 (장면 RGBA 그림들, 장면별 시간)."""
    from PIL import Image, ImageSequence

    원본 = Image.open(경로)
    장면들, 시간 = [], []
    for 장면 in ImageSequence.Iterator(원본):
        장면들.append(장면.convert("RGBA"))
        시간.append(int(장면.info.get("duration") or 100))
    return 장면들, 시간


def 장면그림_만들기(장면들):
    from PIL import Image

    가로, 세로 = 장면들[0].size
    열 = quest_system.장면_열수(가로, len(장면들))
    줄 = -(-len(장면들) // 열)
    그림 = Image.new("RGBA", (가로 * 열, 세로 * 줄), (0, 0, 0, 0))
    for 번호, 장면 in enumerate(장면들):
        그림.paste(장면, ((번호 % 열) * 가로, (번호 // 열) * 세로))
    return 그림


def 데이터_읽기():
    if not _데이터.exists():
        return {}
    공간 = {}
    exec(compile(_데이터.read_text(encoding="utf-8"), str(_데이터), "exec"), 공간)
    return dict(공간["장면정보"])


def 데이터_쓰기(장면정보):
    줄들 = [_머리말, "장면정보 = {\n"]
    for 이름 in sorted(장면정보):
        정보 = 장면정보[이름]
        줄들.append(
            f'    "{이름}": {{"가로": {정보["가로"]}, "세로": {정보["세로"]}, "시간": {정보["시간"]}}},\n'
        )
    줄들.append("}\n")
    _데이터.write_text("".join(줄들), encoding="utf-8", newline="\n")


def main(인자):
    if not 인자:
        print(__doc__)
        return 2
    장면정보 = 데이터_읽기()
    for 원본 in map(pathlib.Path, 인자):
        이름 = 원본.stem + ".webp"
        장면들, 시간 = 장면들_읽기(원본)
        if len(장면들) == 1 and 이름 in 장면정보:
            print(
                f"{원본.name}: 이미 장면 그림이다 - 원본 움직이는 그림을 넣는다",
                file=sys.stderr,
            )
            return 1
        장면그림_만들기(장면들).save(_그림폴더 / 이름, lossless=True, exact=True)
        장면정보[이름] = {
            "가로": 장면들[0].width,
            "세로": 장면들[0].height,
            "시간": 시간,
        }
        print(f"{이름}: {len(장면들)}장 {장면들[0].width}x{장면들[0].height}")
    데이터_쓰기(장면정보)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
