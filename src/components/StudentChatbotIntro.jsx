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

const typingAnimation = {
  initial: { width: 0 },
  animate: { 
    width: "100%",
    transition: {
      duration: 2,
      ease: "easeInOut"
    }
  }
};

function StudentChatbotIntro({ onComplete }) {
  const [introData, setIntroData] = useState(null);
  const [answers, setAnswers] = useState(['', '', '', '']); // Added space for math topic
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [direction, setDirection] = useState(1);
  const [showTypingAnimation, setShowTypingAnimation] = useState(true);

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
        // Hide typing animation after 2 seconds
        setTimeout(() => setShowTypingAnimation(false), 2000);
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
            character: answers[2] || 'adventurer',
            mathTopic: answers[3] || 'algebra' // Include math topic in the request
          }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
          throw new Error(data.error || 'Failed to generate story');
        }
        
        if (!data.sceneText || !data.questions || !Array.isArray(data.questions) || !data.questions[0]?.prompt || !data.questions[0]?.choices) {
          throw new Error('Invalid story data received from server');
        }
        
        onComplete({ 
          answers, 
          character: answers[2] || 'adventurer', 
          storyContext: answers[1] || 'fantasy world', 
          mathTopic: answers[3] || 'algebra',
          storyData: data 
        });
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
    <div className="relative min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-indigo-950 to-purple-900 py-12 px-2 overflow-hidden">
      {/* Animated gradient background */}
      <motion.div
        className="absolute inset-0 z-0"
        style={{ pointerEvents: 'none' }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1 }}
      >
        <motion.div
          className="w-full h-full"
          animate={{
            background: [
              'radial-gradient(circle at 20% 30%, #4f46e5 0%, #a21caf 60%, #111827 100%)',
              'radial-gradient(circle at 80% 70%, #a21caf 0%, #4f46e5 60%, #111827 100%)',
              'radial-gradient(circle at 50% 50%, #4f46e5 0%, #a21caf 60%, #111827 100%)',
              'radial-gradient(circle at 20% 30%, #4f46e5 0%, #a21caf 60%, #111827 100%)'
            ]
          }}
          transition={{ 
            duration: 20, 
            repeat: Infinity, 
            ease: 'easeInOut',
            times: [0, 0.33, 0.66, 1]
          }}
          style={{ width: '100%', height: '100%', position: 'absolute', zIndex: 0 }}
        />
      </motion.div>
      <motion.div
        className="max-w-xl w-full mx-auto bg-white/10 backdrop-blur-lg rounded-3xl p-10 space-y-8 z-10"
        whileHover={{ scale: 1.04 }}
        initial={{ scale: 1 }}
        animate={{ scale: 1 }}
        transition={{ type: 'spring', stiffness: 200, damping: 20 }}
        style={{ minHeight: '60vh' }}
      >
        <motion.h2 
          className="text-2xl font-bold mb-6 text-center"
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 15 }}
        >
          Welcome to Math Adventures!
        </motion.h2>

        {showTypingAnimation && (
          <></>
        )}

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
              {currentQuestion === 3 ? (
                <motion.input
                  type="text"
                  value={answers[currentQuestion]}
                  onChange={(e) => handleAnswerChange(currentQuestion, e.target.value)}
                  className="w-full p-4 rounded-lg bg-white/5 focus:border-white/40 focus:outline-none"
                  placeholder="e.g., fractions, probability, patterns in nature..."
                  required
                  variants={fadeInUp}
                  transition={{ delay: 0.1 }}
                />
              ) : (
                <motion.textarea
                  value={answers[currentQuestion]}
                  onChange={(e) => handleAnswerChange(currentQuestion, e.target.value)}
                  className="w-full p-4 rounded-lg bg-white/5 focus:border-white/40 focus:outline-none"
                  rows="4"
                  placeholder="Tell us about yourself..."
                  required
                  variants={fadeInUp}
                  transition={{ delay: 0.1 }}
                />
              )}
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
    </div>
  );
}

export default StudentChatbotIntro; 