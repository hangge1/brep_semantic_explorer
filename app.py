"""
一体化服务：解析 STEP 文件 + 网格化 + 启动 Web 服务器
用法: python app.py [step_file_path]
"""
import http.server
import json
import os
import sys
import threading
import webbrowser
from urllib.parse import parse_qs, urlparse

# 添加 backend 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from mesh_generator import mesh_step_file
from step_parser_v2 import StepFileParser

# 全局状态
current_mesh = None
current_parser = None
current_filename = ""


class BrepExplorerHandler(http.server.SimpleHTTPRequestHandler):
    """自定义 HTTP 请求处理器"""

    def do_POST(self):
        if self.path == '/api/upload':
            self._handle_upload()
        elif self.path == '/api/load-local':
            self._handle_load_local()
        else:
            self.send_error(404)

    def _handle_upload(self):
        """处理文件上传"""
        import cgi
        content_type = self.headers['Content-Type']
        if not content_type or 'multipart/form-data' not in content_type:
            self._send_json({"error": "Invalid content type"}, 400)
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                'REQUEST_METHOD': 'POST',
                'CONTENT_TYPE': content_type
            }
        )

        if 'file' not in form:
            self._send_json({"error": "No file uploaded"}, 400)
            return

        file_item = form['file']
        filename = file_item.filename
        if not filename.lower().endswith(('.step', '.stp')):
            self._send_json({"error": "Only .step/.stp files allowed"}, 400)
            return

        # 保存上传的文件
        upload_dir = os.path.join(os.path.dirname(__file__), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, filename)

        with open(filepath, 'wb') as f:
            f.write(file_item.file.read())

        # 处理文件
        try:
            load_step_file(filepath)
            self._send_json({
                "status": "success",
                "filename": filename,
                "statistics": current_mesh['statistics'] if current_mesh else {}
            })
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_load_local(self):
        """加载本地文件（通过路径）"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(body)
        filepath = data.get('filepath', '')

        if not os.path.exists(filepath):
            self._send_json({"error": f"File not found: {filepath}"}, 404)
            return

        try:
            load_step_file(filepath)
            self._send_json({
                "status": "success",
                "filename": os.path.basename(filepath),
                "statistics": current_mesh['statistics'] if current_mesh else {}
            })
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == '/api/mesh':
            self._send_json(current_mesh or {"error": "No file loaded"})
        elif path == '/api/statistics':
            if current_parser:
                self._send_json(current_parser.get_statistics())
            else:
                self._send_json({"error": "No file loaded"})
        elif path == '/api/topology':
            if current_parser:
                topology = build_topology_tree(current_parser, current_mesh)
                self._send_json(topology)
            else:
                self._send_json({"error": "No file loaded"})
        elif path.startswith('/api/entity/'):
            entity_id = int(path.split('/')[-1])
            if current_parser:
                info = current_parser.get_entity_with_context(entity_id)
                self._send_json(info or {"error": "Entity not found"})
            else:
                self._send_json({"error": "No file loaded"})
        elif path == '/api/entities':
            params = parse_qs(parsed.query)
            entity_type = params.get('type', [''])[0]
            if current_parser and entity_type:
                entities = current_parser.find_entities_by_type(entity_type)
                self._send_json([{
                    'id': e.entity_id,
                    'type': e.entity_type,
                    'line': e.line_number,
                    'text': e.raw_text[:300]
                } for e in entities[:200]])
            else:
                self._send_json([])
        else:
            # 静态文件服务
            if path == '/':
                self.path = '/frontend/explorer.html'
            super().do_GET()

    def _send_json(self, data, status=200):
        response = json.dumps(data, ensure_ascii=False)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

    def log_message(self, format, *args):
        pass  # 静默日志


def build_topology_tree(parser, mesh_data):
    """从解析器构建拓扑树"""
    tree = []

    solids = parser.find_entities_by_type('MANIFOLD_SOLID_BREP')
    face_entities = parser.find_entities_by_type('ADVANCED_FACE')

    for solid in solids:
        solid_node = {
            'type': 'SOLID',
            'id': solid.entity_id,
            'label': f'Solid #{solid.entity_id}',
            'children': []
        }

        # 找 Shell
        for ref_id in solid.references:
            shell = parser.get_entity(ref_id)
            if not shell or shell.entity_type not in ('CLOSED_SHELL', 'OPEN_SHELL'):
                continue

            shell_node = {
                'type': 'SHELL',
                'id': shell.entity_id,
                'label': f'{shell.entity_type} #{shell.entity_id}',
                'children': []
            }

            # 找 Face
            for face_ref_id in shell.references:
                face = parser.get_entity(face_ref_id)
                if not face or face.entity_type != 'ADVANCED_FACE':
                    continue

                # 确定面在 mesh 中的索引
                mesh_index = -1
                for i, fe in enumerate(face_entities):
                    if fe.entity_id == face.entity_id:
                        mesh_index = i
                        break

                # 获取曲面类型
                surface_type = ''
                face_children = []
                for fref in face.references:
                    fref_e = parser.get_entity(fref)
                    if not fref_e:
                        continue
                    if fref_e.entity_type in ('PLANE', 'CYLINDRICAL_SURFACE', 'CONICAL_SURFACE',
                                              'SPHERICAL_SURFACE', 'TOROIDAL_SURFACE',
                                              'B_SPLINE_SURFACE_WITH_KNOTS'):
                        surface_type = fref_e.entity_type
                    elif fref_e.entity_type in ('FACE_OUTER_BOUND', 'FACE_BOUND'):
                        # 找 EDGE_LOOP
                        for loop_ref in fref_e.references:
                            loop = parser.get_entity(loop_ref)
                            if not loop or loop.entity_type != 'EDGE_LOOP':
                                continue
                            loop_node = {
                                'type': 'EDGE_LOOP',
                                'id': loop.entity_id,
                                'label': f'EdgeLoop #{loop.entity_id}',
                                'children': []
                            }
                            # 找 EDGE_CURVE
                            for oe_ref in loop.references:
                                oe = parser.get_entity(oe_ref)
                                if not oe or oe.entity_type != 'ORIENTED_EDGE':
                                    continue
                                for ec_ref in oe.references:
                                    ec = parser.get_entity(ec_ref)
                                    if ec and ec.entity_type == 'EDGE_CURVE':
                                        # 获取曲线类型
                                        curve_type = ''
                                        for cr in ec.references:
                                            cr_e = parser.get_entity(cr)
                                            if cr_e and cr_e.entity_type in ('LINE', 'CIRCLE', 'ELLIPSE', 'B_SPLINE_CURVE_WITH_KNOTS'):
                                                curve_type = cr_e.entity_type
                                                break
                                        loop_node['children'].append({
                                            'type': 'EDGE',
                                            'id': ec.entity_id,
                                            'label': f'Edge #{ec.entity_id} ({curve_type})',
                                            'children': []
                                        })
                            face_children.append(loop_node)

                face_node = {
                    'type': 'FACE',
                    'id': face.entity_id,
                    'label': f'Face #{face.entity_id} ({surface_type})',
                    'mesh_index': mesh_index,
                    'children': face_children
                }
                shell_node['children'].append(face_node)

            solid_node['children'].append(shell_node)

        tree.append(solid_node)

    return tree


def load_step_file(filepath: str):
    """加载并处理 STEP 文件"""
    global current_mesh, current_parser, current_filename

    print(f"\n{'='*60}")
    print(f"  Brep Explorer - Loading file")
    print(f"{'='*60}")
    print(f"  File: {filepath}")

    # 1. 解析 STEP 文件（提取实体信息用于追溯）
    print("\n  [1/2] Parsing STEP entities...")
    current_parser = StepFileParser(filepath)
    current_parser.parse()

    # 2. 网格化（用于 3D 渲染）
    print("  [2/2] Meshing (tessellation)...")
    mesh_data = mesh_step_file(filepath)

    # 合并 STEP 实体信息到 mesh 数据中
    mesh_data['step_entities'] = {}
    mesh_data['filename'] = os.path.basename(filepath)

    # 为每个面添加 STEP 实体信息
    face_entities = current_parser.find_entities_by_type('ADVANCED_FACE')
    for i, face in enumerate(mesh_data['faces']):
        if i < len(face_entities):
            entity = face_entities[i]
            face['step_entity_id'] = entity.entity_id
            face['step_text'] = entity.raw_text
            face['step_line'] = entity.line_number
            face['step_refs'] = entity.references

            mesh_data['step_entities'][entity.entity_id] = {
                'id': entity.entity_id,
                'type': entity.entity_type,
                'text': entity.raw_text,
                'line': entity.line_number,
                'refs': entity.references
            }

    # 为每个边添加 STEP 实体信息
    edge_entities = current_parser.find_entities_by_type('EDGE_CURVE')
    for i, edge in enumerate(mesh_data['edges']):
        if i < len(edge_entities):
            entity = edge_entities[i]
            edge['step_entity_id'] = entity.entity_id
            edge['step_text'] = entity.raw_text
            edge['step_line'] = entity.line_number

            mesh_data['step_entities'][entity.entity_id] = {
                'id': entity.entity_id,
                'type': entity.entity_type,
                'text': entity.raw_text,
                'line': entity.line_number,
                'refs': entity.references
            }

    current_mesh = mesh_data
    current_filename = os.path.basename(filepath)

    print(f"\n  Done!")
    print(f"  Vertices: {mesh_data['statistics']['vertex_count']}")
    print(f"  Triangles: {mesh_data['statistics']['triangle_count']}")
    print(f"  Faces: {mesh_data['statistics']['face_count']}")
    print(f"  Edges: {mesh_data['statistics']['edge_count']}")
    print(f"  STEP entities: {len(current_parser.entities)}")
    print(f"{'='*60}\n")


def main():
    port = 8080

    # 加载 STEP 文件（可选）
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if not os.path.exists(filepath):
            print(f"Error: File not found: {filepath}")
            sys.exit(1)
        load_step_file(filepath)
    else:
        print("  No file specified. Use the web UI to upload a STEP file.")
        print("  Or restart with: python app.py <path_to_step_file>\n")

    # 启动 HTTP 服务器
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.HTTPServer(('localhost', port), BrepExplorerHandler)

    print(f"  Server: http://localhost:{port}")
    print(f"  按 Ctrl+C 停止\n")

    # 自动打开浏览器
    webbrowser.open(f'http://localhost:{port}')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
        server.shutdown()


if __name__ == '__main__':
    main()
