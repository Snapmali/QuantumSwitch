import axios, { type AxiosError, type AxiosResponse } from 'axios'
import type {
  Song,
  PaginatedResponse,
  GameStatus,
  SwitchSongRequest,
  SwitchSongResponse,
  ApiResponse,
  SongAlias,
  SongAliasMatchItem,
  CreateAliasRequest,
  UpdateAliasRequest,
  ToggleFavoriteRequest,
  ModInfoSearchItem,
} from '@/types'
import { ElMessage } from 'element-plus'

// Create axios instance
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    if (!response.data.success) {
      ElMessage.error(response.data.error || 'Unknown error')
      return Promise.reject(new Error(response.data.error || 'Unknown error'))
    }
    return response
  },
  (error: AxiosError<ApiResponse>) => {
    const message = error.response?.data?.error || error.message || 'Network error'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

// Song API
export const songApi = {
  // Get paginated songs
  getSongs: (params: {
    page?: number
    pageSize?: number
    search?: string
    favorites?: boolean
    searchMode?: 'song' | 'mod'
    modId?: number
  }) => {
    const { page = 1, pageSize = 20, search, favorites, searchMode, modId } = params
    let url = `/songs?page=${page}&pageSize=${pageSize}`
    if (search) {
      url += `&search=${encodeURIComponent(search)}`
    }
    if (favorites) {
      url += '&favorites=true'
    }
    if (searchMode) {
      url += `&searchMode=${searchMode}`
    }
    if (modId !== undefined) {
      url += `&modId=${modId}`
    }
    return api.get<ApiResponse<PaginatedResponse<Song>>>(url)
  },

  // Get song by ID
  getById: (id: number) => api.get<ApiResponse<Song>>(`/songs/detail?song_id=${id}`),

  // Reload songs from PVDB files
  reload: () => api.post<ApiResponse<PaginatedResponse<Song>>>('/songs/reload'),

  // Toggle favorite status
  toggleFavorite: (id: number) => api.post<ApiResponse<{ isFavorite: boolean }>>('/songs/favorite', { songId: id } as ToggleFavoriteRequest),

  // Get all favorite song IDs
  getFavorites: () => api.get<ApiResponse<number[]>>(`/songs/favorites`),
}

// Game API
export const gameApi = {
  // Get game status
  getStatus: () => api.get<ApiResponse<GameStatus>>('/game/status'),

  // Switch song
  switchSong: (data: SwitchSongRequest) => api.post<ApiResponse<SwitchSongResponse>>('/game/switch', data),

  // Get current song
  getCurrent: () => api.get<ApiResponse<{ songId?: number; sortId?: number; difficulty?: number; difficultyName?: string; songName?: string }>>('/game/current'),

  // Reattach to game process
  reattach: () => api.post<ApiResponse<{ attached: boolean }>>('/game/reattach'),
}

// Alias API
export const aliasApi = {
  // Get all aliases
  getAll: () => api.get<ApiResponse<SongAlias[]>>('/songs/aliases'),

  // Create a new alias
  create: (data: CreateAliasRequest) => api.post<ApiResponse<SongAlias>>('/songs/aliases', data),

  // Update an alias
  update: (id: string, data: UpdateAliasRequest) => api.put<ApiResponse<SongAlias>>('/songs/aliases', { ...data, id }),

  // Delete an alias
  delete: (id: string) => api.delete<ApiResponse<{ deleted: boolean }>>(`/songs/aliases?alias_id=${id}`),

  // Search aliases
  search: (query: string, limit?: number) => {
    let url = `/songs/aliases/search?query=${encodeURIComponent(query)}`
    if (limit) {
      url += `&limit=${limit}`
    }
    return api.get<ApiResponse<SongAliasMatchItem[]>>(url)
  },
}

// Mod API
export const modApi = {
  // Search mods by name
  search: (query: string, limit?: number) => {
    let url = `/songs/mods/search?query=${encodeURIComponent(query)}`
    if (limit) {
      url += `&limit=${limit}`
    }
    return api.get<ApiResponse<ModInfoSearchItem[]>>(url)
  },
}

export default api
