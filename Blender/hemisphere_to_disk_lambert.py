"""
Lambert Equal-Area Azimuthal Projection
将下半球全景纹理映射到平面圆盘上（等面积投影）

使用方法：
1. 在Blender中打开此脚本
2. 修改 TEXTURE_PATH 为你的全景纹理路径
3. 运行脚本

脚本会创建一个圆盘mesh，并通过UV映射将下半球纹理以Lambert等面积方式映射上去。
"""

import bpy
import bmesh
import math
import numpy as np

# ============ 参数设置 ============
TEXTURE_PATH = "//panorama_texture.jpg"  # 全景纹理路径（相对或绝对）
DISK_RADIUS = 1.0          # 圆盘半径
DISK_SEGMENTS = 128        # 圆盘细分段数（越大越精细）
DISK_RINGS = 64            # 圆盘环数
OBJECT_NAME = "LambertDisk"
# ==================================


def create_disk_mesh(name, radius, segments, rings):
    """创建一个带有足够细分的圆盘mesh"""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()

    # 创建中心点
    center = bm.verts.new((0, 0, 0))

    # 创建同心环上的顶点
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

    # 创建面：中心到第一环
    for j in range(segments):
        j_next = (j + 1) % segments
        bm.faces.new([center, verts_rings[0][j], verts_rings[0][j_next]])

    # 创建面：环与环之间
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


def lambert_equal_area_uv(x, y, radius):
    """
    Lambert等面积投影：圆盘坐标 -> 全景纹理UV

    圆盘上的点 (x, y) -> 极坐标 (r, alpha)
    反算球面坐标 (theta, phi)
    然后转为equirectangular纹理的UV
    """
    r = math.sqrt(x * x + y * y) / radius
    if r > 1.0:
        r = 1.0
    if r < 1e-10:
        return (0.5, 1.0)  # 南极点 -> 纹理底部中央

    alpha = math.atan2(y, x)

    # Lambert等面积反投影：r = sqrt(1 - cos(|phi|))
    # 其中 |phi| 是从赤道算起的角度（0=赤道, pi/2=南极）
    # 所以 cos(|phi|) = 1 - r^2
    cos_phi = 1.0 - r * r
    cos_phi = max(-1.0, min(1.0, cos_phi))
    abs_phi = math.acos(cos_phi)  # 从赤道到南极的角度

    # 转为equirectangular UV
    # theta (经度) -> u: [0, 2pi] -> [0, 1]
    theta = alpha if alpha >= 0 else alpha + 2 * math.pi
    u = theta / (2 * math.pi)

    # phi (纬度) -> v: 赤道=0.5, 南极=1.0（下半球）
    v = 0.5 + abs_phi / math.pi

    return (u, v)


def apply_uv_mapping(obj, radius):
    """为圆盘对象应用Lambert等面积UV映射"""
    mesh = obj.data
    if not mesh.uv_layers:
        mesh.uv_layers.new(name="LambertUV")

    uv_layer = mesh.uv_layers.active.data

    for poly in mesh.polygons:
        for loop_idx in poly.loop_indices:
            loop = mesh.loops[loop_idx]
            vert = mesh.vertices[loop.vertex_index]
            x, y = vert.co.x, vert.co.y
            u, v = lambert_equal_area_uv(x, y, radius)
            uv_layer[loop_idx].uv = (u, v)


def setup_material(obj, texture_path):
    """创建材质并连接全景纹理"""
    mat = bpy.data.materials.new(name="LambertProjectionMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # 清除默认节点
    nodes.clear()

    # 创建节点
    output = nodes.new('ShaderNodeOutputMaterial')
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    tex_image = nodes.new('ShaderNodeTexImage')

    # 布局
    output.location = (300, 0)
    bsdf.location = (0, 0)
    tex_image.location = (-300, 0)

    # 加载纹理
    try:
        img = bpy.data.images.load(texture_path)
        tex_image.image = img
    except Exception as e:
        print(f"Warning: Could not load texture '{texture_path}': {e}")
        print("Please set the texture manually in the shader editor.")

    # 连接节点
    links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    # 赋予材质
    obj.data.materials.append(mat)


def main():
    # 清除同名对象
    if OBJECT_NAME in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects[OBJECT_NAME], do_unlink=True)

    # 创建圆盘
    mesh = create_disk_mesh(OBJECT_NAME, DISK_RADIUS, DISK_SEGMENTS, DISK_RINGS)
    obj = bpy.data.objects.new(OBJECT_NAME, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # 应用UV映射
    apply_uv_mapping(obj, DISK_RADIUS)

    # 设置材质
    setup_material(obj, TEXTURE_PATH)

    print(f"[Lambert Equal-Area] Created disk '{OBJECT_NAME}' with projection UV mapping.")


if __name__ == "__main__":
    main()
