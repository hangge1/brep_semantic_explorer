"""
增强版 STEP 文件解析器
新增功能：
1. 支持更多实体类型的详细解析
2. 几何信息提取
3. 拓扑关系分析
4. 导出功能
"""
import re
import json
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class StepEntity:
    """STEP 实体"""
    entity_id: int
    entity_type: str
    raw_text: str
    line_number: int
    references: List[int]
    referenced_by: List[int] = None  # 被哪些实体引用

    def __post_init__(self):
        if self.referenced_by is None:
            self.referenced_by = []


class StepFileParser:
    """增强版 STEP 文件解析器"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.entities: Dict[int, StepEntity] = {}
        self.header_info = {}
        self.data_section_start = 0

        # 按类型分类的实体索引
        self.entities_by_type: Dict[str, List[int]] = defaultdict(list)

        # 拓扑关系
        self.topology = {
            'faces': [],
            'edges': [],
            'vertices': [],
            'shells': [],
            'solids': []
        }

    def parse(self):
        """解析 STEP 文件"""
        print(f"正在解析 STEP 文件: {self.filepath}")

        with open(self.filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # 解析 HEADER 部分
        self._parse_header(lines)

        # 解析 DATA 部分
        self._parse_data(lines)

        # 建立反向引用关系
        self._build_reverse_references()

        # 分析拓扑结构
        self._analyze_topology()

        print(f"解析完成！共找到 {len(self.entities)} 个实体")
        return self

    def _parse_header(self, lines: List[str]):
        """解析 HEADER 部分"""
        in_header = False
        header_text = []

        for i, line in enumerate(lines):
            if 'HEADER;' in line:
                in_header = True
                continue
            if 'ENDSEC;' in line and in_header:
                in_header = False
                continue
            if 'DATA;' in line:
                self.data_section_start = i + 1
                break
            if in_header:
                header_text.append(line)

        header_str = ''.join(header_text)

        # 提取文件信息
        if 'FILE_NAME' in header_str:
            self.header_info['has_file_name'] = True
        if 'FILE_SCHEMA' in header_str:
            schema_match = re.search(r"FILE_SCHEMA\s*\(\('([^']+)'", header_str)
            if schema_match:
                self.header_info['schema'] = schema_match.group(1)

    def _parse_data(self, lines: List[str]):
        """解析 DATA 部分"""
        current_entity_lines = []
        current_entity_id = None
        current_line_number = None

        for i in range(self.data_section_start, len(lines)):
            line = lines[i].strip()

            if not line or line.startswith('/*'):
                continue

            if line.startswith('#'):
                if current_entity_lines:
                    self._process_entity(
                        current_entity_id,
                        current_line_number,
                        ''.join(current_entity_lines)
                    )

                current_entity_lines = [line]
                current_line_number = i + 1

                match = re.match(r'#(\d+)\s*=', line)
                if match:
                    current_entity_id = int(match.group(1))
            else:
                if current_entity_lines:
                    current_entity_lines.append(line)

        if current_entity_lines:
            self._process_entity(
                current_entity_id,
                current_line_number,
                ''.join(current_entity_lines)
            )

    def _process_entity(self, entity_id: int, line_number: int, raw_text: str):
        """处理单个实体"""
        match = re.match(r'#\d+\s*=\s*([A-Z_]+)\s*\(', raw_text)
        entity_type = match.group(1) if match else 'UNKNOWN'

        references = self._extract_references(raw_text)

        entity = StepEntity(
            entity_id=entity_id,
            entity_type=entity_type,
            raw_text=raw_text,
            line_number=line_number,
            references=references
        )

        self.entities[entity_id] = entity
        self.entities_by_type[entity_type].append(entity_id)

    def _extract_references(self, text: str) -> List[int]:
        """提取实体中引用的其他实体 ID"""
        matches = re.findall(r'#(\d+)', text)
        return [int(m) for m in matches if m]

    def _build_reverse_references(self):
        """建立反向引用关系"""
        for entity in self.entities.values():
            for ref_id in entity.references:
                if ref_id in self.entities:
                    self.entities[ref_id].referenced_by.append(entity.entity_id)

    def _analyze_topology(self):
        """分析拓扑结构"""
        self.topology['faces'] = self.entities_by_type.get('ADVANCED_FACE', [])
        self.topology['edges'] = self.entities_by_type.get('EDGE_CURVE', [])
        self.topology['vertices'] = self.entities_by_type.get('VERTEX_POINT', [])
        self.topology['shells'] = self.entities_by_type.get('CLOSED_SHELL', []) + \
                                   self.entities_by_type.get('OPEN_SHELL', [])
        self.topology['solids'] = self.entities_by_type.get('MANIFOLD_SOLID_BREP', [])

    def get_entity(self, entity_id: int) -> Optional[StepEntity]:
        """获取指定 ID 的实体"""
        return self.entities.get(entity_id)

    def get_entity_with_context(self, entity_id: int, depth: int = 1) -> Dict:
        """获取实体及其依赖关系"""
        entity = self.get_entity(entity_id)
        if not entity:
            return None

        result = {
            'entity_id': entity.entity_id,
            'entity_type': entity.entity_type,
            'raw_text': entity.raw_text,
            'line_number': entity.line_number,
            'references': entity.references,
            'referenced_by': entity.referenced_by,
            'referenced_entities': [],
            'referencing_entities': []
        }

        # 获取引用的实体
        if depth > 0:
            for ref_id in entity.references[:10]:
                ref_entity = self.get_entity(ref_id)
                if ref_entity:
                    result['referenced_entities'].append({
                        'entity_id': ref_entity.entity_id,
                        'entity_type': ref_entity.entity_type,
                        'raw_text': ref_entity.raw_text[:200] + '...' if len(ref_entity.raw_text) > 200 else ref_entity.raw_text
                    })

        # 获取引用此实体的实体
        for ref_id in entity.referenced_by[:10]:
            ref_entity = self.get_entity(ref_id)
            if ref_entity:
                result['referencing_entities'].append({
                    'entity_id': ref_entity.entity_id,
                    'entity_type': ref_entity.entity_type
                })

        return result

    def find_entities_by_type(self, entity_type: str) -> List[StepEntity]:
        """查找指定类型的所有实体"""
        entity_ids = self.entities_by_type.get(entity_type, [])
        return [self.entities[eid] for eid in entity_ids]

    def search_entities(self, query: str) -> List[StepEntity]:
        """搜索实体"""
        results = []
        query_lower = query.lower()

        for entity in self.entities.values():
            if (str(entity.entity_id) == query or
                query_lower in entity.entity_type.lower() or
                query_lower in entity.raw_text.lower()):
                results.append(entity)

        return results

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        type_counts = {}
        for entity_type, entity_ids in self.entities_by_type.items():
            type_counts[entity_type] = len(entity_ids)

        return {
            'total_entities': len(self.entities),
            'entity_types': len(type_counts),
            'type_distribution': dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:30]),
            'topology': {
                'faces': len(self.topology['faces']),
                'edges': len(self.topology['edges']),
                'vertices': len(self.topology['vertices']),
                'shells': len(self.topology['shells']),
                'solids': len(self.topology['solids'])
            },
            'header': self.header_info
        }

    def export_to_json(self, output_path: str, include_all: bool = False):
        """导出为 JSON 格式"""
        data = {
            'filename': self.filepath,
            'statistics': self.get_statistics(),
            'topology': self.topology
        }

        if include_all:
            data['entities'] = {
                str(eid): {
                    'id': e.entity_id,
                    'type': e.entity_type,
                    'text': e.raw_text,
                    'line': e.line_number,
                    'refs': e.references,
                    'ref_by': e.referenced_by
                }
                for eid, e in self.entities.items()
            }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"已导出到: {output_path}")

    def export_topology_graph(self, output_path: str):
        """导出拓扑关系图（Mermaid 格式）"""
        lines = ["graph TD"]

        # 只导出部分实体，避免图太大
        faces = self.topology['faces'][:10]

        for face_id in faces:
            face = self.entities[face_id]
            lines.append(f"    F{face_id}[Face #{face_id}]")

            for ref_id in face.references[:5]:
                ref = self.entities.get(ref_id)
                if ref:
                    if ref.entity_type == 'EDGE_CURVE':
                        lines.append(f"    E{ref_id}[Edge #{ref_id}]")
                        lines.append(f"    F{face_id} --> E{ref_id}")
                    elif ref.entity_type == 'VERTEX_POINT':
                        lines.append(f"    V{ref_id}[Vertex #{ref_id}]")
                        lines.append(f"    F{face_id} --> V{ref_id}")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"已导出拓扑图到: {output_path}")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        filepath = r'D:\company\code\Step_Test_Data\100106_7f144e5b_0000.step'

    parser = StepFileParser(filepath)
    parser.parse()

    # 显示统计信息
    stats = parser.get_statistics()
    print("\n=== 统计信息 ===")
    print(f"总实体数: {stats['total_entities']}")
    print(f"实体类型数: {stats['entity_types']}")

    print("\n拓扑结构:")
    print(f"  面: {stats['topology']['faces']}")
    print(f"  边: {stats['topology']['edges']}")
    print(f"  顶点: {stats['topology']['vertices']}")
    print(f"  壳: {stats['topology']['shells']}")
    print(f"  实体: {stats['topology']['solids']}")

    print("\n实体类型分布（前 20）:")
    for entity_type, count in list(stats['type_distribution'].items())[:20]:
        print(f"  {entity_type}: {count}")

    # 查找第一个面并显示详细信息
    faces = parser.find_entities_by_type('ADVANCED_FACE')
    if faces:
        print(f"\n第一个面的详细信息:")
        face_info = parser.get_entity_with_context(faces[0].entity_id)
        print(f"  实体 ID: #{face_info['entity_id']}")
        print(f"  类型: {face_info['entity_type']}")
        print(f"  行号: {face_info['line_number']}")
        print(f"  引用了 {len(face_info['references'])} 个其他实体")
        print(f"  被 {len(face_info['referenced_by'])} 个实体引用")

    # 导出示例
    if len(sys.argv) > 2 and sys.argv[2] == '--export':
        parser.export_to_json('output.json', include_all=False)
        parser.export_topology_graph('topology.mmd')
