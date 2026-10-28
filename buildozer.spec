[app]

# 앱 이름 / 패키지 정보
# 기존 APK 파일명(dnfmobile-0.1-arm64-v8a-debug.apk) 기준으로 맞춤.
# package.domain은 원본 값을 알 수 없어 buildozer 기본값(org.test)을 씀 -
# 예전 값과 다르면 폰에 별도 앱으로 설치되고 기존 세이브가 이어지지 않는다.
title = dnfmobile
package.name = dnfmobile
package.domain = org.test
version = 0.1.2

# 소스 위치 (최상위에 main.py / gameflow.py / game/ 가 바로 있음)
source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,ttf,otf,json,kv,atlas,txt
# 원본: 몬스터 그림을 떼어낼 때 쓴 원본 그림 보관용 - APK에 넣지 않는다
source.exclude_dirs = tests, bin, venv, .buildozer, __pycache__, 원본

# 필요 패키지
requirements = python3,kivy

# 화면
orientation = portrait
fullscreen = 0

# 안드로이드
# api 33: HIDDeviceManager.java의 BLUETOOTH_CONNECT 심볼 오류 방지(근거는 이 주석뿐 - 빌드 노트 4절 대응표)
android.api = 33
android.minapi = 21
android.archs = arm64-v8a
android.accept_sdk_license = True
# 크래시 로그를 Download 폴더에 저장(main.py 안전장치, 빌드 노트 5절)
android.permissions = WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
android.allow_backup = True


[buildozer]

log_level = 2
# Colab은 항상 root로 실행되므로 반드시 [buildozer] 섹션에 둔다(빌드 노트 2절 4번)
warn_on_root = 0
