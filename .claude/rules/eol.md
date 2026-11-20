---
paths:
  - ".gitattributes"
  - ".githooks/**"
  - "tools/fix_eol.py"
  - ".git-blame-ignore-revs"
  - "tests/structure/test_repo_hygiene.py"
---

## 줄끝 - 모든 텍스트 파일은 LF

- `.gitattributes`(`* text=auto eol=lf`)가 커밋 시 LF로 정규화하고, `.githooks/pre-commit`이
  `tools/fix_eol.py`로 작업 트리도 LF로 맞춘다. 게이트(`tests/structure/test_repo_hygiene.py`)가 검사한다.
- **GitHub 웹 업로드는 둘 다 거치지 않는다** - CRLF가 그대로 들어가 게이트가 실패하면
  받아서 `python tools/fix_eol.py`로 고친다. 웹에서 훅을 다시 올리면 실행 권한도 사라진다
  (`chmod +x .githooks/pre-commit`).
- 파이썬으로 파일을 쓸 때는 `open(..., "w", newline="\n")`(tests/conftest.py의 골든 쓰기 참고).
- 서식/줄끝 일괄 변경 커밋은 `.git-blame-ignore-revs`에 등록한다
  (`git config blame.ignoreRevsFile .git-blame-ignore-revs`).
