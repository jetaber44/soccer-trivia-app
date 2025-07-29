import React from 'react';

const About = () => {
  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold mb-4">About Quizlazo</h1>

      <p className="mb-4">
        Quizlazo is a free soccer trivia game designed for fans who want to test their knowledge of the world’s most popular sport. From World Cup history to legendary transfers, we offer a fast-paced, competitive way to challenge your brain and relive the greatest soccer moments.
      </p>

      <p className="mb-4">
        Our mission is to become the most trusted and entertaining source of soccer trivia on the web and mobile. Built by fans, for fans — Quizlazo is always evolving. Whether you're a casual watcher or a fanatic, there's something here for you.
      </p>

      <p className="mb-4">
        Have feedback, questions, or business inquiries? We'd love to hear from you.
      </p>

      <p>
        Contact us at{' '}
        <a href="mailto:contact@quizlazo.com" className="text-blue-400 underline">
          contact@quizlazo.com
        </a>
        .
      </p>
    </div>
  );
};

export default About;
