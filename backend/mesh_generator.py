"""
STEP 文件网格化服务
使用 gmsh (内置 OpenCASCADE) 正确离散化 Brep 模型
输出 JSON 格式的三角网格 + 拓扑映射
"""
import gmsh
import json
import sys
import os


def mesh_step_file(filepath: str, mesh_size: float = 0.0) -> dict:
    """
    读取 STEP 文件，离散化为三角网格，并保留拓扑映射关系。

    返回:
    {
        "vertices": [[x,y,z], ...],
        "faces": [
            {
                "id": face_tag,
                "triangles": [[v0,v1,v2], ...],
                "surface_type": "Plane" | "Cylinder" | ...
            }
        ],
        "edges": [
            {
                "id": edge_tag,
                "points": [[x,y,z], ...]
            }
        ],
        "bbox": {"min": [x,y,z], "max": [x,y,z], "center": [...], "size": [...]}
    }
    """
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)

    try:
        gmsh.model.occ.importShapes(filepath)
        gmsh.model.occ.synchronize()

        # 自动计算网格尺寸（如果未指定）
        bbox = gmsh.model.getBoundingBox(-1, -1)
        xmin, ymin, zmin, xmax, ymax, zmax = bbox
        diag = ((xmax-xmin)**2 + (ymax-ymin)**2 + (zmax-zmin)**2) ** 0.5

        if mesh_size <= 0:
            mesh_size = diag / 30.0

        gmsh.option.setNumber("Mesh.CharacteristicLengthMax", mesh_size)
        gmsh.option.setNumber("Mesh.CharacteristicLengthMin", mesh_size * 0.1)

        # 生成 2D 网格（三角化）
        gmsh.model.mesh.generate(2)

        # 提取全局顶点
        node_tags, coords, _ = gmsh.model.mesh.getNodes()
        # 构建 tag -> index 映射
        tag_to_idx = {}
        vertices = []
        for i, tag in enumerate(node_tags):
            tag_to_idx[int(tag)] = i
            vertices.append([coords[3*i], coords[3*i+1], coords[3*i+2]])

        # 提取面信息
        faces_data = []
        face_entities = gmsh.model.getEntities(2)  # dim=2 是面

        for dim, tag in face_entities:
            face_info = {"id": tag, "triangles": [], "surface_type": ""}

            # 获取面的类型
            face_type = gmsh.model.getType(dim, tag)
            face_info["surface_type"] = face_type

            # 获取面的三角网格
            elem_types, elem_tags, elem_nodes = gmsh.model.mesh.getElements(dim, tag)

            for et, en in zip(elem_types, elem_nodes):
                # type 2 = 三角形
                if et == 2:
                    for i in range(0, len(en), 3):
                        tri = [
                            tag_to_idx[int(en[i])],
                            tag_to_idx[int(en[i+1])],
                            tag_to_idx[int(en[i+2])]
                        ]
                        face_info["triangles"].append(tri)

            faces_data.append(face_info)

        # 提取边信息（离散化后的折线）
        edges_data = []
        edge_entities = gmsh.model.getEntities(1)  # dim=1 是边

        for dim, tag in edge_entities:
            edge_info = {"id": tag, "points": [], "curve_type": ""}

            edge_type = gmsh.model.getType(dim, tag)
            edge_info["curve_type"] = edge_type

            # 获取边上的节点（按顺序）
            node_tags_edge, coords_edge, _ = gmsh.model.mesh.getNodes(dim, tag, includeBoundary=True)

            for i in range(len(node_tags_edge)):
                edge_info["points"].append([
                    coords_edge[3*i],
                    coords_edge[3*i+1],
                    coords_edge[3*i+2]
                ])

            edges_data.append(edge_info)

        # 包围盒
        center = [(xmin+xmax)/2, (ymin+ymax)/2, (zmin+zmax)/2]
        size = [xmax-xmin, ymax-ymin, zmax-zmin]

        result = {
            "vertices": vertices,
            "faces": faces_data,
            "edges": edges_data,
            "bbox": {
                "min": [xmin, ymin, zmin],
                "max": [xmax, ymax, zmax],
                "center": center,
                "size": size
            },
            "statistics": {
                "vertex_count": len(vertices),
                "face_count": len(faces_data),
                "edge_count": len(edges_data),
                "triangle_count": sum(len(f["triangles"]) for f in faces_data)
            }
        }

        return result

    finally:
        gmsh.finalize()


def process_step_file(filepath: str, output_path: str = None, mesh_size: float = 0.0):
    """处理 STEP 文件并输出 JSON"""
    print(f"[Mesh] 正在处理: {filepath}")

    result = mesh_step_file(filepath, mesh_size)

    print(f"[Mesh] 完成!")
    print(f"  顶点数: {result['statistics']['vertex_count']}")
    print(f"  面数: {result['statistics']['face_count']}")
    print(f"  边数: {result['statistics']['edge_count']}")
    print(f"  三角形数: {result['statistics']['triangle_count']}")
    print(f"  包围盒: {result['bbox']['size']}")

    if output_path is None:
        base = os.path.splitext(os.path.basename(filepath))[0]
        output_path = os.path.join(os.path.dirname(__file__), '..', 'data', f'{base}_mesh.json')

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(result, f)

    print(f"[Mesh] 已保存到: {output_path}")
    return output_path


if __name__ == '__main__':
    filepath = sys.argv[1] if len(sys.argv) > 1 else r'D:\company\code\Step_Test_Data\100106_7f144e5b_0000_0001.step'
    process_step_file(filepath)
