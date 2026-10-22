import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function isStatisticalModel(modelName?: string | null): boolean {
  if (!modelName) return false
  const lower = modelName.toLowerCase()
  return (
    lower.includes('linear') ||
    lower.includes('polynomial') ||
    lower.includes('ridge') ||
    lower.includes('regression') ||
    lower === 'none'
  )
}

