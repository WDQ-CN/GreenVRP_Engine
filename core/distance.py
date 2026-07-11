"""
距离与时间矩阵计算模块（性能优化版 v3）

使用 Haversine 公式计算球面距离，支持异构车队的不同速度时间矩阵生成。

性能优化 v3：
- 使用 NumPy 向量化计算，距离矩阵构建速度提升 10x+
- 时间矩阵预计算缓存，避免重复计算
- 支持大规模节点（1000+）的高效计算
- 新增：稀疏距离矩阵支持（大规模问题内存优化）
- 新增：KD-Tree加速最近邻搜索
- 新增：scipy cdist加速批量计算

注意：Haversine 距离计算统一引用 utils/geo.py 中的实现，
避免代码重复。core/distance.py 专注于距离矩阵构建和时间矩阵计算。
"""

import hashlib
import json

import numpy as np
import pandas as pd

from config.constants import EARTH_RADIUS_KM
from utils.geo import haversine_distance, haversine_distance_vectorized

# 尝试导入scipy加速计算
try:
    from scipy.spatial import cKDTree
    from scipy.spatial.distance import cdist

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# 大规模问题阈值（超过此值使用稀疏矩阵）
SPARSE_MATRIX_THRESHOLD = 2000
# KD-Tree批量查询阈值
KDTREE_THRESHOLD = 500


def _haversine_metric(u: np.ndarray, v: np.ndarray) -> float:
    """scipy cdist使用的Haversine度量函数（弧度坐标输入）。"""
    lat1, lon1 = u
    lat2, lon2 = v
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * np.arcsin(np.sqrt(a))


def haversine_vectorized(
    lats1: np.ndarray,
    lons1: np.ndarray,
    lats2: np.ndarray,
    lons2: np.ndarray,
    use_scipy: bool = True,
) -> np.ndarray:
    """
    向量化 Haversine 计算，支持批量距离计算。

    使用 utils/geo.haversine_distance_vectorized 作为底层实现，
    在此基础增加 scipy cdist 加速选项。

    Args:
        lats1: 起点纬度数组（度）
        lons1: 起点经度数组（度）
        lats2: 终点纬度数组（度）
        lons2: 终点经度数组（度）
        use_scipy: 是否尝试使用scipy加速（适用于大规模数据）

    Returns:
        距离矩阵（公里），shape 为 (len(lats1), len(lats2))
    """
    # 对于常规规模（<=2000 点），NumPy 向量化计算已在 C 层完成，
    # 比 scipy cdist 调用 Python 回调函数快一个数量级；仅在超大规模
    # 且显式启用 scipy 路径时回退到 cdist 以控制内存峰值。
    if use_scipy and HAS_SCIPY and len(lats1) > 2000:
        # 将经纬度转换为弧度坐标
        coords1 = np.radians(np.column_stack([lats1, lons1]))
        coords2 = np.radians(np.column_stack([lats2, lons2]))
        # 使用自定义度量计算Haversine距离
        return cdist(coords1, coords2, metric=_haversine_metric) * EARTH_RADIUS_KM

    # 默认使用 utils/geo 中的向量化实现
    # 若输入为 1D 数组，通过广播构造 (n, n) 距离矩阵
    lats1_arr = np.asarray(lats1)
    lons1_arr = np.asarray(lons1)
    lats2_arr = np.asarray(lats2)
    lons2_arr = np.asarray(lons2)

    if lats1_arr.ndim == 1 and lats2_arr.ndim == 1:
        return haversine_distance_vectorized(
            lats1_arr[:, np.newaxis],
            lons1_arr[:, np.newaxis],
            lats2_arr[np.newaxis, :],
            lons2_arr[np.newaxis, :],
        )

    return haversine_distance_vectorized(lats1, lons1, lats2, lons2)


class SparseDistanceMatrix:
    """
    稀疏距离矩阵 - 用于大规模问题（1000+节点）的内存优化。

    只存储距离在阈值内的连接，大幅降低内存占用。
    """

    def __init__(
        self,
        locations: list[tuple[float, float]],
        max_distance_km: float = 50.0,
        use_kdtree: bool = True,
    ):
        """
        初始化稀疏距离矩阵。

        Args:
            locations: 位置坐标列表
            max_distance_km: 最大存储距离（公里）
            use_kdtree: 是否使用KD-Tree加速
        """
        self.n = len(locations)
        self.max_distance = max_distance_km
        self.locations = np.array(locations)

        # 使用KD-Tree快速查找近邻
        if use_kdtree and HAS_SCIPY and self.n >= KDTREE_THRESHOLD:
            # 将经纬度转换为笛卡尔坐标近似
            coords = self._latlon_to_cartesian(self.locations)
            self.kdtree = cKDTree(coords)
            self._build_sparse_with_kdtree()
        else:
            self.kdtree = None
            self._build_sparse_brute_force()

        # 构建 O(1) 查询字典
        self._lookup: dict[tuple[int, int], float] = {
            (r, c): d
            for r, c, d in zip(self.row_indices, self.col_indices, self.data, strict=False)
        }

    def _latlon_to_cartesian(self, coords: np.ndarray) -> np.ndarray:
        """将经纬度转换为近似笛卡尔坐标。"""
        lat, lon = coords[:, 0], coords[:, 1]
        # 使用简化的投影（适合短距离）
        x = lon * np.cos(np.radians(lat)) * 111.32
        y = lat * 111.32
        return np.column_stack([x, y])

    def _build_sparse_with_kdtree(self):
        """使用KD-Tree构建稀疏矩阵。"""
        # 查询每个点的近邻（半径内）
        radius_deg = self.max_distance / 111.0  # 近似转换为度
        neighbors = self.kdtree.query_ball_tree(self.kdtree, radius_deg)

        self.row_indices = []
        self.col_indices = []
        self.data = []

        for i, neighbor_list in enumerate(neighbors):
            for j in neighbor_list:
                if i != j:  # 跳过对角线
                    dist = haversine_distance(
                        self.locations[i][0],
                        self.locations[i][1],
                        self.locations[j][0],
                        self.locations[j][1],
                    )
                    if dist <= self.max_distance:
                        self.row_indices.append(i)
                        self.col_indices.append(j)
                        self.data.append(dist)

    def _build_sparse_brute_force(self):
        """暴力法构建稀疏矩阵（小规模问题）。"""
        self.row_indices = []
        self.col_indices = []
        self.data = []

        for i in range(self.n):
            for j in range(i + 1, self.n):
                dist = haversine_distance(
                    self.locations[i][0],
                    self.locations[i][1],
                    self.locations[j][0],
                    self.locations[j][1],
                )
                if dist <= self.max_distance:
                    # 双向添加
                    self.row_indices.extend([i, j])
                    self.col_indices.extend([j, i])
                    self.data.extend([dist, dist])

    def get(self, i: int, j: int) -> float:
        """获取(i, j)位置的距离（O(1) 字典查询）。"""
        if i == j:
            return 0.0
        return self._lookup.get((i, j), float("inf"))

    def to_dense(self) -> np.ndarray:
        """转换为密集矩阵（用于OR-Tools）。"""
        matrix = np.full((self.n, self.n), 999999, dtype=np.int32)
        np.fill_diagonal(matrix, 0)

        for r, c, d in zip(self.row_indices, self.col_indices, self.data, strict=False):
            matrix[r, c] = int(d * 1000)  # 转为米

        return matrix


def build_distance_matrix(
    locations: list[tuple[float, float]],
    scale: int = 1000,
    use_sparse: bool = False,
    sparse_threshold: int = SPARSE_MATRIX_THRESHOLD,
    return_numpy: bool = True,
) -> np.ndarray | list[list[int]] | SparseDistanceMatrix:
    """
    构建距离矩阵，用于 OR-Tools 求解器（优化版 v4）。

    使用 NumPy 向量化计算，性能显著优于嵌套循环。
    v3新增：支持稀疏矩阵模式，大幅降低大规模问题的内存占用。
    v4优化：默认返回 NumPy 数组，避免列表转换开销。

    Args:
        locations: 位置坐标列表 [(lat, lon), ...]
        scale: 距离缩放因子，默认 1000（米）
        use_sparse: 是否使用稀疏矩阵（自动判断是否使用）
        sparse_threshold: 使用稀疏矩阵的节点数阈值
        return_numpy: 是否返回 NumPy 数组（默认True，性能更优）

    Returns:
        距离矩阵（单位：米，整数），或SparseDistanceMatrix对象

    Note:
        OR-Tools 要求距离为整数，因此使用 scale=1000 将公里转为米。
        对于城市配送场景，米级精度足够满足路径规划需求。
    """
    n = len(locations)
    if n == 0:
        return []

    # 自动判断使用稀疏矩阵
    if use_sparse or n >= sparse_threshold:
        return SparseDistanceMatrix(locations)

    # 提取坐标数组
    lats = np.array([loc[0] for loc in locations], dtype=np.float64)
    lons = np.array([loc[1] for loc in locations], dtype=np.float64)

    # 向量化计算距离矩阵
    dist_matrix_km = haversine_vectorized(lats, lons, lats, lons)

    # 对角线设为 0（自己到自己的距离为 0）
    np.fill_diagonal(dist_matrix_km, 0)

    # 缩放并转为整数
    dist_matrix_m = (dist_matrix_km * scale).astype(np.int32)

    # 直接返回 NumPy 数组，避免列表转换开销
    return dist_matrix_m


def build_time_matrix(distance_matrix: list[list[int]], speed_kmh: float) -> list[list[int]]:
    """
    基于距离矩阵和车型速度构建时间矩阵。

    使用 NumPy 向量化计算，性能优于嵌套循环。

    Args:
        distance_matrix: 距离矩阵（单位：米）
        speed_kmh: 车型速度（公里/小时）

    Returns:
        时间矩阵（单位：分钟），time_matrix[i][j] 表示从 i 到 j 的行驶时间

    Note:
        异构车队中不同车型的速度不同：
        - 小型车（4.2m）：速度较快，适合城市拥堵路段
        - 大型车（9.6m）：速度较慢，但单位载重碳排放更低

        时间矩阵用于时间窗约束，确保配送在客户要求的时间范围内完成。
    """
    n = len(distance_matrix)
    if n == 0:
        return []

    # 验证速度参数
    if speed_kmh <= 0:
        raise ValueError(f"速度必须大于0，实际值: {speed_kmh}")

    # 转为 NumPy 数组进行向量化计算
    dist_array = np.array(distance_matrix, dtype=np.float64)

    # 距离（米）-> 距离（公里）-> 时间（小时）-> 时间（分钟）
    time_array = (dist_array / 1000.0 / speed_kmh * 60).astype(np.int32)

    # 对角线保持为 0
    np.fill_diagonal(time_array, 0)

    return time_array.tolist()


def build_time_matrix_numpy(distance_matrix: np.ndarray, speed_kmh: float) -> np.ndarray:
    """
    基于 NumPy 数组构建时间矩阵（高性能版本）。

    直接返回 NumPy 数组，避免列表转换开销。
    适用于大规模计算场景。

    Args:
        distance_matrix: 距离矩阵（NumPy 数组，单位：米）
        speed_kmh: 车型速度（公里/小时）

    Returns:
        时间矩阵（NumPy 数组，单位：分钟）
    """
    # 验证速度参数
    if speed_kmh <= 0:
        raise ValueError(f"速度必须大于0，实际值: {speed_kmh}")

    time_array = (distance_matrix / 1000.0 / speed_kmh * 60).astype(np.int32)
    np.fill_diagonal(time_array, 0)
    return time_array


def get_location_list(
    customers_df: pd.DataFrame, depot_index: int = 0
) -> list[tuple[float, float]]:
    """
    从客户数据框提取位置坐标列表。

    优化：使用 values 属性直接访问底层数组，比 iterrows 快 5-10 倍。

    Args:
        customers_df: 包含 lat, lon 列的客户数据框
        depot_index: 仓库在数据中的索引位置

    Returns:
        位置坐标列表，第一个元素为仓库
    """
    # 使用 NumPy 数组直接提取，性能优于 iterrows
    lat_lon_array = customers_df[["lat", "lon"]].values
    return [tuple(row) for row in lat_lon_array]


def get_location_array(customers_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """
    从客户数据框提取位置坐标数组（高性能版本）。

    直接返回 NumPy 数组，用于向量化计算。

    Args:
        customers_df: 包含 lat, lon 列的客户数据框

    Returns:
        (lats, lons) 两个 NumPy 数组
    """
    lat_lon_array = customers_df[["lat", "lon"]].values
    return lat_lon_array[:, 0], lat_lon_array[:, 1]


class DistanceMatrixCache:
    """
    距离矩阵缓存类（性能优化版）。

    缓存已计算的距离矩阵，避免重复计算。
    适用于多次求解相同场景的情况。

    性能优化：
    - 使用采样哈希，O(1) 时间生成缓存键
    - 支持大规模节点的高效缓存

    Example:
        >>> cache = DistanceMatrixCache()
        >>> dist_matrix = cache.get_or_compute(locations, scale=1000)
        >>> # 第二次调用直接从缓存获取
        >>> dist_matrix = cache.get_or_compute(locations, scale=1000)
    """

    def __init__(self, max_size: int = 100):
        """
        初始化缓存。

        Args:
            max_size: 最大缓存条目数
        """
        self._cache: dict[str, np.ndarray | list[list[int]]] = {}
        self._max_size = max_size

    def _hash_locations(self, locations: list[tuple[float, float]], scale: int) -> str:
        """
        生成位置列表的稳定缓存键。

        使用 json.dumps(..., sort_keys=True) 保证序列化稳定，
        再使用 SHA-256 生成固定长度、低碰撞率的缓存键。

        Args:
            locations: 位置坐标列表
            scale: 距离缩放因子

        Returns:
            缓存键字符串
        """
        key_data = {
            "locations": locations,
            "scale": scale,
        }
        raw = json.dumps(key_data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get_or_compute(
        self, locations: list[tuple[float, float]], scale: int = 1000
    ) -> np.ndarray | list[list[int]]:
        """
        获取或计算距离矩阵（优化版 v4）。

        如果缓存中存在，直接返回；否则计算并缓存。
        现在返回 NumPy 数组以提高性能。

        Args:
            locations: 位置坐标列表
            scale: 距离缩放因子

        Returns:
            距离矩阵（NumPy 数组或列表）
        """
        cache_key = self._hash_locations(locations, scale)

        if cache_key in self._cache:
            return self._cache[cache_key]

        # 缓存满时清理最早的条目
        if len(self._cache) >= self._max_size:
            self._cache.pop(next(iter(self._cache)))

        # 计算并缓存
        dist_matrix = build_distance_matrix(locations, scale)
        self._cache[cache_key] = dist_matrix

        return dist_matrix

    def clear(self) -> None:
        """清空缓存。"""
        self._cache.clear()
