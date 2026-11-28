"""장비 이름이 데이터에서 사라지면 옛 세이브를 위한 마이그레이션이 있어야 한다(#853).

세이브는 장착 칸과 소지품에 장비를 이름으로만 적는다. 이름을 바꾸며 세이브 마이그레이션(save_system의
`_바뀐_장비이름*` 표)을 빠뜨리면 옛 세이브에 데이터에 없는 이름이 남는다 - 불러올 때 장착 칸은 비우지만
(ctl_session._없는_장착장비_빼기) 그 장비는 잃는다. 기록(equipment_names.json)은 지금까지 있던 장비 이름이다.
"""

import json
import os
from pathlib import Path

from game.system import save_system
from tests import support

기록_경로 = Path(__file__).with_name("equipment_names.json")


def _지금_이름():
    카탈로그 = support.새게임()["상점카탈로그"]["장비"]
    return {이름 for 부위 in 카탈로그.values() for 이름 in 부위}


def _옛_이름():
    """save_system의 장비 이름 마이그레이션 표(`_바뀐_장비이름*`, {옛 이름: 새 이름})의 옛 이름."""
    return {
        옛
        for 변수, 표 in vars(save_system).items()
        if 변수.startswith("_바뀐_장비이름") and isinstance(표, dict)
        for 옛 in 표
    }


def test_사라진_장비_이름은_세이브_마이그레이션이_있다():
    기록 = set(json.loads(기록_경로.read_text(encoding="utf-8")))
    사라짐 = sorted(기록 - _지금_이름() - _옛_이름())
    assert not 사라짐, (
        f"장비 데이터에서 사라진 이름 {사라짐} - 이름을 바꿨으면 save_system에 세이브 버전을 올리고 "
        "_바뀐_장비이름_<옛버전>_<새버전> = {옛 이름: 새 이름} 마이그레이션을 더한다. 일부러 지웠으면 "
        f"{기록_경로.name}에서 그 이름을 뺀다(옛 세이브의 그 장비는 불러올 때 장착 칸에서 빠진다)."
    )


def test_새_장비_이름은_기록에_있다():
    """새 장비는 기록에 더한다 - UPDATE_GOLDEN=1이면 이 테스트가 새 이름만 더해 다시 쓴다(지우지는 않는다)."""
    기록 = json.loads(기록_경로.read_text(encoding="utf-8"))
    새것 = sorted(_지금_이름() - set(기록))
    if 새것 and os.environ.get("UPDATE_GOLDEN") == "1":
        기록_경로.write_text(
            json.dumps(sorted(set(기록) | set(새것)), ensure_ascii=False, indent=0)
            + "\n",
            encoding="utf-8",
        )
        return
    assert not 새것, f"{기록_경로.name}에 없는 장비 {새것} - UPDATE_GOLDEN=1로 더한다"
