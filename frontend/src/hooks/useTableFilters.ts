import { computed, reactive } from 'vue'

export interface FilterField {
  key: string
  label: string
  options: Array<{ value: string; label: string }>
}

export function useTableFilters(
  initial: Record<string, string>,
  fields: FilterField[],
  onChange: () => void,
) {
  const state = reactive<Record<string, string>>({ ...initial })

  const activeCount = computed(() => Object.values(state).filter((value) => value !== '').length)

  function apply() {
    onChange()
  }

  function reset() {
    for (const key of Object.keys(state)) state[key] = ''
    onChange()
  }

  function setValue(key: string, value: string) {
    if (key in state) state[key] = value
    onChange()
  }

  return { state, fields, activeCount, reset, setValue, apply }
}
