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

// 禁用状态的浅色颜色值
export const DifficultyDisabledColorValues: Record<string, string> = {
  'EASY': '#a0cfff',
  'NORMAL': '#b3e19d',
  'HARD': '#f0c78a',
  'EXTREME': '#fab6b6',
  'EXTRA EXTREME': '#d8b4fe',
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

/** 获取禁用状态的 CSS 样式对象（使用对应难度的浅色版本） */
export function getDifficultyDisabledStyle(diffName: string): Record<string, string> {
  const color = DifficultyDisabledColorValues[diffName] || '#c0c4cc'
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
// 新的层级结构辅助函数
// ============================================

/** 获取 ChartStyle 的显示名称 */
export function getChartStyleDisplayName(style: string): string {
  const names: Record<string, string> = {
    'ARCADE': 'Arcade',
    'CONSOLE': 'Console',
    'MIXED': 'Mixed',
    'Mixed': 'Mixed',
  }
  return names[style] || style
}

/** 根据 style 和 type 查找对应的 DifficultyTypeDetail */
export function findDifficultyDetail(
  song: Song,
  style: string,
  difficultyType: number
): DifficultyTypeDetail | undefined {
  const styleDetail = song.difficultyDetails.find(s => s.style === style)
  if (!styleDetail) return undefined
  return styleDetail.difficulties.find(d => d.type === difficultyType)
}

/** 检查歌曲是否有特定难度类型 */
export function hasDifficultyType(song: Song, difficultyType: number): boolean {
  return song.difficultyDetails.some(style =>
    style.difficulties.some(diff => diff.type === difficultyType && diff.hasEnabledCharts)
  )
}

/** 获取歌曲的所有可用难度类型（去重） */
export function getAvailableDifficultyTypes(song: Song): DifficultyTypeDetail[] {
  const result: DifficultyTypeDetail[] = []
  const seen = new Set<number>()

  for (const style of song.difficultyDetails) {
    for (const diff of style.difficulties) {
      if (!seen.has(diff.type) && diff.hasEnabledCharts) {
        result.push(diff)
        seen.add(diff.type)
      }
    }
  }

  // Sort by type number
  result.sort((a, b) => a.type - b.type)
  return result
}

/** 获取特定 Style 和 DifficultyType 的第一个启用的 ChartInfo */
export function getFirstEnabledChartInfo(
  song: Song,
  style: string,
  difficultyType: number
): ChartInfoDetail | undefined {
  const diffDetail = findDifficultyDetail(song, style, difficultyType)
  if (!diffDetail) return undefined
  return diffDetail.chartInfos.find(c => c.enabled)
}

/** 获取特定难度类型的首选 ChartInfo（跨所有 Styles） */
export function getPreferredChartInfo(
  song: Song,
  difficultyType: number
): { chartInfo?: ChartInfoDetail; style?: string } {
  const styleOrder = ['ARCADE', 'CONSOLE', 'MIXED']

  for (const style of styleOrder) {
    const diff = findDifficultyDetail(song, style, difficultyType)
    if (diff?.hasEnabledCharts) {
      const chart = diff.chartInfos.find(c => c.enabled)
      if (chart) {
        return { chartInfo: chart, style }
      }
    }
  }

  return {}
}

// ============================================
// 接口定义 - 新的层级结构
// ============================================

// Individual chart information from a specific mod
export interface ChartInfoDetail {
  level: number
  edition?: number
  scriptPath?: string
  isExtra?: boolean
  isOriginal?: boolean
  isSlide?: boolean
  modId: number
  modName?: string
  enabled?: boolean
}

// Difficulty type containing all its charts
export interface DifficultyTypeDetail {
  type: number
  name: string
  shortName: string
  chartInfos: ChartInfoDetail[]
  hasEnabledCharts?: boolean
}

// Chart style (ARCADE/CONSOLE/Mixed) containing all difficulties
export interface ChartStyleDetail {
  style: string  // "ARCADE", "CONSOLE", "MIXED"
  displayName: string  // "街机", "主机", "混合"
  difficulties: DifficultyTypeDetail[]
  hasEnabledDifficulties?: boolean
}

// [DEPRECATED] Old flat difficulty structure - kept for reference
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
  modIds?: number[]  // 来源 Mod ID 列表
  enabled?: boolean  // 难度是否可用
}

// Song data structure
export interface Song {
  id: number
  name: string  // Japanese name (priority)
  nameEn?: string
  nameReading?: string
  difficultyDetails: ChartStyleDetail[]  // 新的层级结构：ChartStyle -> DifficultyType -> ChartInfo
  hidden?: boolean
  modPath?: string
  modInfo?: ModInfo  // Mod information (single, for backward compatibility)
  modInfos?: ModInfo[]  // All associated Mod information list
  modEnabled?: boolean  // Whether the mod is enabled
  isVanilla?: boolean  // Whether this is a vanilla (original) song
  bpm?: string
  description?: string
  attributes?: Record<string, string>
  isFavorite?: boolean  // Whether this song is favorited

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
  id: number        // Mod 唯一标识符
  name: string
  path: string
  enabled: boolean
  author?: string
  version?: string
}

// Current song difficulty info
export interface CurrentSongDifficultyInfo {
  name: string  // 难度名称，如 "EASY", "NORMAL" 等
  enabled: boolean  // 是否启用
}

// Current song info from game status
export interface CurrentSongInfo {
  id: number
  name: string
  nameEn?: string
  difficulties: CurrentSongDifficultyInfo[]  // 难度信息列表
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
  currentSongInfo?: CurrentSongInfo  // 新增：当前歌曲信息
  currentChartStyle?: string  // 新增：当前 ChartStyle (ARCADE/CONSOLE/MIXED)
  isIngame?: boolean  // 新增：是否正在游玩中
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
  currentSongInfo?: CurrentSongInfo  // 新增：当前歌曲完整信息
  currentChartStyle?: string  // 新增：当前 ChartStyle
  isIngame?: boolean  // 新增：是否正在游玩中
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
  style?: string  // "ARCADE", "CONSOLE", "MIXED"
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
  favoritesOnly?: boolean  // 是否只显示收藏歌曲
}
