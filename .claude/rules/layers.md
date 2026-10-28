---
paths:
  - "game/**"
  - "gameflow.py"
  - "main.py"
  - "tools/**"
---

## 구조와 계층 규칙

```
main.py            Kivy 앱 진입점, 화면 등록, 크래시 로그 훅
gameflow.py        화면 <-> 로직/데이터 컨트롤러의 창구(재수출만). 화면은 이 파일의 함수만 부른다
game/controller/   컨트롤러 구현 - 주제별 ctl_*.py 19개(battle/shop/party/levelup ...), gameflow.py가 다시 내보낸다
game/screens/      Kivy 화면 (kivy 의존은 여기와 main.py에만)
game/system/       전투, 스킬, 장비, 세이브 등 게임 로직
  combat/            전투 패키지(모듈 목록은 combat/__init__.py). 쓰는 쪽은
                     `from game.system.combat import flow, stats` 처럼 모듈을 직접 불러 쓴다
  skill/             스킬 실행 엔진 모듈 6개(skill_grant -> usage/target -> apply -> attack -> run, 아래로만).
                     쓰는 쪽은 `game.system.skill_system`(재수출 창구)을 부른다
game/system/rng.py 모든 무작위의 출처 - 용도별 흐름(주사위/확률/대상/던전/보상). 전역 random을 직접 쓰지 않는다
game/data/         직업, 몬스터, 맵, 아이템 데이터(파이썬 딕셔너리)
  common_names.py    여러 계층이 같이 쓰는 이름 목록·표(속성, 연출 모양, 행동자원 ...) - 새로 반복하지 말고 여기서 가져다 쓴다
game/assets/       폰트, 이미지
tests/             헤드리스 테스트 + golden/*.json (kivy 없이 돈다, 테스트 지도는 docs/test-map.md)
tools/check.py     완료 기준 게이트 (CLAUDE.md "완료 기준"), --골든은 골든 갱신 요약
tools/ui_smoke.py  화면 스모크(kivy + Xvfb, 스크린샷) - CI 밖, 화면 바꿀 때 직접
tools/fix_eol.py   줄끝을 LF로 통일 (pre-commit 훅이 부른다)
tools/golden_diff.py  바뀐 골든 요약(파일마다 한 줄) - 큰 diff 대신 읽는다
tools/project_bridge.py  이슈 <-> megasunu 작업 보드 브리지 (project-sync/-snapshot 워크플로가 부른다)
tools/balance_sim.py  직업 밸런스 모의전투(승률·랜덤·변형 패턴) - 기록은 docs/balance/, 게이트 밖에서 직접
.githooks/         pre-commit (줄끝 통일)
docs/              빌드 노트, 구조 점검 보고서, 리뷰 보고서, 시나리오 장부, 게임 규칙(game-rules.md)
README.md          입구(실행/개발/구조/빌드 요약)
```

**계층은 한 방향이다: `screens` -> `gameflow`(창구) -> `controller` -> `system` -> `data`.**
- `game/system/`, `game/data/`, `game/controller/`, `gameflow.py`는 **kivy를 import하지 않는다.** 그래서
  테스트가 화면 없이 돈다(`test_헤드리스_계층은_kivy에_의존하지_않는다`가 지킨다).
- 화면은 `game.system`/`game.controller`를 직접 부르지 않고 `gameflow`를 거친다(`gameflow.xxx_system.`
  으로 우회하는 것도 금지). 화면에 필요한 조회/동작은 주제에 맞는 `game/controller/ctl_*.py`에 함수로
  추가하고 그 모듈의 `__all__`에 넣는다(gameflow.py는 건드리지 않는다 - 창구에는 구현을 두지 않는다).
  `test_화면은_game_system을_직접_쓰지_않는다`와 `test_controller_structure.py`가 지킨다.
- 컨트롤러 모듈은 위에서 아래로만 부른다(registry -> party -> 기능 모듈 -> dungeon/potion/rewards/charview/tavern).
  모듈끼리 순환하거나 다른 모듈의 밑줄 이름을 가져오면 테스트가 실패한다.
- **전투 엔진이 작업 스레드에서 도는 동안 화면은 게임상태를 쓰지 않는다**(`screens_battle._엔진_실행`: 전투 화면을 `disabled`로
  막고 `_엔진중`이면 새 작업을 받지 않는다). 그사이 화면 쪽 일은 반응 팝업(`_반응_묻기`, 엔진은 `Event`로 기다림)의 읽기뿐이고,
  끝 처리는 `Clock.schedule_once`로 메인 스레드에서 한다. 반응 자동이면 스레드 없이 바로 돈다. 테스트는 이 규약을 못 본다.

## 데이터(`game/data/`)를 고칠 때

- `test_data_integrity.py`가 오타(수식 변수, 특성/버프 이름, 그림 파일, 던전 연결)를 잡는다. 런타임은 평가할 수 없는
  수식을 0으로, 정의 없는 특성을 건너뛰어 조용히 넘어가므로 이 테스트가 유일한 안전망이다. 새 변수/예외는 허용 목록에 이유와 함께 더한다.
- 새 스킬/몬스터/버프/상태이상은 전수 스윕이 자동으로 포함해 골든이 바뀐다 - `python tools/check.py --골든`으로 다시 쓰고
  요약을 본다(필요한 파일만 diff를 읽는다). 어느 테스트가 무엇을 지키는지는 `docs/test-map.md`에서 검색한다.
