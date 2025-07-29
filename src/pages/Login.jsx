// src/pages/Login.jsx
import React, { useState } from 'react';
import { auth } from '../firebase';
import { db } from '../firebase';
import { signInWithEmailAndPassword, createUserWithEmailAndPassword } from 'firebase/auth';
import { doc, setDoc, serverTimestamp } from 'firebase/firestore';
import { useNavigate } from 'react-router-dom';

function Login() {
  const [isLoginMode, setIsLoginMode] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const toggleMode = () => {
    setIsLoginMode((prev) => !prev);
    setMessage('');
    setError('');
    setEmail('');
    setPassword('');
  };

  const handleAuth = async () => {
    setIsLoading(true);
    setMessage('');
    setError('');

    try {
      if (isLoginMode) {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        setMessage(`Welcome back, ${userCredential.user.email}!`);
        navigate('/profile'); // ✅ Redirect after login
      } else {
        const userCredential = await createUserWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;

        // Create user document in Firestore
        await setDoc(doc(db, 'users', user.uid), {
          email: user.email,
          createdAt: serverTimestamp(),
        });

        setMessage(`Account created: ${user.email}`);
        navigate('/profile'); // ✅ Redirect after signup
      }
    } catch (err) {
      setError(mapFirebaseError(err.message));
    } finally {
      setIsLoading(false);
    }
  };

  const mapFirebaseError = (msg) => {
    if (msg.includes('email-already-in-use')) return 'That email is already registered.';
    if (msg.includes('auth/invalid-email')) return 'Please enter a valid email.';
    if (msg.includes('wrong-password')) return 'Incorrect password.';
    if (msg.includes('user-not-found')) return 'No account found with that email.';
    if (msg.includes('weak-password')) return 'Password should be at least 6 characters.';
    return msg;
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 p-4">
      <div className="bg-white shadow-md rounded-xl p-6 w-full max-w-md">
        <h2 className="text-2xl font-bold mb-4 text-center text-black">
          {isLoginMode ? 'Login to Quizlazo' : 'Create your Quizlazo Account'}
        </h2>

        <input
          type="email"
          placeholder="Email"
          className="w-full mb-3 p-2 border rounded text-black"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password"
          placeholder="Password"
          className="w-full mb-3 p-2 border rounded text-black"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {isLoading && <div className="text-blue-600 text-sm mb-3">Please wait...</div>}
        {error && <div className="text-red-600 text-sm mb-3">{error}</div>}
        {message && <div className="text-green-600 text-sm mb-3">{message}</div>}

        <button
          onClick={handleAuth}
          className={`w-full ${
            isLoginMode ? 'bg-blue-600 hover:bg-blue-700' : 'bg-green-600 hover:bg-green-700'
          } text-white py-2 rounded mb-2`}
        >
          {isLoginMode ? 'Log In' : 'Sign Up'}
        </button>

        <p className="text-sm text-gray-600 text-center mt-4">
          {isLoginMode ? "Don't have an account?" : 'Already have an account?'}{' '}
          <button onClick={toggleMode} className="text-blue-600 underline">
            {isLoginMode ? 'Sign Up' : 'Log In'}
          </button>
        </p>

        {/* ✅ Legal links */}
        <div className="text-center text-xs text-zinc-500 mt-6 space-x-4">
          <a href="/about" className="hover:underline">About</a>
          <a href="/privacy" className="hover:underline">Privacy Policy</a>
        </div>
        <div className="text-center text-xs text-zinc-500 mt-2">
          <a href="mailto:contact@quizlazo.com" className="hover:underline">Need help? Contact us</a>
        </div>
      </div>
    </div>
  );
}

export default Login;
