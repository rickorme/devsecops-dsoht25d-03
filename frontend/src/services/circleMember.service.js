// frontend/src/services/circleMember.service.js
import api from './api';

export const circleMemberService = {
  // Search users to add to circle
  searchUsers: async (query, circleId) => {
    console.log('📡 API Call: GET /users/search', { query, circleId });
    try {
    const response = await api.get(`/users/search?query=${query}&circle_id=${circleId}`);
    console.log('📡 API Response:', response.data);
    return response.data;
    } catch (error) {
    console.error('📡 API Error:', error.response?.status, error.response?.data);
    throw error;
  }
  },

  // Add member to circle
  addMember: async (circleId, userId) => {
    const response = await api.post(`/circles/${circleId}/members`, { user_id: userId });
    return response.data;
  },

  // Remove member from circle
  removeMember: async (circleId, userId) => {
    const response = await api.delete(`/circles/${circleId}/members/${userId}`);
    return response.data;
  },

  // Update member role
  updateRole: async (circleId, userId, role) => {
    const response = await api.put(`/circles/${circleId}/members/${userId}/role`, { role });
    return response.data;
  },

  // Update circle name (owner only)
  updateCircleName: async (circleId, name) => {
    const response = await api.put(`/circles/${circleId}/name`, { name });
    return response.data;
  }

  // Additional member management methods can be added here
};