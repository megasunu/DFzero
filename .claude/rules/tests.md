---
paths:
  - "tests/**"
  - "tools/check.py"
---

## 테스트 지도

파일별로 무엇을 지키는지는 `docs/test-map.md`에 있다. 통째로 읽지 말고 `grep -n "<주제어>" docs/test-map.md`로 찾는다.
새 테스트 파일을 만들거나 주제가 넓어지면 그 행을 같은 병합 요청에서 고친다.

## 폴더

`tests/` 바로 아래는 공용(`conftest.py`·`support.py`·`scenario.py`, `golden/`)과 어느 묶음에도 안 드는 시험이다. 주제 폴더:
`combat/`(전투 규칙·효과·자동전투) `items/`(아이템·제작·상점) `jobs/`(직업별) `monsters/`(몬스터·종족·챔피언)
`scenarios/`(풀 시나리오 s1~) `structure/`(계층·데이터 무결성·저장소 규칙) `devtools/`(tools/ 도구). 새 파일은 맞는 폴더에 둔다.
`import support`는 pytest가 `tests/conftest.py`를 불러오며 `tests/`를 경로에 넣으므로 어느 폴더에서나 된다. 저장소 뿌리는 `Path(__file__).parents[2]`다.

## 규칙

- 공용 도우미는 `tests/support.py`(자동 전투, 강제 승리/패배, 경로 걷기, 결정적 성장, 골든 쓰기·골든 로그 모으기, 전투 단위 테스트의
  `주사위고정`·`시험_전투`·`추가행동_전장`,
  `핵심_로그`·`수치_변화`·`참가자_변화`·`뒤_라운드_기록` - 스윕 골든에는 적의 공격 줄과 바뀌지 않은 수치·참가자를 싣지 않고,
  뒤 라운드는 남는 효과를 받은 참가자 것만 싣는다).
- 테스트 파일은 한 주제만 갖고 다른 테스트 파일을 불러오지 않는다 - 그 파일과 `support.py`만 읽으면 되게. 둘 이상이 쓰는 도우미는 `support.py`로 옮긴다.
- 문장 골든(`battle_log_sentences`)은 `UPDATE_GOLDEN=1`일 때 세션 끝에 다시 쓴다(`conftest.pytest_sessionfinish`) - 갱신은 한 번이면 된다.
- 무작위는 전부 `game/system/rng.py`의 용도별 흐름(주사위/확률/대상/던전/보상/칭호/대화)이고 `rng.시드()` 하나로 재현된다(전역 `random`도 같이 - 테스트의
  플레이어 정책용). 테스트마다 0으로 시작한다(`conftest.전역_난수_시드`). 풀 시나리오의 고르기(퍽·보상 칸·살 물건 등)는 목록 맨 위가 아니라
  `scenario.선택`으로 하고 `scenario.시드`·`scenario.성장`을 쓴다(`docs/scenarios.md`, #725). 굴림을 바꿔치기할 때는 그 흐름을 바꾼다(`monkeypatch.setattr(rng.주사위, "randint", ...)`).
- 골든 갱신은 `python tools/check.py --골든` 한 번(서식 고침 + 직렬 갱신 + `golden_diff.py` 요약, 출력은 실패 줄과 끝 줄만).
