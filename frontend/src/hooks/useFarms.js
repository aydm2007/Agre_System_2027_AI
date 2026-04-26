import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Farms } from '../api/client'
import ar from '../i18n/ar'

const TEXT = ar.farms

/**
 * Custom hook to manage Farm data using React Query.
 * Provides: farms (list), loading/error states, and standard mutations (add, update, delete).
 */
export function useFarms(searchQuery = '') {
  const queryClient = useQueryClient()
  const queryKey = ['farms', searchQuery]

  // 1. Fetch
  const {
    data: farms = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey,
    queryFn: async () => {
      const { data } = await Farms.list(searchQuery ? { q: searchQuery } : {})
      return data.results || data || []
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    keepPreviousData: true,
  })

  // 2. Mutations
  const addMutation = useMutation({
    mutationFn: (newFarm) => Farms.create(newFarm),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['farms'] })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, updates }) => Farms.update(id, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['farms'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => Farms.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['farms'] })
    },
  })

  return {
    farms,
    isLoading,
    isError,
    errorObj: error,
    errorMessage: isError ? error?.response?.data?.detail || TEXT.loadError : null,

    addFarm: addMutation.mutateAsync,
    updateFarm: updateMutation.mutateAsync,
    deleteFarm: deleteMutation.mutateAsync,

    isAdding: addMutation.isPending,
    isUpdating: updateMutation.isPending,
    isDeleting: deleteMutation.isPending,
  }
}
