// frontend/src/components/posts/PostCard.jsx
import './PostCard.css';


const PostCard = ({ post, showCircle = false }) => {
  return (
    <div className="post-card">
      <div className="post-header">
        <div className="post-author-avatar">
          {post.author_name?.charAt(0).toUpperCase() || 'U'}
        </div>
        <div className="post-author-info">
          <div className="post-author">{post.author_name}</div>
          <div className="post-date">{new Date(post.created_at).toLocaleDateString()}</div>
        </div>
      </div>
      <div className="post-content">
        <h4>{post.title}</h4>
        <p>{post.content}</p>
        {showCircle && post.circle_name && (
          <div className="post-circle">in {post.circle_name}</div>
        )}
      </div>
      <div className="post-actions">
        <button className="post-action-btn">❤️ Like</button>
        <button className="post-action-btn">💬 Comment</button>
        <button className="post-action-btn">🔄 Share</button>
      </div>
    </div>
  );
};

export default PostCard;