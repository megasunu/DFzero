"""공용 픽스처.

tests/는 kivy 없이 돈다 - gameflow.py 이하(game/system, game/data)는 kivy를
import하지 않기 때문이다. game/screens/와 main.py는 여기서 다루지 않는다.
"""

import json
import os
import random

import pytest

from game.controller import ctl_battle
from game.system import save_system
from game.system.combat import core
from tests import support

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden")


@pytest.fixture(autouse=True)
def 임시_세이브폴더(tmp_path, monkeypatch):
    """테스트가 실제 game/saves/를 건드리지 않게 세이브 폴더를 바꿔치기한다."""
    monkeypatch.setattr(save_system, "_세이브_폴더", lambda: str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def 기기_설정_기본값():
    """테스트마다 [설정]의 세 값(반응 자동/자동전투/전투로그 방식)을 기본값으로 시작한다."""
    ctl_battle._설정.clear()
    ctl_battle._설정.update(ctl_battle._설정_기본값)


@pytest.fixture(autouse=True)
def 전역_난수_시드():
    """테스트마다 전역 random을 0으로 시작한다 - 테스트를 하나만 돌려도, 순서를 바꿔도 결과가 같게."""
    random.seed(0)


@pytest.fixture(autouse=True)
def 전투_로그_종류_검사(monkeypatch):
    """모든 테스트에서 엔진이 쌓는 로그 항목의 "종류"가 core.로그_종류 중 하나인지 본다(품질 계획 P4)."""
    원래 = core.로그

    def 검사(전투상태, 항목, *, 종류):
        assert 종류 in core.로그_종류, f"모르는 로그 종류 {종류!r}: {항목}"
        return 원래(전투상태, 항목, 종류=종류)

    monkeypatch.setattr(core, "로그", 검사)


def _정규화(값):
    """JSON 왕복으로 튜플/키 타입 차이를 없앤다(골든 파일과 비교할 모양)."""
    return json.loads(json.dumps(값, ensure_ascii=False, default=str))


@pytest.fixture
def golden():
    """golden(이름, 실제값): tests/golden/<이름>.json과 비교한다.

    동작을 일부러 바꿨다면 UPDATE_GOLDEN=1 로 실행해 골든 파일을 다시 쓰고,
    그 diff를 커밋에서 설명한다. 리팩터링(동작 불변)이라면 골든이 바뀌면 안 된다.
    """

    def _비교(이름, 실제값):
        경로 = os.path.join(GOLDEN_DIR, f"{이름}.json")
        실제값 = _정규화(실제값)
        if os.environ.get("UPDATE_GOLDEN") == "1" or not os.path.exists(경로):
            support.골든_쓰기(경로, 실제값)
            if os.environ.get("UPDATE_GOLDEN") != "1":
                pytest.fail(
                    f"골든 파일이 없어 새로 만들었다: {경로} - 내용을 확인하고 커밋할 것"
                )
            return
        with open(경로, encoding="utf-8") as f:
            기대값 = json.load(f)
        assert 실제값 == 기대값, (
            f"{이름}: 골든과 다르다 (의도한 변경이면 UPDATE_GOLDEN=1)"
        )

    return _비교


def pytest_sessionfinish(session, exitstatus):
    """골든을 갱신했으면(UPDATE_GOLDEN=1) 문장 골든을 다른 골든이 다 쓰인 뒤에 한 번 더 쓴다.

    문장 골든은 다른 골든의 로그에서 만들어지므로, 그 테스트가 먼저 돌면 바뀌기 전 골든을 읽는다.
    세션 끝에 다시 쓰면 테스트 순서(병렬 실행 포함)와 상관없이 갱신 한 번으로 맞는다.
    병렬 실행의 작업자는 건너뛰고 주 프로세스만 쓴다.
    """
    if os.environ.get("UPDATE_GOLDEN") != "1" or hasattr(session.config, "workerinput"):
        return
    support.골든_쓰기(
        os.path.join(GOLDEN_DIR, f"{support.문장_골든}.json"),
        support.골든_문장들(GOLDEN_DIR),
    )
