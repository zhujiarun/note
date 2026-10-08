"""
Stereographic Projection（立体投影/保角投影）
将下半球全景纹理映射到平面圆盘上（保持局部角度和形状）

使用方法：
1. 在Blender中打开此脚本
2. 修改 TEXTURE_PATH 为你的全景纹理路径
3. 运行脚本

脚本会创建一个圆盘mesh，并通过UV映射将下半球纹理以立体投影方式映射上去。
"""

import bpy
import bmesh
import math

# ============ 参数设置 ============
TEXTURE_PATH = "//panorama_texture.jpg"  # 全景纹理路径
DISK_RADIUS = 1.0
DISK_SEGMENTS = 128
DISK_RINGS = 64
OBJECT_NAME = "StereographicDisk"
# ==================================


def create_disk_mesh(name, radius, segments, rings):
    """创建一个带有足够细分的圆盘mesh"""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    center = bm.verts.new((0, 0, 0))

    verts_rings = []
    for i in range(1, rings + 1):
        r = radius * i / rings
        ring_verts = []
        for j in range(segments):
            angle = 2 * math.pi * j / segments
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            v = bm.verts.new((x, y, 0))
            ring_verts.append(v)
        verts_rings.append(ring_verts)

    # 中心到第一环
    for j in range(segments):
        j_next = (j + 1) % segments
        bm.faces.new([center, verts_rings[0][j], verts_rings[0][j_next]])

    # 环与环之间
    for i in range(len(verts_rings) - 1):
        for j in range(segments):
            j_next = (j + 1) % segments
            bm.faces.new([
                verts_rings[i][j],
                verts_rings[i + 1][j],
                verts_rings[i + 1][j_next],
                verts_rings[i][j_next]
            ])

    bm.to_mesh(mesh)
    bm.free()
    return mesh


def stereographic_uv(x, y, radius):
    """
    立体投影：圆盘坐标 -> 全景纹理UV

    从北极点向下投影到赤道平面。
    对于下半球，投影点在赤道平面的圆盘内。

    映射关系：r_disk = tan(|phi|/2) （归一化后）
    其中 |phi| 从赤道(0)到南极(pi/2)

    由于 tan(pi/4) = 1，南极映射到 r=1 时需要归一化。
    实际上：r_disk = tan((pi/2 - |latitude|) / 2) 从北极投影
    对于下半球从北极投影：r = 1 / tan(|phi|/2 + ?) 

    这里我们采用从北极投影到赤道平面的标准公式：
    对于球面点 (theta, phi_lat)，其中 phi_lat 是纬度 [-pi/2, pi/2]
    投影到赤道平面：r = cos(phi_lat) / (1 + sin(phi_lat))
    
    对于下半球 phi_lat ∈ [-pi/2, 0]:
    r ∈ [inf, 1] 从北极投影会趋向无穷大
    
    所以我们改用从南极投影：
    r = cos(phi_lat) / (1 - sin(phi_lat))
    对于下半球 phi_lat ∈ [-pi/2, 0]:
    当 phi_lat = -pi/2 (南极): r = 0
    当 phi_lat = 0 (赤道): r = 1
    
    这给出了一个很好的 [0, 1] 范围映射。
    """
    r = math.sqrt(x * x + y * y) / radius
    if r > 1.0:
        r = 1.0
    if r < 1e-10:
        return (0.5, 1.0)  # 南极点

    alpha = math.atan2(y, x)

    # 从南极投影的反算：
    # r_disk = cos(phi) / (1 - sin(phi))
    # 其中 phi 是纬度（下半球为负值）
    # 设 t = -phi (t ∈ [0, pi/2])，则：
    # r_disk = cos(t) / (1 + sin(t))
    # 解反函数：
    # r * (1 + sin(t)) = cos(t)
    # r + r*sin(t) = cos(t)
    # r = cos(t) - r*sin(t)
    # r^2 = cos^2(t) - 2r*sin(t)*cos(t) + r^2*sin^2(t)  -- 不好解
    # 
    # 用半角公式：r = cos(t)/(1+sin(t)) = (1-tan(t/2)^2)/(1+tan(t/2)^2) / (1 + 2tan(t/2)/(1+tan(t/2)^2))
    # 简化：r = (1 - tan(t/2)) / (1 + tan(t/2))
    # 所以 tan(t/2) = (1 - r) / (1 + r)
    # t = 2 * atan((1 - r) / (1 + r))

    t = 2.0 * math.atan2(1.0 - r, 1.0 + r)  # t = |phi|, 从赤道到南极
    abs_phi = t

    # 转为equirectangular UV
    theta = alpha if alpha >= 0 else alpha + 2 * math.pi
    u = theta / (2 * math.pi)

    # 下半球：赤道v=0.5, 南极v=1.0
    v = 0.5 + abs_phi / math.pi

    return (u, v)


def apply_uv_mapping(obj, radius):
    """为圆盘对象应用立体投影UV映射"""
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="StereographicUV")

    uv_layer = mesh.uv_layers.active.data

    for poly in mesh.polygons:
        for loop_idx in poly.loop_indices:
            loop = mesh.loops[loop_idx]
            vert = mesh.vertices[loop.vertex_index]
            x, y = vert.co.x, vert.co.y
            u, v = stereographic_uv(x, y, radius)
            uv_layer[loop_idx].uv = (u, v)


def setup_material(obj, texture_path):
    """创建材质并连接全景纹理"""
    mat = bpy.data.materials.new(name="StereographicProjectionMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()

    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    tex_image = nodes.new('ShaderNodeTexImage')

    output.location = (300, 0)
    bsdf.location = (0, 0)
    tex_image.location = (-300, 0)

    try:
        img = bpy.data.images.load(texture_path)
        tex_image.image = img
    except Exception as e:
        print(f"Warning: Could not load texture '{texture_path}': {e}")
        print("Please set the texture manually in the shader editor.")

    links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    obj.data.materials.append(mat)


def main():
    if OBJECT_NAME in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[OBJECT_NAME], do_unlink=True)

    mesh = create_disk_mesh(OBJECT_NAME, DISK_RADIUS, DISK_SEGMENTS, DISK_RINGS)
    obj = bpy.data.objects.new(OBJECT_NAME, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    apply_uv_mapping(obj, DISK_RADIUS)
    setup_material(obj, TEXTURE_PATH)

    print(f"[Stereographic] Created disk '{OBJECT_NAME}' with projection UV mapping.")


if __name__ == "__main__":
    main()
