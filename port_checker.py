# -*- coding: utf-8 -*-
"""
端口占用检测器 v2.0
功能：
1. 先UAC提权到管理员
2. 检测用户输入指定端口是否被占用
3. 如果被占用，找出是哪个进程占用
4. 允许用户强制杀死该进程（系统进程需二次确认）
5. 支持批量查询（逗号/空格/范围分隔）
"""
import os
import sys
import ctypes
import subprocess
import re


# ============ UAC 提权 ============
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def request_admin():
    """请求 UAC 提权，以管理员身份重新运行"""
    if not is_admin():
        print("[!] 需要管理员权限，正在请求 UAC 提权...")
        # 重新以管理员运行自身
        params = ' '.join([f'"{a}"' for a in sys.argv])
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{sys.argv[0]}" {params}', None, 1)
        sys.exit(0)


OK = '\033[1;32m'
WARN = '\033[1;33m'
RED = '\033[1;31m'
HDR = '\033[1;36m'
END = '\033[0m'


# ============ 系统关键进程列表 ============
SYSTEM_PROCESSES = {
    'system', 'idle', 'smss.exe', 'csrss.exe', 'wininit.exe',
    'services.exe', 'lsass.exe', 'winlogon.exe', 'winlogonexe',
    'svchost.exe', 'spoolsv.exe', 'explorer.exe', 'dwm.exe'
}


def parse_input(s):
    """解析端口输入：支持 '80, 443, 8000-8010, 22' 等格式"""
    ports = set()
    s = s.replace('，', ',')
    for part in s.replace(',', ' ').split():
        part = part.strip()
        if not part:
            continue
        if '-' in part:  # 范围
            a, b = part.split('-')
            try:
                a, b = int(a), int(b)
                for p in range(a, b + 1):
                    ports.add(p)
            except ValueError:
                continue
        else:  # 单个端口
            try:
                ports.add(int(part))
            except ValueError:
                pass
    return sorted(ports)


def get_netstat():
    """获取所有 TCP 监听/连接状态的端口→PID 映射"""
    result = subprocess.run(
        ['netstat', '-ano'], capture_output=True, text=True, errors='ignore')
    port_pid = {}  # 端口 -> (状态, pid)
    for line in result.stdout.splitlines():
        line = line.strip()
        # 匹配形如  TCP    0.0.0.0:80     0.0.0.0:0    LISTENING     1234
        m = re.match(r'^\s*(TCP|UDP)\s+(\S+):(\d+)\s+(\S+)\s+(\w+)\s*(\d*)\s*$', line)
        if m:
            proto, local, port, remote, state, pid = m.groups()
            try:
                port = int(port)
            except ValueError:
                continue
            # 只关心监听和被占用状态
            if 'LISTEN' in state.upper() or (remote and remote.split(':')[-1] != '0'):
                port_pid[port] = (state, pid)
    return port_pid


def get_process_name(pid):
    """通过 tasklist 获取进程名"""
    try:
        result = subprocess.run(
            ['tasklist', '/FI', f'PID eq {pid}'], capture_output=True, text=True, errors='ignore')
        for line in result.stdout.splitlines():
            if pid in line and '.exe' in line.lower():
                return line.split()[0]
    except Exception:
        pass
    return 'Unknown'


def get_process_detail(pid):
    """获取进程详细信息（命令行等）"""
    try:
        result = subprocess.run(
            ['wmic', 'process', 'where', f'ProcessId={pid}', 'get', 'Name,CommandLine', '/format:list'],
            capture_output=True, text=True, errors='ignore')
        name = cmd = ''
        for line in result.stdout.splitlines():
            if line.startswith('Name='):
                name = line.split('=', 1)[1].strip()
            elif line.startswith('CommandLine='):
                cmd = line.split('=', 1)[1].strip()[:120]
        return name or get_process_name(pid), cmd
    except Exception:
        return get_process_name(pid), ''


def kill_process(pid):
    """强制杀死进程"""
    result = subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                            capture_output=True, text=True)
    if result.returncode == 0:
        return True, "已强制终止"
    return False, result.stderr.strip() or "终止失败（可能无权限或进程已退出）"


def check_port(port, port_pid):
    """检查单个端口"""
    print(f"\n{'─'*60}")
    print(f"{HDR}📡 端口 {port}{END}")
    if port < 0 or port > 65535:
        print(f"{RED}❌ 无效端口范围 (0-65535){END}")
        return
    if port not in port_pid:
        print(f"{OK}✅ 端口 {port} 未被占用{END}")
        return

    state, pid = port_pid[port]
    pid = pid.strip()
    name = get_process_name(pid)
    cmd = ""
    try:
        n2, cmd = get_process_detail(pid)
        if n2:
            name = n2
    except Exception:
        pass

    # 判断是否系统关键进程
    is_system = name.lower() in SYSTEM_PROCESSES or os.path.basename(cmd).lower() in SYSTEM_PROCESSES

    print(f"{RED}⚠️  端口 {port} 已被占用！{END}")
    print(f"   占用进程: {name}")
    print(f"   PID     : {pid}")
    print(f"   状态    : {state}")
    if cmd:
        print(f"   命令行  : {cmd}")
    if is_system:
        print(f"{WARN}⚠️  检测到系统关键进程！{END}")

    # 首次确认
    kill_choice = input(f"\n是否强制终止进程 {name} (PID {pid})? [y/N]: ").strip().lower()
    if kill_choice in ('y', 'yes'):
        # 系统关键进程：二次确认
        if is_system:
            print(f"{WARN}⚠️  警告: {name} 是系统关键进程！强制终止可能导致系统不稳定或崩溃。{END}")
            confirm = input(f"{RED}❗ 二次确认: 确定要强制终止系统进程 {name} (PID {pid})? (输入 YES 确认): {END}").strip()
            if confirm.upper() != 'YES':
                print(f"{OK}↩️ 已取消终止（未输入 YES）{END}")
                return
        ok, msg = kill_process(pid)
        if ok:
            print(f"{OK}✅ {msg}: {name} (PID {pid}){END}")
        else:
            print(f"{RED}❌ {msg}{END}")


def main():
    # ===== UAC 提权 =====
    if os.name == 'nt':
        request_admin()

    print('=' * 60)
    print(f"{HDR}🔍 端口占用检测器 v2.0{END}")
    print('=' * 60)
    print("支持批量查询: 逗号/空格分隔，支持范围 如 '80, 443, 8000-8010'")
    print("系统进程强制终止需二次确认 (输入 YES)")

    while True:
        inp = input("\n请输入要查询的端口 (输入 q 退出): ").strip()
        if inp.lower() in ('q', 'quit', 'exit'):
            break
        if not inp:
            continue

        ports = parse_input(inp)
        if not ports:
            print(f"{WARN}⚠️  无法解析端口输入，请检查格式{END}")
            continue
        if len(ports) > 50:
            print(f"{WARN}⚠️  单次最多查询 50 个端口{END}")
            continue

        print(f"{OK}⏳ 正在扫描 {len(ports)} 个端口...{END}")
        port_pid = get_netstat()
        for port in ports:
            check_port(port, port_pid)

    print("\n👋 已退出")


if __name__ == "__main__":
    main()
