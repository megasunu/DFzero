"""자동 병합 판정 - PR의 head 커밋이 병합해도 될 만큼 초록인지 정한다.

`.github/workflows/auto-merge.yml`이 부른다. stella-rain/.github의 scripts/auto_merge_gate.py에
buildozer.spec을 기본 보호 경로로 더했다(CLAUDE.md "Git").

커밋의 check run과 combined commit status(GitHub REST API가 주는 그대로)를 읽고 한 단어를 찍는다:

- `merge`: check run이 모두 초록(success, neutral, skipped)으로 끝났고, 하나 이상 성공했고, 필수 검사가
  모두 성공했고, 대기 중이거나 실패한 commit status가 없다.
- `wait`: 아직 도는 것이 있거나, 아무것도 보고되지 않았거나, 필수 검사가 아직 성공하지 않았다
  (시작 전이거나 건너뜀).
- `stop`: 실패한 것이 있거나 사용자에게 남기는 PR이다: 초안, 보호 경로(`.github/workflows/`,
  `buildozer.spec`, 이 스크립트, `CLAUDE.md`, `.claude/rules/`(테스트 지도 `tests.md`와 모듈 배치 `layers.md`는 뺀다),
  `--protect` 경로)를 바꾸는 PR, 파일 목록을 다 읽지 못한 PR.

사용법: python3 auto_merge_gate.py [--require NAMES]... [--protect PATHS]...
           [--pr PR_JSON [--files FILES_JSON]] CHECK_RUNS_JSON COMBINED_STATUS_JSON
CHECK_RUNS_JSON은 check run 배열, COMBINED_STATUS_JSON은 `GET /repos/{repo}/commits/{sha}/status`의
객체다. NAMES와 PATHS는 줄 목록이고 빈 줄은 무시한다. `--require`는 성공해야 하는 check run 이름이라
워크플로가 아직 시작하지 않은 검사를 건너뛸 수 없다. `--protect`는 경로를 더한다: `/`로 끝나면 폴더,
아니면 파일 하나. PR_JSON은 `GET /repos/{repo}/pulls/{n}`의 `draft`와 `changed_files`, FILES_JSON은
그 파일들(모든 페이지)의 `filename`과 `previous_filename` 배열이다. --pr이 있는데 --files가 없으면 멈춘다.
제목은 찍지 않는다(Actions 로그는 공개다) - 검사 이름, 결과, 경로만.

병합한 뒤: python3 auto_merge_gate.py --issues-to-close REFS_JSON OWNER/REPO
REFS_JSON은 PR의 `closingIssuesReferences`(`gh pr view --json`)다. OWNER/REPO에서 닫을 이슈 번호를
한 줄에 하나씩 찍는다. GITHUB_TOKEN으로 한 병합은 닫는 키워드(`Closes #N`)를 적용하지 않으므로
워크플로가 직접 닫는다.
"""

import json
import sys

GREEN = {"success", "neutral", "skipped"}

# 사용자가 병합하는 PR: 워크플로(검사와 병합 규칙 자체), buildozer.spec(릴리스 버전), 이 스크립트(auto-merge.yml이
# main-branch의 이것을 돌린다 - 바꾸는 PR이 스스로 병합되면 다음 PR부터 보호가 풀린다), 에이전트 규칙(전역 G23).
PROTECTED = (
    ".github/workflows/",
    "buildozer.spec",
    "tools/auto_merge_gate.py",
    "CLAUDE.md",
    ".claude/rules/",
)
# 보호 경로 안의 예외(파일 하나씩): 기능 PR이 새 테스트 파일·모듈을 적는 곳이라 기능과 같이 병합한다
# (CLAUDE.md "Overrides of global rules").
UNPROTECTED = (".claude/rules/tests.md", ".claude/rules/layers.md")


def name_list(text):
    """줄 목록에서 빈 줄을 빼고 앞뒤 공백을 자른 것."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def protected_paths(files, protected=()):
    """PR 파일 중 보호 경로에 걸리는 것(이름 바꾸기는 두 이름 모두). 정렬, 중복 없음."""
    rules = PROTECTED + tuple(protected)
    dirs = tuple(r for r in rules if r.endswith("/"))
    whole = {r for r in rules if not r.endswith("/")}
    names = {
        n for f in files for n in (f.get("filename"), f.get("previous_filename")) if n
    }
    return sorted(
        n for n in names if (n.startswith(dirs) or n in whole) and n not in UNPROTECTED
    )


def left_to_user(pr, files, protected=()):
    """이 PR을 사용자에게 남기는 이유, 없으면 None."""
    if pr.get("draft"):
        return "draft"
    if files is None or len(files) != pr.get("changed_files"):
        return "file list not read whole"
    touched = protected_paths(files, protected)
    if touched:
        return "protected paths: " + ", ".join(touched)
    return None


def decide(check_runs, combined_status, required=(), pr=None, files=None, protected=()):
    if pr is not None and left_to_user(pr, files, protected):
        return "stop"
    waiting = False
    for check in check_runs:
        if check.get("status") != "completed":
            waiting = True
        elif check.get("conclusion") not in GREEN:
            return "stop"
    if combined_status.get("total_count", 0) > 0:
        state = combined_status.get("state")
        if state in ("failure", "error"):
            return "stop"
        if state != "success":
            waiting = True
    succeeded = {c.get("name") for c in check_runs if c.get("conclusion") == "success"}
    if waiting or not succeeded or not set(required) <= succeeded:
        return "wait"
    return "merge"


def issues_to_close(refs, repo):
    """참조된 이슈 중 `repo`(owner/name)에 있는 것의 번호. 정렬, 중복 없음."""
    wanted = repo.lower()
    numbers = set()
    for r in refs:
        repository = r.get("repository") or {}
        owner = (repository.get("owner") or {}).get("login", "")
        if f"{owner}/{repository.get('name', '')}".lower() == wanted:
            numbers.add(r["number"])
    return sorted(numbers)


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv):
    if len(argv) == 4 and argv[1] == "--issues-to-close":
        for number in issues_to_close(_load(argv[2]), argv[3]):
            print(number)
        return 0
    required, protected, options, args = [], [], {}, argv[1:]
    while len(args) >= 2 and args[0] in ("--require", "--protect", "--pr", "--files"):
        if args[0] == "--require":
            required += name_list(args[1])
        elif args[0] == "--protect":
            protected += name_list(args[1])
        else:
            options[args[0]] = args[1]
        args = args[2:]
    if len(args) != 2 or ("--files" in options and "--pr" not in options):
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2
    pr = _load(options["--pr"]) if "--pr" in options else None
    files = _load(options["--files"]) if "--files" in options else None
    check_runs = _load(args[0])
    combined_status = _load(args[1])
    for check in check_runs:
        print(
            f"check: {check.get('name')}: {check.get('status')} {check.get('conclusion')}",
            file=sys.stderr,
        )
    for name in required:
        print(f"required: {name}", file=sys.stderr)
    if pr is not None:
        print(
            f"left to user: {left_to_user(pr, files, protected) or 'no'}",
            file=sys.stderr,
        )
    print(decide(check_runs, combined_status, required, pr, files, protected))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
