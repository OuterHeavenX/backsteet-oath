extends Node
## Scratch: print what the previews say.

func _ready() -> void:
	Audio.unlocked = true
	GameState.reset_new_game()
	GameState.hp = 42
	print("hp a ", GameState.hp)
	print(Preview.ref_fighter())
	print("hp b ", GameState.hp)
	var b := Preview.Bench.new()
	print("hp c ", GameState.hp, " ", b._plain)
	b.close()
	print("hp d ", GameState.hp)
	print(Preview.sheet())
	print("hp e ", GameState.hp)
	get_tree().quit(0)
