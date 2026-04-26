const DB_NAME = 'SaradudAgriDB';
const DB_VERSION = 2;
let dbInstance = null;

const DEFAULT_SERVICE_SCOPE = 'general';
const normaliseServiceScopeValue = (value, fallback = DEFAULT_SERVICE_SCOPE) => {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (trimmed) {
      return trimmed;
    }
  }
  return fallback;
};

const normaliseServiceCountEntry = (entry) => {
  if (!entry || typeof entry !== 'object') {
    return { entry, changed: false };
  }
  const normalized = { ...entry };
  let changed = false;
  const scope = normaliseServiceScopeValue(
    entry.service_scope,
    normaliseServiceScopeValue(entry.service_type, DEFAULT_SERVICE_SCOPE),
  );
  if (normalized.service_scope !== scope) {
    normalized.service_scope = scope;
    changed = true;
  }
  const currentType = typeof normalized.service_type === 'string' ? normalized.service_type.trim() : '';
  if (!currentType) {
    normalized.service_type = scope;
    changed = true;
  }
  return { entry: normalized, changed };
};

const normaliseServiceCountsList = (list) => {
  if (!Array.isArray(list)) {
    return { list, changed: false };
  }
  let changed = false;
  const normalized = list.map((item) => {
    const { entry, changed: entryChanged } = normaliseServiceCountEntry(item);
    if (entryChanged) {
      changed = true;
    }
    return entry;
  });
  return { list: normalized, changed };
};

// فتح قاعدة البيانات
export const initDB = async () => {
  return new Promise((resolve, reject) => {
    if (dbInstance) {
      resolve(dbInstance);
      return;
    }

    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = (event) => {
      console.error('Database error:', event.target.error);
      reject(event.target.error);
    };

    request.onsuccess = (event) => {
      dbInstance = event.target.result;
      resolve(dbInstance);
    };

    request.onupgradeneeded = (event) => {
      const db = event.target.result;

      // إنشاء مخازن البيانات إذا لم تكن موجودة
      if (!db.objectStoreNames.contains('static')) {
        db.createObjectStore('static', { keyPath: 'key' });
      }

      if (!db.objectStoreNames.contains('userData')) {
        db.createObjectStore('userData', { keyPath: 'key' });
      }

      if (!db.objectStoreNames.contains('unsynced')) {
        const unsyncedStore = db.createObjectStore('unsynced', { 
          keyPath: 'id', 
          autoIncrement: true 
        });
        // إنشاء فهرس للنوع لتسهيل البحث
        unsyncedStore.createIndex('type', 'type', { unique: false });
      }

      if (!db.objectStoreNames.contains('dailyLogs')) {
        const dailyLogsStore = db.createObjectStore('dailyLogs', { 
          keyPath: ['date', 'farmId'],
        });
        // إنشاء فهارس للتسهيل البحث
        dailyLogsStore.createIndex('date', 'date', { unique: false });
        dailyLogsStore.createIndex('farmId', 'farmId', { unique: false });
      }

      if (!db.objectStoreNames.contains('activities')) {
        const activitiesStore = db.createObjectStore('activities', { 
          keyPath: 'id', 
          autoIncrement: true 
        });
        // إنشاء فهارس للتسهيل البحث
        activitiesStore.createIndex('date', 'date', { unique: false });
        activitiesStore.createIndex('farmId', 'farmId', { unique: false });
        activitiesStore.createIndex('syncStatus', 'syncStatus', { unique: false });
      }

      if (event.oldVersion < 2 && db.objectStoreNames.contains('dailyLogs')) {
        const upgradeTransaction = event.target.transaction;
        if (upgradeTransaction) {
          const dailyLogsStore = upgradeTransaction.objectStore('dailyLogs');
          const requestAll = dailyLogsStore.getAll();
          requestAll.onsuccess = () => {
            const records = Array.isArray(requestAll.result) ? requestAll.result : [];
            records.forEach((record) => {
              if (!record || typeof record !== 'object' || !record.data || typeof record.data !== 'object') {
                return;
              }
              const nextRecord = { ...record };
              const nextData = { ...record.data };
              let mutated = false;

              const { list: normalizedCounts, changed: countsChanged } = normaliseServiceCountsList(nextData.serviceCounts);
              if (countsChanged) {
                nextData.serviceCounts = normalizedCounts;
                mutated = true;
              }

              if (Array.isArray(nextData.service_counts)) {
                const { list: legacyCounts, changed: legacyChanged } = normaliseServiceCountsList(nextData.service_counts);
                if (legacyChanged) {
                  nextData.service_counts = legacyCounts;
                  mutated = true;
                }
              }

              if (mutated) {
                nextRecord.data = nextData;
                dailyLogsStore.put(nextRecord);
              }
            });
          };
        }
      }
    };
  });
};

// دالة مساعدة للتعامل مع قاعدة البيانات
const withDB = async (callback) => {
  const db = await initDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['static', 'userData', 'unsynced', 'dailyLogs', 'activities'], 'readwrite');
    const result = callback(transaction);

    transaction.oncomplete = () => {
      resolve(result);
    };

    transaction.onerror = (event) => {
      reject(event.target.error);
    };
  });
};

// حفظ البيانات الثابتة
export const saveStaticData = async (key, data) => {
  return new Promise((resolve, reject) => {
    withDB((transaction) => {
      const store = transaction.objectStore('static');
      const request = store.put({ key, data, timestamp: Date.now() });

      request.onsuccess = () => {
        resolve(request.result);
      };

      request.onerror = () => {
        reject(request.error);
      };

      return request.result;
    }).catch(reject);
  });
};

// جلب البيانات الثابتة
export const getStaticData = async (key) => {
  return new Promise((resolve, reject) => {
    withDB((transaction) => {
      const store = transaction.objectStore('static');
      const request = store.get(key);

      request.onsuccess = () => {
        resolve(request.result ? request.result.data : null);
      };

      request.onerror = () => {
        reject(request.error);
      };

      return request.result;
    }).catch(reject);
  });
};

// حفظ بيانات المستخدم
export const saveUserData = async (key, data) => {
  return new Promise((resolve, reject) => {
    withDB((transaction) => {
      const store = transaction.objectStore('userData');
      const request = store.put({ key, data, timestamp: Date.now() });

      request.onsuccess = () => {
        resolve(request.result);
      };

      request.onerror = () => {
        reject(request.error);
      };

      return request.result;
    }).catch(reject);
  });
};

// جلب بيانات المستخدم
export const getUserData = async (key) => {
  return new Promise((resolve, reject) => {
    withDB((transaction) => {
      const store = transaction.objectStore('userData');
      const request = store.get(key);

      request.onsuccess = () => {
        resolve(request.result ? request.result.data : null);
      };

      request.onerror = () => {
        reject(request.error);
      };

      return request.result;
    }).catch(reject);
  });
};

// إضافة بيانات غير مزامنة
export const addUnsyncedData = async (type, data) => {
  return new Promise((resolve, reject) => {
    withDB((transaction) => {
      const store = transaction.objectStore('unsynced');
      const request = store.add({
        type,
        data,
        timestamp: Date.now(),
        attempts: 0
      });

      request.onsuccess = () => {
        resolve(request.result);
      };

      request.onerror = () => {
        reject(request.error);
      };

      return request.result;
    }).catch(reject);
  });
};

// جلب البيانات غير المزامنة
export const getUnsyncedData = async (type = null) => {
  return new Promise((resolve, reject) => {
    withDB((transaction) => {
      const store = transaction.objectStore('unsynced');
      let request;

      if (type) {
        // استخدام الفهرس للبحث حسب النوع
        const index = store.index('type');
        request = index.getAll(type);
      } else {
        request = store.getAll();
      }

      request.onsuccess = () => {
        resolve(request.result);
      };

      request.onerror = () => {
        reject(request.error);
      };

      return request.result;
    }).catch(reject);
  });
};

// حذف البيانات غير المزامنة
export const deleteUnsyncedData = async (id) => {
  return new Promise((resolve, reject) => {
    withDB((transaction) => {
      const store = transaction.objectStore('unsynced');
      const request = store.delete(id);

      request.onsuccess = () => {
        resolve(request.result);
      };

      request.onerror = () => {
        reject(request.error);
      };

      return request.result;
    }).catch(reject);
  });
};

// حفظ سجل يومي
export const saveDailyLog = async (date, farmId, data) => {
  return new Promise((resolve, reject) => {
    withDB((transaction) => {
      const store = transaction.objectStore('dailyLogs');
      const request = store.put({
        date,
        farmId,
        data,
        timestamp: Date.now()
      });

      request.onsuccess = () => {
        resolve(request.result);
      };

      request.onerror = () => {
        reject(request.error);
      };

      return request.result;
    }).catch(reject);
  });
};

// جلب السجل اليومي
export const getDailyLog = async (date, farmId) => {
  return new Promise((resolve, reject) => {
    withDB((transaction) => {
      const store = transaction.objectStore('dailyLogs');
      const request = store.get([date, farmId]);

      request.onsuccess = () => {
        resolve(request.result ? request.result.data : null);
      };

      request.onerror = () => {
        reject(request.error);
      };

      return request.result;
    }).catch(reject);
  });
};

// جلب جميع السجلات اليومية
export const getAllDailyLogs = async () => {
  return new Promise((resolve, reject) => {
    withDB((transaction) => {
      const store = transaction.objectStore('dailyLogs');
      const request = store.getAll();

      request.onsuccess = () => {
        resolve(request.result);
      };

      request.onerror = () => {
        reject(request.error);
      };

      return request.result;
    }).catch(reject);
  });
};

// إضافة نشاط
export const addActivity = async (activity) => {
  return new Promise((resolve, reject) => {
    withDB((transaction) => {
      const store = transaction.objectStore('activities');
      const request = store.add({
        ...activity,
        timestamp: Date.now(),
        syncStatus: 'pending'
      });

      request.onsuccess = () => {
        resolve(request.result);
      };

      request.onerror = () => {
        reject(request.error);
      };

      return request.result;
    }).catch(reject);
  });
};

// جلب الأنشطة
export const getActivities = async (filters = {}) => {
  return new Promise((resolve, reject) => {
    withDB((transaction) => {
      const store = transaction.objectStore('activities');
      let request;

      // تطبيق الفلاتر باستخدام الفهارس
      if (filters.date && filters.farmId) {
        // البحث حسب التاريخ والمزرعة
        const dateIndex = store.index('date');
        const dateRequest = dateIndex.getAll(filters.date);

        dateRequest.onsuccess = () => {
          const activitiesByDate = dateRequest.result;
          const filteredActivities = activitiesByDate.filter(
            activity => activity.farmId === filters.farmId
          );
          resolve(filteredActivities);
        };

        dateRequest.onerror = () => {
          reject(dateRequest.error);
        };

        return dateRequest.result;
      } else if (filters.date) {
        // البحث حسب التاريخ فقط
        const dateIndex = store.index('date');
        request = dateIndex.getAll(filters.date);
      } else if (filters.farmId) {
        // البحث حسب المزرعة فقط
        const farmIndex = store.index('farmId');
        request = farmIndex.getAll(filters.farmId);
      } else {
        // جلب جميع الأنشطة
        request = store.getAll();
      }

      if (request) {
        request.onsuccess = () => {
          resolve(request.result);
        };

        request.onerror = () => {
          reject(request.error);
        };
      }
    }).catch(reject);
  });
};

// تحديث حالة مزامنة النشاط
export const updateActivitySyncStatus = async (id, status) => {
  return new Promise((resolve, reject) => {
    withDB((transaction) => {
      const store = transaction.objectStore('activities');
      const getRequest = store.get(id);

      getRequest.onsuccess = () => {
        const activity = getRequest.result;
        if (activity) {
          activity.syncStatus = status;
          activity.lastSyncAttempt = Date.now();

          const putRequest = store.put(activity);

          putRequest.onsuccess = () => {
            resolve(putRequest.result);
          };

          putRequest.onerror = () => {
            reject(putRequest.error);
          };
        } else {
          resolve(null);
        }
      };

      getRequest.onerror = () => {
        reject(getRequest.error);
      };

      return getRequest.result;
    }).catch(reject);
  });
};

// مسح البيانات القديمة
export const cleanupOldData = async (days = 30) => {
  return new Promise((resolve, reject) => {
    const cutoffDate = Date.now() - (days * 24 * 60 * 60 * 1000);

    withDB((transaction) => {
      const staticStore = transaction.objectStore('static');
      const userDataStore = transaction.objectStore('userData');
      const unsyncedStore = transaction.objectStore('unsynced');
      const activitiesStore = transaction.objectStore('activities');
      const dailyLogsStore = transaction.objectStore('dailyLogs');

      // مسح البيانات الثابتة القديمة
      const staticKeysRequest = staticStore.getAllKeys();
      staticKeysRequest.onsuccess = () => {
        const keys = staticKeysRequest.result;
        let pendingOperations = keys.length;

        if (pendingOperations === 0) {
          // الانتقال إلى الخطوة التالية
          cleanupUserData();
          return;
        }

        keys.forEach(key => {
          const getRequest = staticStore.get(key);
          getRequest.onsuccess = () => {
            const item = getRequest.result;
            if (item && item.timestamp < cutoffDate) {
              const deleteRequest = staticStore.delete(key);
              deleteRequest.onsuccess = deleteRequest.onerror = () => {
                pendingOperations--;
                if (pendingOperations === 0) {
                  cleanupUserData();
                }
              };
            } else {
              pendingOperations--;
              if (pendingOperations === 0) {
                cleanupUserData();
              }
            }
          };

          getRequest.onerror = () => {
            pendingOperations--;
            if (pendingOperations === 0) {
              cleanupUserData();
            }
          };
        });
      };

      // مسح بيانات المستخدم القديمة
      const cleanupUserData = () => {
        const userKeysRequest = userDataStore.getAllKeys();
        userKeysRequest.onsuccess = () => {
          const keys = userKeysRequest.result;
          let pendingOperations = keys.length;

          if (pendingOperations === 0) {
            // الانتقال إلى الخطوة التالية
            cleanupUnsyncedData();
            return;
          }

          keys.forEach(key => {
            const getRequest = userDataStore.get(key);
            getRequest.onsuccess = () => {
              const item = getRequest.result;
              if (item && item.timestamp < cutoffDate) {
                const deleteRequest = userDataStore.delete(key);
                deleteRequest.onsuccess = deleteRequest.onerror = () => {
                  pendingOperations--;
                  if (pendingOperations === 0) {
                    cleanupUnsyncedData();
                  }
                };
              } else {
                pendingOperations--;
                if (pendingOperations === 0) {
                  cleanupUnsyncedData();
                }
              }
            };

            getRequest.onerror = () => {
              pendingOperations--;
              if (pendingOperations === 0) {
                cleanupUnsyncedData();
              }
            };
          });
        };
      };

      // مسح البيانات غير المزامنة القديمة جداً (أكثر من 7 أيام)
      const cleanupUnsyncedData = () => {
        const unsyncedCutoffDate = Date.now() - (7 * 24 * 60 * 60 * 1000);
        const unsyncedRequest = unsyncedStore.getAll();

        unsyncedRequest.onsuccess = () => {
          const items = unsyncedRequest.result;
          let pendingOperations = items.length;

          if (pendingOperations === 0) {
            // الانتقال إلى الخطوة التالية
            cleanupActivities();
            return;
          }

          items.forEach(item => {
            if (item.timestamp < unsyncedCutoffDate) {
              const deleteRequest = unsyncedStore.delete(item.id);
              deleteRequest.onsuccess = deleteRequest.onerror = () => {
                pendingOperations--;
                if (pendingOperations === 0) {
                  cleanupActivities();
                }
              };
            } else {
              pendingOperations--;
              if (pendingOperations === 0) {
                cleanupActivities();
              }
            }
          });
        };
      };

      // مسح الأنشطة القديمة (أكثر من 90 يوماً)
      const cleanupActivities = () => {
        const activitiesCutoffDate = Date.now() - (90 * 24 * 60 * 60 * 1000);
        const activitiesRequest = activitiesStore.getAll();

        activitiesRequest.onsuccess = () => {
          const items = activitiesRequest.result;
          let pendingOperations = items.length;

          if (pendingOperations === 0) {
            // الانتقال إلى الخطوة التالية
            cleanupDailyLogs();
            return;
          }

          items.forEach(item => {
            if (item.timestamp < activitiesCutoffDate) {
              const deleteRequest = activitiesStore.delete(item.id);
              deleteRequest.onsuccess = deleteRequest.onerror = () => {
                pendingOperations--;
                if (pendingOperations === 0) {
                  cleanupDailyLogs();
                }
              };
            } else {
              pendingOperations--;
              if (pendingOperations === 0) {
                cleanupDailyLogs();
              }
            }
          });
        };
      };

      // مسح السجلات اليومية القديمة (أكثر من سنة)
      const cleanupDailyLogs = () => {
        const logsCutoffDate = Date.now() - (365 * 24 * 60 * 60 * 1000);
        const logsRequest = dailyLogsStore.getAll();

        logsRequest.onsuccess = () => {
          const items = logsRequest.result;
          let pendingOperations = items.length;

          if (pendingOperations === 0) {
            // انتهت جميع العمليات
            resolve();
            return;
          }

          items.forEach(item => {
            if (item.timestamp < logsCutoffDate) {
              const deleteRequest = dailyLogsStore.delete([item.date, item.farmId]);
              deleteRequest.onsuccess = deleteRequest.onerror = () => {
                pendingOperations--;
                if (pendingOperations === 0) {
                  resolve();
                }
              };
            } else {
              pendingOperations--;
              if (pendingOperations === 0) {
                resolve();
              }
            }
          });
        };
      };

      // بدء العملية
      staticKeysRequest.onerror = () => {
        reject(staticKeysRequest.error);
      };
    }).catch(reject);
  });
};
