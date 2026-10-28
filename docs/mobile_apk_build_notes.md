# 모바일 APK 빌드 노트

2026-10-06에 현재 방식(GitHub Actions)에 맞게 다시 썼다. 예전 판(2026-09-16, Colab 기준)은 `git log -- docs/mobile_apk_build_notes.md`로
볼 수 있다. 값이 맞는지는 `buildozer.spec`과 `.github/workflows/build-apk.yml`이 정답이다.

## 1. 빌드 방법 (GitHub Actions)

워크플로 `.github/workflows/build-apk.yml`("Build APK")이 디버그 APK를 만든다.

- **언제 도나:** `v*` 태그를 push할 때만(2026-10-10부터). **게임 코드 push/PR이나 이 파일의 변경으로는 돌지 않는다.**
  그래서 게임 코드 변경이 빌드를 깨도 PR 단계에서는 모른다 - 큰 기능이 병합될 때마다 Claude가 지금 릴리스할지 사용자에게 묻고, 지금이면
  Claude가 버전을 올리는 PR을 열고, 병합한 뒤 사용자가 GitHub 웹에서 릴리스를 게시해 태그를 만든다(사용자는 PC가 없고 이 세션은 태그를 push할 수 없다).
  태그가 `v<spec의 version>`이 아니면 첫 단계에서 실패한다. 전체 절차와 CHANGELOG 규칙은 `.claude/rules/build-and-save.md`.
- **무엇을 하나:** JDK 17 + Python 3.11 + buildozer/cython 설치 -> `yes | buildozer -v android debug`(SDK 라이선스 자동 동의) -> APK 업로드.
- **산출물:** 워크플로 아티팩트 `dnfmobile-apk`와 태그 이름의 릴리스(`v0.1.1` 등, 본문은 그때의 `CHANGELOG.md`, 같은 태그를 다시 돌리면 APK만 덮어쓴다).
  폰에서는 릴리스의 `*.apk`를 받아 설치한다. 옛 `latest-apk` 릴리스는 더 갱신되지 않는다.
  파일 이름 예: `dnfmobile-0.1.1-arm64-v8a-debug.apk`.
- **캐시:** `~/.buildozer`(SDK/NDK)를 `buildozer-<OS>-<android.* 줄 해시>` 키로 캐시한다. 태그 실행이 저장한 캐시는 그 태그에서만 보여
  다음 릴리스가 못 쓰므로(GitHub 규칙을 이 세션에서 문서로 확인하지는 못했다) 저장은 `main-branch`에서 `buildozer.spec`이 바뀔 때 도는
  `warm-cache.yml`이 하고(릴리스는 만들지 않는다), 태그 빌드는 불러오기만 한다. 7일 안 쓰인 캐시는 GitHub가 지우는데 정기 갱신은 하지 않기로
  했으므로, 오래 릴리스하지 않으면 다음 빌드가 SDK/NDK를 새로 받을 수 있다.
  `version`, 주석, `source.*`를 바꿔도 키는 그대로다. **`android.*` 줄을 바꾸면** 키가 바뀌어 SDK/NDK를 새로 받는다(수십 분) - 꼭 필요할 때만, 묶어서 바꾼다.
- 제한 시간 120분. 첫 빌드(캐시 없음)가 가장 오래 걸린다.

## 2. 로컬/Colab에서 빌드하기 (대안)

클라우드 코딩 세션(이 저장소를 편집하는 샌드박스)은 네트워크가 막혀 SDK/NDK를 받을 수 없어 APK를 못 만든다. 직접 빌드가 필요하면:

1. `pip install buildozer cython`
2. 저장소 최상위에서 `buildozer android debug` (결과: `bin/*.apk`)
3. 처음에 Android SDK 라이선스 질문(`Accept? (y/N):`)이 나오면 `yes | buildozer android debug`로 돌리거나 `android.accept_sdk_license = True`(이미 spec에 있음)에 맡긴다.
4. **root로 실행하면**(Colab 등) `[buildozer]` 섹션의 `warn_on_root = 0`이 있어야 "Buildozer is running as root!" 질문에서 멈추지 않는다(이미 spec에 있고, `[app]`이 아니라 `[buildozer]`에 둬야 인식된다).

## 3. 한글이 네모(□)로 깨지는 문제

- **원인:** Kivy 기본 폰트 별칭 `Roboto`에 한글 글리프가 없다.
- **수정:** `main.py`가 화면을 import하기 **전에** `LabelBase.register(name="Roboto", fn_regular=<폰트>)`로 별칭 자체를 나눔고딕으로 덮어쓴다.
  위젯마다 `font_name`을 지정하지 않아도 모든 Label/Button에 적용된다. import 순서가 중요하다.
- **폰트 파일:** `game/assets/font/NanumGothic-Diet.ttf` 1개(약 1.3MB, 렌더링에 불필요한 테이블만 뺀 나눔고딕 Regular). 볼드 파일은 없고,
  Kivy가 볼드 스타일에도 이 파일을 대신 쓴다.
- **`buildozer.spec`의 `source.include_exts`에 `ttf`가 있어야** APK에 폰트가 들어간다(빠지면 로컬에서는 되고 APK에서만 다시 깨진다).
- Kivy `Window`/`App` 없이 `CoreLabel(...).refresh()`만 부르면 이 헤드리스 환경에서 세그폴트가 난다(폰트와 무관). 검증은 `App` 컨텍스트 안에서(`tools/ui_smoke.py`).

## 4. `buildozer.spec` 주석의 "빌드 노트 N절" 대응표

`buildozer.spec` 주석은 예전 판의 절 번호를 가리켰다. 2026-10-28(#182)에 주석을 이 문서의 절 번호로 고쳤고, 옛 번호와의 대응은 다음과 같다.

| spec 주석 | 내용 | 지금 어디 |
|---|---|---|
| "빌드 노트 2절 4번" | root 실행 시 `warn_on_root = 0`을 `[buildozer]`에 | 이 문서 2절 4번 |
| "빌드 노트 11절" | `android.api = 33` - `HIDDeviceManager.java`의 `BLUETOOTH_CONNECT` 심볼 오류를 피하려고 | spec 주석이 근거의 전부다(원문 11절은 사라짐) |
| "빌드 노트 13절" | 크래시 로그를 Download 폴더에 저장하는 `main.py` 안전장치와 그 권한 | 이 문서 5절 |


## 5. 크래시 로그와 권한 (확인 안 됨)

- `main.py`는 처리 못 한 예외를 `/storage/emulated/0/Download/dnf_crash_log.txt`에 쓴다(`sys.excepthook`). 앱이 Kivy 화면을 띄우기도 전에 죽는 경우를 잡으려는 임시 장치다.
  이벤트 루프 안의 예외는 `ExceptionHandler`가 잡아 오류 팝업(복사 버튼 포함)으로 보여 준다.
- `android.permissions = WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE`는 그 로그용이다. **API 33에서 이 권한이 실제로 효과가 있는지, 로그 파일이 써지는지는 실기기로 확인하지 못했다**
  (`docs/architecture_review.md` W-7). 확인되면 로그 위치를 앱 전용 폴더로 옮기고 권한을 뺀다.

## 6. 앱 ID와 세이브

- `package.domain = org.test`는 원래 값을 몰라 buildozer 기본값을 쓴 것이다. 예전 APK와 다르면 폰에 별도 앱으로 설치되고 세이브가 이어지지 않는다. 확인 안 됨.
- 세이브는 예전에 `game/saves/slot_N.json`(앱 소스 폴더)에 저장돼 앱을 업데이트하면 사라질 수 있었다. 2026-10-06부터 앱 데이터 폴더(Kivy `user_data_dir`/`saves/`)에 저장하고, 옛 위치의 세이브는 처음 실행할 때 한 번 복사해 온다(`save_system.세이브_폴더_설정`, `main.py`). **실기기에서 업데이트 후 세이브가 남는지는 확인하지 못했다.**

## 7. 포함 범위

APK에는 `source.include_exts`에 맞는 파일이 `source.dir = .` 아래에서 들어간다. `tests/`, `bin/`, `원본/`은 `source.exclude_dirs`로 뺀다.
`tools/`의 `.py`도 같이 들어가지만 무해하다(빼려면 spec 수정, 캐시는 유지된다).
