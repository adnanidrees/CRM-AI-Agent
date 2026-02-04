from __future__ import annotations
import requests

GRAPH_BASE = "https://graph.facebook.com"

def wa_send_text(phone_number_id: str, access_token: str, to_number: str, text: str):
    url = f"{GRAPH_BASE}/v20.0/{phone_number_id}/messages"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"messaging_product":"whatsapp","to":to_number,"type":"text","text":{"body":text}}
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()

def graph_send_text(access_token: str, recipient_id: str, text: str):
    url = f"{GRAPH_BASE}/v20.0/me/messages"
    params = {"access_token": access_token}
    payload = {"recipient":{"id":recipient_id},"message":{"text":text}}
    r = requests.post(url, params=params, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()
