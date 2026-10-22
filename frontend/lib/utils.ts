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

/**
 * Memastikan string ISO tanpa penanda timezone (misal UTC dari backend)
 * di-parse sebagai UTC sehingga otomatis disesuaikan ke waktu lokal (WIB / UTC+7).
 */
export function toUtcDate(isoString: string | null | undefined): Date | null {
  if (!isoString) return null
  const s = isoString.endsWith('Z') || isoString.includes('+') ? isoString : `${isoString}Z`
  const d = new Date(s)
  return isNaN(d.getTime()) ? new Date(isoString) : d
}
