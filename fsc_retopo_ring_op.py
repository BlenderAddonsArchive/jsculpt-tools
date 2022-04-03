import math
import blf
import bmesh
import bpy

from bpy.props import *

from . utils.fsc_bool_util import select_active

from . types.line_container import LineContainer

from . types.vertices import *
from . utils.fsc_view_utils import *
from . utils.fsc_select_mode_utils import *

from . fsc_draw_base_op import *

# Draw mode operator
class FSC_OT_Retopo_Ring_Operator(FSC_OT_Draw_Base_Operator):
    bl_idname = "object.fsc_retopo_ring"
    bl_label = "Retopo Ring Operator"
    bl_description = "Retopo Ring Operator"
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}

    def __init__(self):
        self.draw_handle_2d = None
        self.draw_handle_3d = None
        self.points = LineContainer()
        self.points_ring = VertexContainer()

    def modal(self, context, event):
        if context.area:
            context.area.tag_redraw()

        result = "PASS_THROUGH"
                              
        if event.type == "ESC" and event.value == "PRESS":
            return self.finish()

        if event.type == "RET" and event.value == "PRESS":
            return self.finish()

        # The mouse is moved
        if event.type == "MOUSEMOVE":
            mouse_pos_2d = (event.mouse_region_x, event.mouse_region_y)
            mouse_pos_3d = get_3d_vertex(context, mouse_pos_2d)

            if mouse_pos_3d and self.points.is_initialized():
                self.points.set_vertex(1, mouse_pos_2d, mouse_pos_3d)
            
        # Left mouse button is released
        if event.value == "RELEASE" and event.type == "LEFTMOUSE":
            pass

        # Left mouse button is pressed
        if event.value == "PRESS" and event.type == "LEFTMOUSE":

            mouse_pos_2d = (event.mouse_region_x, event.mouse_region_y)

            mouse_pos_3d = get_3d_vertex(context, mouse_pos_2d)
            if mouse_pos_3d:

                if not self.points.is_initialized() and event.ctrl:
                    self.points.append(mouse_pos_2d, mouse_pos_3d)
                    self.points.append(mouse_pos_2d, mouse_pos_3d.copy())
                    result = "RUNNING_MODAL"

                elif self.points.is_initialized() :
                    self.project_loop_onto_object(context)
                    self.to_mesh(context)
                    self.points.reset()
                    self.points_ring.reset()

                    result = "RUNNING_MODAL"

        return { result }

    def to_mesh(self, context):
      
      mesh = bpy.data.meshes.new("Retopo_Ring_Mesh")
      obj  = bpy.data.objects.new("Retopo_Ring_Object", mesh)

      bpy.context.scene.collection.objects.link(obj)

      make_active(obj)

      to_object()

      bpy.ops.object.select_all(action='DESELECT')

      bpy.context.view_layer.objects.active = obj
      obj.select_set(state=True)

      # Create a bmesh and add the vertices
      # added by mouse clicks
      bm = bmesh.new()
      bm.from_mesh(mesh) 

      for v in self.points_ring.get_vertices().copy():
          bm.verts.new(v)

      bm.verts.index_update()
      bm.faces.new(bm.verts)

      bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

      bm.to_mesh(mesh)
      bm.free()

      to_edit()
      
      bpy.ops.mesh.delete(type='ONLY_FACE')

      select_mesh()


    def get_center_object(self, context):
        
        # 1. Get center of line (line_center)     
        # 2. raycast from line_center onto selected object (line_center_hit1)
        # 3. raycast from line_center_hit1 in the same direction (line_center_hit2)
        # 4. get center of line_center_hit1 and line_center_hit2 (center_object)

        origin, direction = get_origin_and_direction( self.points.get_center_2d(), context)

        _, line_center_hit1 = scene_raycast(direction, origin, context)

        _, line_center_hit2 = scene_raycast(direction, line_center_hit1 + (direction * 0.01), context)

        return get_center_vectors(line_center_hit1, line_center_hit2), direction

    def project_loop_onto_object(self, context):

        center_object, direction = self.get_center_object(context)

        # Draw cirle around center_object, diameter = line_length
        v1_n = (self.points.get_end_point() - self.points.get_start_point()).normalized()

        t = 0
        r = self.points.get_length() / 2

        circle_points = []

        while t < 2 * math.pi:
            circle_points.append(center_object + r * math.cos(t) * v1_n + r * math.sin(t) * direction)
            t += 2 * math.pi / context.scene.loop_cuts

        # raycast all points of the circle in direction to center_object and collect hit_points
        for cp in circle_points:
            hit, hit_vertex = scene_raycast(-(cp - center_object).normalized(), cp, context)
            if hit:
                self.points_ring.append(hit_vertex)

	  # Draw handler to paint in pixels
    def draw_callback_2d(self, op, context):

        region = context.region
        xt = int(region.width / 2.0)

        # Draw text for draw mode
        blf.size(0, 22, 72)
        blf.color(0, 1, 1, 1, 1)

        blf.size(1, 16, 72)
        blf.color(1, 1, 1, 1, 1)

        title = "- Retopo Ring Mesh -"
        desc = "Ctrl + Click: Add points, Enter: Create, Ctrl + Enter: Create closed"

        blf.position(0, xt - blf.dimensions(0, title)[0] / 2, 45, 0)
        blf.draw(0, title)

        blf.position(1, xt - blf.dimensions(1, desc)[0] / 2, 20, 0)
        blf.draw(1, desc)