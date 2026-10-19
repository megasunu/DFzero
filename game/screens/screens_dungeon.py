# =====================
# 던전 화면 - 던전 지도 위젯, 던전 목록, 던전
# =====================
# main.py가 game/screens/ 여섯 파일의 화면을 ScreenManager에 등록한다.

import math
import zlib

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Rectangle, Ellipse, ScissorPush, ScissorPop

import gameflow
from game.screens.screens_common import (
    게임메뉴_열기,
    닫기_버튼,
    스크롤_목록,
    _캐릭터이미지_경로,
    _에셋_경로,
    뒤로키_버튼,
    파티칸줄,
    파티원_정사각형_채우기,
    상단_높이,
    하단_높이,
    정사각형_크기,
    상단_그림_높이,
    하단_첫줄_높이,
    하단_나머지_높이,
    하단_좌우여백,
)


# =====================================================
# 던전 맵 그리드를 그리는 위젯 (칸마다 타일 이미지 또는 색칠한 사각형 +
# 현재 위치를 표시하는 초상화 또는 원)
# =====================================================

_칸_색 = {
    "X": (0.2, 0.2, 0.2, 1),
    "Y": (0.53, 0.75, 0.95, 1),  # 하늘(이동불가) - 전용 타일 그림은 아직 없다
    "O": (0.78, 0.9, 0.79, 1),
    "@": (1, 0.72, 0.3, 1),
    "#": (0.56, 0.79, 0.98, 1),
}
_기본_칸_색 = (0.4, 0.4, 0.4, 1)

# 던전 지도 위젯의 짧은 쪽에 보여줄 칸 수. 칸은 항상 정사각형이라 긴 쪽에는
# 그만큼 칸이 더 보인다(끝 칸은 잘려 보일 수 있다). 플레이어가 항상 위젯
# 정중앙 칸에 오도록 그린다(아래 던전맵위젯._다시그리기 참고).
_뷰포트_크기 = 9
# 뷰포트가 실제 맵 범위를 벗어난 칸(지도 밖)을 칠하는 색 - "X"(벽)와
# 구분되게 더 어둡게 뒀다.
_맵밖_색 = (0, 0, 0, 1)

# 던전 지도 타일 이미지 (game/assets/dungeon/).
# 풀밭/흙길/게이트는 8x8 한 칸, 나무는 8x16 세로 2칸 - 아래 절반이 그
# 칸에 서고, 위 절반은 바로 윗칸에 겹쳐 그린다. 파일이 없으면 그 칸만
# _칸_색으로 칠한다.
_타일_파일 = {
    "풀밭": "asset_tile_grass.webp",
    "흙길": "asset_tile_dirt.webp",
    "나무": "asset_tile_tree.webp",
    "게이트": "asset_tile_gate_grandflores.webp",
}
# 풀밭 위에 그림을 올리는 지도 기호 ("X"=나무, "#"=게이트)
_올림타일_기호 = {"X": "나무", "#": "게이트"}
# 그중 세로 2칸짜리 타일을 쓰는 기호 (나무)
_높은타일_기호 = {"X": "나무"}
# 출입구(연결지역) 기호 - 나무/큰 오브젝트를 다 그린 뒤에 다시 그려서 가려지지 않는다
_출입구_기호 = "#"
# 흙길 배치 - 좌표 기준으로 항상 같은 자리에 오도록 해시값 노이즈를
# 쓴다(무작위 아님). 덩어리 크기(칸)와 문턱값(클수록 흙길이 적어짐).
_흙길_덩어리크기 = 3
_흙길_문턱값 = 0.66


def _좌표해시(x, y, 시드):
    """(x, y, 시드)마다 항상 같은 0~1 사이 값을 돌려준다(파이썬 내장
    hash()는 실행할 때마다 값이 바뀌어서 쓰지 않는다)."""
    값 = (x * 374761393 + y * 668265263 + 시드 * 2246822519) & 0xFFFFFFFF
    값 = ((값 ^ (값 >> 13)) * 1274126177) & 0xFFFFFFFF
    return (값 ^ (값 >> 16)) / 0xFFFFFFFF


def _흙길_여부(x, y, 시드):
    """ "O" 칸에 흙길을 깔지 정한다. 굵은 격자의 해시값을 부드럽게
    이어서(값 노이즈) 흙길이 낱개로 흩어지지 않고 듬성듬성 덩어리지게
    하고, 칸마다 약간의 흔들림을 더해 경계를 자연스럽게 만든다."""
    크기 = _흙길_덩어리크기
    gx, gy = x / 크기, y / 크기
    x0, y0 = math.floor(gx), math.floor(gy)
    fx, fy = gx - x0, gy - y0
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    위 = _좌표해시(x0, y0, 시드) * (1 - fx) + _좌표해시(x0 + 1, y0, 시드) * fx
    아래 = _좌표해시(x0, y0 + 1, 시드) * (1 - fx) + _좌표해시(x0 + 1, y0 + 1, 시드) * fx
    값 = 위 * (1 - fy) + 아래 * fy
    값 += (_좌표해시(x, y, 시드 + 1) - 0.5) * 0.3
    return 값 > _흙길_문턱값


def _비율맞춤(텍스처, x, y, 폭, 높이):
    """텍스처 비율을 지켜 (x, y, 폭, 높이) 안에 꽉 맞춘 바닥 가운데 자리 - Rectangle 인자."""
    tw, th = 텍스처.size
    배율 = min(폭 / tw, 높이 / th)
    w, h = tw * 배율, th * 배율
    return {"pos": (x + (폭 - w) / 2, y), "size": (w, h)}


class 던전맵위젯(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.그리드 = None
        self.위치 = None
        self.초상화코드 = None
        self._텍스처_캐시 = {}
        self._타일_캐시 = {}
        self._흙길시드 = 0
        self.오브젝트 = {}
        self.맵타일 = {}
        self._열수 = self._행수 = _뷰포트_크기
        self._층들 = []  # 갱신()이 채운다 - [지금 맵, 이어진 맵...]
        self.bind(size=self._다시그리기, pos=self._다시그리기)

    def 갱신(
        self,
        그리드,
        위치,
        초상화코드=None,
        던전파일명=None,
        오브젝트=None,
        맵타일=None,
        이웃=None,
    ):
        self.그리드 = 그리드
        self.위치 = 위치
        self.초상화코드 = 초상화코드
        # 던전마다 흙길 무늬가 달라지도록 파일명으로 시드를 정한다.
        self._흙길시드 = zlib.crc32((던전파일명 or "").encode("utf-8")) & 0xFFFF
        # 맵정보["오브젝트"] - "@" 칸에 전용 "타일"이 있는지 찾는 데 쓴다.
        self.오브젝트 = 오브젝트 or {}
        # 맵정보["타일"] - 이 맵에서 기호마다 쓸 한 칸짜리 타일(dungeon_format.py).
        self.맵타일 = 맵타일 or {}
        # 포탈로 이어진 다른 던전들(gameflow.이어진_맵_목록) - 지금 맵 밖 칸에 함께
        # 그린다. 지금 맵이 가장 우선이고, 그다음 목록 앞쪽(가까운 맵)이 우선.
        self._층들 = [
            {
                "지도": 그리드,
                "타일": self.맵타일,
                "시드": self._흙길시드,
                "오프셋": (0, 0),
            }
        ] + [
            {
                "지도": 이웃맵["지도"],
                "타일": 이웃맵["타일"],
                "시드": zlib.crc32(이웃맵["던전파일명"].encode("utf-8")) & 0xFFFF,
                "오프셋": 이웃맵["오프셋"],
            }
            for 이웃맵 in (이웃 or [])
        ]
        self._다시그리기()

    def _타일(self, 이름):
        """공용 타일(_타일_파일의 이름)의 텍스처를 돌려준다."""
        return self._파일_타일(_타일_파일[이름])

    def _파일_타일(self, 파일명, 폴더="dungeon"):
        """game/assets/<폴더>/(기본 dungeon)의 타일 텍스처를 한 번만 읽어 캐시한다.
        도트를 크게 늘려도 번지지 않게 확대/축소 필터를 nearest로 둔다.
        파일이 없으면 None."""
        키 = (폴더, 파일명)
        if 키 not in self._타일_캐시:
            텍스처 = None
            경로 = _에셋_경로(폴더, 파일명)
            if 경로:
                try:
                    텍스처 = CoreImage(경로).texture
                    텍스처.mag_filter = "nearest"
                    텍스처.min_filter = "nearest"
                except Exception:  # kivy는 못 읽는 그림에 Exception 자체를 던진다
                    텍스처 = None
            self._타일_캐시[키] = 텍스처
        return self._타일_캐시[키]

    def _맵_타일(self, 문자, 층=None):
        """그 맵(층 - 기본은 지금 맵)의 "타일"에 문자(지도 기호)가 지정돼 있으면 그
        텍스처들을 아래층부터 리스트로(파일명 하나면 한 겹, 리스트면 여러 겹), 없거나
        파일이 하나도 없으면 None을 돌려준다."""
        파일들 = (층["타일"] if 층 is not None else self.맵타일).get(문자)
        if not 파일들:
            return None
        if isinstance(파일들, str):
            파일들 = [파일들]
        텍스처들 = [t for t in (self._파일_타일(f) for f in 파일들) if t is not None]
        return 텍스처들 or None

    def _오브젝트_타일(self, 맵x, 맵y):
        """(맵x, 맵y) 오브젝트에 "타일"이 지정돼 있으면 그 텍스처를,
        없거나 파일이 없으면 None을 돌려준다. 한 번 클리어한 감옥 보스전처럼
        "보스그림"(gameflow.던전_오브젝트_표시)이 있으면 그 몬스터 그림이 먼저다."""
        정보 = self.오브젝트.get((맵x, 맵y))
        if not 정보:
            return None
        if 정보.get("보스그림"):
            그림 = self._파일_타일(정보["보스그림"], 폴더="monster")
            if 그림 is not None:
                return 그림
        if not 정보.get("타일"):
            return None
        return self._파일_타일(정보["타일"])

    def _보스그림인가(self, 맵x, 맵y):
        정보 = self.오브젝트.get((맵x, 맵y)) or {}
        return bool(정보.get("보스그림"))

    def _오브젝트_타일크기(self, 맵x, 맵y):
        """오브젝트 "타일크기"(칸 수, 기본 1). 2 이상이면 그 칸 중심에 맞춰
        크게 그린다(_큰오브젝트_그리기). 감옥 대신 보스 그림을 그릴 때는 1칸 -
        2x2는 감옥 그림의 크기다."""
        정보 = self.오브젝트.get((맵x, 맵y)) or {}
        if 정보.get("보스그림"):
            return 1
        return 정보.get("타일크기", 1)

    def _높은타일_반쪽(self, 이름):
        """세로 2칸 타일을 (아래 절반, 위 절반) 텍스처로 나눠 돌려준다.
        Kivy 텍스처는 왼쪽 아래가 원점이라 y=0 쪽이 아래 절반이다."""
        텍스처 = self._타일(이름)
        if 텍스처 is None:
            return None, None
        폭, 높이 = 텍스처.size
        반 = 높이 // 2
        return 텍스처.get_region(0, 0, 폭, 반), 텍스처.get_region(0, 반, 폭, 반)

    def _플레이어_텍스처(self):
        """선택된 모험단 프로필 이미지의 텍스처를 돌려준다. 아직 실제
        webp 파일이 없거나(개발 중), 코드가 없으면 None을 돌려주고,
        _다시그리기는 그 경우 원(Ellipse)으로 대신 그린다."""
        코드 = self.초상화코드
        if 코드 is None:
            return None
        if 코드 not in self._텍스처_캐시:
            try:
                self._텍스처_캐시[코드] = CoreImage(_캐릭터이미지_경로(코드)).texture
            except Exception:  # kivy는 못 읽는 그림에 Exception 자체를 던진다
                self._텍스처_캐시[코드] = None
        return self._텍스처_캐시[코드]

    def _칸(self, x, y):
        """(x, y)(지금 맵 좌표)의 (문자, 그 칸을 가진 층). 지금 맵이 먼저, 그 밖이면
        이어진 맵들을 앞에서부터 본다. 어느 맵에도 없으면 (None, None)(맵 밖)."""
        for 층 in self._층들:
            지도 = 층["지도"]
            lx, ly = x - 층["오프셋"][0], y - 층["오프셋"][1]
            if 0 <= ly < len(지도) and 0 <= lx < len(지도[ly]):
                return 지도[ly][lx], 층
        return None, None

    def _칸_문자(self, x, y):
        """(x, y)의 지도 문자. 지금 맵과 이어진 맵 모두 밖이면 None(맵 밖)."""
        return self._칸(x, y)[0]

    def _다시그리기(self, *args):
        self.canvas.clear()
        if (
            self.그리드 is None
            or self.위치 is None
            or self.width <= 0
            or self.height <= 0
        ):
            return

        # 맵 전체를 위젯 크기에 맞춰 축소하는 대신, 플레이어를 중심으로
        # 정사각형 칸을 짧은 쪽 _뷰포트_크기 칸만큼의 크기로 그린다 - 맵이
        # 커져도 칸 크기는 그대로고, 플레이어가 움직이면 그 칸 창이
        # 함께 움직이는 방식(카메라가 플레이어를 따라간다). 긴 쪽 끝의
        # 잘린 칸이 위젯 밖으로 나가지 않게 위젯 범위로 자른다.
        self._열수, self._행수 = self._칸_수()
        창x, 창y = self.to_window(self.x, self.y)
        with self.canvas:
            ScissorPush(
                x=int(창x), y=int(창y), width=int(self.width), height=int(self.height)
            )
            self._바닥_그리기()
            self._높은타일_그리기()
            self._큰오브젝트_그리기()
            self._출입구_그리기()
            self._플레이어_그리기()
            ScissorPop()

    def _칸_크기(self):
        """칸은 정사각형 - 위젯의 짧은 쪽에 _뷰포트_크기 칸이 들어가는 크기."""
        칸 = min(self.width, self.height) / _뷰포트_크기
        return (칸, 칸)

    def _칸_수(self):
        """(열 수, 행 수) - 가운데 칸(플레이어)을 빼고 양쪽에 같은 수만큼, 위젯을
        다 덮도록(끝 칸은 일부만 보일 수 있다). 항상 홀수."""
        칸, _ = self._칸_크기()
        return tuple(
            2 * math.ceil((길이 / 2 - 칸 / 2) / 칸 - 1e-9) + 1
            for 길이 in (self.width, self.height)
        )

    def _칸위치(self, 화면x, 화면y):
        # 지도 데이터는 y=0이 맨 윗줄이지만, Kivy 좌표는
        # 왼쪽 아래가 원점이라 아래에서부터 그려 올라간다.
        # 가운데 칸(열수//2, 행수//2)이 위젯 정중앙에 온다.
        칸, _ = self._칸_크기()
        return (
            self.center_x + (화면x - self._열수 // 2 - 0.5) * 칸,
            self.center_y + (self._행수 // 2 - 화면y - 0.5) * 칸,
        )

    def _맵_좌표(self, 화면x, 화면y):
        return (
            self.위치[0] - self._열수 // 2 + 화면x,
            self.위치[1] - self._행수 // 2 + 화면y,
        )

    def _바닥_텍스처(self, 문자, 맵x, 맵y, 층=None):
        """칸의 바닥 텍스처 리스트(아래층부터). "O"는 풀밭(좌표에 따라 흙길), "X"/"#"은 그 위에
        나무/게이트를 올릴 풀밭. 그 밖이나 그림이 없으면 None(색으로 칠한다).
        맵에 그 기호의 타일이 정해져 있으면 그 타일이 먼저다(나무/게이트도 안 올린다)."""
        맵타일 = self._맵_타일(문자, 층)
        if 맵타일 is not None:
            return 맵타일
        시드 = 층["시드"] if 층 is not None else self._흙길시드
        풀밭 = self._타일("풀밭")
        흙길 = self._타일("흙길")
        바닥 = None
        if 문자 == "O":
            바닥 = 흙길 if (흙길 is not None and _흙길_여부(맵x, 맵y, 시드)) else 풀밭
        elif 문자 in _올림타일_기호 and self._타일(_올림타일_기호[문자]) is not None:
            바닥 = 풀밭
        return [바닥] if 바닥 is not None else None

    def _바닥_그리기(self):
        """1단계 - 바닥. 오브젝트에 "타일"이 있으면 발판(맵의 "O" 타일, 없으면 풀밭) 위에
        그 타일, 없으면 기존 색 그대로, 지도 밖은 검정. "타일크기" 2 이상인 오브젝트는
        여기서 발판만 깔고 그림은 _큰오브젝트_그리기가 그린다."""
        칸크기 = self._칸_크기()
        발판 = self._맵_타일("O") or (
            [self._타일("풀밭")] if self._타일("풀밭") is not None else None
        )
        for 화면y in range(self._행수):
            for 화면x in range(self._열수):
                맵x, 맵y = self._맵_좌표(화면x, 화면y)
                문자, 층 = self._칸(맵x, 맵y)
                바닥 = self._바닥_텍스처(문자, 맵x, 맵y, 층)
                오브젝트타일 = self._오브젝트_타일(맵x, 맵y) if 문자 == "@" else None
                if 오브젝트타일 is not None and 발판 is not None:
                    바닥 = 발판
                if 오브젝트타일 is not None and self._오브젝트_타일크기(맵x, 맵y) > 1:
                    오브젝트타일 = None  # 큰 그림은 3단계에서
                위치 = self._칸위치(화면x, 화면y)
                if 바닥 is None:
                    Color(
                        *(_맵밖_색 if 문자 is None else _칸_색.get(문자, _기본_칸_색))
                    )
                    Rectangle(pos=위치, size=칸크기)
                    continue
                Color(1, 1, 1, 1)
                for 겹 in 바닥:
                    Rectangle(texture=겹, pos=위치, size=칸크기)
                if 오브젝트타일 is not None:
                    if self._보스그림인가(맵x, 맵y):
                        Rectangle(
                            texture=오브젝트타일,
                            **_비율맞춤(오브젝트타일, *위치, *칸크기),
                        )
                    else:
                        Rectangle(texture=오브젝트타일, pos=위치, size=칸크기)

    def _높은타일_그리기(self):
        """2단계 - 나무(세로 2칸). 윗줄부터 차례로 그려서 아래쪽
        나무의 위 절반이 윗칸 위에 겹치게 한다. 뷰포트 바로 아래 줄에
        서 있는 것도 위 절반만은 맨 아랫줄에 보이므로 한 줄 더 돈다."""
        칸크기 = self._칸_크기()
        Color(1, 1, 1, 1)
        for 화면y in range(self._행수 + 1):
            for 화면x in range(self._열수):
                문자, 층 = self._칸(*self._맵_좌표(화면x, 화면y))
                if 문자 not in _높은타일_기호 or self._맵_타일(문자, 층) is not None:
                    continue
                아래절반, 위절반 = self._높은타일_반쪽(_높은타일_기호[문자])
                if 아래절반 is None:
                    continue
                if 화면y < self._행수:
                    Rectangle(
                        texture=아래절반, pos=self._칸위치(화면x, 화면y), size=칸크기
                    )
                if 화면y >= 1:
                    Rectangle(
                        texture=위절반, pos=self._칸위치(화면x, 화면y - 1), size=칸크기
                    )

    def _큰오브젝트_그리기(self):
        """3단계 - "타일크기" 2 이상인 오브젝트(감옥 등). 그 칸 중심에 맞춰 크기 x 크기 칸으로
        그린다 - 바닥/나무보다 위, 플레이어보다 아래. 뷰포트 바로 밖의 오브젝트도 삐져나온
        부분이 보이도록 한 칸 더 돌고, 위젯 밖으로 나간 부분은 잘라 낸다."""
        칸폭, 칸높이 = self._칸_크기()
        Color(1, 1, 1, 1)
        for 화면y in range(-1, self._행수 + 1):
            for 화면x in range(-1, self._열수 + 1):
                맵x, 맵y = self._맵_좌표(화면x, 화면y)
                if self._칸_문자(맵x, 맵y) != "@":
                    continue
                크기 = self._오브젝트_타일크기(맵x, 맵y)
                텍스처 = self._오브젝트_타일(맵x, 맵y)
                if 크기 <= 1 or 텍스처 is None:
                    continue
                x, y = self._칸위치(화면x, 화면y)
                중심x, 중심y = x + 칸폭 / 2, y + 칸높이 / 2
                영역 = (
                    중심x - 칸폭 * 크기 / 2,
                    중심y - 칸높이 * 크기 / 2,
                    칸폭 * 크기,
                    칸높이 * 크기,
                )
                if self._보스그림인가(맵x, 맵y):
                    # 몬스터 그림은 정사각형이 아니라 비율을 지켜 영역 바닥 가운데에
                    맞춤 = _비율맞춤(텍스처, *영역)
                    영역 = (*맞춤["pos"], *맞춤["size"])
                self._잘라_그리기(텍스처, *영역)

    def _출입구_그리기(self):
        """4단계 - 출입구("#"). 바닥(맵 타일 또는 풀밭)과 게이트를 한 칸에 다시 그린다 -
        아래 나무의 위 절반이나 큰 오브젝트보다 위, 플레이어보다 아래. 맵 타일이 있으면
        그 겹들이 곧 게이트다(예: 하늘성 벽 위 게이트). 그림이 없으면 1단계의 색 그대로."""
        칸크기 = self._칸_크기()
        게이트 = self._타일(_올림타일_기호[_출입구_기호])
        Color(1, 1, 1, 1)
        for 화면y in range(self._행수):
            for 화면x in range(self._열수):
                맵x, 맵y = self._맵_좌표(화면x, 화면y)
                문자, 층 = self._칸(맵x, 맵y)
                if 문자 != _출입구_기호:
                    continue
                겹들 = self._바닥_텍스처(문자, 맵x, 맵y, 층)
                if 겹들 is None:
                    continue
                if self._맵_타일(문자, 층) is None:
                    겹들 = [*겹들, 게이트]
                위치 = self._칸위치(화면x, 화면y)
                for 겹 in 겹들:
                    Rectangle(texture=겹, pos=위치, size=칸크기)

    def _잘라_그리기(self, 텍스처, x, y, 폭, 높이):
        """(x, y, 폭, 높이)에 텍스처를 그리되 위젯 범위 밖은 잘라 낸다(텍스처도 같은 비율로)."""
        x0, y0 = max(x, self.x), max(y, self.y)
        x1, y1 = min(x + 폭, self.right), min(y + 높이, self.top)
        if x1 <= x0 or y1 <= y0:
            return
        tw, th = 텍스처.size
        조각 = 텍스처.get_region(
            int((x0 - x) / 폭 * tw),
            int((y0 - y) / 높이 * th),
            max(1, int((x1 - x0) / 폭 * tw)),
            max(1, int((y1 - y0) / 높이 * th)),
        )
        Rectangle(texture=조각, pos=(x0, y0), size=(x1 - x0, y1 - y0))

    def _플레이어_그리기(self):
        """플레이어는 항상 위젯 정중앙 칸(열수//2, 행수//2)에 그린다. 모험단 프로필 이미지가
        있으면 그 이미지를, 없으면(파일이 아직 없거나 코드 미설정) 빨간 원을 그린다."""
        칸폭, 칸높이 = self._칸_크기()
        여백폭 = 칸폭 * 0.2
        여백높이 = 칸높이 * 0.2
        x, y = self._칸위치(self._열수 // 2, self._행수 // 2)
        플레이어위치 = (x + 여백폭, y + 여백높이)
        플레이어크기 = (칸폭 - 여백폭 * 2, 칸높이 - 여백높이 * 2)
        텍스처 = self._플레이어_텍스처()
        if 텍스처 is not None:
            Color(1, 1, 1, 1)
            Rectangle(texture=텍스처, pos=플레이어위치, size=플레이어크기)
        else:
            Color(1, 0.15, 0.15, 1)
            Ellipse(pos=플레이어위치, size=플레이어크기)


# =====================================================
# 4-1. 던전 목록 화면 (마을 -> 던전 사이에 들어가는 선택 화면)
# =====================================================


class 던전목록화면(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        루트 = BoxLayout(orientation="vertical", padding=16, spacing=10)
        루트.add_widget(Label(text="던전 이동", font_size="24sp", size_hint=(1, 0.12)))

        self.목록틀 = BoxLayout(orientation="vertical", size_hint=(1, 0.68), spacing=8)
        루트.add_widget(self.목록틀)

        self.안내라벨 = Label(text="", size_hint=(1, 0.1))
        루트.add_widget(self.안내라벨)

        뒤로버튼 = Button(text="뒤로", size_hint=(1, 0.1))
        뒤로키_버튼(뒤로버튼)
        뒤로버튼.bind(on_release=lambda *_: setattr(self.manager, "current", "마을"))
        루트.add_widget(뒤로버튼)

        self.add_widget(루트)

    def on_pre_enter(self, *args):
        self.갱신()

    def 갱신(self):
        self.목록틀.clear_widgets()
        앱 = App.get_running_app()
        던전목록 = gameflow.이동가능던전목록(앱.게임상태)

        if not 던전목록:
            self.안내라벨.text = "이 마을에서 갈 수 있는 던전이 없습니다."
            return
        self.안내라벨.text = ""

        # 바로 앞 던전 보스를 아직 안 깬 던전은 보이되 누를 수 없다(gameflow.던전_열림)
        for 파일명, 표시이름, 열림 in gameflow.던전목록_표시(앱.게임상태):
            버튼 = Button(
                text=표시이름, size_hint=(1, None), height=dp(56), disabled=not 열림
            )
            버튼.bind(on_release=lambda inst, f=파일명: self._선택(f))
            self.목록틀.add_widget(버튼)

    def _선택(self, 파일명):
        앱 = App.get_running_app()
        gameflow.던전_진입(앱.게임상태, 파일명)
        self.manager.get_screen("던전").갱신()
        self.manager.current = "던전"


# =====================================================
# 5. 던전 이동 화면
# =====================================================


class 던전화면(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._대기중오브젝트 = None

        # 상단(1170): 1줄 파티원 정사각형, 2~4줄 지도(1080x970)
        # 하단(1170): 1줄 위치·걸음수, 2~4줄 방향 버튼/메시지 - screens_common "화면 배치"
        루트 = BoxLayout(orientation="vertical")
        상단 = BoxLayout(orientation="vertical", size_hint=(1, None), height=상단_높이)
        self.파티줄 = 파티칸줄(size_hint=(1, None), height=정사각형_크기)
        상단.add_widget(self.파티줄)
        self.지도위젯 = 던전맵위젯(size_hint=(1, None), height=상단_그림_높이)
        상단.add_widget(self.지도위젯)
        루트.add_widget(상단)

        하단 = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=하단_높이,
            padding=(하단_좌우여백, 0, 하단_좌우여백, 하단_좌우여백),
            spacing=8,
        )
        self.상태라벨 = Label(
            text="", font_size="18sp", size_hint=(1, 하단_첫줄_높이 / 하단_높이)
        )
        하단.add_widget(self.상태라벨)
        나머지 = BoxLayout(
            orientation="vertical",
            size_hint=(1, 하단_나머지_높이 / 하단_높이),
            spacing=8,
        )
        하단.add_widget(나머지)
        루트.add_widget(하단)

        방향틀 = GridLayout(cols=3, size_hint=(1, 0.56), spacing=6)

        파티버튼 = Button(text="파티")
        파티버튼.bind(on_release=self._파티_클릭)
        방향틀.add_widget(파티버튼)

        위버튼 = Button(text="▲")
        위버튼.bind(on_release=lambda *_: self._이동("위"))
        방향틀.add_widget(위버튼)

        메뉴버튼 = Button(text="메뉴")
        메뉴버튼.bind(on_release=self._메뉴_클릭)
        방향틀.add_widget(메뉴버튼)

        왼쪽버튼 = Button(text="◀")
        왼쪽버튼.bind(on_release=lambda *_: self._이동("왼쪽"))
        방향틀.add_widget(왼쪽버튼)

        self.상호작용버튼 = Button(text="상호작용", disabled=True)
        self.상호작용버튼.bind(on_release=self._상호작용)
        방향틀.add_widget(self.상호작용버튼)

        오른쪽버튼 = Button(text="▶")
        오른쪽버튼.bind(on_release=lambda *_: self._이동("오른쪽"))
        방향틀.add_widget(오른쪽버튼)

        소지품버튼 = Button(text="소지품")
        소지품버튼.bind(on_release=self._소지품_클릭)
        방향틀.add_widget(소지품버튼)
        아래버튼 = Button(text="▼")
        아래버튼.bind(on_release=lambda *_: self._이동("아래"))
        방향틀.add_widget(아래버튼)
        스킬버튼 = Button(text="스킬")
        스킬버튼.bind(on_release=self._스킬_클릭)
        방향틀.add_widget(스킬버튼)

        나머지.add_widget(방향틀)

        self.메시지라벨 = Label(text="", size_hint=(1, 0.44))
        나머지.add_widget(self.메시지라벨)

        self.add_widget(루트)

    def 갱신(self):
        앱 = App.get_running_app()
        게임상태 = 앱.게임상태
        던전상태 = 게임상태["던전상태"]

        파티원_정사각형_채우기(self.파티줄, 게임상태)
        self.상태라벨.text = f"위치 {던전상태['위치']}  걸음수 {던전상태['걸음수']}"
        if 던전상태.get("봉절걸음", 0) > 0:
            self.상태라벨.text += f"  봉절 {던전상태['봉절걸음']}"
        self.지도위젯.갱신(
            던전상태["그리드"],
            던전상태["위치"],
            게임상태.get("선택된초상화"),
            던전상태.get("던전파일명"),
            gameflow.던전_오브젝트_표시(게임상태),
            던전상태["맵정보"].get("타일"),
            gameflow.이어진_맵_목록(게임상태),
        )
        self.메시지라벨.text = ""
        self.상호작용버튼.disabled = True
        self._대기중오브젝트 = None

    def _이동(self, 방향):
        앱 = App.get_running_app()
        결과 = gameflow.던전_이동(앱.게임상태, 방향)

        if 결과["결과"] == "이동불가":
            self.메시지라벨.text = "그 쪽으로는 갈 수 없습니다."

        elif 결과["결과"] == "오브젝트":
            self._대기중오브젝트 = (결과["위치"], 결과["오브젝트"])
            self.상호작용버튼.disabled = False
            self.메시지라벨.text = "무언가 있습니다. '말 걸기'를 눌러보세요."

        elif 결과["결과"] == "전투시작":
            self.manager.get_screen("전투").갱신(신규=True)
            self.manager.current = "전투"
            return

        elif 결과["결과"] == "이동":
            self.갱신()
            if 결과.get("봉절해제"):
                self.메시지라벨.text = "봉절이 풀렸습니다."
            연결지역 = 결과.get("연결지역")
            if 연결지역 is not None:
                처리 = gameflow.연결지역_처리(앱.게임상태, 연결지역)
                if 처리["타입"] == "마을":
                    self.manager.get_screen("마을").갱신()
                    self.manager.current = "마을"
                    return
                elif 처리["타입"] == "던전":
                    # 다른 던전으로 이어지는 연결점 - 새 던전 지도로 바로
                    # 갱신한다.
                    self.갱신()
                    self.메시지라벨.text = f"{처리['지도명']}(으)로 이동했습니다."
                    return
                else:
                    self.메시지라벨.text = (
                        "이 앞은 다른 지역으로 이어지지만, 이번 프로토타입에는 "
                        "아직 구현돼 있지 않습니다."
                    )

    def _상호작용(self, *args):
        if self._대기중오브젝트 is None:
            return
        위치, 오브젝트 = self._대기중오브젝트
        앱 = App.get_running_app()
        결과 = gameflow.오브젝트_상호작용(앱.게임상태, 위치, 오브젝트)

        if 결과["결과"] == "전투시작":
            self.manager.get_screen("전투").갱신(신규=True)
            self.manager.current = "전투"
            return
        elif 결과["결과"] == "미지원":
            self.메시지라벨.text = (
                결과.get("설명") or "여긴 아직 아무 일도 일어나지 않습니다."
            )
        else:
            self.메시지라벨.text = "몬스터 데이터가 없어 전투를 시작할 수 없습니다."

        self.상호작용버튼.disabled = True
        self._대기중오브젝트 = None

    def _스킬_클릭(self, *args):
        """[스킬] - 파티원의 던전스킬(던전 캠핑 등) 목록 팝업. 줄을 누르면 쓴다."""
        게임상태 = App.get_running_app().게임상태
        줄들 = gameflow.던전스킬_목록(게임상태)
        if not 줄들:
            self.메시지라벨.text = "던전에서 쓸 수 있는 스킬이 없습니다."
            return
        본문 = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        팝업 = Popup(
            title="던전 스킬", content=본문, size_hint=(0.9, None), height=dp(480)
        )
        스크롤, 목록틀 = 스크롤_목록(0.85, 간격=dp(6))
        for 줄 in 줄들:
            캐릭터 = 줄["캐릭터"]
            이름 = 캐릭터.get("캐릭터명") or 캐릭터.get("직업", "")
            남은 = f" {줄['남은'][0]}/{줄['남은'][1]}" if 줄["남은"] else ""
            글 = f"{이름} - {줄['스킬']}{남은}  " + (
                "(풀기)" if 줄["해제"] else f"MP {줄['MP']}"
            )
            if not 줄["가능"]:
                글 += f"\n({줄['사유']})"
            버튼 = Button(
                text=글,
                size_hint_y=None,
                height=dp(72),
                halign="center",
                disabled=not 줄["가능"],
            )
            버튼.bind(
                on_release=lambda *_, 캐릭터=캐릭터, 스킬=줄["스킬"]: self._스킬_사용(
                    팝업, 캐릭터, 스킬
                )
            )
            목록틀.add_widget(버튼)
        본문.add_widget(스크롤)
        본문.add_widget(닫기_버튼(팝업, size_hint=(1, 0.15)))
        팝업.open()

    def _스킬_사용(self, 팝업, 캐릭터, 스킬이름):
        팝업.dismiss()
        결과 = gameflow.던전스킬_사용(App.get_running_app().게임상태, 캐릭터, 스킬이름)
        self.갱신()  # 파티 HP 칸을 다시 그린다(메시지를 비우므로 문구는 뒤에)
        self.메시지라벨.text = 결과["문구"]

    def _소지품_클릭(self, *args):
        self.manager.get_screen("소지품").복귀화면 = "던전"
        self.manager.current = "소지품"

    def _메뉴_클릭(self, *args):
        게임메뉴_열기(self)

    def _파티_클릭(self, *args):
        self.manager.get_screen("파티관리").복귀화면 = "던전"
        self.manager.current = "파티관리"
