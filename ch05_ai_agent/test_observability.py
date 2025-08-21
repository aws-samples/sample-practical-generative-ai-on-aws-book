#!/usr/bin/env python3
"""
Observability 機能のテストスクリプト
エージェントの監視機能を包括的にテスト
"""

import subprocess
import json
import time
import sys
import argparse
from datetime import datetime

class ObservabilityTester:
    """Observability 機能のテストクラス"""
    
    def __init__(self, agent_name=None):
        self.agent_name = agent_name
        
    def test_basic_functionality(self):
        """基本的な機能テスト"""
        
        print("🧪 基本機能テスト開始...")
        print("=" * 50)
        
        test_cases = [
            {
                "name": "顧客識別テスト",
                "prompt": "差出人: me@example.net - こんにちは、サポートをお願いします。"
            },
            {
                "name": "注文履歴確認テスト", 
                "prompt": "差出人: me@example.net - 私の注文履歴を確認してください。"
            },
            {
                "name": "製品情報検索テスト",
                "prompt": "差出人: me@example.net - スマートフォンの充電器について教えてください。"
            },
            {
                "name": "計算機能テスト",
                "prompt": "差出人: me@example.net - 123 + 456 を計算してください。"
            },
            {
                "name": "エラーハンドリングテスト",
                "prompt": "差出人: unknown@test.com - 存在しない顧客のテスト"
            }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🔍 テスト {i}/{len(test_cases)}: {test_case['name']}")
            
            try:
                # エージェント呼び出し
                if self.agent_name:
                    # クラウドデプロイ版をテスト
                    cmd = [
                        'agentcore', 'invoke',
                        json.dumps({"prompt": test_case['prompt']})
                    ]
                else:
                    # ローカル版をテスト
                    cmd = [
                        'agentcore', 'invoke', '--local',
                        json.dumps({"prompt": test_case['prompt']})
                    ]
                
                start_time = time.time()
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                response_time = time.time() - start_time
                
                if result.returncode == 0:
                    response_data = json.loads(result.stdout)
                    
                    test_result = {
                        "test_name": test_case['name'],
                        "status": "SUCCESS",
                        "response_time": response_time,
                        "response_length": len(str(response_data.get('result', ''))),
                        "metadata": response_data.get('metadata', {}),
                        "observability_enabled": response_data.get('metadata', {}).get('observability_enabled', False)
                    }
                    
                    print(f"  ✅ 成功 ({response_time:.2f}秒)")
                    print(f"  📊 Observability: {'有効' if test_result['observability_enabled'] else '無効'}")
                    
                else:
                    test_result = {
                        "test_name": test_case['name'],
                        "status": "FAILED",
                        "error": result.stderr,
                        "response_time": response_time
                    }
                    
                    print(f"  ❌ 失敗: {result.stderr}")
                
                results.append(test_result)
                
                # テスト間の間隔
                time.sleep(2)
                
            except subprocess.TimeoutExpired:
                print(f"  ⏰ タイムアウト")
                results.append({
                    "test_name": test_case['name'],
                    "status": "TIMEOUT",
                    "response_time": 60
                })
            
            except Exception as e:
                print(f"  ❌ エラー: {e}")
                results.append({
                    "test_name": test_case['name'],
                    "status": "ERROR",
                    "error": str(e)
                })
        
        return results
    
    def test_load_performance(self, num_requests=10):
        """負荷テスト"""
        
        print(f"\n🚀 負荷テスト開始 ({num_requests}リクエスト)...")
        print("=" * 50)
        
        test_prompt = "差出人: me@example.net - システムの負荷テストです。現在の時刻を教えてください。"
        
        results = []
        total_start_time = time.time()
        
        for i in range(num_requests):
            print(f"リクエスト {i+1}/{num_requests}...", end=" ")
            
            try:
                if self.agent_name:
                    cmd = [
                        'agentcore', 'invoke',
                        json.dumps({"prompt": test_prompt})
                    ]
                else:
                    cmd = [
                        'agentcore', 'invoke', '--local',
                        json.dumps({"prompt": test_prompt})
                    ]
                
                start_time = time.time()
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                response_time = time.time() - start_time
                
                if result.returncode == 0:
                    print(f"✅ {response_time:.2f}秒")
                    results.append({
                        "request_id": i + 1,
                        "status": "SUCCESS",
                        "response_time": response_time
                    })
                else:
                    print(f"❌ エラー")
                    results.append({
                        "request_id": i + 1,
                        "status": "FAILED",
                        "response_time": response_time
                    })
                
                # 短い間隔で連続実行
                time.sleep(0.5)
                
            except subprocess.TimeoutExpired:
                print("⏰ タイムアウト")
                results.append({
                    "request_id": i + 1,
                    "status": "TIMEOUT",
                    "response_time": 30
                })
            
            except Exception as e:
                print(f"❌ {e}")
                results.append({
                    "request_id": i + 1,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        total_time = time.time() - total_start_time
        
        # 統計分析
        successful_requests = [r for r in results if r['status'] == 'SUCCESS']
        failed_requests = [r for r in results if r['status'] != 'SUCCESS']
        
        if successful_requests:
            response_times = [r['response_time'] for r in successful_requests]
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            min_response_time = min(response_times)
            
            print(f"\n📊 負荷テスト結果:")
            print(f"  総実行時間: {total_time:.2f}秒")
            print(f"  成功リクエスト: {len(successful_requests)}/{num_requests}")
            print(f"  失敗リクエスト: {len(failed_requests)}/{num_requests}")
            print(f"  平均レスポンス時間: {avg_response_time:.2f}秒")
            print(f"  最大レスポンス時間: {max_response_time:.2f}秒")
            print(f"  最小レスポンス時間: {min_response_time:.2f}秒")
            print(f"  スループット: {len(successful_requests)/total_time:.2f} req/sec")
        
        return {
            "total_requests": num_requests,
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "total_time": total_time,
            "results": results
        }
    
    def test_memory_integration(self):
        """Memory統合テスト"""
        
        print("\n🧠 Memory統合テスト開始...")
        print("=" * 50)
        
        # 段階的な会話テスト
        conversation_steps = [
            {
                "step": 1,
                "prompt": "差出人: me@example.net - こんにちは、私の名前は田中です。",
                "expected_keywords": ["田中", "こんにちは"]
            },
            {
                "step": 2, 
                "prompt": "差出人: me@example.net - 私の注文履歴を確認してください。",
                "expected_keywords": ["注文", "履歴"]
            },
            {
                "step": 3,
                "prompt": "差出人: me@example.net - 先ほどお話しした私の名前を覚えていますか？",
                "expected_keywords": ["田中", "名前"]
            }
        ]
        
        results = []
        
        for step in conversation_steps:
            print(f"\nステップ {step['step']}: {step['prompt'][:50]}...")
            
            try:
                if self.agent_name:
                    cmd = [
                        'agentcore', 'invoke',
                        json.dumps({"prompt": step['prompt']})
                    ]
                else:
                    cmd = [
                        'agentcore', 'invoke', '--local',
                        json.dumps({"prompt": step['prompt']})
                    ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    response_data = json.loads(result.stdout)
                    response_text = response_data.get('result', '')
                    
                    # キーワード検証
                    keywords_found = []
                    for keyword in step['expected_keywords']:
                        if keyword in response_text:
                            keywords_found.append(keyword)
                    
                    memory_enabled = response_data.get('metadata', {}).get('memory_enabled', False)
                    
                    step_result = {
                        "step": step['step'],
                        "status": "SUCCESS",
                        "memory_enabled": memory_enabled,
                        "keywords_found": keywords_found,
                        "keywords_expected": step['expected_keywords'],
                        "response_length": len(response_text)
                    }
                    
                    print(f"  ✅ 成功")
                    print(f"  🧠 Memory: {'有効' if memory_enabled else '無効'}")
                    print(f"  🔍 キーワード: {keywords_found}")
                    
                else:
                    step_result = {
                        "step": step['step'],
                        "status": "FAILED",
                        "error": result.stderr
                    }
                    print(f"  ❌ 失敗: {result.stderr}")
                
                results.append(step_result)
                
                # ステップ間の間隔
                time.sleep(3)
                
            except Exception as e:
                print(f"  ❌ エラー: {e}")
                results.append({
                    "step": step['step'],
                    "status": "ERROR",
                    "error": str(e)
                })
        
        return results
    
    def generate_test_report(self, basic_results, load_results, memory_results):
        """テストレポートを生成"""
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_name": self.agent_name,
            "test_summary": {
                "basic_tests": {
                    "total": len(basic_results),
                    "successful": len([r for r in basic_results if r.get('status') == 'SUCCESS']),
                    "failed": len([r for r in basic_results if r.get('status') != 'SUCCESS'])
                },
                "load_test": {
                    "total_requests": load_results['total_requests'],
                    "successful_requests": load_results['successful_requests'],
                    "failed_requests": load_results['failed_requests'],
                    "total_time": load_results['total_time']
                },
                "memory_tests": {
                    "total": len(memory_results),
                    "successful": len([r for r in memory_results if r.get('status') == 'SUCCESS']),
                    "memory_enabled": any(r.get('memory_enabled', False) for r in memory_results)
                }
            },
            "detailed_results": {
                "basic_tests": basic_results,
                "load_test": load_results,
                "memory_tests": memory_results
            }
        }
        
        # レポートをファイルに保存
        report_filename = f"observability_test_report_{int(time.time())}.json"
        with open(report_filename, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n✅ テストレポートを {report_filename} に保存しました")
        
        return report

def main():
    """メイン実行関数"""
    
    parser = argparse.ArgumentParser(description='Observability 機能のテスト')
    parser.add_argument('command', choices=['basic', 'load', 'memory', 'comprehensive'], 
                       help='実行するテストタイプ')
    parser.add_argument('--agent-name', type=str, 
                       help='テスト対象のエージェント名（クラウドデプロイ版）')
    parser.add_argument('--requests', type=int, default=10,
                       help='負荷テストのリクエスト数')
    
    args = parser.parse_args()
    
    tester = ObservabilityTester(args.agent_name)
    
    print("🧪 AgentCore Observability テスト開始")
    print(f"対象: {'クラウド版 (' + args.agent_name + ')' if args.agent_name else 'ローカル版'}")
    print("=" * 60)
    
    if args.command == 'basic':
        # 基本機能テスト
        results = tester.test_basic_functionality()
        
        successful = len([r for r in results if r.get('status') == 'SUCCESS'])
        print(f"\n📊 基本機能テスト結果: {successful}/{len(results)} 成功")
    
    elif args.command == 'load':
        # 負荷テスト
        results = tester.test_load_performance(args.requests)
        
    elif args.command == 'memory':
        # Memory統合テスト
        results = tester.test_memory_integration()
        
        successful = len([r for r in results if r.get('status') == 'SUCCESS'])
        print(f"\n📊 Memory統合テスト結果: {successful}/{len(results)} 成功")
    
    elif args.command == 'comprehensive':
        # 包括的テスト
        print("🚀 包括的テストを実行中...")
        
        basic_results = tester.test_basic_functionality()
        load_results = tester.test_load_performance(args.requests)
        memory_results = tester.test_memory_integration()
        
        # レポート生成
        report = tester.generate_test_report(basic_results, load_results, memory_results)
        
        print(f"\n📊 包括的テスト結果:")
        print(f"  基本機能: {report['test_summary']['basic_tests']['successful']}/{report['test_summary']['basic_tests']['total']} 成功")
        print(f"  負荷テスト: {report['test_summary']['load_test']['successful_requests']}/{report['test_summary']['load_test']['total_requests']} 成功")
        print(f"  Memory統合: {report['test_summary']['memory_tests']['successful']}/{report['test_summary']['memory_tests']['total']} 成功")
        print(f"  Memory機能: {'有効' if report['test_summary']['memory_tests']['memory_enabled'] else '無効'}")
    
    print(f"\n🎯 次のステップ:")
    print("1. python observability_inspector.py report --hours 1")
    print("2. CloudWatch ダッシュボードで詳細な監視データを確認")
    print("3. python observability_inspector.py dashboard")

if __name__ == "__main__":
    main()