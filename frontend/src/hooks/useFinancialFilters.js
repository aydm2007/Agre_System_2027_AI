/**
 * [AGRI-GUARDIAN Axis 6 / AGENTS.md L142-154, L186-200]
 * Smart multi-level cascading filter hook for financial interfaces.
 */
import { useSearchParams } from 'react-router-dom'

import { api } from '../api/httpClient'
import { useFarmContext } from '../api/farmContextHook'
import { createUseFinancialFilters, DIM } from './useFinancialFiltersCore'

export const useFinancialFilters = createUseFinancialFilters({
  api,
  useFarmContext,
  useSearchParamsHook: useSearchParams,
})

export { DIM }

export default useFinancialFilters
