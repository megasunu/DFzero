"""tools/golden_diff.py - 바뀐 골든을 큰 diff 대신 짧게 요약한다(#237 작업시간: 골든 diff 읽기)."""

import json

from tools import golden_diff

옛 = {"HP": 10, "로그": [{"대상": "A", "피해": 3}, {"피해": 2}]}
새 = {"HP": 7, "로그": [{"대상": "A", "피해": 3}, {"피해": 5}, {"피해": 1}]}


def test_바뀐_곳을_키별로_세고_처음_갈린_곳을_찾는다():
    요약 = golden_diff.차이_요약(옛, 새)
    assert 요약["바뀐_곳"] == 3
    assert 요약["키별"] == {
        "HP": 1,
        "피해": 1,
        "로그": 1,
    }  # 늘어난 항목은 목록 이름으로 센다
    assert 요약["첫_갈림"] == "HP"


def test_같으면_바뀐_곳이_없다():
    assert golden_diff.차이_요약(옛, json.loads(json.dumps(옛)))["바뀐_곳"] == 0


def test_로그_목록은_몇_번째_항목부터_갈렸는지_알려준다():
    요약 = golden_diff.차이_요약({"로그": [1, 2, 3, 4]}, {"로그": [1, 2, 9, 9, 9]})
    assert 요약["로그_갈림"] == {
        "로그": (2, 4, 5)
    }  # (처음 다른 번호, 옛 길이, 새 길이)


def test_파일마다_한_줄로_요약하고_추가_삭제도_적는다(tmp_path):
    (tmp_path / "가.json").write_text(
        json.dumps(새, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "나.json").write_text("{}", encoding="utf-8")
    옛_파일들 = {"가": 옛, "다": {}}  # 다는 지워졌고 나는 새로 생겼다
    줄들 = golden_diff.요약_줄들(str(tmp_path), 옛_파일들.get, ["가", "다"])
    assert 줄들[0].startswith("가: 3곳")
    assert "HP 1" in 줄들[0] and "피해 1" in 줄들[0]
    assert "로그 2번째 항목부터" in 줄들[0]  # 사람이 읽는 번호는 1부터
    assert "나: 새 파일" in 줄들
    assert "다: 지워짐" in 줄들
    assert 줄들[-1] == "골든 3개 바뀜(변경 1, 새 파일 1, 지워짐 1), 바뀐 곳 3"


def test_한글_이름의_골든도_git_기준과_비교한다(tmp_path, monkeypatch, capsys):
    """git은 한글 경로를 따옴표·8진수로 바꿔 찍는다 - 그대로 쓰면 모든 한글 골든이 "새 파일"로 보였다."""
    import subprocess

    폴더 = tmp_path / "tests" / "golden"
    폴더.mkdir(parents=True)
    (폴더 / "전투_귀검사.json").write_text('{"피해": 1}', encoding="utf-8")

    def git(*인자):
        subprocess.run(["git", *인자], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    git("add", "-A")
    git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "옛")
    (폴더 / "전투_귀검사.json").write_text('{"피해": 2}', encoding="utf-8")
    monkeypatch.setattr(golden_diff, "ROOT", str(tmp_path))
    assert golden_diff.main([]) == 0
    출력 = capsys.readouterr().out
    assert "전투_귀검사: 1곳 (피해 1)" in 출력
    assert "전투_귀검사: 새 파일" not in 출력
