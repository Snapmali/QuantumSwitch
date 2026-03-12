import axios, { type AxiosError, type AxiosResponse } from 'axios'
import type {
  Song,
  PaginatedResponse,
  GameStatus,
  AppConfig,
  SwitchSongRequest,
  SwitchSongResponse,
  ApiResponse,
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
  getSongs: (params: { page?: number; pageSize?: number; search?: string; favorites?: boolean }) => {
    const { page = 1, pageSize = 20, search, favorites } = params
    let url = `/songs?page=${page}&pageSize=${pageSize}`
    if (search) {
      url += `&search=${encodeURIComponent(search)}`
    }
    if (favorites) {
      url += '&favorites=true'
    }
    return api.get<ApiResponse<PaginatedResponse<Song>>>(url)
  },

  // Get song by ID
  getById: (id: number) => api.get<ApiResponse<Song>>(`/songs/${id}`),

  // Reload songs from PVDB files
  reload: () => api.post<ApiResponse<PaginatedResponse<Song>>>('/songs/reload'),

  // Toggle favorite status
  toggleFavorite: (id: number) => api.post<ApiResponse<{ isFavorite: boolean }>>(`/songs/${id}/favorite`),

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
}

// System API
export const systemApi = {
  // Health check
  health: () => api.get<ApiResponse<{ status: string; gameRunning: boolean; version: string }>>('/health'),

  // Get config
  getConfig: () => api.get<ApiResponse<AppConfig>>('/config'),
}

export default api
