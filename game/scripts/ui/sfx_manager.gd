extends Node

signal played(cue: String)

const STREAMS = {
	"gold": preload("res://assets/sounds/gold.mp3"),
	"appraisal": preload("res://assets/sounds/appraisal.mp3"),
	"check": preload("res://assets/sounds/check.mp3"),
	"click": preload("res://assets/sounds/click.mp3"),
}
var volume_db = 0.0:
	set(value):
		volume_db = value
		if is_instance_valid(player):
			player.volume_db = value
var player: AudioStreamPlayer
var playback_serial = 0

func _ready() -> void:
	player = AudioStreamPlayer.new()
	add_child(player)
	player.volume_db = volume_db

func play(cue: String) -> void:
	if not STREAMS.has(cue):
		return
	# A single voice prevents unrelated UI effects piling up on rapid clicks.
	player.stop()
	player.stream = STREAMS[cue]
	player.play()
	playback_serial += 1
	played.emit(cue)

func perform(action: Callable) -> void:
	var before = playback_serial
	action.call()
	# Specialized feedback emitted by the action replaces the generic click.
	if playback_serial == before:
		play("click")

func _exit_tree() -> void:
	player.stop()
	player.stream = null
