"""tools/balance_analysis.py - 밸런스 체크 분석용 전투(#690): 고른 무작위 파티, 무작위 행동, 판 기록, 집계, 선형 회귀."""

import collections
import random

from tools import balance_analysis as ba
from tools import balance_sim as bs

# 전투를 도는 테스트가 쓰는 작은 파티 둘(버퍼·인형·반응이 섞이게)
파티A = [
    ("귀검사", "검귀"),
    ("프리스트", "크루세이더"),
    ("거너", "레인저"),
    ("마법사", "엘리멘탈마스터"),
]
파티B = [
    ("격투가", "넨마스터"),
    ("귀검사", "소울브링어"),
    ("프리스트", "인파이터"),
    ("거너", "메카닉"),
]


def test_고른_파티는_묶음마다_전직이_한_번씩_들어가고_한_파티에_같은_전직이_없다():
    전직표 = bs.측정_전직표()
    전직들 = [j for 목록 in 전직표.values() for j in 목록]
    파티들 = ba.고른_파티들(전직표, 묶음=3, R=random.Random(5))
    assert len(파티들) == 3 * len(전직들) // 4
    횟수 = collections.Counter(전 for 파티 in 파티들 for _, 전 in 파티)
    assert set(횟수) == set(전직들) and set(횟수.values()) == {3}
    for 파티 in 파티들:
        assert len(파티) == 4 and len({전 for _, 전 in 파티}) == 4
        assert all(전 in 전직표[일차] for 일차, 전 in 파티)
    assert 파티들 == ba.고른_파티들(전직표, 묶음=3, R=random.Random(5))
    assert 파티들 != ba.고른_파티들(전직표, 묶음=3, R=random.Random(6))


def test_선형_기여는_정확히_선형인_승률에서_전직별_효과를_되찾는다():
    효과 = {"가": 0.10, "나": -0.05, "다": 0.0, "라": 0.02, "마": -0.07}
    R = random.Random(1)
    판들 = []
    for _ in range(200):
        파티 = R.sample(sorted(효과), 3)
        판들.append((파티, 0.5 + sum(효과[j] for j in 파티)))
    기여 = ba.선형_기여(판들)
    평균 = sum(효과.values()) / len(효과)
    for j, v in 효과.items():
        assert abs(기여[j] - (v - 평균)) < 1e-6
    assert abs(sum(기여.values())) < 1e-9


def test_분석_전투는_같은_시드면_같고_판_기록에_모든_칸이_있다():
    환경 = ba.분석환경()
    r1 = 환경.전투(파티A, 시드=3, 섞기=0.3)
    r2 = 환경.전투(파티A, 시드=3, 섞기=0.3)
    assert r1 == r2
    이름들 = [전 for _, 전 in 파티A]
    assert r1["파티"] == 이름들 and r1["시드"] == 3
    assert isinstance(r1["승"], bool) and r1["라운드"] >= 1
    for 칸 in ("딜", "받음", "생존", "쓰러진라운드", "스킬"):
        assert set(r1[칸]) == set(이름들), 칸
    assert all(isinstance(v, bool) for v in r1["생존"].values())
    for 전 in 이름들:
        if not r1["생존"][전]:
            assert r1["쓰러진라운드"][전] is not None
    # 스킬 기록: {스킬: {"횟수", "피해"}} - 일반공격도 하나의 행동으로 센다
    assert any(r1["스킬"][전] for 전 in 이름들)
    for 기록 in r1["스킬"].values():
        for 값 in 기록.values():
            assert 값["횟수"] >= 1 and 값["피해"] >= 0


def test_분석_전투는_시드마다_행동이_갈라지고_무작위_행동이_전력전투와_다르다():
    환경 = ba.분석환경()
    판들 = [환경.전투(파티A, 시드=s, 섞기=0.3) for s in range(4)]
    assert len({str(r["스킬"]) for r in 판들}) > 1
    무작위 = [환경.전투(파티A, 시드=s, 섞기=0.0)["스킬"] for s in range(3)]
    전력 = [환경.전투(파티A, 시드=s, 섞기=1.0)["스킬"] for s in range(3)]
    assert 무작위 != 전력


def test_분석_전투는_치트_아이템을_쓰지_않는다():
    환경 = ba.분석환경()
    상태 = 환경.파티(파티B)
    for c in 상태["파티"]["파티원"]:
        assert 환경.gf.캐릭터_장착아이템(상태, c, "무기")["레어도"] != "치트"


def test_분석_실행은_일꾼_수와_상관없이_같은_판_기록을_낸다():
    한 = ba.분석_실행([파티A, 파티B], 판=2, 섞기=0.3, 일꾼=1)
    둘 = ba.분석_실행([파티A, 파티B], 판=2, 섞기=0.3, 일꾼=2)
    assert 한 == 둘 and len(한) == 4


def _판(파티, 승, 딜, 생존=None, 쓰러짐=None, 스킬=None, 라운드=3):
    return {
        "파티": 파티,
        "시드": 0,
        "승": 승,
        "라운드": 라운드,
        "딜": dict(zip(파티, 딜)),
        "받음": {j: 1 for j in 파티},
        "생존": 생존 or {j: True for j in 파티},
        "쓰러진라운드": 쓰러짐 or {j: None for j in 파티},
        "스킬": 스킬 or {j: {} for j in 파티},
        "인형": {},
    }


def test_집계는_전직별_승률_생존율_딜지분과_스킬별_썼을_때_승률을_낸다():
    판들 = [
        _판(
            ["가", "나"],
            True,
            [30, 10],
            스킬={"가": {"베기": {"횟수": 2, "피해": 20}}, "나": {}},
        ),
        _판(
            ["가", "나"],
            False,
            [10, 10],
            생존={"가": False, "나": False},
            쓰러짐={"가": 2, "나": 1},
            스킬={"가": {}, "나": {}},
        ),
        _판(
            ["가", "다"],
            True,
            [20, 20],
            스킬={"가": {"베기": {"횟수": 1, "피해": 8}}, "다": {}},
        ),
    ]
    요약 = ba.집계(판들)
    가 = 요약["전직"]["가"]
    assert 가["판"] == 3 and abs(가["승률"] - 2 / 3) < 1e-9
    assert abs(가["생존율"] - 2 / 3) < 1e-9
    # 딜지분은 판마다 그 판 파티 딜 중 몫의 평균
    assert abs(가["딜지분"] - (30 / 40 + 10 / 20 + 20 / 40) / 3) < 1e-9
    베기 = 요약["스킬"][("가", "베기")]
    assert 베기["판"] == 2 and 베기["횟수"] == 3 and abs(베기["판당피해"] - 14) < 1e-9
    assert 베기["썼을때승률"] == 1.0 and 베기["안썼을때승률"] == 0.0
    # 진 판에서 먼저 쓰러진 전직은 "나"(1라운드)
    assert 요약["먼저쓰러짐"] == {"나": 1}
    assert {p["파티"] for p in 요약["파티"]} == {("가", "나"), ("가", "다")}
    assert set(요약["기여"]) == {"가", "나", "다"}


def test_보고서는_마크다운_표로_전직_기여_스킬_파티를_보인다():
    판들 = [
        _판(["가", "나"], True, [30, 10]),
        _판(["가", "다"], False, [5, 5]),
        _판(["나", "다"], True, [1, 9]),
    ]
    글 = ba.보고서(ba.집계(판들), {"판": 3, "섞기": 0.3, "파티": 3, "규칙지문": "abc"})
    for 제목 in ("## 전직", "## 스킬", "## 파티", "선형 회귀", "표준오차"):
        assert 제목 in 글
    assert "| 가 |" in 글


def test_분석_명령은_보고서를_쓴다(tmp_path):
    경로 = tmp_path / "분석.md"
    인수 = ["전체", "--분석", "--묶음", "1", "--판", "1", "--일꾼", "1"]
    assert bs.main(인수 + ["--보고서", str(경로)]) == 0
    글 = 경로.read_text(encoding="utf-8")
    assert "파티 6개 x 파티당 1판 = 6판" in 글
    assert bs.main(["검귀", "--분석"]) == 2
