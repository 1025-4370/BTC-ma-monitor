#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC 5分钟均线金叉死叉监控脚本 - GitHub Actions版本
只在MA20与MA60穿越时推送通知，避免重复推送
"""

import requests
import os
import numpy as np
from datetime import datetime

class BTCSignalMonitor:
    def __init__(self, bark_key):
        self.bark_key = bark_key
        self.bark_url = f"https://api.day.app/{bark_key}"
        self.last_signal = None  # 记录上次推送信号，防止重复
    
    def get_btc_price_okx(self):
        try:
            url = "https://www.okx.com/api/v5/market/candles"
            params = {
                'instId': 'BTC-USDT',
                'bar': '5m',
                'limit': '70'  # 至少要70根5分钟K线才能计算MA60
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
            else:
                print(f"OKX接口异常: {data}")
                return None
        except Exception as e:
            print(f"获取OKX数据失败: {e}")
            return None
    
    def get_btc_price_binance(self):
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': '5m',
                'limit': 70
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
        if len(prices) < 60:
            return None
        closes = [p['close'] for p in prices]
        
        # 计算MA20列表和MA60列表
        ma20_list = [np.mean(closes[i-20:i]) for i in range(20, len(closes)+1)]
        ma60_list = [np.mean(closes[i-60:i]) for i in range(60, len(closes)+1)]
        
        # 当前和上一根的MA值
        ma20_current = ma20_list[-1]
        ma20_prev = ma20_list[-2]
        ma60_current = ma60_list[-1]
        ma60_prev = ma60_list[-2]
        
        current_price = closes[-1]
        
        return {
            'current_price': current_price,
            'ma20_current': ma20_current,
            'ma20_prev': ma20_prev,
            'ma60_current': ma60_current,
            'ma60_prev': ma60_prev,
            'timestamp': prices[-1]['timestamp']
        }
    
    def analyze_signal(self, ma_data):
        if not ma_data:
            return None
        
        ma20_current = ma_data['ma20_current']
        ma20_prev = ma_data['ma20_prev']
        ma60_current = ma_data['ma60_current']
        ma60_prev = ma_data['ma60_prev']
        
        signal = None
        
        # 判断金叉（短期均线向上穿过长期均线）
        if ma20_prev <= ma60_prev and ma20_current > ma60_current:
            signal = "MA20金叉MA60，买入信号"
        # 判断死叉（短期均线向下穿过长期均线）
        elif ma20_prev >= ma60_prev and ma20_current < ma60_current:
            signal = "MA20死叉MA60，卖出信号"
        
        return signal
    
    def send_bark_notification(self, title, content, level="active"):
        try:
            if len(content) > 500:
                content = content[:500] + "..."
            url = f"{self.bark_url}/{title}"
            data = {
                'body': content,
                'level': level,
                'sound': 'birdsong',
                'icon': 'https://cryptologos.cc/logos/bitcoin-btc-logo.png'
            }
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
        print(f"🔍 开始检查BTC均线穿越信号... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
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
        
        ma_data = self.calculate_moving_averages(prices)
        if not ma_data:
            print("❌ 数据不足，无法计算均线")
            return
        
        signal = self.analyze_signal(ma_data)
        if not signal:
            print("ℹ️ 无穿越信号，跳过推送")
            return
        
        # 防止重复推送同一信号
        if signal == self.last_signal:
            print("ℹ️ 信号未变化，跳过推送")
            return
        self.last_signal = signal
        
        timestamp = datetime.fromtimestamp(ma_data['timestamp'] / 1000)
        title = f"BTC 5分钟均线信号 {timestamp.strftime('%m-%d %H:%M')}"
        content = f"{signal}\n当前价格: ${ma_data['current_price']:.2f}\n数据来源: {data_source}"
        
        print(title)
        print(content)
        self.send_bark_notification(title, content)

def main():
    bark_key = os.environ.get('BARK_KEY')
    if not bark_key:
        print("❌ 未设置BARK_KEY环境变量!")
        print("请在GitHub仓库的Settings -> Secrets中添加BARK_KEY")
        return
    
    monitor = BTCSignalMonitor(bark_key)
    monitor.run_check()

if __name__ == "__main__":
    main()
