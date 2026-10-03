Godot button/dialogue panel UI resource

Main recommended texture:
- button_panel_9patch.png

Recommended Godot nodes:
- NinePatchRect (resizable panel)
- Button + StyleBoxTexture or TextureButton (button skin)

Recommended patch margins:
- Left: 90
- Right: 90
- Top: 70
- Bottom: 70

Godot 4.6.1 setup:
1. Add a NinePatchRect and assign button_panel_9patch.png as the Texture.
2. Set Patch Margin Left/Right/Top/Bottom to the values above.
3. Enable Draw Center.
4. If used as a button, add a Button node and use this texture for the normal state.
5. Put a Label on top for the button text.

Texture import tips:
- Filter: On
- Mipmaps: Off
- Repeat: Disabled

The 9 individual PNG slices are also included for manual composition.
All filenames are English-only.
