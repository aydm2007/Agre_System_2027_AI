const fs = require('fs');
const filePath = 'c:/tools/workspace/AgriAsset_v44/frontend/src/pages/CropPlanDetail.jsx';
const lines = fs.readFileSync(filePath, 'utf8').split('\n');

// Find start of grid
let gridStartIdx = lines.findIndex(l => l.includes('<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">'));
let budgetStartIdx = lines.findIndex((l, i) => i > gridStartIdx && l.includes('الميزانية التفصيلية</h3>'));
budgetStartIdx = lines.lastIndexOf('        <div className="border dark:border-slate-700 rounded p-4 bg-white dark:bg-slate-800 shadow-sm">', budgetStartIdx);

let activityStartIdx = lines.findIndex((l, i) => i > budgetStartIdx && l.includes('الأنشطة المرتبطة</h3>'));
activityStartIdx = lines.lastIndexOf('        <div className="border dark:border-slate-700 rounded p-4 bg-white dark:bg-slate-800 shadow-sm">', activityStartIdx);

let gridEndIdx = lines.findIndex((l, i) => i > activityStartIdx && l.includes('{showImportModal && ('));
// the wrapper closes before showImportModal
gridEndIdx = lines.lastIndexOf('      </div>', gridEndIdx);

if (gridStartIdx !== -1 && budgetStartIdx !== -1 && activityStartIdx !== -1 && gridEndIdx !== -1) {
    // Modify grid-cols to space-y-6
    lines[gridStartIdx] = lines[gridStartIdx].replace('<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">', '<div className="space-y-6">');
    
    // Extract sections
    // Budget: from budgetStartIdx to activityStartIdx - 1
    // Activities: from activityStartIdx to gridEndIdx - 1
    const budgetSection = lines.slice(budgetStartIdx, activityStartIdx);
    const activitySection = lines.slice(activityStartIdx, gridEndIdx);
    
    // Swap them
    lines.splice(budgetStartIdx, activitySection.length + budgetSection.length, ...activitySection, '', ...budgetSection);
    
    fs.writeFileSync(filePath, lines.join('\n'), 'utf8');
    fs.writeFileSync('c:/tools/workspace/AgriAsset_v44/swap_success.txt', 'Swapped correctly. Lines used: ' + budgetStartIdx + ',' + activityStartIdx + ',' + gridEndIdx, 'utf8');
    console.log('Done');
} else {
    fs.writeFileSync('c:/tools/workspace/AgriAsset_v44/swap_error.txt', `Indices: grid=${gridStartIdx}, bdg=${budgetStartIdx}, act=${activityStartIdx}, end=${gridEndIdx}\n`, 'utf8');
    console.log('Error');
}
