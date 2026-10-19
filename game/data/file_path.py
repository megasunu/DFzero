# =====================
# 파일 경로 레지스트리
# =====================
# 프로젝트의 모든 .py 모듈이 실제로 어느 패키지 경로에 있는지 기록해둔
# 참고용 딕셔너리다. 새 파일을 추가하면 이 목록에도 항목을 추가한다.
#
# import 문을 쓸 때는 여기 적힌 dotted 경로를 그대로 쓰면 된다.
# 예) skill_system.py에서 buff.py를 쓰려면
#     from game.data.buff import buff
# 처럼, 이 딕셔너리 값에서 마지막 조각(모듈명)을 뺀 나머지를 "from" 뒤에,
# 마지막 조각(모듈명)을 "import" 뒤에 쓰면 된다.
#
# 키: 파일명 (확장자 제외)
# 값: 전체 dotted 경로 (game.으로 시작, 모듈명까지 포함)
#
# 주의: 이 딕셔너리는 .py 모듈의 import 경로만 관리한다. 폰트/이미지
# 같은 비-코드 리소스 파일의 위치는 맨 아래 "에셋 파일 위치" 절 참고.

파일경로 = {
    # game/data/ 최상위
    "file_path": "game.data.file_path",
    # game/data/job_skill/
    "job_skill_010m_ghost_swordsman": "game.data.job_skill.job_skill_010m_ghost_swordsman",
    "job_skill_011m_weapon_master": "game.data.job_skill.job_skill_011m_weapon_master",
    "job_skill_020f_fighter": "game.data.job_skill.job_skill_020f_fighter",
    "job_skill_030f_gunner": "game.data.job_skill.job_skill_030f_gunner",
    "job_skill_022f_striker": "game.data.job_skill.job_skill_022f_striker",
    "job_skill_031f_ranger": "game.data.job_skill.job_skill_031f_ranger",
    "job_skill_040f_mage": "game.data.job_skill.job_skill_040f_mage",
    "job_skill_041f_elemental_master": "game.data.job_skill.job_skill_041f_elemental_master",
    "job_skill_050f_priest": "game.data.job_skill.job_skill_050f_priest",
    "job_skill_051f_crusader": "game.data.job_skill.job_skill_051f_crusader",
    "job_skill_format": "game.data.job_skill.job_skill_format",
    "job_skill_0000": "game.data.job_skill.job_skill_0000",
    # game/data/job_level/
    "job_level_000x_style": "game.data.job_level.job_level_000x_style",
    "job_level_010m_ghost_swordsman": "game.data.job_level.job_level_010m_ghost_swordsman",
    "job_level_011m_weapon_master": "game.data.job_level.job_level_011m_weapon_master",
    "job_level_020f_fighter": "game.data.job_level.job_level_020f_fighter",
    "job_level_022f_striker": "game.data.job_level.job_level_022f_striker",
    "job_level_030f_gunner": "game.data.job_level.job_level_030f_gunner",
    "job_level_031f_ranger": "game.data.job_level.job_level_031f_ranger",
    "job_level_040f_mage": "game.data.job_level.job_level_040f_mage",
    "job_level_041f_elemental_master": "game.data.job_level.job_level_041f_elemental_master",
    "job_level_050f_priest": "game.data.job_level.job_level_050f_priest",
    "job_level_051f_crusader": "game.data.job_level.job_level_051f_crusader",
    "job_level_format": "game.data.job_level.job_level_format",
    # game/data/perks/
    "perks_class_0000": "game.data.perks.perks_class_0000",
    "perks_class_010m": "game.data.perks.perks_class_010m",
    "perks_class_020f": "game.data.perks.perks_class_020f",
    "perks_class_030f": "game.data.perks.perks_class_030f",
    "perks_class_040f": "game.data.perks.perks_class_040f",
    "perks_class_050f": "game.data.perks.perks_class_050f",
    "perks_class_format": "game.data.perks.perks_class_format",
    # game/data/buff/
    "buff": "game.data.buff.buff",
    "debuff": "game.data.buff.debuff",
    "skill_effects": "game.data.buff.skill_effects",
    "status_effects": "game.data.buff.status_effects",
    "summon_00": "game.data.buff.summon_00",
    # game/data/ability/
    "job_ability_010m": "game.data.ability.job_ability_010m",
    "job_ability_020f": "game.data.ability.job_ability_020f",
    "job_ability_030f": "game.data.ability.job_ability_030f",
    "job_ability_040f": "game.data.ability.job_ability_040f",
    "job_ability_050f": "game.data.ability.job_ability_050f",
    "job_ability_format": "game.data.ability.job_ability_format",
    "job_ability_0000": "game.data.ability.job_ability_0000",
    # game/data/monster/
    "monster_defaults": "game.data.monster.monster_defaults",
    "monster_race_goblin": "game.data.monster.monster_race_goblin",
    "monster_race_tau": "game.data.monster.monster_race_tau",
    "monster_race_lugaru": "game.data.monster.monster_race_lugaru",
    "monster_race_human": "game.data.monster.monster_race_human",
    "monster_race_zombie": "game.data.monster.monster_race_zombie",
    "monster_race_dragon": "game.data.monster.monster_race_dragon",
    "monster_race_spacefish": "game.data.monster.monster_race_spacefish",
    "monster_format": "game.data.monster.monster_format",
    "monster_ability": "game.data.monster.monster_ability",
    "monster_title": "game.data.monster.monster_title",
    "monster_drop": "game.data.monster.monster_drop",
    # game/data/equipment/
    "eq_01_weapon_010": "game.data.equipment.eq_01_weapon_010",
    "eq_01_weapon_020": "game.data.equipment.eq_01_weapon_020",
    "eq_01_weapon_format": "game.data.equipment.eq_01_weapon_format",
    "eq_01_weapon_030": "game.data.equipment.eq_01_weapon_030",
    "eq_01_weapon_040": "game.data.equipment.eq_01_weapon_040",
    "eq_01_weapon_050": "game.data.equipment.eq_01_weapon_050",
    "eq_00_magic_seal": "game.data.equipment.eq_00_magic_seal",
    "eq_03_accessory_08_bracelet": "game.data.equipment.eq_03_accessory_08_bracelet",
    "eq_02_armor_01_top": "game.data.equipment.eq_02_armor_01_top",
    "eq_02_armor_03_shoulder": "game.data.equipment.eq_02_armor_03_shoulder",
    "eq_02_armor_04_belt": "game.data.equipment.eq_02_armor_04_belt",
    "eq_02_armor_format": "game.data.equipment.eq_02_armor_format",
    "eq_02_armor_set": "game.data.equipment.eq_02_armor_set",
    "eq_02_armor_05_shoes": "game.data.equipment.eq_02_armor_05_shoes",
    "eq_03_accessory_06_necklace": "game.data.equipment.eq_03_accessory_06_necklace",
    "eq_03_accessory_07_ring": "game.data.equipment.eq_03_accessory_07_ring",
    "eq_03_accessory_set": "game.data.equipment.eq_03_accessory_set",
    "eq_04_special_11_earring": "game.data.equipment.eq_04_special_11_earring",
    "eq_04_special_10_magicstone": "game.data.equipment.eq_04_special_10_magicstone",
    "eq_04_special_09_subequipment": "game.data.equipment.eq_04_special_09_subequipment",
    "eq_04_special_set": "game.data.equipment.eq_04_special_set",
    "eq_02_armor_02_bottom": "game.data.equipment.eq_02_armor_02_bottom",
    # game/data/item/
    "item_potion": "game.data.item.item_potion",
    "item_consumable": "game.data.item.item_consumable",
    "item_food": "game.data.item.item_food",
    "item_doll": "game.data.item.item_doll",
    "item_materials": "game.data.item.item_materials",
    "item_quest": "game.data.item.item_quest",
    # game/data/collection/
    "collection_monster": "game.data.collection.collection_monster",
    # game/data/achievement/
    "achievement_list": "game.data.achievement.achievement_list",
    # game/data/character/
    "character_format": "game.data.character.character_format",
    "player_format": "game.data.character.player_format",
    # game/data/dungeon/
    "dungeon_format": "game.data.dungeon.dungeon_format",
    "dungeon_utils": "game.data.dungeon.dungeon_utils",
    "dungeon_01A_D01_Lorien": "game.data.dungeon.dungeon_01A_D01_Lorien",
    "dungeon_01A_D02_Hollow_Lorien": "game.data.dungeon.dungeon_01A_D02_Hollow_Lorien",
    "dungeon_01A_D03_mirkwood": "game.data.dungeon.dungeon_01A_D03_mirkwood",
    "dungeon_01A_D04_Hollow_mirkwood": "game.data.dungeon.dungeon_01A_D04_Hollow_mirkwood",
    "dungeon_01A_D05_thunderland": "game.data.dungeon.dungeon_01A_D05_thunderland",
    "dungeon_01A_D06_poison_thunderland": "game.data.dungeon.dungeon_01A_D06_poison_thunderland",
    "dungeon_01A_D07_frost_mirkwood": "game.data.dungeon.dungeon_01A_D07_frost_mirkwood",
    "dungeon_01A_D08_grakquarak": "game.data.dungeon.dungeon_01A_D08_grakquarak",
    "dungeon_01A_D09_blazing_grakquarak": "game.data.dungeon.dungeon_01A_D09_blazing_grakquarak",
    "dungeon_01A_D10_shadow_thunderland": "game.data.dungeon.dungeon_01A_D10_shadow_thunderland",
    "dungeon_02A_D11_amon_lower": "game.data.dungeon.dungeon_02A_D11_amon_lower",
    "dungeon_02A_D12_amon_upper": "game.data.dungeon.dungeon_02A_D12_amon_upper",
    "dungeon_02A_D13_sephiroth_lower": "game.data.dungeon.dungeon_02A_D13_sephiroth_lower",
    "dungeon_02A_D14_sephiroth_upper": "game.data.dungeon.dungeon_02A_D14_sephiroth_upper",
    "dungeon_02A_D15_middleocean_shallow": "game.data.dungeon.dungeon_02A_D15_middleocean_shallow",
    "dungeon_02A_D16_middleocean_deep": "game.data.dungeon.dungeon_02A_D16_middleocean_deep",
    # game/data/town/
    "town_01A_T01_Elvengard": "game.data.town.town_01A_T01_Elvengard",
    "town_01A_T02_hendonmyre": "game.data.town.town_01A_T02_hendonmyre",
    "town_02A_T03_westcoast": "game.data.town.town_02A_T03_westcoast",
    "town_format": "game.data.town.town_format",
    # game/system/
    "equipment_system": "game.system.equipment_system",
    "dice_utils": "game.system.dice_utils",
    "effect_engine": "game.system.effect_engine",
    "monster_ai": "game.system.monster_ai",
    "dungeon_system": "game.system.dungeon_system",
    "party_system": "game.system.party_system",
    "player_system": "game.system.player_system",
    "save_system": "game.system.save_system",
    "settings_system": "game.system.settings_system",
    "shop_system": "game.system.shop_system",
    "loot_system": "game.system.loot_system",
    "quest_system": "game.system.quest_system",
    "town_system": "game.system.town_system",
    "character_data_system": "game.system.character_data_system",
    "character_creation_system": "game.system.character_creation_system",
    "character_levelup_system": "game.system.character_levelup_system",
    # game/system/combat/ (전투 시스템 패키지 - R4에서 옛 combat_system.py를 나눔)
    "core": "game.system.combat.core",
    "formula": "game.system.combat.formula",
    "participants": "game.system.combat.participants",
    "traits": "game.system.combat.traits",
    "status": "game.system.combat.status",
    "stats": "game.system.combat.stats",
    "resources": "game.system.combat.resources",
    "damage": "game.system.combat.damage",
    "attacks": "game.system.combat.attacks",
    "monster_actions": "game.system.combat.monster_actions",
    "reactions": "game.system.combat.reactions",
    "flow": "game.system.combat.flow",
    "skill_system": "game.system.skill_system",
    # game/system/skill/ (스킬 실행 엔진 패키지 - skill_system.py가 재수출하는 구현)
    "skill_grant": "game.system.skill.skill_grant",
    "skill_usage": "game.system.skill.skill_usage",
    "skill_target": "game.system.skill.skill_target",
    "skill_apply": "game.system.skill.skill_apply",
    "skill_attack": "game.system.skill.skill_attack",
    "skill_run": "game.system.skill.skill_run",
    "skill_learn_system": "game.system.skill_learn_system",
    "lodge_system": "game.system.lodge_system",
    "dismantle_system": "game.system.dismantle_system",
    "drink_system": "game.system.drink_system",
    "potion_system": "game.system.potion_system",
    "state_schema": "game.system.state_schema",
    "collection_system": "game.system.collection_system",
    "achievement_system": "game.system.achievement_system",
    "magic_seal_system": "game.system.magic_seal_system",
    # game/controller/ (화면 <-> 로직/데이터 컨트롤러 - gameflow.py가 재수출하는 구현, N5)
    "ctl_registry": "game.controller.ctl_registry",
    "ctl_party": "game.controller.ctl_party",
    "ctl_session": "game.controller.ctl_session",
    "ctl_profile": "game.controller.ctl_profile",
    "ctl_town": "game.controller.ctl_town",
    "ctl_shop": "game.controller.ctl_shop",
    "ctl_equip": "game.controller.ctl_equip",
    "ctl_battle": "game.controller.ctl_battle",
    "ctl_battle_log": "game.controller.ctl_battle_log",
    "ctl_autobattle": "game.controller.ctl_autobattle",
    "ctl_dungeon": "game.controller.ctl_dungeon",
    "ctl_potion": "game.controller.ctl_potion",
    "ctl_rewards": "game.controller.ctl_rewards",
    "ctl_levelup": "game.controller.ctl_levelup",
    "ctl_charview": "game.controller.ctl_charview",
    "ctl_tavern": "game.controller.ctl_tavern",
    "ctl_skills": "game.controller.ctl_skills",
    "ctl_collection": "game.controller.ctl_collection",
    "ctl_achievement": "game.controller.ctl_achievement",
    "ctl_profession": "game.controller.ctl_profession",
    # game/screens/ (Kivy 화면)
    "screens_common": "game.screens.screens_common",
    "screens_menu": "game.screens.screens_menu",
    "screens_town": "game.screens.screens_town",
    "screens_dungeon": "game.screens.screens_dungeon",
    "screens_battle": "game.screens.screens_battle",
    "screens_party": "game.screens.screens_party",
    "screens_collection": "game.screens.screens_collection",
}

# =====================
# 참고: 에셋(폰트/이미지 등 비-코드 리소스) 파일 위치
# =====================
# 실제 프로젝트 기준. 최상위 루트는 코딩연습/ 폴더이고, 실행 진입점
# (main.py 등)과 빌드 설정은 루트에, 게임 패키지는 루트 아래 game/에 있다.
# game은 UI/플랫폼과 무관한 순수 로직+데이터 패키지 성격을 유지하되,
# 폰트·이미지처럼 화면 표시에만 쓰이는 리소스는 코드/데이터와 구분해서
# game 바로 아래의 assets/ 폴더에 담는다 (game과 형제가 아니라 game 안에 있음).
# (이 파일들은 .py 모듈이 아니므로 위 파일경로 딕셔너리에는 넣지 않는다)
#
# 코딩연습/
# ├── main.py
# ├── gameflow.py          (창구 - game/controller/ctl_*.py를 재수출)
# ├── buildozer.spec
# └── game/
#     ├── data/            (직업/몬스터/맵 등 게임 콘텐츠 데이터)
#     ├── system/          (전투/스킬 등 로직)
#     ├── controller/      (화면 <-> 로직/데이터 컨트롤러 19개 모듈 - ctl_battle/shop/party ...)
#     ├── screens/         (Kivy 화면 7개 - screens_common/menu/town/
#     │                     dungeon/battle/party/collection.py, main.py가 가져온다)
#     ├── saves/           (세이브 파일)
#     ├── assets/
#     │   ├── attack/     공격 연출 그림 (투명 배경, 전투 화면이 대상 위에 0.5초 띄운다)
#     │   │                  asset_attack_{모양}_{색}.webp  20장 (2026-10-14 교체)
#     │   │                    모양: slash 참격 / blunt 타격 / pierce 관통 / magic 마법(역장도)
#     │   │                    색  : none 무속성 / fire 화 / water 수 / light 명 / dark 암
#     │   │                  asset_attack_stuck.webp  공격 실패 글자 "Stuck!!" (967x240)
#     │   ├── font/       NanumGothic-Diet.ttf (다이어트 폰트 1개, 볼드 없음)
#     │   ├── character/  캐릭터 SD 이미지 (asset_sd_character_*.webp)
#     │   ├── dungeon/    던전 타일 이미지 (asset_tile_*.webp)
#     │   │                  asset_tile_grass.webp   풀밭 (8x8)
#     │   │                  asset_tile_dirt.webp    흙길 (8x8)
#     │   │                  asset_tile_forest.webp  숲 (8x8, 아직 미사용)
#     │   │                  asset_tile_tree.webp    나무 (8x16, 세로 2칸)
#     │   │                  asset_tile_gate_grandflores.webp 게이트 - 그란플로리스 (8x8, 한 칸, 공용)
#     │   │                  asset_tile_gate_skycastle.webp 게이트 - 하늘성 (64x64, 한 칸, 투명 배경)
#     │   │                  asset_tile_prison_seria.webp 감옥 - 세리아 (96x96, 오브젝트 "타일크기" 2)
#     │   │                  asset_tile_prison_lorien.webp 감옥 - 로리안 (128x128, 투명 배경, 아몬 하층 보스 "타일크기" 2)
#     │   │                  asset_tile_emerald.webp 하늘성 탑 발판 - 에메랄드빛 돌 (8x8, 하늘성 탑 4곳의 "타일")
#     │   │                  asset_tile_skyyellow.webp 하늘 - 노을빛 (8x8, 하늘성 탑 4곳의 "타일")
#     │   │                  asset_tile_sky.webp     하늘 - 푸른빛, 노을과 같은 무늬 (8x8, 아직 미사용)
#     │   │                  asset_tile_skycastlewall.webp 하늘성 벽 - 노란 벽돌 (8x8, 하늘성 탑 4곳의 "타일")
#     │   ├── monster/     몬스터 이미지 (asset_monster_*.webp)
#     │   └── town/       마을 배경 그림 (asset_town_*.webp)
#     │                      asset_town_elvengard.webp   엘븐가드 (1323x1189, 숲 마을)
#     │                      asset_town_hendonmyre.webp  헨돈마이어 (720x342)
#     │                      asset_town_westcoast.webp   웨스트코스트 (1323x1189, 항구)
#     └── __init__.py
#
# 주의: assets/font/ 안에는 폰트 파일(.ttf/.otf)만 둔다. 문서·노트
# 파일은 에셋이 아니므로 저장소 최상위 docs/에 둔다.
#
# 폰트 관련 배경(한글 깨짐 문제 및 등록 코드)은
# docs/mobile_apk_build_notes.md 참고.
