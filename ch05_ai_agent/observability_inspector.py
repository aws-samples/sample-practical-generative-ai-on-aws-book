#!/usr/bin/env python3
"""
AgentCore Observability データの確認・分析スクリプト
CloudWatch ログ、メトリクス、トレースの確認機能
"""

import boto3
import json
import time
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
import argparse

class ObservabilityInspector:
    """Observability データの確認・分析クラス"""
    
    def __init__(self):
        self.logs_client = boto3.client('logs')
        self.cloudwatch_client = boto3.client('cloudwatch')
        self.xray_client = boto3.client('xray')
        self.application_signals = boto3.client('application-signals')
        
        # 設定を読み込み
        self.config = self.load_config()
        
    def load_config(self):
        """設定ファイルを読み込み"""
        config = {}
        
        # Observability 設定
        try:
            with open("observability_config.json", "r") as f:
                config.update(json.load(f))
        except FileNotFoundError:
            print("⚠️ observability_config.json が見つかりません")
        
        # Memory 設定
        try:
            with open("memory_config.json", "r") as f:
                memory_config = json.load(f)
                config["memory_id"] = memory_config.get("memory_id")
        except FileNotFoundError:
            print("⚠️ memory_config.json が見つかりません")
        
        # Gateway 設定
        try:
            with open("gateway_config.json", "r") as f:
                gateway_config = json.load(f)
                config["gateway_id"] = gateway_config.get("gateway_id")
        except FileNotFoundError:
            print("⚠️ gateway_config.json が見つかりません")
        
        return config
    
    def get_agent_runtime_logs(self, hours=1, limit=50):
        """エージェントランタイムのログを取得"""
        
        print(f"📝 過去{hours}時間のエージェントランタイムログを取得中...")
        
        # ログ群を検索
        log_groups = []
        try:
            response = self.logs_client.describe_log_groups(
                logGroupNamePrefix='/aws/bedrock-agentcore/runtimes/'
            )
            log_groups = [lg['logGroupName'] for lg in response['logGroups']]
            print(f"見つかったログ群: {len(log_groups)}個")
            
        except ClientError as e:
            print(f"❌ ログ群の取得エラー: {e}")
            return []
        
        if not log_groups:
            print("⚠️ エージェントランタイムのログ群が見つかりません")
            return []
        
        # 各ログ群からログを取得
        all_logs = []
        end_time = int(time.time() * 1000)
        start_time = end_time - (hours * 60 * 60 * 1000)
        
        for log_group in log_groups:
            try:
                response = self.logs_client.filter_log_events(
                    logGroupName=log_group,
                    startTime=start_time,
                    endTime=end_time,
                    limit=limit
                )
                
                events = response.get('events', [])
                for event in events:
                    all_logs.append({
                        'log_group': log_group,
                        'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000),
                        'message': event['message']
                    })
                    
                print(f"  {log_group}: {len(events)}件のログ")
                
            except ClientError as e:
                print(f"⚠️ {log_group} のログ取得エラー: {e}")
        
        # 時系列でソート
        all_logs.sort(key=lambda x: x['timestamp'])
        
        return all_logs
    
    def get_memory_logs(self, hours=1):
        """Memory リソースのログを取得"""
        
        memory_id = self.config.get("memory_id")
        if not memory_id:
            print("⚠️ Memory ID が設定されていません")
            return []
        
        print(f"📝 Memory {memory_id} の過去{hours}時間のログを取得中...")
        
        log_group_name = f'/aws/vendedlogs/bedrock-agentcore/{memory_id}'
        
        try:
            end_time = int(time.time() * 1000)
            start_time = end_time - (hours * 60 * 60 * 1000)
            
            response = self.logs_client.filter_log_events(
                logGroupName=log_group_name,
                startTime=start_time,
                endTime=end_time
            )
            
            events = response.get('events', [])
            logs = []
            
            for event in events:
                logs.append({
                    'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000),
                    'message': event['message']
                })
            
            print(f"✅ {len(logs)}件のMemoryログを取得しました")
            return logs
            
        except ClientError as e:
            if "ResourceNotFoundException" in str(e):
                print(f"⚠️ Memory ログ群が見つかりません: {log_group_name}")
            else:
                print(f"❌ Memory ログ取得エラー: {e}")
            return []
    
    def get_cloudwatch_metrics(self, hours=1):
        """CloudWatch メトリクスを取得"""
        
        print(f"📊 過去{hours}時間のCloudWatchメトリクスを取得中...")
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        metrics_data = {}
        
        # AgentCore メトリクスを取得
        metric_queries = [
            {
                'namespace': 'bedrock-agentcore',
                'metric_name': 'customer_support_requests_total',
                'stat': 'Sum'
            },
            {
                'namespace': 'bedrock-agentcore', 
                'metric_name': 'customer_support_response_time_seconds',
                'stat': 'Average'
            },
            {
                'namespace': 'bedrock-agentcore',
                'metric_name': 'memory_operations_total',
                'stat': 'Sum'
            },
            {
                'namespace': 'bedrock-agentcore',
                'metric_name': 'tool_usage_total',
                'stat': 'Sum'
            }
        ]
        
        for query in metric_queries:
            try:
                response = self.cloudwatch_client.get_metric_statistics(
                    Namespace=query['namespace'],
                    MetricName=query['metric_name'],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=300,  # 5分間隔
                    Statistics=[query['stat']]
                )
                
                datapoints = response.get('Datapoints', [])
                if datapoints:
                    # 時系列でソート
                    datapoints.sort(key=lambda x: x['Timestamp'])
                    metrics_data[query['metric_name']] = datapoints
                    print(f"  {query['metric_name']}: {len(datapoints)}個のデータポイント")
                else:
                    print(f"  {query['metric_name']}: データなし")
                    
            except ClientError as e:
                print(f"⚠️ {query['metric_name']} メトリクス取得エラー: {e}")
        
        return metrics_data
    
    def get_xray_traces(self, hours=1):
        """X-Ray トレースを取得"""
        
        print(f"🔍 過去{hours}時間のX-Rayトレースを取得中...")
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        try:
            # トレースサマリーを取得
            response = self.xray_client.get_trace_summaries(
                TimeRangeType='TimeRangeByStartTime',
                StartTime=start_time,
                EndTime=end_time,
                FilterExpression='service("bedrock-agentcore")'
            )
            
            trace_summaries = response.get('TraceSummaries', [])
            print(f"✅ {len(trace_summaries)}個のトレースサマリーを取得しました")
            
            # 詳細なトレースデータを取得（最初の5個）
            detailed_traces = []
            for summary in trace_summaries[:5]:
                trace_id = summary['Id']
                
                try:
                    trace_response = self.xray_client.batch_get_traces(
                        TraceIds=[trace_id]
                    )
                    
                    traces = trace_response.get('Traces', [])
                    if traces:
                        detailed_traces.append({
                            'trace_id': trace_id,
                            'duration': summary.get('Duration', 0),
                            'response_time': summary.get('ResponseTime', 0),
                            'segments': len(traces[0].get('Segments', []))
                        })
                        
                except ClientError as e:
                    print(f"⚠️ トレース {trace_id} の詳細取得エラー: {e}")
            
            return {
                'summaries': trace_summaries,
                'detailed': detailed_traces
            }
            
        except ClientError as e:
            print(f"❌ X-Ray トレース取得エラー: {e}")
            return {'summaries': [], 'detailed': []}
    
    def analyze_performance(self, metrics_data):
        """パフォーマンス分析"""
        
        print("\n📈 パフォーマンス分析:")
        print("=" * 50)
        
        # リクエスト数分析
        if 'customer_support_requests_total' in metrics_data:
            requests = metrics_data['customer_support_requests_total']
            total_requests = sum(dp['Sum'] for dp in requests)
            print(f"総リクエスト数: {total_requests}")
            
            if requests:
                avg_requests_per_period = total_requests / len(requests)
                print(f"平均リクエスト数/5分: {avg_requests_per_period:.2f}")
        
        # レスポンス時間分析
        if 'customer_support_response_time_seconds' in metrics_data:
            response_times = metrics_data['customer_support_response_time_seconds']
            if response_times:
                avg_response_time = sum(dp['Average'] for dp in response_times) / len(response_times)
                max_response_time = max(dp['Average'] for dp in response_times)
                min_response_time = min(dp['Average'] for dp in response_times)
                
                print(f"平均レスポンス時間: {avg_response_time:.2f}秒")
                print(f"最大レスポンス時間: {max_response_time:.2f}秒")
                print(f"最小レスポンス時間: {min_response_time:.2f}秒")
        
        # ツール使用分析
        if 'tool_usage_total' in metrics_data:
            tool_usage = metrics_data['tool_usage_total']
            total_tool_usage = sum(dp['Sum'] for dp in tool_usage)
            print(f"総ツール使用回数: {total_tool_usage}")
        
        # Memory操作分析
        if 'memory_operations_total' in metrics_data:
            memory_ops = metrics_data['memory_operations_total']
            total_memory_ops = sum(dp['Sum'] for dp in memory_ops)
            print(f"総Memory操作回数: {total_memory_ops}")
    
    def generate_report(self, hours=1):
        """包括的なObservabilityレポートを生成"""
        
        print(f"📊 過去{hours}時間のObservabilityレポートを生成中...")
        print("=" * 60)
        
        # データ収集
        agent_logs = self.get_agent_runtime_logs(hours)
        memory_logs = self.get_memory_logs(hours)
        metrics_data = self.get_cloudwatch_metrics(hours)
        traces_data = self.get_xray_traces(hours)
        
        # レポート生成
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'time_range_hours': hours,
            'summary': {
                'agent_log_entries': len(agent_logs),
                'memory_log_entries': len(memory_logs),
                'metrics_collected': len(metrics_data),
                'traces_found': len(traces_data['summaries'])
            },
            'agent_logs': agent_logs[-10:],  # 最新10件
            'memory_logs': memory_logs[-10:],  # 最新10件
            'metrics': metrics_data,
            'traces': traces_data
        }
        
        # パフォーマンス分析
        self.analyze_performance(metrics_data)
        
        # レポートをファイルに保存
        report_filename = f"observability_report_{int(time.time())}.json"
        with open(report_filename, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n✅ レポートを {report_filename} に保存しました")
        
        return report
    
    def show_dashboard_info(self):
        """CloudWatch ダッシュボード情報を表示"""
        
        print("\n🎯 CloudWatch ダッシュボードアクセス情報:")
        print("=" * 50)
        
        region = boto3.Session().region_name or 'us-east-1'
        
        print(f"🌐 Generative AI Observability ダッシュボード:")
        print(f"   https://console.aws.amazon.com/cloudwatch/home?region={region}#gen-ai-observability")
        
        print(f"\n📝 CloudWatch ログ:")
        print(f"   https://console.aws.amazon.com/cloudwatch/home?region={region}#logsV2:log-groups")
        
        print(f"\n📊 CloudWatch メトリクス:")
        print(f"   https://console.aws.amazon.com/cloudwatch/home?region={region}#metricsV2:")
        
        print(f"\n🔍 X-Ray トレース:")
        print(f"   https://console.aws.amazon.com/xray/home?region={region}#/traces")
        
        print(f"\n🔍 Transaction Search:")
        print(f"   https://console.aws.amazon.com/cloudwatch/home?region={region}#application-signals:services")

def main():
    """メイン実行関数"""
    
    parser = argparse.ArgumentParser(description='AgentCore Observability データの確認・分析')
    parser.add_argument('command', choices=['logs', 'metrics', 'traces', 'report', 'dashboard'], 
                       help='実行するコマンド')
    parser.add_argument('--hours', type=int, default=1, 
                       help='データ取得時間範囲（時間）')
    
    args = parser.parse_args()
    
    inspector = ObservabilityInspector()
    
    if args.command == 'logs':
        # ログ確認
        agent_logs = inspector.get_agent_runtime_logs(args.hours)
        memory_logs = inspector.get_memory_logs(args.hours)
        
        print(f"\n📝 エージェントログ（最新10件）:")
        for log in agent_logs[-10:]:
            print(f"  {log['timestamp']}: {log['message'][:100]}...")
        
        print(f"\n📝 Memoryログ（最新10件）:")
        for log in memory_logs[-10:]:
            print(f"  {log['timestamp']}: {log['message'][:100]}...")
    
    elif args.command == 'metrics':
        # メトリクス確認
        metrics_data = inspector.get_cloudwatch_metrics(args.hours)
        inspector.analyze_performance(metrics_data)
    
    elif args.command == 'traces':
        # トレース確認
        traces_data = inspector.get_xray_traces(args.hours)
        
        print(f"\n🔍 トレースサマリー:")
        for trace in traces_data['detailed']:
            print(f"  ID: {trace['trace_id'][:16]}...")
            print(f"    継続時間: {trace['duration']:.2f}秒")
            print(f"    セグメント数: {trace['segments']}")
    
    elif args.command == 'report':
        # 包括的レポート生成
        inspector.generate_report(args.hours)
    
    elif args.command == 'dashboard':
        # ダッシュボード情報表示
        inspector.show_dashboard_info()

if __name__ == "__main__":
    main()