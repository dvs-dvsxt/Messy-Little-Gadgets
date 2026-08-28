# -*- coding: utf-8 -*-
"""
目录树分析器 v1.0
功能：指定目录查看详细的目录树信息和统计信息
- 递归目录树展示
- 文件/目录数量统计
- 大小分布分析（按扩展名、按层级、按大小区间）
- Top N 大文件
- 深层目录
"""
import os
import sys
from collections import defaultdict
from datetime import datetime

# ============ 配置 ============
MAX_TREE_DEPTH = 8          # 目录树显示最大深度
MAX_TREE_ITEMS = 5000       # 目录树显示最大条目数（防止爆炸）
SHOW_TREE = True            # 是否显示目录树
DEFAULT_IGNORE = {'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.idea', '.vscode'}

# ============ 颜色 ============
class C:
    DIR = '\033[1;34m'      # 目录 - 蓝
    FILE = '\033[0m'        # 文件 - 默认
    SIZE = '\033[0;36m'     # 大小 - 青
    HDR = '\033[1;33m'      # 标题 - 黄
    WARN = '\033[1;31m'     # 警告 - 红
    OK = '\033[1;32m'       # 成功 - 绿
    END = '\033[0m'

def human_size(n):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if n < 1024.0:
            return f"{n:.1f} {unit}" if unit != 'B' else f"{int(n)} B"
        n /= 1024.0
    return f"{n:.1f} PB"

def fmt_num(n):
    return f"{n:,}"

class DirAnalyzer:
    def __init__(self, root, ignore=None):
        self.root = os.path.abspath(root)
        self.ignore = DEFAULT_IGNORE | (ignore or set())
        self.total_files = 0
        self.total_dirs = 0
        self.total_size = 0
        self.ext_sizes = defaultdict(lambda: [0, 0])   # ext -> [count, size]
        self.level_stats = defaultdict(lambda: [0, 0])  # depth -> [count, size]
        self.size_buckets = defaultdict(int)            # size 区间
        self.large_files = []                           # (size, path)
        self.deep_dirs = []                             # (depth, path)
        self.max_depth = 0
        self.max_width_dir = (0, '')                    # 最多子项的目录
        self.errors = 0
        self.dir_children = defaultdict(int)            # dir -> 子项数
        self.tree_lines = []
        self.scanned = 0

    # ---- 大小区间 ----
    def bucket(self, size):
        if size < 1*1024: return "<1KB"
        if size < 10*1024: return "1-10KB"
        if size < 100*1024: return "10-100KB"
        if size < 1*1024*1024: return "100KB-1MB"
        if size < 10*1024*1024: return "1-10MB"
        if size < 100*1024*1024: return "10-100MB"
        if size < 1*1024*1024*1024: return "100MB-1GB"
        return ">1GB"

    def scan(self):
        self.tree_lines.append(f"{C.HDR}{self.root}{C.END}")
        self._walk(self.root, 0)
        return self

    def _walk(self, path, depth):
        self.scanned += 1
        try:
            entries = os.listdir(path)
        except (PermissionError, OSError) as e:
            self.errors += 1
            self.tree_lines.append("  "*depth + f"{C.WARN}[权限拒绝] {os.path.basename(path)}{C.END}")
            return

        self.dir_children[path] = len(entries)
        if self.dir_children[path] > self.max_width_dir[0]:
            self.max_width_dir = (self.dir_children[path], path)

        show_children = (len(self.tree_lines) < MAX_TREE_ITEMS and depth < MAX_TREE_DEPTH)

        for name in entries:
            if name in self.ignore:
                continue
            full = os.path.join(path, name)
            try:
                if os.path.isdir(full):
                    self.total_dirs += 1
                    self.level_stats[depth+1][0] += 1
                    if depth+1 > self.max_depth:
                        self.max_depth = depth+1
                    self.deep_dirs.append((depth+1, full))
                    if show_children:
                        self.tree_lines.append("  "*depth + f"{C.DIR}├─ {name}/  {C.END}")
                    self._walk(full, depth+1)
                else:
                    size = os.path.getsize(full)
                    self.total_files += 1
                    self.total_size += size
                    ext = os.path.splitext(name)[1].lower() or "(no-ext)"
                    self.ext_sizes[ext][0] += 1
                    self.ext_sizes[ext][1] += size
                    self.level_stats[depth+1][1] += size
                    self.size_buckets[self.bucket(size)] += 1
                    self.large_files.append((size, full))
                    if show_children:
                        self.tree_lines.append("  "*depth + f"{C.FILE}├─ {name}  {C.SIZE}({human_size(size)}){C.END}")
            except (PermissionError, OSError):
                self.errors += 1

    # ---- 报表 ----
    def summary(self):
        print(f"\n{'='*60}")
        print(f"{C.HDR}📊 目录分析报告{C.END}")
        print(f"{'='*60}")
        print(f"扫描目录 : {self.root}")
        print(f"扫描时间 : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        print(f"{C.OK}总文件数  : {fmt_num(self.total_files)} 个{C.END}")
        print(f"{C.DIR}总目录数  : {fmt_num(self.total_dirs)} 个{C.END}")
        print(f"{C.SIZE}总大小    : {human_size(self.total_size)} ({fmt_num(self.total_size)} B){C.END}")
        print(f"最大深度  : {self.max_depth} 层")
        print(f"权限错误  : {self.errors} 处")

        if self.max_width_dir[0] > 0:
            print(f"\n[C] 子项最多的目录: {self.max_width_dir[0]} 个 → {self.max_width_dir[1]}")

    def report_ext(self):
        if not self.ext_sizes:
            return
        print(f"\n{'─'*60}\n{C.HDR}📁 扩展名统计 (Top 15){C.END}")
        sorted_ext = sorted(self.ext_sizes.items(), key=lambda x: -x[1][1])
        print(f"{'扩展名':<15}{'数量':>10}{'总大小':>12}{'占比':>8}")
        print('─'*60)
        for ext, (cnt, sz) in sorted_ext[:15]:
            pct = sz / self.total_size * 100 if self.total_size else 0
            print(f"{ext:<15}{cnt:>10,}{human_size(sz):>12}{pct:>7.1f}%")

    def report_levels(self):
        print(f"\n{'─'*60}\n{C.HDR}📂 层级分布 (深度: 文件/大小){C.END}")
        for depth in sorted(self.level_stats):
            cnt, sz = self.level_stats[depth]
            if cnt == 0 and sz == 0:
                continue
            bar = '█' * min(int(sz / (self.total_size/60 + 1)), 60) if self.total_size else ''
            print(f"深度{depth:<3} {cnt:>8,} 文件  {human_size(sz):>12}  {C.SIZE}{bar}{C.END}")

    def report_buckets(self):
        print(f"\n{'─'*60}\n{C.HDR}📦 文件大小分布{C.END}")
        order = ["<1KB","1-10KB","10-100KB","100KB-1MB","1-10MB","10-100MB","100MB-1GB",">1GB"]
        for b in order:
            cnt = self.size_buckets.get(b, 0)
            bar = '█' * min(int(cnt / (self.total_files/50 + 1)), 50) if self.total_files else ''
            print(f"{b:<12} {cnt:>8,} 个  {C.OK}{bar}{C.END}")

    def report_large(self, n=15):
        print(f"\n{'─'*60}\n{C.HDR}🐘 Top {n} 大文件{C.END}")
        self.large_files.sort(reverse=True)
        for i, (sz, path) in enumerate(self.large_files[:n], 1):
            print(f"{i:>2}. {human_size(sz):>12}  {path}")

    def report_deep_dirs(self, n=10):
        print(f"\n{'─'*60}\n{C.HDR}🕳️ 最深目录 (Top {n}){C.END}")
        self.deep_dirs.sort(key=lambda x: -x[0])
        for i, (depth, path) in enumerate(self.deep_dirs[:n], 1):
            print(f"{i:>2}. 深度{depth:<3}  {C.DIR}{path}{C.END}")

    def print_tree(self):
        if SHOW_TREE:
            print(f"\n{'─'*60}\n{C.HDR}🌳 目录树{C.END}")
            for line in self.tree_lines[:MAX_TREE_ITEMS]:
                print(line)
            if len(self.tree_lines) >= MAX_TREE_ITEMS:
                print(f"{C.WARN}... (目录树已截断){C.END}")


def main():
    target = input("请输入要分析的目录(. 表示当前目录): ").strip() or "."
    if not os.path.exists(target):
        print(f"{C.WARN}❌ 路径不存在: {target}{C.END}")
        return
    if not os.path.isdir(target):
        print(f"{C.WARN}❌ 不是目录: {target}{C.END}")
        return

    print(f"{C.OK}⏳ 正在扫描 {target} ...{C.END}")
    analyzer = DirAnalyzer(target)
    analyzer.scan()
    if SHOW_TREE:
        analyzer.print_tree()
    analyzer.summary()
    analyzer.report_ext()
    analyzer.report_levels()
    analyzer.report_buckets()
    analyzer.report_large()
    analyzer.report_deep_dirs()
    print(f"\n{C.OK}✅ 分析完成! 共扫描 {fmt_num(analyzer.scanned)} 个条目{C.END}")

if __name__ == "__main__":
    main()
