// frontend/src/services/search.service.js
import api from './api';

// Service for handling search-related API calls
export const searchService = {
  search: async (query) => {
    try {
      // 1. Get all users and filter locally )
      const usersResponse = await api.get('/users?limit=100');
      const allUsers = usersResponse.data || [];
      
      // 2. Filter by username (case insensitive)
      const filteredUsers = allUsers.filter(user => 
        user.username.toLowerCase().includes(query.toLowerCase())
      );
      
      // 3. For now, return only users (we'll add circles and posts later)
      return {
        users: filteredUsers,
        circles: [],
        posts: []
      };
    } catch (error) {
      console.error('Search error:', error);
      return { users: [], circles: [], posts: [] };
    }
  }
};