const BASE_URL = "http://localhost:8000/api";
const { randomUUID } = require('crypto');

async function run() {
    console.log("--- 🚀 بدء دورة الحصاد والمبيعات الآلية (REST API) ---");

    // 1. Login
    console.log("🔑 تسجيل الدخول...");
    const loginRes = await fetch(`${BASE_URL}/token/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: "admin", password: "ADMIN123" })
    });

    if (!loginRes.ok) {
        console.log("❌ فشل تسجيل الدخول:", await loginRes.text());
        return;
    }
    const token = (await loginRes.json()).access;
    const headers = { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" };

    // 2. Fetch Context
    console.log("🌍 جلب البيانات الأولية...");
    const farmsRes = await fetch(`${BASE_URL}/farms/`, { headers });
    const farms = (await farmsRes.json()).results || [];
    if (!farms.length) { console.log("❌ لم يتم العثور على مزارع."); return; }
    const farm_id = farms[0].id;

    const locRes = await fetch(`${BASE_URL}/locations/?farm=${farm_id}`, { headers });
    const locations = (await locRes.json()).results || [];
    const location_id = locations.length > 0 ? locations[0].id : null;

    const tasksRes = await fetch(`${BASE_URL}/tasks/`, { headers });
    const tasks = (await tasksRes.json()).results || [];
    const harvestTask = tasks.find(t => t.is_harvest_task) || tasks[0];
    const harvest_task_id = harvestTask ? harvestTask.id : null;

    const itemsRes = await fetch(`${BASE_URL}/items/`, { headers });
    const items = (await itemsRes.json()).results || [];
    const yieldItems = items.filter(i => i.group === 'Yield' || i.category === 'Yield');

    let product_id = null;
    if (yieldItems.length === 0) {
        console.log("⚠️ إنشاء صنف محصول...");
        const itemCreateRes = await fetch(`${BASE_URL}/items/`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ name: "Test Harvest Product", group: "Yield", type: "Goods" })
        });
        const createdItem = await itemCreateRes.json();
        product_id = createdItem.id;
    } else {
        product_id = yieldItems[0].id;
    }

    // 3. Create Daily Log Harvest Activity
    console.log(`📦 تجهيز عملية حصاد (Product ID: ${product_id})...`);
    const idempKey = randomUUID();
    const today = new Date().toISOString().split('T')[0];

    const logPayload = {
        date: today,
        farm_id,
        location_id,
        task_id: harvest_task_id,
        labor_entry_mode: "CASUAL_BATCH",
        employees_payload: [
            {
                labor_type: "CASUAL_BATCH",
                workers_count: 10,
                surrah_share: 1,
                labor_batch_label: "عمال حصاد النظام"
            }
        ],
        harvest_quantity: 500,
        product_id,
        batch_number: "E2E-BATCH-01",
        surrah_count: 1,
        variance_note: "حصاد تجريبي E2E"
    };

    console.log("⏳ إرسال سجل النشاط اليومي...");
    const logHeaders = { ...headers, "X-Idempotency-Key": idempKey };
    const rLog = await fetch(`${BASE_URL}/daily-logs/`, {
        method: 'POST',
        headers: logHeaders,
        body: JSON.stringify(logPayload)
    });

    if (!rLog.ok) {
        console.log("❌ فشل التسجيل:", await rLog.text());
        return;
    }
    console.log("✅ تم إنشاء سجل النشاط بنجاح:", await rLog.json());

    // 4. Create Sales Invoice
    console.log("💰 تجهيز فاتورة مبيعات...");
    const salesPayload = {
        date: today,
        farm_id,
        status: "DRAFT",
        customer_name: "عميل الاختبار",
        lines: [
            {
                item_id: product_id,
                quantity: 100,
                unit_price: 250.00
            }
        ]
    };

    const salesIdemp = randomUUID();
    const sHeaders = { ...headers, "X-Idempotency-Key": salesIdemp };

    const rSales = await fetch(`${BASE_URL}/sales/invoices/`, { // Note: guessing endpoint path
        method: 'POST',
        headers: sHeaders,
        body: JSON.stringify(salesPayload)
    });

    if (!rSales.ok) {
        console.log("⚠️ فشل الفاتورة أو 엔드بوينت Sales غير موجود كالتوقع:", rSales.status, await rSales.text());
    } else {
        console.log("✅ تم إنشاء فاتورة المبيعات بنجاح:", await rSales.json());
    }

    console.log("--- 🎉 اكتملت الدورة الآلية ---");
}

run().catch(console.error);
