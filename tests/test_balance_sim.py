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


def test_시험자는_전직의_1차_직업으로_만들고_파티_전원이_추천_무기를_든다():
    """11-02 사용자 지정(#520) - 측정 조건처럼 전원이 전직 추천 종류의 언커먼 무기를 든다."""
    import scenario
    import gameflow as gf

    m = bs.측정("마도학자")
    상태 = m._상태(m.기본파티)
    시험자 = 상태["파티"]["파티원"][0]
    assert 시험자["직업"] == "마법사" and 시험자["전직"] == "마도학자"
    for c in 상태["파티"]["파티원"]:
        무기 = gf.캐릭터_장착아이템(상태, c, "무기")
        assert (무기["레어도"], 무기["타입"]) == (
            "언커먼",
            scenario.전직_추천무기[c["전직"]],
        ), c["전직"]
    assert "데스 파우더" in m.행동목록


def test_시험_직업이나_같은_무기_종류가_기본_파티에_있어도_파티를_만든다():
    """레인저는 기본 파티의 레인저와, 패러메딕은 같은 리볼버와 겹친다 - 무기를 하나씩 더 넣어야 한다.
    시험 직업과 같은 전직은 다른 파티처럼 기본 파티에서도 대신할 전직으로 바꾼다."""
    import gameflow as gf

    for 직업 in ("레인저", "패러메딕", "스트라이커", "크루세이더"):
        m = bs.측정(직업)
        assert 직업 not in [전 for _, 전 in m.기본파티]
        상태 = m._상태(m.기본파티)
        for c in 상태["파티"]["파티원"]:
            assert gf.캐릭터_장착아이템(상태, c, "무기")["레어도"] == "언커먼", c[
                "전직"
            ]
