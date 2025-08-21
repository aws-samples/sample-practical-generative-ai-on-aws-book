#!/usr/bin/env python3
"""
AgentCore Gateway 用の Lambda ツール関数
顧客サポートに役立つ各種ツールを実装
"""

import json
import boto3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


def get_named_parameter(event: Dict[str, Any], name: str) -> Optional[str]:
    """イベントから指定されたパラメータを取得"""
    return event.get(name)


def get_order_history(customer_id: str, limit: int = 5) -> Dict[str, Any]:
    """顧客の注文履歴を取得（模擬データ）"""
    # 実際の実装では DynamoDB や RDS から取得
    mock_orders = [
        {
            "order_id": "ORD-2024-001",
            "date": "2024-01-15",
            "status": "配送完了",
            "items": [
                {"name": "スマートフォン Pro", "price": 89800, "quantity": 1}
            ],
            "total": 89800
        },
        {
            "order_id": "ORD-2024-002", 
            "date": "2024-02-20",
            "status": "配送完了",
            "items": [
                {"name": "ワイヤレスイヤホン", "price": 15800, "quantity": 1},
                {"name": "充電ケーブル", "price": 2800, "quantity": 2}
            ],
            "total": 21400
        },
        {
            "order_id": "ORD-2024-003",
            "date": "2024-03-10", 
            "status": "処理中",
            "items": [
                {"name": "タブレット", "price": 45800, "quantity": 1}
            ],
            "total": 45800
        }
    ]
    
    # 顧客IDに基づいてフィルタリング（実際の実装では DB クエリ）
    customer_orders = mock_orders[:limit]
    
    return {
        "customer_id": customer_id,
        "orders": customer_orders,
        "total_orders": len(customer_orders)
    }


def get_product_info(product_name: str) -> Dict[str, Any]:
    """製品情報を取得（模擬データ）"""
    # 実際の実装では製品データベースから取得
    mock_products = {
        "スマートフォン": {
            "name": "スマートフォン Pro",
            "model": "SP-2024-PRO",
            "price": 89800,
            "description": "最新のプロセッサーと高解像度カメラを搭載したフラッグシップモデル",
            "specifications": {
                "display": "6.7インチ OLED",
                "storage": "256GB",
                "camera": "48MP トリプルカメラ",
                "battery": "4500mAh"
            },
            "warranty": "1年間",
            "availability": "在庫あり"
        },
        "タブレット": {
            "name": "タブレット Pro",
            "model": "TB-2024-PRO", 
            "price": 45800,
            "description": "仕事にも娯楽にも最適な高性能タブレット",
            "specifications": {
                "display": "11インチ LCD",
                "storage": "128GB",
                "processor": "A15 Bionic",
                "battery": "10時間駆動"
            },
            "warranty": "1年間",
            "availability": "在庫あり"
        },
        "ワイヤレスイヤホン": {
            "name": "ワイヤレスイヤホン Pro",
            "model": "WE-2024-PRO",
            "price": 15800,
            "description": "ノイズキャンセリング機能付きの高音質イヤホン",
            "specifications": {
                "battery": "最大30時間再生",
                "connectivity": "Bluetooth 5.3",
                "features": "アクティブノイズキャンセリング",
                "water_resistance": "IPX4"
            },
            "warranty": "1年間",
            "availability": "在庫あり"
        }
    }
    
    # 部分一致で製品を検索
    for key, product in mock_products.items():
        if key.lower() in product_name.lower() or product_name.lower() in key.lower():
            return product
    
    return {
        "error": f"製品 '{product_name}' が見つかりませんでした",
        "available_products": list(mock_products.keys())
    }


def check_shipping_status(order_id: str) -> Dict[str, Any]:
    """配送状況を確認（模擬データ）"""
    # 実際の実装では配送業者の API を呼び出し
    mock_shipping = {
        "ORD-2024-001": {
            "status": "配送完了",
            "tracking_number": "TRK-001-2024",
            "estimated_delivery": "2024-01-18",
            "actual_delivery": "2024-01-17",
            "carrier": "佐川急便",
            "tracking_history": [
                {"date": "2024-01-15", "status": "注文受付", "location": "配送センター"},
                {"date": "2024-01-16", "status": "配送中", "location": "中継センター"},
                {"date": "2024-01-17", "status": "配送完了", "location": "お客様宅"}
            ]
        },
        "ORD-2024-002": {
            "status": "配送完了",
            "tracking_number": "TRK-002-2024", 
            "estimated_delivery": "2024-02-23",
            "actual_delivery": "2024-02-22",
            "carrier": "ヤマト運輸",
            "tracking_history": [
                {"date": "2024-02-20", "status": "注文受付", "location": "配送センター"},
                {"date": "2024-02-21", "status": "配送中", "location": "中継センター"},
                {"date": "2024-02-22", "status": "配送完了", "location": "お客様宅"}
            ]
        },
        "ORD-2024-003": {
            "status": "処理中",
            "tracking_number": "TRK-003-2024",
            "estimated_delivery": "2024-03-15",
            "actual_delivery": None,
            "carrier": "佐川急便",
            "tracking_history": [
                {"date": "2024-03-10", "status": "注文受付", "location": "配送センター"},
                {"date": "2024-03-12", "status": "商品準備中", "location": "倉庫"}
            ]
        }
    }
    
    if order_id in mock_shipping:
        return mock_shipping[order_id]
    else:
        return {
            "error": f"注文ID '{order_id}' が見つかりませんでした",
            "message": "注文IDを確認してください"
        }


def get_support_faq(query: str) -> Dict[str, Any]:
    """サポートFAQを検索（模擬データ）"""
    # 実際の実装では Elasticsearch や OpenSearch を使用
    mock_faqs = [
        {
            "id": "FAQ-001",
            "question": "製品の保証期間はどのくらいですか？",
            "answer": "すべての製品には購入日から1年間のメーカー保証が付いています。保証期間中は無償で修理・交換を承ります。",
            "category": "保証・サポート",
            "keywords": ["保証", "期間", "修理", "交換"]
        },
        {
            "id": "FAQ-002", 
            "question": "返品・交換はできますか？",
            "answer": "商品到着から14日以内であれば、未開封・未使用の商品に限り返品・交換を承ります。詳細は返品ポリシーをご確認ください。",
            "category": "返品・交換",
            "keywords": ["返品", "交換", "14日", "未開封"]
        },
        {
            "id": "FAQ-003",
            "question": "配送料はいくらですか？",
            "answer": "5,000円以上のご注文で送料無料です。5,000円未満の場合は全国一律500円の配送料がかかります。",
            "category": "配送・送料", 
            "keywords": ["配送料", "送料", "5000円", "無料"]
        },
        {
            "id": "FAQ-004",
            "question": "支払い方法は何がありますか？",
            "answer": "クレジットカード、銀行振込、代金引換、コンビニ決済をご利用いただけます。",
            "category": "支払い方法",
            "keywords": ["支払い", "クレジットカード", "銀行振込", "代引き", "コンビニ"]
        }
    ]
    
    # クエリに基づいてFAQを検索
    matching_faqs = []
    query_lower = query.lower()
    
    for faq in mock_faqs:
        # 質問、回答、キーワードで検索
        if (query_lower in faq["question"].lower() or 
            query_lower in faq["answer"].lower() or
            any(keyword in query_lower for keyword in faq["keywords"])):
            matching_faqs.append(faq)
    
    return {
        "query": query,
        "results": matching_faqs,
        "total_results": len(matching_faqs)
    }


def lambda_handler(event, context):
    """Lambda のメインハンドラー関数"""
    print(f"Event: {event}")
    print(f"Context: {context}")
    
    try:
        # AgentCore Gateway からのコンテキスト情報を取得
        tool_name = context.client_context.custom["bedrockAgentCoreToolName"]
        session_id = context.client_context.custom.get("bedrockAgentCoreSessionId")
        
        print(f"Tool name: {tool_name}")
        print(f"Session ID: {session_id}")
        
        # ツール名から実際の関数名を抽出
        if "___" in tool_name:
            resource = tool_name.split("___")[1]
        else:
            resource = tool_name
            
        print(f"Resource: {resource}")
        
        # 各ツールの処理
        if resource == "get_order_history":
            customer_id = get_named_parameter(event, "customer_id")
            limit = get_named_parameter(event, "limit") or 5
            
            if not customer_id:
                return {
                    "statusCode": 400,
                    "body": "❌ customer_id パラメータが必要です"
                }
            
            try:
                limit = int(limit)
            except (ValueError, TypeError):
                limit = 5
                
            result = get_order_history(customer_id, limit)
            return {
                "statusCode": 200,
                "body": json.dumps(result, ensure_ascii=False, indent=2)
            }
            
        elif resource == "get_product_info":
            product_name = get_named_parameter(event, "product_name")
            
            if not product_name:
                return {
                    "statusCode": 400,
                    "body": "❌ product_name パラメータが必要です"
                }
                
            result = get_product_info(product_name)
            return {
                "statusCode": 200,
                "body": json.dumps(result, ensure_ascii=False, indent=2)
            }
            
        elif resource == "check_shipping_status":
            order_id = get_named_parameter(event, "order_id")
            
            if not order_id:
                return {
                    "statusCode": 400,
                    "body": "❌ order_id パラメータが必要です"
                }
                
            result = check_shipping_status(order_id)
            return {
                "statusCode": 200,
                "body": json.dumps(result, ensure_ascii=False, indent=2)
            }
            
        elif resource == "get_support_faq":
            query = get_named_parameter(event, "query")
            
            if not query:
                return {
                    "statusCode": 400,
                    "body": "❌ query パラメータが必要です"
                }
                
            result = get_support_faq(query)
            return {
                "statusCode": 200,
                "body": json.dumps(result, ensure_ascii=False, indent=2)
            }
            
        else:
            return {
                "statusCode": 400,
                "body": f"❌ 不明なツール名: {resource}"
            }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": f"❌ 内部エラー: {str(e)}"
        }


# テスト用のローカル実行
if __name__ == "__main__":
    # テスト用のイベントとコンテキスト
    test_event = {
        "customer_id": "customer_oauth_verified",
        "limit": 3
    }
    
    class MockContext:
        class ClientContext:
            custom = {
                "bedrockAgentCoreToolName": "get_order_history",
                "bedrockAgentCoreSessionId": "test-session-123"
            }
        
        client_context = ClientContext()
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, ensure_ascii=False, indent=2))