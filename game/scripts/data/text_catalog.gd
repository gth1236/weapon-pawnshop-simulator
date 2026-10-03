class_name TextCatalog
extends RefCounted

const CLASSES = {"WARRIOR": "전사", "MAGE": "마법사", "ROGUE": "도적", "ARCHER": "궁수", "GUNNER": "총잡이", "CLERIC": "성직자"}
const WEAPONS = {"one_handed_sword": "한손검", "greatsword": "대검", "spear": "창", "axe": "도끼", "staff": "지팡이", "wand": "마법봉", "grimoire": "마도서", "dagger": "단검", "throwing_weapon": "투척 무기", "bow": "활", "crossbow": "석궁", "gun": "총", "heavy_weapon": "중화기", "gauntlet": "건틀릿", "mace": "철퇴"}
const SECTIONS = {"normal_stat": "기본 능력치", "high_stat": "상위 능력치", "unique_property": "고유 속성", "reinforcement": "강화 상태", "refining": "제련", "amplification": "증폭", "stability": "안정도", "class_popularity": "시장 인기", "class_balance": "직업 밸런스"}
const GRADES = ["낮음", "무난", "좋음", "매우 좋음"]

static func judgement_options(section: String) -> Array:
	if section == "class_popularity":
		return ["인기 없음", "무난함", "인기 많음"]
	if section == "class_balance":
		return ["약함", "무난함", "강함"]
	if section == "unique_property":
		return ["없음", "있음", "높음"]
	if section == "amplification":
		return ["미적용", "0줄", "1줄 낮음", "1줄 높음", "2줄 낮음", "2줄 높음", "3줄 낮음", "3줄 높음"]
	return GRADES
const STATS = {"strength": "힘", "dexterity": "민첩", "intelligence": "지능", "luck": "행운", "divine_power": "신성력", "magic_power": "마법 공격력", "attack": "공격력", "critical_chance": "치명타 확률", "critical_damage": "치명타 피해", "armor_penetration": "방어 관통", "element_damage": "속성 피해"}

static func weapon(key: String) -> String:
	return WEAPONS.get(key, "무기")

static func stat(line: Dictionary) -> String:
	return "%s +%s%s" % [STATS.get(line.stat_id, "능력치"), str(line.actual_value).trim_suffix(".0"), "%" if line.display_unit == "PERCENT" else ""]

static func property_result(section: String, value) -> String:
	if value == null:
		return "???"
	if section == "refining":
		return "제련 +%d" % int(value)
	if section == "stability":
		return "안정도 %d%%" % int(value)
	var descriptions = {"PERFECT": "결함 없는 강화", "GOOD": "고르게 강화됨", "MIXED": "강화 편차 있음", "BAD": "강화부 손상", "UNENHANCED": "강화되지 않음", "UNAPPLIED": "증폭되지 않음", "ZERO_LINE": "증폭 적용 · 부여 능력치 없음", "ONE_LINE_LOW": "약한 증폭 1줄", "ONE_LINE_HIGH": "강한 증폭 1줄", "TWO_LINE_LOW": "약한 증폭 2줄", "TWO_LINE_HIGH": "강한 증폭 2줄", "THREE_LINE_LOW": "약한 증폭 3줄", "THREE_LINE_HIGH": "강한 증폭 3줄", "HIGH": "강한 고유 반응", "LOW": "약한 고유 반응", "NONE": "고유 반응 없음"}
	return descriptions.get(value, "확인되지 않은 결과")
