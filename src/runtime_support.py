"""Explicit host accounting; portable execution never pretends to be POSIX."""
import os
import sys


def portable_enabled():
    return os.environ.get('STAGECONFLUENCE_PORTABLE') == '1'


def peak_rss_kib():
    if os.name == 'posix':
        import resource
        raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return (raw + 1023)//1024 if sys.platform == 'darwin' else raw
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        size = ctypes.c_size_t
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                        ('PeakWorkingSetSize', size), ('WorkingSetSize', size),
                        ('QuotaPeakPagedPoolUsage', size), ('QuotaPagedPoolUsage', size),
                        ('QuotaPeakNonPagedPoolUsage', size), ('QuotaNonPagedPoolUsage', size),
                        ('PagefileUsage', size), ('PeakPagefileUsage', size)]
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        record = Counters()
        record.cb = ctypes.sizeof(record)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(record), record.cb):
            raise OSError(ctypes.get_last_error(), 'GetProcessMemoryInfo failed')
        return (record.PeakWorkingSetSize + 1023)//1024
    return None


def legacy_limits():
    if os.name == 'posix':
        import resource
        if hasattr(os, 'sched_getaffinity'):
            os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})
        resource.setrlimit(resource.RLIMIT_AS, (3*1024**3, 3*1024**3))
        resource.setrlimit(resource.RLIMIT_CPU, (180,185))
    elif not portable_enabled():
        raise RuntimeError('legacy CLI requires POSIX limits or explicit portable mode')


def scope():
    return dict(platform=sys.platform, portable=portable_enabled(),
                posix_child_cpu_address_space_limits=os.name == 'posix',
                rss_metric='ru_maxrss KiB on Linux; PeakWorkingSetSize/1024 on Windows')
