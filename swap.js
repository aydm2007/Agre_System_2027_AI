const fs = require('fs');
const filePath = 'c:/tools/workspace/AgriAsset_v44/frontend/src/pages/CropPlanDetail.jsx';
const content = fs.readFileSync(filePath, 'utf8');

// The budget container start is the div just before "الميزانية التفصيلية"
let budgetIdx = content.indexOf('الميزانية التفصيلية');
let budgetStart = content.lastIndexOf('<div className="border dark:border-slate-700 rounded p-4', budgetIdx);

// The activities container start is the div just before "الأنشطة المرتبطة"
let actIdx = content.indexOf('الأنشطة المرتبطة');
let actStart = content.lastIndexOf('<div className="border dark:border-slate-700 rounded p-4', actIdx);

// The modal start is after both
let modalIdx = content.indexOf('{showImportModal && (');
let gridEnd = content.lastIndexOf('</div>', modalIdx);
// specifically, we want the closing div for the actStart block. It ends right before modalIdx's parent wrapper closes if any, or just before modalIdx.
// Wait, the grid has <div className="grid"> ... budget ... act ... </div>
let gridStart = content.indexOf('<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">');
if (gridStart !== -1) {
  let modified = content.replace('<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">', '<div className="space-y-6">');
  // Re-calculate indices on modified string
  budgetIdx = modified.indexOf('الميزانية التفصيلية');
  budgetStart = modified.lastIndexOf('<div className="border dark:border-slate-700 rounded p-4', budgetIdx);
  actIdx = modified.indexOf('الأنشطة المرتبطة');
  actStart = modified.lastIndexOf('<div className="border dark:border-slate-700 rounded p-4', actIdx);
  modalIdx = modified.indexOf('{showImportModal && (');
  
  // The activities block is from actStart to just before the closing </div> of <div className="space-y-6">
  // which is just before modalIdx
  let actStr = modified.substring(actStart, modalIdx);
  // Remove the trailing "      </div>\n\n      " from actStr to get just the activities div
  let lastDivIdx = actStr.lastIndexOf('</div>');
  let realActBlock = actStr.substring(0, lastDivIdx + 6); // Up to the </div>
  
  let budgetBlock = modified.substring(budgetStart, actStart);
  
  let finalContent = modified.substring(0, budgetStart) + realActBlock + "\n\n" + budgetBlock + modified.substring(actStart + realActBlock.length);
  
  fs.writeFileSync(filePath, finalContent, 'utf8');
  console.log("SUCCESS_NODE_SWAP");
} else {
  console.log("ERROR: Could not find gridStart grid-cols-1 lg:grid-cols-2 gap-6");
}
