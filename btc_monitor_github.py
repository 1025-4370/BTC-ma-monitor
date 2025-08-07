#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC 5分钟K线 MA20/MA60 交叉信号监控
专门监控MA20与MA60的金叉/死叉信号
"""

import requests
import json
import os
import time
import numpy as np
from datetime import datetime, timedelta

class MACrossoverMonitor:
    def __init__(self, bark_key):
        self.bark_key = bark_key
        self.bark_url = f"https://api.day.app/{bark_key}"
        
        # 存储历史状态，用于检测交叉
        self.last_ma20 = None
        self.last_ma60 = None
        self.last_crossover_state = None  # 'golden' or 'death' or None
        self.last_signal_time = None
        
        # 交叉确认参数
        self.confirmation_periods = 2  # 需要连续2个周期确认交叉
        self.crossover_history = []  # 存储最近的交叉状态
        
    def get_btc_5min_klines(self, limit=100):
        """获取BTC 5分钟K线数据"""
        # 优先尝试OKX
        data = self.get_okx_5min_data(limit)
        if data:
            return data
        
        # 备用Binance
        data = self.get_binance_5min_data(limit)
        if data:
            return data
            
        return None
    
    def get_okx_5min_data(self, limit):
        """从OKX获取5分钟K线数据"""
        try:
            url = "https://www.okx.com/api/v5/market/candles"
            params = {
                'instId': 'BTC-USDT',
                'bar': '5m',  # 5分钟K线
                'limit': str(limit)
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['code'] == '0':
                klines = []
                for item in data['data']:
                    klines.append({
                        'timestamp': int(item[0]),
                        'open': float(item[1]),
                        'high': float(item[2]),
                        'low': float(item[3]),
                        'close': float(item[4]),
                        'volume': float(item[5]),
                        'time_str': datetime.fromtimestamp(int(item[0])/1000).strftime('%m-%d %H:%M')
                    })
                
                # 按时间升序排列
                klines.sort(key=lambda x: x['timestamp'])
                return {'data': klines, 'source': 'OKX'}
            
            return None
            
        except Exception as e:
            print(f"OKX 5分钟数据获取失败: {e}")
            return None
    
    def get_binance_5min_data(self, limit):
        """从Binance获取5分钟K线数据"""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': '5m',  # 5分钟K线
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            klines = []
            for item in data:
                klines.append({
                    'timestamp': int(item[0]),
                    'open': float(item[1]),
                    'high': float(item[2]),
                    'low': float(item[3]),
                    'close': float(item[4]),
                    'volume': float(item[5]),
                    'time_str': datetime.fromtimestamp(int(item[0])/1000).strftime('%m-%d %H:%M')
                })
            
            return {'data': klines, 'source': 'Binance'}
            
        except Exception as e:
            print(f"Binance 5分钟数据获取失败: {e}")
            return None
    
    def calculate_moving_averages(self, klines):
        """计算MA20和MA60"""
        if len(klines) < 60:
            print(f"❌ K线数据不足: {len(klines)}/60")
            return None
        
        # 提取收盘价
        closes = [k['close'] for k in klines]
        
        # 计算移动平均线
        ma20_values = []
        ma60_values = []
        
        # 从第60根K线开始计算（确保MA60有效）
        for i in range(59, len(closes)):
            ma20 = np.mean(closes[i-19:i+1])  # MA20
            ma60 = np.mean(closes[i-59:i+1])  # MA60
            
            ma20_values.append(ma20)
            ma60_values.append(ma60)
        
        # 返回最新的均线数据和历史数据
        return {
            'current_ma20': ma20_values[-1],
            'current_ma60': ma60_values[-1],
            'previous_ma20': ma20_values[-2] if len(ma20_values) > 1 else ma20_values[-1],
            'previous_ma60': ma60_values[-2] if len(ma60_values) > 1 else ma60_values[-1],
            'ma20_history': ma20_values[-10:],  # 最近10个MA20值
            'ma60_history': ma60_values[-10:],  # 最近10个MA60值
            'current_price': closes[-1],
            'current_time': klines[-1]['time_str']
        }
    
    def detect_crossover(self, ma_data):
        """检测MA20与MA60的交叉信号"""
        current_ma20 = ma_data['current_ma20']
        current_ma60 = ma_data['current_ma60']
        previous_ma20 = ma_data['previous_ma20']
        previous_ma60 = ma_data['previous_ma60']
        
        crossover_info = {
            'signal_type': None,
            'signal_strength': 'weak',
            'crossover_confirmed': False,
            'price_position': None
        }
        
        # 检测交叉
        # 金叉：MA20从下方穿越MA60上方
        if previous_ma20 <= previous_ma60 and current_ma20 > current_ma60:
            crossover_info['signal_type'] = 'golden_cross'
            crossover_info['signal_strength'] = self.calculate_signal_strength(ma_data, 'golden')
            
        # 死叉：MA20从上方穿越MA60下方  
        elif previous_ma20 >= previous_ma60 and current_ma20 < current_ma60:
            crossover_info['signal_type'] = 'death_cross'
            crossover_info['signal_strength'] = self.calculate_signal_strength(ma_data, 'death')
        
        # 判断价格相对均线的位置
        current_price = ma_data['current_price']
        if current_price > max(current_ma20, current_ma60):
            crossover_info['price_position'] = 'above_both'
        elif current_price < min(current_ma20, current_ma60):
            crossover_info['price_position'] = 'below_both'
        else:
            crossover_info['price_position'] = 'between_mas'
        
        # 交叉确认逻辑
        if crossover_info['signal_type']:
            # 检查是否与上次信号相同（避免重复）
            if self.last_crossover_state != crossover_info['signal_type']:
                crossover_info['crossover_confirmed'] = True
                self.last_crossover_state = crossover_info['signal_type']
            else:
                crossover_info['crossover_confirmed'] = False
        
        return crossover_info
    
    def calculate_signal_strength(self, ma_data, signal_type):
        """计算信号强度"""
        ma20_history = ma_data['ma20_history']
        ma60_history = ma_data['ma60_history']
        current_price = ma_data['current_price']
        current_ma20 = ma_data['current_ma20']
        current_ma60 = ma_data['current_ma60']
        
        strength_score = 0
        
        # 1. 均线斜率（趋势强度）
        if len(ma20_history) >= 5:
            ma20_slope = (ma20_history[-1] - ma20_history[-5]) / ma20_history[-5]
            ma60_slope = (ma60_history[-1] - ma60_history[-5]) / ma60_history[-5]
            
            if signal_type == 'golden':
                if ma20_slope > 0 and ma60_slope > 0:  # 双均线上升
                    strength_score += 2
                elif ma20_slope > 0:  # MA20上升
                    strength_score += 1
            else:  # death cross
                if ma20_slope < 0 and ma60_slope < 0:  # 双均线下降
                    strength_score += 2
                elif ma20_slope < 0:  # MA20下降
                    strength_score += 1
        
        # 2. 价格与均线的关系
        if signal_type == 'golden':
            if current_price > current_ma20 > current_ma60:
                strength_score += 2
            elif current_price > current_ma20:
                strength_score += 1
        else:  # death cross
            if current_price < current_ma20 < current_ma60:
                strength_score += 2
            elif current_price < current_ma20:
                strength_score += 1
        
        # 3. 均线间的距离（分离度）
        ma_distance = abs(current_ma20 - current_ma60) / current_ma60
        if ma_distance > 0.001:  # 0.1%以上分离
            strength_score += 1
        
        # 评级
        if strength_score >= 4:
            return 'strong'
        elif strength_score >= 2:
            return 'medium'
        else:
            return 'weak'
    
    def format_crossover_message(self, ma_data, crossover_info, source):
        """格式化交叉信号消息"""
        signal_type = crossover_info['signal_type']
        signal_strength = crossover_info['signal_strength']
        price_position = crossover_info['price_position']
        
        # 信号标题
        if signal_type == 'golden_cross':
            title = "🚀 BTC金叉信号"
            signal_emoji = "📈"
            signal_name = "金叉(MA20↗MA60)"
        else:
            title = "📉 BTC死叉信号"  
            signal_emoji = "📉"
            signal_name = "死叉(MA20↘MA60)"
        
        # 强度标识
        strength_emoji = {
            'strong': '🔥',
            'medium': '⚡', 
            'weak': '💫'
        }
        
        # 价格位置描述
        position_desc = {
            'above_both': '价格在双均线上方',
            'below_both': '价格在双均线下方', 
            'between_mas': '价格在均线之间'
        }
        
        current_time = ma_data['current_time']
        current_price = ma_data['current_price']
        current_ma20 = ma_data['current_ma20']
        current_ma60 = ma_data['current_ma60']
        
        # 计算均线偏离度
        ma20_deviation = ((current_price - current_ma20) / current_ma20) * 100
        ma60_deviation = ((current_price - current_ma60) / current_ma60) * 100
        
        title = f"{title} {current_time}"
        
        content = f"""{signal_emoji} {signal_name}
{strength_emoji[signal_strength]} 强度: {signal_strength.upper()}

💰 当前价格: ${current_price:,.2f}
📊 MA20: ${current_ma20:,.2f} ({ma20_deviation:+.2f}%)
📊 MA60: ${current_ma60:,.2f} ({ma60_deviation:+.2f}%)

📍 {position_desc[price_position]}
⏰ 5分钟K线交叉确认
📡 数据源: {source}"""
        
        return title, content
    
    def send_crossover_alert(self, title, content, signal_strength):
        """发送交叉信号推送"""
        try:
            # 根据信号强度确定推送级别
            alert_level = {
                'strong': 'timeSensitive',
                'medium': 'active', 
                'weak': 'passive'
            }
            
            sound_map = {
                'strong': 'alarm',
                'medium': 'bell',
                'weak': 'birdsong'
            }
            
            url = f"{self.bark_url}/{title}"
            data = {
                'body': content,
                'level': alert_level[signal_strength],
                'sound': sound_map[signal_strength],
                'icon': 'https://cryptologos.cc/logos/bitcoin-btc-logo.png'
            }
            
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('code') == 200:
                print(f"✅ 交叉信号推送成功: {signal_strength}")
                return True
            else:
                print(f"❌ 推送失败: {result}")
                return False
                
        except Exception as e:
            print(f"❌ 发送推送失败: {e}")
            return False
    
    def run_crossover_monitoring(self, duration_minutes=30):
        """运行交叉信号监控"""
        print("🎯 BTC MA20/MA60 交叉信号监控启动")
        print("📊 监控周期: 5分钟K线")
        print("🔍 监控信号: MA20与MA60金叉/死叉") 
        print(f"⏰ 监控时长: {duration_minutes}分钟")
        print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        check_count = 0
        
        while time.time() < end_time:
            check_count += 1
            current_time = datetime.now().strftime('%H:%M:%S')
            
            try:
                # 获取5分钟K线数据
                kline_data = self.get_btc_5min_klines(100)
                if not kline_data:
                    print(f"❌ [{current_time}] K线数据获取失败")
                    time.sleep(60)  # 等待1分钟后重试
                    continue
                
                # 计算均线
                ma_data = self.calculate_moving_averages(kline_data['data'])
                if not ma_data:
                    print(f"❌ [{current_time}] 均线计算失败")
                    time.sleep(60)
                    continue
                
                # 检测交叉信号
                crossover_info = self.detect_crossover(ma_data)
                
                # 显示当前状态
                ma20 = ma_data['current_ma20']
                ma60 = ma_data['current_ma60']
                price = ma_data['current_price']
                
                # 判断当前均线排列
                if ma20 > ma60:
                    ma_status = f"MA20>{ma60:.0f} (多头排列)"
                else:
                    ma_status = f"MA20<{ma60:.0f} (空头排列)"
                
                print(f"📊 [{current_time}] ${price:,.0f} | {ma_status} | {kline_data['source']}")
                
                # 发送交叉信号
                if crossover_info['signal_type'] and crossover_info['crossover_confirmed']:
                    title, content = self.format_crossover_message(
                        ma_data, crossover_info, kline_data['source']
                    )
                    
                    print(f"🚨 [{current_time}] 检测到{crossover_info['signal_type']} - 强度:{crossover_info['signal_strength']}")
                    
                    if self.send_crossover_alert(title, content, crossover_info['signal_strength']):
                        self.last_signal_time = time.time()
                        print(f"✅ [{current_time}] 交叉信号已推送")
                    else:
                        print(f"❌ [{current_time}] 推送失败")
                
                # 每15分钟发送状态更新（如果没有交叉信号）
                elif check_count % 15 == 0:
                    title = f"BTC均线监控 {current_time}"
                    content = f"""📊 MA20/MA60监控正常运行
💰 当前价格: ${price:,.0f}
📈 MA20: ${ma20:,.0f}
📈 MA60: ${ma60:,.0f}
📍 {ma_status}
⏰ 第{check_count}次检查
📡 数据源: {kline_data['source']}"""
                    
                    self.send_crossover_alert(title, content, 'weak')
                    print(f"📱 [{current_time}] 状态更新已推送")
                
                # 更新历史状态
                self.last_ma20 = ma20
                self.last_ma60 = ma60
                
            except Exception as e:
                print(f"❌ [{current_time}] 监控异常: {e}")
            
            # 等待1分钟后下次检查
            time.sleep(60)
        
        print(f"✅ 交叉信号监控结束，共检查{check_count}次")

def main():
    """主函数"""
    bark_key = os.environ.get('BARK_KEY')
    
    if not bark_key:
        print("❌ 未设置BARK_KEY环境变量!")
        print("请在GitHub仓库的Settings -> Secrets中添加BARK_KEY")
        return
    
    # 创建交叉信号监控器
    monitor = MACrossoverMonitor(bark_key)
    
    # 运行30分钟监控会话（每分钟检查一次）
    monitor.run_crossover_monitoring(duration_minutes=30)

if __name__ == "__main__":
    main()
