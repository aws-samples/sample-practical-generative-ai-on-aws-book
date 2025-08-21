#!/usr/bin/env python3
"""
顧客の Memory を初期化し、サンプル会話を投入
長期記憶が機能するための基礎データを作成
"""

from bedrock_agentcore.memory import MemoryClient
import json
import time
import hashlib
from datetime import datetime

def serialize_memory_record(record):
    """Memory レコードを JSON シリアライズ可能な形式に変換"""
    if isinstance(record, dict):
        result = {}
        for key, value in record.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = serialize_memory_record(value)
            elif isinstance(value, list):
                result[key] = [serialize_memory_record(item) for item in value]
            else:
                result[key] = value
        return result
    elif isinstance(record, list):
        return [serialize_memory_record(item) for item in record]
    elif isinstance(record, datetime):
        return record.isoformat()
    else:
        return record

def format_memory_results(memories):
    """Memory の検索結果を読みやすい形式に整形"""
    if not memories:
        return "記憶が見つかりません"
    
    if isinstance(memories, list):
        formatted = []
        for memory in memories:
            if isinstance(memory, dict):
                # content.text を抽出
                content = memory.get('content', {})
                if isinstance(content, dict):
                    text = content.get('text', '')
                    # JSON 文字列の場合はパース
                    try:
                        if text.startswith('{'):
                            parsed = json.loads(text)
                            formatted.append(parsed)
                        else:
                            formatted.append(text)
                    except:
                        formatted.append(text)
                else:
                    formatted.append(str(memory))
        return formatted
    else:
        return str(memories)

def initialize_customer_memory(email: str):
    """特定顧客の Memory を初期化"""
    
    # Memory 設定を読み込み
    with open("memory_config.json", "r") as f:
        MEMORY_ID = json.load(f)["memory_id"]
    
    memory_client = MemoryClient()
    
    # 顧客IDを生成
    actor_id = f"customer_{hashlib.md5(email.encode()).hexdigest()[:8]}"
    
    print(f"顧客 {email} ({actor_id}) の Memory を初期化中...")
    
    # 過去のサポート履歴をシミュレート（複数セッション）
    conversations = [
        {
            "session_id": "session_001_initial_purchase",
            "messages": [
                ("こんにちは。スマートフォンを購入したいのですが、おすすめはありますか？", "USER"),
                ("お問い合わせありがとうございます。お客様のご利用用途を教えていただけますか？", "ASSISTANT"),
                ("主に仕事用です。メールとビデオ会議が多いです。バッテリー持ちを重視します。", "USER"),
                ("ビジネス用途でバッテリー重視でしたら、ProModel-X がおすすめです。", "ASSISTANT"),
                ("それにします。あと、充電器は付属していますか？", "USER"),
                ("はい、USB-C充電器が付属しています。EU/UK/USプラグアダプターも同梱です。", "ASSISTANT"),
                ("完璧です。注文します。カバーも一緒に購入したいです。", "USER"),
                ("承知しました。黒色のプレミアムカバーがビジネス用途に人気です。", "ASSISTANT"),
                ("それも追加でお願いします。", "USER"),
                ("ご注文を承りました。注文番号は#1234です。", "ASSISTANT")
            ]
        },
        {
            "session_id": "session_002_setup_help",
            "messages": [
                ("先日購入したスマートフォンが届きました。初期設定を教えてください。", "USER"),
                ("お買い上げありがとうございます。まず、電源ボタンを3秒長押ししてください。", "ASSISTANT"),
                ("起動しました。次は？", "USER"),
                ("言語設定画面が表示されます。日本語を選択してください。", "ASSISTANT"),
                ("できました。WiFi設定はどうすればいいですか？", "USER"),
                ("設定メニューから「ネットワーク」を選び、お使いのWiFiを選択してください。", "ASSISTANT"),
                ("接続できました。メールの設定も教えてください。", "USER"),
                ("「アカウント」から「メールアカウント追加」を選択し、お使いのメールアドレスを入力してください。", "ASSISTANT"),
                ("すべて設定できました。ありがとうございます。", "USER"),
                ("お役に立てて光栄です。他にご不明な点があればお気軽にお問い合わせください。", "ASSISTANT")
            ]
        },
        {
            "session_id": "session_003_troubleshooting",
            "messages": [
                ("スマートフォンの調子が悪いです。時々フリーズします。", "USER"),
                ("ご不便をおかけして申し訳ございません。いつ頃から発生していますか？", "ASSISTANT"),
                ("2日前からです。アプリを複数起動すると固まります。", "USER"),
                ("メモリ不足の可能性があります。バックグラウンドアプリを終了してみてください。", "ASSISTANT"),
                ("どうやって終了させますか？初心者なので詳しく教えてください。", "USER"),
                ("画面下部から上にスワイプし、起動中のアプリを上にスワイプして終了させてください。", "ASSISTANT"),
                ("できました！動きが軽くなりました。", "USER"),
                ("よかったです。定期的にアプリを終了させることをお勧めします。", "ASSISTANT"),
                ("わかりました。丁寧な説明ありがとうございます。メールで手順書を送ってもらえますか？", "USER"),
                ("承知しました。トラブルシューティングガイドをメールでお送りします。", "ASSISTANT")
            ]
        }
    ]
    
    # 各セッションの会話を Memory に投入
    for conv in conversations:
        print(f"  セッション {conv['session_id']} を投入中...")
        
        memory_client.create_event(
            memory_id=MEMORY_ID,
            actor_id=actor_id,
            session_id=conv['session_id'],
            messages=conv['messages']
        )
        
        # API レート制限を考慮
        time.sleep(2)
    
    print(f"✅ 初期会話データを投入しました（{len(conversations)} セッション）")
    
    # 長期記憶が処理されるのを待つ
    print("⏳ 長期記憶の処理を待機中（60秒）...")
    time.sleep(60)
    
    # 長期記憶が生成されたか確認
    try:
        # ユーザー嗜好を確認
        preferences_raw = memory_client.retrieve_memories(
            memory_id=MEMORY_ID,
            namespace=f"/preferences/{actor_id}",
            query="顧客の好みと特徴"
        )
        preferences = format_memory_results(preferences_raw)
        
        # 過去の問題を確認
        issues_raw = memory_client.retrieve_memories(
            memory_id=MEMORY_ID,
            namespace=f"/issues/{actor_id}/products",
            query="過去の問題と解決策"
        )
        issues = format_memory_results(issues_raw)
        
        # セッションサマリーを確認
        summaries_raw = memory_client.retrieve_memories(
            memory_id=MEMORY_ID,
            namespace=f"/summaries/{actor_id}/session_003_troubleshooting",
            query="トラブルシューティングの要約"
        )
        summaries = format_memory_results(summaries_raw)
        
        print("\n=== 生成された長期記憶 ===")
        print(f"顧客嗜好数: {len(preferences_raw) if isinstance(preferences_raw, list) else 0}")
        print(f"記録された問題数: {len(issues_raw) if isinstance(issues_raw, list) else 0}")
        print(f"セッション要約数: {len(summaries_raw) if isinstance(summaries_raw, list) else 0}")
        
        # 読みやすい形式で主要な記憶を表示
        if preferences:
            print("\n📝 顧客の特徴:")
            if isinstance(preferences, list) and len(preferences) > 0:
                for i, pref in enumerate(preferences[:3], 1):  # 最初の3つを表示
                    if isinstance(pref, dict):
                        print(f"  {i}. {pref.get('preference', pref.get('context', str(pref)))}")
                    else:
                        print(f"  {i}. {str(pref)[:100]}...")  # 最初の100文字
        
        if issues:
            print("\n⚠️ 記録された問題:")
            if isinstance(issues, list) and len(issues) > 0:
                for i, issue in enumerate(issues[:3], 1):
                    print(f"  {i}. {str(issue)[:100]}...")
        
        return {
            "actor_id": actor_id,
            "sessions_created": len(conversations),
            "memories_generated": {
                "preferences_count": len(preferences_raw) if isinstance(preferences_raw, list) else 0,
                "issues_count": len(issues_raw) if isinstance(issues_raw, list) else 0,
                "summaries_count": len(summaries_raw) if isinstance(summaries_raw, list) else 0
            },
            "status": "success"
        }
        
    except Exception as e:
        print(f"⚠️ 長期記憶の取得でエラー: {e}")
        return {
            "actor_id": actor_id,
            "sessions_created": len(conversations),
            "status": "processing",
            "note": "長期記憶は処理中です。数分後に再度確認してください。"
        }

def bulk_initialize_customers():
    """複数の顧客データを一括初期化"""
    
    test_customers = [
        "me@example.net",
        "john.doe@example.com",
        "support.test@example.org"
    ]
    
    results = []
    for email in test_customers:
        print(f"\n{'='*50}")
        result = initialize_customer_memory(email)
        results.append(result)
        print(f"{'='*50}\n")
        
        # 次の顧客の処理前に少し待機
        time.sleep(5)
    
    return results

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 特定の顧客を初期化
        email = sys.argv[1]
        result = initialize_customer_memory(email)
    else:
        # デフォルトの顧客を初期化
        result = initialize_customer_memory("me@example.net")
    
    # シリアライズ可能な形式で出力
    print(f"\n最終結果: {json.dumps(result, ensure_ascii=False, indent=2)}")