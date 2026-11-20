# 던전앤파이터 모바일 프로토타입

Kivy로 만든 턴제 RPG 프로토타입. 5개 직업(귀검사/격투가/거너/마법사/프리스트)으로 파티를 꾸려 마을, 던전, 전투, 성장,
장비/상점을 진행한다. 안드로이드 APK는 buildozer로 빌드한다.

- 원격 저장소: https://github.com/megasunu/DFzero (기본 브랜치 `main-branch`)
- 규칙(완료 기준, 가드레일): [`CLAUDE.md`](CLAUDE.md), 주제별 규칙은 [`.claude/rules/`](.claude/rules/), 절차는 [`.claude/skills/`](.claude/skills/) - 기여 전에 읽는다
- 할 일과 상태: 작업 보드 [던전앤파이터 모바일](https://github.com/orgs/megasunu/projects/1)(이슈) - 쓰는 법은 [`docs/setup/project-board.md`](docs/setup/project-board.md)

## 실행

```
pip install kivy
python main.py
```

세이브는 앱 데이터 폴더의 `saves/slot_N.json`(JSON, 슬롯 3개, 쓰기는 원자적이고 `.bak` 백업을 남긴다)에 저장된다. 옛 위치 `game/saves/`의 세이브는 처음 실행할 때 한 번 복사해 온다. 화면은 한글 폰트(`game/assets/font/`)를 쓴다.

## 개발

```
pip install pytest pytest-cov ruff==0.16.9   # CI와 같은 버전
git config core.hooksPath .githooks          # 줄끝을 LF로 맞추는 pre-commit 훅
python tools/check.py                        # 완료 기준 게이트: compileall + ruff + pytest + 커버리지
```

- 로직(전투, 스킬, 장비, 세이브 ...)은 kivy 없이 돈다. 테스트(`tests/`)도 화면 없이 돌고, 골든 파일(`tests/golden/`)과 풀 시나리오(`docs/scenarios.md`)로 검증한다.
- 화면을 바꿨다면 `xvfb-run -a -s "-screen 0 1080x2340x24" python tools/ui_smoke.py`로 실제 화면을 돌려 본다(리눅스 기준).

## 구조

```
main.py            Kivy 앱 진입점
gameflow.py        화면 <-> 로직 창구(재수출만, 화면은 이 파일의 함수만 부른다)
game/controller/   컨트롤러 구현(주제별 ctl_*.py - 전투/상점/파티/레벨업 ...)
game/screens/      Kivy 화면
game/system/       전투(combat/), 스킬, 장비, 세이브 등 게임 로직
game/data/         직업, 몬스터, 던전, 아이템 데이터(파이썬 딕셔너리)
game/assets/       폰트, 이미지
tests/  tools/    테스트, 게이트(check.py)와 화면 스모크(ui_smoke.py)
docs/             빌드 노트, 구조 점검 보고서, 게임 규칙(game-rules.md), 보드 설정(setup/)
```

계층은 한 방향이다: `screens -> gameflow -> controller -> system -> data`. 자세한 구조와 점검 결과는 [`docs/reports/architecture_review.md`](docs/reports/architecture_review.md).

## 빌드

APK는 GitHub Actions의 "Build APK" 워크플로(수동 실행)가 만든다. 방법과 주의점은 [`docs/mobile_apk_build_notes.md`](docs/mobile_apk_build_notes.md).

## 문서

| 파일 | 내용 |
|---|---|
| [`CLAUDE.md`](CLAUDE.md), [`.claude/`](.claude/) | 규칙(완료 기준, 가드레일), 주제별 규칙, 스킬 |
| [`docs/reports/architecture_review.md`](docs/reports/architecture_review.md) | 구조/아키텍처 점검, 다음 로드맵 |
| [`docs/reports/refactoring_report.md`](docs/reports/refactoring_report.md) | 점검 항목의 리팩터링 전/후 비교(병합 후 재측정) |
| [`docs/reports/code_quality_review.md`](docs/reports/code_quality_review.md) | 코드 품질·아키텍처 재점검(2026-10-13, 10-06 대비 변화와 백로그) |
| [`docs/scenarios.md`](docs/scenarios.md) | 풀 시나리오 장부 |
| [`docs/mobile_apk_build_notes.md`](docs/mobile_apk_build_notes.md) | APK 빌드 노트 |
| [`docs/game-rules.md`](docs/game-rules.md) | 게임 규칙과 수치(사용자 결정) |
| [`docs/setup/project-board.md`](docs/setup/project-board.md) | 작업 보드·브리지 설정, 세션이 보드를 쓰는 법 |
