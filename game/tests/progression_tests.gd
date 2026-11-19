extends Node
## Scratch: print what the previews say.

func _ready() -> void:
	Audio.unlocked = true
	GameState.reset_new_game()
	GameState.hp = 42
	var before := var_to_bytes(GameState.to_dict())
	print(Preview.ref_fighter())
	print(Preview.sheet())
	for id in ["pancakes", "coffee", "iron_stew", "tonic", "vitamin_pack", "smelling_salts"]:
		print(id, ": ", PreviewText.food(id))
	for s in GameState.STATS:
		print(PreviewText.stat_point(s))
	for line in Content.upgrades:
		print(line, ": ", PreviewText.workbench(line))
	for fam in Content.weapon_families:
		print(fam, ": ", PreviewText.mastery(fam))
	for sid in Content.skills:
		print(sid, ": ", PreviewText.technique_input(sid), " | ", PreviewText.technique(sid))
	print("unchanged: ", before == var_to_bytes(GameState.to_dict()), " audio ", Audio.unlocked, " blocked ", GameState.is_blocking_signals())
	get_tree().quit(0)
