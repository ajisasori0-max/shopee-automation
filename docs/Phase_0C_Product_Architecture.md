# Phase 0C — Product Architecture & Domain Model
## Commerce Operating System (COS) / Future Commerce Hermes Platform

**Role:** Chief Product Architect  
**Date:** 2026-07-16  
**Status:** Proposed — awaiting approval  
**Constraint:** No implementation. No code. No databases. No refactoring. Design only.

---

## Executive Summary

We are designing a **Commerce Operating System (COS)** — first as Gerard’s personal commerce command center, then as a multi-store, multi-marketplace, and eventually multi-tenant SaaS platform.

The product is not a dashboard. It is not a Shopee connector. It is not an AI chatbot. It is a **system of record, reasoning, and control** for commerce operations.

The core product hypothesis is:

> **Small ecommerce sellers need a single system that knows their business state, alerts them to what matters, proposes decisions, and executes low-risk actions safely — while keeping them in control.**

Today, Gerard uses disconnected tools: Shopee Seller Center, Shopee Ads, spreadsheets, local scripts, Obsidian, Telegram. Each holds a fragment of truth. The product replaces that fragmentation with a unified operating system.

Tomorrow, the same architecture serves multiple stores, marketplaces, and companies — because the domain model is designed around commerce concepts, not marketplace APIs.

---

# Part 1 — Product Definition

## 1.1 Mission

To build a commerce operating system that gives small and mid-sized ecommerce operators complete visibility, intelligent prioritization, and safe automation — so they can run a bigger business with fewer operational mistakes.

## 1.2 Vision

A single platform where the business state is always known, risks are surfaced before they become crises, decisions are proposed with evidence, and low-risk operations run autonomously — while high-stakes decisions remain human-controlled.

## 1.3 Target Customer Today (Customer #1)

**Gerard** — a solo entrepreneur running a Shopee store in Indonesia.

**Profile:**
- 1 marketplace, 1 store, multiple SKUs
- Uses ads, suppliers, courier fulfillment
- Manages operations largely manually or via ad-hoc scripts
- Needs visibility into profit, inventory, ads, and cashflow
- Wants to spend less time on routine monitoring and more time on growth

**Pain points today:**
- No single source of truth for profit/loss
- Order and income API integration is broken, so financials are unreliable
- Ads performance and inventory are disconnected
- Decisions are made on gut or partial data
- Too many manual checks and reports
- Knowledge lives in scattered notes

## 1.4 Target Customer in 3 Years

**Small-to-medium ecommerce operators in Southeast Asia** running 1-10 stores across multiple marketplaces.

**Profile:**
- 1-10 stores per organization
- 2-5 marketplaces (Shopee, Lazada, Tokopedia, TikTok Shop, etc.)
- 10-1,000 SKUs
- 1-10 team members
- Needs automation, analytics, and AI-assisted decision making
- Wants to understand true profitability, not just revenue

**Pain points in 3 years:**
- Managing multi-platform operations across teams
- Understanding real profit after platform fees, ads, shipping, returns, and COGS
- Avoiding stockouts and overstock
- Optimizing ad spend across channels
- Supplier coordination and payment tracking
- Customer service at scale
- Compliance and tax readiness

## 1.5 Core Value Proposition

1. **Unified Business Truth** — One system that knows revenue, cost, profit, inventory, ads, and cash across all stores and marketplaces.
2. **Intelligent Prioritization** — Tells the operator what to do today, not just what happened yesterday.
3. **Safe Automation** — Executes low-risk actions (data sync, reports, status checks, budget tweaks within policy) autonomously.
4. **Explainable Decisions** — Every proposal, alert, and recommendation links back to data, policy, and reasoning.
5. **Institutional Memory** — Decisions, SOPs, incidents, and lessons live in a structured knowledge base that improves over time.

## 1.6 Competitive Positioning

| Competitor | What They Do | Our Differentiation |
|------------|--------------|---------------------|
| **BigSeller** | Multi-channel seller tool for Southeast Asia | We are not just listing/order management; we are an **operating system** with business state, AI-assisted decisions, and institutional memory. |
| **CiciKelola** | Indonesian store management + analytics | We go deeper into **profitability modeling, AI reasoning, and automation safety** rather than just dashboards. |
| **Shopee Seller Center** | Platform-native tools | We are **cross-platform**, **profit-aware**, and **AI-assisted**. |
| **Lazada Seller Center** | Platform-native tools | Same as above. |
| **TikTok Shop Seller Center** | Platform-native tools | Same as above. |
| **Google Sheets / Excel** | Manual reporting | We replace manual work with **automated data collection, validation, and AI synthesis**. |
| **Hire a VA** | Human operational support | We make the operator **self-sufficient** with better tooling, not dependent on labor. |

**Why choose us instead of BigSeller or CiciKelola?**

- **Profit-first, not revenue-first.** We model true profit including COGS, platform fees, shipping, returns, and ad spend.
- **AI-assisted reasoning, not just dashboards.** We don’t just show data; we explain what it means and propose actions.
- **Safe automation.** We distinguish between low-risk actions and high-stakes decisions, with approvals and audit trails.
- **Institutional memory.** Knowledge is preserved in Obsidian, not lost in chat history or spreadsheets.
- **Evolves into a platform.** Built for multi-store and multi-tenant from the start, not retrofitted.

## 1.7 Key Product Assumptions I Am Challenging

| Common Assumption | Challenge | Our Stance |
|-------------------|-----------|------------|
| Sellers want more dashboards. | They want to know what to do. | Dashboards are necessary but secondary to action and prioritization. |
| AI should replace the seller. | AI should augment the seller. | High-stakes decisions stay human. Low-risk work gets automated. |
| Multi-marketplace support means building N connectors. | It means building a **platform abstraction** and N connectors. | The core product is marketplace-agnostic. |
| SaaS must be multi-tenant from day one. | SaaS should emerge from a real customer operating system. | Gerard is Customer #1. The platform grows organically. |
| Reports are the product. | Reports are an output. The product is **business control**. | Reports, alerts, and decisions are all expressions of the same state. |
| Knowledge management is optional. | Knowledge is the only durable advantage. | SOPs, decisions, and lessons are first-class product features. |

---

# Part 2 — Domain Model

## 2.1 Design Principles

1. **Marketplace-agnostic.** Entities are business concepts, not API responses.
2. **Tenant-aware.** Multi-tenancy is possible later without redesign.
3. **Event-driven lifecycle.** Entities change state through events and actions.
4. **Traceable.** Every entity links to its source, owner, and audit history.
5. **No over-modeling.** We model only what is needed today, but leave room for growth.

## 2.2 Core Entities

### 2.2.1 Organization

| Field | Description |
|-------|-------------|
| `organization_id` | Unique identifier |
| `name` | Business or legal name |
| `type` | sole_prop, pt, cv, etc. |
| `country` | Tax jurisdiction |
| `currency` | Base currency |
| `timezone` | Operating timezone |
| `owner` | Human owner/user |
| `created_at` | Timestamp |
| `status` | active, suspended, archived |

**Purpose:** Represents the legal/business entity that owns stores and employees.  
**Owner:** User (Gerard).  
**Relationships:** Has many Businesses, Stores, Employees, Warehouses.  
**Lifecycle:** Created by user, updated when legal/tax info changes, archived when dissolved.  
**Required data:** name, type, country, currency.  
**Optional data:** tax_id, address, bank_accounts.  
**Example:** Gerard’s holding entity in Indonesia.

---

### 2.2.2 Business

| Field | Description |
|-------|-------------|
| `business_id` | Unique identifier |
| `organization_id` | Parent organization |
| `name` | Brand or trading name |
| `industry` | category (fashion, electronics, etc.) |
| `strategy` | Growth strategy summary |
| `status` | active, paused, archived |

**Purpose:** A commercial unit under an Organization. One Organization can have multiple Businesses (e.g., different brands).  
**Owner:** User.  
**Relationships:** Belongs to Organization; has many Stores, Products, Suppliers, Campaigns.  
**Lifecycle:** Created for a new brand or product line; archived if discontinued.  
**Required data:** name, organization_id.  
**Optional data:** industry, strategy, target_margin.  
**Example:** Gerard’s main fashion brand.

---

### 2.2.3 Store

| Field | Description |
|-------|-------------|
| `store_id` | Unique identifier |
| `business_id` | Parent business |
| `marketplace_id` | Linked marketplace (Shopee, Lazada, etc.) |
| `external_store_id` | Platform-native store ID |
| `name` | Store display name |
| `country` | Store country |
| `status` | active, inactive, disconnected, suspended |
| `credentials_ref` | Reference to secret vault entry |

**Purpose:** A single storefront on a marketplace.  
**Owner:** User.  
**Relationships:** Belongs to Business; has many Orders, Products, Campaigns.  
**Lifecycle:** Created when connecting a marketplace account; disconnected if credentials expire or user removes it.  
**Required data:** business_id, marketplace_id, external_store_id, name.  
**Optional data:** country, currency, timezone.  
**Example:** Gerard’s Shopee store in Indonesia (shop_id 1147948100).

---

### 2.2.4 Marketplace

| Field | Description |
|-------|-------------|
| `marketplace_id` | Unique identifier |
| `code` | shopee, lazada, tokopedia, tiktok, etc. |
| `name` | Display name |
| `supported_countries` | List of supported country codes |
| `features` | Supported capabilities (orders, ads, inventory, reviews, etc.) |
| `connector_version` | Version of the connector |

**Purpose:** A supported ecommerce platform. The core product never hardcodes marketplace behavior.  
**Owner:** System (platform provider).  
**Relationships:** Has many Stores, Connectors, MarketplacePolicies.  
**Lifecycle:** Added when a new connector is built; versioned as APIs change.  
**Required data:** code, name.  
**Optional data:** supported_countries, features, connector_version.  
**Example:** Shopee.

---

### 2.2.5 Warehouse

| Field | Description |
|-------|-------------|
| `warehouse_id` | Unique identifier |
| `organization_id` | Parent organization |
| `name` | Warehouse name |
| `type` | own, supplier, dropship, 3pl |
| `location` | City / country |
| `status` | active, inactive |

**Purpose:** A physical or logical location where inventory is held.  
**Owner:** User.  
**Relationships:** Belongs to Organization; has many Inventory records.  
**Lifecycle:** Created when a new storage location is added.  
**Required data:** name, type, organization_id.  
**Optional data:** address, contact, capacity.  
**Example:** Gerard’s home warehouse; supplier’s warehouse; 3PL partner.

---

### 2.2.6 Supplier

| Field | Description |
|-------|-------------|
| `supplier_id` | Unique identifier |
| `organization_id` | Parent organization |
| `name` | Supplier name |
| `contact` | Primary contact |
| `payment_terms` | e.g., 30 days, COD |
| `lead_time_days` | Average lead time |
| `status` | active, inactive, blacklisted |
| `rating` | Internal performance score |

**Purpose:** A vendor that provides products.  
**Owner:** User + Supplier Agent.  
**Relationships:** Belongs to Organization; supplies many Products; has many PurchaseOrders.  
**Lifecycle:** Created by user; updated by Supplier Agent with performance data; blacklisted if repeatedly defective/late.  
**Required data:** name, organization_id.  
**Optional data:** contact, payment_terms, lead_time, rating, notes.  
**Example:** Fabric supplier in Bandung.

---

### 2.2.7 Product

| Field | Description |
|-------|-------------|
| `product_id` | Unique identifier |
| `business_id` | Parent business |
| `sku` | Internal SKU |
| `name` | Product name |
| `category` | Product category |
| `base_cogs` | Base cost of goods sold |
| `weight` | Weight for shipping estimation |
| `status` | active, discontinued, draft |
| `primary_supplier_id` | Preferred supplier |

**Purpose:** A catalog item that can be sold.  
**Owner:** User + Inventory Agent.  
**Relationships:** Belongs to Business; has many Variants, Inventory records, PurchaseOrders.  
**Lifecycle:** Created as draft; activated when ready to sell; discontinued when no longer sold.  
**Required data:** sku, name, business_id.  
**Optional data:** category, base_cogs, weight, supplier_id.  
**Example:** Men’s cotton t-shirt.

---

### 2.2.8 Variant

| Field | Description |
|-------|-------------|
| `variant_id` | Unique identifier |
| `product_id` | Parent product |
| `sku` | Variant SKU |
| `name` | Variant description (e.g., size, color) |
| `barcode` | EAN/UPC/etc. |
| `weight` | Override weight |
| `base_cogs` | Override cost |
| `status` | active, inactive |

**Purpose:** A specific sellable configuration of a Product.  
**Owner:** User + Inventory Agent.  
**Relationships:** Belongs to Product; has Inventory; appears in OrderItems.  
**Lifecycle:** Created with Product; activated/deactivated as inventory changes.  
**Required data:** product_id, sku, name.  
**Optional data:** barcode, weight, base_cogs.  
**Example:** Men’s cotton t-shirt — Black, Size L.

---

### 2.2.9 Inventory

| Field | Description |
|-------|-------------|
| `inventory_id` | Unique identifier |
| `variant_id` | Linked variant |
| `warehouse_id` | Linked warehouse |
| `quantity_available` | Sellable quantity |
| `quantity_reserved` | Reserved for orders |
| `quantity_inbound` | Incoming from supplier |
| `reorder_point` | Threshold to reorder |
| `reorder_quantity` | Suggested reorder amount |
| `last_updated` | Timestamp |
| `source` | marketplace_sync, manual, purchase_order |

**Purpose:** Tracks stock levels per variant per warehouse.  
**Owner:** Inventory Agent + deterministic sync.  
**Relationships:** Belongs to Variant and Warehouse.  
**Lifecycle:** Updated continuously by marketplace sync, manual adjustments, purchase orders, and sales.  
**Required data:** variant_id, warehouse_id, quantity_available.  
**Optional data:** reorder_point, reorder_quantity, last_updated.  
**Example:** 45 black L t-shirts in home warehouse.

---

### 2.2.10 PurchaseOrder

| Field | Description |
|-------|-------------|
| `po_id` | Unique identifier |
| `supplier_id` | Supplier |
| `warehouse_id` | Destination warehouse |
| `status` | draft, sent, acknowledged, partially_received, received, cancelled |
| `items` | List of variant_id + quantity + unit_cost |
| `total_cost` | Total PO value |
| `expected_delivery` | Expected date |
| `actual_delivery` | Actual date |
| `payment_status` | unpaid, partial, paid |

**Purpose:** A request to a supplier to deliver inventory.  
**Owner:** Inventory Agent proposes; User approves.  
**Relationships:** Linked to Supplier, Warehouse, Products/Variants.  
**Lifecycle:** Drafted by agent, sent by user or system, acknowledged by supplier, received into inventory.  
**Required data:** supplier_id, warehouse_id, items.  
**Optional data:** expected_delivery, payment_terms.  
**Example:** PO to fabric supplier for 200 t-shirts.

---

### 2.2.11 Customer

| Field | Description |
|-------|-------------|
| `customer_id` | Unique identifier |
| `organization_id` | Parent organization |
| `external_customer_id` | Platform-native customer ID (may be hashed) |
| `name` | Customer name (if available) |
| `phone` | Masked phone |
| `email` | Masked email |
| `city` | Shipping city |
| `first_order_at` | First order date |
| `lifetime_value` | Computed LTV |
| `order_count` | Number of orders |
| `return_rate` | Return rate |

**Purpose:** A buyer who has placed one or more orders.  
**Owner:** System (derived from orders).  
**Relationships:** Belongs to Organization; has many Orders.  
**Lifecycle:** Created on first order; updated with each subsequent order.  
**Required data:** organization_id, external_customer_id.  
**Optional data:** name, phone, email, city, LTV.  
**Example:** A repeat buyer in Jakarta.

---

### 2.2.12 Order

| Field | Description |
|-------|-------------|
| `order_id` | Unique identifier |
| `store_id` | Store where order was placed |
| `external_order_id` | Platform-native order ID |
| `customer_id` | Customer |
| `status` | pending, processing, shipped, delivered, cancelled, returned, refunded |
| `order_date` | Order timestamp |
| `currency` | Order currency |
| `subtotal` | Product total |
| `discount` | Discounts applied |
| `shipping_paid` | Shipping paid by customer |
| `platform_fee` | Marketplace commission/fee |
| `tax` | Tax amount |
| `total` | Order total |
| `payment_status` | paid, pending, refunded |
| `source` | marketplace_sync |

**Purpose:** A customer purchase transaction.  
**Owner:** Deterministic sync from marketplace.  
**Relationships:** Belongs to Store; has many OrderItems; linked to Customer and Shipments.  
**Lifecycle:** Created from marketplace sync; status updated as order progresses.  
**Required data:** store_id, external_order_id, order_date, status.  
**Optional data:** amounts, customer_id, payment_status.  
**Example:** Order #SP-12345 on Shopee.

---

### 2.2.13 OrderItem

| Field | Description |
|-------|-------------|
| `order_item_id` | Unique identifier |
| `order_id` | Parent order |
| `variant_id` | Linked variant |
| `quantity` | Quantity sold |
| `unit_price` | Price per unit |
| `discount` | Discount per unit |
| `cogs` | Cost of goods per unit at time of sale |
| `platform_fee` | Fee attributed to item |
| `status` | normal, returned, refunded |

**Purpose:** A line item within an Order.  
**Owner:** Deterministic sync.  
**Relationships:** Belongs to Order and Variant.  
**Lifecycle:** Created with Order; updated if returned/refunded.  
**Required data:** order_id, variant_id, quantity, unit_price.  
**Optional data:** cogs, discount, platform_fee.  
**Example:** 2 × black L t-shirts in order #SP-12345.

---

### 2.2.14 Shipment

| Field | Description |
|-------|-------------|
| `shipment_id` | Unique identifier |
| `order_id` | Linked order |
| `courier_id` | Courier |
| `tracking_number` | Tracking number |
| `status` | pending, picked_up, in_transit, delivered, failed, returned |
| `shipped_at` | Timestamp |
| `estimated_delivery` | ETA |
| `delivered_at` | Timestamp |
| `source` | marketplace_sync or courier_api |

**Purpose:** The physical delivery of an order.  
**Owner:** Operations Agent + deterministic sync.  
**Relationships:** Belongs to Order; linked to Courier.  
**Lifecycle:** Created when order ships; updated via courier API or marketplace sync.  
**Required data:** order_id, tracking_number.  
**Optional data:** courier_id, status, timestamps.  
**Example:** JNE tracking #JNE12345 for order #SP-12345.

---

### 2.2.15 Return

| Field | Description |
|-------|-------------|
| `return_id` | Unique identifier |
| `order_id` | Linked order |
| `order_item_id` | Linked item |
| `reason` | Customer reason |
| `status` | requested, approved, rejected, received, refunded |
| `requested_at` | Timestamp |
| `resolved_at` | Timestamp |
| `refund_amount` | Refund amount |

**Purpose:** A customer return request and resolution.  
**Owner:** Customer Agent + Operations Agent.  
**Relationships:** Belongs to Order.  
**Lifecycle:** Created from marketplace sync; resolved by user or policy.  
**Required data:** order_id, reason, status.  
**Optional data:** order_item_id, refund_amount.  
**Example:** Return for wrong size.

---

### 2.2.16 Campaign

| Field | Description |
|-------|-------------|
| `campaign_id` | Unique identifier |
| `store_id` | Linked store |
| `external_campaign_id` | Platform-native campaign ID |
| `name` | Campaign name |
| `type` | ads, discount, flash_sale, voucher, bundle |
| `status` | active, paused, ended, draft |
| `start_at` | Start time |
| `end_at` | End time |
| `budget` | Budget amount (if applicable) |
| `source` | marketplace_sync |

**Purpose:** A marketing or promotional campaign.  
**Owner:** Growth Agent + User.  
**Relationships:** Belongs to Store; has many Ads (if type=ads) or Promotions.  
**Lifecycle:** Created on marketplace; synced into COS; updated by Growth Agent or user.  
**Required data:** store_id, external_campaign_id, name, type.  
**Optional data:** budget, dates, status.  
**Example:** Shopee ads campaign “Test-Campaign-1”.

---

### 2.2.17 Advertisement (Ad)

| Field | Description |
|-------|-------------|
| `ad_id` | Unique identifier |
| `campaign_id` | Linked campaign |
| `external_ad_id` | Platform-native ad ID |
| `name` | Ad name |
| `type` | product_ad, keyword_ad, etc. |
| `status` | active, paused, ended |
| `targeting` | Targeting summary |
| `source` | marketplace_sync |

**Purpose:** A single ad unit within a Campaign.  
**Owner:** Growth Agent.  
**Relationships:** Belongs to Campaign.  
**Lifecycle:** Created and updated via marketplace sync.  
**Required data:** campaign_id, external_ad_id.  
**Optional data:** name, type, targeting.  
**Example:** Product ad for SKU-12345.

---

### 2.2.18 Promotion

| Field | Description |
|-------|-------------|
| `promotion_id` | Unique identifier |
| `campaign_id` | Linked campaign |
| `type` | discount, voucher, flash_sale, bundle |
| `discount_amount` | Discount value |
| `discount_type` | percentage, fixed |
| `applicable_variants` | List of variant IDs |
| `start_at` | Start time |
| `end_at` | End time |

**Purpose:** A non-ad promotional mechanic.  
**Owner:** User + Growth Agent.  
**Relationships:** Belongs to Campaign.  
**Lifecycle:** Created by user or synced from marketplace; evaluated by Growth Agent.  
**Required data:** campaign_id, type.  
**Optional data:** discount, dates, variants.  
**Example:** 10% flash sale for selected SKUs.

---

### 2.2.19 AdPerformance (Daily)

| Field | Description |
|-------|-------------|
| `ad_performance_id` | Unique identifier |
| `ad_id` | Linked ad |
| `date` | Date of performance |
| `impressions` | Impressions |
| `clicks` | Clicks |
| `ctr` | Click-through rate |
| `spend` | Spend amount |
| `orders` | Attributed orders |
| `gmv` | Attributed GMV |
| `roas` | Return on ad spend |
| `source` | marketplace_sync |

**Purpose:** Time-series performance data for ads.  
**Owner:** Deterministic sync.  
**Relationships:** Belongs to Ad.  
**Lifecycle:** Created daily by marketplace sync.  
**Required data:** ad_id, date.  
**Optional data:** impressions, clicks, spend, orders, gmv, roas.  
**Example:** Ad performance for 2026-07-15.

---

### 2.2.20 Expense

| Field | Description |
|-------|-------------|
| `expense_id` | Unique identifier |
| `organization_id` | Parent organization |
| `category` | rent, salaries, software, packaging, shipping, ads, other |
| `description` | What the expense was for |
| `amount` | Amount |
| `currency` | Currency |
| `incurred_at` | Date incurred |
| `paid_at` | Date paid |
| `payment_method` | bank_transfer, cash, card |
| `source` | manual, bank_sync, marketplace_sync |

**Purpose:** Any cost incurred by the business.  
**Owner:** Finance Agent + User.  
**Relationships:** Belongs to Organization.  
**Lifecycle:** Created manually or synced; categorized by Finance Agent or user.  
**Required data:** organization_id, category, amount, incurred_at.  
**Optional data:** description, paid_at, source.  
**Example:** Monthly packaging cost of Rp 5M.

---

### 2.2.21 Revenue

| Field | Description |
|-------|-------------|
| `revenue_id` | Unique identifier |
| `order_id` | Linked order (if applicable) |
| `organization_id` | Parent organization |
| `amount` | Revenue amount |
| `currency` | Currency |
| `recognized_at` | Revenue recognition date |
| `type` | product_sales, shipping, other |
| `source` | computed_from_order |

**Purpose:** Revenue recognized by the business.  
**Owner:** Deterministic calculation from Orders.  
**Relationships:** Linked to Order.  
**Lifecycle:** Generated from order data when order is paid/delivered.  
**Required data:** organization_id, amount, recognized_at.  
**Optional data:** order_id, type.  
**Example:** Rp 1.5M from order #SP-12345.

---

### 2.2.22 Payment

| Field | Description |
|-------|-------------|
| `payment_id` | Unique identifier |
| `order_id` | Linked order |
| `amount` | Payment amount |
| `currency` | Currency |
| `status` | pending, received, held, refunded, released |
| `platform_fee` | Marketplace fee deducted |
| `net_amount` | Amount after fees |
| `expected_payout_at` | Expected payout date |
| `paid_out_at` | Actual payout date |
| `source` | marketplace_sync |

**Purpose:** A payment associated with an order or payout.  
**Owner:** Deterministic sync.  
**Relationships:** Linked to Order.  
**Lifecycle:** Created from order/payout sync; updated as payment status changes.  
**Required data:** order_id, amount.  
**Optional data:** fees, status, payout dates.  
**Example:** Shopee payout for order #SP-12345.

---

### 2.2.23 Invoice

| Field | Description |
|-------|-------------|
| `invoice_id` | Unique identifier |
| `organization_id` | Parent organization |
| `invoice_number` | Tax invoice number |
| `type` | incoming, outgoing |
| `amount` | Amount |
| `tax_amount` | Tax amount |
| `status` | draft, issued, paid, cancelled |
| `issued_at` | Issue date |
| `due_at` | Due date |
| `paid_at` | Payment date |
| `source` | manual, platform_sync |

**Purpose:** Tax/compliance document for transactions.  
**Owner:** Compliance Agent + User.  
**Relationships:** Belongs to Organization; may link to Orders or Expenses.  
**Lifecycle:** Created manually or synced from platform; tracked by Compliance Agent.  
**Required data:** organization_id, invoice_number, type, amount.  
**Optional data:** tax, status, dates.  
**Example:** Outgoing tax invoice for a Shopee order.

---

### 2.2.24 Employee / User

| Field | Description |
|-------|-------------|
| `user_id` | Unique identifier |
| `organization_id` | Parent organization |
| `email` | Login email |
| `role` | owner, admin, finance, ops, marketing, viewer |
| `status` | active, inactive |
| `permissions` | Granular permissions |

**Purpose:** A person who uses the platform.  
**Owner:** User (owner).  
**Relationships:** Belongs to Organization.  
**Lifecycle:** Invited by owner; deactivated when they leave.  
**Required data:** organization_id, email, role.  
**Optional data:** permissions, status.  
**Example:** Gerard as owner; a future finance assistant as finance role.

---

### 2.2.25 Task

| Field | Description |
|-------|-------------|
| `task_id` | Unique identifier |
| `organization_id` | Parent organization |
| `title` | Task title |
| `description` | Task details |
| `status` | open, in_progress, blocked, done, cancelled |
| `priority` | low, medium, high, critical |
| `assigned_to` | User or agent |
| `due_at` | Due date |
| `created_by` | Agent or user |
| `source` | agent, manual, incident |

**Purpose:** A unit of work to be done.  
**Owner:** COO Agent + User.  
**Relationships:** Belongs to Organization; may link to Risks, Incidents, Decisions.  
**Lifecycle:** Created by agent or user; assigned and tracked until done.  
**Required data:** organization_id, title, status.  
**Optional data:** description, priority, due_at, assigned_to.  
**Example:** “Approve supplier PO for 200 t-shirts.”

---

### 2.2.26 Notification

| Field | Description |
|-------|-------------|
| `notification_id` | Unique identifier |
| `organization_id` | Parent organization |
| `user_id` | Recipient |
| `channel` | telegram, email, sms, in_app |
| `type` | alert, report, decision_required, info |
| `title` | Short title |
| `body` | Message body |
| `priority` | low, medium, high, critical |
| `sent_at` | Timestamp |
| `read_at` | Timestamp |
| `source_event` | Reference to originating event |

**Purpose:** A message sent to a user.  
**Owner:** Notification Module.  
**Relationships:** Belongs to Organization and User.  
**Lifecycle:** Created by event; delivered via channel; marked read.  
**Required data:** organization_id, user_id, channel, type, body.  
**Optional data:** title, priority, source_event.  
**Example:** Telegram alert: “Stockout risk for SKU-12345 in 7 days.”

---

### 2.2.27 Approval

| Field | Description |
|-------|-------------|
| `approval_id` | Unique identifier |
| `organization_id` | Parent organization |
| `decision_id` | Linked decision |
| `requested_by` | Agent or user |
| `approver` | Required approver |
| `status` | pending, approved, rejected, expired |
| `requested_at` | Timestamp |
| `resolved_at` | Timestamp |
| `reason` | Reason for approval/rejection |

**Purpose:** A request for human authorization.  
**Owner:** Approval Engine.  
**Relationships:** Linked to Decision.  
**Lifecycle:** Created by Decision Engine; resolved by approver.  
**Required data:** organization_id, decision_id, requested_by, approver.  
**Optional data:** reason, timestamps.  
**Example:** Approval request to increase ad budget by 20%.

---

### 2.2.28 SOP

| Field | Description |
|-------|-------------|
| `sop_id` | Unique identifier |
| `organization_id` | Parent organization |
| `name` | SOP name |
| `domain` | finance, inventory, growth, ops, customer, supplier, compliance |
| `version` | Version number |
| `content` | Markdown content |
| `status` | active, draft, archived |
| `source` | obsidian |

**Purpose:** A standard operating procedure.  
**Owner:** User.  
**Relationships:** Belongs to Organization; referenced by agents.  
**Lifecycle:** Created by user; versioned; archived when replaced.  
**Required data:** organization_id, name, domain.  
**Optional data:** content, version, status.  
**Example:** “How to handle a return request.”

---

### 2.2.29 KPI

| Field | Description |
|-------|-------------|
| `kpi_id` | Unique identifier |
| `organization_id` | Parent organization |
| `name` | KPI name |
| `domain` | revenue, profit, inventory, ads, ops, customer |
| `value` | Current value |
| `target` | Target value |
| `unit` | currency, percentage, count, days |
| `period` | daily, weekly, monthly, quarterly |
| `computed_at` | Timestamp |
| `source` | business_state |

**Purpose:** A metric tracked over time.  
**Owner:** Analytics Agent + deterministic computation.  
**Relationships:** Belongs to Organization.  
**Lifecycle:** Computed from Business State; stored historically.  
**Required data:** organization_id, name, value.  
**Optional data:** target, unit, period.  
**Example:** Daily net profit margin target 15%.

---

### 2.2.30 Incident

| Field | Description |
|-------|-------------|
| `incident_id` | Unique identifier |
| `organization_id` | Parent organization |
| `severity` | low, medium, high, critical |
| `status` | open, investigating, resolved, closed |
| `title` | Short description |
| `description` | Detailed description |
| `started_at` | Timestamp |
| `resolved_at` | Timestamp |
| `owner` | User or agent |
| `source` | monitoring, agent, user, system |
| `related_entity_type` | e.g., order, campaign, supplier |
| `related_entity_id` | ID |

**Purpose:** A disruption or problem requiring attention.  
**Owner:** Operations Agent + User.  
**Relationships:** Belongs to Organization; linked to Tasks, Decisions.  
**Lifecycle:** Detected, triaged, assigned, resolved, post-mortem.  
**Required data:** organization_id, title, severity, status.  
**Optional data:** description, owner, related entities.  
**Example:** “Ads API returned zero data for 6 hours.”

---

### 2.2.31 Decision

| Field | Description |
|-------|-------------|
| `decision_id` | Unique identifier |
| `organization_id` | Parent organization |
| `title` | Decision question |
| `domain` | finance, inventory, growth, ops, customer, supplier, compliance |
| `options` | JSON options |
| `recommended_option` | Agent recommendation |
| `confidence` | Confidence score |
| `impact` | low, medium, high, critical |
| `status` | pending, approved, rejected, auto_executed, expired |
| `decided_by` | auto or user_id |
| `decided_at` | Timestamp |
| `reason` | Reasoning |
| `source` | agent, user, system |

**Purpose:** A recorded choice with context and outcome.  
**Owner:** Decision Engine.  
**Relationships:** Belongs to Organization; linked to Approval, Task, Incident.  
**Lifecycle:** Proposed, evaluated, approved/rejected, executed, verified.  
**Required data:** organization_id, title, domain, options.  
**Optional data:** recommendation, confidence, impact, status, reason.  
**Example:** “Increase TikTok budget by 15%?”

---

### 2.2.32 Risk

| Field | Description |
|-------|-------------|
| `risk_id` | Unique identifier |
| `organization_id` | Parent organization |
| `title` | Risk description |
| `domain` | inventory, finance, supplier, customer, compliance, ops |
| `severity` | low, medium, high, critical |
| `probability` | low, medium, high |
| `impact` | low, medium, high, critical |
| `status` | active, mitigated, accepted, closed |
| `owner` | User or agent |
| `mitigation` | Mitigation plan |
| `detected_at` | Timestamp |
| `updated_at` | Timestamp |

**Purpose:** A potential problem that could harm the business.  
**Owner:** COO Agent + relevant domain agent.  
**Relationships:** Belongs to Organization; linked to Tasks, Decisions.  
**Lifecycle:** Detected, assessed, mitigated or accepted, closed.  
**Required data:** organization_id, title, domain, severity.  
**Optional data:** probability, impact, mitigation, owner.  
**Example:** “Supplier lead time increasing; stockout risk in 7 days.”

---

## 2.3 Entity Relationship Summary

```
Organization
├── Business
│   ├── Store
│   │   ├── Order
│   │   │   ├── OrderItem
│   │   │   ├── Shipment
│   │   │   ├── Return
│   │   │   └── Payment
│   │   ├── Campaign
│   │   │   ├── Ad
│   │   │   ├── Promotion
│   │   │   └── AdPerformance
│   │   └── Product (via catalog linkage)
│   ├── Product
│   │   ├── Variant
│   │   │   └── Inventory
│   │   └── Supplier (via primary_supplier_id)
│   └── Supplier
│       └── PurchaseOrder
├── Warehouse
│   └── Inventory
├── Customer
│   └── Order
├── Employee / User
├── Expense
├── Revenue
├── Invoice
├── Task
├── Notification
├── Approval
├── SOP
├── KPI
├── Incident
├── Decision
└── Risk
```

---

# Part 3 — Modules

## 3.1 Module Design Principles

1. **Each module owns one domain.** No cross-domain logic leaking.
2. **Modules communicate via events and APIs.** Not file parsing or direct DB access outside their domain.
3. **Modules are replaceable.** A better inventory module can be swapped without rewriting finance.
4. **Modules are tenant-aware.** All data is scoped to organization_id/business_id.

## 3.2 Module Registry

### 3.2.1 Identity

| Field | Description |
|-------|-------------|
| **Responsibilities** | User authentication, organization management, roles, permissions, session management |
| **Inputs** | Login credentials, invitations, role changes |
| **Outputs** | Authenticated sessions, user profiles, role assignments |
| **Dependencies** | None (foundational) |
| **Future extensibility** | SSO, MFA, team management, API keys for integrations |

### 3.2.2 Settings

| Field | Description |
|-------|-------------|
| **Responsibilities** | Organization settings, business config, currency, timezone, notification preferences, integration settings |
| **Inputs** | User configuration, marketplace credentials |
| **Outputs** | Configuration values consumed by other modules |
| **Dependencies** | Identity, Secret Vault |
| **Future extensibility** | Multi-currency, multi-location tax settings, branding |

### 3.2.3 Marketplace Connector Layer

| Field | Description |
|-------|-------------|
| **Responsibilities** | Abstract all marketplace-specific APIs; provide canonical data to Commerce Core |
| **Inputs** | Marketplace credentials, connector configuration, sync requests |
| **Outputs** | Normalized orders, products, inventory, ads, payments, reviews |
| **Dependencies** | Settings, Secret Vault, Observability |
| **Future extensibility** | New connectors are plugins implementing a standard interface |

### 3.2.4 Commerce Core

| Field | Description |
|-------|-------------|
| **Responsibilities** | Unified business data model; order, product, inventory, customer, shipment lifecycle |
| **Inputs** | Normalized data from connectors, manual entry, other modules |
| **Outputs** | Single source of truth for operational data |
| **Dependencies** | Marketplace Connector Layer, Identity, Settings |
| **Future extensibility** | Multi-store, multi-business, multi-warehouse, complex fulfillment |

### 3.2.5 Inventory

| Field | Description |
|-------|-------------|
| **Responsibilities** | Stock tracking, reorder points, inbound tracking, stock alerts, warehouse management |
| **Inputs** | Product/variant data, order data, purchase orders, manual adjustments |
| **Outputs** | Inventory levels, reorder proposals, stockout/overstock alerts |
| **Dependencies** | Commerce Core, Supplier, Analytics |
| **Future extensibility** | Demand forecasting, multi-location optimization, 3PL integrations |

### 3.2.6 Finance

| Field | Description |
|-------|-------------|
| **Responsibilities** | Revenue recognition, expense tracking, COGS, profit calculation, cashflow, payouts, tax readiness |
| **Inputs** | Orders, payments, expenses, inventory, ad spend, platform fees |
| **Outputs** | P&L, balance sheet, cashflow, reconciliation reports, expense alerts |
| **Dependencies** | Commerce Core, Inventory, Advertising, Settings |
| **Future extensibility** | Bank feeds, accounting software integrations (Xero, QuickBooks), multi-currency |

### 3.2.7 Advertising

| Field | Description |
|-------|-------------|
| **Responsibilities** | Campaign and ad management, performance tracking, budget proposals, optimization recommendations |
| **Inputs** | Ad performance data, campaign settings, inventory, finance data |
| **Outputs** | Budget proposals, campaign recommendations, performance reports |
| **Dependencies** | Commerce Core, Finance, Inventory |
| **Future extensibility** | Cross-platform ad management (Meta, Google), creative performance, attribution modeling |

### 3.2.8 CRM (Customer)

| Field | Description |
|-------|-------------|
| **Responsibilities** | Customer profiles, order history, segmentation, review tracking, ticket-like issues |
| **Inputs** | Orders, reviews, returns, customer interactions |
| **Outputs** | Customer segments, repeat buyer alerts, satisfaction trends, response drafts |
| **Dependencies** | Commerce Core |
| **Future extensibility** | Email/SMS marketing, loyalty programs, chat integration |

### 3.2.9 Customer Service

| Field | Description |
|-------|-------------|
| **Responsibilities** | Review responses, return handling, complaint triage, response drafting |
| **Inputs** | Reviews, returns, customer messages, SOPs |
| **Outputs** | Response drafts, escalation flags, refund recommendations |
| **Dependencies** | CRM, Commerce Core, SOP/Knowledge |
| **Future extensibility** | Chatbot integration, automated return classification |

### 3.2.10 Supplier

| Field | Description |
|-------|-------------|
| **Responsibilities** | Supplier directory, performance tracking, purchase order proposals, negotiation support |
| **Inputs** | Purchase orders, inventory, product data, supplier communications |
| **Outputs** | Supplier scorecards, PO proposals, negotiation drafts |
| **Dependencies** | Inventory, Commerce Core |
| **Future extensibility** | Supplier portals, contract management, B2B procurement |

### 3.2.11 Analytics

| Field | Description |
|-------|-------------|
| **Responsibilities** | Trend analysis, forecasting, cohort analysis, anomaly detection, experiment tracking |
| **Inputs** | All operational data, external signals |
| **Outputs** | Forecasts, anomaly alerts, dashboards, experiment reports |
| **Dependencies** | Commerce Core, Finance, Inventory, Advertising |
| **Future extensibility** | Machine learning models, predictive LTV, demand forecasting |

### 3.2.12 Reporting

| Field | Description |
|-------|-------------|
| **Responsibilities** | Generate scheduled and on-demand reports: daily, weekly, monthly, executive |
| **Inputs** | Business State, KPIs, module outputs |
| **Outputs** | PDF/Excel/markdown reports, Obsidian notes, dashboard widgets |
| **Dependencies** | Analytics, Finance, Commerce Core |
| **Future extensibility** | Custom report builder, white-label reports, scheduled email delivery |

### 3.2.13 Automation

| Field | Description |
|-------|-------------|
| **Responsibilities** | Workflow engine, scheduling, action execution, retry logic, verification |
| **Inputs** | Scheduled tasks, agent proposals, approved decisions |
| **Outputs** | Executed actions, verification results, logs |
| **Dependencies** | All modules, Approval Engine, Observability |
| **Future extensibility** | Visual workflow builder, conditional automation, third-party triggers |

### 3.2.14 Approval Engine

| Field | Description |
|-------|-------------|
| **Responsibilities** | Evaluate proposals against policy, route to auto-approve or human approval, track decisions |
| **Inputs** | Agent proposals, policy config, user roles |
| **Outputs** | Approved actions, approval requests, decision log entries |
| **Dependencies** | Identity, Automation, Knowledge |
| **Future extensibility** | Multi-level approvals, delegation, policy simulation |

### 3.2.15 Knowledge

| Field | Description |
|-------|-------------|
| **Responsibilities** | Manage institutional memory: SOPs, decision logs, incidents, strategy, meeting notes, agent docs |
| **Inputs** | Human writing, machine-generated reports, decisions, incidents |
| **Outputs** | Structured notes in Obsidian, agent-readable context |
| **Dependencies** | None (but consumed by all AI modules) |
| **Future extensibility** | Knowledge graph, semantic search, AI-powered SOP suggestions |

### 3.2.16 Notifications

| Field | Description |
|-------|-------------|
| **Responsibilities** | Route alerts and reports to the right channel and user at the right priority |
| **Inputs** | Events, priorities, user preferences |
| **Outputs** | Telegram, email, SMS, in-app notifications |
| **Dependencies** | Identity, Settings |
| **Future extensibility** | Notification templates, quiet hours, escalation chains |

### 3.2.17 Audit

| Field | Description |
|-------|-------------|
| **Responsibilities** | Immutable log of all state changes, actions, and decisions |
| **Inputs** | Events from all modules |
| **Outputs** | Audit trail, compliance reports, forensic logs |
| **Dependencies** | All modules |
| **Future extensibility** | Compliance dashboards, regulatory exports, tamper-proof logs |

### 3.2.18 Observability

| Field | Description |
|-------|-------------|
| **Responsibilities** | Health monitoring, metrics, alerting, log aggregation, SLA tracking |
| **Inputs** | Logs, events, metrics from all modules |
| **Outputs** | Health dashboard, alerts, incident triggers |
| **Dependencies** | All modules |
| **Future extensibility** | APM, distributed tracing, anomaly detection on system health |

### 3.2.19 AI Layer

| Field | Description |
|-------|-------------|
| **Responsibilities** | Host department agents, COO agent, reasoning, proposal generation, knowledge retrieval |
| **Inputs** | Business State, Obsidian knowledge, module outputs, user messages |
| **Outputs** | Proposals, decisions, briefs, drafted communications, tasks |
| **Dependencies** | All modules, Knowledge, Approval Engine |
| **Future extensibility** | Additional agents, voice interface, predictive analytics |

---

# Part 4 — Marketplace Connector Architecture

## 4.1 Core Principle

The platform must think in **business concepts**, not marketplace APIs. A Shopee order and a Lazada order are both `Order` entities with the same fields. The connector layer handles the translation.

## 4.2 Connector Interface

Every connector implements:

```
Connector Interface:

- authenticate(credentials) → AuthToken
- refresh_auth(token) → AuthToken
- get_orders(store, since) → List[Order]
- get_order_detail(store, order_id) → Order
- get_products(store) → List[Product]
- get_inventory(store) → List[Inventory]
- get_campaigns(store) → List[Campaign]
- get_ads(store) → List[Ad]
- get_ad_performance(store, since) → List[AdPerformance]
- get_payments(store, since) → List[Payment]
- get_reviews(store, since) → List[Review]
- get_returns(store, since) → List[Return]
- apply_action(store, action) → Result
- health_check(store) → ConnectorHealth
- validate_webhook(payload) → WebhookEvent
```

## 4.3 Shopee Connector

- **Authentication:** Partner ID + Shop ID + OAuth token refresh.
- **APIs:** Shopee Open Platform (seller API) + Shopee Ads API.
- **Mapping:** Shopee-specific fields (e.g., `ordersn`, `total_amount`) map to canonical `Order` fields.
- **Challenges:** Token expiry every 4 hours for ads; API schema changes; income API currently broken/unreliable.
- **Versioning:** Connector version pinned to API version; migrations handled in connector.

## 4.4 Lazada Connector

- **Authentication:** Lazada Open Platform app key + secret + access token.
- **APIs:** Lazada Seller API, Lazada Sponsored Solutions (ads).
- **Mapping:** Lazada order fields → canonical `Order`.
- **Challenges:** Different ad platform, different payout model, different fee structure.

## 4.5 Tokopedia Connector

- **Authentication:** Tokopedia Open API client credentials.
- **APIs:** Tokopedia Seller API, campaign/promotion APIs.
- **Mapping:** Tokopedia order and product fields → canonical entities.
- **Challenges:** Webhook support, fulfillment model differences.

## 4.6 TikTok Shop Connector

- **Authentication:** TikTok Shop Partner API / Seller API credentials.
- **APIs:** TikTok Shop Seller API, TikTok Shop Ads (if available).
- **Mapping:** TikTok order, product, fulfillment fields → canonical entities.
- **Challenges:** Rapidly evolving API, different commission structure, live commerce integration.

## 4.7 Adding a New Marketplace

To add a new marketplace:

1. Implement the connector interface for that marketplace.
2. Map marketplace-specific entities to canonical schema.
3. Add marketplace metadata to `Marketplace` table.
4. Add health checks and validation tests.
5. Update documentation and SOPs.
6. No changes to Finance, Inventory, Advertising, or AI modules.

## 4.8 Connector Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Core Platform                            │
│  Commerce Core · Finance · Inventory · Advertising · AI · etc. │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ Canonical API (Orders, Products, Ads, etc.)
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Connector Abstraction Layer                    │
│        Auth · Rate Limiting · Retries · Validation · Webhooks   │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        │              │              │              │
        ▼              ▼              ▼              ▼
   ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐
   │ Shopee  │  │ Lazada  │  │Tokopedia │  │ TikTok   │
   │Connector│  │Connector│  │ Connector│  │  Shop    │
   └─────────┘  └─────────┘  └──────────┘  └──────────┘
```

---

# Part 5 — Business State

## 5.1 Purpose

The **Business State** is the real-time, derived, canonical snapshot of the business. It is the heartbeat of the platform. Every agent, dashboard, report, and notification reads from it.

It is not the raw database. It is the **answer to the question: “What is the state of the business right now?”**

## 5.2 Business State Schema

### 5.2.1 Metadata

| Field | Value | Example |
|-------|-------|---------|
| `state_id` | UUID | uuidv4 |
| `organization_id` | FK | org_gerard |
| `generated_at` | ISO timestamp | 2026-07-16T08:00:00+07:00 |
| `valid_until` | ISO timestamp | 2026-07-16T09:00:00+07:00 |
| `version` | Semantic version | 2026.07.16.08.00 |
| `data_quality_score` | 0-1 | 0.92 |
| `sources_fresh` | List of sources | ["shopee_orders", "shopee_ads", "manual_expenses"] |
| `sources_stale` | List of stale sources | ["lazada_orders"] |
| `alerts_count` | Integer | 3 |
| `pending_decisions_count` | Integer | 2 |
| `open_tasks_count` | Integer | 5 |

### 5.2.2 Summary

| Field | Description | Owner | Update Frequency | Source |
|-------|-------------|-------|------------------|--------|
| `revenue_today` | Total recognized revenue today | Finance | Every 15-60 min | Orders + Payments |
| `revenue_7d` | Rolling 7-day revenue | Finance | Hourly | Orders + Payments |
| `revenue_30d` | Rolling 30-day revenue | Finance | Hourly | Orders + Payments |
| `profit_today` | Net profit today | Finance | Every 15-60 min | Orders - COGS - Fees - Ad Spend - Expenses |
| `profit_margin_7d` | 7-day profit margin | Finance | Hourly | Computed |
| `orders_today` | Orders today | Commerce Core | Every 15-60 min | Orders |
| `orders_7d` | Orders last 7 days | Commerce Core | Hourly | Orders |
| `aov_today` | Average order value today | Analytics | Hourly | Orders |
| `units_sold_today` | Units sold today | Commerce Core | Every 15-60 min | OrderItems |
| `active_campaigns` | Count of active campaigns | Advertising | Hourly | Campaigns |
| `ad_spend_today` | Ad spend today | Advertising | Every 1-4h | AdPerformance |
| `roas_today` | Return on ad spend today | Advertising | Every 1-4h | AdPerformance |
| `mer_7d` | Marketing efficiency revenue 7-day | Advertising | Daily | AdSpend / Revenue |
| `inventory_low_stock_count` | Number of SKUs below reorder point | Inventory | Every 1-6h | Inventory |
| `inventory_overstock_count` | Number of SKUs overstocked | Inventory | Every 1-6h | Inventory |
| `pending_shipments` | Orders awaiting shipment | Operations | Hourly | Orders + Shipments |
| `late_shipments` | Shipments past SLA | Operations | Hourly | Shipments |
| `open_returns` | Returns awaiting resolution | Customer Service | Hourly | Returns |
| `open_tickets` | Customer issues open | Customer Service | Hourly | Reviews + Returns |
| `cash_on_hand` | Estimated cash balance | Finance | Daily | Bank + Payouts - Expenses |
| `upcoming_payouts` | Expected incoming payouts | Finance | Daily | Payments |
| `runway_days` | Days of cash at current burn | Finance | Daily | Cashflow model |
| `top_priorities` | List of top 5 priorities | COO Agent | Every workflow | Derived from state |
| `open_actions` | List of open tasks | COO Agent | Every workflow | Tasks |
| `pending_decisions` | List of pending decisions | Decision Engine | Every workflow | Decisions |
| `active_risks` | List of active risks | COO Agent | Every workflow | Risks |
| `supplier_issues` | List of supplier issues | Supplier Agent | Daily | Supplier + PO data |
| `shipping_issues` | List of shipping issues | Operations Agent | Hourly | Shipments |
| `customer_issues` | List of customer issues | Customer Service Agent | Hourly | Reviews + Returns |
| `data_quality_flags` | List of data quality issues | Validation Layer | Every sync | Validation output |
| `last_sync_status` | Per-connector sync status | Connectors | Every sync | Health checks |

### 5.3 Validation Methods

| Field | Validation |
|-------|------------|
| Revenue | Reconciled against sum of paid orders minus discounts/refunds |
| Profit | COGS must be present for all sold items; fees must match platform fee rules |
| Inventory | Marketplace quantity must match internal quantity within tolerance |
| Ad Spend | Cross-check with campaign budget and daily reported spend |
| Cash | Bank/payout data must not conflict with computed revenue minus expenses |
| Orders | Duplicate external_order_ids rejected; status transitions validated |

### 5.4 Consumers

- COO Agent
- Department Agents
- Dashboards
- Notifications
- Reports
- Obsidian (machine-generated summaries)
- Approval Engine
- Automation Engine

### 5.5 Versioning and History

- Each Business State snapshot is immutable and versioned.
- Historical snapshots retained for 90 days for operational queries, 2 years for analytics, then archived.
- Major state changes (e.g., revenue spikes, stockouts) trigger event log entries.

### 5.6 Conflict Resolution

If two sources conflict (e.g., Shopee order total vs. internal computed total):

1. **Flag** the conflict in `data_quality_flags`.
2. **Do not overwrite** the trusted value until resolved.
3. **Prefer platform-reported values** for revenue and fees, internal computation for profit.
4. **Escalate** to Finance Agent if variance exceeds threshold.
5. **Log** the conflict in audit trail and Decision Log.

---

# Part 6 — AI Architecture

## 6.1 Design Philosophy

AI is a **reasoning layer**, not a control layer. AI agents read Business State, read Obsidian knowledge, and produce proposals. They do not execute actions, see secrets, or make irreversible decisions.

## 6.2 AI Layer Components

### 6.2.1 Department Agents

One agent per domain, as defined in Phase 0B:

- Finance Agent
- Inventory Agent
- Growth Agent
- Operations Agent
- Customer Service Agent
- Supplier Agent
- Compliance Agent
- Analytics Agent

Each agent:

- Reads Business State snapshot
- Reads relevant Obsidian SOPs and domain notes
- Proposes actions, risks, or decisions
- Writes to Obsidian domain notes and Decision Log
- Does not execute

### 6.2.2 Commerce Hermes (COO Agent)

The central orchestrator. Its responsibilities:

- Load Business State at start of each workflow
- Query relevant department agents for inputs
- Prioritize issues using scoring model
- Make or escalate decisions based on policy
- Update `Open Actions`, `Risks`, `Pending Decisions`
- Generate morning/midday/evening briefs
- Communicate via Telegram/Obsidian/email
- Never execute directly

### 6.2.3 Shared Memory

Agents do not hold persistent memory. Shared memory is:

1. **Business Database** — operational truth
2. **Business State** — current context snapshot
3. **Obsidian Knowledge** — SOPs, decisions, incidents, lessons
4. **Decision Log** — past choices
5. **Incident Log** — past failures

This prevents memory drift and makes every reasoning traceable.

## 6.3 Knowledge Flow

```
External APIs → Collectors → Validation → Business DB → State Builder → Business State
                                                              │
                                                              ▼
                              Obsidian ←── Agents ←── COO ←── Agents
                                │
                                ▼
                         Decision Log / Incident Log / Reports
```

## 6.4 Escalation

Escalate to human when:

- Confidence < 80%
- Financial impact exceeds threshold
- Action is irreversible
- Policy is silent or ambiguous
- Agents conflict
- Verification fails
- Security/compliance risk

## 6.5 Approval Flow

```
Agent proposes action
    ↓
Decision Engine evaluates against policy
    ↓
If within auto-approve band:
    → Queue for deterministic execution
    → Verify
    → Log
If outside auto-approve band:
    → Create Approval request
    → Notify human
    → Wait for human
    → If approved, execute; if rejected, log reason
```

## 6.6 Failure Handling

| Failure | Handling |
|---------|----------|
| Agent produces no output | COO flags as system incident, retries once, escalates |
| Agent conflicts with another | COO resolves using prioritization model; if unresolved, escalates |
| Agent proposes dangerous action | Policy engine rejects before approval; logged and flagged |
| AI hallucinates data | Deterministic validation layer catches inconsistencies |
| AI context limit exceeded | Business State is constrained; only relevant notes loaded |

## 6.7 Confidence Scoring

Confidence is computed from data quality, not estimated:

| Factor | Weight |
|--------|--------|
| Data completeness | 30% |
| Historical stability | 25% |
| Source freshness | 20% |
| Policy clarity | 15% |
| Cross-validation | 10% |

## 6.8 What AI Must NEVER Do

- Move money
- Directly change prices or budgets without approval
- Issue refunds or returns without policy/human approval
- See or use secrets
- Modify SOPs or policy
- Delete data
- Execute irreversible actions
- Make legal/tax filings
- Override validation failures

---

# Part 7 — Knowledge Architecture

## 7.1 Knowledge Types

| Type | Examples | Owner | Mutable | Format |
|------|----------|-------|---------|--------|
| **Human-written** | Vision, strategy, SOPs, meeting notes, reflections | User | Yes | Free-form markdown |
| **Machine-generated** | Daily reports, executive summaries, KPIs, supplier scorecards | ACOS | No after publish | Markdown + YAML frontmatter |
| **Living documents** | Open actions, risks, pending decisions, inventory status | ACOS | Yes, continuously | Markdown + YAML frontmatter |
| **Read-only references** | SOPs, agent docs, policy, decision log | User/ACOS | Controlled | Markdown |
| **Append-only** | Decision log, incident log, audit trail | ACOS | Append only | Timestamped entries |

## 7.2 Folder Structure (Same as Phase 0B)

- `Company/`
- `SOPs/`
- `Products/`
- `Suppliers/`
- `Finance/`
- `Operations/`
- `Marketing & Growth/`
- `Projects/`
- `Decisions/`
- `Incidents/`
- `Meetings/`
- `Executive/`
- `Agents/`
- `Archive/`

## 7.3 Preventing Knowledge Duplication

- **Single source of truth rules:**
  - Operational truth → Business DB
  - Decisions → Decision Log
  - SOPs → SOPs folder
  - Strategy → Company folder
  - Tasks → Tasks table + Open Actions note
- **Linking convention:** Use `[[Note]]` wiki links to connect related notes.
- **Templates:** Every machine-generated note uses a template with YAML frontmatter.
- **Linting:** Periodically check for orphaned notes, duplicate titles, and broken links.
- **Review cycle:** Quarterly review of knowledge architecture to prune and consolidate.

## 7.4 Knowledge Evolution Over Years

| Year | Focus |
|------|-------|
| 1 | Establish structure, daily reports, decision log, SOPs |
| 2 | Richer product/supplier notes, incident post-mortems, strategy updates |
| 3 | Cross-business knowledge, comparative analytics, platform patterns |
| 4+ | Semantic search, knowledge graph, automated SOP suggestions |

## 7.5 Human vs. Machine Boundaries

- **Humans write:** Strategy, SOPs, meeting notes, creative direction, ethical judgment, high-stakes decisions.
- **Machines write:** Operational reports, status updates, scorecards, proposed actions, routine summaries.
- **Both write:** Product notes, supplier notes, project notes, risk registers.

---

# Part 8 — Automation Maturity Model

## 8.1 Levels

| Level | Name | Definition | Requirements | Examples |
|-------|------|------------|--------------|----------|
| **0** | Manual | Operator does everything by hand. | No automation. | Logging into Shopee Seller Center to check orders. |
| **1** | Monitoring | System collects data and shows dashboards. | Connectors, Business DB, dashboards. | Daily revenue dashboard, stock levels. |
| **2** | Recommendations | System analyzes data and suggests actions. | Analytics, Business State, agents. | “ROAS is dropping; consider reducing budget.” |
| **3** | Approval-based automation | System proposes actions and executes after approval. | Decision Engine, Approval Engine, policy. | “Approve budget increase?” → human taps approve. |
| **4** | Low-risk autonomous execution | System executes low-risk actions within policy. | Policy bands, verification, audit. | Adjust budget by 5% when ROAS is strong. |
| **5** | Fully autonomous operations | System manages routine operations end-to-end with human oversight only for exceptions. | Mature policies, high confidence, human trust. | Auto-reorder stock, auto-optimize ads, auto-detect issues. |

## 8.2 Current State Assessment

Gerard’s system is between **Level 1 and Level 2**:

- ✅ Monitoring: daily reports, dashboards, stock checks
- ⚠️ Recommendations: some ad optimization exists but is dangerous
- ❌ Approval-based automation: missing
- ❌ Low-risk autonomous execution: missing
- ❌ Fully autonomous: missing

## 8.3 Target Maturity by Phase

| Phase | Target Level | Focus |
|-------|--------------|-------|
| 1 | Level 1 solid | Reliable monitoring, clean data, validation |
| 2 | Level 2 | Reliable recommendations and alerts |
| 3 | Level 3 | Approval-based automation for key actions |
| 4 | Level 4 | Low-risk autonomous execution within policy |
| 5 | Level 5 | Fully autonomous operations with exception handling |

## 8.4 Safety Constraint

We will not progress to the next maturity level until:

- Current level is stable for 30 days.
- No P0 or P1 incidents caused by automation.
- Human approval rate is healthy (not too high, not too low).
- Audit trail is complete and reviewed.

---

# Part 9 — Product Roadmap

## 9.1 Phase 1 — Foundations (Months 1-2)

**Objectives:**
- Establish a reliable source of truth.
- Clean up security and technical debt.
- Fix the broken order/income integration.

**Deliverables:**
- Secret vault migration (no secrets in code)
- Canonical Business Database with schema + migrations
- Shopee seller connector working (orders, products, inventory, payments)
- Shopee ads connector working (campaigns, ads, performance)
- Validation and reconciliation layer
- Structured logging and basic observability
- Fix broken cron paths

**Dependencies:**
- Shopee API access and credentials
- Gerard provides real COGS and supplier data
- Decision on hosting (local vs. cloud)

**Exit Criteria:**
- Orders and payments sync reliably.
- Profit calculation matches Gerard’s manual checks.
- No secrets in code.
- System health dashboard shows all green.

**Why this phase exists:** Without reliable data and secure foundations, everything built on top is wrong or dangerous.

---

## 9.2 Phase 2 — Reliable Commerce OS (Months 3-4)

**Objectives:**
- Make the system a reliable daily operating tool.
- Replace current scripts with module-based automation.
- Build the Business State.

**Deliverables:**
- Commerce Core module (orders, products, inventory, customers, shipments)
- Finance module (P&L, cashflow, expenses)
- Inventory module (reorder points, alerts)
- Advertising module (campaign tracking, performance)
- Business State builder and snapshot
- Daily/weekly/monthly reports in Obsidian
- Morning/midday/evening Telegram briefs
- Task and notification system

**Dependencies:**
- Phase 1 complete
- Gerard adopts Obsidian structure
- Notification preferences defined

**Exit Criteria:**
- Gerard can stop checking Seller Center manually.
- Morning brief is accurate and actionable.
- Reports match Business State.

**Why this phase exists:** The product must first be a reliable tool before it can be an intelligent assistant.

---

## 9.3 Phase 3 — Operational Intelligence (Months 5-6)

**Objectives:**
- Add analytics, anomaly detection, and recommendations.
- Introduce the Decision Engine and Approval Engine.

**Deliverables:**
- Analytics module (trends, forecasting, anomaly detection)
- KPI tracking and targets
- Department agents (Finance, Inventory, Growth, Ops, Customer)
- Decision Engine with confidence scoring
- Approval Engine with policy config
- Decision Log and Open Actions in Obsidian
- Proposals instead of direct actions for ad optimizer

**Dependencies:**
- Phase 2 complete
- Policies defined (budget bands, price floors, approval thresholds)
- Agent SOPs documented

**Exit Criteria:**
- Agents produce useful proposals daily.
- No autonomous budget changes without approval.
- Gerard approves/rejects decisions easily via Telegram.

**Why this phase exists:** Intelligence without control creates risk. This phase adds the control layer.

---

## 9.4 Phase 4 — Commerce AI (Months 7-9)

**Objectives:**
- Make the AI layer a true COO assistant.
- Add safe autonomous execution for low-risk actions.

**Deliverables:**
- Commerce Hermes COO agent with daily workflows
- Prioritization model and executive briefs
- Low-risk automation (e.g., budget tweaks within policy, status checks)
- Supplier performance scorecards and PO proposals
- Customer service response drafts and return triage
- Advanced analytics (cohorts, LTV, demand forecasting)

**Dependencies:**
- Phase 3 complete
- Gerard trusts agent proposals
- Verification loops working

**Exit Criteria:**
- COO briefs reduce Gerard’s daily cognitive load.
- Low-risk automation runs safely for 30 days without incident.
- Human approval rate is between 20-40%.

**Why this phase exists:** This is the product’s core differentiation — AI-assisted operations, not just reporting.

---

## 9.5 Phase 5 — Multi-Store (Months 10-12)

**Objectives:**
- Support multiple stores under one organization.
- Prepare for multi-business without redesign.

**Deliverables:**
- Multi-store dashboard and reporting
- Cross-store inventory and product management
- Consolidated P&L and cashflow
- Business-level organization
- User roles and permissions

**Dependencies:**
- Phase 4 complete
- Gerard has or plans a second store

**Exit Criteria:**
- Gerard can add a second store without engineering help.
- Consolidated reporting works accurately.

**Why this phase exists:** Gerard’s growth will likely require multiple stores; the architecture must support it natively.

---

## 9.6 Phase 6 — Multi-Marketplace (Months 13-15)

**Objectives:**
- Add support for Lazada, Tokopedia, and/or TikTok Shop.

**Deliverables:**
- Lazada connector
- Tokopedia connector
- TikTok Shop connector
- Cross-marketplace inventory and order management
- Cross-marketplace ad and financial reporting

**Dependencies:**
- Phase 5 complete
- Marketplace API access and sandbox accounts

**Exit Criteria:**
- New marketplace connected in < 1 week of development.
- Cross-marketplace reports are accurate.

**Why this phase exists:** Platform diversification is a natural growth path for Southeast Asian ecommerce.

---

## 9.7 Phase 7 — Platform (Months 16-20)

**Objectives:**
- Turn the internal system into a multi-organization platform.
- Add multi-tenancy, billing, onboarding, and support.

**Deliverables:**
- Multi-tenant architecture
- Organization isolation
- Admin dashboard
- Subscription billing
- Customer onboarding flow
- API for third-party integrations
- White-label options

**Dependencies:**
- Phase 6 complete
- Product-market fit evidence from Gerard and early users
- Cloud infrastructure and compliance readiness

**Exit Criteria:**
- New organization can sign up and connect a store without manual engineering.
- Billing and support processes defined.

**Why this phase exists:** This is the SaaS evolution. It only makes sense after the product is proven.

---

## 9.8 Phase 8 — SaaS (Months 21+)

**Objectives:**
- Scale the SaaS platform.

**Deliverables:**
- Scalable infrastructure
- Advanced analytics and AI features
- Marketplace/app ecosystem
- Enterprise features (teams, compliance, custom reports)
- Regional expansion

**Dependencies:**
- Phase 7 complete
- Funding or revenue to support SaaS operations

**Exit Criteria:**
- Sustainable unit economics.
- Net revenue retention > 100%.

**Why this phase exists:** Long-term commercialization of the platform.

---

# Part 10 — Critique

## 10.1 Weaknesses

1. **Complexity vs. stage mismatch.** A multi-tenant, multi-platform architecture is heavy for one Shopee shop. The risk is building infrastructure before it is needed.
2. **Knowledge discipline required.** Obsidian only works if Gerard maintains templates and links. If not, it becomes another messy folder.
3. **AI reliability at scale.** Proposals are only as good as the data. If income API remains unreliable, Finance and COO agents will be wrong.
4. **Approval friction.** Approval-based automation may feel slower than Gerard wants, especially for fast-moving ad optimization.
5. **Connector maintenance burden.** Every marketplace API change requires connector updates. This is ongoing operational work.
6. **Security model is not trivial.** Secret vault, access control, audit logging, and backups add overhead.

## 10.2 Trade-offs

| Trade-off | Chosen | Sacrificed |
|-----------|--------|------------|
| Safety vs. speed | Safety | Slower automation |
| Abstraction vs. simplicity | Abstraction | Higher initial complexity |
| Multi-tenant ready vs. single-tenant | Tenant-aware from start | Some unused fields and modules early |
| Human-in-the-loop vs. full autonomy | Human-in-the-loop | Less magical automation |
| Obsidian vs. structured DB | Hybrid | Neither is perfect for both humans and machines |

## 10.3 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Marketplace API changes break connectors | High | High | Versioned connectors, abstraction layer, monitoring |
| Data quality issues corrupt Business State | Medium | High | Validation layer, reconciliation, anomaly detection |
| Scalability assumptions fail | Medium | Medium | Start with SQLite/Postgres, measure before scaling |
| AI agent conflicts or noise | Medium | Medium | Strong COO, confidence scoring, escalation rules |
| Secret management failures | Low | Critical | Vault, rotation, audit, no secrets in code |
| Migration from scripts to modules stalls | Medium | High | Gradual replacement, keep old scripts running |

## 10.4 Business Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Gerard loses interest or capacity during long build | Medium | High | Deliver visible value every 2-4 weeks |
| Product-market fit for SaaS is unproven | High | High | Validate with Gerard as Customer #1 before building SaaS |
| Competitors (BigSeller, CiciKelola) add similar AI features | Medium | High | Differentiate on profit-first reasoning and safety |
| Pricing model unclear | Medium | Medium | Test willingness to pay with early users |
| Compliance/regulatory complexity in Indonesia | Medium | High | Compliance Agent, tax integrations, local expertise |

## 10.5 Unknowns

1. What is Gerard’s actual monthly GMV and order volume?
2. How many SKUs and suppliers are there?
3. What is the real cost structure (COGS, packaging, shipping, fees)?
4. Does Gerard have appetite for a 12-20 month roadmap, or does he want a faster fix?
5. What is the budget for cloud infrastructure and engineering?
6. Are there other stakeholders (accountant, VA, partner) who will use the system?
7. What is the exact competitive landscape Gerard cares about?

## 10.6 Intentionally Postponed

- **Mobile app:** Not needed until SaaS phase.
- **White-label:** Not needed until platform phase.
- **Advanced ML forecasting:** Analytics first, ML later.
- **Bank integrations:** Manual expense entry first; bank feeds later.
- **Marketplace listing management:** Order/ads/inventory first; listing creation later.
- **Customer chatbot:** Response drafts first; autonomous chat later.

## 10.7 Likely to Change

- Exact entity fields as new marketplaces and business models are added.
- Maturity level progression speed based on trust and stability.
- Specific connectors and features prioritized based on Gerard’s immediate pain.
- AI agent boundaries as the system matures and trust grows.

---

# Final Question: Is This Document Sufficient?

**Question:** If I hired five senior engineers tomorrow with no prior knowledge of this project, would this document be sufficient for them to understand the product, the architecture, and the long-term direction without asking fundamental questions?

**Answer:** No. It is strong on direction and domain, but several practical questions remain unresolved:

1. **Exact hosting and infrastructure stack:** Local macOS? Render? AWS? This determines cost, scalability, and deployment approach.
2. **Real transaction volume and SKU count:** Needed for database sizing and performance assumptions.
3. **Authentication and user model:** Will Gerard be the only user for months, or do we need multi-user from day one?
4. **Budget and timeline constraints:** Is this a 6-month sprint or a 2-year build?
5. **API specifics and limitations:** Shopee API version, rate limits, webhook availability, sandbox access for other marketplaces.
6. **Obsidian integration mechanism:** File sync, git, or a future API/MCP? How will ACOS write to Obsidian reliably?
7. **Notification channels and preferences:** Telegram only? Email? SMS? Who gets alerted for what?
8. **Policy defaults:** Exact thresholds for auto-approve vs. human approval (e.g., budget change %, price change %).
9. **Compliance and tax requirements:** Indonesian tax invoicing, e-filing, platform reporting obligations.
10. **Team and execution model:** Will engineers build from scratch, or wrap existing scripts? What is the testing/QA process?

These are not flaws in the architecture. They are the **natural next questions** before implementation begins. They should be answered in the **Phase 1 planning document** or **technical specification**, not in this product architecture.

---

# Status

**Phase 0C Product Architecture is complete and proposed.**

**No implementation has occurred.**

**Awaiting Gerard’s approval, challenges, or adjustments before Phase 1.**
