import React from "react";
import { useNavigate, useParams } from "react-router-dom";

const DifficultySelection = () => {
  const navigate = useNavigate();
  const { category, subcategory } = useParams();

  const handleSelect = () => {
    navigate(`/quiz/${category}/${subcategory}/default`);
  };

  return (
    <div className="p-6 text-center">
      <h2 className="text-2xl font-bold mb-6">Start Quiz</h2>
      <p className="mb-2">Category: <strong>{category}</strong></p>
      <p className="mb-6">Subcategory: <strong>{subcategory}</strong></p>

      <button
        onClick={handleSelect}
        className="bg-white text-black p-4 rounded-xl shadow hover:shadow-lg transition"
      >
        Start Quiz
      </button>
    </div>
  );
};

export default DifficultySelection;