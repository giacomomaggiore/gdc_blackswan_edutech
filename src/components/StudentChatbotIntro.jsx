import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 }
};

const pageTransition = {
  initial: { opacity: 0, x: 20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -20 }
};

function StudentChatbotIntro({ onComplete }) {
  const [introData, setIntroData] = useState(null);
  const [answers, setAnswers] = useState(['', '']);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [direction, setDirection] = useState(1);

  useEffect(() => {
    // Fetch questions from backend
    fetch('http://localhost:5000/api/intro')
      .then(response => {
        if (!response.ok) {
          throw new Error('Failed to fetch questions');
        }
        return response.json();
      })
      .then(data => {
        setIntroData(data);
        setIsLoading(false);
      })
      .catch(error => {
        console.error('Error fetching intro data:', error);
        setError('Failed to load questions. Please make sure the backend server is running.');
        setIsLoading(false);
      });
  }, []);

  const handleAnswerChange = (index, value) => {
    const newAnswers = [...answers];
    newAnswers[index] = value;
    setAnswers(newAnswers);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (currentQuestion < introData.questions.length - 1) {
      setDirection(1);
      setCurrentQuestion(prev => prev + 1);
    } else {
      try {
        setIsLoading(true);
        const response = await fetch('http://localhost:5000/api/generate-story', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            storyContext: answers[1] || 'fantasy world',
            character: answers[2] || 'adventurer'
          }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
          throw new Error(data.error || 'Failed to generate story');
        }
        
        if (!data.sceneText || !data.question || !data.options) {
          throw new Error('Invalid story data received from server');
        }
        
        onComplete({ answers, character: answers[2] || 'adventurer', storyData: data });
      } catch (error) {
        console.error('Error generating story:', error);
        setError(error.message || 'Failed to generate story. Please try again.');
      } finally {
        setIsLoading(false);
      }
    }
  };

  if (isLoading) {
    return (
      <motion.div 
        className="flex justify-center items-center h-64"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        <motion.div 
          className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-white"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        />
      </motion.div>
    );
  }

  if (error) {
    return (
      <motion.div 
        className="max-w-2xl mx-auto bg-red-500/10 backdrop-blur-lg rounded-xl p-8 shadow-xl"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
      >
        <motion.h2 
          className="text-2xl font-bold mb-6 text-center text-red-500"
          initial={{ scale: 0.9 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 15 }}
        >
          Error
        </motion.h2>
        <motion.p 
          className="text-center"
          variants={fadeInUp}
          initial="initial"
          animate="animate"
        >
          {error}
        </motion.p>
        <motion.p 
          className="text-center mt-4"
          variants={fadeInUp}
          initial="initial"
          animate="animate"
          transition={{ delay: 0.1 }}
        >
          Make sure the backend server is running at http://localhost:5000
        </motion.p>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="max-w-2xl mx-auto bg-white/10 backdrop-blur-lg rounded-xl p-8 shadow-xl"
    >
      <motion.h2 
        className="text-2xl font-bold mb-6 text-center"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 200, damping: 15 }}
      >
        Welcome to Math Adventures!
      </motion.h2>
      <form onSubmit={handleSubmit} className="space-y-6">
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div 
            key={currentQuestion}
            custom={direction}
            variants={pageTransition}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="space-y-4"
          >
            <motion.label 
              className="block text-lg"
              variants={fadeInUp}
            >
              {introData.questions[currentQuestion]}
            </motion.label>
            <motion.textarea
              value={answers[currentQuestion]}
              onChange={(e) => handleAnswerChange(currentQuestion, e.target.value)}
              className="w-full p-4 rounded-lg bg-white/5 border border-white/20 focus:border-white/40 focus:outline-none"
              rows="4"
              placeholder="Tell us about yourself..."
              required
              variants={fadeInUp}
              transition={{ delay: 0.1 }}
            />
          </motion.div>
        </AnimatePresence>
        <motion.button
          type="submit"
          className="w-full py-3 px-6 bg-indigo-600 hover:bg-indigo-700 rounded-lg font-semibold transition-colors"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          variants={fadeInUp}
          transition={{ delay: 0.2 }}
        >
          {currentQuestion < introData.questions.length - 1 ? 'Next Question' : 'Start Adventure'}
        </motion.button>
      </form>
    </motion.div>
  );
}

export default StudentChatbotIntro; 