// frontend/src/services/userDashboard.service.js
// import axios from 'axios';
import api from './api';
import { API_BASE_URL } from '../config/index';
import { circleService } from './circle.service';
import { postService } from './post.service';

export const userDashboardService = {
  async getUserDashboardData() {
    try {
      // 3 parallel API calls to fetch user info, circles with badges, and recent feed posts
      const [userResponse, circlesResponse, feedResponse] = await Promise.all([
        // 1. User info (exists)
        api.get(`${API_BASE_URL}/auth/me`, {
          withCredentials: true
        }),
        
        // 2. User's circles with badges (new)
        circleService.getMyCircles(),
        
        // 3. Recent feed posts (new)
        postService.getFeed(10) // limit 10 posts
      ]);
      
      // Structure the dashboard data
      return {
        user: userResponse.data,
        circles: circlesResponse, // array of circles with badges
        posts: feedResponse, // array of recent posts
        // Summarize counts for dashboard overview
        circlesCount: circlesResponse?.length || 0,
        postsCount: feedResponse?.length || 0,
        notificationsCount: 0, // Add notification count logic if needed
      };
      
    } catch (error) {
      console.error('User Dashboard service error:', error);
      throw error;
    }
  }
};