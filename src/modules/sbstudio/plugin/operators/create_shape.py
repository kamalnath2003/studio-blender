import bpy
from bpy.types import Operator
from bpy.props import EnumProperty
from bpy.utils import register_class

__all__ = ("CreateShapeOperator",)

class CreateShapeOperator(Operator):
    bl_idname = "object.create_shape"
    bl_label = "Create Shape"

    shape_type: EnumProperty(
        items=[('CUBE', 'Cube', 'Create a cube'),
               ('SPHERE', 'Sphere', 'Create a sphere')],
        name="Shape Type",
        description="Select the type of shape to create",
        default='CUBE'
    )

    def execute(self, context):
        if self.shape_type == 'CUBE':
            bpy.ops.mesh.primitive_cube_add(size=2)
        elif self.shape_type == 'SPHERE':
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1)
        return {'FINISHED'}

def register():
    register_class(CreateShapeOperator)

def unregister():
    pass

if __name__ == "__main__":
    register()
