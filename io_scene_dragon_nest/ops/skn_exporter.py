import os

from .common import get_active_armature_object
from .msh_exporter import MshExporter
from ..gui import gui
from ..types import common
from ..types.skn import SKN, Material, MaterialProperty, MatPropType


class SknExporter:

    def export_data(self, context, options):
        self.skn.file_type = "Eternity Engine Skin File 0.1"
        self.skn.version = options["version"]

        for material in options["materials"]:
            properties = []

            if material.dragon_nest.enable_colors:
                properties.append(MaterialProperty(
                    name="g_MaterialAmbient",
                    type=MatPropType.VECTOR,
                    value=common.Vector4D(*material.dragon_nest.material_ambient),
                ))

                properties.append(MaterialProperty(
                    name="g_MaterialDiffuse",
                    type=MatPropType.VECTOR,
                    value=common.Vector4D(*material.dragon_nest.material_diffuse),
                ))

            if material.dragon_nest.emissive_texture:
                properties.append(MaterialProperty(
                    name="g_EmissivePower",
                    type=MatPropType.FLOAT,
                    value=material.dragon_nest.emissive_power,
                ))

                properties.append(MaterialProperty(
                    name="g_EmissivePowerRange",
                    type=MatPropType.FLOAT,
                    value=material.dragon_nest.emissive_power_range,
                ))

                properties.append(MaterialProperty(
                    name="g_EmissiveAniSpeed",
                    type=MatPropType.FLOAT,
                    value=material.dragon_nest.emissive_ani_speed,
                ))

            if material.dragon_nest.diffuse_texture:
                properties.append(MaterialProperty(
                    name="g_DiffuseTex",
                    type=MatPropType.TEXTURE,
                    value=material.dragon_nest.diffuse_texture,
                ))

            if material.dragon_nest.emissive_texture:
                properties.append(MaterialProperty(
                    name="g_EmissiveTex",
                    type=MatPropType.TEXTURE,
                    value=material.dragon_nest.emissive_texture,
                ))

            if material.dragon_nest.mask_texture:
                properties.append(MaterialProperty(
                    name="g_MaskTex",
                    type=MatPropType.TEXTURE,
                    value=material.dragon_nest.mask_texture,
                ))

            for extra_prop in material.dragon_nest.extra:
                prop_name = extra_prop.name
                prop_type = int(extra_prop.type)

                if prop_type == MatPropType.INT:
                    prop_value = extra_prop.integer_value
                elif prop_type == MatPropType.FLOAT:
                    prop_value = extra_prop.float_value
                elif prop_type == MatPropType.VECTOR:
                    prop_value = common.Vector4D(*extra_prop.vector_value)
                elif prop_type == MatPropType.TEXTURE:
                    prop_value = extra_prop.string_value
                else:
                    prop_value = None

                properties.append(MaterialProperty(
                    name=prop_name,
                    type=prop_type,
                    value=prop_value,
                ))

            self.skn.materials.append(Material(
                name=material.name,
                effect=material.dragon_nest.effect,
                alpha=material.dragon_nest.alpha_value,
                alpha_blend=material.dragon_nest.enable_alpha_blend,
                properties=properties,
            ))

    def __init__(self):
        self.skn = SKN()


def save(context, filepath, options):
    arm_obj = get_active_armature_object(context)
    if not arm_obj:
        context.window_manager.popup_menu(gui.need_armature_to_export, title='Error', icon='ERROR')
        return

    msh_options = {
        "version": options["msh_version"],
        "armature_object": arm_obj,
        "apply_root_transform": options["apply_root_transform"],
    }

    msh_exporter = MshExporter()
    msh_exporter.export_data(context, msh_options)

    materials = []
    for mesh_obj in msh_exporter.mesh_objects:
        mesh_materials = []
        for material_slot in mesh_obj.material_slots:
            if material_slot.material:
                mesh_materials.append(material_slot.material)

        if len(mesh_materials) == 0:
            context.window_manager.popup_menu(gui.missing_material, title=f"Error ({mesh_obj.name})", icon='ERROR')
            return

        if len(mesh_materials) > 1:
            context.window_manager.popup_menu(gui.too_many_materials, title=f"Error ({mesh_obj.name})", icon='ERROR')
            return

        materials.append(mesh_materials[0])

    skn_options = {
        "version": options["skn_version"],
        "materials": materials
    }

    directory = os.path.dirname(filepath)

    msh_name = os.path.splitext(options["msh_name"])[0] or os.path.splitext(os.path.basename(filepath))[0]
    msh_name += '.msh'

    skn_exporter = SknExporter()
    skn_exporter.skn.name = msh_name
    skn_exporter.export_data(context, skn_options)

    skn_exporter.skn.save_file(filepath)
    msh_exporter.msh.save_file(os.path.join(directory, msh_name))

    return skn_exporter
