import React from "react";
import { useNavigate, useParams } from "react-router-dom";
import { NO_EASY_OR_HARD_MODE } from "../utils/constants";

const DifficultySelection = () => {
  const navigate = useNavigate();
  const { category, subcategory } = useParams();

  // Determine which difficulties are available
  let availableDifficulties = ["Easy", "Default", "Hard"];
  if (NO_EASY_OR_HARD_MODE.includes(subcategory)) {
    availableDifficulties = ["Default"];
  }

  const handleSelect = (difficulty) => {
    navigate(`/quiz/${category}/${subcategory}/${difficulty.toLowerCase()}`);
  };

  return (
    <div className="p-6 text-center">
      <h2 className="text-2xl font-bold mb-6">Choose Difficulty</h2>
      <p className="mb-2">Category: <strong>{category}</strong></p>
      <p className="mb-6">Subcategory: <strong>{subcategory}</strong></p>

      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        {availableDifficulties.map((level) => (
          <button
            key={level}
            onClick={() => handleSelect(level)}
            className="bg-white text-black p-4 rounded-xl shadow hover:shadow-lg transition"
          >
            {level} Mode
          </button>
        ))}
      </div>

      {availableDifficulties.length === 1 && availableDifficulties[0] === "Default" && (
        <p className="mt-4 text-sm text-gray-500 italic">
          Only Default Mode is available for this subcategory.
        </p>
      )}
    </div>
  );
};

export default DifficultySelection;
