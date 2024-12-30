# dn-model-import

**dn-model-import** is a plugin for Blender 3D that allows you to import 3D models
and animations from Dragon Nest game into the editor.
It works with formats such as: skin data (`.skn`), models (`.msh`) and animations (`.ani`, `.anim`).
The plugin cannot export loaded models.

## How to import DN model
To import a model, just choose the `.skn` file from the import menu. Make sure the `.msh` file is located in the same directory. You can also import `.msh` directly without materials.

## How to import DN animation
1. Import model into Blender
2. Make armature active
3. Import `.anim` animation

After successful import, animations will be available in the Action Editor.

## TODO:
* Export support
* Vertex color import support
* Collisions import support
* SKN version 11 import support
* Materials properties support

## Requirements
* Blender (2.80 and above)
