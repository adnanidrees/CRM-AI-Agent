# CRM AI SaaS (Blueprint) — Multi-Client WhatsApp / Facebook / Instagram

This is a **SaaS-ready blueprint** that matches your requirements:

✅ Multi-tenant DB: tenants, users, channel_accounts  
✅ Client registration + email/phone OTP verification (provider is "mock" by default)  
✅ Super Admin approval (tenant status: pending/active/suspended)  
✅ Webhook routing per-tenant (select correct tokens by phone_number_id/page_id/ig_id)  
✅ CRM: contacts, deals, messages per tenant  
✅ AI agent: structured output (reply + stage + extracted fields)  
✅ Works locally with SQLite; recommended Postgres in production

> OTP sending is mocked (printed in server logs).  
> Replace providers with real SMS/Email (Twilio/MessageBird + SendGrid/Mailgun).

---

## Quick start (Windows PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

Open:
- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/health

---

## Key flows

### 1) Client Signup + Verify
1. POST `/auth/register` (email + phone + password + company name)
2. OTP codes are logged in console (mock)
3. POST `/auth/verify-email` and `/auth/verify-phone`
4. Tenant stays **pending** until SuperAdmin approves

### 2) SuperAdmin Approve
- SuperAdmin auto-created on first run using `SUPERADMIN_EMAIL` + `SUPERADMIN_PASSWORD`
- POST `/admin/tenants/{tenant_id}/approve`

### 3) Tenant Connect Channels
After approval, client logs in and saves tokens:
- POST `/tenant/channels` with:
  - channel = whatsapp/messenger/instagram
  - external_id = phone_number_id (WA) OR page_id (FB) OR ig_id (IG)
  - access_token, app_secret (optional)

### 4) Webhook routing
Webhook endpoint:
- GET  `/webhooks/meta` verify
- POST `/webhooks/meta` events

Routing keys:
- WhatsApp: value.metadata.phone_number_id
- Messenger: entry[].id (page_id)
- Instagram: entry[].id (ig_id) OR object=instagram

---

See `docs/saas_blueprint.md` for schema + onboarding screens + routing logic.
