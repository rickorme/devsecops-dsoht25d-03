// frontend/src/pages/SearchPage.jsx
import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { searchService } from '../services/search.service';
import './SearchPage.css';

function SearchPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const query = searchParams.get('q') || '';
  
  const [results, setResults] = useState({
    users: [],
    circles: [],
    posts: []
  });
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('users');

  // Function to perform search using the search service
  const performSearch = useCallback(async () => {
    setLoading(true);
    try {
      const data = await searchService.search(query);
      setResults(data);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setLoading(false);
    }
  }, [query]);

  useEffect(() => {
    if (query) {
      performSearch();
    } else {
    loadAllUsers();
  }
}, [query, performSearch]);

  const loadAllUsers = async () => {
  setLoading(true);
  try {
    const usersResponse = await api.get('/users?limit=100');
    setResults({
      users: usersResponse.data || [],
      circles: [],
      posts: []
    });
  } catch (error) {
    console.error('Failed to load users:', error);
  } finally {
    setLoading(false);
  }
  };


  return (
  <main className="dashboard-main">
    <div className="search-header">
      <h1>Search Results for "{query}"</h1>
      <p className="results-count">
        Found {results.users.length} users, {results.circles.length} circles, {results.posts.length} posts
      </p>
    </div>

    <div className="search-tabs">
      <button 
        className={`tab ${activeTab === 'users' ? 'active' : ''}`}
        onClick={() => setActiveTab('users')}
      >
        Users ({results.users.length})
      </button>
      <button 
        className={`tab ${activeTab === 'circles' ? 'active' : ''}`}
        onClick={() => setActiveTab('circles')}
      >
        Circles ({results.circles.length})
      </button>
      <button 
        className={`tab ${activeTab === 'posts' ? 'active' : ''}`}
        onClick={() => setActiveTab('posts')}
      >
        Posts ({results.posts.length})
      </button>
    </div>

    <div className="search-results">
      {loading ? (
        <div className="loading-spinner">Searching...</div>
      ) : (
        <>
          {activeTab === 'users' && (
            <div className="users-grid">
              {results.users.map(user => (
                <div key={user.id} className="user-card">
                  <div className="user-avatar">
                    {user.username.charAt(0).toUpperCase()}
                  </div>
                  <div className="user-info">
                    <h3>{user.username}</h3>
                    <p>{user.email}</p>
                  </div>
                  <button 
                    className="view-btn"
                    onClick={() => navigate(`/profile/${user.id}`)}
                  >
                    View Profile
                  </button>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'circles' && (
            <div className="circles-grid">
              {results.circles.map(circle => (
                <div key={circle.id} className="circle-card">
                  <h3>{circle.name}</h3>
                  <p>{circle.description}</p>
                  <button 
                    className="view-btn"
                    onClick={() => navigate(`/circles/${circle.id}`)}
                  >
                    View Circle
                  </button>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'posts' && (
            <div className="posts-feed">
              {results.posts.map(post => (
                <div key={post.id} className="post-card">
                  <h4>{post.title}</h4>
                  <p>{post.content}</p>
                  <div className="post-meta">
                    <span>Posted by {post.author_name}</span>
                    <span>{new Date(post.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  </main>
);
}

export default SearchPage;
