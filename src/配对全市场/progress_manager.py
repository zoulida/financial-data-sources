"""
进度管理模块

支持批量处理和断点续传功能，将大量配对分批处理，
每批完成后保存进度，支持从中断处继续运行。
"""

import os
import pickle
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from config import Config

logger = logging.getLogger(__name__)


class ProgressManager:
    """进度管理器"""
    
    def __init__(self, progress_file: str = None):
        """
        初始化进度管理器
        
        Args:
            progress_file: 进度文件路径，默认使用配置中的路径
        """
        self.progress_file = Path(progress_file or Config.Progress.PROGRESS_FILE)
        self.batch_size = Config.Progress.BATCH_SIZE
        self.save_interval = Config.Progress.SAVE_INTERVAL
        
        # 确保进度文件目录存在
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.progress_data = self._load_progress()
        
        logger.info(f"进度管理器初始化完成，批大小: {self.batch_size}")
    
    def _load_progress(self) -> Dict:
        """
        加载进度文件
        
        Returns:
            进度数据字典
        """
        if not self.progress_file.exists():
            logger.info("未找到进度文件，将创建新的进度记录")
            return {
                'completed_pairs': set(),
                'batch_results': [],
                'current_batch': 0,
                'total_batches': 0,
                'start_time': None,
                'last_update': None,
                'status': 'new'
            }
        
        try:
            with open(self.progress_file, 'rb') as f:
                progress_data = pickle.load(f)
            logger.info(f"加载进度文件成功，已完成 {len(progress_data.get('completed_pairs', set()))} 个配对")
            return progress_data
        except Exception as e:
            logger.error(f"加载进度文件失败: {e}")
            return self._load_progress()  # 返回新的进度数据
    
    def _save_progress(self):
        """保存进度到文件"""
        try:
            self.progress_data['last_update'] = datetime.now().isoformat()
            
            with open(self.progress_file, 'wb') as f:
                pickle.dump(self.progress_data, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            logger.debug(f"进度已保存")
        except Exception as e:
            logger.error(f"保存进度文件失败: {e}")
    
    def initialize_task(self, total_pairs: List[Tuple[str, str]]):
        """
        初始化任务
        
        Args:
            total_pairs: 所有待处理的配对列表
        """
        total_batches = (len(total_pairs) + self.batch_size - 1) // self.batch_size
        
        self.progress_data.update({
            'total_pairs': len(total_pairs),
            'total_batches': total_batches,
            'start_time': datetime.now().isoformat(),
            'status': 'running'
        })
        
        logger.info(f"任务初始化完成，总配对数: {len(total_pairs)}, 总批次: {total_batches}")
        self._save_progress()
    
    def get_remaining_pairs(
        self,
        all_pairs: List[Tuple[str, str]]
    ) -> List[Tuple[str, str]]:
        """
        获取尚未处理的配对
        
        Args:
            all_pairs: 所有配对列表
            
        Returns:
            尚未处理的配对列表
        """
        completed = self.progress_data.get('completed_pairs', set())
        
        remaining = [pair for pair in all_pairs if pair not in completed]
        
        logger.info(f"总配对: {len(all_pairs)}, 已完成: {len(completed)}, 剩余: {len(remaining)}")
        
        return remaining
    
    def create_batches(
        self,
        pairs: List[Tuple[str, str]]
    ) -> List[List[Tuple[str, str]]]:
        """
        将配对列表分成批次
        
        Args:
            pairs: 配对列表
            
        Returns:
            批次列表
        """
        batches = []
        
        for i in range(0, len(pairs), self.batch_size):
            batch = pairs[i:i + self.batch_size]
            batches.append(batch)
        
        logger.info(f"创建了 {len(batches)} 个批次")
        
        return batches
    
    def mark_batch_completed(
        self,
        batch_pairs: List[Tuple[str, str]],
        batch_results: List[Dict],
        batch_index: int
    ):
        """
        标记批次完成
        
        Args:
            batch_pairs: 批次中的配对列表
            batch_results: 批次处理结果
            batch_index: 批次索引
        """
        # 添加到已完成集合
        completed_pairs = self.progress_data.get('completed_pairs', set())
        completed_pairs.update(batch_pairs)
        self.progress_data['completed_pairs'] = completed_pairs
        
        # 保存批次结果
        batch_results_list = self.progress_data.get('batch_results', [])
        batch_results_list.append({
            'batch_index': batch_index,
            'batch_size': len(batch_pairs),
            'results': batch_results,
            'timestamp': datetime.now().isoformat()
        })
        self.progress_data['batch_results'] = batch_results_list
        
        # 更新当前批次
        self.progress_data['current_batch'] = batch_index + 1
        
        # 按保存间隔保存进度
        if (batch_index + 1) % self.save_interval == 0:
            self._save_progress()
            logger.info(f"批次 {batch_index + 1} 完成，进度已保存")
    
    def finalize_task(self):
        """完成任务"""
        self.progress_data['status'] = 'completed'
        self.progress_data['end_time'] = datetime.now().isoformat()
        
        self._save_progress()
        
        logger.info("任务已完成，进度已保存")
    
    def get_all_results(self) -> List[Dict]:
        """
        获取所有批次的结果
        
        Returns:
            所有结果的列表
        """
        all_results = []
        
        batch_results_list = self.progress_data.get('batch_results', [])
        
        for batch_data in batch_results_list:
            all_results.extend(batch_data.get('results', []))
        
        logger.info(f"获取到 {len(all_results)} 个配对结果")
        
        return all_results
    
    def get_progress_info(self) -> Dict:
        """
        获取进度信息
        
        Returns:
            进度信息字典
        """
        completed_pairs = len(self.progress_data.get('completed_pairs', set()))
        total_pairs = self.progress_data.get('total_pairs', 0)
        current_batch = self.progress_data.get('current_batch', 0)
        total_batches = self.progress_data.get('total_batches', 0)
        
        progress_pct = (completed_pairs / total_pairs * 100) if total_pairs > 0 else 0
        batch_pct = (current_batch / total_batches * 100) if total_batches > 0 else 0
        
        info = {
            'status': self.progress_data.get('status', 'unknown'),
            'total_pairs': total_pairs,
            'completed_pairs': completed_pairs,
            'remaining_pairs': total_pairs - completed_pairs,
            'progress_percentage': progress_pct,
            'current_batch': current_batch,
            'total_batches': total_batches,
            'batch_percentage': batch_pct,
            'start_time': self.progress_data.get('start_time'),
            'last_update': self.progress_data.get('last_update'),
            'end_time': self.progress_data.get('end_time')
        }
        
        return info
    
    def reset_progress(self):
        """重置进度（谨慎使用）"""
        logger.warning("重置进度文件")
        
        if self.progress_file.exists():
            self.progress_file.unlink()
        
        self.progress_data = self._load_progress()
    
    def __del__(self):
        """析构函数，确保进度被保存"""
        if self.progress_data.get('status') == 'running':
            self._save_progress()


if __name__ == '__main__':
    """进度管理器测试"""
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("="*80)
    print("进度管理器测试")
    print("="*80)
    
    # 创建测试用的进度管理器
    test_progress_file = 'cache/test_progress.pkl'
    pm = ProgressManager(progress_file=test_progress_file)
    
    # 生成测试配对
    print("\n生成测试配对...")
    test_pairs = [(f'stock_{i}', f'stock_{j}') 
                  for i in range(20) 
                  for j in range(i+1, 20)]
    
    print(f"生成了 {len(test_pairs)} 个配对")
    
    # 测试1: 初始化任务
    print("\n测试1: 初始化任务")
    pm.initialize_task(test_pairs)
    info = pm.get_progress_info()
    print(f"总配对数: {info['total_pairs']}")
    print(f"总批次数: {info['total_batches']}")
    print(f"状态: {info['status']}")
    
    # 测试2: 创建批次
    print("\n测试2: 创建批次")
    batches = pm.create_batches(test_pairs)
    print(f"创建了 {len(batches)} 个批次")
    for i, batch in enumerate(batches):
        print(f"  批次 {i}: {len(batch)} 个配对")
    
    # 测试3: 模拟处理几个批次
    print("\n测试3: 模拟处理批次")
    for i, batch in enumerate(batches[:3]):  # 只处理前3个批次
        # 模拟处理结果
        results = [{'pair': pair, 'score': i * 10} for pair in batch]
        
        pm.mark_batch_completed(batch, results, i)
        print(f"批次 {i} 已完成")
        
        # 显示进度
        info = pm.get_progress_info()
        print(f"  进度: {info['completed_pairs']}/{info['total_pairs']} ({info['progress_percentage']:.1f}%)")
    
    # 测试4: 获取剩余配对
    print("\n测试4: 获取剩余配对")
    remaining = pm.get_remaining_pairs(test_pairs)
    print(f"剩余 {len(remaining)} 个配对待处理")
    
    # 测试5: 获取所有结果
    print("\n测试5: 获取所有结果")
    all_results = pm.get_all_results()
    print(f"已获取 {len(all_results)} 个配对结果")
    
    # 测试6: 进度信息
    print("\n测试6: 进度信息")
    info = pm.get_progress_info()
    print(f"状态: {info['status']}")
    print(f"总配对: {info['total_pairs']}")
    print(f"已完成: {info['completed_pairs']}")
    print(f"剩余: {info['remaining_pairs']}")
    print(f"进度: {info['progress_percentage']:.1f}%")
    print(f"批次进度: {info['current_batch']}/{info['total_batches']} ({info['batch_percentage']:.1f}%)")
    
    # 清理测试文件
    print("\n清理测试文件...")
    if Path(test_progress_file).exists():
        Path(test_progress_file).unlink()
    
    print("\n" + "="*80)

