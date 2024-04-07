import bpy
import time

from bpy.props import EnumProperty, StringProperty

from sbstudio.plugin.model.formation import add_objects_to_formation, create_formation

from sbstudio.plugin.utils import propose_name

from .base import FormationOperator
from .update_formation import (
    collect_objects_and_points_for_formation_update,
    get_options_for_formation_update,
    propose_mode_for_formation_update,
)
from sbstudio.plugin.operators import (

    AppendFormationToStoryboardOperator,
)

__all__ = ("CreateFormationOperator",)


class CreateFormationOperator(FormationOperator):
    """Creates a new formation in the Formations collection, optionally filling
    it from the selection.
    """

    bl_idname = "skybrush.create_formation"
    bl_label = "Create Formation"
    bl_description = "Creates a new formation in the Formations collection."
    bl_options = {"REGISTER", "UNDO"}

    name = StringProperty(name="Name", description="Name of the new formation")
    contents = EnumProperty(
        name="Initialize with",
        items=get_options_for_formation_update,
    )

    works_with_no_selected_formation = True

    @classmethod
    def poll(cls, context):

        if not FormationOperator.poll(context):
            return True

        formations = context.scene.skybrush.formations
        storyboard = getattr(context.scene.skybrush, "storyboard", None)
        if storyboard:
            return (
                not storyboard.entries
                or storyboard.entries[-1].formation != formations.selected
            )
        else:
            return True
            

    def invoke(self, context, event):
        if context.mode == "EDIT_MESH":
            # In edit mode, the name of the formation should be the same as
            # the name of the object we are editing
            self.name = propose_name(context.object.name, for_collection=True)
        else:
            # In object mode, the name of the formation should be the same as
            # the name of the selected object if there is a single selection
            if len(context.selected_objects) == 1:
                name_proposal = context.selected_objects[0].name
            else:
                name_proposal = "Formation {}"
            self.name = propose_name(name_proposal, for_collection=True)
        self.contents = propose_mode_for_formation_update(context)
        return context.window_manager.invoke_props_dialog(self)


    def execute_on_formation(self, formation, context):
    #     original_context = bpy.context.copy()

    # # Set the context for the operator
    #     bpy.context.area.type = 'SEQUENCE_EDITOR'

    # # Call the append operator to add the newly created formation to the storyboard
    #     bpy.ops.skybrush.append_formation_to_storyboard()

    # # Restore the original context
    #     bpy.context = original_context

         
        storyboard = getattr(context.scene.skybrush, "storyboard", None)
        if not storyboard or (
            storyboard.entries and storyboard.entries[-1].formation == formation
        ):
            return {"CANCELLED"}

        safety_check = getattr(context.scene.skybrush, "safety_check", None)
        settings = getattr(context.scene.skybrush, "settings", None)

        last_formation = storyboard.last_formation
        last_frame = storyboard.frame_end
        time.sleep(2)

        entry = storyboard.add_new_entry(
            name=formation.name, select=True, formation=formation
        )
        assert entry is not None

        fps = context.scene.render.fps

        # Set up safety check parameters
        safety_kwds = {
            "max_velocity_xy": safety_check.velocity_xy_warning_threshold
            if safety_check
            else 8,
            "max_velocity_z": safety_check.velocity_z_warning_threshold
            if safety_check
            else 2,
            "max_velocity_z_up": safety_check.velocity_z_warning_threshold_up_or_none
            if safety_check
            else None,
            "max_acceleration": settings.max_acceleration if settings else 4,
        }

        with create_position_evaluator() as get_positions_of:
            if last_formation is not None:
                source = get_world_coordinates_of_markers_from_formation(
                    last_formation, frame=last_frame
                )
                source = [tuple(coord) for coord in source]
            else:
                drones = Collections.find_drones().objects
                source = get_positions_of(drones, frame=last_frame)

            target = get_world_coordinates_of_markers_from_formation(
                formation, frame=entry.frame_start
            )
            target = [tuple(coord) for coord in target]
        try:
            plan = get_api().plan_transition(source, target, **safety_kwds)
        except Exception:
            raise
            self.report(
                {"ERROR"},
                "Error while invoking transition planner on the Skybrush Studio server",
            )
            return {"CANCELLED"}

        # To get nicer-looking frame counts, we round the end of the
        # transition up to the next whole second. We need to take into account
        # whether the scene starts from frame 1 or 0 or anything else
        # stored in storyboard.frame_start, though.
        new_start = ceil(
            last_frame + (plan.total_duration if plan.durations else 10) * fps
        )
        diff = ceil((new_start - storyboard.frame_start) / fps) * fps
        entry.frame_start = storyboard.frame_start + diff
        self.append_to_storyboard(formation, context)

    def append_to_storyboard(self, formation, context):
        # Retrieve necessary data from the context or other sources
        storyboard = getattr(context.scene.skybrush, "storyboard", None)
        safety_check = getattr(context.scene.skybrush, "safety_check", None)
        settings = getattr(context.scene.skybrush, "settings", None)
        
        # Check if the storyboard exists and if the formation is different from the last one
        if not storyboard or (
            storyboard.entries and storyboard.entries[-1].formation == formation
        ):
            return {"CANCELLED"}

        # Add the formation to the storyboard
        entry = storyboard.add_new_entry(
            name=formation.name, select=True, formation=formation
        )
        assert entry is not None

        # Retrieve necessary data for transition planning
        last_formation = storyboard.last_formation
        last_frame = storyboard.frame_end
        fps = context.scene.render.fps

        # Set up safety check parameters
        safety_kwds = {
            "max_velocity_xy": safety_check.velocity_xy_warning_threshold
            if safety_check
            else 8,
            "max_velocity_z": safety_check.velocity_z_warning_threshold
            if safety_check
            else 2,
            "max_velocity_z_up": safety_check.velocity_z_warning_threshold_up_or_none
            if safety_check
            else None,
            "max_acceleration": settings.max_acceleration if settings else 4,
        }

        # Get world coordinates of markers for transition planning
        with create_position_evaluator() as get_positions_of:
            if last_formation is not None:
                source = get_world_coordinates_of_markers_from_formation(
                    last_formation, frame=last_frame
                )
                source = [tuple(coord) for coord in source]
            else:
                drones = Collections.find_drones().objects
                source = get_positions_of(drones, frame=last_frame)

            target = get_world_coordinates_of_markers_from_formation(
                formation, frame=entry.frame_start
            )
            target = [tuple(coord) for coord in target]

        # Plan transition and update entry frame start
        try:
            plan = get_api().plan_transition(source, target, **safety_kwds)
        except Exception:
            raise
            self.report(
                {"ERROR"},
                "Error while invoking transition planner on the Skybrush Studio server",
            )
            return {"CANCELLED"}

        # Round the end of the transition up to the next whole second
        new_start = ceil(
            last_frame + (plan.total_duration if plan.durations else 10) * fps
        )
        diff = ceil((new_start - storyboard.frame_start) / fps) * fps
        entry.frame_start = storyboard.frame_start + diff

        return {"FINISHED"}

