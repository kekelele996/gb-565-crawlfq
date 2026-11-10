import { onBeforeUnmount, onMounted, ref } from 'vue'

export function usePolling(task: () => Promise<void> | void, intervalMs = 8000, immediate = true) {
  const active = ref(false)
  const lastRun = ref<string>('')
  let timer: number | null = null

  async function run() {
    if (active.value) return
    active.value = true
    try {
      await task()
      lastRun.value = new Date().toISOString()
    } finally {
      active.value = false
    }
  }

  function start() {
    if (timer !== null) return
    timer = window.setInterval(run, intervalMs)
  }

  function stop() {
    if (timer !== null) {
      window.clearInterval(timer)
      timer = null
    }
  }

  onMounted(() => {
    if (immediate) void run()
    start()
  })

  onBeforeUnmount(stop)

  return { active, lastRun, run, start, stop }
}
