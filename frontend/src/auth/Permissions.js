import { Farms } from '../api/client';

// دالة للتحقق من صلاحيات المستخدم وجلب المزارع المرتبطة به
export async function getUserFarms() {
  try {
    // في تطبيق حقيقي، يجب جلب هذه البيانات من سياق المصادقة أو نقطة نهاية API خاصة
    const { data } = await Farms.list();
    return data.results || data;
  } catch (error) {
    console.error('Error fetching user farms:', error);
    return [];
  }
}

// دالة للتحقق مما إذا كان المستخدم لديه صلاحية الوصول إلى مزرعة معينة
export async function hasFarmAccess(farmId, userFarms) {
  // إذا كانت userFarms غير محددة، قم بجلبها
  if (!userFarms) {
    userFarms = await getUserFarms();
  }

  // تحقق مما إذا كان المستخدم لديه صلاحية الوصول إلى المزرعة
  return userFarms.some(farm => farm.id === parseInt(farmId));
}

// دالة للحصول على معرفات المزارع التي يصل إليها المستخدم
export async function getUserFarmIds() {
  const farms = await getUserFarms();
  return farms.map(farm => farm.id);
}

// دالة لإضافة فلتر المزرعة إلى معاملات API
export async function addFarmFilter(params = {}) {
  const farmIds = await getUserFarmIds();

  // إذا لم يكن هناك فلتر farm_id مسبق، أضف فلتر المزارع المتاحة للمستخدم
  if (!params.farm_id && farmIds.length > 0) {
    return { ...params, farm_id: farmIds.join(',') };
  }

  return params;
}
