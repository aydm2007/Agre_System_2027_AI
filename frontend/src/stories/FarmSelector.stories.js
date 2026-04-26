/**
 * [AGRI-GUARDIAN] Storybook Stories — Production Components
 *
 * Stories for the core reusable components used across all modules.
 * Run: npx storybook dev -p 6006
 */
import FarmSelector from '../components/FarmSelector.jsx'

// ──────────────────────────────────────────────────────────────────────────────
// FarmSelector
// ──────────────────────────────────────────────────────────────────────────────
export default {
  title: 'Core/FarmSelector',
  component: FarmSelector,
  parameters: {
    layout: 'centered',
    docs: {
      description: { component: 'مُحدد المزرعة — يظهر في كل الصفحات. يدعم "الكل" أو مزرعة واحدة.' },
    },
  },
  tags: ['autodocs'],
}

export const Default = {
  args: {
    farms: [
      { id: 1, name: 'مزرعة سردود' },
      { id: 2, name: 'مزرعة الوادي' },
      { id: 3, name: 'مزرعة الجبل' },
    ],
    selectedFarmId: 1,
    onChange: (id) => console.log('Farm selected:', id),
  },
}

export const AllFarmsSelected = {
  args: {
    ...Default.args,
    selectedFarmId: 'all',
  },
}

export const SingleFarm = {
  args: {
    farms: [{ id: 1, name: 'مزرعة سردود' }],
    selectedFarmId: 1,
    onChange: (id) => console.log('Farm selected:', id),
  },
}
