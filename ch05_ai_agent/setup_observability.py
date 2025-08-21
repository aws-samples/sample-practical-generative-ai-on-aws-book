#!/usr/bin/env python3
"""
AgentCore Observability のセットアップスクリプト
CloudWatch Transaction Search の有効化とログ配信設定を自動化
"""

import boto3
import json
import time
from botocore.exceptions import ClientError

def setup_cloudwatch_transaction_search():
    """CloudWatch Transaction Search を有効化"""
    
    print("🔍 CloudWatch Transaction Search を有効化中...")
    
    # CloudWatch Application Signals クライアント
    application_signals = boto3.client('application-signals')
    
    try:
        # Transaction Search を有効化
        response = application_signals.start_discovery()
        print("✅ CloudWatch Transaction Search が有効化されました")
        
        # 設定確認
        config = application_signals.get_service_level_objective()
        print(f"📊 Transaction Search 設定: {config}")
        
        return True
        
    except ClientError as e:
        if "AlreadyExistsException" in str(e):
            print("ℹ️ CloudWatch Transaction Search は既に有効化されています")
            return True
        else:
            print(f"❌ Transaction Search 有効化エラー: {e}")
            return False

def setup_observability_for_memory():
    """Memory リソースの Observability を設定"""
    
    # Memory 設定を読み込み
    try:
        with open("memory_config.json", "r") as f:
            memory_config = json.load(f)
            memory_id = memory_config["memory_id"]
    except FileNotFoundError:
        print("⚠️ memory_config.json が見つかりません。Memory の Observability 設定をスキップします。")
        return None
    
    print(f"📝 Memory {memory_id} の Observability を設定中...")
    
    # AWS 情報を取得
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    region = boto3.Session().region_name or 'us-east-1'
    
    # Memory ARN を構築
    memory_arn = f"arn:aws:bedrock-agentcore:{region}:{account_id}:memory/{memory_id}"
    
    logs_client = boto3.client('logs')
    
    try:
        # ログ配信設定
        enable_observability_for_resource(
            resource_arn=memory_arn,
            resource_id=memory_id,
            account_id=account_id,
            region=region
        )
        
        print(f"✅ Memory {memory_id} の Observability が設定されました")
        return memory_id
        
    except Exception as e:
        print(f"❌ Memory Observability 設定エラー: {e}")
        return None

def enable_observability_for_resource(resource_arn, resource_id, account_id, region='us-east-1'):
    """
    Bedrock AgentCore リソースの Observability を有効化
    公式ドキュメントのサンプルコードを基に実装
    """
    logs_client = boto3.client('logs', region_name=region)

    # ログ配信用のログ群を作成
    log_group_name = f'/aws/vendedlogs/bedrock-agentcore/{resource_id}'
    
    try:
        logs_client.create_log_group(logGroupName=log_group_name)
        print(f"📝 ログ群を作成: {log_group_name}")
    except ClientError as e:
        if "ResourceAlreadyExistsException" in str(e):
            print(f"ℹ️ ログ群は既に存在: {log_group_name}")
        else:
            raise e
    
    log_group_arn = f'arn:aws:logs:{region}:{account_id}:log-group:{log_group_name}'
    
    # 配信ソースを作成（ログ用）
    try:
        logs_source_response = logs_client.put_delivery_source(
            name=f"{resource_id}-logs-source",
            logType="APPLICATION_LOGS",
            resourceArn=resource_arn
        )
        print(f"📤 ログ配信ソースを作成: {logs_source_response['deliverySource']['name']}")
    except ClientError as e:
        if "ResourceAlreadyExistsException" in str(e):
            print(f"ℹ️ ログ配信ソースは既に存在: {resource_id}-logs-source")
        else:
            print(f"⚠️ ログ配信ソース作成エラー: {e}")
    
    # 配信ソースを作成（トレース用）
    try:
        traces_source_response = logs_client.put_delivery_source(
            name=f"{resource_id}-traces-source", 
            logType="TRACES",
            resourceArn=resource_arn
        )
        print(f"🔍 トレース配信ソースを作成: {traces_source_response['deliverySource']['name']}")
    except ClientError as e:
        if "ResourceAlreadyExistsException" in str(e):
            print(f"ℹ️ トレース配信ソースは既に存在: {resource_id}-traces-source")
        else:
            print(f"⚠️ トレース配信ソース作成エラー: {e}")
    
    # 配信先を作成（ログ用）
    try:
        logs_destination_response = logs_client.put_delivery_destination(
            name=f"{resource_id}-logs-destination",
            deliveryDestinationType='CWL',
            deliveryDestinationConfiguration={
                'destinationResourceArn': log_group_arn,
            }
        )
        print(f"📥 ログ配信先を作成: {logs_destination_response['deliveryDestination']['name']}")
    except ClientError as e:
        if "ResourceAlreadyExistsException" in str(e):
            print(f"ℹ️ ログ配信先は既に存在: {resource_id}-logs-destination")
        else:
            print(f"⚠️ ログ配信先作成エラー: {e}")
    
    # 配信先を作成（トレース用）
    try:
        traces_destination_response = logs_client.put_delivery_destination(
            name=f"{resource_id}-traces-destination",
            deliveryDestinationType='XRAY'
        )
        print(f"🔍 トレース配信先を作成: {traces_destination_response['deliveryDestination']['name']}")
    except ClientError as e:
        if "ResourceAlreadyExistsException" in str(e):
            print(f"ℹ️ トレース配信先は既に存在: {resource_id}-traces-destination")
        else:
            print(f"⚠️ トレース配信先作成エラー: {e}")
    
    # 配信を作成（ログ）
    try:
        logs_delivery = logs_client.create_delivery(
            deliverySourceName=f"{resource_id}-logs-source",
            deliveryDestinationArn=f"arn:aws:logs:{region}:{account_id}:delivery-destination:{resource_id}-logs-destination"
        )
        print(f"🚚 ログ配信を作成: {logs_delivery['delivery']['id']}")
    except ClientError as e:
        if "ResourceAlreadyExistsException" in str(e):
            print(f"ℹ️ ログ配信は既に存在")
        else:
            print(f"⚠️ ログ配信作成エラー: {e}")
    
    # 配信を作成（トレース）
    try:
        traces_delivery = logs_client.create_delivery(
            deliverySourceName=f"{resource_id}-traces-source", 
            deliveryDestinationArn=f"arn:aws:logs:{region}:{account_id}:delivery-destination:{resource_id}-traces-destination"
        )
        print(f"🔍 トレース配信を作成: {traces_delivery['delivery']['id']}")
    except ClientError as e:
        if "ResourceAlreadyExistsException" in str(e):
            print(f"ℹ️ トレース配信は既に存在")
        else:
            print(f"⚠️ トレース配信作成エラー: {e}")
    
    print(f"✅ {resource_id} の Observability が有効化されました")

def setup_gateway_observability():
    """Gateway リソースの Observability を設定"""
    
    try:
        with open("gateway_config.json", "r") as f:
            gateway_config = json.load(f)
            gateway_id = gateway_config["gateway_id"]
    except FileNotFoundError:
        print("⚠️ gateway_config.json が見つかりません。Gateway の Observability 設定をスキップします。")
        return None
    
    print(f"🌐 Gateway {gateway_id} の Observability を設定中...")
    
    # AWS 情報を取得
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    region = boto3.Session().region_name or 'us-east-1'
    
    # Gateway ARN を構築
    gateway_arn = f"arn:aws:bedrock-agentcore:{region}:{account_id}:gateway/{gateway_id}"
    
    try:
        # ログ配信設定
        enable_observability_for_resource(
            resource_arn=gateway_arn,
            resource_id=gateway_id,
            account_id=account_id,
            region=region
        )
        
        print(f"✅ Gateway {gateway_id} の Observability が設定されました")
        return gateway_id
        
    except Exception as e:
        print(f"❌ Gateway Observability 設定エラー: {e}")
        return None

def main():
    """メイン実行関数"""
    
    print("🚀 AgentCore Observability セットアップを開始...")
    print("=" * 60)
    
    # 1. CloudWatch Transaction Search を有効化
    transaction_search_enabled = setup_cloudwatch_transaction_search()
    
    print("\n" + "=" * 60)
    
    # 2. Memory の Observability を設定
    memory_id = setup_observability_for_memory()
    
    print("\n" + "=" * 60)
    
    # 3. Gateway の Observability を設定
    gateway_id = setup_gateway_observability()
    
    print("\n" + "=" * 60)
    
    # 結果をまとめて表示
    print("📊 Observability セットアップ結果:")
    print(f"  Transaction Search: {'✅ 有効' if transaction_search_enabled else '❌ 無効'}")
    print(f"  Memory Observability: {'✅ 設定済み' if memory_id else '⚠️ スキップ'}")
    print(f"  Gateway Observability: {'✅ 設定済み' if gateway_id else '⚠️ スキップ'}")
    
    # 設定情報を保存
    observability_config = {
        "transaction_search_enabled": transaction_search_enabled,
        "memory_id": memory_id,
        "gateway_id": gateway_id,
        "setup_timestamp": time.time()
    }
    
    with open("observability_config.json", "w") as f:
        json.dump(observability_config, f, indent=2)
    
    print(f"\n✅ 設定情報を observability_config.json に保存しました")
    
    print("\n🎯 次のステップ:")
    print("1. エージェントコードに OTEL インストルメンテーションを追加")
    print("2. requirements.txt に aws-opentelemetry-distro を追加")
    print("3. エージェントを再デプロイ")
    print("4. CloudWatch ダッシュボードで監視データを確認")

if __name__ == "__main__":
    main()