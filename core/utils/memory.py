import ctypes
import ctypes.util


# * AI Generated
def tune_malloc():
    '''
    限制 glibc 的多线程堆行为，防止长时间下载时 RSS 持续上涨。

    glibc 的 malloc 是「每线程一个 arena」的多仓库设计：线程第一次分配时
    绑定一个 arena，之后都从自己的分仓切内存，减少全局锁竞争。默认上限是
    8 × CPU 核数（64 位最多 32 个），每个非主 arena 会预留 64 MiB 的虚拟
    地址空间。

    '''
    try:
        libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6")
        libc.mallopt(-8, 2)              # M_ARENA_MAX
        libc.mallopt(-3, 128 * 1024)     # M_MMAP_THRESHOLD
        libc.mallopt(-1, 128 * 1024)     # M_TRIM_THRESHOLD
    except Exception as e:
        pass