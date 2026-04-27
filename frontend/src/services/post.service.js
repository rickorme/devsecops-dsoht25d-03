// frontend/src/services/post.service.js
import api from './api';

const BASE_URL = '/posts';

export const postService = {
  // Get feed (recent posts from user's circles)
  getFeed: async (limit = 20, offset = 0) => {
    try {
      const response = await api.get(`${BASE_URL}/feed?limit=${limit}&offset=${offset}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching feed:', error);
      throw error;
    }
  },

  // Get posts from a specific circle
  getCirclePosts: async (circleId, limit = 50, offset = 0) => {
    try {
      // Note: The backend API should support pagination for circle posts to handle large circles efficiently.
      const response = await api.get(`${BASE_URL}/circle/${circleId}?limit=${limit}&offset=${offset}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching circle posts:', error);
      throw error;
    }
  },

  // Create post
  createPost: async (postData) => {
    try {
      const response = await api.post(`${BASE_URL}/`, postData);
      return response.data;
    } catch (error) {
      console.error('Error creating post:', error);
      throw error;
    }
  },

  // Get single post
  getPost: async (postId) => {
    try {
      const response = await api.get(`${BASE_URL}/${postId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching post:', error);
      throw error;
    }
  },

  // Delete post
  deletePost: async (postId) => {
    try {
      await api.delete(`${BASE_URL}/${postId}`);
    } catch (error) {
      console.error('Error deleting post:', error);
      throw error;
    }
  }
};