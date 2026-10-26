/** Browser online flag. Listeners live in an effect so a later motion pass can wrap the banner. */

import { useEffect, useState } from "react"

export function useOnline(): boolean {
  const [online, setOnline] = useState(() => (typeof navigator === "undefined" ? true : navigator.onLine))

  useEffect(() => {
    function onlineNow() {
      setOnline(true)
    }
    function offlineNow() {
      setOnline(false)
    }
    window.addEventListener("online", onlineNow)
    window.addEventListener("offline", offlineNow)
    return () => {
      window.removeEventListener("online", onlineNow)
      window.removeEventListener("offline", offlineNow)
    }
  }, [])

  return online
}
