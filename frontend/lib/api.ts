import { GameSnapshot, DataSourcesMeta } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = {
  getGames: async (): Promise<{ data: GameSnapshot[]; meta: DataSourcesMeta }> => {
    const res = await fetch(`${API_BASE}/api/games`, { cache: 'no-store' });
    if (!res.ok) {
      throw new Error(`API call failed: ${res.status}`);
    }
    return res.json();
  }
};