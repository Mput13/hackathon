import { useState, useEffect } from 'react'

export default function CountUp({ end, duration = 2000, suffix = "" }) {
  const [count, setCount] = useState(0)

  useEffect(() => {
    let startTime
    let animationFrame

    // Parse the end value (remove non-numeric chars if any, though passed as prop is better)
    const endVal = parseFloat(String(end).replace(/[^0-9.-]+/g, ""))
    if (isNaN(endVal)) {
      setCount(end)
      return
    }

    const step = (timestamp) => {
      if (!startTime) startTime = timestamp
      const progress = Math.min((timestamp - startTime) / duration, 1)
      
      // Easing function: easeOutExpo
      const easeOut = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)
      
      setCount(Math.floor(easeOut * endVal))

      if (progress < 1) {
        animationFrame = requestAnimationFrame(step)
      }
    }

    animationFrame = requestAnimationFrame(step)

    return () => cancelAnimationFrame(animationFrame)
  }, [end, duration])

  return <span>{count}{suffix}</span>
}
