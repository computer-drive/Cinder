
def levenshtein(a: str, b: str) -> int:
    '''计算两个字符串之间的编辑距离'''
    m, n = len(a), len(b)
    # 只保留两行，空间 O(min(m,n))
    if m < n:
        a, b = b, a
        m, n = n, m
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            cur[j] = min(
                prev[j] + 1,        # 删除
                cur[j-1] + 1,       # 插入
                prev[j-1] + cost    # 替换/匹配
            )
        prev = cur
    return prev[n]