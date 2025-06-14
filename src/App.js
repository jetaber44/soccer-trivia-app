import { useState } from "react";

function App() {
  const questions = [
    {
      text: "Who won the FIFA World Cup in 2018?",
      options: ["Brazil", "France", "Germany", "Argentina"],
      correctAnswer: "France",
    },
    {
      text: "Which country has won the most World Cups?",
      options: ["Italy", "Germany", "Brazil", "Argentina"],
      correctAnswer: "Brazil",
    },
    {
      text: "Who is the all-time top scorer in the UEFA Champions League?",
      options: ["Messi", "Cristiano Ronaldo", "Lewandowski", "Benzema"],
      correctAnswer: "Cristiano Ronaldo",
    },
  ];

  const [screen, setScreen] = useState("start");
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [score, setScore] = useState(0);

  const currentQuestion = questions[currentQuestionIndex];

  const handleAnswerClick = (answer) => {
    setSelectedAnswer(answer);
    if (answer === currentQuestion.correctAnswer) {
      setScore(score + 1);
    }

    // Delay before moving to next question or result
    setTimeout(() => {
      const nextIndex = currentQuestionIndex + 1;
      if (nextIndex < questions.length) {
        setCurrentQuestionIndex(nextIndex);
        setSelectedAnswer(null);
      } else {
        setScreen("result");
      }
    }, 1000); // 1-second delay to show correct/wrong color
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      {/* Start Screen */}
      {screen === "start" && (
        <div className="text-center space-y-4">
          <h1 className="text-3xl font-bold text-blue-700">Soccer Trivia App</h1>
          <button
            className="bg-blue-600 text-white text-lg px-6 py-3 rounded-xl hover:bg-blue-700 transition"
            onClick={() => setScreen("question")}
          >
            Start Quiz
          </button>
        </div>
      )}

      {/* Question Screen */}
      {screen === "question" && (
        <div className="text-center space-y-6">
          <h2 className="text-2xl font-semibold text-gray-800">
            {currentQuestion.text}
          </h2>
          <div className="grid grid-cols-1 gap-4 max-w-xs mx-auto">
            {currentQuestion.options.map((option) => {
              let bgColor = "bg-white";
              if (selectedAnswer) {
                if (option === currentQuestion.correctAnswer) {
                  bgColor = "bg-green-200";
                } else if (option === selectedAnswer) {
                  bgColor = "bg-red-200";
                }
              }

              return (
                <button
                  key={option}
                  className={`${bgColor} border border-gray-300 py-2 rounded-xl hover:bg-gray-100`}
                  onClick={() => handleAnswerClick(option)}
                  disabled={selectedAnswer !== null}
                >
                  {option}
                </button>
              );
            })}
          </div>
          {selectedAnswer && (
            <p className="mt-4 text-lg font-medium text-gray-700">
              {selectedAnswer === currentQuestion.correctAnswer
                ? "Correct! 🎉"
                : `Wrong. The correct answer was ${currentQuestion.correctAnswer}.`}
            </p>
          )}
        </div>
      )}

      {/* Result Screen */}
      {screen === "result" && (
        <div className="text-center space-y-4">
          <h2 className="text-3xl font-bold text-green-700">Quiz Complete!</h2>
          <p className="text-lg text-gray-700">
            You scored <strong>{score}</strong> out of{" "}
            <strong>{questions.length}</strong>
          </p>
          <button
            className="bg-blue-600 text-white text-lg px-6 py-3 rounded-xl hover:bg-blue-700 transition"
            onClick={() => {
              setScreen("start");
              setCurrentQuestionIndex(0);
              setSelectedAnswer(null);
              setScore(0);
            }}
          >
            Play Again
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
