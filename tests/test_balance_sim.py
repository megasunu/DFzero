"""밸런스 측정 도구(tools/balance_sim.py) - 승률패턴 계산·변형, 규칙 지문, 기록 이어 쓰기.

실제 측정(수백 판)은 게이트 밖에서 돌린다. 여기서는 몇 판만 돌려 기록이 이어지는지 본다.
"""

import json
import random

from tools import balance_sim as bs


def test_승률패턴은_슬롯마다_보정_승률이_가장_높은_행동이고_판수가_모자라면_뺀다():
    누적 = [
        {"일반공격": [3, 10], "귀참": [5, 6]},  # (3+1)/12 < (5+1)/8
        {"일반공격": [6, 10], "카잔": [4, 4]},  # 카잔은 4판뿐이라 후보가 아니다
        {},
    ]
    assert bs.승률패턴_계산(누적, 최소=5) == ["귀참", "일반공격", "일반공격"]
    # 후보가 없는 슬롯은 이전 승률패턴을 그대로 둔다
    assert bs.승률패턴_계산(누적, ["카잔"] * 3) == ["귀참", "일반공격", "카잔"]


def test_변형은_비율만큼만_슬롯을_바꾼다():
    패턴 = ["카잔"] * 10
    assert bs.변형(패턴, ["일반공격"], random.Random(1), 비율=0) == 패턴
    assert bs.변형(패턴, ["일반공격"], random.Random(1), 비율=1) == ["일반공격"] * 10


def test_규칙_지문은_게임_데이터나_로직이_바뀌면_달라진다(tmp_path):
    for 폴더 in ("game/data", "game/system"):
        (tmp_path / 폴더).mkdir(parents=True)
    (tmp_path / "game/data/a.py").write_text("값 = 1\n", encoding="utf-8")
    (tmp_path / "game/system/b.py").write_text("def f():\n    pass\n", encoding="utf-8")
    전 = bs.규칙지문(tmp_path)
    assert bs.규칙지문(tmp_path) == 전
    (tmp_path / "game/data/a.py").write_text("값 = 2\n", encoding="utf-8")
    assert bs.규칙지문(tmp_path) != 전


def test_규칙이_바뀌면_이전_기록은_남되_참고하지_않는다():
    옛 = {"규칙지문": "옛것", "판수": 1000, "승률패턴": ["카잔"]}
    기록 = {"웨펀마스터": [옛]}
    assert bs.현재기록(기록, "웨펀마스터", "새것") is None
    새 = {"규칙지문": "새것", "판수": 3}
    bs.기록_넣기(기록, "웨펀마스터", 새)
    assert 기록["웨펀마스터"] == [새, 옛]
    assert bs.현재기록(기록, "웨펀마스터", "새것") is 새
    더새 = {"규칙지문": "새것", "판수": 6}
    bs.기록_넣기(기록, "웨펀마스터", 더새)  # 같은 규칙이면 바꿔 끼운다
    assert 기록["웨펀마스터"] == [더새, 옛]


def test_이어서_실행하면_저장된_승률패턴으로_판을_더하고_기록을_갱신한다(tmp_path):
    경로 = tmp_path / "patterns.json"
    지문 = bs.규칙지문()
    시작 = bs.빈기록("웨펀마스터", 지문)
    시작["승률패턴"] = ["귀신 : 카잔"] + ["일반공격"] * (bs.슬롯수 - 1)
    옛 = dict(bs.빈기록("웨펀마스터", "옛 규칙"), 판수=999)
    경로.write_text(
        json.dumps({"웨펀마스터": [시작, 옛]}, ensure_ascii=False), encoding="utf-8"
    )

    assert bs.main(["웨펀마스터", "--판", "3", "--기록", str(경로)]) == 0

    기록 = json.loads(경로.read_text(encoding="utf-8"))["웨펀마스터"]
    지금, 남은옛 = 기록
    assert 지금["규칙지문"] == 지문 and 지금["판수"] == 3
    assert sum(n for 칸 in 지금["누적"] for _, n in 칸.values()) >= 3
    assert sum(n for _, n in 지금["실행"][-1]["종류별"].values()) == 3
    assert 지금["승률패턴"][0] == "귀신 : 카잔"  # 3판으로는 슬롯이 바뀌지 않는다
    assert 남은옛["판수"] == 999  # 다른 규칙의 기록은 그대로 남는다
