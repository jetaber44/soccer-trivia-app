import React, { useState } from 'react';
import { db } from '../firebase';
import { collection, addDoc, serverTimestamp } from 'firebase/firestore';

const ContactForm = () => {
  const [email, setEmail] = useState('');
  const [topic, setTopic] = useState('');
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus('');

    if (message.trim() === '') {
      setStatus('Please enter a message before submitting.');
      return;
    }

    try {
      await addDoc(collection(db, 'contactMessages'), {
        email: email.trim(),
        topic: topic || null,
        message: message.trim(),
        createdAt: serverTimestamp(),
      });

      setEmail('');
      setTopic('');
      setMessage('');
      setStatus('Message sent successfully. Thank you!');
    } catch (error) {
      console.error('Error sending message:', error);
      setStatus('Something went wrong. Please try again later.');
    }
  };

  return (
    <div className="mt-10 p-4 border-t border-gray-300">
      <h2 className="text-lg font-semibold text-white mb-2">Contact Us</h2>
      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          type="email"
          placeholder="Your email (optional)"
          className="w-full p-2 border rounded text-black"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <select
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          className="w-full p-2 border rounded text-black"
        >
          <option value="">Topic (optional)</option>
          <option value="Bug or Technical Issue">Bug or Technical Issue</option>
          <option value="Incorrect Trivia Question">Incorrect Trivia Question</option>
          <option value="Suggest a New Trivia Question">Suggest a New Trivia Question</option>
          <option value="Suggest a New Trivia Topic">Suggest a New Trivia Topic</option>
          <option value="Feature or Design Feedback">Feature or Design Feedback</option>
          <option value="Business Inquiry">Business Inquiry</option>
          <option value="Other">Other</option>
        </select>

        <textarea
          placeholder="Your message"
          className="w-full p-2 border rounded h-24 text-black"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          required
        />

        <button
          type="submit"
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
        >
          Send Message
        </button>

        {status && (
          <p className="text-sm mt-2 text-black">{status}</p>
        )}
      </form>
    </div>
  );
};

export default ContactForm;
