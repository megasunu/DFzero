# =====================
# 게임 흐름 컨트롤러
# =====================
# Kivy 화면(game/screens/)과 game/system, game/data 사이를 잇는다. 화면은
# 이 파일의 함수만 부르고, 로직/데이터 파일을 직접 조합하는 일은 여기서
# 한다.
#
# - 5직업(귀검사/격투가/거너/마법사/프리스트)은 "_직업_데이터파일"(직업 -> 데이터 파일명)
#   한 줄씩으로 등록하고, 그 표로 "직업_레지스트리"를 만든다.
#   1차 전직(레벨 6~)은 "전직_레지스트리"에 등록한다.
# - 파티는 최대 4명(party_system.파티_최대인원). combat 패키지/
#   skill_system.py는 참가자 리스트를 순회하므로 인원수와 무관하게 동작한다.
# - 마을과 던전은 "마을파일_레지스트리"/"던전_레지스트리"에 등록한다.
#   던전의 "#" 연결지역은 마을이면 그 마을로, 다른 던전이면 "진입좌표"로
#   그 던전에 들어간다(연결지역_처리). 보스 첫 클리어 시
#   진행도["클리어한던전"]에 기록해 헨돈마이어(로리엔 안쪽 클리어 필요)가
#   열린다.
# - 상점 카탈로그는 _상점_카탈로그_생성()이 만들고 게임상태["상점카탈로그"]
#   에 캐싱한다. 무기 탭은 5직업 무기를 전부 합치고, 나머지 부위는
#   eq_02~04 데이터를 그대로 쓴다.
# - NPC/창고는 아직 로직이 없어 마을 화면에 버튼만 두고 비활성 상태다.
# - 세이브/불러오기는 save_system.py를 쓴다. 슬롯은 3개, 저장 대상은
#   "파티"와 "진행도", "소지품" 전부다. save_system.py는 {"레벨","파티",
#   "소지품"} 모양의 "플레이어" 딕셔너리를 기대하므로, 게임상태를 그
#   모양으로 감싸는 플레이어뷰() 헬퍼를 통해 넘긴다.
# - 장비데이터모음(전투용 {캐릭터명: {슬롯: 아이템데이터}})은 장착한 모든
#   부위(무기/방어구/악세서리/특수장비)를 상점 카탈로그에서 이름으로 찾아
#   담는다. 그래서 전투 AC에 방어구가 반영된다.
# - 전투_시작()에는 몬스터 특성(monster_ability.py + 공용 특성)/캐릭터
#   특성(job_ability_XX.py 전부)/몬스터 칭호(monster_title.py)/방어구
#   세트(eq_02_armor_set.py) 정의 테이블을 함께 넘긴다.
#
# 캐릭터는 레벨 1로 시작한다.
#
# 몬스터 최대HP/AC 수식 평가: 몬스터 데이터(monster_race_*.py)의 "최대HP"/"AC"는
# None이고, 몬스터 "역할군"에 따른 "레벨×(6+건강보정치)" 같은 수식 문자열
# (monster_format.py 역할군공식)을 쓴다. combat 패키지의
# 적_참가자_생성()/최종AC()가 이 수식을 실제로 평가하려면 몬스터의
# "레벨"/"차수"가 필요한데, 몬스터 데이터 자신에는 없고(항상 None)
# 던전 맵의 인카운트/오브젝트 데이터 쪽에 있다(monster_format.py 설명
# 참고) - 그래서 이 파일의 전투_시작()이 그 값을 몬스터 원본 데이터
# 사본에 덮어써서 넘긴다(_몬스터원본목록_생성 참고).
#
# [N5] 구현은 game/controller/ctl_*.py(주제별 모듈)로 나눴다. 이 파일은 화면/테스트가 쓰는 이름을
# 그대로 다시 내보내는 창구다 - `import gameflow as gf; gf.새_게임_시작(...)`이 그대로 동작한다.
# 새 컨트롤러 함수는 주제에 맞는 ctl_*.py에 두고(__all__에 넣는다), 여기는 건드리지 않는다.
# 계층: screens -> gameflow(창구) -> game/controller -> game/system -> game/data.
#
# 모듈 안내(위에서 아래로만 부른다):
#   ctl_registry  데이터 배선 - 몬스터/직업/전직/던전/마을 레지스트리, 전투용 특성 정의 테이블
#   ctl_party     캐릭터/파티/게임상태 만들기, 능력치/HP/MP 조회, 이름 자르기
#   ctl_session   게임 시작, 세이브/불러오기      ctl_profile  모험단 프로필(초상화)
#   ctl_town      마을 이동/휴식                  ctl_shop     상점 구매/판매/해체
#   ctl_equip     장비 교체                       ctl_levelup  파티관리 레벨업(퍽/전직/스킬강화)
#   ctl_battle    전투 시작/조회/행동/턴 넘기기   ctl_skills   스킬 습득
#                 + [설정] 값과 기기 설정 파일(settings_system)
#   ctl_battle_log 전투 로그 dict -> 화면 문장(로그_문장들)
#   ctl_autobattle [자동전투] 한 턴, 전력전투 스킬 고르기(ctl_battle 다음)
#   ctl_dungeon   던전 이동/상호작용(인카운트)    ctl_potion   회복포션 사용
#   ctl_rewards   전투 보상/결과 정리             ctl_charview 파티원 화면용 조회(읽기 전용)
#   ctl_tavern    주점(영입/대기/합류/추방)
#   ctl_collection 도감(분류/목록/등록 현황)       ctl_achievement 업적(목록/보상 받기)
#   ctl_profession 마을 [전문직업](봉인해제/봉인변환 - 장비해체는 ctl_shop 함수)

from game.controller.ctl_registry import *  # noqa: F403
from game.controller.ctl_party import *  # noqa: F403
from game.controller.ctl_session import *  # noqa: F403
from game.controller.ctl_profile import *  # noqa: F403
from game.controller.ctl_town import *  # noqa: F403
from game.controller.ctl_shop import *  # noqa: F403
from game.controller.ctl_equip import *  # noqa: F403
from game.controller.ctl_battle import *  # noqa: F403
from game.controller.ctl_battle_log import *  # noqa: F403
from game.controller.ctl_autobattle import *  # noqa: F403
from game.controller.ctl_dungeon import *  # noqa: F403
from game.controller.ctl_potion import *  # noqa: F403
from game.controller.ctl_rewards import *  # noqa: F403
from game.controller.ctl_levelup import *  # noqa: F403
from game.controller.ctl_charview import *  # noqa: F403
from game.controller.ctl_tavern import *  # noqa: F403
from game.controller.ctl_skills import *  # noqa: F403
from game.controller.ctl_collection import *  # noqa: F403
from game.controller.ctl_achievement import *  # noqa: F403
from game.controller.ctl_profession import *  # noqa: F403
from game.controller.ctl_npc import *  # noqa: F403
