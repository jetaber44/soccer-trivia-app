import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { collection, getDocs, query, where } from "firebase/firestore";
import { db } from "../firebase";

export default function QuizGame() {
  const { category, subcategory, difficulty } = useParams();
  const navigate = useNavigate();

  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selected, setSelected] = useState(null);
  const [isAnswered, setIsAnswered] = useState(false);
  const [score, setScore] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(15);
  const [timerActive, setTimerActive] = useState(true);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [points, setPoints] = useState(null);
  const [streak, setStreak] = useState(0);
  const [showYellowCard, setShowYellowCard] = useState(false);
  const [yellowCards, setYellowCards] = useState(0);
  const [showRedCard, setShowRedCard] = useState(false);

  const [correctAnswers, setCorrectAnswers] = useState(0);
const [longestStreak, setLongestStreak] = useState(0);
useEffect(() => {
    async function fetchQuestions() {
      const NO_EASY_OR_HARD_MODE = [
        "CONCACAF", "CAF", "AFC", "OFC",
        "MLS", "Rest of World",
        "2000s", "1990s", "1980s", "1970s or Earlier"
      ];

      try {
        const baseQuery = collection(db, "triviaQuestions");

        let snapshot;

        if (subcategory === "All") {
          snapshot = await getDocs(
            query(baseQuery, where("category", "==", category))
          );
        } else {
          snapshot = await getDocs(
            query(baseQuery, where("subcategories", "array-contains", subcategory))
          );
        }
const all = snapshot.docs.map(doc => doc.data());

        let selected = [];

          const mode = difficulty.toLowerCase();
          const usedTexts = new Set();

          if (mode === "default") {
            const easyPool = all.filter(q => q.difficulty === "easy");
            const hardPool = all.filter(q => q.difficulty === "hard");
            const defaultPool = all.filter(q => !["easy", "hard"].includes(q.difficulty));

            const easySet = shuffle([...easyPool, ...defaultPool]);
            const hardSet = shuffle([...hardPool, ...defaultPool]);

            const pickedEasy = [];
            const pickedHard = [];

            for (let q of easySet) {
              if (!usedTexts.has(q.question)) {
                pickedEasy.push(q);
                usedTexts.add(q.question);
              }
              if (pickedEasy.length === 5) break;
            }

            for (let q of hardSet) {
              if (!usedTexts.has(q.question)) {
                pickedHard.push(q);
                usedTexts.add(q.question);
              }
              if (pickedHard.length === 5) break;
            }

            selected = shuffle([...pickedEasy, ...pickedHard]);

          } else if (mode === "easy" || mode === "hard") {
            const filtered = all.filter(q =>
              q.difficulty === mode || !["easy", "hard"].includes(q.difficulty)
            );  
            selected = dedupeAndSlice(filtered, 10);
          }

        setQuestions(selected);
      } catch (err) {
        console.error("Error loading questions:", err);
      } finally {
        setLoading(false);
      }
    }

    function shuffle(arr) {
      return [...arr].sort(() => Math.random() - 0.5);
    }

    function dedupeAndSlice(pool, count) {
      const seen = new Set();
      const unique = [];

      for (const q of shuffle(pool)) {
        if (!seen.has(q.question)) {
          seen.add(q.question);
          unique.push(q);
        }
        if (unique.length === count) break;
      }
      return unique;
    }

    fetchQuestions();
  }, [category, subcategory, difficulty]);

  useEffect(() => {
    if (!timerActive || isAnswered) return;

    const timer = setInterval(() => {
      setElapsedTime(prev => prev + 1);
      setTimeRemaining(prev => {
        if (prev <= 0.1) {
          clearInterval(timer);
          setIsAnswered(true);
          setStreak(0);
          return 0;
        }
        return +(prev - 0.1).toFixed(1);
      });
    }, 100);

    return () => clearInterval(timer);
  }, [timerActive, isAnswered]);

  if (loading) return <p>Loading questions...</p>;
  if (questions.length === 0)
    return (
      <p>
        No questions found for {category} – {subcategory} – {difficulty}
      </p>
    );

  const currentQuestion = questions[currentQuestionIndex];

  function handleSelect(option) {
  if (isAnswered) return;
  setSelected(option);
  setIsAnswered(true);

  if (option === currentQuestion.answer) {
    const rawScore = 1000 - (elapsedTime / 150) * 700;
    const points = Math.max(Math.round(rawScore), 300);
    setScore(prev => prev + points);
    setPoints(points);
    setCorrectAnswers(prev => prev + 1);
    setStreak(prev => prev + 1);
    setLongestStreak(prev => Math.max(prev, streak + 1));

    // Reset card state on correct answer
    setWrongStreak(0);
    setShowYellowCard(false);
  } else {
    setPoints(0);
    setStreak(0);

    setWrongStreak(prev => {
      const newCount = prev + 1;

      // 6 wrong in a row = red card
      if (newCount === 6) {
        triggerRedCardEnd();
      }

      // 3 wrong in a row = yellow card
      if (newCount === 3) {
  if (yellowCards === 1) {
    triggerRedCardEnd(); // 2nd yellow = red
  } else {
    setShowYellowCard(true);
    setYellowCards(1);
  }
}


      return newCount;
    });
  }
}

  function nextQuestion() {
    setSelected(null);
    setIsAnswered(false);
    setCurrentQuestionIndex(prev => prev + 1);
    setTimeRemaining(15);
    setElapsedTime(0);
    setTimerActive(true);
    setPoints(null);
    setShowYellowCard(false);
  }

  function triggerRedCardEnd() {
    setShowRedCard(true);
    setTimeout(() => {
      setCurrentQuestionIndex(questions.length); // Forces summary screen
    }, 1500);
  }

  if (currentQuestionIndex >= questions.length) {
  return (
    <div className="text-center px-4 py-10 max-w-xl mx-auto">
      <h2 className="text-3xl font-extrabold mb-6 text-white">🎉 Quiz Complete!</h2>

      <p className="text-amber-400 text-xl font-bold mb-2">
        Total Score: {score}
      </p>
      <p className="text-white text-lg mb-1">
        Questions Correct: {correctAnswers} / {questions.length}
      </p>
      <p className="text-white text-lg mb-6">
        Longest Streak: {longestStreak}
      </p>

      <button
        onClick={() => navigate("/")}
        className="bg-white text-black font-semibold px-6 py-3 rounded-xl shadow hover:shadow-lg transition"
      >
        🔁 Back to Category Selection
      </button>
    </div>
  );
}

  return (
  <>
    {showRedCard && (
      <div className="fixed inset-0 bg-black bg-opacity-80 flex flex-col justify-center items-center z-50">
        <div className="w-24 h-36 bg-red-500 border-4 border-black rounded-sm shadow-2xl animate-pulse"></div>
        <p className="text-white font-bold mt-4 text-2xl">🚫 Red Card – Game Over</p>
      </div>
    )}

    <div className="text-center px-4 py-6 max-w-2xl mx-auto">
      <p className="text-amber-400 font-extrabold text-lg mb-4">Total Score: {score}</p>
      <h2 className="text-2xl font-semibold mb-4">Question {currentQuestionIndex + 1}</h2>

      {/* Timer Bar */}
      <div className="h-2 bg-gray-300 rounded mb-4 overflow-hidden">
        <div
          className="h-full transition-all"
          style={{
            width: `${(timeRemaining / 15) * 100}%`,
            backgroundColor: timeRemaining <= 3 ? "red" : "#00b894",
          }}
        />
      </div>

      <p className="mb-4 font-medium">Time Remaining: {timeRemaining.toFixed(1)}s</p>

      {isAnswered && timeRemaining === 0 && (
        <p className="text-red-500 font-bold mb-2">⏰ Time’s up!</p>
      )}

      {isAnswered && points !== null && (
        <p className="text-amber-400 font-extrabold text-xl mb-4">+{points} points</p>
      )}

      <p className="text-lg mb-6">{currentQuestion.question}</p>

      {/* Answer Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        {currentQuestion.options.map((option, idx) => (
          <button
            key={idx}
            onClick={() => handleSelect(option)}
            disabled={isAnswered}
            className={`p-4 rounded-xl shadow font-bold text-black w-full transition
              ${isAnswered
                ? option === currentQuestion.answer
                  ? "bg-green-400"
                  : option === selected
                  ? "bg-red-400"
                  : "bg-white"
                : "bg-white hover:shadow-lg"}
            `}
          >
            {option}
          </button>
        ))}
      </div>

      {showYellowCard && (
        <div className="flex flex-col items-center mb-6">
          <div className="w-20 h-32 bg-yellow-400 border-4 border-black rounded-sm shadow-lg"></div>
          <p className="text-yellow-300 font-semibold mt-3">⚠️ 3 wrong in a row</p>
        </div>
      )}

      {isAnswered && (
        <button
          onClick={nextQuestion}
          className="bg-blue-600 text-white px-6 py-3 rounded-xl shadow hover:bg-blue-700 transition"
        >
          Next
        </button>
      )}

      <p className="mt-6 font-medium">Current Streak: {streak}</p>
    </div>
  </>
)};
