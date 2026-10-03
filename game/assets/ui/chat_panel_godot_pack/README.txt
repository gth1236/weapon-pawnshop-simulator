Godot DialoguePanel UI resource

Main recommended texture:
- dialogue_panel_9patch.png

Recommended Godot node:
- NinePatchRect

Patch margins:
- Left: 120
- Right: 120
- Top: 235
- Bottom: 115

Godot 4.6.1 setup:
1. Add a NinePatchRect.
2. Assign dialogue_panel_9patch.png to Texture.
3. Set Patch Margin Left/Right/Top/Bottom to the values above.
4. Set Draw Center = On.
5. Keep texture filtering enabled for this painted UI style; mipmaps can stay disabled for 2D UI.
6. Put MarginContainer + RichTextLabel inside for text.

The 9 individual PNG files are also included if you prefer manual composition.
All filenames are English-only.
