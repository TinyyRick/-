#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量删除图片黑色背景脚本
支持批量处理JPG格式图片，将纯黑背景转换为透明背景，保持图片清晰度
"""

import os
import sys
import argparse
from pathlib import Path
from PIL import Image, ImageOps
import numpy as np
from tqdm import tqdm


class BackgroundRemover:
    """背景删除器类"""
    
    def __init__(self, threshold=30, tolerance=10):
        """
        初始化背景删除器
        
        Args:
            threshold (int): 黑色阈值，低于此值的像素被认为是黑色背景
            tolerance (int): 容差值，用于处理接近黑色的像素
        """
        self.threshold = threshold
        self.tolerance = tolerance
    
    def is_black_background(self, pixel):
        """
        判断像素是否为黑色背景
        
        Args:
            pixel: RGB像素值 (r, g, b) 或 (r, g, b, a)
            
        Returns:
            bool: 是否为黑色背景
        """
        if len(pixel) == 4:  # RGBA
            r, g, b, a = pixel
            if a == 0:  # 已经是透明的
                return True
        else:  # RGB
            r, g, b = pixel
        
        # 检查是否为黑色或接近黑色
        return r <= self.threshold and g <= self.threshold and b <= self.threshold
    
    def remove_black_background(self, image_path, output_path=None, quality=95):
        """
        删除图片的黑色背景
        
        Args:
            image_path (str): 输入图片路径
            output_path (str): 输出图片路径，如果为None则覆盖原文件
            quality (int): 输出图片质量 (1-100)
            
        Returns:
            bool: 处理是否成功
        """
        try:
            # 打开图片
            with Image.open(image_path) as img:
                # 转换为RGBA模式以支持透明度
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # 获取图片数据
                data = np.array(img)
                
                # 创建透明度掩码
                alpha_channel = data[:, :, 3].copy()
                
                # 遍历每个像素
                for y in range(data.shape[0]):
                    for x in range(data.shape[1]):
                        pixel = data[y, x]
                        if self.is_black_background(pixel):
                            # 将黑色背景像素设为透明
                            alpha_channel[y, x] = 0
                
                # 更新alpha通道
                data[:, :, 3] = alpha_channel
                
                # 创建新图片
                result_img = Image.fromarray(data, 'RGBA')
                
                # 确定输出路径
                if output_path is None:
                    output_path = image_path
                
                # 保存图片
                if output_path.lower().endswith('.jpg') or output_path.lower().endswith('.jpeg'):
                    # JPG不支持透明度，转换为PNG
                    output_path = output_path.rsplit('.', 1)[0] + '.png'
                    result_img.save(output_path, 'PNG', optimize=True)
                else:
                    result_img.save(output_path, 'PNG', optimize=True)
                
                return True
                
        except Exception as e:
            print(f"处理图片 {image_path} 时出错: {str(e)}")
            return False
    
    def batch_remove_background(self, input_dir, output_dir=None, recursive=True, 
                               file_extensions=('.jpg', '.jpeg'), quality=95):
        """
        批量删除图片背景
        
        Args:
            input_dir (str): 输入目录
            output_dir (str): 输出目录，如果为None则在原目录创建processed子目录
            recursive (bool): 是否递归处理子目录
            file_extensions (tuple): 要处理的文件扩展名
            quality (int): 输出图片质量
            
        Returns:
            dict: 处理结果统计
        """
        input_path = Path(input_dir)
        if not input_path.exists():
            raise ValueError(f"输入目录不存在: {input_dir}")
        
        # 确定输出目录
        if output_dir is None:
            output_path = input_path / 'processed'
        else:
            output_path = Path(output_dir)
        
        # 创建输出目录
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 获取所有图片文件
        if recursive:
            image_files = []
            for ext in file_extensions:
                image_files.extend(input_path.rglob(f'*{ext}'))
                image_files.extend(input_path.rglob(f'*{ext.upper()}'))
        else:
            image_files = []
            for ext in file_extensions:
                image_files.extend(input_path.glob(f'*{ext}'))
                image_files.extend(input_path.glob(f'*{ext.upper()}'))
        
        if not image_files:
            print(f"在目录 {input_dir} 中未找到 {file_extensions} 格式的图片文件")
            return {'total': 0, 'success': 0, 'failed': 0}
        
        print(f"找到 {len(image_files)} 个图片文件，开始处理...")
        
        # 处理统计
        stats = {'total': len(image_files), 'success': 0, 'failed': 0}
        
        # 批量处理
        for image_file in tqdm(image_files, desc="处理图片", unit="张"):
            try:
                # 计算相对路径以保持目录结构
                relative_path = image_file.relative_to(input_path)
                output_file = output_path / relative_path
                
                # 确保输出目录存在
                output_file.parent.mkdir(parents=True, exist_ok=True)
                
                # 处理图片
                if self.remove_black_background(str(image_file), str(output_file), quality):
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
                    
            except Exception as e:
                print(f"处理文件 {image_file} 时出错: {str(e)}")
                stats['failed'] += 1
        
        return stats


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='批量删除图片黑色背景')
    parser.add_argument('input_dir', help='输入目录路径')
    parser.add_argument('-o', '--output', help='输出目录路径（默认为输入目录下的processed文件夹）')
    parser.add_argument('-t', '--threshold', type=int, default=30, 
                       help='黑色阈值，低于此值的像素被认为是黑色背景（默认30）')
    parser.add_argument('-q', '--quality', type=int, default=95, 
                       help='输出图片质量1-100（默认95）')
    parser.add_argument('--no-recursive', action='store_true', 
                       help='不递归处理子目录')
    parser.add_argument('--extensions', nargs='+', default=['.jpg', '.jpeg'], 
                       help='要处理的文件扩展名（默认.jpg .jpeg）')
    
    args = parser.parse_args()
    
    # 创建背景删除器
    remover = BackgroundRemover(threshold=args.threshold)
    
    try:
        # 批量处理
        stats = remover.batch_remove_background(
            input_dir=args.input_dir,
            output_dir=args.output,
            recursive=not args.no_recursive,
            file_extensions=tuple(args.extensions),
            quality=args.quality
        )
        
        # 输出结果
        print(f"\n处理完成！")
        print(f"总计: {stats['total']} 张图片")
        print(f"成功: {stats['success']} 张")
        print(f"失败: {stats['failed']} 张")
        
        if stats['success'] > 0:
            output_dir = args.output or os.path.join(args.input_dir, 'processed')
            print(f"处理后的图片保存在: {output_dir}")
        
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
