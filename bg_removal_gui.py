#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量删除图片黑色背景 - 图形界面版本
提供简单易用的GUI界面进行批量背景删除
"""

import os
import sys
import threading
from pathlib import Path
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QThread, pyqtSignal
from batch_bg_removal import BackgroundRemover


class ProcessingThread(QThread):
    """处理线程类"""
    progress_updated = pyqtSignal(int, int)  # 当前进度, 总数
    status_updated = pyqtSignal(str)  # 状态信息
    finished = pyqtSignal(dict)  # 完成信号，传递统计信息
    
    def __init__(self, input_dir, output_dir, threshold, quality, recursive, extensions):
        super().__init__()
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.threshold = threshold
        self.quality = quality
        self.recursive = recursive
        self.extensions = extensions
        self.remover = BackgroundRemover(threshold=threshold)
    
    def run(self):
        """运行处理线程"""
        try:
            self.status_updated.emit("开始处理图片...")
            
            # 获取所有图片文件
            input_path = Path(self.input_dir)
            if self.recursive:
                image_files = []
                for ext in self.extensions:
                    image_files.extend(input_path.rglob(f'*{ext}'))
                    image_files.extend(input_path.rglob(f'*{ext.upper()}'))
            else:
                image_files = []
                for ext in self.extensions:
                    image_files.extend(input_path.glob(f'*{ext}'))
                    image_files.extend(input_path.glob(f'*{ext.upper()}'))
            
            if not image_files:
                self.status_updated.emit("未找到符合条件的图片文件")
                self.finished.emit({'total': 0, 'success': 0, 'failed': 0})
                return
            
            self.status_updated.emit(f"找到 {len(image_files)} 个图片文件")
            
            # 确定输出目录
            if self.output_dir is None:
                output_path = input_path / 'processed'
            else:
                output_path = Path(self.output_dir)
            
            # 创建输出目录
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 处理统计
            stats = {'total': len(image_files), 'success': 0, 'failed': 0}
            
            # 批量处理
            for i, image_file in enumerate(image_files):
                try:
                    # 更新进度
                    self.progress_updated.emit(i + 1, len(image_files))
                    self.status_updated.emit(f"正在处理: {image_file.name}")
                    
                    # 计算相对路径以保持目录结构
                    relative_path = image_file.relative_to(input_path)
                    output_file = output_path / relative_path
                    
                    # 确保输出目录存在
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 处理图片
                    if self.remover.remove_black_background(str(image_file), str(output_file), self.quality):
                        stats['success'] += 1
                    else:
                        stats['failed'] += 1
                        
                except Exception as e:
                    self.status_updated.emit(f"处理文件 {image_file.name} 时出错: {str(e)}")
                    stats['failed'] += 1
            
            self.status_updated.emit("处理完成！")
            self.finished.emit(stats)
            
        except Exception as e:
            self.status_updated.emit(f"处理过程中出现错误: {str(e)}")
            self.finished.emit({'total': 0, 'success': 0, 'failed': 0})


class BackgroundRemovalGUI(QtWidgets.QMainWindow):
    """背景删除GUI主窗口"""
    
    def __init__(self):
        super().__init__()
        self.processing_thread = None
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle('批量删除图片黑色背景')
        self.setGeometry(100, 100, 600, 500)
        
        # 创建中央部件
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        
        # 输入目录选择
        input_group = QtWidgets.QGroupBox("输入设置")
        input_layout = QtWidgets.QHBoxLayout(input_group)
        
        self.input_dir_edit = QtWidgets.QLineEdit()
        self.input_dir_edit.setPlaceholderText("选择包含图片的目录...")
        input_layout.addWidget(self.input_dir_edit)
        
        self.input_dir_btn = QtWidgets.QPushButton("浏览...")
        self.input_dir_btn.clicked.connect(self.select_input_dir)
        input_layout.addWidget(self.input_dir_btn)
        
        main_layout.addWidget(input_group)
        
        # 输出目录选择
        output_group = QtWidgets.QGroupBox("输出设置")
        output_layout = QtWidgets.QHBoxLayout(output_group)
        
        self.output_dir_edit = QtWidgets.QLineEdit()
        self.output_dir_edit.setPlaceholderText("选择输出目录（留空则在输入目录下创建processed文件夹）...")
        output_layout.addWidget(self.output_dir_edit)
        
        self.output_dir_btn = QtWidgets.QPushButton("浏览...")
        self.output_dir_btn.clicked.connect(self.select_output_dir)
        output_layout.addWidget(self.output_dir_btn)
        
        main_layout.addWidget(output_group)
        
        # 处理参数设置
        params_group = QtWidgets.QGroupBox("处理参数")
        params_layout = QtWidgets.QGridLayout(params_group)
        
        # 黑色阈值
        params_layout.addWidget(QtWidgets.QLabel("黑色阈值:"), 0, 0)
        self.threshold_spin = QtWidgets.QSpinBox()
        self.threshold_spin.setRange(1, 255)
        self.threshold_spin.setValue(30)
        self.threshold_spin.setToolTip("低于此值的像素被认为是黑色背景")
        params_layout.addWidget(self.threshold_spin, 0, 1)
        
        # 图片质量
        params_layout.addWidget(QtWidgets.QLabel("图片质量:"), 1, 0)
        self.quality_spin = QtWidgets.QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(95)
        self.quality_spin.setToolTip("输出图片质量 (1-100)")
        params_layout.addWidget(self.quality_spin, 1, 1)
        
        # 递归处理
        self.recursive_check = QtWidgets.QCheckBox("递归处理子目录")
        self.recursive_check.setChecked(True)
        params_layout.addWidget(self.recursive_check, 2, 0, 1, 2)
        
        # 文件扩展名
        params_layout.addWidget(QtWidgets.QLabel("文件扩展名:"), 3, 0)
        self.extensions_edit = QtWidgets.QLineEdit(".jpg, .jpeg")
        self.extensions_edit.setToolTip("用逗号分隔的文件扩展名")
        params_layout.addWidget(self.extensions_edit, 3, 1)
        
        main_layout.addWidget(params_group)
        
        # 进度显示
        progress_group = QtWidgets.QGroupBox("处理进度")
        progress_layout = QtWidgets.QVBoxLayout(progress_group)
        
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QtWidgets.QLabel("准备就绪")
        progress_layout.addWidget(self.status_label)
        
        main_layout.addWidget(progress_group)
        
        # 控制按钮
        button_layout = QtWidgets.QHBoxLayout()
        
        self.start_btn = QtWidgets.QPushButton("开始处理")
        self.start_btn.clicked.connect(self.start_processing)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QtWidgets.QPushButton("停止处理")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(button_layout)
        
        # 结果显示
        self.result_text = QtWidgets.QTextEdit()
        self.result_text.setMaximumHeight(100)
        self.result_text.setReadOnly(True)
        main_layout.addWidget(self.result_text)
    
    def select_input_dir(self):
        """选择输入目录"""
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择输入目录")
        if dir_path:
            self.input_dir_edit.setText(dir_path)
    
    def select_output_dir(self):
        """选择输出目录"""
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.output_dir_edit.setText(dir_path)
    
    def start_processing(self):
        """开始处理"""
        input_dir = self.input_dir_edit.text().strip()
        if not input_dir or not os.path.exists(input_dir):
            QtWidgets.QMessageBox.warning(self, "警告", "请选择有效的输入目录")
            return
        
        # 获取参数
        output_dir = self.output_dir_edit.text().strip() or None
        threshold = self.threshold_spin.value()
        quality = self.quality_spin.value()
        recursive = self.recursive_check.isChecked()
        
        # 解析文件扩展名
        extensions_text = self.extensions_edit.text().strip()
        if not extensions_text:
            extensions = ['.jpg', '.jpeg']
        else:
            extensions = [ext.strip() for ext in extensions_text.split(',') if ext.strip()]
            if not extensions:
                extensions = ['.jpg', '.jpeg']
        
        # 更新UI状态
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.result_text.clear()
        
        # 创建并启动处理线程
        self.processing_thread = ProcessingThread(
            input_dir, output_dir, threshold, quality, recursive, extensions
        )
        self.processing_thread.progress_updated.connect(self.update_progress)
        self.processing_thread.status_updated.connect(self.update_status)
        self.processing_thread.finished.connect(self.processing_finished)
        self.processing_thread.start()
    
    def stop_processing(self):
        """停止处理"""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.terminate()
            self.processing_thread.wait()
            self.update_status("处理已停止")
            self.processing_finished({'total': 0, 'success': 0, 'failed': 0})
    
    def update_progress(self, current, total):
        """更新进度条"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
    
    def update_status(self, status):
        """更新状态信息"""
        self.status_label.setText(status)
    
    def processing_finished(self, stats):
        """处理完成"""
        # 更新UI状态
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        # 显示结果
        if stats['total'] > 0:
            result_text = f"处理完成！\n"
            result_text += f"总计: {stats['total']} 张图片\n"
            result_text += f"成功: {stats['success']} 张\n"
            result_text += f"失败: {stats['failed']} 张\n"
            
            if stats['success'] > 0:
                output_dir = self.output_dir_edit.text().strip()
                if not output_dir:
                    output_dir = os.path.join(self.input_dir_edit.text(), 'processed')
                result_text += f"处理后的图片保存在: {output_dir}"
            
            self.result_text.setText(result_text)
            self.update_status("处理完成")
        else:
            self.update_status("未找到符合条件的图片文件")


def main():
    """主函数"""
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("批量删除图片黑色背景")
    
    # 设置应用图标（如果有的话）
    # app.setWindowIcon(QtGui.QIcon('icon.png'))
    
    window = BackgroundRemovalGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
