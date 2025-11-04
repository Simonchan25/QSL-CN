#!/usr/bin/env python3
"""
更新股票映射表 - 从Tushare获取最新的所有A股数据
"""
import json
import os
from pathlib import Path
from core.tushare_client import stock_basic

def update_symbol_map():
    """更新symbol_map.json,包含所有上市A股"""
    print("正在从Tushare获取最新股票列表...")

    # 获取所有上市股票(包括上交所和深交所)
    df = stock_basic(list_status='L', force=True)

    if df is None or df.empty:
        print("❌ 获取股票列表失败!")
        return False

    print(f"✅ 获取到 {len(df)} 只股票")

    # 转换为映射格式
    stock_list = []
    for _, row in df.iterrows():
        stock_info = {
            'ts_code': row['ts_code'],
            'name': row['name'],
            'industry': row.get('industry', ''),
            'area': row.get('area', ''),
            'aliases': []  # 初始为空,后续可手动添加别名
        }

        # 自动添加一些常见别名
        name = row['name']
        code = row['ts_code'].split('.')[0]
        aliases = []

        # 添加不带后缀的代码
        aliases.append(code)

        # 添加常见简称变体
        if 'A' in name and name.endswith('A'):
            aliases.append(name[:-1])  # 去掉末尾的A

        # 特殊处理:ST股票
        if name.startswith('ST'):
            aliases.append(name[2:])  # 去掉ST前缀
        if name.startswith('*ST'):
            aliases.append(name[3:])  # 去掉*ST前缀

        stock_info['aliases'] = list(set(aliases))  # 去重
        stock_list.append(stock_info)

    # 按代码排序
    stock_list.sort(key=lambda x: x['ts_code'])

    # 保存到文件
    output_path = Path(__file__).parent / 'core' / 'symbol_map.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(stock_list, f, ensure_ascii=False, indent=2)

    print(f"✅ 股票映射表已更新: {output_path}")
    print(f"   共 {len(stock_list)} 只股票")

    # 显示一些统计信息
    industries = {}
    for stock in stock_list:
        industry = stock.get('industry', '未知')
        industries[industry] = industries.get(industry, 0) + 1

    print(f"\n📊 行业分布 (前10):")
    for industry, count in sorted(industries.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"   {industry}: {count}只")

    return True

if __name__ == '__main__':
    success = update_symbol_map()
    exit(0 if success else 1)
