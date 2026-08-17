# ⚡ IR-RUSE Subscription Collector

> **Automatic V2Ray Subscription**
>
> جمع‌آوری خودکار کانفیگ‌ها از منابع مختلف و ارائه آن‌ها در قالب یک Subscription واحد.
یک سیستم ساده برای کسانی که نمی‌خواهند هر بار کانفیگ‌ها را از چندین منبع پیدا، کپی و دستی وارد کلاینت کنند.

---

## 🌐 Subscription | اشتراک

### 🔗 لینک اصلی

```text
https://raw.githubusercontent.com/KhodeJav/ir-ruse-sub/main/output/subscription.txt
```

> لینک بالا را در کلاینت خود اضافه کنید و فقط Subscription را Update کنید.

---

## ✨ Features | امکانات

* 📢 دریافت کانفیگ از کانال‌های Telegram
* 🔗 دریافت از Subscription URL
* ⚡ پشتیبانی از VLESS، VMess، Trojan، Shadowsocks و SSR
* 🔐 تشخیص Base64
* 🧩 استخراج کانفیگ از متن، Code، Mono و Quote
* ♻️ حذف کانفیگ‌های تکراری
* 🧹 حذف خودکار کانفیگ‌های قدیمی
* 🤖 بروزرسانی خودکار با GitHub Actions
* 🖥️ بدون نیاز به VPS
* 🔗 یک لینک Subscription برای استفاده در کلاینت

---

## 🎯 Why IR-RUSE? | چرا IR-RUSE؟

بجای اینکه هر روز:

```text
Telegram 1 → Copy
Telegram 2 → Copy
Telegram 3 → Copy
       ↓
Paste everything manually
       ↓
Update client
```

فقط یک Subscription داشته باشید:

```text
Sources
   ↓
IR-RUSE
   ↓
Collect
   ↓
Extract
   ↓
Clean
   ↓
Publish
   ↓
Your Client
```

---

## 📱 How to Use | نحوه استفاده

### 1. لینک Subscription را کپی کنید

```text
https://raw.githubusercontent.com/KhodeJav/ir-ruse-sub/main/output/subscription.txt
```

### 2. در کلاینت خود وارد بخش Subscription شوید

ممکن است نام این بخش در کلاینت‌های مختلف متفاوت باشد:

```text
Subscription
Remote Subscription
Subscription Groups
Import from URL
```

### 3. لینک را اضافه کنید

```text
┌─────────────────────────────────────────────┐
│ Subscription URL                            │
├─────────────────────────────────────────────┤
│ https://raw.githubusercontent.com/...       │
│ output/subscription.txt                     │
└─────────────────────────────────────────────┘
```

### 4. روی Update بزنید

تمام.

> بعد از اضافه کردن لینک، دیگر لازم نیست کانفیگ‌ها را یکی‌یکی کپی کنید.

---

## 🔄 How It Works | نحوه عملکرد

### Telegram

در اولین اجرای هر کانال:

```text
Channel
   ↓
Last 20 Messages
   ↓
Extract Configs
   ↓
Save
```

بعد از آن، سیستم فقط **آخرین پیام کانال** را بررسی می‌کند.

```text
Last Message ID
       ↓
Check Latest Message
       ↓
 ┌─────┴─────┐
 │           │
Same ID    New ID
 │           │
 ▼           ▼
Nothing    Extract
to do      Configs
```

بنابراین قرار نیست در هر اجرا کل تاریخچه کانال دوباره خوانده شود.

---

## 📦 Sources | منابع

منابع را می‌توان از دو نوع استفاده کرد:

### Telegram

```text
@channel
https://t.me/channel
```

### Subscription

```text
https://example.com/subscription.txt
```

---

## 🧠 Config Extraction | استخراج کانفیگ

IR-RUSE کانفیگ‌های رایج را شناسایی می‌کند:

```text
vless://...
vmess://...
trojan://...
ss://...
ssr://...
socks://...
socks5://...
```

همچنین تلاش می‌کند کانفیگ‌های موجود در:

```text
Normal Text
Code
Monospace
Quote
Base64
```

را استخراج کند.

---

## ♻️ Duplicate Removal | حذف تکراری‌ها

اگر یک کانفیگ از چند منبع مختلف دریافت شود، فقط یک نسخه از آن نگه داشته می‌شود.

```text
Source A ──┐
Source B ──┼──► Same Config ──► One Copy
Source C ──┘
```

---

## 🧹 Expiration | حذف قدیمی‌ها

برای جلوگیری از باقی ماندن کانفیگ‌های قدیمی، کانفیگ‌ها پس از:

```text
48 Hours
```

به‌صورت خودکار حذف می‌شوند.

```text
New Config
    ↓
   48h
    ↓
Remove
```

---

## 🤖 Automatic Update | بروزرسانی خودکار

پروژه با GitHub Actions به‌صورت خودکار اجرا می‌شود.

زمان‌بندی فعلی:

```text
XX:07
XX:37
```

یعنی تقریباً هر ۳۰ دقیقه.

> GitHub ممکن است اجرای Scheduled Workflow را در شرایط شلوغ با کمی تأخیر انجام دهد.

---

## 🖥️ No VPS

برای اجرای پروژه به VPS یا سرور دائمی نیاز نیست.

```text
❌ VPS
❌ Server
❌ Manual Run

        ↓

✅ GitHub Actions
```

---

## 📂 Output | خروجی

```text
output/
├── subscription.txt
└── configs.txt
```

### `subscription.txt`

خروجی Subscription برای استفاده در کلاینت‌ها.

### `configs.txt`

نسخه قابل مشاهده کانفیگ‌های استخراج‌شده.

---

## 🏷️ Remark

برای مرتب بودن نام کانفیگ‌ها، Remark خروجی به این شکل تنظیم می‌شود:

```text
Telegram @iR_RUSE
```

قسمت اصلی URI کانفیگ نباید تغییر کند و فقط نام نمایشی انتهای لینک تغییر می‌کند.

---

## ⚠️ Important | نکته مهم

IR-RUSE **سرویس تست سلامت سرورها نیست**.

یعنی:

```text
Config extracted
       ≠
Server is guaranteed online
```

ممکن است یک کانفیگ با موفقیت استخراج شود اما سرور آن در همان لحظه فعال نباشد.

هدف پروژه:

```text
Collect
→ Extract
→ Manage
→ Publish
```

است.

---

## 👤 Who Is It For? | مناسب چه کسانی است؟

### ✅ مناسب برای

* کسانی که چند منبع کانفیگ دارند
* کسانی که کانفیگ جدید زیاد دریافت می‌کنند
* مدیران کانال‌ها و صفحات پروکسی
* کسانی که یک Subscription ثابت می‌خواهند
* کسانی که نمی‌خواهند کانفیگ‌ها را دستی کپی کنند

### ❌ ضروری نیست برای

* کسی که فقط یک یا دو کانفیگ دارد
* کسی که همه کانفیگ‌ها را دستی مدیریت می‌کند

---

## 🗺️ Roadmap | مسیر توسعه

* [x] Telegram Collector
* [x] Subscription Collector
* [x] Config Extraction
* [x] Base64 Detection
* [x] Duplicate Removal
* [x] Expiration System
* [x] Automatic GitHub Actions
* [x] Subscription Output
* [ ] Advanced Filtering
* [ ] More Source Types
* [ ] Better Extraction Rules

---

# 🇬🇧 English

## ⚡ What is IR-RUSE?

**IR-RUSE** is an automatic V2Ray subscription collector.

It collects configurations from different sources, extracts them, removes duplicates and publishes them through one subscription URL.

```text
Sources
   ↓
Collect
   ↓
Extract
   ↓
Clean
   ↓
Publish
   ↓
Your Client
```

---

## 🔗 Subscription URL

```text
https://raw.githubusercontent.com/KhodeJav/ir-ruse-sub/main/output/subscription.txt
```

Add this URL to any client that supports remote subscriptions.

---

## ✨ Features

* Telegram source support
* Subscription URL support
* VLESS / VMess / Trojan
* Shadowsocks / SSR
* Base64 detection
* Text / Code / Monospace / Quote extraction
* Duplicate removal
* Automatic expiration
* Automatic GitHub Actions updates
* No VPS required
* One subscription URL

---

## 🚀 How to Use

### Step 1

Copy the subscription URL:

```text
https://raw.githubusercontent.com/KhodeJav/ir-ruse-sub/main/output/subscription.txt
```

### Step 2

Open your client and find:

```text
Subscription
Remote Subscription
Subscription Groups
Import from URL
```

### Step 3

Paste the URL.

### Step 4

Press **Update**.

Done.

---

## 🔄 Automatic Updates

GitHub Actions runs the collector automatically.

Current schedule:

```text
XX:07
XX:37

≈ Every 30 Minutes
```

The first Telegram scan checks only the last **20 messages**.

Later runs check only the **latest message**.

---

## 📦 Supported Sources

### Telegram

```text
@channel
https://t.me/channel
```

### Subscription URL

```text
https://example.com/subscription.txt
```

---

## 🧠 Config Extraction

The project detects common configuration formats:

```text
vless://...
vmess://...
trojan://...
ss://...
ssr://...
socks://...
socks5://...
```

It can also extract configs from:

```text
Normal Text
Code
Monospace
Quote
Base64
```

---

## ♻️ Duplicate Removal

If the same configuration comes from multiple sources, only one copy is kept.

```text
Source A ──┐
Source B ──┼──► One Config
Source C ──┘
```

---

## 🧹 Old Config Cleanup

Configurations expire after:

```text
48 Hours
```

This keeps the subscription fresh and prevents unlimited growth.

---

## 🤖 No VPS Required

The project runs through GitHub Actions.

```text
No VPS
   ↓
No Server
   ↓
No Manual Execution
   ↓
GitHub Actions
```

---

## ⚠️ Important

IR-RUSE does **not** verify server availability.

A successfully extracted configuration does not mean the server is guaranteed to be online.

The project focuses on:

```text
Collect
→ Extract
→ Manage
→ Publish
```

---

## 👤 Who Is It For?

IR-RUSE is useful for people who:

* use multiple configuration sources
* receive new configs frequently
* want one subscription URL
* do not want to manually copy configs
* want automatic updates

---

## 🗺️ Roadmap

* [x] Telegram Collector
* [x] Subscription Collector
* [x] Config Extraction
* [x] Base64 Detection
* [x] Duplicate Removal
* [x] Expiration System
* [x] Automatic Updates
* [x] Subscription Output
* [ ] Advanced Filtering
* [ ] More Source Types
* [ ] Better Extraction Rules

---

## ⭐ Support

If you find IR-RUSE useful, consider giving the repository a ⭐.

It helps the project grow.

---

<div align="center">

### ⚡ IR-RUSE

**Collect · Extract · Update · Subscribe**

Telegram: **@iR_RUSE**

</div>

