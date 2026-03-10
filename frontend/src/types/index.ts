// Song difficulty types
export enum DifficultyType {
  EASY = 0,
  NORMAL = 1,
  HARD = 2,
  EXTREME = 3,
  EXTRA_EXTREME = 4,
}

// ============================================
// 统一难度颜色配置 - 所有组件都应使用这里的定义
// ============================================

// Element Plus Tag 类型
export const DifficultyTagTypes: Record<string, string> = {
  'EASY': 'primary',
  'NORMAL': 'success',
  'HARD': 'warning',
  'EXTREME': 'danger',
  'EXTRA EXTREME': '', // 空字符串表示使用自定义颜色
}

// CSS 颜色值 (用于自定义样式)
export const DifficultyColorValues: Record<string, string> = {
  'EASY': '#409eff',
  'NORMAL': '#67c23a',
  'HARD': '#e6a23c',
  'EXTREME': '#f56c6c',
  'EXTRA EXTREME': '#9333ea',
}

// 短标签名称
export const DifficultyShortNames: Record<string, string> = {
  'EASY': 'E',
  'NORMAL': 'N',
  'HARD': 'H',
  'EXTREME': 'Ex',
  'EXTRA EXTREME': 'EX',
}

// 完整标签名称
export const DifficultyFullNames: Record<string, string> = {
  'EASY': 'EASY',
  'NORMAL': 'NORMAL',
  'HARD': 'HARD',
  'EXTREME': 'EXTREME',
  'EXTRA EXTREME': 'EXTRA EXTREME',
}

// ============================================
// 辅助函数
// ============================================

/** 获取 Element Plus Tag 类型 */
export function getDifficultyTagType(diffName: string): string {
  return DifficultyTagTypes[diffName] || 'info'
}

/** 获取自定义颜色值 (EXTRA EXTREME 使用紫色) */
export function getDifficultyColor(diffName: string): string {
  if (diffName === 'EXTRA EXTREME') {
    return '#9333ea' // Purple
  }
  return ''
}

/** 获取 CSS 样式对象 */
export function getDifficultyStyle(diffName: string): Record<string, string> {
  const color = DifficultyColorValues[diffName] || '#909399'
  return {
    backgroundColor: color,
    color: '#fff',
  }
}

/** 获取短标签 */
export function getDifficultyShortLabel(diffName: string): string {
  return DifficultyShortNames[diffName] || diffName
}

/** 获取完整标签 */
export function getDifficultyLabel(diffName: string): string {
  return DifficultyFullNames[diffName] || diffName
}

/** 格式化等级显示 */
export function formatLevel(level: number): string {
  if (level === 0) return ''
  return Number.isInteger(level) ? level.toString() : level.toFixed(1)
}

// ============================================
// 接口定义
// ============================================

// Difficulty detail information
export interface DifficultyDetail {
  type: number
  name: string
  level: number  // 支持小数如 6.5
  edition: number  // 谱面版本
  scriptPath?: string
  isExtra?: boolean  // 是否为 EXTRA EXTREME
  isOriginal?: boolean  // 是否为原谱
  isSlide?: boolean  // 是否为滑动谱
  index?: number  // 同类型难度的索引
}

// Song data structure
export interface Song {
  id: number
  sortId: number
  name: string  // Japanese name (priority)
  nameEn?: string
  nameReading?: string
  difficultyDetails: DifficultyDetail[]
  hidden?: boolean
  modPath?: string
  modInfo?: ModInfo  // Mod information (single, for backward compatibility)
  modInfos?: ModInfo[]  // All associated Mod information list
  modEnabled?: boolean  // Whether the mod is enabled
  isVanilla?: boolean  // Whether this is a vanilla (original) song
  bpm?: string
  description?: string
  attributes?: Record<string, string>

  // Song credits from songinfo
  music?: string        // 作曲家
  arranger?: string     //编曲家
  lyrics?: string       // 作词家
  guitarPlayer?: string  // 吉他手
  illustrator?: string   // 画师/插画师
  manipulator?: string   // 调教师
  pvEditor?: string      // PV编辑
}

// Mod information
export interface ModInfo {
  name: string
  path: string
  enabled: boolean
  author?: string
  version?: string
}

// Game status - matches backend GameStatusResponse
export interface GameStatus {
  running: boolean
  processId?: number
  currentSongId?: number
  currentSortId?: number
  currentDifficulty?: number
  currentDifficultyName?: string
  gameState?: number
  edenVersion: boolean
  edenOffset: number
}

// Game status display format for GameStatus component
export interface GameStatusDisplay {
  status: 'running' | 'not_running' | 'busy' | 'error'
  isEdenVersion: boolean
  edenOffset: number
  currentSong?: {
    name: string
    difficultyType: string
  }
}

// API response wrapper
export interface ApiResponse<T = unknown> {
  success: boolean
  data: T
  error: string | null
}

// Paginated response
export interface PaginatedResponse<T> {
  songs: T[]
  total: number
  page: number
  pageSize: number
  totalPages: number
  hiddenCount?: number
}

// Song list response (alias for PaginatedResponse<Song>)
export type SongListResponse = PaginatedResponse<Song>

// Switch song request
export interface SwitchSongRequest {
  songId: number
  difficulty: number
  force?: boolean
}

// Switch song response - matches backend SwitchSongResponse
export interface SwitchSongResponse {
  success: boolean
  message: string
  actualDifficulty?: number
  actualDifficultyName?: string
  requiresDelayedUpdate?: boolean
}

// App config - matches backend ConfigResponse
export interface AppConfig {
  appName?: string
  appVersion: string
  gameProcessName: string
  gameRunning: boolean
  gameBaseAddress?: string
  edenOffsetApplied?: boolean
  pvdbFiles: string[]
}

// Filter options
export interface FilterOptions {
  search: string
  difficulties: DifficultyType[]
  hiddenOnly: boolean
  sortBy: 'id' | 'name' | 'pvId'
  sortOrder: 'asc' | 'desc'
}
