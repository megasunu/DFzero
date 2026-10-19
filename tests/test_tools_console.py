"""tools/*.py CLI가 콘솔 인코딩과 상관없이 한글을 찍는지 (#200).

Windows에서 출력이 리디렉션되면 stdout이 cp1252가 되어 한글 print가 UnicodeEncodeError로 죽었다
(pre-commit 훅이 `fix_eol.py`에서 커밋을 막음). stdout/stderr를 cp1252 스트림으로 바꿔 끼우는 것은
`PYTHONIOENCODING=cp1252`와 같다.
"""

import contextlib
import io
import sys
from unittest import mock

from tools import check, fix_eol, project_bridge


@contextlib.contextmanager
def cp1252_콘솔():
    """cp1252 stdout/stderr를 끼운다. 끝나면 찍힌 바이트를 UTF-8로 읽어 `글[0]`에 둔다.

    pytest의 출력 가로채기가 단계(setup/call)마다 sys.stdout을 다시 끼우므로 픽스처가 아니라
    테스트 본문 안에서 바꾼다.
    """
    out = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    err = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    글 = [""]
    with mock.patch.object(sys, "stdout", out), mock.patch.object(sys, "stderr", err):
        yield 글
        out.flush()
    글[0] = out.buffer.getvalue().decode("utf-8")


def test_fix_eol은_cp1252_콘솔에서도_끝까지_찍는다(monkeypatch):
    monkeypatch.setattr(fix_eol, "crlf_files", lambda: [])
    with cp1252_콘솔() as 글:
        assert fix_eol.main([]) == 0
    assert "0개 파일 변환" in 글[0]


def test_check는_cp1252_콘솔에서도_끝까지_찍는다(monkeypatch, tmp_path):
    monkeypatch.setattr(check, "STEPS", [("빈 단계", [sys.executable, "-c", "pass"])])
    monkeypatch.setattr(
        check, "TIME_LOG", str(tmp_path)
    )  # 세션의 작업시간 기록을 더럽히지 않는다
    with cp1252_콘솔() as 글:
        assert check.main() == 0
    assert "PASS: 모든 검사 통과" in 글[0]


def test_project_bridge는_cp1252_콘솔에서도_끝까지_찍는다():
    with cp1252_콘솔() as 글:
        assert project_bridge.main(["labels"]) == 0
    assert "명령:" in 글[0]
