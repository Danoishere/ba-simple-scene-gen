import bpy
import numpy as np
from random import sample
from bpy_extras.mesh_utils import triangle_random_points
import uuid
import tempfile, os
import cv2
import zipfile
import msgpack
import msgpack_numpy as m
import json
from bpy_extras.object_utils import world_to_camera_view
m.patch()

steps = 36
radius = 1.2
height = 0.4

colors = {
    "red" : (1.0, 0.0, 0.0, 1.0),
    "green" : (0.0, 1.0, 0.0, 1.0),
    "blue" : (0.0, 0.0, 1.0, 1.0),
    "yellow" : (1.0, 1.0, 0.0, 1.0),
    "white" : (1.0, 1.0, 1.0, 1.0),
    "grey" : (0.15, 0.15, 0.15, 1.0),
    "purple" : (1.0, 0.0, 1.0, 1.0)
    }

process_id = str(uuid.uuid1())


def clear_placed_objects():
    cs_col = bpy.data.collections['PlacedObjects']
    objs = bpy.data.objects
    for obj in cs_col.all_objects:
        objs.remove(objs[obj.name], do_unlink=True)


def get_random_available_objects():
    ou_col = bpy.data.collections['AvailableObjects']
    col = []
    for obj in ou_col.objects:
        if obj.parent is None:
            col.append(obj)
    ou = np.random.choice(col)
    return ou

def get_random_color():
    keys = list(colors.keys())
    key = np.random.choice(keys)
    print(key)
    return key, colors[key]


def place_available_objects():

    ground = bpy.data.objects['Ground']
    center = bpy.data.objects['Center']
    scene = bpy.data.collections['PlacedObjects']

    me = ground.data
    me.calc_loop_triangles()
    points = []
    lights_per_meter = 0.2
    
    points = []
    for tri in me.loop_triangles:
        points += triangle_random_points(int(1000 * tri.area), [tri])
    points = sample(points, 100)

    selected_points = []
    for point in points:
        found_close_point = False
        for selected_point in selected_points:
            if (selected_point - point).length < np.sqrt(0.22**2 + 0.22**2):
                found_close_point = True
        
        if not found_close_point:
            selected_points.append(point)
        
    placed_objects = {}
    for point in selected_points:
        obj_orig = get_random_available_objects()
        color_name, color_rgb = get_random_color()
        
        obj_name = obj_orig.name
        obj_key = obj_name + '-' + color_name
        
        print(obj_key)
        if obj_key not in placed_objects:
            print("was not inside")
            obj_copy = obj_orig.copy()
            obj_copy.data = obj_copy.data.copy()
            obj_copy.location = point
            scene.objects.link(obj_copy)
            
            obj_copy.parent = center
            placed_objects[obj_key] = {}
            placed_objects[obj_key]["color-name"] = color_name
            placed_objects[obj_key]["color-rgb"] = color_rgb
            placed_objects[obj_key]["blender-obj-name"] = obj_copy.name
            # placed_objects[obj_key]["pos"] = obj_copy.matrix_world.translation
            
            set_color(obj_copy, color_rgb)
            
            # Maybe place object on top of other 
            if np.random.random() < 0.5:
                top_obj_orig = get_random_available_objects()
                top_color_name, top_color_rgb = get_random_color()
                
                top_obj_name = top_obj_orig.name
                top_obj_key = top_obj_name + '-' + top_color_name
                
                if top_obj_key not in placed_objects:
                    top_obj_copy = top_obj_orig.copy()
                    top_obj_copy.data = top_obj_copy.data.copy()
                    top_obj_copy.location = point
                    top_obj_copy.location[2] += 0.2
                    scene.objects.link(top_obj_copy)
                    
                    top_obj_copy.parent = center
                    placed_objects[top_obj_key] = {}
                    placed_objects[top_obj_key]["color-name"] = top_color_name
                    placed_objects[top_obj_key]["color-rgb"] = top_color_rgb
                    # placed_objects[top_obj_key]["pos"] = top_obj_copy.matrix_world.translation                 
                    placed_objects[top_obj_key]["is_above"] = obj_key
                    placed_objects[top_obj_key]["blender-obj-name"] = top_obj_copy.name
                    placed_objects[obj_key]["is_below"] = top_obj_key
                    
                    set_color(top_obj_copy, top_color_rgb)
            
            
        if len(placed_objects) >= 5:
            break
        
    return placed_objects

    
def set_color(obj, color):
    # get the material
    mat = obj.data.materials[0].copy()
    obj.data.materials[0] = mat
    # get the nodes
    nodes = mat.node_tree.nodes
    diffuse = nodes.get("Principled BSDF").inputs[0].default_value = color
    
# not in use
def place_obstacle():
    obst = bpy.data.objects['Obstacle']
    obst.scale = (
            0.1 + np.random.random() *2,
            0.6 + np.random.random() *1.3,
            0.4 + np.random.random() * 2)


def set_random_color_to_floor():
    col = (np.random.random(), np.random.random(),np.random.random(), 1.0)
    set_color(bpy.data.objects['Floor'], col)
    
def set_random_color_to_obstacle():
    col = (np.random.random(), np.random.random(),np.random.random(), 1.0)
    set_color(bpy.data.objects['Obstacle'], col)
    
def set_random_color_to_sky():
    col = (np.random.random(), np.random.random(),np.random.random(), 1.0)
    bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = col
    
def randomly_rotate_scene():
    center = bpy.data.objects['Center']
    center.rotation_euler = (0,0,np.random.random()*np.pi*2)
    
def randomly_rotate_sun():
    sun = bpy.data.objects['Sun']
    rot_range = np.pi - 0.5
    sun.rotation_euler = (
        np.random.random()*rot_range - rot_range/2, 
        np.random.random()*rot_range - rot_range/2, 
        np.random.random()*np.pi*2)

def render_rgb_img(w,h):
    path = tempfile.gettempdir() + os.path.sep + process_id + "-rgb-blender-render.png"
    bpy.context.scene.render.filepath = path
    bpy.context.scene.render.resolution_x = w
    bpy.context.scene.render.resolution_y = h
    bpy.ops.render.render(write_still = True)
   
    rgb = cv2.imread(path)
    rgb = cv2.cvtColor(rgb, cv2.COLOR_BGR2RGB)
    return rgb

def render_depth_img(w,h):
    depth = np.asarray(bpy.data.images["Viewer Node"].pixels)
    depth = np.reshape(depth, (h,w,4))
    depth = depth[:,:,0]
    depth = np.flipud(depth)
    depth[depth == 65504.0] =  np.nan
   
    return depth


def numpy_to_file(array, out_filename):
    enc_data = msgpack.packb(array, default=m.encode)
    with open(out_filename, 'wb') as outfile:
        msgpack.pack(enc_data, outfile)

def set_init_cam_pos():
    cam_base = bpy.data.objects['CamBase']
    cam_base.location = (2, 0, 0)

    cam = bpy.data.objects['Camera']
    random_angle = ((np.random.random() - 0.5)*np.pi)/10
    cam.rotation_euler = (np.pi/2 + random_angle, 0, 0)

    frame = 0
    
def update_obj_positions(objs):
    bpy.context.view_layer.update()
    # Update all obj positions after rotation
    for obj_key in objs:
        obj_name = objs[obj_key]["blender-obj-name"]
        obj = bpy.data.objects[obj_name]
        print(obj_key, obj_name, "pos:", obj.matrix_world.translation)
        objs[obj_key]["pos"] = tuple(obj.matrix_world.translation)
   
def make_cam_rotation(arc):
    # np.pi + np.pi/2
    frame = 0
    cam_base = bpy.data.objects['CamBase']
    for x in np.linspace(0,arc,steps):
        frame += 1
        cam_base.location = (np.cos(x)*radius, np.sin(x)*radius, 0)
        cam_base.rotation_euler[2] = x + np.pi/2
        cam_base.keyframe_insert(data_path='location', frame=frame)
        cam_base.keyframe_insert(data_path='rotation_euler', frame=frame)
     
def get_relative_position_of_obj(target):
    e_from = bpy.data.objects["CamBase"]
    mat = e_from.matrix_world.copy()
    mat.invert()
    pos = mat @ target.matrix_world.translation
    # pos.z = target.location.z
    return pos


def render_frames(objs):
    rgb_imgs = []
    depth_imgs = []
    cam_base_mat = []
    cam = bpy.data.objects['Camera']
    cam_base = bpy.data.objects['CamBase']

    ss_obj_pos = []
    for frame in range(1, steps + 1):
        print(frame, "/", steps)
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        
        rgb = render_rgb_img(w,h)
        depth = render_depth_img(w, h)
        
        rgb_imgs.append(rgb)
        depth_imgs.append(depth)

        cam_base_mat.append(np.asarray(cam_base.matrix_world).tolist())

        ss_objs = {}
        for obj in objs:
            ss_objs[obj] = {}
            blender_obj = bpy.data.objects[objs[obj]["blender-obj-name"]]
            x,y,dist = world_to_camera_view(bpy.context.scene, cam, blender_obj.matrix_world.translation)
            ss_objs[obj]["screen_x"] = x
            ss_objs[obj]["screen_y"] = y
            ss_objs[obj]["screen_dist"] = dist
            

        ss_obj_pos.append(ss_objs)
            
        
    rgb_imgs = np.asarray(rgb_imgs)
    depth_imgs = np.asarray(depth_imgs)
    
    return rgb_imgs, depth_imgs, cam_base_mat, ss_obj_pos


w,h = 128, 128
training_data = "D:/training-data-very-simple-ss/"
tmp_path = tempfile.gettempdir() + os.path.sep

for episode in range(100000):
    clear_placed_objects()
    objs = place_available_objects()
    set_init_cam_pos()
    
    update_obj_positions(objs)
    
    arc = np.pi*2
    make_cam_rotation(arc)    

    scene_id = str(uuid.uuid1())
    rgb_imgs, depth_imgs, cam_base_mat, ss_objs = render_frames(objs)

    scene = {}      
    scene["objects"] = objs
    scene["cam_base_matricies"] = cam_base_mat
    scene["ss_objs"] = ss_objs
    print(scene)

    files = []
    img_path = scene_id + "-combined.npz"
    np.savez_compressed(training_data + img_path, rgb=rgb_imgs, depth=depth_imgs)
    files.append(img_path)


    scene_filename = scene_id + '-scene.json'
    files.append(scene_filename)
    with open(training_data + scene_filename, 'w') as outfile:
        json.dump(scene, outfile)

    zip_filename = scene_id + '.zip'
    zipObj = zipfile.ZipFile(training_data + zip_filename, 'w', zipfile.ZIP_DEFLATED)

    for file in files:
        zipObj.write(training_data + file, arcname=file)
       
    zipObj.close()

    for file in files:
        os.remove(training_data + file)

