export const getAvailableVarietiesForLocation = (locationId, farmContext) => {
    // 1. حماية ضد القيم الفارغة
    if (!locationId || !farmContext) return [];

    let availableVarieties = [];

    // 2. مسار المحاصيل الموسمية (Crop Plans)
    if (farmContext.cropPlans && Array.isArray(farmContext.cropPlans)) {
        const activePlans = farmContext.cropPlans.filter(
            plan => (plan?.location_id === locationId || plan?.location === locationId) && 
                    plan?.status === 'ACTIVE'
        );
        
        activePlans.forEach(plan => {
            const v = plan?.crop_variety || plan?.variety;
            if (v) availableVarieties.push(v);
        });
    }

    // 3. مسار الأشجار المعمرة (Tree Inventory) - دعم كافة مسميات الـ API المحتملة
    const treeInventory = farmContext.locationTreeStocks || farmContext.treeStocks || farmContext.tree_census || farmContext.trees || [];
    
    if (Array.isArray(treeInventory)) {
        const strLocationId = String(locationId)
        const locationTrees = treeInventory.filter(stock => {
            // دعم كلٍّ من location_id (مفرد) و location_ids (جمع - من treeVarietySummary البطاقة الذكية)
            const inSingle =
                String(stock?.location_id) === strLocationId ||
                String(stock?.location) === strLocationId
            const inArray =
                Array.isArray(stock?.location_ids) &&
                stock.location_ids.map(String).includes(strLocationId)
            if (!inSingle && !inArray) return false

            // دعم كافة حقول العدد المحتملة (current_tree_count_total من locationVarietySummary)
            // [FIX]: إضافة cohort_alive_total كمسار بديل — الأصناف التي لم تُزامن في LocationTreeStock
            // لكنها موجودة في BiologicalAssetCohort يجب ألا تُستبعد من القائمة المنسدلة
            const count =
                stock?.current_tree_count_total ??
                stock?.current_tree_count ??
                stock?.number_of_trees ??
                stock?.quantity ??
                0
            const cohortAlive = stock?.cohort_alive_total ?? 0
            return Number(count) > 0 || Number(cohortAlive) > 0
        });

        locationTrees.forEach(stock => {
            // دعم كافة أسماء حقول الأصناف المحتملة في الجرد
            let v = stock?.crop_variety || stock?.variety || stock?.tree_variety;
            
            // معالجة حالة treeVarietySummary التي تحمل variety_id + variety_name بدلاً من كائن صنف كامل
            if (!v && stock?.variety_id) {
                // أولاً: جرّب إيجاد الكائن الكامل في lookups.varieties
                if (Array.isArray(farmContext.varieties)) {
                    v = farmContext.varieties.find(variety => String(variety?.id) === String(stock.variety_id))
                }
                // ثانياً: إذا لم يُوجد، أنشئ كائناً بسيطاً من variety_id + variety_name
                if (!v) {
                    v = { id: stock.variety_id, name: stock.variety_name || `الصنف ${stock.variety_id}` }
                }
            }
            
            // 🚨 معالجة حرجة: إذا كان الصنف مجرد ID (رقم أو نص)، نقوم بجلبه من قائمة الأصناف العامة
            if ((typeof v === 'number' || typeof v === 'string') && Array.isArray(farmContext.varieties)) {
                v = farmContext.varieties.find(variety => variety?.id === Number(v));
            }
            
            if (v) availableVarieties.push(v);
        });
    }

    // 4. الفلترة الصارمة وإزالة التكرار (Strict Deduplication)
    const uniqueIds = new Set();
    return availableVarieties.filter(v => {
        // إذا لم يكن هناك كائن صنف أو ليس له ID صحيح، يتم تجاهله
        if (!v || !v.id) return false; 
        
        // إذا تم إضافة الصنف مسبقاً للقائمة، يتم تجاهله لمنع التكرار
        if (uniqueIds.has(v.id)) return false; 
        
        uniqueIds.add(v.id);
        return true;
    });
};
