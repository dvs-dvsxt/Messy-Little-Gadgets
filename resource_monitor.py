# -*- coding: utf-8 -*-
"""
资源大户监控器 v1.0
功能：查询内存里面 Top10 的内存大户和 CPU 大户，30s 刷新
- 实时显示内存 Top10 和 CPU Top10
- 每 30 秒自动刷新
- 显示进程名、PID、内存占用、CPU 占用
"""
import os
import time
import sys

try:
    import psutil
except ImportError:
    print("需要安装 psutil: pip install psutil")
    sys.exit(1)

REFRESH = 30  # 刷新间隔（秒）
TOP_N = 10

OK = '\033[1;32m'
WARN = '\033[1;33m'
RED = '\033[1;31m'
HDR = '\033[1;36m'
END = '\033[0m'


def human_size(n):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if n < 1024.0:
            return f"{n:.1f} {unit}" if unit != 'B' else f"{int(n)} B"
        n /= 1024.0
    return f"{n:.1f} PB"


def get_top(by='memory'):
    """按内存或CPU取Top N进程"""
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent', 'memory_info']):
        try:
            procs.append(p.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    if by == 'memory':
        procs.sort(key=lambda x: x['memory_percent'] or 0, reverse=True)
    else:
        procs.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
    return procs[:TOP_N]


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def show_header():
    print('=' * 78)
    print(f"{HDR}📊 资源大户监控器   (每30秒自动刷新, Ctrl+C 退出){END}")
    print('=' * 78)
    vm = psutil.virtual_memory()
    try:
        cpu = psutil.cpu_percent(interval=None)
    except Exception:
        cpu = 0
    cores = psutil.cpu_count(logical=False)
    lcores = psutil.cpu_count()
    print(f"💾 总内存: {human_size(vm.total)} | 已用: {human_size(vm.used)} "
          f"({vm.percent}%) | 可用: {human_size(vm.available)}")
    print(f"⚡ CPU: {cpu}% | 物理核心: {cores} | 逻辑核心: {lcores}")
    print('=' * 78)


def show_top(data, by):
    if by == 'memory':
        label = "内存"
    else:
        label = "CPU"

    print('-' * 78)
    print(f"{HDR}🔝 Top{TOP_N} {label}大户{END}")
    print('-' * 78)
    print(f"{'#':<4}{'进程名':<30}{'PID':<8}{'占用':<14}{'占比':>8}")
    print('-' * 78)
    for i, d in enumerate(data, 1):
        name = (d.get('name') or '?')[:28]
        pid = d.get('pid', '?')
        if by == 'memory':
            mem_b = (d.get('memory_info') or {}).rss or 0
            disp = human_size(mem_b)
            pct = d.get('memory_percent') or 0
        else:
            val = d.get('cpu_percent') or 0
            disp = f"{val:.1f}%"
            pct = val
        color = OK if pct < 30 else (WARN if pct < 60 else RED)
        bar = '█' * min(int(pct / 2), 20)
        print(f"{i:<4}{name:<30}{pid:<8}{disp:<14} {color}{bar}{END}")


def warm_cpu():
    for p in psutil.process_iter(['cpu_percent']):
        try:
            p.cpu_percent(None)
        except Exception:
            pass


def main():
    # 预热 cpu_percent
    warm_cpu()
    time.sleep(0.5)

    try:
        while True:
            clear()
            show_header()
            mem_top = get_top('memory')
            cpu_top = get_top('cpu')
            show_top(mem_top, 'memory')
            show_top(cpu_top, 'cpu')
            now = time.strftime('%H:%M:%S')
            print('=' * 78)
            print(f"  最后刷新: {now}  下次刷新: {REFRESH} 秒后...")
            try:
                time.sleep(REFRESH)
            except KeyboardInterrupt:
                break
            warm_cpu()
    except KeyboardInterrupt:
        pass
    print(f"\n{'='*78}")
    print("👋 已退出监控")


if __name__ == "__main__":
    main()
