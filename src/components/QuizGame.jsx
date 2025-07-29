import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { collection, getDocs, query, where } from "firebase/firestore";
import { db } from "../firebase";
import RefereeCard from "../components/RefereeCard";
import { doc, setDoc, getDoc, increment } from "firebase/firestore";
import { auth } from "../firebase";


async function updateScoreDistribution(uid, score) {
  const statsRef = doc(db, "users", uid, "stats", "overall");
  const docSnap = await getDoc(statsRef);
  const data = docSnap.exists() ? docSnap.data() : {};
  const current = data.scoreDistribution || {};

  const updated = {
    ...current,
    [score]: (current[score] || 0) + 1,
  };

  await setDoc(statsRef, {
    scoreDistribution: updated,
  }, { merge: true });
}

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
  const [yellowCards, setYellowCards] = useState(0);
  const [showCard, setShowCard] = useState(false);
  const [cardType, setCardType] = useState("red");

  const [correctAnswers, setCorrectAnswers] = useState(0);
  const [longestWrongStreak, setLongestWrongStreak] = useState(0);
  const [longestStreak, setLongestStreak] = useState(0);
  const [redCardGiven, setRedCardGiven] = useState(false);

  useEffect(() => {
    async function fetchQuestions() {
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
        const all = snapshot.docs.map(doc => ({
          ...doc.data(),
          questionId: doc.id,
        }));

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

  useEffect(() => {
    async function updateStats() {
      if (
        questions.length > 0 &&
        currentQuestionIndex === questions.length
      ) {
        const user = auth.currentUser;
        if (!user) return;

        try {
          const statsRef = doc(db, "users", user.uid, "stats", "overall");
          const isPerfect = correctAnswers === questions.length;
          await updateScoreDistribution(user.uid, correctAnswers);
          const docSnap = await getDoc(statsRef);
          const currentStats = docSnap.exists() ? docSnap.data() : {};
          const prevCorrect = currentStats.correctAnswers || 0;
          const prevIncorrect = currentStats.incorrectAnswers || 0;
          const prevQuizzes = currentStats.totalQuizzes || 0;
          const prevPerfect = currentStats.totalPerfectQuizzes || 0;
          const prevYellow = currentStats.yellowCards || 0;
          const prevRed = currentStats.redCards || 0;

          const updatedCorrect = prevCorrect + correctAnswers;
          const updatedIncorrect = prevIncorrect + (questions.length - correctAnswers);
          const updatedQuizzes = prevQuizzes + 1;
          const updatedPerfect = isPerfect ? prevPerfect + 1 : prevPerfect;
          const updatedYellow = prevYellow + yellowCards;
          const updatedRed = redCardGiven ? prevRed + 1 : prevRed;

          // Calculated percentages
          const correctPercentage = updatedCorrect + updatedIncorrect > 0
          ? ((updatedCorrect / (updatedCorrect + updatedIncorrect)) * 100).toFixed(1)
          : "0.0";

          const perfectQuizPercentage = updatedQuizzes > 0
          ? ((updatedPerfect / updatedQuizzes) * 100).toFixed(1)
          : "0.0";

          const yellowCardRate = updatedQuizzes > 0
          ? ((updatedYellow / updatedQuizzes) * 100).toFixed(1)
          : "0.0";

          const redCardRate = updatedQuizzes > 0
          ? ((updatedRed / updatedQuizzes) * 100).toFixed(1)
          : "0.0";

          const longestCorrect = currentStats.longestStreakCorrect || 0;
          const longestWrong = currentStats.longestStreakWrong || 0;

          const newLongestCorrect = longestStreak > longestCorrect;
          const newLongestWrong = longestWrongStreak > longestWrong;

          await setDoc(statsRef, {
            totalQuizzes: increment(1),
            correctAnswers: increment(correctAnswers),
            incorrectAnswers: increment(questions.length - correctAnswers),
            ...(isPerfect && { totalPerfectQuizzes: increment(1) }),
            longestStreakCorrect: newLongestCorrect ? longestStreak : longestCorrect,
            longestStreakWrong: newLongestWrong ? longestWrongStreak : longestWrong,
            ...(yellowCards > 0 && { yellowCards: increment(yellowCards) }),
            ...(redCardGiven && { redCards: increment(1) }),
            correctPercentage,
            perfectQuizPercentage,
            yellowCardRate,
            redCardRate
          }, { merge: true });

          // Category stats
          const effectiveSubcategory = subcategory === "All" ? category : subcategory;
          const categoryRef = doc(db, "users", user.uid, "categoryStats", effectiveSubcategory);
          const prevCatSnap = await getDoc(categoryRef);
          const prevCatData = prevCatSnap.exists() ? prevCatSnap.data() : {};
          const prevCatCorrect = prevCatData.correctAnswers || 0;
          const prevCatIncorrect = prevCatData.incorrectAnswers || 0;
          const updatedCatCorrect = prevCatCorrect + correctAnswers;
          const updatedCatIncorrect = prevCatIncorrect + (questions.length - correctAnswers);
          const catCorrectPercentage = updatedCatCorrect + updatedCatIncorrect > 0
            ? ((updatedCatCorrect / (updatedCatCorrect + updatedCatIncorrect)) * 100).toFixed(1)
            : "0.0";

          await setDoc(categoryRef, {
            quizzesPlayed: increment(1),
            correctAnswers: increment(correctAnswers),
            incorrectAnswers: increment(questions.length - correctAnswers),
            correctPercentage: catCorrectPercentage
          }, { merge: true });
        } catch (err) {
          console.error("Failed to update stats:", err);
        }
      }
    }

    updateStats();
  }, [currentQuestionIndex, questions.length, correctAnswers, longestStreak, longestWrongStreak, yellowCards, redCardGiven, subcategory, category]);

  if (loading) return <p>Loading questions...</p>;
  if (questions.length === 0)
    return (
      <p>
        No questions found for {category} – {subcategory} – {difficulty}
      </p>
    );

  const currentQuestion = questions[currentQuestionIndex];

  function triggerRefereeCard(type) {
    setCardType(type);
    setShowCard(true);
    setTimeout(() => setShowCard(false), 2000);
  }

  async function handleSelect(option) {
    if (isAnswered) return;
    setSelected(option);
    setIsAnswered(true);
    // 🧠 Phase 4: Update /collectionBook with question stats
    const user = auth.currentUser;
    if (user && currentQuestion && currentQuestion.questionId) {
      const questionId = currentQuestion.questionId;
      const collectionRef = doc(db, "users", user.uid, "collectionBook", questionId);
      const wasCorrect = option === currentQuestion.answer;
      const now = new Date();

      try {
        const docSnap = await getDoc(collectionRef);
        const existing = docSnap.exists() ? docSnap.data() : {};

        const correctCount = (existing.correctCount || 0) + (wasCorrect ? 1 : 0);
        const incorrectCount = (existing.incorrectCount || 0) + (!wasCorrect ? 1 : 0);
        const firstSeen = existing.firstSeen || now;

        await setDoc(collectionRef, {
          correctCount,
          incorrectCount,
          subcategory,
          firstSeen,
          lastSeen: now
        }, { merge: true });
      } catch (err) {
        console.error("Failed to update collection book:", err);
      }
    }
    
    if (option === currentQuestion.answer) {
      const rawScore = 1000 - (elapsedTime / 150) * 700;
      const points = Math.max(Math.round(rawScore), 300);
      setScore(prev => prev + points);
      setPoints(points);
      setCorrectAnswers(prev => prev + 1);
      setStreak(prev => prev + 1);
      setLongestStreak(prev => Math.max(prev, streak + 1));

      // Reset card state on correct answer
      setLongestWrongStreak(0);
    } else {
      setPoints(0);
      setStreak(0);

      setLongestWrongStreak(prev => {
        const newCount = prev + 1;

        // 6 wrong in a row = red card
        if (newCount === 6) {
          triggerRedCardEnd();
        }

        // 3 wrong in a row = yellow card or red if already had one
        if (newCount === 3) {
          if (yellowCards === 1) {
            triggerRefereeCard("red");
            setRedCardGiven(true);
            triggerRedCardEnd(); // 2nd yellow = red
          } else {
            setYellowCards(1);
            triggerRefereeCard("yellow");
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
  }

  function triggerRedCardEnd() {
    setRedCardGiven(true);
    triggerRefereeCard("red");
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
          <p className="text-red-500 font-bold mb-2">⏰ Time's up!</p>
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
      {yellowCards > 0 && (
        <div
          className="absolute top-3 right-3 z-[200] flex flex-col items-center scale-90 sm:scale-100"
          style={{
            animation: "bounceCard 1s ease-in-out infinite",
            maxWidth: "calc(100vw - 1.5rem)",
          }}
        >
          <div className="w-8 h-14 sm:w-12 sm:h-20 bg-yellow-400 border-2 border-black rounded-sm shadow-lg" />
          <p className="text-yellow-300 font-bold mt-1 text-[11px] sm:text-sm text-center leading-tight whitespace-nowrap">
            ⚠️ 1st Yellow
          </p>
        </div>
      )}
      <RefereeCard type={cardType} show={showCard} />
    </>
  );
}