#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC均线信号监控脚本 - GitHub Actions版本
适用于GitHub Actions自动化执行，无需while循环
"""

import requests
import json
import os
import pandas as pd
import numpy as np
from datetime import datetime

class BTCSignalMonitor:
    def __init__(self, bark_key):
        self.bark_key = bark_key
        self.bark_url = f"https://api.day.app/{bark_key}"
        
    def get_btc_price_okx(self):
        """从OKX获取BTC价格数据"""
        try:
            url = "https://www.okx.com/api/v5/market/candles"
            params = {
                'instId': 'BTC-USDT',
                'bar': '1H',
                'limit': '100'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['code'] == '0':
                prices = []
                for item in data['data']:
                    prices.append({
                        'timestamp': int(item[0]),
                        'close': float(item[4])
                    })
                return sorted(prices, key=lambda x: x['timestamp'])
            return None
                
        except Exception as e:
            print(f"获取OKX数据失败: {e}")
            return None
    
    def get_btc_price_binance(self):
        """从Binance获取BTC价格数据"""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': '1h',
                'limit': 100
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            prices = []
            for item in data:
                prices.append({
                    'timestamp': int(item[0]),
                    'close': float(item[4])
                })
            return prices
            
        except Exception as e:
            print(f"获取Binance数据失败: {e}")
            return None
    
    def calculate_moving_averages(self, prices):
        """计算移动平均线"""
        if len(prices) < 50:
            return None
            
        closes = [p['close'] for p in prices]
        
        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:])
        ma20 = np.mean(closes[-20:])
        ma50 = np.mean(closes[-50:])
        
        current_price = closes[-1]
        
        return {
            'current_price': current_price,
            'ma5': ma5,
            'ma10': ma10,
            'ma20': ma20,
            'ma50': ma50,
            'timestamp': prices[-1]['timestamp']
        }
    
    def analyze_signal(self, ma_data):
        """分析均线信号"""
        if not ma_data:
            return None
            
        current_price = ma_data['current_price']
        ma5 = ma_data['ma5']
        ma10 = ma_data['ma10']
        ma20 = ma_data['ma20']
        ma50 = ma_data['ma50']
        
        signals = []
        
        # 均线排列分析
        if ma5 > ma10 > ma20:
            signals.append("短期看涨趋势")
        elif ma5 < ma10 < ma20:
            signals.append("短期看跌趋势")
            
        # 价格与关键均线关系
        if current_price > ma20:
            signals.append("价格站上MA20")
        else:
            signals.append("价格跌破MA20")
        
        # 趋势判断
        trend = self.determine_trend(ma5, ma10, ma20, ma50)
        
        # 计算偏离度
        ma20_deviation = ((current_price - ma20) / ma20) * 100
        
        return {
            'signals': signals,
            'ma20_deviation': ma20_deviation,
            'trend': trend
        }
    
    def determine_trend(self, ma5, ma10, ma20, ma50):
        """判断趋势"""
        if ma5 > ma10 > ma20 > ma50:
            return "强势上涨"
        elif ma5 > ma10 > ma20:
            return "上涨"
        elif ma5 < ma10 < ma20 < ma50:
            return "强势下跌"
        elif ma5 < ma10 < ma20:
            return "下跌"
        else:
            return "震荡"
    
    def send_bark_notification(self, title, content, level="active"):
        """发送Bark推送通知"""
        try:
            # 限制content长度，避免URL过长
            if len(content) > 500:
                content = content[:500] + "..."
            
            url = f"{self.bark_url}/{title}"
            data = {
                'body': content,
                'level': level,
                'sound': 'birdsong',
                'icon': 'https://cryptologos.cc/logos/bitcoin-btc-logo.png'
            }
            
            # 使用POST请求发送长内容
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 200:
                print(f"✅ 推送成功: {title}")
                return True
            else:
                print(f"❌ 推送失败: {result}")
                return False
                
        except Exception as e:
            print(f"❌ 发送Bark通知失败: {e}")
            return False
    
    def run_check(self):
        """执行一次检查"""
        print(f"🔍 开始检查BTC均线信号... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 获取价格数据
        prices = self.get_btc_price_okx()
        data_source = "OKX"
        
        if not prices:
            print("⚠️ OKX数据获取失败，尝试Binance...")
            prices = self.get_btc_price_binance()
            data_source = "Binance"
        
        if not prices:
            error_msg = "❌ 无法获取价格数据"
            print(error_msg)
            self.send_bark_notification("BTC监控错误", error_msg, "timeSensitive")
            return
        
        # 计算均线
        ma_data = self.calculate_moving_averages(prices)
        if not ma_data:
            print("❌ 数据不足，无法计算均线")
            return
        
        # 分析信号
        signal_data = self.analyze_signal(ma_data)
        if not signal_data:
            print("❌ 信号分析失败")
            return
        
        # 格式化消息
        timestamp = datetime.fromtimestamp(ma_data['timestamp'] / 1000)
        title = f"BTC均线信号 {timestamp.strftime('%m-%d %H:%M')}"
        
        content = f"""💰 ${ma_data['current_price']:,.0f}
📊 MA5: ${ma_data['ma5']:,.0f}
📊 MA20: ${ma_data['ma20']:,.0f}
📊 MA50: ${ma_data['ma50']:,.0f}
📈 {signal_data['trend']}
📍 MA20偏离: {signal_data['ma20_deviation']:+.1f}%

🔔 {' | '.join(signal_data['signals'][:2])}
📡 {data_source}"""
        
        print(f"📊 {title}")
        print(f"📝 {content}")
        
        # 发送通知
        self.send_bark_notification(title, content, "timeSensitive")

def main():
    """主函数 - GitHub Actions版本"""
    # 从环境变量获取Bark key
    bark_key = os.environ.get('BARK_KEY')
    
    if not bark_key:
        print("❌ 未设置BARK_KEY环境变量!")
        print("请在GitHub仓库的Settings -> Secrets中添加BARK_KEY")
        return
    
    # 创建监控器并执行检查
    monitor = BTCSignalMonitor(bark_key)
    monitor.run_check()

if __name__ == "__main__":
    main()
