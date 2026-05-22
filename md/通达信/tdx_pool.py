"""示例：利用 pytdx 的 IP 池自动切换主备行情服务器。"""

from __future__ import annotations

import logging
import pprint
import random

from pytdx.config.hosts import hq_hosts
from pytdx.hq import TdxHq_API
from pytdx.pool.hqpool import TdxHqPool_API
from pytdx.pool.ippool import AvailableIPPool


def build_api_with_pool(sample_size: int = 5) -> TdxHqPool_API:
    """构建带 IP 池的 TdxHqPool_API 对象。"""

    # 从官方主站列表中抽取若干 IP 作为候选池
    ip_ports = [(host, port) for _, host, port in hq_hosts]
    random.shuffle(ip_ports)
    selected = ip_ports[:sample_size]

    ippool = AvailableIPPool(TdxHq_API, selected)
    return TdxHqPool_API(TdxHq_API, ippool)


def get_fastest_ip(
    sample_size: int = 5, enable_logging: bool = True
) -> tuple[str, int]:
    """
    从 IP 池中测试并返回最快的 IP 地址。

    Args:
        sample_size: IP 池采样大小，默认 5
        enable_logging: 是否启用日志记录，默认 True

    Returns:
        tuple: (host, port) 元组，表示最快的 IP 地址

    Example:
        >>> fastest_ip = get_fastest_ip()
        >>> host, port = fastest_ip
        >>> print(f"最快IP: {host}:{port}")
    """
    # 构建 IP 池
    api_pool = build_api_with_pool(sample_size)
    # 获取最快的 IP
    (fastest_ip,) = api_pool.ippool.sync_get_top_n(1)
    
    if enable_logging:
        logging.info("最快IP: %s:%s", fastest_ip[0], fastest_ip[1])
    
    return fastest_ip


def select_primary_and_backup_servers(
    sample_size: int = 5, enable_logging: bool = True
) -> tuple[tuple[str, int], tuple[str, int], TdxHqPool_API]:
    """
    构建 IP 池并挑选主备服务器。

    Args:
        sample_size: IP 池采样大小，默认 5
        enable_logging: 是否启用日志记录，默认 True

    Returns:
        tuple: (主站IP, 备站IP, api_pool对象)
            - 主站IP: (host, port) 元组
            - 备站IP: (host, port) 元组
            - api_pool: TdxHqPool_API 对象，可用于后续数据请求

    Example:
        >>> primary_ip, backup_ip, api_pool = select_primary_and_backup_servers()
        >>> logging.info("主站: %s, 备站: %s", primary_ip, backup_ip)
        >>> with api_pool.connect(primary_ip, backup_ip):
        ...     result = api_pool.get_xdxr_info(0, "000001")
    """
    # 构建 IP 池
    api_pool = build_api_with_pool(sample_size)
    # 挑选主备服务器
    primary_ip, hot_backup_ip = api_pool.ippool.sync_get_top_n(2)
    
    if enable_logging:
        logging.info("选择主站: %s, 备站: %s", primary_ip, hot_backup_ip)
    
    return primary_ip, hot_backup_ip, api_pool


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    # 示例1：获取最快的IP
    print("=" * 60)
    print("示例1：获取最快的IP")
    print("=" * 60)
    try:
        fastest_ip = get_fastest_ip(sample_size=10)
        host, port = fastest_ip
        print(f"最快IP: {host}:{port}")
    except Exception as e:
        logging.error(f"获取最快IP失败: {e}")

    # 示例2：构建 IP 池，并挑选主备服务器
    print("\n" + "=" * 60)
    print("示例2：挑选主备服务器")
    print("=" * 60)
    try:
        primary_ip, hot_backup_ip, api_pool = select_primary_and_backup_servers()
        print(f"主站: {primary_ip[0]}:{primary_ip[1]}")
        print(f"备站: {hot_backup_ip[0]}:{hot_backup_ip[1]}")
    except Exception as e:
        logging.error(f"获取主备服务器失败: {e}")

    # 使用上下文管理自动连接主备站
    # with api_pool.connect(primary_ip, hot_backup_ip):
    #     logging.info("开始请求除权信息 ...")
    #     result = api_pool.get_xdxr_info(0, "000001")  # 深市平安银行
    #     logging.info("请求完成，结果如下：")
    #     pprint.pprint(result)


if __name__ == "__main__":
    main()


