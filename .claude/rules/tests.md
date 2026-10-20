---
paths:
  - "tests/**"
  - "game/data/**"
  - "tools/check.py"
  - "pyproject.toml"
---

## 테스트 지도

| 파일 | 무엇을 | 방식 |
|---|---|---|
| `test_systems_basic.py` | 주사위, 효과, 파티, 소지품, 캐릭터 데이터, 마을, 지도, 몬스터AI | 정확한 값 |
| `test_systems_items.py` | 상점, 장비, 세이브, 레벨업 | 정확한 값 |
| `test_gameflow.py` | 새 게임 5직업, 세이브 왕복, 로리엔 보스전 | 골든 |
| `test_gameflow_scenarios.py` | 캠페인(던전 10개/숏컷/마을 개방), 패배/도망/휴식, 상점·장비, 성장 1->10(전직) | 골든 + 값 |
| `test_combat_rules.py` | 수식, 피해, 속성, 사용 가능 여부, 타겟, 효과 적용, 조건 | 정확한 값 |
| `test_combat_skills.py` | 스킬 전수(기본/준비됨) | 골든 |
| `test_combat_monsters.py` | 몬스터 고유 패턴 전수 + 보스 칭호 | 골든 |
| `test_combat_stagger.py` | 경직(일반 이니셔티브 -1, 잡기·경직 태그 우선도 -1, 슈퍼아머·경직불가·잡기불가, 남은 순서만 재정렬, 다음 라운드 원래대로), 홀딩(차례 시작 피해, 이점, 시전자 쓰러짐·무력화로 끝, 이미 행동한 대상의 홀딩 전용 차례) | 정확한 값 |
| `test_perks_common.py` | 공용 퍽 전투 특성(만독불침/심안/웨펀·아머브레이커) | 정확한 값 |
| `test_job_soul_bender.py` | 귀검사 달빛베기, 소울브링어 전직 특성(어둠의 친화/사슬 해제)·잔영의 케이가·골드 스킬(브레멘/라사/툼스톤)·퍽 귀영보(첫 피격 불리점) | 정확한 값 |
| `test_job_berserker.py` | 버서커 혈기왕성(HP 비용)/혈십자(HP 단계)/폭주, 퍽 광기(프렌지 켜고 끄기·출혈·처치 회복, 사무치는 광기 HP 하한), 골드 스킬 새크리파이스/피폭발/블러드 러스트 | 정확한 값 |
| `test_dungeon_skills.py` | 던전 화면 스킬(던전스킬 - 유루캠 던전 캠핑, 봉절): 목록/사용/휴식당 횟수/전투·마을에서 막힘, 봉절 걸음·풀기·저장 | 정확한 값 |
| `test_combat_effects.py` | 상태이상/버프/디버프 전수, 반응스킬 전투 | 골든 |
| `test_battle_log.py` | 골든 로그의 화면 문장 기준(`battle_log_sentences`), 로그 `"종류"` 규칙(conftest가 모든 테스트에서 검사) | 골든 + 규칙 |
| `test_screen_api.py` | 화면용 gameflow 창구, 화면 -> system/controller 직접 호출 금지 | 값 + 규칙 |
| `test_controller_structure.py` | 창구에 구현 금지, 컨트롤러 `__all__` 완전성/이름 겹침/순환 금지, 창구가 쓰이는 이름을 다 내보냄 | 규칙 |
| `test_formula_parity.py` | 수식 평가기가 옛 eval 구현과 같은 값을 내는지(데이터 수식 전부 + 무작위 식), 안전 평가기의 거부 규칙 | 기준 구현과 비교 |
| `test_architecture.py` | combat 모듈 순환은 허용 묶음뿐, combat은 skill_system/skill을 안 부름, skill 패키지는 아래로만, 다른 모듈의 밑줄 이름 금지, 게임 코드에 eval/exec 금지 | 규칙 |
| `test_state_schema.py` | 캐릭터/전투 참가자/게임상태가 `state_schema.py` 표대로인지(칸이 빠지거나 이름이 바뀌면 실패), 불러올 때 핵심 칸 검사 | 규칙 |
| `test_data_integrity.py` | 데이터의 수식이 엄격하게 평가되는지, 몬스터/스킬/버프/던전/마을/상점의 키·이름 참조 | 규칙(허용 목록은 이유와 함께) |
| `test_scenario_*.py` | 풀 시나리오(실제 전투로 처음부터 끝까지, scenarios.md) | 요약 골든 + 값 |
| `test_auto_merge_gate.py`, `test_project_bridge.py` | 자동 병합 판정, 보드 브리지(명령 라벨·사건별 상태·STATUS.md) | 값 |
| `test_tools_console.py` | `tools/*.py` CLI가 cp1252 콘솔에서도 한글을 찍고 끝나는지(#200) | 값 |
| `test_imports.py`, `test_repo_hygiene.py` | 모듈 import, file_path.py, LF 줄끝, 비밀값 금지, 시나리오 장부 대조, 게이트(싼 검사 실패 시 멈춤, `--빠른`) | 규칙 |

- 공용 도우미는 `tests/support.py`(자동 전투, 강제 승리/패배, 경로 걷기, 결정적 성장, 골든 쓰기·골든 로그 모으기).
- 문장 골든(`battle_log_sentences`)은 `UPDATE_GOLDEN=1`일 때 세션 끝에 다시 쓴다(`conftest.pytest_sessionfinish`) - 갱신은 한 번이면 된다.
- 무작위는 전부 전역 `random`이라 `random.seed()`로 재현된다. 테스트마다 0으로 시작한다(`conftest.전역_난수_시드`). 골든은 시드를 고정해 만든다.
- **데이터를 추가/수정하면** `test_data_integrity.py`가 오타(수식 변수, 특성/버프 이름, 그림 파일, 던전 연결)를 잡는다. 런타임은 평가할 수 없는
  수식을 0으로, 정의 없는 특성을 건너뛰어 조용히 넘어가므로 이 테스트가 유일한 안전망이다. 새 변수/예외는 허용 목록에 이유와 함께 더한다.
- **새 스킬/몬스터/버프/상태이상 데이터를 추가하면** 전수 스윕이 자동으로 포함해 골든이
  바뀐다 - `UPDATE_GOLDEN=1`로 다시 쓰고 새 항목이 맞는지 diff를 읽는다.
