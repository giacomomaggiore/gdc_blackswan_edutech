import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

function ChallengeModal({ challenge, onClose }) {
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [isCorrect, setIsCorrect] = useState(false);

  const handleAnswerSelect = (index) => {
    setSelectedAnswer(index);
    const correct = index === challenge.correctAnswer;
    setIsCorrect(correct);
    setShowFeedback(true);

    // Simulate API call to submit answer
    setTimeout(() => {
      // In a real app, this would be an API call
      console.log('Answer submitted:', { questionIndex: index, correct });
    }, 500);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-white/10 backdrop-blur-lg rounded-xl p-8 max-w-lg w-full shadow-xl"
      >
        <h3 className="text-xl font-semibold mb-6">{challenge.question}</h3>
        
        <div className="space-y-3">
          {challenge.options.map((option, index) => (
            <motion.button
              key={index}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => handleAnswerSelect(index)}
              disabled={selectedAnswer !== null}
              className={`w-full p-4 text-left rounded-lg transition-colors ${
                selectedAnswer === index
                  ? isCorrect
                    ? 'bg-green-500/20 border-green-500'
                    : 'bg-red-500/20 border-red-500'
                  : 'bg-white/5 hover:bg-white/10 border-white/20'
              } border`}
            >
              {option}
            </motion.button>
          ))}
        </div>

        <AnimatePresence>
          {showFeedback && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className={`mt-6 p-4 rounded-lg ${
                isCorrect ? 'bg-green-500/20' : 'bg-red-500/20'
              }`}
            >
              <p className="text-center font-semibold">
                {isCorrect ? 'Correct! Well done!' : 'Not quite right. Try again!'}
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="mt-6 flex justify-end">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onClose}
            className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-semibold transition-colors"
          >
            Close
          </motion.button>
        </div>
      </motion.div>
    </motion.div>
  );
}

export default ChallengeModal; 