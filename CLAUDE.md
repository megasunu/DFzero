# 던전앤파이터 모바일 프로토타입

Kivy로 만든 턴제 RPG 프로토타입이다. buildozer로 안드로이드 APK를 빌드한다.
원격 저장소: https://github.com/megasunu/DFzero (기본 브랜치 `main-branch`)

**할 일과 상태는 작업 보드 [던전앤파이터 모바일](https://github.com/orgs/megasunu/projects/1)에만 있다** - 아래 "작업 보드".
이어서 하는 세션은 `session-resume` 스킬로 시작한다.

## 구조와 계층 규칙

**계층은 한 방향이다: `screens` -> `gameflow`(창구) -> `controller` -> `system` -> `data`.**
세부 구조와 모듈 배치는 `.claude/rules/layers.md` (`game/`, `gameflow.py`를 건드릴 때 읽힌다).

## 처음 한 번 (저장소마다)

```
pip install pytest pytest-cov pytest-xdist==3.8.0 ruff==0.16.9   # CI와 같은 버전 - ruff는 버전마다 서식이 다르다
git config core.hooksPath .githooks          # pre-commit 훅 켜기
```

클라우드 세션은 컨테이너가 사라지므로 **세션마다** 이 둘을 다시 한다. 브랜치는 `claude/<작업>`, 끝내기 전에 push한다.

## 완료 기준 (Definition of Done)

한 작업을 끝냈다고 하려면 다음을 모두 만족해야 한다:

1. **`python tools/check.py` 통과** - compileall + `ruff check` + `ruff format --check` + `pytest` +
   커버리지 하한(game/system + game/controller + gameflow.py, `COVERAGE_FLOOR`) + 훅 `node --test`. CI(`.github/workflows/check.yml`)도
   모든 push/PR에서 같은 명령을 돌린다. 서식이 걸리면 `python -m ruff format .`.
   **로직을 추가/변경하면 테스트도 같이 추가한다** - 어디에 넣을지는 `.claude/rules/tests.md`의 "테스트 지도".
2. **골든 파일(`tests/golden/`)이 바뀌었다면 이유를 커밋에 적는다.** 리팩터링은
   동작을 바꾸지 않는 것이 정의이므로 골든이 바뀌면 안 된다. 동작을 일부러
   바꾼 경우만 `UPDATE_GOLDEN=1 python -m pytest`로 다시 쓰고 diff를 설명한다.
3. **화면(kivy) 변경은 tests/가 못 잡는다.** `python tools/ui_smoke.py`(리눅스는
   `xvfb-run -a -s "-screen 0 1080x2340x24"`를 앞에)로 실제 화면을 돌려 확인하고,
   바꾼 동작이 스모크에 없으면 스모크에 단계를 추가한다(주제별 `_단계_*` 제너레이터에 넣는다).
   CI에도 같은 스모크를 도는 `ui-smoke` 잡이 있고, 실패하면 PR을 막는다.
4. **보드 갱신** - PR 본문에 `Closes #N`으로 이슈를 잇고, 남은 일·새 버그·확인 못 한 것은 이슈로 만든다(아래 "작업 보드").
5. **큰 기능은 풀 시나리오로 검증한다** - `.claude/rules/scenarios.md`.
6. **큰 기능이면 `CHANGELOG.md`의 `미릴리스`에 한 줄**을 같은 커밋에 더한다. 변경 내역은 거기만 본다.

**돌리지 못한 검증은 통과로 쓰지 않는다.** 커밋 본문에
`NOT VERIFIED: <무엇을> 실행해 보지 못함 - <이유>`로 남긴다. APK 빌드는 CI(`build-apk.yml`)에서만
되고, 화면은 헤드리스 테스트 범위 밖이다.

## 작업 방식 (가드레일)

- **계획 먼저.** 작업의 첫 턴에는 편집하지 않는다. 바꿀 것, 바꾸지 않을 것, 게이트, 이 세션이 그 게이트를 돌릴 수 있는지를
  보여주고 명시적 승인을 받은 뒤 진행한다. 승인은 계획에 적힌 단계만 덮고, 범위가 넓어지는 새 단계는 다시 사용자에게 묻는다.
- **새 모듈·의존성·서비스는 사용자와 먼저 정한다** - 선택지, 각각의 장기 유지보수 비용, 추천을 가져온다.
- **테스트 먼저.** 새 동작이나 수정 전에 실패하는 테스트를 만들고 옳은 이유로 실패하는 것을 본다. 단위 테스트가 안 되는 것은 커밋 본문에 쓴다.
- **리팩터링과 동작 변경을 한 커밋에 섞지 않는다.** 버그를 발견하면 이슈로 만들고 따로 고친다.
- **자동 수정은 최대 2번.** 같은 문제로 두 번 고쳐도 게이트가 안 통과하면 멈추고(같은 검사가 매번 다른 곳에서 깨져도 같은 문제)
  상황을 보고한다. 테스트나 검사를 건너뛰거나 끄거나 약하게 해서 초록을 만들지 않는다. `main-branch`에서도 빨간 실패는 PR에 적는다.
- **값은 데이터 파일이 아니라 실행 결과로 확인한다.** 딕셔너리에 적힌 값이 실제 게임에
  쓰이는지는 별개다(예: "미정" HP가 1로 등장). 테스트나 스모크로 돌려 본 것만 사실로 쓴다.
- **테스트/스모크/플레이 확인에서 "치트" 아이템을 쓰지 않는다** - 레어도 "치트" 아이템(치트용 소검,
  치트용 마법석 등)은 사용자 전용이다. 장착/구매/사용 모두 금지. 예외는 그 치트 아이템 자체를 검사하는 테스트뿐이다.
- **되돌리기 어려운 명령은 실행하는 순간에 따로 허락을 받는다** - 원격 브랜치 강제 push,
  브랜치 삭제, PR 병합(Claude의 `claude/*` PR은 워크플로가 병합 - 아래 "Git"), `game/saves/` 삭제. 그 명령이 들어 있는 계획을 승인받은 것은
  실행 허락이 아니다.
- **비밀값을 커밋하지 않는다** - 서명 키스토어, 토큰, 비밀번호, `*.pem`, `.env`. CI 비밀은 GitHub Secrets로.
- **이 저장소는 공개다** - 이슈와 Actions 로그도 전부 공개다. 내부 URL, 개인정보, 비공개 계획을 쓰지 않는다.
- **GitHub 워크플로:** 맨 위 `permissions: {}`와 잡별 권한, `actions/checkout`은 `persist-credentials: false`, 액션은 주 버전 고정.

## 규칙 파일과 스킬

해당 파일을 건드릴 때 읽히는 규칙(`.claude/rules/`, 파일마다 80줄 이하 - 게이트가 검사한다): `layers.md`(구조·계층),
`tests.md`(테스트 지도), `scenarios.md`(풀 시나리오), `build-and-save.md`(세이브 호환성·buildozer), `eol.md`(줄끝).
`CLAUDE.md`는 100줄 이하(게이트가 검사). **모든 텍스트 파일은 LF** - `.gitattributes`(`* text=auto eol=lf`)와 pre-commit 훅이 지키고 게이트가 검사한다(세부 `eol.md`).

작업할 때 `repo-workflow` 스킬(계획·검증·클라우드·브랜치·커밋·PR)을 따른다. 그 밖의 스킬(`.claude/skills/`): `handoff-trigger`
(핸드오프 권유는 맥락 400k부터, `context-guard` 훅이 알림), `session-handoff`, `session-resume`, `code-graph`(Graft).

## 작업 보드 (할 일의 유일한 기록, 2026-10-16부터)

- **이슈가 작업 단위다.** 상태(백로그/다음/지금/검토 중/완료)·단계·검증·우선순위는 보드 칸에만 둔다. `MEMORY.md`/`.memory/`는 쓰지 않는다(게이트가 검사).
- **주인이 정할 일 = 담당자 kirnata77**("결정 대기"). 폰에서만 확인되는 일은 검증 칸 `실기기 필요`. 담당자 없는 이슈는 세션이 가져갈 수 있다.
- 로컬은 `gh project`(보드 #1)로, 클라우드 세션은 `status` 브랜치의 `STATUS.md`로 읽고 명령 라벨(`명령:상태-지금` 등)로 쓴다.
  새 이슈·닫힘은 `project-sync`가 반영한다. 방법과 라벨 표: `docs/setup/project-board.md`. 게임 규칙은 `docs/game-rules.md`.

## Git

- **`main-branch`에 직접 push하지 않는다.** 기능마다 최신 `main-branch`에서 브랜치를 따서 게이트 통과 후 PR을 연다.
  **Claude가 연 `claude/*` PR은 `auto-merge.yml`이 CI(`check`·`ui-smoke`) 초록에서 병합한다**(2026-10-15 사용자 결정) - Claude는 GitHub 자동 병합을
  켜거나 손으로 병합하지 않고 빨간 CI를 고친다. 보호 경로(`.github/workflows/`·`buildozer.spec`·`tools/auto_merge_gate.py`·`CLAUDE.md`·`.claude/rules/` - `tests.md`·`layers.md`는 뺀다)를 바꾸는 PR은 초안으로 열고, 초안과 사용자가 연 PR은 사용자가 병합한다. 병합된 브랜치는 끝난 것이다.
- **작업 중 커밋은 빠른 확인(`check.py --빠른`), push 전에 전체 게이트 한 번.** 원격에 올라간 커밋은 고치지 않는다(강제 push 금지). 절차 전체는 `repo-workflow` 스킬.
- Claude의 커밋은 `Claude <noreply@anthropic.com>`으로 쓴다: 커밋마다 `git -c user.name=Claude -c user.email=noreply@anthropic.com commit`,
  git config에는 넣지 않는다. 이슈와 사용자가 연 PR은 사용자의 것이다.
- **APK 빌드는 `v*` 태그 push로만 돈다**(`build-apk.yml`). 사용자는 PC가 없고 이 세션의 git은 태그 push를 403으로 막는다. **릴리스는 사용자가
  APK를 만들어 달라고 할 때만 한다 - 그전에는 릴리스를 묻거나 권하지 않는다**(2026-10-13 사용자 지시). 요청을 받으면 Claude가 버전 PR을 열고(절차: `.claude/rules/build-and-save.md`), 사용자가 병합한 뒤
  GitHub 웹에서 릴리스를 게시한다(태그가 생겨 빌드가 돈다). Claude는 그 실행과 릴리스를 확인한다. 릴리스 삭제는 사용자에게 부탁한다.

## Overrides of global rules (전역 규칙의 예외)

- **결정은 kirnata77.** 전역 규칙이 Kade의 몫이라고 하는 결정(새 모듈·의존성, 사용자에게 남기는 병합, 주인이 정할 이슈)은 주인 kirnata77이나 Kade가 한다.
- **테스트 지도와 모듈 배치는 자동 병합한다.** `.claude/rules/tests.md`·`layers.md`는 기능 PR이 함께 고치므로 전역 G23(에이전트 규칙은 사람이 병합)에서 뺀다.
- **기본 브랜치는 `main-branch`.** 전역 규칙의 `main`(브랜치를 따는 곳, PR과 자동 병합의 대상)은 여기서 `main-branch`다.
