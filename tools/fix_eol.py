"""줄끝 규칙 검사/수정 - 저장소의 모든 텍스트 파일은 LF (.claude/rules/eol.md).

    python tools/fix_eol.py          # CRLF(또는 CR)가 섞인 파일을 LF로 바꾼다
    python tools/fix_eol.py --check  # 바꾸지 않고 위반 파일만 출력(있으면 종료코드 1)

git의 `* text=auto eol=lf`(.gitattributes)가 커밋할 때 CRLF를 LF로 정규화하지만,
GitHub 웹 업로드처럼 git을 거치지 않고 들어온 파일이나 아직 커밋 안 한 작업 파일은
그 정규화를 받지 않는다 - 그런 것을 이 스크립트와 tests/structure/test_repo_hygiene.py가 잡는다.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 텍스트로 취급할 확장자/파일명. 이미지(.webp 등)/폰트는 건드리지 않는다.
TEXT_EXTS = {
    ".py",
    ".cjs",
    ".md",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".spec",
    ".txt",
    ".kv",
    ".cfg",
    ".ini",
    ".csv",
}
TEXT_NAMES = {".gitignore", ".gitattributes", ".git-blame-ignore-revs"}
# 확장자가 없어도 폴더 안 파일 전부가 텍스트인 곳(git 훅 - sh가 실행한다)
TEXT_DIRS = {".githooks"}

# 저장소 파일이 아닌 폴더(빌드/캐시/세이브/로컬 설정)
SKIP_DIRS = {
    ".git",
    ".buildozer",
    "bin",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".claude",
    "venv",
    ".venv",
    "ui_smoke_shots",
}
SKIP_PATHS = {os.path.join("game", "saves")}


def text_files():
    for folder, dirs, files in os.walk(ROOT):
        rel = os.path.relpath(folder, ROOT)
        dirs[:] = sorted(
            d
            for d in dirs
            if d not in SKIP_DIRS
            and os.path.normpath(os.path.join(rel, d)) not in SKIP_PATHS
        )
        전부텍스트 = os.path.normpath(rel) in TEXT_DIRS
        for name in sorted(files):
            if (
                전부텍스트
                or name in TEXT_NAMES
                or os.path.splitext(name)[1].lower() in TEXT_EXTS
            ):
                yield os.path.join(folder, name)


def has_cr(data):
    return b"\r" in data


def to_lf(data):
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def crlf_files():
    """CR(CRLF 포함)이 들어 있는 파일의 상대경로 목록."""
    bad = []
    for path in text_files():
        with open(path, "rb") as f:
            if has_cr(f.read()):
                bad.append(os.path.relpath(path, ROOT))
    return bad


def main(argv):
    # Windows에서 리디렉션된 출력은 cp1252라 한글 print가 죽는다 - 콘솔 인코딩과 상관없이 UTF-8로.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    bad = crlf_files()
    if "--check" in argv:
        for rel in bad:
            print(f"CRLF 섞임: {rel}")
        return 1 if bad else 0
    for rel in bad:
        path = os.path.join(ROOT, rel)
        with open(path, "rb") as f:
            data = f.read()
        with open(path, "wb") as f:
            f.write(to_lf(data))
        print(f"LF로 변환: {rel}")
    print(f"{len(bad)}개 파일 변환")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
