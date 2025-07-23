#!/usr/bin/env python3
"""
清理预设模型脚本
用于删除不需要的Emohaa预设模型
"""

import sys
import os

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from open_webui.models.models import Models

def cleanup_preset_models():
    """删除预设的Emohaa模型"""
    models_to_remove = [
        "emohaa-chat-v1",
        "emohaa-analysis-v1", 
        "emohaa-counselor-v1"
    ]
    
    print("🧹 开始清理预设模型...")
    
    for model_id in models_to_remove:
        try:
            existing_model = Models.get_model_by_id(model_id)
            if existing_model:
                success = Models.delete_model_by_id(model_id)
                if success:
                    print(f"✅ 已删除模型: {model_id}")
                else:
                    print(f"❌ 删除失败: {model_id}")
            else:
                print(f"⚠️  模型不存在: {model_id}")
        except Exception as e:
            print(f"❌ 删除模型 {model_id} 时出错: {e}")
    
    print("🎉 清理完成！")

if __name__ == "__main__":
    cleanup_preset_models() 