"""화면 스모크 테스트 - 실제 Kivy 앱을 띄워 주요 화면 동작을 호출하고 스크린샷을 남긴다.

    pip install kivy                       # 한 번
    xvfb-run -a -s "-screen 0 1080x2340x24" python tools/ui_smoke.py [스크린샷폴더]  # 리눅스(화면 없음)
    python tools/ui_smoke.py [스크린샷폴더]                                        # Windows/맥(창이 뜬다)

tests/는 kivy 없이 gameflow 이하만 검사한다. 화면(game/screens) 코드를 바꿨다면 이것을
돌려 확인한다(CLAUDE.md 완료 기준 3). 레벨 10 파티를 만들어 다음을 실제로 호출한다:
파티 구성 이름칸(6자 제한), 상점 구매/판매 목록, 능력치 배분 팝업, 장비 교체 팝업/상세보기, 파티원 포션/주류 사용(취기 표시), 뒤로 키, 전투 화면 스킬 팝업과 스킬별 실제 타겟(4직업 전 스킬),
적 대상 선택 팝업(일반공격, 취소), 케라하 나이아스 소환(그림 없는 정령 칸), 전투 [아이템] 포션/버프포션/소환 아이템/주류(보조행동), 만취 아군 자동 행동, 적반복지정(썬더콜링) 선택 - 은신 대상 거부 포함, 행동 선택 팝업(쇼타임행동/일반행동), 도망(구속이면 막힘 팝업, 실패하면 턴 종료),
전투 종료 팝업(승리 전리품/없음, 도망, 패배)과 전투 보상(3칸 선택/빈칸 포기), 자동전투(켜기/중지/끝까지), 몬스터 크기 배율, 적 도망(황금 고블린),
기준 화면 틀(비율이 다른 창에서 검정 여백/터치/팝업 크기).
예외가 나면 종료코드 1.
스크린샷 기본 폴더: ui_smoke_shots/ (.gitignore에 들어 있다).
단계는 주제별로 tools/smoke/에 있다(party/town/battle/world/jobs/menu, 공통 도우미는 common).
새 단계는 주제에 맞는 모듈의 `_단계_*` 제너레이터로 넣고 아래 `_단계들`에서 부른다.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# common을 맨 먼저 불러야 kivy 창 설정(크기·밀도)이 창보다 먼저 정해진다.
from tools.smoke.common import 결과, 스크린샷폴더, 전직  # noqa: E402
import main  # noqa: E402 - 크래시 로그 훅/폰트 등록 등 앱 초기화를 그대로 쓴다
import json  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402
import tempfile  # noqa: E402
import traceback  # noqa: E402
from kivy.animation import Animation  # noqa: E402
from kivy.clock import Clock  # noqa: E402
import gameflow as gf  # noqa: E402
from game.system import rng  # noqa: E402
from game.system import save_system  # noqa: E402
from tests import support  # noqa: E402
from tools.smoke.party import 파티단계  # noqa: E402
from tools.smoke.town import 마을단계  # noqa: E402
from tools.smoke.battle import 전투단계  # noqa: E402
from tools.smoke.world import 세계단계  # noqa: E402
from tools.smoke.jobs import 직업스킬단계  # noqa: E402
from tools.smoke.menu import 메뉴단계  # noqa: E402


class 스모크앱(
    main.DnfMobileApp, 파티단계, 마을단계, 전투단계, 세계단계, 직업스킬단계, 메뉴단계
):
    def _세이브_폴더_준비(self):
        # 이 스모크는 세이브를 임시 폴더로 바꿔서 쓴다(실제 앱 데이터 폴더를 건드리지 않는다) -
        # 자동 저장이 마을에 올 때마다 쓰므로 실행 내내 임시 폴더를 쓴다
        폴더 = tempfile.mkdtemp(prefix="ui_smoke_saves_all_")
        save_system._폴더_재정의 = 폴더

    def on_start(self):
        self._단계 = self._단계들()
        Clock.schedule_once(self._다음, 1)

    def _다음(self, _dt):
        try:
            Clock.schedule_once(
                lambda _: self._애니메이션_기다리기(0), next(self._단계)
            )  # 단계 사이에 화면을 그리게 기다린다
        except StopIteration:
            self.stop()
        except Exception:  # noqa: BLE001
            결과["오류"] = traceback.format_exc()
            self.stop()

    def _애니메이션_기다리기(self, 기다린):
        """정해진 시간이 지나도 팝업 열기/닫기 애니메이션(kivy ModalView의 페이드)이 아직 돌면 끝날 때까지
        0.05초씩 더 기다린 뒤 다음 단계로(최대 5초). 느린 러너(CI Python 3.11)에서는 0.1초짜리 페이드가
        0.3초 뒤에도 안 끝나 닫히는 팝업이 남아 팝업 수를 2로 셌다."""
        if Animation._instances and 기다린 < 5:
            Clock.schedule_once(
                lambda _: self._애니메이션_기다리기(기다린 + 0.05), 0.05
            )
            return
        self._다음(0)

    def _단계들(self):
        rng.시드(0)  # 난수 흐름 분리 뒤 3은 행동 선택 단계에서 팝업이 남는다
        상태 = support.새게임(
            [("", "귀검사"), ("", "거너"), ("", "마법사"), ("", "프리스트")]
        )
        for c in 상태["파티"]["파티원"]:
            support.성장(상태, c, 10, 전직=전직[c["직업"]])
        gf.파티_최대치로_회복(상태)
        self.게임상태 = 상태
        매니저 = self.매니저

        yield from self._단계_파티생성(상태, 매니저)
        yield from self._단계_상점(상태, 매니저)
        yield from self._단계_파티관리_팝업(상태, 매니저)
        yield from self._단계_반응스킬_표시(상태, 매니저)
        전투 = yield from self._단계_장비_포션_뒤로키_전투팝업(상태, 매니저)
        yield from self._단계_전투종료_자동전투_주점(상태, 매니저, 전투)
        yield from self._단계_맵_타일(상태, 매니저)
        yield from self._단계_출입구_위(상태, 매니저)
        yield from self._단계_목록_스크롤(상태, 매니저)
        yield from self._단계_세이브(상태, 매니저)
        yield from self._단계_자동저장(상태, 매니저)
        yield from self._단계_설정(매니저)
        yield from self._단계_화면_배치(상태, 매니저)
        yield from self._단계_던전목록(상태, 매니저)
        yield from self._단계_던전_스킬(상태, 매니저)
        yield from self._단계_마을_전환스킬(상태, 매니저)
        yield from self._단계_마을_NPC(상태, 매니저)
        yield from self._단계_화면_틀(매니저)
        yield from self._단계_공격연출(상태, 매니저)
        yield from self._단계_감옥_대상팝업(상태, 매니저)
        yield from self._단계_골렘_소환(상태, 매니저)
        yield from self._단계_정령_소환(상태, 매니저)
        yield from self._단계_프렌드_실드(상태, 매니저)
        yield from self._단계_인형(상태, 매니저)
        yield from self._단계_란마(상태, 매니저)
        yield from self._단계_축염포(상태, 매니저)
        yield from self._단계_추적(상태, 매니저)
        yield from self._단계_연계_팝업(매니저)
        yield from self._단계_넨가드_채널링(매니저)
        yield from self._단계_합격(상태, 매니저)
        yield from self._단계_소지품(상태, 매니저)
        yield from self._단계_레테(상태, 매니저)
        yield from self._단계_스프레이_플라스크(상태, 매니저)
        yield from self._단계_도감_업적(상태, 매니저)
        yield from self._단계_메뉴(상태, 매니저)
        yield from self._단계_보스_귀환(상태, 매니저)


if __name__ == "__main__":
    # Windows에서 리디렉션된 출력은 cp1252라 한글 print가 죽는다 - 콘솔 인코딩과 상관없이 UTF-8로.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    스모크앱().run()
    for 단계 in 결과["단계"]:
        print("OK  ", 단계)
    if 결과["오류"]:
        print(결과["오류"])
    print(
        json.dumps(
            {"스크린샷": 스크린샷폴더, "성공": 결과["오류"] is None}, ensure_ascii=False
        )
    )
    sys.exit(1 if 결과["오류"] else 0)
