"""
Azimuthal Equidistant Projection（等距方位投影）
将下半球全景纹理映射到平面圆盘上（保持径向距离比例）

使用方法：
1. 在Blender中打开此脚本
2. 修改 TEXTURE_PATH 为你的全景纹理路径
3. 运行脚本

脚本会创建一个圆盘mesh，并通过UV映射将下半球纹理以等距方式映射上去。
"""

import bpy
import bmesh
import math

# ============ 参数设置 ============
TEXTURE_PATH = "//panorama_texture.jpg"  # 全景纹理路径
DISK_RADIUS = 1.0
DISK_SEGMENTS = 128
DISK_RINGS = 64
OBJECT_NAME = "EquidistantDisk"
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


def equidistant_uv(x, y, radius):
    """
    等距方位投影：圆盘坐标 -> 全景纹理UV

    映射关系：r = |phi| / (pi/2)
    即纬度线性映射到圆盘半径
    """
    r = math.sqrt(x * x + y * y) / radius
    if r > 1.0:
        r = 1.0
    if r < 1e-10:
        return (0.5, 1.0)  # 南极点

    alpha = math.atan2(y, x)

    # 等距投影反算：r = |phi| / (pi/2)
    # 所以 |phi| = r * pi/2
    abs_phi = r * (math.pi / 2.0)

    # 转为equirectangular UV
    theta = alpha if alpha >= 0 else alpha + 2 * math.pi
    u = theta / (2 * math.pi)

    # 下半球：赤道v=0.5, 南极v=1.0
    v = 0.5 + abs_phi / math.pi

    return (u, v)


def apply_uv_mapping(obj, radius):
    """为圆盘对象应用等距方位UV映射"""
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="EquidistantUV")

    uv_layer = mesh.uv_layers.active.data

    for poly in mesh.polygons:
        for loop_idx in poly.loop_indices:
            loop = mesh.loops[loop_idx]
            vert = mesh.vertices[loop.vertex_index]
            x, y = vert.co.x, vert.co.y
            u, v = equidistant_uv(x, y, radius)
            uv_layer[loop_idx].uv = (u, v)


def setup_material(obj, texture_path):
    """创建材质并连接全景纹理"""
    mat = bpy.data.materials.new(name="EquidistantProjectionMat")
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

    print(f"[Equidistant] Created disk '{OBJECT_NAME}' with projection UV mapping.")


if __name__ == "__main__":
    main()
