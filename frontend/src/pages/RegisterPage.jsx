// frontend/src/pages/RegisterPage.jsx
import { useState } from 'react';
import { useAuth } from '../contexts/useAuth.js';
import { useNavigate } from 'react-router-dom';
import { Link } from 'react-router-dom';
import './RegisterPage.css';

function RegisterPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [fullName, setFullName] = useState(''); 
  const [email, setEmail] = useState('');
  
  const { register, loading } = useAuth(); 

  const navigate = useNavigate();

  const handleSubmit = async (e) => {
  e.preventDefault();
  setError('');
  
  // Validation
  if (password !== confirmPassword) {
    setError('Passwords do not match');
    return;
  }
  
  if (password.length < 8) {
    setError('Password must be at least 8 characters');
    return;
  }

  if (password && !/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@£$€&]).{8,}$/.test(password)) {
    setError('Password must include at least one upper and lower case letter, a number and a special character')
    return;
  }
  
  if (username.length < 3 || username.length > 50) {
    setError('Username must be between 3 and 50 characters');
    return;
  }

  if (email && !/\S+@\S+\.\S+/.test(email)) {
  setError('Please enter a valid email address');
  return;
}

if (fullName && (fullName.length < 2 || fullName.length > 100)) {
  setError('Full name must be between 2-100 characters if provided');
  return;
}

  try {
    // Construct the user data object to send to the backend
    const userData = {
      username,
      password,
      full_name: fullName, 
      email
    };
    
    const result = await register(userData);  // send the whole object to the register function
    console.log('Registration successful:', result);
    
    const message = `Account created for ${result.username || username}! You can now login.`;

    navigate('/login', { state: { success: message } });
  } catch (err) {
    setError(err.message || 'Registration failed');
    console.error('Registration error:', err);
  }
};

  return (
    <div className="register-page">
      <div className="register-container">
        <h1 className="register-title">Create Account</h1>
        
        <form onSubmit={handleSubmit} className="register-form">

          {/* Username Field */}
          <div className="form-group">
            <label htmlFor="username">Username *</label>
            <input
              name='username'
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Choose a username"
              required
              disabled={loading}
              minLength="3"
              maxLength="50"
            />
            <small className="form-hint">3-50 characters, letters, numbers and underscores only</small>
          </div>
          
          {/* Full Name Field */}
          <div className="form-group">
            <label htmlFor="fullName">Full Name (Optional)</label>
            <input
              name='fullName'
              id="fullName"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Your full name"
              disabled={loading}
              minLength="2"
              maxLength="100"
            />
          </div>
          
          {/* Email Field */}
          <div className="form-group">
            <label htmlFor="email">Email *</label>
            <input
              name='email'
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Your email address"
              required
              disabled={loading}
            />
            <small className="form-hint">Required. Please use a valid email address.</small>
          </div>

          {/* Password Field */}
          <div className="form-group">
            <label htmlFor="password">Password *</label>
            <input
              name='password'
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Create a password"
              required
              disabled={loading}
              minLength="8"
            />
            <small className="form-hint">At least 8 characters must include upper and lower case letters, numbers and special characters</small>
          </div>
          
          {/* Confirm Password Field */}
          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password *</label>
            <input
              name='confirmPassword'
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm your password"
              required
              disabled={loading}
            />

          </div>
          
          {error && <div className="error-message">{error}</div>}
          
          <button
            type="submit"
            className="submit-button"
            disabled={loading || !username || !password || !confirmPassword}
          >
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>
        
        <div className="register-links">
          {/* <p>Already have an account? <a href="/login">Login here</a></p> */}
          <p>Already have an account? <Link to="/login">Login here</Link></p>
          <p className="terms-note">
            By registering, you agree to our <Link to="/terms">Terms of Service</Link> and <Link to="/privacy">Privacy Policy</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default RegisterPage;