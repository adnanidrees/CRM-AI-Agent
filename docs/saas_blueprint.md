# SaaS Blueprint (Ready Spec)

## A) Database schema (core)

### tenants
- id (PK)
- name
- status: pending | active | suspended
- country, timezone, currency
- created_at

### users
- id (PK)
- tenant_id (FK tenants.id, nullable for SuperAdmin)
- email (unique)
- phone (unique)
- password_hash
- role: superadmin | tenant_admin | agent | viewer
- email_verified (bool)
- phone_verified (bool)
- created_at

### otps
- id (PK)
- user_id (FK users.id)
- channel: email | phone
- code_hash
- expires_at
- is_used (bool)

### channel_accounts
- id (PK)
- tenant_id (FK)
- channel: whatsapp | messenger | instagram
- external_id (routing key)
    - whatsapp: phone_number_id
    - messenger: page_id
    - instagram: ig_id
- access_token (encrypt in production)
- app_secret (optional)
- created_at

### contacts / deals / messages
All include tenant_id to enforce isolation.

---

## B) Onboarding flow screens (UI plan)

1) Sign Up  
2) Verify Email + Phone  
3) Pending Approval  
4) Connect Channels (WA/FB/IG)  
5) CRM Dashboard  
6) SuperAdmin Panel

---

## C) Webhook routing logic

1) Detect object:
- whatsapp_business_account => WhatsApp
- page => Messenger
- instagram => Instagram

2) Extract routing key:
- WhatsApp: entry[0].changes[0].value.metadata.phone_number_id
- Messenger: entry[0].id (page_id)
- Instagram: entry[0].id (ig_id)

3) Lookup:
SELECT * FROM channel_accounts WHERE channel=<channel> AND external_id=<routing_key>

4) Use tenant token to reply + save CRM rows under tenant_id
